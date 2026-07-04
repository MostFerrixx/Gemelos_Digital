# HANDOFF — Gemelo Digital de Almacen
# Estado operativo para nueva sesion de Cerebellum

**Generado:** 2026-06-18  ·  **Actualizado:** 2026-07-04
**Por:** Cerebellum (sesion de traspaso)
**Rama activa:** `feature/mej-1-red-seguridad` (desde `0179539` = main)
**Ultimo hito:** MEJ-1 COMPLETA (red de seguridad: pytest + gate byte-identico
+ CI). Ver docs/PLAN_MEJORA_1_RED_SEGURIDAD.md y seccion 4. Proxima accion
sugerida: merge de MEJ-1 y arrancar MEJ-3 (seccion 5).

---

## 1. QUE ES EL PROYECTO

Simulador de gemelo digital de almacen (Warehouse Digital Twin).
- **Motor:** SimPy (eventos discretos, headless) -> archivo `.jsonl` -> analitica Excel + heatmap.
- **Web:** FastAPI en puerto 8000 — configurador + runner + **visor de replay web (unico frontend)**.
- **Entidades:** GroundOperator (picking manual), Forklift (carga pesada), WorkOrders (SKU de rack a staging).
- **NO hay simulacion en vivo**: el flujo siempre es headless -> jsonl -> replay.

Stack: Python / SimPy / pytmx / pandas+openpyxl / Optuna / FastAPI+uvicorn+pydantic / SQLite.
`pygame-ce` es dependencia del headless (lectura del TMX en layout_manager), no de GUI.
> NOTA: FastAPI/uvicorn/pydantic YA estan en requirements.txt; un pip install limpio levanta el servidor web.

---

## 2. ARQUITECTURA — CADENA VIVA (verificada 2026-06-29)

```
entry_points/run_generate_replay.py
  -> src/engines/event_generator.py          (headless SimPy -> .jsonl + Excel + heatmap)

entry_points/run_optimization.py
  -> src/tools/optimizer.py                  (Optuna)

web_prototype/server.py  (FastAPI :8000)     (configurador web + runner + VIEWER WEB)
  -> start_server.bat / server_manager.py / start_hidden.py   (unico frontend vigente)

run_migration.py
  -> src/subsystems/database/               (Excel -> SQLite warehouse.db)
```

`src/engines/` solo contiene `event_generator.py` y `analytics_engine.py`.

Nucleo de simulacion SANO: `src/subsystems/simulation/`
  warehouse.py, dispatcher.py (DispatcherV11), operators.py, order_strategies.py,
  data_manager.py, assignment_calculator.py, route_calculator.py,
  pathfinder.py, layout_manager.py, outbound.py
  + capa de congestion (Iniciativa 2, VIVA y ACTIVA en config canonico):
  congestion_manager.py, reservation_table.py, spacetime_planner.py.
  `congestion.enabled: true, mode: "timewindow", shadow: false` en config.json
  => los operarios EJECUTAN el plan espacio-temporal (Fase 2, fallback estatico).
  El baseline byte-identico (a4ae8d4e...) se genero CON esta capa activa.

Archivos VIVOS fuera de src/ (no borrar sin pensar):
  simulation_buffer.py, visualizer.py (heatmap por subprocess),
  server_manager.py, start_hidden.py

ARCHIVADO en `_legacy/` (deprecado, reversible, NO borrar sin avisar):
  - `_legacy/gui_escritorio/` (commit 3cd37e6): las 3 GUI de escritorio —
    viewer Pygame (run_replay_viewer.py + replay_engine.py), dashboard PyQt6
    (visualization/ + IPC), configurador Tkinter (configurator.py). Reemplazadas
    por el frontend web. **La live simulation Pygame ya no forma parte de la cadena.**
  - `_legacy/web_dashboard/` (puerto 8001): tabla de WOs huerfana (apunta a un
    replay inexistente), redundante con el panel del viewer web. PENDIENTE decision.
  - `_legacy/legacy|src_shared|utils_root|tools_duplicados|tests_rotos/`: codigo muerto.

Fuente de datos canonica = RAIZ (config.json, layouts/WH1.tmx, layouts/Warehouse_Logic.xlsx).
El arbol data/ es una migracion abandonada que solo lee codigo muerto.

---

## 3. GIT — ESTADO ACTUAL

**Rama:** `feature/allocation-layer-v12.1`
**HEAD:** `0179539` (local y remote identicos)
**main:** `0179539` (sincronizado via fast-forward; divergencia 0/0, verificado 2026-07-04)

No hay commits pendientes de push ni merge.

### Log completo de la rama (mas reciente primero)

```
0179539  docs(backlog): inventario de iniciativas reconciliado + notas de arquitectura
afe5602  docs(readme): al dia post-INIT-4 -- features opt-in y correcciones
a70410e  docs: reconciliar arquitectura real + documentar flags opt-in (CLAUDE + HANDOFF)
edba925  docs(init-4): cierre -- INIT-4 completo (C1+C2+C3), INT-1 ok, docs al dia
fd0a41d  feat(init-4 C3): olas (waves) por release diferido (opt-in)
c27dacb  feat(init-4 C2 Opcion C): prioridad fuerte "limpia" -- urgentes primero sin diluir
0c1682c  feat(init-4 C2): prioridad de pedido / SLA en el despacho (opt-in, base)
91dd6c0  feat(init-4 C1): tiempo de pick escalable por cantidad/volumen (opt-in, neutro)
f3a3ec5  chore(ui): eliminar botones stub E6/E7 (BK-05 cerrado)
7efc9c7  docs(handoff): actualizar estado post-sesion 2026-06-27
41ddc22  refactor(p2): extraer agent_process a BaseOperator (Template Method)
413888c  feat(gate): WAREHOUSE_SEED via env var para reproducibilidad determinista
b990964  refactor(logging): print() -> logging por nivel en hot-path del motor
0e6d3dd  feat(ui): D-13 tokens compartidos + D-15 marcadores de eventos + D-16 no-color
902877a  feat(ui): D-14 stepper numerado de pestanas en el configurador
23b374b  feat(dev): anti-cache en estaticos del front
8cc7f8d  feat(init-5): exponer nivel de servicio / backorders en visor, API y Excel
e2c6293  feat(qa3): mapa explicito work_area_equipment como fuente de verdad
19e8829  fix(bk-04): cerrar grietas QA-1/QA-2/QA-3
e50b924  docs(qa): QA adversarial de BK-04 -- 2 grietas halladas
1bb24a3  fix(bk-04): prevenir areas sin agente (cobertura) + flota por defecto valida
0fa64e3  feat(ui): exponer truck_interval en configurador + bajar default a 90
bb53c8e  docs(handoff): reflejar push+merge hechos; validar KPIs outbound G15/G16
ba55f27  chore(limpieza): sanear indice FUSE, borrar junk y actualizar docs desfasados
...      (historico anterior ya en main; ver git log para detalle)
```

---

## 4. LO QUE SE HIZO (HISTORIAL POR SESION)

### Sesion 2026-07-04 — MEJ-1: red de seguridad automatizada (rama feature/mej-1-red-seguridad)

Revision general de docs (capa de congestion documentada como VIVA y ACTIVA;
HEADs corregidos) + 3 mejoras aprobadas por el Director (MEJ-1/2/3, ver BACKLOG)
+ ejecucion completa de MEJ-1 (plan: docs/PLAN_MEJORA_1_RED_SEGURIDAD.md):

- **F1**: `tests/` legacy completo archivado en `_legacy/tests_gui/` (git mv).
- **F2**: pytest instalado; `pytest.ini` (excluye `_legacy/`, `basura/`, etc.;
  marker `gate` deseleccionado por default); `tests/conftest.py` con fixtures
  (FakeEnv/FakeWO/FakeOperator/make_dispatcher, sin SimPy real).
- **F3**: 59 unit tests en `tests/unit/`: prioridad C2 (PR), olas C3 (OL),
  estrategias+router H-5+radio blando H-6 (ES), allocation (AL), division de
  cantidades en warehouse (WH, con el bug de WOs sobredimensionadas documentado
  como skip), validacion web de config BK-04/QA (CF), nivel de servicio INIT-5 (SL).
- **F4**: `tests/baseline.json` (sha completo `a4ae8d4e9f7dd444eb217aa60ac874cb
  b5b062a3e8ccfaaa908cf9f7d1e86c6e`, 5.379.372 bytes, seed 42, Python 3.13.6) +
  `scripts/regression_gate.py` (corre la sim canonica, compara SHA, PASS/FAIL,
  `--update-baseline --yes` para cambios intencionales, limpia su corrida) +
  smoke `tests/test_gate_smoke.py` (marker gate) + `make test`/`make gate` y
  `run test`/`run gate`.
- **F5**: CI `.github/workflows/tests.yml` (ubuntu, Python 3.13, SDL dummy):
  pytest + migracion Excel->SQLite + gate en cada push/PR. **VALIDADA EN VERDE**
  (run `9f57bea` conclusion=success) tras resolver dos fallos reales:
  1. `warehouse.db` no se versiona (Ley 7) -> sin ella el motor cae al fallback
     Excel y el SHA difiere. Fix: la CI corre `run_migration.py` antes del gate.
     Bonus verificado: una BD recien migrada reproduce el baseline byte-identico
     (NO hay deriva entre la BD local y el Excel canonico).
  2. El `.jsonl` se escribe en modo texto: CRLF (Windows) vs LF (Linux), delta
     11.880 bytes = numero exacto de lineas. Fix: el gate hashea con EOL
     normalizado (CRLF->LF). El SHA normalizado de Windows coincidio EXACTO con
     el de ubuntu (`4a208831…`), probando determinismo multiplataforma incluso
     entre Python 3.13.6 y 3.13.14. Baseline regenerado (equivale al historico
     `a4ae8d4e…` con CRLF). El motor NO se toco.
- **Prueba de fuego**: sabotaje `max_wos_por_tour` 20->19 -> suite ROJA
  (`assert 19 == 20`) -> revertido. El primer intento NO fallo y destapo un test
  debil (fixture pasaba el valor explicito): se agrego ES-01b (defaults con
  config vacio). `git diff src/` vacio al cierre: motor intacto.
- Verificacion previa del baseline: corrida real reproduce el SHA historico en
  ~15-27 s (2 corridas del gate + 1 manual, 3/3 PASS).

### Sesion 2026-07-04 (cont.) — MEJ-3: esquema unico de config (rama feature/mej-3-config-schema)

- **`src/core/config_schema.py`** (pydantic): fuente de verdad de TODAS las
  claves de config.json, cada una anotada con su lector real. Validacion-only
  (no muta): typos -> WARNING con nombre, tipos invalidos -> ERROR.
- **Integracion**: motor (`core/config_manager`) loguea `[CONFIG][SCHEMA][...]`
  al cargar (no bloquea, byte-identico); web (`validate_config`) BLOQUEA el
  guardado ante tipos invalidos y avisa claves desconocidas/legacy en el log.
- **Purga** (config.json + defaults core/web + app.js serialize + index.html):
  10 claves top-level muertas + 9 subclaves F3 de congestion. Se eliminaron DOS
  CONTROLES DE UI SIN EFECTO: "Capacidad del Carro" y "Escala del Mapa" (el
  motor nunca leyo `capacidad_carro` ni `map_scale`). Conservadas:
  `num_operarios_terrestres`/`num_montacargas` (fallback vivo), `staggered_start`
  + `spawn_offset` (spawn escalonado VIVO), `num_operarios_total` (REQUIRED_KEYS).
- **El gate atrapo la purga** (FAIL esperado): el `.jsonl` incrusta el config en
  la metadata SIMULATION_START. Evidencia de neutralidad: sha de los 11.879
  eventos sin la linea 1 identico (`98cc021b…`) antes/despues. Baseline
  regenerado: `662ed5e3…` (5.367.009 bytes).
- Suite 67 passed (SC-01..09 nuevos) + gate PASS x2.

### Sesion 2026-07-04 (cont. 2) — MEJ-4: anti-colisiones completado (rama feature/mej-4-anticolisiones)

Ver `docs/PLAN_MEJORA_4_ANTICOLISIONES.md` (analisis §1-2, resultados §4). Resumen:
- **Cableado del dwell** (la pieza que faltaba): picking (Ground y Forklift con
  lift), descarga granular, y **destino-con-permanencia** — el dwell del destino
  se reserva AL PLANIFICAR el tramo (`plan_and_reserve(goal_dwell=...)`), no al
  llegar, para que los demas lo vean antes de comprometer sus planes.
- **Planner reescrito estilo SIPP** (`spacetime_planner.py`): `earliest_free`
  en la tabla, movimientos con salida retrasada (la espera queda implicita en
  el delta y RESERVADA), y dominancia por (celda, intervalo seguro) — sin esto
  los dwells largos del staging reventaban max_expansions (17 planes fallidos
  en la iteracion intermedia). Resultado: 0 fallos y coste 0.7 ms/plan (mejor
  que los 2.4 ms originales).
- **Fallback visible**: sin plan -> reserva best-effort de la ruta estatica +
  WARN (antes el agente degradado era invisible).
- **clearance 0.05** en el canonico (mata las carreras de relevo instantaneas)
  y **parking idle disperso** post-descarga (reusa `_spawn_lane`).
- **Resultados**: co-ocupaciones 28 -> 9 (todas pares instantaneos; max 2 por
  celda, antes 4), hotspot staging 22 -> 2, invariante de tabla 0, esperas
  planificadas 0.095/plan. Tests: +6 TW (suite 73 passed). Baseline nuevo
  `c6f129ef…` via --update-baseline.
- **HALLAZGO ABIERTO**: makespan 2011 -> 3121 s (+55%). Es la cola REAL del
  staging unico (antes 4 agentes descargaban superpuestos = fisica imposible
  que inflaba el throughput). Decision del Director pendiente: reequilibrar
  el escenario (repartir staging / discharge_time) o aceptar los KPIs reales.

### Sesion 2026-06-29 — INIT-4 completo (commits 91dd6c0..edba925)

Prioridad/SLA/olas + tiempos de pick realistas, en 3 fases, cada una opt-in con
gate de no-regresion byte-identico (REG-1, `WAREHOUSE_SEED=42` → SHA `a4ae8d4e…`).
Plan y pruebas en `docs/PLAN_INIT4.md`.

**C1 — Tiempos de pick realistas** (`91dd6c0`)
`BaseOperator._compute_pick_time()` escala el tiempo por cantidad/volumen
(`base + por_unidad*cant + por_volumen*vol`, cota `minimo`). Bloque OPCIONAL
`config["tiempos"]["pick_time_model"]`; neutro → tiempo historico. E2E:
tiempo_picking varia 8..24 segun cantidad. PICK-1..6 pasan.

**C2 — Prioridad de pedido / SLA (Opcion C)** (`c27dacb`, base en `0c1682c`)
`WorkOrder` gana priority/due_time (leidos del archivo de ordenes, coercion
defensiva). Flag `priority_dispatch_enabled` (default off). Opcion C "fuerte limpia":
mientras haya urgentes, el tour se arma solo con urgentes (no se diluyen), sin
cruzar de zona (`_pool_para_barrido`). E2E: urgentes t_fin 18.8 vs 71.2 (~4x);
ranking medio 5.6 vs 20.8. Costo: llenado -33%, throughput intacto. PRIO-1..7 pasan.

**C3 — Olas (waves)** (`fd0a41d`)
Release diferido por ola: `WorkOrder.wave_id`; bloque `config["waves"]`
(enabled + release_times). `_wo_elegible_por_ola` en las 4 estrategias.
`simulacion_ha_terminado()` sin cambio (las WOs de olas futuras ya cuentan en el
total). E2E: WAVE-1 (ola2 respeta release 100), WAVE-TERM (release 400 > fin
natural: no cuelga, termina t=520.6). WAVE unit + INT-1 (ola manda sobre prioridad) pasan.

**Cierre** (`edba925`): BACKLOG/HANDOFF/CLAUDE al dia; INT-1 ok.

### Sesion 2026-06-27 (commits f3a3ec5..b990964)

**Logging refactor — Punto 1** (`b990964`)
~186 prints convertidos a logging por nivel en hot-path:
- `event_generator.py` (58 prints → INFO), `dispatcher.py` (86 → DEBUG/INFO/WARN/ERROR),
  `operators.py` (42 → DEBUG/INFO/WARN).
Salida en produccion: de miles de lineas a ~800 milestones.
La linea critica para Watch Replay (`.jsonl` generado) queda como INFO.

**Gate WAREHOUSE_SEED** (`413888c`)
Variable de entorno `WAREHOUSE_SEED=42` fija `random.seed()` antes de la sim.
Sin la variable: comportamiento estocastico de produccion (sin cambio).
Gate byte-identico: SHA256 = `a4ae8d4e9f7dd444...` (5,379,372 bytes) en dos corridas.

**Template Method — Punto 2** (`41ddc22`)
`BaseOperator.agent_process()` extrae el ciclo pull-based completo (PASO 1-6).
`_do_picking_at()` es hook abstracto; `GroundOperator` y `Forklift` lo implementan.
Resultado: -296 lineas en operators.py (1772→1476, -16.7%).
Gate byte-identico post-refactor: SHA256 = idem baseline.

**E6/E7 eliminados — Punto 3** (`f3a3ec5`)
Botones stub "Generar Plantilla TMX" / "Poblar SKUs Aleatorios" quitados de
`index.html` y `app.js`. Tarjeta "Acciones de Datos" queda con un solo boton real.
BK-05 cerrado en BACKLOG.md.

---

### Sesiones previas (antes de 2026-06-27)

**D-13..D-16** (`0e6d3dd`, `902877a`)
Design tokens compartidos configurador/viewer, stepper numerado de tabs,
event markers en scrubber de timeline, fix accesibilidad no-color (WCAG AA).

**anti-cache estaticos** (`23b374b`)
Query string `?v=<timestamp>` en referencias CSS/JS para evitar reload forzado.

**INIT-5 — nivel de servicio** (`8cc7f8d`)
Backorders/fill-rate expuestos en visor web (KPI "Servicio"), API
(`/api/snapshot`, `/api/state`, `/api/metrics`) y hoja Excel "Nivel de servicio".
Fuente: `core/replay_utils.build_service_level_summary(almacen)`.
En modo estocastico (sin validacion de stock) muestra N/A.

**BK-04 + QA-1/2/3** (`1bb24a3`, `e50b924`, `e2c6293`, `19e8829`)
- Fix preventivo: flota por defecto asigna work_areas validas a Forklift.
- Mapa explicito `work_area_equipment` en `work_area_calculator.py` como fuente de verdad.
- QA adversarial cerro 3 grietas: motor valida arranque, flota vacia detectada, tipo de equipo validado.
- Outbound termina correctamente cuando no hay mas WOs.

**truck_interval en UI** (`0fa64e3`)
Campo expuesto en configurador; default bajado a 90 seg (antes 300, causaba sim sin trucks visibles).

**Allocation Layer V12.1** (base de la rama)
Asignacion de stock real FCFS antes de crear WorkOrders.
`data_manager.py::get_available_stock()`, `warehouse.py::WorkOrder`
(qty_requested/qty_allocated/is_partial), `order_strategies.py`.
`fulfillment_policy: "ship_partial"` en config.json.

**Fixes de estrategias** (H-5, BK-01, H-6)
- H-5 (`c4c772f`): alias "Ejecucion de Plan" reconocido por el dispatcher.
- BK-01 (`bcdb264`, `76f1e21`): Cercania + radio_cercania + expansion expuestos en UI.
- H-6 (`8a2fe86`): radio blando elimina deadlock de Cercania con radio restrictivo.
- BK-03 (`dd5c729`): greedy nearest-neighbor descartado con evidencia experimental.

**D-03..D-12 + limpieza** (sesiones anteriores)
Sidebar colapsable/iconos, fleet cards, inline validation, KPIs jerarquicos,
colores de seccion, notificaciones. Cuarentena de 40+ archivos basura.

---

## 5. PENDIENTES Y PROXIMOS PASOS

### Backlog activo (ver docs/BACKLOG.md para detalle completo)

| Item | Estado | Esfuerzo estimado |
|------|--------|-------------------|
| MEJ-1 — Red de seguridad (pytest + gate regresion) | HECHO 2026-07-04 (ver seccion 4) | — |
| MEJ-3 — Esquema unico de config (pydantic) + purga claves | HECHO 2026-07-04 (ver seccion 4) | — |
| MEJ-4 — Completar anti-colisiones (dwell + fallback visible) | HECHO 2026-07-04 — HALLAZGO makespan +55% pendiente de decision | — |
| **MEJ-2** — Experiment runner (replicas + A/B estadistico) | APROBADA — SIGUIENTE | 2 sesiones |
| **Makespan +55% post-MEJ-4** — reequilibrar escenario canonico? | PENDIENTE DECISION Director (PLAN_MEJORA_4 §4) | Bajo |
| **BK-02** — FIFO Estricto en UI | EN REPENSAR (diseno pendiente del Director) | ~15 min cuando se decida |
| **`_legacy/web_dashboard/`** (puerto 8001) | PENDIENTE DECISION (Director quiere revisarla) | Depende de decision |
| **INIT-1** — Picking por ubicacion real + reservas en BD | Pendiente | Alto |
| **INIT-3** — Reparar optimizador Optuna | Pendiente | Bajo-Medio |
| **INIT-4 → KPI de SLA vencido** | Pendiente (unico punto diferido de INIT-4) | Bajo |
| **WOs sobredimensionadas** | Pendiente (falsifica KPIs) | Bajo (fix defensivo) |

INIT-4 (C1 tiempos, C2 prioridad Opcion C, C3 olas) esta HECHO (ver seccion 4 y
docs/PLAN_INIT4.md); solo queda diferido el KPI de SLA vencido en el reporte.
Ver `docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md` para descripcion de INIT-1/3.

**BK-02 — FIFO Estricto en UI** (EN REPENSAR)
El motor lo implementa correctamente. No se expone porque el Director quiere redefinir
primero que deberia hacer FIFO operacionalmente.

**web_dashboard/** (PENDIENTE DECISION)
Puerto 8001. Ruta de replay rota. Parece huerfana; el Director quiere revisarla
antes de decidir si se conserva, se repara o se elimina.

**INIT-1 — Picking por ubicacion real**
Hoy el allocation layer asigna la WO a una ubicacion de picking elegida al azar
dentro del area, aunque ese SKU no este ahi. La tabla `inventory(location_id, ...)`
en warehouse.db ya tiene la informacion; falta usarla en `order_strategies.py`.

**INIT-3 — Optimizador Optuna**
Los nombres de estrategia y parametros del optimizador estan desalineados del motor
real. Resultado: el optimizador puede estar probando configuraciones que el motor ignora.

**INIT-4 — Prioridad / SLA / olas + tiempos de pick** — HECHO 2026-06-29
Commits 91dd6c0 (C1 tiempos escalables), c27dacb (C2 prioridad Opcion C),
fd0a41d (C3 olas). Todo opt-in con gate byte-identico. Ver docs/PLAN_INIT4.md.
Diferido: KPI de SLA vencido en el reporte (no bloqueante).

**WOs sobredimensionadas**
En `warehouse.py::_validar_y_ajustar_cantidad`: si `sku.volumen > max_capacity`,
`unidades_por_viaje = 0` → bucle infinito (o la WO se marca 'staged' con qty=0).
Fix: forzar minimo 1 unidad por viaje; marcar WOs imposibles como 'failed' (no 'staged').

### Issues conocidos (no criticos)
- `warehouse.db-shm` / `warehouse.db-wal`: archivos WAL de SQLite, aparecen como
  untracked pero ya estan en .gitignore.

---

## 6. DOCUMENTACION VIGENTE

| Archivo | Estado | Descripcion |
|---|---|---|
| `README.md` (raiz) | ACTUALIZADO 2026-06-29 | Vision, arquitectura, instalacion y uso; frontend web |
| `CLAUDE.md` | ACTUALIZADO 2026-06-29 | Identidad, arquitectura, flags opt-in, leyes, estado |
| `AUDITORIA.md` | Vigente (mayo 2026) | Diagnostico estructural completo del repo |
| `docs/HANDOFF.md` | ACTUALIZADO 2026-06-29 | Este archivo — estado operativo para nueva sesion |
| `docs/PLAN_INIT4.md` | Vigente (2026-06-29) | Plan + pruebas + checklist de INIT-4 (C1/C2/C3) |
| `docs/PLAN_MEJORA_1_RED_SEGURIDAD.md` | Vigente (2026-07-04) | Plan aprobado de MEJ-1: suite pytest + gate de regresion |
| `docs/BACKLOG.md` | ACTUALIZADO 2026-06-29 | INIT-4 + INIT-5 + BK cerrados; INIT-1/3/KPI-SLA/WOs pendientes |
| `docs/VALIDACION_UI_WEB.md` | ACTUALIZADO 2026-06-27 | 60 controles; E6/E7 eliminados, D1 resuelto |
| `docs/PROPUESTA_MEJORA_DISENO_UI.md` | ACTUALIZADO 2026-06-27 | D-01..D-16 implementadas |
| `docs/PRUEBAS_E2E_SISTEMA.md` | Referencia (2026-06-13) | Catalogo de 53 casos E2E |
| `docs/RESULTADOS_PRUEBAS_E2E.md` | Referencia (2026-06-13) | Resultados: 40 PASS, 0 FAIL, 3 WARN |
| `docs/COMO_FUNCIONA_EL_PROGRAMA.md` | Referencia | Descripcion operativa del sistema |
| `docs/VISION_PRODUCTO.md` | Referencia | Vision y roadmap de alto nivel |
| `docs/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md` | Referencia | Tileset y estructura de layouts TMX |
| `docs/INSTRUCCIONES_PROYECTO_COWORK.md` | Referencia | Metodologia atemporal del proyecto |
| `docs/antiguos/` | ARCHIVO HISTORICO | Planes/bitacoras de iniciativas completadas |

---

## 7. FLUJO DE TRABAJO GIT (Windows nativo)

Cerebellum corre en **Windows nativo** con acceso directo a git y a la red
(el viejo protocolo anti-FUSE del sandbox Linux ya NO aplica). Flujo por hito:
```bash
git add <archivos>
git commit -m "..."                              # co-autoria al pie
git push origin feature/allocation-layer-v12.1   # push de la rama
git push origin HEAD:refs/heads/main             # fast-forward de main server-side
git fetch origin main:main                       # sincronizar main local
git rev-list --count main..feature/...           # verificar divergencia 0
```
`main` se sincroniza por **fast-forward server-side** (sin checkout de main).
Verificar siempre divergencia 0/0 tras el push.

> Nota de entorno: `git` puede avisar "LF will be replaced by CRLF"; es esperado
> en Windows y no afecta el contenido. OJO: el `.jsonl` se escribe en modo texto,
> asi que Windows produce CRLF y Linux LF con contenido logico IDENTICO (delta =
> numero de lineas). Por eso el gate (MEJ-1) normaliza EOL antes de hashear:
> SHA256 normalizado `4a208831…` (5.367.492 bytes) identico en Windows y CI
> ubuntu (verificado 2026-07-04). El SHA historico `a4ae8d4e…` (5.379.372 bytes)
> era el MISMO archivo con CRLF sin normalizar.

---

## 8. CONFIG.JSON — DEFAULTS SEGUROS (estado post-experimentos)

```json
{
  "dispatch_strategy": "Ejecucion de Plan",
  "radio_cercania": 100,
  "radio_expansion_paso": 50,
  "radio_max_expansiones": 5,
  "cercania_tour_mode": "cost",
  "total_ordenes": 300,
  "num_operarios_terrestres": 2,
  "num_montacargas": 2
}
```
`cercania_tour_mode: "cost"` es el default seguro post-BK-03. El valor `"greedy_nn"`
existe como opcion pero no se recomienda (ver BK-03 descartado).

### Flags OPT-IN de INIT-4 (AUSENTES del config canonico a proposito)
El motor los lee con `.get()` + defaults neutros. Por eso el canonico NO los trae:
mantiene el `.jsonl` byte-identico al baseline. Se activan en configs de prueba/UI.
```jsonc
// Tiempo de pick escalable (C1). Neutro = tiempo historico fijo.
"tiempos": { "pick_time_model": { "base": null, "por_unidad": 0.0,
                                   "por_volumen": 0.0, "minimo": 0.0 } },
// Prioridad de pedido en el despacho (C2, Opcion C fuerte "limpia"). Default off.
"priority_dispatch_enabled": false,   // priority/due_time vienen del archivo de ordenes
// Olas por release diferido (C3). Default off -> todo elegible desde t=0.
"waves": { "enabled": false, "release_times": { "1": 0, "2": 300 } }
```
- `WAREHOUSE_SEED` (variable de entorno, NO config): fija la semilla para corridas
  deterministas/reproducibles. Gate byte-identico: SHA256 `a4ae8d4e…`, 5.379.372 bytes.
- Validacion de estos bloques en `web_prototype/config_manager.py` (release_times
  acotado a <= 1.000.000 para evitar hangs). Detalle en `docs/PLAN_INIT4.md`.

### Bloque `congestion` (Iniciativa 2) — PRESENTE y ACTIVO en el canonico
A diferencia de los flags INIT-4 (ausentes/neutros), el bloque `congestion` SI
esta en el config.json canonico y ACTIVO desde antes del baseline:
`enabled: true`, `mode: "timewindow"`, `timewindow.shadow: false` => ruteo por
reserva espacio-temporal EJECUTADO (Fase 2; fallback a ruta estatica si no hay
plan). Modulos: congestion_manager.py, reservation_table.py, spacetime_planner.py.
El gate byte-identico (`a4ae8d4e…`) incluye esta capa: NO desactivarla si se
quiere reproducir el baseline. Historia: docs/antiguos/PLAN_INICIATIVA_2_OPCION_C.md.
