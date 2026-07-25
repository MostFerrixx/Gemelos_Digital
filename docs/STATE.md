# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-12

## Git

- `main` = actualizacion documental completa (al cierre), pusheado. Push
  directo a main autorizado por el Director.
- Baseline byte-identico vigente: **`sha256=2233b3c6...`, 10.039.862 bytes**,
  seed 42, Python 3.13.6 (`tests/baseline.json`). Ultimo reajuste:
  normalizacion del canonico a enteros JS-estables (guardar desde la UI es
  un no-op byte-identico). Anteriores: `cbdb3073` (AUD8-2), `8f9f78d5`
  (INIT-8 F2), `930a1e6f` (INIT-7 F4).
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock (rompe el determinismo del gate).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 193 passed, 1 deselected (~10s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 2233b3c6)
```

## Iniciativas cerradas recientemente (detalle en CHANGELOG + planes)

- **INIT-7 INBOUND** (F0-F5, 2026-07-08/10): recepcion de camiones + putaway
  + slotting conmutable + KPIs + flujo mixto (prioridad de flota y
  cross-docking). Opt-in, ausente del canonico. Auditada (3 fixes) +
  MEJ-ROBUSTEZ (try/except por tour + watchdog de no-progreso). Plan y
  decisiones: `docs/antiguos/PLAN_INIT7_INBOUND.md`. Demo cross-dock:
  `examples/config_cross_dock_demo.json`.
- **INIT-8 TIEMPOS REALISTAS** (F1-F4 + auditoria 4/4 + UI, 2026-07-11/12):
  catalogo fisico por SKU (hoja `SkuCatalog`), tiempos por clase/peso
  calibrados ACTIVOS en el canonico (el mundo plano sobreestimaba ~2x),
  velocidad segun carga y variabilidad Log-Normal (opt-in), mezcla de
  pedidos por clase real (AUD8-2), UI completa (cards en tabs Carga y
  Estrategias). Plan con tabla de calibracion y fuentes:
  `docs/antiguos/PLAN_INIT8_TIEMPOS.md`. Resumen operativo en CLAUDE.md §5.
- **Documentacion (2026-07-12):** triage ejecutado — planes completados y 4
  docs obsoletos movidos a `docs/antiguos/` (detalle y criterios en el
  addendum de `docs/META_DOCUMENTACION.md`); README/CLAUDE/STATE al dia.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow: activa en el canonico (no opt-in).
- INIT-8 nucleo (catalogo fisico + tiempos por clase/peso + mezcla por
  clase): ACTIVO en el canonico. F3/F4 de INIT-8 e inbound completo:
  opt-in via config/UI.
- INIT-4 (prioridad/SLA/olas), INIT-6 (destino->staging + UI), INIT-4b
  (KPI SLA), MEJ-BOTTLENECK, MEJ-SLA-OPT: opt-in o aditivos.
- MEJ-2 experiment runner + tab A/B. KPIs opcionales comparables:
  fill_rate_pct, avg_dock_to_stock, avg_putaway_distance, avg_putaway_wait,
  fill_rate_effective_pct (+ throughput_picks_per_s como KPI limpio).
- Optimizador Optuna CLI+web (warm-start en serie antes de paralelizar).
- Web: `server.py` + `app_state.py` + `routers/`. Tabs: Carga 1 (con
  distribucion por clase), Estrategias 2 (con las 4 cards de tiempos
  INIT-8), Flota 3, Layout 4, Outbound Staging 5, Inbound 6, Optimizacion
  7, Experimentos A/B 8.
- Robustez del motor: excepcion a mitad de tour degrada por WO (no pierde
  la corrida); watchdog de no-progreso corta deadlocks con volcado parcial.
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

Candidatos: INIT-3 v3 (capacidades por agente en el optimizador, listo para
tomar), BK-05 (guard de flota vacia al guardar el canonico desde la UI, ver
BACKLOG), decisiones pendientes de arriba, o iniciativa nueva del Director.

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya
  en `.gitignore`.
- BK-05 (UX pre-existente): guardar el config canonico desde la UI lo
  bloquea el guard de flota vacia (`agent_types: []` usa el fallback por
  contadores que la UI no representa como grupos). En BACKLOG.
