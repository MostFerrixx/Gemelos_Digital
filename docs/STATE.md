# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-05

## Git

- `main` = `3b0af80`. Working tree limpio. Sin ramas feature pendientes de
  merge. Push directo a main autorizado por el Director para esta sesion
  (confirmado 2026-07-05 tras un bloqueo del clasificador de permisos).
- Baseline byte-identico vigente: `sha256=5f1f4adcd2a288d2...`, 4.919.513 bytes,
  seed 42, Python 3.13.6 (`tests/baseline.json`). Sin cambios desde INIT-1 --
  todo lo posterior (MEJ-2 v2, INIT-3 v2, INIT-6 + su UI) no toca el
  escenario canonico (outbound deshabilitado ahi) ni el motor de picking.

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 104 passed, 1 deselected (~7s)
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
- `export_optimization_metrics()` expone `fill_rate_pct`/`service_level`.
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

## Decisiones del Director pendientes

1. **BK-02 — FIFO Estricto en UI.** El Director quiere redefinir que deberia
   hacer FIFO operacionalmente antes de exponerlo.
2. **`_legacy/web_dashboard/`** (puerto 8001, huerfano/roto). Conservar /
   reparar / eliminar — el Director queria revisarlo primero.
3. **INIT-6 Opcion C (clustering geografico)** -- solo si el negocio va a
   tener datos reales de geolocalizacion de clientes. No es bloqueante, es
   una decision de producto a futuro, no de esta semana.
4. **Distribucion real de `outbound_staging_distribution`** en el config
   canonico: ¿repartir el trafico entre las 7 zonas ahora que el mecanismo
   funciona, o mantener 100% en zona 1? Es tuning de negocio, no un bug.

## Siguiente prioridad sugerida (sin decidir aun)

INIT-3 v3 (capacidades por agente en el optimizador), INIT-4b (KPI de SLA
vencido), o alguna de las decisiones de arriba. Ver `docs/BACKLOG.md` para el
resto del inventario abierto.

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya
  en `.gitignore`.
