# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-10

## Git

- `main` = `c967f79` (merge F4) + INIT-7 F5 (rama `feature/init7-inbound-f0`,
  a mergear y pushear al cierre). Push directo a main autorizado.
- Baseline byte-identico vigente: `sha256=930a1e6f879420a8...`, 4.920.393
  bytes, seed 42, Python 3.13.6 (`tests/baseline.json`; reajustado en F4 por
  metadata nueva, eventos intactos). F5 NO lo toco (GATE PASS sin update:
  las claves nuevas del service_level solo aparecen si hubo rescates
  cross-dock, e inbound sigue ausente del canonico).
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock (rompe el determinismo del gate).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 170 passed, 1 deselected (~8s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 930a1e6f)
```

## INIT-7 INBOUND — COMPLETA (F0-F5, 2026-07-08 a 2026-07-10)

Plan, 4 decisiones del Director y decisiones tecnicas por fase:
**`docs/PLAN_INIT7_INBOUND.md`**. Resumen: recepcion de camiones (ASN
determinista / estocastico pre-muestreado) -> putaway (WOs por evento, cola
propia, 1 pallet/viaje) -> stock real -> slotting conmutable (fija/cercana/
abc) -> KPIs (dock-to-stock, distancia, contencion) -> flujo mixto (F5):

- **F5a `putaway_priority`** (`picks_first` default / `putaway_first`):
  quien manda en la flota compartida. KPI `avg_putaway_wait`. Smoke: espera
  1305s vs 88s segun prioridad.
- **F5b `cross_dock_enabled`** (solo modo deterministic): backorders de la
  allocation t=0 se rescatan con el stock del dia (picks dinamicos WO-XD
  desde la ubicacion recien abastecida, heredan prioridad/due_time/destino).
  KPI `fill_rate_effective_pct`. Demo estable:
  `examples/config_cross_dock_demo.json` (README en `examples/`).
- Todo opt-in; canonico intacto. Tests IN-01..56 + auditoria.
- **Auditoria 2026-07-10 (3 fixes):** total de WOs se refresca en cada alta
  (visor ya no muestra >100% con inbound; verificado 55/55); A/B parea por
  semilla antes de filtrar None (`_collect_paired_values`); demo movida a
  `examples/` (temp_web tiene purga 24h).
- **MEJ-ROBUSTEZ-AGENTES HECHO (2026-07-10):** (A) tours envueltos en
  try/except (`_execute_pick_tour` extraido verbatim + `_abort_tour` +
  `dispatcher.notificar_wo_fallida`: una excepcion ya NO revienta la corrida
  entera, marca las WOs failed y la corrida completa) + (D) watchdog de
  no-progreso en el engine (`compute_stall_limit`, diagnostico accionable,
  volcado parcial: los deadlocks dinamicos ya no cuelgan para siempre).
  La investigacion corrigio el diagnostico original: la excepcion era CRASH
  TOTAL (no cuelgue silencioso) y el caso estatico ya lo cubria QA-3.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- INIT-7 inbound COMPLETO (opt-in, ausente del canonico): ver arriba.
- Congestion timewindow: activa en `config.json` canonico (no opt-in).
- INIT-4 (prioridad/SLA/olas, pick times), INIT-6 (destino->staging map + UI),
  INIT-4b (KPI SLA), MEJ-BOTTLENECK, MEJ-SLA-OPT: opt-in o aditivos.
- MEJ-2 experiment runner + MEJ-EXP-WEB (tab A/B). KPIs opcionales del A/B:
  fill_rate_pct, avg_dock_to_stock, avg_putaway_distance, avg_putaway_wait,
  fill_rate_effective_pct.
- Optimizador Optuna CLI+web; warm-start en serie antes de paralelizar.
- Web: `server.py` + `app_state.py` + `routers/`. Tab Inbound = paso 6
  (con prioridad de flota y cross-dock), Optimizacion 7, A/B 8.
- Disco: temporales en `temp_web/` (D, gitignoreado, purge 24h). VM de
  Claude en D:\ClaudeData via junction.
- Patron de guia UI en 3 niveles (.tab-intro/.description-text/.help-text).

## Decisiones del Director pendientes

1. **BK-02 — FIFO Estricto en UI:** redefinir que deberia hacer FIFO antes
   de exponerlo.
2. **INIT-6 Opcion C (clustering geografico):** solo si habra datos reales
   de geolocalizacion. No bloqueante.
3. **`outbound_staging_distribution` real** en el canonico: tuning de
   negocio (hoy 100% zona 1); cambiarlo rompe baseline intencionalmente.

## Siguiente prioridad (sin decidir aun)

INIT-7 cerrada por completo. Candidatos: INIT-3 v3 (capacidades por agente
en el optimizador, listo para tomar), alguna decision pendiente de arriba, o
una iniciativa nueva del Director.

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya
  en `.gitignore`.
