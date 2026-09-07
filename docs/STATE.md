# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-07

## Git

- `main` = **BK-06 mergeada** (fast-forward desde `fix/bk06-capacidad-area`,
  autorizado por el Director). Rama de trabajo ya integrada.
- Baseline byte-identico vigente: **`sha256=95b59db0...`, 15.925.714 bytes**,
  seed 42 (`tests/baseline.json`). Regenerado el 2026-09-07 por el cambio
  intencional de BK-06. Anterior: `2233b3c6` (10.039.862 bytes).
- Ramas muertas de 2025 borradas (2026-07-25), recuperables por tag:
  `archive/feat-realtime-workorder-dashboard`, `archive/fix-configurator-tool`.
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock (rompe el determinismo del gate).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 207 passed, 1 deselected (~9s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 95b59db0)
```

## Ultima iniciativa cerrada: BK-06 (2026-09-07)

Bug de motor: la capacidad de dimensionado de WorkOrders por area quedaba
ciega con el canonico (`agent_types: []`) y dimensionaba TODAS las areas a 150,
aunque las atendieran montacargas de 1000. Causa raiz: `work_area_equipment`
era la fuente de verdad de que equipo sirve cada area, pero el hot-path de
simulacion no la consultaba. Detalle completo, RCA y resultados en
**`docs/PLAN_BK06_CAPACIDAD_AREA.md`** (seccion 9) y en el CHANGELOG.

Comportamiento de referencia nuevo: **626 WOs / 8783 s / 0 errores de
dispatcher**, moviendo el MISMO volumen (21.150) y las mismas 300 ordenes que
las 666 WOs anteriores (son 40 viajes menos, no menos trabajo). El makespan
sube 18,1% respecto al viejo 7440 s, que no era legitimo: se lograba en parte
con asignaciones fisicamente imposibles. Trade-off aceptado por el Director
(principio rector #1, `CLAUDE.md` 1.5).

## Decisiones del Director pendientes

1. **BK-08 (ALTA) — confirmar `work_area_equipment` con el almacen real.** Todo
   BK-06 asume que Area_High/Area_Special son 100% montacargas. Es un SUPUESTO
   no verificado del que dependen los numeros. Si es falso se corrige en
   config (tab Flota), sin tocar codigo.
2. **BK-09 — la flota 2+2 esta sub-dimensionada.** Medido: 2+3 -> 6042 s,
   2+4 -> 4844 s (optimo), 2+5 empeora por congestion. Decision de negocio.
   Recomendacion de Cerebellum: NO tocar el canonico -- debe reflejar el
   almacen real del cliente y mostrarle el costo, no maquillar el KPI.
3. **BK-07 — areas mixtas** (varios tipos de equipo por area). Hoy el mapa
   admite uno solo. Depende de la respuesta a BK-08.
4. **BK-05 — guard de flota vacia en la UI.** DESBLOQUEADO por BK-06 (la
   opcion (b) ya es un no-op de comportamiento). Elegir entre (a), (b) o (c).
5. **BK-02 — FIFO Estricto en UI:** redefinir que deberia hacer antes de
   exponerlo.
6. **`outbound_staging_distribution` real** en el canonico (hoy 100% zona 1).
7. **INIT-6 Opcion C (clustering geografico):** solo con datos reales de
   geolocalizacion. No bloqueante.

## Siguiente prioridad (sin decidir aun)

Candidatos: **INIT-3 v3** (capacidades por agente en el optimizador -- quedo
MUCHO mas barato tras BK-06 y encontraria BK-09 solo), BK-05 (~1 h la opcion a),
las decisiones de arriba, o iniciativa nueva del Director.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow: activa en el canonico (no opt-in).
- **BK-06:** `work_area_equipment` gobierna la compatibilidad agente-area en el
  motor; la capacidad de dimensionado por area se deriva de la flota real
  (minimo como red de seguridad); flota resuelta en `src/core/fleet.py` y
  areas en `src/core/work_areas.py` (fuentes unicas). Bloque nuevo opt-in
  `fleet_defaults` (capacidades configurables, antes hardcodeadas).
- INIT-8 nucleo (catalogo fisico + tiempos por clase/peso + mezcla por clase):
  ACTIVO. F3/F4 de INIT-8 e inbound completo: opt-in via config/UI.
- INIT-4 (prioridad/SLA/olas), INIT-6, INIT-4b (KPI SLA), MEJ-BOTTLENECK,
  MEJ-SLA-OPT: opt-in o aditivos.
- MEJ-2 experiment runner + tab A/B. Optimizador Optuna CLI+web.
- Web: `server.py` + `app_state.py` + `routers/`. Tabs: Carga 1, Estrategias 2,
  Flota 3, Layout 4, Outbound Staging 5, Inbound 6, Optimizacion 7,
  Experimentos A/B 8.
- Robustez: excepcion a mitad de tour degrada por WO; watchdog de no-progreso.
- Disco: temporales en `temp_web/` (D, gitignoreado, purge 24h).

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya en
  `.gitignore`.
- BK-05 (UX): guardar el canonico desde la UI lo bloquea el guard de flota
  vacia. Ver BACKLOG.
- Deuda menor: la copia de `_expected_equipment_for_area` en
  `web_prototype/config_manager.py` y en `fleet-manager.js` sigue duplicada. El
  motor ya usa la fuente unica `src/core/work_areas.py`; consolidar la web
  queda pendiente.
