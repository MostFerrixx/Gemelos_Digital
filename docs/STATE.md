# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-09

## Git

- `main` = `ead81f7` (merge F3) + INIT-7 F4 (rama `feature/init7-inbound-f0`,
  a mergear y pushear al cierre). Push directo a main autorizado.
- Baseline byte-identico vigente: `sha256=930a1e6f879420a8...`, 4.920.393
  bytes, seed 42, Python 3.13.6 (`tests/baseline.json`). REAJUSTADO en F4:
  agrego SOLO `inbound_summary:{available:false}` a la metadata (linea 1);
  los EVENTOS (linea 2+) quedan byte-identicos al baseline previo (verificado
  sha `6e57752e` con y sin F4). Mismo caso que MEJ-BOTTLENECK. F0-F3 no lo
  habian tocado. Determinismo con inbound ON tambien verificado.
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock (rompe el determinismo del gate).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 157 passed, 1 deselected (~8s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 930a1e6f)
```

## INIT-7 INBOUND (recepcion y almacenamiento) — ALCANCE v1 COMPLETO

Plan completo + 4 decisiones del Director (2026-07-08):
**`docs/PLAN_INIT7_INBOUND.md`** (con decisiones tecnicas por fase). Alcance
v1 aprobado = F0-F4, TODO HECHO. Solo queda F5 (segunda etapa).

- **F0 (2026-07-08):** hoja `InboundDocks` + tabla `inbound_docks` + loaders
  data_manager + bloque `inbound` en config_schema + ASN ejemplo. IN-01..09.
- **F1 (2026-07-08):** `inbound.py` (`InboundProcess`, `InboundDock`,
  `InboundPallet`, `load_asn_trucks`); llegadas ASN/estocastico; eventos
  inbound_* + marcador verde en el visor. IN-10..16.
- **F2 (2026-07-09):** putaway completo — WOs pre-generadas en t=0, elegibles
  al aterrizar, cola propia en dispatcher (picks primero),
  `_execute_putaway_tour`, stock real via `data_manager.add_stock`. IN-20..25.
- **F3 (2026-07-09):** slotting conmutable — `resolve_slotting`
  (`fija_por_sku` / `cercana_al_muelle` / `abc_rotacion`) resuelto al
  aterrizar; UI tab "Inbound" (paso 6). IN-30..35.
- **F4 (2026-07-09):** KPIs — `build_inbound_summary()` (dock-to-stock,
  distancia de putaway, contencion de muelles) -> metadata/API/panel
  "Recepcion (Inbound)" del visor/hoja Excel "Inbound"; `avg_dock_to_stock`
  y `avg_putaway_distance` como KPIs del A/B (OPTIONAL_KPI_KEYS). El KPI
  discrimina (dist avg cercana 29.4 < abc 30.8 < fija 31.4). IN-40..43.

**Como probar inbound:** activar el tab "Inbound" del configurador (o poner un
bloque `inbound.enabled:true` en un config) con `slotting_strategy` a elegir;
comparar 2 estrategias con la pestaña "Experimentos A/B".

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- INIT-7 inbound COMPLETO v1 (opt-in, ausente del canonico): recepcion +
  putaway + slotting conmutable + KPIs. Modulo `inbound.py`, integrado en
  warehouse/dispatcher/operators/event_generator/replay_utils/exporter_v2.
- Congestion timewindow: activa en `config.json` canonico (no opt-in).
- INIT-4 (prioridad/SLA/olas, pick times), INIT-6 (destino->staging map + UI),
  INIT-4b (KPI SLA), MEJ-BOTTLENECK (panel cuellos de botella), MEJ-SLA-OPT:
  todos opt-in o aditivos, detalle en CHANGELOG 2026-07-05/06.
- MEJ-2 experiment runner (CLI `run`/`compare`) + MEJ-EXP-WEB (tab
  "Experimentos A/B", progreso via --progress-json atomico). Ahora compara
  tambien `avg_dock_to_stock` / `avg_putaway_distance` (F4).
- Optimizador Optuna CLI+web; warm-start en serie antes de paralelizar.
- Arquitectura web: `server.py` (89 lineas) + `app_state.py` +
  `routers/{configurator,replay,runners,system}.py`. Tab "Inbound" = paso 6,
  Optimizacion 7, Experimentos A/B 8.
- Disco: temporales del proyecto en `temp_web/` (disco D, gitignoreado) con
  `purge_stale_temp(24h)`. VM de Claude en D:\ClaudeData via junction.
- Patron de guia UI en 3 niveles (.tab-intro / .description-text / .help-text).

## Decisiones del Director pendientes

1. **INIT-7 decision 4 (para arrancar F5):** stock recibido disponible para
   picking del mismo dia (cross-docking implicito) vs turnos separados.
2. **BK-02 — FIFO Estricto en UI:** redefinir que deberia hacer FIFO antes de
   exponerlo.
3. **INIT-6 Opcion C (clustering geografico):** solo si habra datos reales de
   geolocalizacion. No bloqueante.
4. **`outbound_staging_distribution` real** en el canonico: tuning de negocio
   (hoy 100% zona 1); cambiarlo rompe baseline intencionalmente.

## Siguiente prioridad

INIT-7 v1 (F0-F4) cerrado. Opciones: **F5 (flujo mixto)** — requiere la
decision 4 del Director; o retomar backlog (INIT-3 v3 capacidades por agente
en el optimizador, o alguna decision pendiente). A definir por el Director.

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya
  en `.gitignore`.
