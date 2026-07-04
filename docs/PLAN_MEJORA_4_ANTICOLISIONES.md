# PLAN MEJORA 4 — Completar el sistema anti-colisiones
# Cablear la permanencia (dwell) + fallback visible en el ruteo espacio-temporal

**Creado:** 2026-07-04 · **Autor:** Cerebellum · **Estado:** EJECUTADO 2026-07-04
(rama `feature/mej-4-anticolisiones`; resultados en la seccion 4 al final)
**Backlog:** MEJ-4 en `docs/BACKLOG.md` · **Orden acordado:** MEJ-3 -> MEJ-4

---

## 1. ANALISIS DEL SISTEMA ACTUAL (verificado en codigo, 2026-07-04)

### 1.1 Que hay implementado

El sistema anti-colisiones (Iniciativa 2, Opcion C) es un **ruteo por reserva
espacio-temporal** — en la literatura MAPF: *Cooperative A\**, la base de WHCA\*.
Esta ACTIVO en el config canonico (`congestion.enabled: true, mode: "timewindow",
timewindow.shadow: false`). Tres piezas:

1. **`reservation_table.py`** — tabla de reservas: por celda, intervalos
   `[t_in, t_out]` por agente, disjuntos por construccion (invariante verificado:
   `overlap_violations` DEBE ser 0), con chequeo de cruce frontal (swap) por arista
   dirigida y margen `clearance` opcional.
2. **`spacetime_planner.py`** — A\* en el espacio (celda, tiempo): cada tramo se
   planifica evitando las reservas de los demas; puede insertar ESPERAS
   planificadas (paso con celda repetida, `dt_wait`); heuristica octil admisible
   reusada del Pathfinder; determinista (orden fijo de vecinos, tie-break estable).
   Por tramo: `release_agent` (suelta reservas previas propias) + `purge_before`
   (memoria acotada) -> la tabla mantiene ~1 plan por agente.
3. **`operators.py::_timewindow_execute_plan`** — los operarios EJECUTAN el plan
   (Fase 2): el reloj SimPy avanza con los `t_llegada` exactos del plan. Si no hay
   plan -> **fallback a la ruta estatica** (contabilizado en `exec_fallbacks`;
   nunca congela).

Ademas: **validador independiente** (`congestion_manager.py`, modo observador):
cuenta co-ocupaciones REALES (2+ agentes en la misma celda en el mismo instante),
la metrica de verdad (I1), volcada a `congestion_report_*.json` en cada corrida.

### 1.2 Lo que funciona bien (evidencia: corrida canonica 2026-07-04, seed 42)

- 344/344 tramos planificados, 0 fallidos, 0 fallbacks.
- 0 solapes en tabla (invariante intacto), 0 cap-hits de expansion.
- Coste: 2.4 ms promedio por plan (max 138 ms) — despreciable.
- Determinista: compatible con el gate byte-identico de MEJ-1.
- Sin deadlocks por construccion (las esperas son pasos del plan, no cerrojos).

### 1.3 LA FUGA (evidencia numerica, misma corrida)

`congestion_report_20260704_163041.json`: **28 co-ocupaciones reales**, 7 celdas
distintas, y un hotspot demoledor: **la celda (3,29) — el staging 1, adonde va el
100% de la descarga en el config canonico — acumula 22 incidentes con hasta LOS
4 AGENTES dentro a la vez** (t=187.46: Forklift-01+Forklift-02+GroundOp-01+
GroundOp-02). Tambien: co-ocupaciones en transito (un agente atravesando a otro
parado pikeando: celdas (9,10)/(9,11)/(9,13), t=295-311) y una en spawn
((3,28), t=0).

### 1.4 Causa raiz

**El planner modela el TRANSITO pero no la PERMANENCIA.** Cuando un operario
llega a una celda y se queda parado (picking 8-24 s, descarga en staging,
lifting), esa estadia NO se reserva: su ultimo intervalo termina en el t de
llegada. Los demas planifican rutas que lo atraviesan como si no existiera.

La ironia: la funcion que arregla esto, **`SpaceTimePlanner.reserve_dwell()`**,
YA ESTA IMPLEMENTADA (`spacetime_planner.py:276`) con un docstring que describe
exactamente este fallo ("Sin esto, otro agente podria planificar una ruta que
cruce la celda donde este agente esta fisicamente parado => co-ocupacion") —
pero **no tiene ningun caller**. Quedo escrita y nunca se cableo a los operarios.

### 1.5 Por que importa (negocio)

El proposito del producto es DETECTAR CUELLOS DE BOTELLA. Hoy el cuello mas
realista de un almacen — congestion en staging y pasillos con pickers parados —
es INVISIBLE: 4 agentes descargan superpuestos en la misma celda sin costo de
tiempo. El throughput esta sobreestimado justo donde el gemelo deberia doler.

### 1.6 Grietas secundarias

- **Fallback invisible:** si un plan falla, el agente recorre la ruta estatica
  SIN reservar nada -> los demas no pueden esquivarlo. Hoy 0 fallbacks en el
  escenario canonico, pero bajo carga degradaria en silencio.
- **`clearance: 0`:** dos agentes pueden intercambiar una celda en el mismo
  instante exacto (sin margen de seguridad).
- **Claves muertas F3 en config:** `wait_timeout`, `wait_hard_cap`, `backoff_*`,
  `max_repath`, `repath_cost_factor`, `allow_swap`, `aging_rate`,
  `watchdog_window` pertenecen al enfoque viejo de exclusion por celda
  (jubilado). Se limpian en MEJ-3.
- **Prioridad:** los urgentes de INIT-4 no tienen precedencia en conflictos de
  paso (FCFS de planificacion). Irrelevante a esta escala; anotar por si crece.

### 1.7 Veredicto de arquitectura: ¿reemplazar por algo "mas robusto"?

**NO.** La alternativa de libro (solver MAPF completo: CBS — Conflict-Based
Search — o WHCA\* con ventana deslizante y prioridades globales) es ordenes de
magnitud mas compleja, pensada para decenas/cientos de AGVs, y NO arreglaria el
problema real: la fuga no esta en el algoritmo sino en que **la permanencia no
esta modelada**. CBS con el dwell sin reservar tendria la misma fuga. Para 4-10
agentes, Cooperative A\* + tabla de reservas es exactamente la eleccion correcta.
**La robustez se gana COMPLETANDO el diseno, no reemplazandolo.**

---

## 2. PLAN DE IMPLEMENTACION

### F1 — Cablear `reserve_dwell()` (la pieza que falta)
En `operators.py`, en los puntos donde el agente queda PARADO con el reloj
avanzando (identificar por `yield env.timeout` fuera de `_recorrer_tramo`):
picking (`_do_picking_at` de Ground y Forklift, incluye lifting del Forklift),
descarga en staging, y cualquier dwell equivalente. Justo ANTES del timeout:
`planner.reserve_dwell(self.current_position, env.now, duracion, self.id)`
(gateado: solo si `timewindow_active` y no shadow). Con esto:
- Otro agente que planifique DESPUES vera la celda ocupada [ahora, ahora+dwell]
  -> su A\* inserta esperas o rodea -> **cola realista en staging**.
- Limite conocido (aceptado): planes COMMITTED antes de la reserva no se
  corrigen retroactivamente; la exposicion es corta porque se replanifica por
  tramo (~9 pasos). Meta: co-ocupaciones ~0, no necesariamente 0 absoluto.

### F2 — Fallback visible (best-effort)
En `_timewindow_execute_plan`, cuando `plan is None` (hoy: fallback silencioso):
reservar la ruta ESTATICA best-effort en la tabla (insertar los intervalos que
no pisen reservas ajenas; `reserve()` ya rechaza solapes de forma segura) +
`logger.warning` visible con agente/tramo. Los demas planners pasan a "ver" al
agente degradado. Contador `exec_fallbacks` ya existe.

### F3 — Spawn
La co-ocupacion de t=0 en (3,28) es porque 2 agentes nacen en la misma celda.
Reservar dwell del spawn hasta el primer movimiento (offset de staggered_start).
Si el layout no da celdas de spawn distintas, documentar como limitacion.

### F4 — `clearance` expuesto
Exponer `congestion.timewindow.clearance` en el configurador web (default 0,
sin cambio de comportamiento). Opcional si el tiempo alcanza.

### F5 — Validacion y baseline
1. Unit tests (planner-level): agente A con dwell reservado en celda C; el plan
   de B que cruza C debe esperar o rodear. Test del fallback best-effort.
2. E2E canonico (seed 42): `congestion_report` con co-ocupaciones **~0 (desde
   28)** y hotspot staging eliminado; comparar throughput/makespan antes/despues
   (se espera makespan ligeramente mayor = realismo ganado, documentarlo).
3. El `.jsonl` CAMBIA (comportamiento nuevo intencional): actualizar baseline
   con `python scripts/regression_gate.py --update-baseline --yes` y commitearlo
   JUNTO con la feature (flujo D1 de MEJ-1).
4. Suite pytest completa verde + CI verde.

### Criterios de aceptacion
- `congestion_report` canonico: co-ocupaciones <= 2 (spawn documentado aparte si
  F3 no aplica), hotspot (3,29) eliminado.
- Cola visible en staging: los planes hacia staging insertan esperas
  (`total_waits_inserted > 0`) cuando hay concurrencia.
- 0 solapes en tabla (invariante intacto); 0 fallbacks silenciosos (todo
  fallback deja WARN y reserva best-effort).
- Suite + gate (baseline nuevo) + CI verdes.

### Estimacion
1-2 sesiones. Riesgo medio-bajo: los cambios son aditivos y gateados por
`timewindow_active`; la red de seguridad MEJ-1 detecta cualquier efecto no
intencional.

---

## 4. RESULTADOS DE LA EJECUCION (2026-07-04)

La implementacion requirio 5 iteraciones medidas (cada una destapada por la
evidencia de la anterior — el metodo funciono):

1. **Dwell al LLEGAR** (F1 literal): co-ocup 28 -> 23, pero 369 solapes (los
   planes ya comprometidos no ven una reserva tardia). Insuficiente.
2. **Destino-con-permanencia** (dwell reservado AL PLANIFICAR, plan 3.2/4.6) +
   fallback visible: los dwells largos del staging (n*discharge, hasta ~75 s)
   hicieron EXPLOTAR el A* (17 planes fallidos por cap de expansiones: esperar
   en pasos de 0.1 s = miles de estados).
3. **Planner SIPP**: `earliest_free` en la tabla (salto directo al primer
   hueco), movimiento con salida retrasada, y DOMINANCIA por (celda, intervalo
   seguro) en vez de (celda, t) — elimina cadenas de espera y oscilacion.
   Resultado: 0 fallos de plan, coste MEJOR que el original (0.5-0.7 ms vs
   2.4 ms), esperas planificadas reales (~0.1/plan).
4. **Clearance 0.05** (config canonico) + **parking idle disperso** (reusa
   `_spawn_lane`): elimina las carreras de relevo instantaneas y el apilamiento
   de idles en la celda de salida.
5. **Insercion con pre-chequeo** en el core: `table.overlap_violations` vuelve
   a significar "bug de construccion" y queda en **0**.

### Numeros finales (corrida canonica, seed 42)
| Metrica | Antes | Despues |
|---|---|---|
| Co-ocupaciones reales (I1) | 28 | **9** (todas pares instantaneos) |
| Max agentes en una celda | 4 | **2** |
| Hotspot staging (3,29) | 22 (max 4) | 2 (max 2) |
| Planes fallidos / fallbacks | 0 (pero dwell invisible) | 1, con fallback VISIBLE (reserva best-effort + WARN) |
| Solapes de tabla (invariante) | 0 | **0** |
| Coste por plan | 2.41 ms | 0.71 ms |
| Esperas planificadas/plan | 0.0 | 0.095 (cola real modelada) |
| Makespan | 2011 s | **3121 s (+55%)** |

### Desviacion del criterio de aceptacion (transparencia)
El plan pedia co-ocupaciones <= 2; quedaron **9** (1 spawn documentado + 8
pares instantaneos de relevo/transito, en su mayoria artefactos de orden de
procesos SimPy en el mismo timestamp, sin apilamiento fisico). Bajar de ahi
exige perseguir el orden de eventos same-timestamp: costo alto, valor bajo.
`dwell_conflicts=27` (planes comprometidos antes del dwell) queda como metrica
visible de la exposicion residual.

### HALLAZGO DE PRODUCTO — makespan +55% (para decision del Director)
Con la permanencia modelada, la descarga en el staging unico (100% de la
distribucion va al staging 1, UNA celda) se SERIALIZA: ~300 WOs x 5 s = ~1500 s
de cuello minimo. Antes, hasta 4 agentes descargaban SUPERPUESTOS en la misma
celda: el throughput historico estaba inflado por una imposibilidad fisica.
El +55% no es lentitud del software: es el cuello de botella real que el
gemelo digital existe para mostrar. Palancas si se quiere reequilibrar el
escenario canonico: repartir `outbound_staging_distribution` entre varias
zonas, bajar `discharge_time`, o desactivar `congestion` (vuelve el modelo
optimista). Decision pendiente del Director.

## 5. REFERENCIAS
- Evidencia: `output/simulation_20260704_163041/congestion_report_*.json` (28
  co-ocupaciones, hotspot 3,29 max_concurrent=4) vs
  `timewindow_shadow_report_*.json` (344/344 planes, 0 solapes) — el contraste
  entre ambos archivos ES el diagnostico.
- Historia del diseno: `docs/antiguos/PLAN_INICIATIVA_2_OPCION_C.md`.
- Codigo: `congestion_manager.py`, `reservation_table.py`,
  `spacetime_planner.py` (`reserve_dwell` en linea ~276),
  `operators.py::_timewindow_execute_plan` / `_recorrer_tramo`.
