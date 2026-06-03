# ANALISIS PROFUNDO — INICIATIVAS PRIORITARIAS (Gemelo Digital de Almacen)

> Documento de progreso INCREMENTAL. Rama: `feature/allocation-layer-v12.1`. Fecha: 2026-05-31.
> Objetivo: concluir en las 5 iniciativas mas importantes a implementar ahora.

---

## A. ESTADO DEL ANALISIS (checklist)

| Area | Archivos clave | Estado |
|------|----------------|--------|
| 0. Mapa del repo | estructura, LOC | [x] REVISADO |
| 1. Motor SimPy — warehouse | warehouse.py (582) | [x] REVISADO |
| 2. Dispatcher (doble barrido) | dispatcher.py (1318) | [x] REVISADO |
| 3. Operarios | operators.py (1128) | [x] REVISADO |
| 4. Estrategias de orden | order_strategies.py (676) | [x] REVISADO |
| 5. Allocation Layer V12.1 | data_manager, warehouse, order_strategies | [x] REVISADO |
| 6. Modelo de datos | data_manager.py (681) | [x] REVISADO |
| 7. Routing/pathfinding | pathfinder, route_calculator, assignment_calculator | [~] PARCIAL (sin congestion) |
| 8. DB / migracion / schema | database_manager, importer, schema.sql | [x] REVISADO |
| 9. Generacion replay | event_generator.py (329) | [x] REVISADO |
| 10. Analytics / reportes / heatmap | analytics_engine, exporter_v2, visualizer.py | [x] REVISADO |
| 11. GUI web | web_prototype/server.py (1167), static/* | [x] REVISADO |
| 12. Optimizacion Optuna | optimizer.py (353) | [x] REVISADO |

LOC total nucleo ~10.7k lineas Python.

---

## B. HALLAZGOS POR AREA

### 0. Mapa del repo
- Vivo: `src/`, `entry_points/`, `web_prototype/`, raiz (run_migration, server_manager, simulation_buffer, start_hidden, visualizer).
- Mas grandes: dispatcher.py (1318), server.py (1167), operators.py (1128) -> candidatos a complejidad/God-object.

### 1+5. warehouse.py + Allocation Layer V12.1
- `WorkOrder` tiene qty_requested/qty_allocated/is_partial. Pero qty_allocated = cantidad en __init__; is_partial casi siempre False. El backorder REAL se calcula en order_strategies, no en la WO.
- `_validar_y_ajustar_cantidad`: divide WO si volumen > capacidad. BUG: si `sku.volumen > max_capacity` -> `unidades_por_viaje = 0` -> bucle infinito.
- `registrar_evento`: acopla logica de replay (pixel coords, capacidad) dentro del modelo de dominio. Mezcla responsabilidades.
- Catalogo desde SQLite (data_manager), fallback sintetico. Volumen m3 -> int*100.

### 5. order_strategies.DeterministicOrderStrategy (Allocation Layer)
- FCFS por orden de archivo. Sin prioridad de orden ni de SKU. `min(requested, stock)`, decrementa stock virtual (snapshot), registra unfilled_demand. SOLO en modo determinista; el estocastico NO valida stock.
- GAP CORRECTITUD CLAVE: la ubicacion de la WO se asigna con `random.choice` de cualquier picking point del area (`_get_location_for_area`), DESACOPLADA de donde realmente esta el stock del SKU. Stock se suma agregado por SKU; la WO puede ir a una ubicacion que no contiene ese SKU.
- No hay reasignacion/split de un item entre varias ubicaciones con stock. No hay reservas; el stock no se decrementa durante la sim (solo pre-sim).
- `_get_default_work_area`: heuristica por volumen, puede no coincidir con equipment_required real.
- Backorders quedan SOLO en validation_result (reporte); la "deuda adjunta" en dashboard NO esta implementada.

### 6. data_manager.py
- Dual-mode: SQLite (warehouse.db) preferido, Excel fallback.
- `get_all_available_stock`: SUM(qty_available) GROUP BY sku_code -> agregado por SKU (ver gap de ubicacion). `get_available_stock` abre conexion SQLite por llamada (ineficiente).
- Validacion: picking fuera de grid = warning; staging fuera de grid = fatal.
- Inventario por ubicacion EXISTE en tabla `inventory` (location_id, sku_code, qty_available) pero la sim NO lo usa por ubicacion, solo agregado. Oportunidad lista.

### 2. dispatcher.py (DispatcherV11, doble barrido)
- 4 estrategias: FIFO Estricto, Optimizacion Global, Ejecucion de Plan (Filtro por Prioridad), Cercania. La "prioridad" es por WORK_AREA del operario, NO por prioridad de orden.
- GAP: WorkOrder NO tiene atributo `priority` real -> en todos los eventos se usa `getattr(wo,'priority',99)`. Urgencias/SLA/olas no modeladas.
- Doble barrido (progresivo seq>=min + circular seq<min) bien documentado. Primera WO por costo (Opt Global) o menor seq (Ejec Plan).
- PERFORMANCE: cientos de print() en hot path por WO/area/tour -> log gigante y sim lenta.
- Pull-based con polling timeout(0.1); sin re-despacho dinamico ni balanceo de carga.
- Deadlock-guard: WOs oversized se marcan 'staged' con cantidad 0 (se "completan" sin pickear) -> falsean KPIs.

### 3. operators.py (GroundOperator, Forklift)
- DUPLICACION MASIVA: `agent_process` de Ground (~330 lineas) y Forklift ~95% identicos (solo lifting + velocidad). Mantenibilidad fragil.
- GAP FUNCIONAL CRITICO: NO hay modelado de congestion/colisiones. Operarios se mueven celda a celda con TIME_PER_CELL fijo SIN exclusion mutua; varios pueden ocupar la misma celda/pasillo/staging sin penalizacion. El simulador NO puede detectar cuellos de botella por trafico (su razon de ser).
- Tiempo de picking = discharge_time FIJO, independiente de cantidad/volumen. Baja fidelidad.
- Movimiento emite un evento `estado_agente` (+ a veces work_order_update) POR CADA CELDA -> .jsonl enorme.
- Sin turnos/descansos/fatiga/averias. Velocidad hardcodeada (TIME_PER_CELL=0.1, LIFT_TIME=2.0).

### 7. Pathfinding / congestion [PARCIAL]
- CONFIRMADO por grep: NO existe modelado de congestion/colision entre agentes en src/. `collision_matrix` es solo para obstaculos ESTATICOS del A*. No hay SimPy Resource/exclusion en celdas, pasillos, ubicaciones de picking ni staging.

### 8. DB / migracion / schema
- `schema.sql` YA tiene `inventory(location_id, sku_code, qty_available, qty_reserved)` y vistas `v_inventory_status` (qty_free = available - reserved) y total por SKU. Infraestructura de RESERVAS e inventario POR UBICACION existe pero NO se usa: el allocation layer agrega por SKU y nunca escribe qty_reserved.
- Bug conocido de doble ruta Warehouse_Logic.xlsx (sim vs run_migration) puede divergir BD/sim.

### 9. event_generator.py
- Loop: `env.run(until=now+1.0)` en while hasta `simulacion_ha_terminado()`. Exporta analytics + .jsonl + metricas opt.
- `export_optimization_metrics` lee `num_operarios_terrestres`/`num_montacargas` (legacy) para resource_costs -> si el config usa `agent_types`, esos contadores pueden ser 0/erroneos en el score del optimizador.

### 10. Analytics / reportes / heatmap
- exporter_v2: pipeline JSON + raw_events + Excel (KPIs, agent performance, heatmap, VisualHeatmap con formato condicional) + PNG via subprocess visualizer.py. Solido.
- GAP: el reporte NO incluye servicio/backorders (qty_requested vs qty_picked, fill rate) ni metricas de congestion (no existen).
- Duplicacion: export_complete_analytics y _with_buffer casi identicos.

### 11. GUI web (server.py + static)
- Endpoints: configurator CRUD, upload-orders (determinista + policy), websocket /ws/simulation-runner, upload/load/validate replay, snapshot/state/metrics (viewer + scrubber), restart/health.
- Replay viewer: `get_state(t)` hace deepcopy del snapshot mas cercano + re-aplica eventos hasta t en CADA frame; `get_metrics` re-llama get_state (doble trabajo). O(eventos) por frame -> lag con replays grandes.
- GAP UI: no expone allocation/backorders (unfilled_demand existe pero no llega a /api/metrics ni al dashboard). Sin comparacion A/B ni resultados del optimizador en la web.
- Seguridad menor: checks anti path-traversal son `pass` (no-op). Local, bajo riesgo.

### 12. Optimizer Optuna
- BUG 1: prueba estrategias (`"FIFO Simple"`, `"Proximity-Based"`) que NO coinciden con los nombres del dispatcher (`"FIFO Estricto"`, `"Cercania"`, `"Optimizacion Global"`). Caen al default silenciosamente.
- BUG 2 (no-op): sugiere `num_operarios_terrestres`/`num_montacargas` (legacy), pero `crear_operarios` usa `agent_types` cuando existe (config real lo tiene). Variar nº operarios puede no tener efecto.
- Espacio de busqueda estrecho (solo nº operarios + estrategia). subprocess por trial. Score = throughput/(costo+penalizacion); failed_wo casi siempre 0.

---

## C. SINTESIS — GAPS FUNCIONALES TRANSVERSALES

1. El gemelo no modela congestion/trafico -> no cumple su proposito de detectar cuellos de botella.
2. La asignacion de stock esta desacoplada de la ubicacion fisica -> rutas, distancias y heatmaps poco realistas.
3. Sin prioridad de orden / SLA / olas; tiempos de pick fijos -> baja fidelidad.
4. El optimizador (feature estrella) prueba estrategias inexistentes y varia parametros que el motor ignora -> posiblemente no-op.
5. La deuda/backorders se calcula pero no se muestra en UI ni reportes.
6. Tech-debt: duplicacion Ground/Forklift, prints masivos en hot path, eventos por celda, deepcopy por frame en replay.
7. Robustez: posible bucle infinito si SKU.volumen > capacidad; WOs oversized auto-"staged" falsean KPIs.

---

## D. TOP 5 INICIATIVAS (FINAL, ordenadas por prioridad)

### #1 — Inventario y picking POR UBICACION real + reservas (correccion fundacional)
**Que es / valor:** Hoy el allocation layer suma stock por SKU y manda la WO a una ubicacion de picking ELEGIDA AL AZAR dentro del area, aunque ese SKU no este ahi. Cambiar a asignar cada item a la(s) ubicacion(es) que REALMENTE tienen stock (tabla `inventory.location_id/qty_available`), dividiendo entre ubicaciones cuando haga falta, y registrar `qty_reserved` (las reservas y `v_inventory_status` YA existen en schema.sql).
**Por que prioritaria:** Base de correctitud de todo el simulador. Sin ubicaciones reales, rutas, distancias, tiempos, heatmaps y el optimizador miden sobre datos ficticios. Esfuerzo relativamente bajo porque la BD ya soporta inventario por ubicacion.
**Esfuerzo:** Medio. **Impacto:** Alto.
**Archivos:** `order_strategies.py` (`_get_location_for_area`, generate_work_orders), `data_manager.py` (consultas por ubicacion), `warehouse.py`, `schema.sql`/`importer.py` (usar qty_reserved).

### #2 — Modelado de congestion / contencion de recursos (capacidad diferencial del gemelo)
**Que es / valor:** Introducir contencion con SimPy: capacidad finita en celdas/pasillos criticos, ubicaciones de picking y stagings (p.ej. `simpy.Resource`/`Container` o reserva de celdas), de modo que dos agentes en el mismo punto generen espera. El replay y los reportes revelan cuellos de botella por trafico y su efecto en el throughput.
**Por que prioritaria:** Es literalmente el proposito del producto ("detectar cuellos de botella y subir el throughput"), hoy ausente. Diferencia un gemelo digital de un simple planificador. Debe construirse sobre ubicaciones realistas (#1).
**Esfuerzo:** Alto. **Impacto:** Muy alto.
**Archivos:** `operators.py` (movimiento -> adquirir/soltar recurso), `route_calculator.py`/`pathfinder.py` (coste con ocupacion), `warehouse.py`, `config.json` (capacidad pasillos, velocidades), analytics (metricas de espera).

### #3 — Reparar y ampliar el optimizador Optuna (feature estrella hoy roto/no-op)
**Que es / valor:** (a) Alinear nombres de `dispatch_strategy` con los del dispatcher; (b) traducir los parametros sugeridos a `agent_types` reales (no a claves legacy que el motor ignora) y corregir `resource_costs`; (c) ampliar el espacio de busqueda (capacidades, max_wos_por_tour, prioridades de zona). Exponer el mejor resultado en la web.
**Por que prioritaria:** "Optimizar" es promesa central del producto y hoy puede no mover nada real. Bajo costo arreglarlo y multiplica el valor del resto.
**Esfuerzo:** Bajo-Medio. **Impacto:** Alto.
**Archivos:** `src/tools/optimizer.py`, `src/engines/event_generator.py` (export_optimization_metrics), plumbing `config.json`/`agent_types`, `web_prototype/server.py`.

### #4 — Prioridad de ordenes / SLA / olas + fidelidad de tiempos de pick
**Que es / valor:** Anadir prioridad/urgencia real (y opcional due-time/ola) a la WorkOrder y que el dispatcher la respete (hoy `priority` es siempre 99 placeholder). Escalar el tiempo de picking/descarga por cantidad/volumen en vez de `discharge_time` fijo. Permite modelar pedidos urgentes y tiempos crebles.
**Por que prioritaria:** Eleva la fidelidad y habilita planificacion (ondas, SLAs). Esfuerzo medio y acotado.
**Esfuerzo:** Medio. **Impacto:** Alto.
**Archivos:** `warehouse.py` (WorkOrder.priority/due), `order_strategies.py` (parsear prioridad), `dispatcher.py` (orden por prioridad), `operators.py` (tiempo = f(cantidad)).

### #5 — Exponer asignacion/backorders ("deuda adjunta") en dashboard y reportes
**Que es / valor:** El allocation layer ya calcula `unfilled_demand`, fill rate y qty_requested vs qty_allocated, pero no llega a UI ni Excel. Propagar al `.jsonl`/metadata, exponer en `/api/metrics` y `/api/state`, mostrar en el dashboard (QTY REQ vs QTY PICK / backorder) y anadir hoja de servicio al reporte.
**Por que prioritaria:** Idea pendiente explicita del Director (CLAUDE.md), aporta visibilidad de nivel de servicio y es victoria rapida (la logica existe; falta cablear datos a la vista).
**Esfuerzo:** Bajo-Medio. **Impacto:** Medio-Alto.
**Archivos:** `order_strategies.py`/`warehouse.py`, `core/replay_utils.py`+`event_generator.py` (metadata), `web_prototype/server.py`, `static/right-dashboard.js`, `analytics_engine.py`.

---

## E. APENDICE — Quick-fixes de robustez (baratos, fuera del TOP5)
- `warehouse._validar_y_ajustar_cantidad`: si `sku.volumen > max_capacity` -> `unidades_por_viaje=0` -> bucle infinito. Forzar minimo 1.
- WOs oversized se marcan 'staged' con cantidad 0 (cuentan como completadas sin pickear) -> marcar como 'failed/backorder' aparte.
- Reducir prints del hot path (dispatcher/operators) a logging por nivel.
- Unificar doble ruta de `Warehouse_Logic.xlsx` (sim vs run_migration).
- Consolidar la duplicacion Ground/Forklift `agent_process` en un metodo base parametrizado.
