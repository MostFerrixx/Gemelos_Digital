# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-08

## Git

- `main` = `713a9b6` + INIT-7 F0 (rama `feature/init7-inbound-f0`, a mergear
  y pushear al cierre). Push directo a main autorizado por el Director.
- Baseline byte-identico vigente: `sha256=71fc9904141ddc73...`, 4.920.352
  bytes, seed 42, Python 3.13.6 (`tests/baseline.json`). INIT-7 F0 NO lo
  toco (GATE PASS sin update: el motor todavia no lee nada del inbound).
- REGLA pinneada por test BN-05: la metadata del .jsonl NO puede contener
  valores wall-clock (rompe el determinismo del gate).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 134 passed, 1 deselected (~14s)
python scripts/regression_gate.py  # GATE PASS esperado
```

## INICIATIVA ACTIVA: INIT-7 INBOUND (recepcion y almacenamiento)

Plan completo + 4 decisiones del Director (2026-07-08):
**`docs/PLAN_INIT7_INBOUND.md`**. Detalle de fases pendientes en
`docs/BACKLOG.md`.

- **F0 HECHO (2026-07-08):** hoja `InboundDocks` en Excel canonico (muelles
  1=(3,1), 2=(15,1), 3=(27,1)), tabla `inbound_docks` (propia, aditiva),
  loaders DB+Excel en data_manager (`get_inbound_dock_locations()`, sin
  defaults), bloque `inbound` en config_schema (opt-in, NO esta en el
  canonico), ASN ejemplo `layouts/Inbound Test.json`, tests IN-01..09.
- **Proxima fase: F1 (llegadas)** — `InboundProcess` espejo de
  `OutboundProcess`, ASN deterministico + modo estocastico, eventos al
  .jsonl. Gate debe seguir PASS sin update.
- Palancas confirmadas por investigacion: olas INIT-4 para release=arrival
  (sin inyeccion dinamica de WOs); `warehouse.db` ya migrada con los 3
  muelles; tileset TMX ya traia tipo `inbound` (gid 6, walkable);
  filas y=0..2 del WH1 caminables.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow: activa en `config.json` canonico (no opt-in).
- INIT-4 (prioridad/SLA/olas, pick times), INIT-6 (destino->staging map + UI),
  INIT-4b (KPI SLA), MEJ-BOTTLENECK (panel cuellos de botella), MEJ-SLA-OPT
  (score del optimizador penaliza orders_late, $50 default): todos opt-in o
  aditivos, detalle en CHANGELOG 2026-07-05/06.
- MEJ-2 experiment runner (CLI `run`/`compare`) + MEJ-EXP-WEB (tab
  "Experimentos A/B" del configurador, progreso via --progress-json atomico).
- Optimizador Optuna CLI+web; warm-start SIEMPRE en serie antes de
  paralelizar; espacio: operarios/montacargas/estrategia/max_wos/radio.
- Arquitectura web: `server.py` (89 lineas) + `app_state.py` +
  `routers/{configurator,replay,runners,system}.py`.
- Disco: temporales del proyecto en `temp_web/` (disco D, gitignoreado) con
  `purge_stale_temp(24h)`. VM de Claude relocalizada a D:\ClaudeData via
  junction (el Director ejecuto el .bat, confirmado 2026-07-08).
- Patron de guia UI en 3 niveles (.tab-intro / .description-text / .help-text)
  para cualquier control nuevo (aplicar al selector de slotting en F3).

## Decisiones del Director pendientes

1. **INIT-7 decision 4 (al arrancar F5):** stock recibido disponible para
   picking del mismo dia (cross-docking implicito) vs turnos separados.
2. **BK-02 — FIFO Estricto en UI:** redefinir que deberia hacer FIFO
   operacionalmente antes de exponerlo.
3. **INIT-6 Opcion C (clustering geografico):** solo si habra datos reales
   de geolocalizacion. No bloqueante.
4. **`outbound_staging_distribution` real** en el canonico: tuning de negocio
   (hoy 100% zona 1); cambiarlo rompe baseline intencionalmente.

## Siguiente prioridad

INIT-7 F1 (llegadas de camiones inbound), salvo que el Director cambie el
rumbo. F2 (putaway) detras.

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya
  en `.gitignore`.
