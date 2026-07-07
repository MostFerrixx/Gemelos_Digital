# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-07

## Git

- `main` = pendiente del commit del cierre de la review. Working tree limpio
  salvo eso. Sin ramas feature pendientes de
  merge. Push directo a main autorizado por el Director.
- Baseline byte-identico vigente: `sha256=71fc9904141ddc73...`, 4.920.352 bytes,
  seed 42, Python 3.13.6 (`tests/baseline.json`). Actualizado en
  MEJ-BOTTLENECK: SOLO metadata nueva (`bottleneck_summary`) -- eventos
  byte-identicos desde INIT-1 (sha sin linea 1 = `67749aa4...`). REGLA nueva
  pinneada por test BN-05: la metadata del .jsonl NO puede contener valores
  wall-clock (avg_plan_ms rompio el determinismo y se corrigio).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 125 passed, 1 deselected (~8s)
python scripts/regression_gate.py  # GATE PASS esperado
```

## Que esta VIVO y ACTIVO ahora mismo (ademas de lo descrito en CLAUDE.md §3)

- Congestion timewindow: activa en `config.json` canonico (no opt-in).
- INIT-4 (prioridad/SLA/olas, tiempos de pick escalables): opt-in, default off.
- MEJ-2 (experiment runner `scripts/experiment_runner.py`): CLI, modos
  `run`/`compare`, requiere `scipy`. KPIs incluyen `fill_rate_pct` (N/A en
  modo Stochastic, real en modo Deterministic/archivo).
- Optimizador Optuna: CLI Y web con UI visual (tab "Optimizacion" en el
  configurador). Espacio de busqueda: `num_operarios_terrestres`,
  `num_montacargas`, `dispatch_strategy`, `max_wos_por_tour`, `radio_cercania`
  (solo si estrategia == Cercania). El warm-start se consume SIEMPRE en serie
  antes de paralelizar (bug real de perdida de trials si no).
- INIT-1: `StochasticOrderStrategy` asigna cada WO a ubicacion REAL de su SKU.
- `export_optimization_metrics()` expone `fill_rate_pct`/`service_level` y
  `orders_late`/`sla_summary` (MEJ-SLA-OPT); el score del optimizador penaliza
  `orders_late * PENALTY_LATE_ORDER` ($50 default, `--penalty-late` / campo web).
- **INIT-6**: `OutboundProcess` (outbound.py) sirve UNA zona de staging por
  camion (la del pallet mas antiguo), no mezcla zonas/rutas. Pedidos en modo
  archivo (Deterministic) pueden traer `destino` (string) que se resuelve a
  `staging_id` via `config["destino_staging_map"]`
  (`AlmacenMejorado._resolver_staging_id`). 7 zonas fisicas reales
  (`Warehouse_Logic.xlsx`, hoja `OutboundStaging`); el canonico sigue
  mandando 100% a zona 1 (decision de negocio separada). **UI web completa**
  (tab "Outbound Staging" del configurador): editor de filas
  destino->zona + campo `truck_capacity` (visible con outbound activo).
  Validado en navegador real: guardar persiste `destino_staging_map`
  correctamente (`save_config` hace merge, no descarta claves que la UI no
  gestiona explicitamente).
- **Patron de guia en la UI** (formalizado a pedido del Director): 3 niveles,
  todos ya en uso -- `.tab-intro` (1 parrafo arriba de la pestaña, el "por
  que" general de la seccion, NUEVO), `.description-text` (contexto por
  card), `.help-text` (detalle por campo, bajo cada input). Aplicarlo a
  cualquier control nuevo que se agregue de aca en mas -- ya esta en
  `style.css` listo para reusar.
- **INIT-4b**: KPI "SLA" (cumplimiento de `due_time`) en visor/API/Excel,
  mismo patron que INIT-5 (`build_sla_summary()` en `core/replay_utils.py`).
  N/A si ninguna WO completada trae `due_time` (INIT-4 C2 apagado o modo
  Stochastic). Un pedido cuenta "a tiempo" si TODAS sus WOs terminan antes de
  su `due_time` (se usa el MAX `tiempo_fin` del pedido).
- **MEJ-EXP-WEB**: comparador A/B en el configurador (tab "Experimentos A/B",
  paso 7): Config A/B ("Actual" o preset guardado, validado antes de lanzar),
  replicas pareadas, progreso en vivo, tabla de veredictos por KPI.
  Endpoints `/api/experiment/start|status|stop`; el runner CLI reporta
  progreso via `--progress-json` (escritura atomica). Queda un preset
  "PRUEBA B - 3 ground" en `data/config_presets/` (gitignoreado) para probar.
- **MEJ-BOTTLENECK**: `build_bottleneck_summary()` (replay_utils) consolida
  congestion + planner + muelle en metadata del .jsonl, API, hoja Excel
  "Cuellos de Botella" y panel del dashboard derecho del visor. Cada corrida
  genera ahora 5 archivos (antes 8): purgados raw_events / simulation_report
  .json / simulacion_completada. PROHIBIDO meter valores wall-clock en la
  metadata del .jsonl (test BN-05 lo pina; rompe el gate byte-identico).

## Plan acordado con el Director (terna de mejoras, 2026-07-05)

**TERNA COMPLETA (2026-07-06):** (3) comparador A/B web -- HECHO -> (1)
MEJ-BOTTLENECK -- HECHO -> (2) MEJ-SLA-OPT -- HECHO (el optimizador penaliza
pedidos con SLA vencido via orders_late en las metricas; $50/pedido default,
configurable en CLI y web, 0 la desactiva; sin due_time el score es identico
al historico). Detalle en `docs/CHANGELOG.md` 2026-07-06.

## Decisiones del Director pendientes

1. **BK-02 — FIFO Estricto en UI.** El Director quiere redefinir que deberia
   hacer FIFO operacionalmente antes de exponerlo.
2. **INIT-6 Opcion C (clustering geografico)** -- solo si el negocio va a
   tener datos reales de geolocalizacion de clientes. No es bloqueante, es
   una decision de producto a futuro, no de esta semana.
3. **Distribucion real de `outbound_staging_distribution`** en el config
   canonico: ¿repartir el trafico entre las 7 zonas ahora que el mecanismo
   funciona, o mantener 100% en zona 1? Es tuning de negocio, no un bug.

## Siguiente prioridad (sin decidir aun)

La terna acordada quedo completa y la auditoria integral tambien (CHANGELOG
2026-07-06). Candidatos: INIT-3 v3 (capacidades por agente en el
optimizador), fase de limpieza/poda (exporter V1, _with_buffer, CSS
duplicado historico -- requiere OK del Director), o alguna de las decisiones
pendientes de arriba.

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya
  en `.gitignore`.
