# CHANGELOG — Gemelo Digital de Almacen

Registro append-only de iniciativas cerradas. NUNCA se edita una entrada vieja,
solo se agrega una nueva arriba. El detalle exhaustivo vive en el mensaje de
commit (`git log`/`git show <sha>`) y, si existio, en el plan original bajo
`docs/antiguos/`; esto es solo un indice escaneable con el "por que" cuando no
es obvio del commit.

Formato por entrada: `YYYY-MM-DD  ITEM — resumen de 1-2 lineas. sha(s). [link a plan si aplica]`

---

## 2026-07-05 (cont. 4)

- **INIT-6 — UI web para configurar staging por destino + capacidad de
  camion.** Auditoria (a pedido del Director) encontro 2 huecos reales: la
  UI no tenia forma de editar `destino_staging_map` (INIT-6 Opcion B, sin
  riesgo de perdida de datos -- `save_config` hace merge y preserva claves
  que la UI no gestiona, pero tampoco era EDITABLE desde el navegador) ni
  `outbound.truck_capacity` (ya se guardaba/preservaba, pero sin campo para
  cambiarlo). Se agrego: editor de filas destino->zona (tab "Outbound
  Staging", mismo patron visual que "Prioridades de Work Area" de
  fleet-manager) + campo `truck-capacity` junto a `truck-interval` (visible
  solo con outbound activo). **Guia sutil en la UI** (a pedido del Director,
  "profesional, sin ambiguedad, sin manual gigante"): se identifico que el
  patron ya existia parcialmente (`help-text` por campo) y se formalizo en 2
  niveles -- `.tab-intro` (1 parrafo corto arriba de cada pestaña, el "por
  que" general, nuevo) + `.description-text` (contexto por card, ya
  existia) + `.help-text` (detalle por campo, ya existia). Aplicado a la
  pestaña Staging explicando la precedencia real (zona explicita en el
  archivo > destino mapeado > reparto aleatorio). Validado en navegador real
  (Preview): agregar/quitar filas, guardar y verificar el round-trip completo
  en `config.json` (incluyo confirmar que `save_config` no descarta la clave
  nueva). `config.json` restaurado a su estado original tras la prueba (no
  se dejo data de prueba commiteada). Suite 104 passed, gate PASS sin cambio
  de baseline (solo archivos estaticos web).

## 2026-07-05 (cont. 3)

- **INIT-6 (Opciones A + B) — staging multi-destino por ruta.** RCA en codigo
  (no supuesto) revelo que ya existian 7 zonas fisicas reales de staging
  (`Warehouse_Logic.xlsx`, hoja `OutboundStaging`) e infraestructura parcial
  (`ParsedOrder.staging_id`), pero el config canonico manda 100% a una sola
  zona, y el hallazgo mas importante: `OutboundProcess` tomaba pallets FIFO
  de una cola GLOBAL sin filtrar por `staging_id`, mezclando pedidos de
  zonas/rutas distintas en un mismo camion -- el eslabon perdido real.
  **Opcion A**: `OutboundProcess.run()` ahora sirve una sola zona por camion
  (la del pallet mas antiguo en espera); sin inanicion, sin cambio al
  baseline (outbound esta deshabilitado en el canonico). **Opcion B**: campo
  `destino` opcional en pedidos (JSON/CSV) + `destino_staging_map` en config
  (mismo patron que `work_area_equipment`) resuelto via nuevo
  `AlmacenMejorado._resolver_staging_id()` (precedencia: staging_id explicito
  > destino mapeado > fallback aleatorio, sin regresion). Opcion C
  (clustering geografico automatico) diferida -- requiere datos de
  geolocalizacion de clientes inexistentes hoy. 9 tests nuevos + 3 de
  validacion web. Suite: 104 passed. Gate PASS sin cambio de baseline (ningun
  cambio toca el escenario canonico, que tiene outbound deshabilitado).

## 2026-07-05 (cont. 2)

- **INIT-3 v2 — UI web del optimizador + fix de bug de concurrencia real
  encontrado en el camino.** Nuevo tab "Optimizacion" en el configurador web
  (`web_prototype/static/web_configurator/`): inputs (trials, jobs, costos),
  boton Iniciar/Detener, panel de progreso con polling cada 3s
  (`/api/optimization/status`), recupera un estudio en curso si la pagina se
  recarga. **Bug real encontrado y corregido**: `study.enqueue_trial()`
  (warm-start) + `study.optimize(n_jobs>1)` provoca una carrera de Optuna --
  dos workers toman el mismo trial encolado y le asignan el mismo
  `trial.number`, perdiendo un trial silenciosamente (reproducido de forma
  aislada y confirmado: con n_trials=2/n_jobs=2 solo se completaba 1 trial).
  Preexistente en `optimizer.py` desde su creacion, nunca antes expuesto
  porque nadie habia corrido `n_jobs>1` -- el panel web lo dispara con su
  default (`n_jobs=2`). Fix: `SimulationOptimizer.optimize()` consume el
  warm-start en serie (n_jobs=1, n_trials=1) ANTES de arrancar el resto en
  paralelo. Ademas: `OptimizationRunner.status()` capturaba solo `KeyError`
  para "estudio no existe todavia"; una consulta de status justo despues de
  `start()` puede chocar con la migracion Alembic del subprocess recien
  lanzado (`IntegrityError` de sqlalchemy) -- ahora se captura como
  transitorio. Validado: CLI (n_trials=2/4, n_jobs=2/3, sin perdida de
  trials) + flujo real via navegador (3/3 trials completados, antes se
  perdia 1). 2 tests nuevos de regresion (orquestacion Optuna con objective
  mockeado, sin correr sim real). Suite: 92 passed. Gate PASS sin cambio de
  baseline (no toca el motor).

## 2026-07-05 (cont.)

- **MEJ-2 v2** — `export_optimization_metrics()` ahora incluye `fill_rate_pct`
  y `service_level` (mismo patron/fuente que INIT-5:
  `build_service_level_summary()`). En modo Stochastic (default de
  `config.json`) es `None`/N/A -- consistente con como ya se comporta en
  visor/API/Excel, no es un caso especial nuevo. `experiment_runner.py`
  filtra los `None` (`_collect_values`) en vez de tratarlos como 0.0. No toca
  el `.jsonl` (metrica en archivo separado) -- gate PASS sin cambio de
  baseline. Probado en ambos modos (Stochastic -> N/A; Deterministic con
  `layouts/Orders Test.json` -> 100.0%). 2 tests nuevos, suite 90 passed.

## 2026-07-05

- **INIT-3** (`3cf359e`) — RCA revelo que el desalineamiento motor-optimizador
  del backlog ya no existia (nombres de estrategia correctos, fallback de
  flota vivo). Se amplio el espacio de busqueda (`max_wos_por_tour`,
  `radio_cercania` condicional) y se expuso en la web (`optimization_runner.py`
  + 3 endpoints, fire-and-forget con polling via BD Optuna). Sin cambio al motor.
- **INIT-1** (`be29590`) — RCA redujo el alcance real: el modo por archivo ya
  usaba ubicacion real (Allocation Layer V12.1); el bug vivia solo en
  `StochasticOrderStrategy` (SKU y ubicacion elegidos sin relacion). Fix:
  indice `points_by_sku` sobre `sku_initial`. Baseline actualizado
  (`5f1f4adc...`, 4.919.513 bytes, -3.9%; makespan intacto).
- **Fix WOs sobredimensionadas** (`bac6606`) — `_validar_y_ajustar_cantidad`
  entraba en bucle infinito si `sku.volumen > max_capacity`. Guard temprano
  devuelve `[]` (backorder implicito) en vez de colgarse. Sin cambio al
  baseline (el escenario canonico no dispara el path).
- **MEJ-2 v1** (`6624630`) — `scripts/experiment_runner.py`: N replicas +
  IC95%, comparacion A/B con t-test pareado (`scipy`). KPIs v1 = los que ya
  exporta `export_optimization_metrics`; v2 (nivel de servicio) diferido.
- **Merge MEJ-3+MEJ-4 a main** (`3cf359e`..`82f1487` ff) — autorizado por el
  Director tras CI verde.
- **Reestructuracion de documentacion** — ver seccion "Meta" mas abajo.

## 2026-07-04

- **MEJ-4** (`d1fec07`) — anti-colisiones completo: dwell reservado al
  planificar (picking/descarga/destino-con-permanencia), planner reescrito
  estilo SIPP (0 fallos, 0.7ms/plan), fallback visible, clearance 0.05,
  parking disperso. Co-ocupaciones 28->9. Baseline `c6f129ef...`.
  **Hallazgo:** makespan +55% (2011->3121s) es la cola REAL del staging unico
  (antes 4 agentes superpuestos, fisica imposible). Redefinido 2026-07-05 como
  **INIT-6** (staging debe consolidar por ruta/destino, no un unico punto) —
  ver BACKLOG.md. Plan: `docs/antiguos/PLAN_MEJORA_4_ANTICOLISIONES.md`.
- **MEJ-3** (`e4db0ab`) — `src/core/config_schema.py` (pydantic, unico,
  validacion-only). Purga de 10 claves muertas + 9 subclaves F3 de congestion
  + 2 controles UI sin efecto (capacidad_carro, map_scale). Baseline `662ed5e3...`.
- **MEJ-1** (`6b0b438`..`093b8c9`, en main) — suite pytest (`tests/`, ~73
  tests) + `scripts/regression_gate.py` (byte-identico modulo EOL) + CI
  GitHub Actions verde. Primera red de seguridad automatizada del proyecto.
  Plan: `docs/antiguos/PLAN_MEJORA_1_RED_SEGURIDAD.md`.

## 2026-06-29

- **INIT-4** (`91dd6c0`, `c27dacb`, `fd0a41d`) — prioridad/SLA/olas + tiempos
  de pick escalables, 3 fases opt-in con gate byte-identico. C1 tiempo por
  cantidad/volumen; C2 prioridad "fuerte limpia" (Opcion C del Director); C3
  olas por release diferido. Diferido: KPI de SLA vencido (INIT-4b, pendiente).
  Plan: `docs/antiguos/PLAN_INIT4.md` (o `docs/PLAN_INIT4.md` si aun no se movio).

## 2026-06-27

- **Logging refactor** (`b990964`) — ~186 `print()` -> logging por nivel en
  hot-path (dispatcher, operators, event_generator).
- **WAREHOUSE_SEED** (`413888c`) — semilla determinista via env var. Gate
  byte-identico base (`a4ae8d4e...`, 5.379.372 bytes).
- **Template Method** (`41ddc22`) — `BaseOperator.agent_process()` + hook
  `_do_picking_at()` por subclase. -296 lineas en operators.py (-16.7%).
- **BK-05** (`f3a3ec5`) — botones stub E6/E7 eliminados (sin backend real).

## 2026-06-21 / 2026-06-20

- **INIT-5** (`8cc7f8d`) — nivel de servicio / backorders expuestos en visor,
  API y Excel. Fuente: `core/replay_utils.build_service_level_summary()`.
- **BK-04 + QA-1/2/3** (`1bb24a3`, `e50b924`, `e2c6293`, `19e8829`) — flota por
  defecto sin `work_area` causaba outbound colgado (camiones vacios
  indefinidamente). Fix preventivo (validacion bloqueante + flota real +
  indicador UI) + hardening QA (mapa explicito `work_area_equipment`).

## 2026-06-14 / 2026-06-15

- **BK-01** — estrategia "Cercania" + `radio_cercania` expuestos en UI.
  Incluye fix H-5 (alias "Ejecucion de Plan") y H-6 (radio blando, evita
  deadlock).
- **BK-03 descartado** — greedy nearest-neighbor evaluado con evidencia
  (N=3): -1.54% distancia/WO, dentro del ruido estadistico. Flag
  `cercania_tour_mode` default "cost".

## Anterior a 2026-06-14

Ver `git log --oneline` para el detalle completo (Allocation Layer V12.1,
migracion V11->V12, arquitectura headless, eliminacion de live simulation).
Documentos historicos de esas fases en `docs/antiguos/`.

---

## Meta: reestructuracion de la documentacion (2026-07-05)

Con este archivo se separa "estado actual" (`docs/STATE.md`, se REESCRIBE
entero cada sesion, nunca acumula) de "historial" (este CHANGELOG, append-only,
terso) de "pendientes" (`docs/BACKLOG.md`, recortado a solo lo abierto) de
"identidad/reglas/arquitectura" (`CLAUDE.md`, estable, ya no carga estado).
Razon completa y estructura objetivo: ver `docs/META_DOCUMENTACION.md`.
