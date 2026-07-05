# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-05

## Git

- `main` = pendiente de commit de este cierre (ver commit mas reciente en
  `git log -1`). Working tree limpio salvo lo de esta sesion. Sin ramas
  feature pendientes de merge.
- Baseline byte-identico vigente: `sha256=5f1f4adcd2a288d2...`, 4.919.513 bytes,
  seed 42, Python 3.13.6 (`tests/baseline.json`). Sin cambios desde INIT-1
  (MEJ-2 v2 no toca el `.jsonl`, solo el archivo separado de metricas).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 90 passed, 1 deselected (~3.5s)
python scripts/regression_gate.py  # GATE PASS esperado
```

## Que esta VIVO y ACTIVO ahora mismo (ademas de lo descrito en CLAUDE.md §3)

- Congestion timewindow: activa en `config.json` canonico (no opt-in).
- INIT-4 (prioridad/SLA/olas, tiempos de pick escalables): opt-in, default off.
- MEJ-2 (experiment runner `scripts/experiment_runner.py`): CLI, modos
  `run`/`compare`, requiere `scipy` (ya en requirements.txt). KPIs incluyen
  `fill_rate_pct` (N/A en modo Stochastic, real en modo Deterministic/archivo
  -- MEJ-2 v2).
- Optimizador Optuna: CLI (`entry_points/run_optimization.py`) Y web
  (`POST/GET /api/optimization/start|status|stop`, fire-and-forget +
  polling via BD SQLite de Optuna). Espacio de busqueda: `num_operarios_terrestres`,
  `num_montacargas`, `dispatch_strategy`, `max_wos_por_tour`, `radio_cercania`
  (solo si estrategia == Cercania).
- INIT-1: `StochasticOrderStrategy` asigna cada WO a ubicacion REAL de su SKU
  (no round-robin ciego). `DeterministicOrderStrategy` (modo archivo) ya lo
  hacia asi desde antes (Allocation Layer V12.1).
- `export_optimization_metrics()` (`event_generator.py`) ahora expone
  `fill_rate_pct`/`service_level` ademas de los KPIs de siempre -- `None` en
  modo Stochastic, mismo comportamiento que INIT-5 en visor/API/Excel.

## Decisiones del Director pendientes (bloqueantes para arrancar trabajo ahi)

1. **INIT-6 — staging multi-destino por ruta.** Necesita que el Director
   conteste antes de planificar: ¿existe campo de destino en el esquema de
   pedidos? ¿cuantas zonas de staging hay dibujadas en el TMX? ¿que se
   entiende operativamente por "ruta"? Ver `docs/BACKLOG.md`.
2. **BK-02 — FIFO Estricto en UI.** El Director quiere redefinir que deberia
   hacer FIFO operacionalmente antes de exponerlo.
3. **`_legacy/web_dashboard/`** (puerto 8001, huerfano/roto). Conservar /
   reparar / eliminar — el Director queria revisarlo primero.

## Siguiente prioridad sugerida (sin decidir aun)

INIT-3 v2 (UI minima para el optimizador web, o capacidades por agente en el
espacio de busqueda), INIT-4b (KPI de SLA vencido), o alguna de las 3
decisiones de arriba. Ver `docs/BACKLOG.md` para el resto del inventario
abierto.

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya
  en `.gitignore`.
