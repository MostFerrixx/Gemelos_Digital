# PLAN — INICIATIVA #1: Inventario y picking POR UBICACION real + reservas

> Documento VIVO. Rama: `feature/allocation-layer-v12.1`.
> NO se guarda con git (locks colgados). Solo se escribe en disco.
> Actualizar el CHECKLIST y la BITACORA despues de CADA paso.

---

## 0. ESTADO Y CONTEXTO

El Allocation Layer V12.1 (modo determinista) hoy:
1. Suma stock **agregado por SKU** (`DataManager.get_all_available_stock()` ->
   `SELECT sku_code, SUM(qty_available) GROUP BY sku_code`).
2. Asigna la WorkOrder a una ubicacion de picking **ALEATORIA** del area
   (`DeterministicOrderStrategy._get_location_for_area()` -> `random.choice`),
   totalmente desacoplada de donde esta fisicamente el SKU.
3. **Nunca escribe `qty_reserved`**: dos ordenes pueden "asignar" el mismo stock.

La BD ya soporta lo necesario y esta SIN USAR:
- `inventory(location_id PK, sku_code, qty_available, qty_reserved)`.
  `location_id` es PRIMARY KEY => **cada ubicacion contiene exactamente 1 SKU**.
- Un SKU se reparte en VARIAS ubicaciones (ej.: SKU042 en 14 ubicaciones).
- Vista `v_inventory_full` con `qty_free = qty_available - qty_reserved`.
- Estado actual de la BD: 360 ubicaciones PICKING, 50 SKUs, `qty_reserved = 0`
  en todas las filas.

Objetivo: asignar cada item de cada orden a la(s) ubicacion(es) que REALMENTE
tienen ese SKU, dividiendo entre ubicaciones cuando haga falta, y reservar la
cantidad comprometida (`qty_reserved`) para que dos ordenes no peleen por el
mismo stock.

---

## 1. DIAGNOSTICO EXACTO (archivos y funciones implicadas)

| Archivo | Funcion | Rol en el problema / cambio |
|---------|---------|------------------------------|
| `src/subsystems/simulation/order_strategies.py` | `DeterministicOrderStrategy.generate_work_orders` (lin ~352) | Nucleo: hoy asigna ubicacion aleatoria con stock agregado. Se reescribe la fase de allocation. |
| idem | `_build_picking_points_index`, `_get_location_for_area`, `_get_default_work_area` | Helpers de la logica vieja por area. Se sustituyen por allocation por ubicacion real. |
| `src/subsystems/simulation/data_manager.py` | `get_all_available_stock` (lin ~646) | Agregado por SKU. Se conserva pero se añade consulta por ubicacion. |
| idem | (NUEVO) `get_inventory_by_location` | Snapshot SKU -> lista ordenada de ubicaciones con stock. |
| idem | (NUEVO) `commit_reservations` / `reset_reservations` | Persistir `qty_reserved` de forma idempotente. |
| `src/subsystems/simulation/warehouse.py` | `WorkOrder.__init__` / `to_dict` (lin 28 / 96) | Añadir `location_id` para trazar la ubicacion real. |
| idem | `_validar_y_ajustar_cantidad` (lin 327) | Se reutiliza tal cual para el split por capacidad de operario. |
| idem | `_generar_flujo_ordenes` (lin 435) | Punto donde, tras generar WOs, se comprometen las reservas. |
| `src/subsystems/database/schema.sql` / `importer.py` | `inventory.qty_reserved` | Ya existe; el importer lo inicializa a 0. No requiere cambio de schema. |

### Causa raiz
La allocation trabaja sobre un total agregado por SKU y elige la ubicacion al
azar. La informacion de "que ubicacion tiene que SKU" existe en `inventory` pero
no se consulta a ese nivel. Resultado: rutas, distancias, heatmaps y el
optimizador miden sobre ubicaciones ficticias.

---

## 2. DISEÑO DE LA SOLUCION

### 2.1 Snapshot de inventario por ubicacion (DataManager)
Nuevo `get_inventory_by_location()` con UNA sola query (join `inventory` +
`locations`), devolviendo:

```
{
  sku_code: [
    {location_id, x, y, pick_sequence, work_area, equipment_required,
     qty_available, qty_reserved, qty_free},   # qty_free = available - reserved
    ... (ordenadas por pick_sequence ASC)
  ]
}
```

Orden por `pick_sequence ASC` => FCFS deterministico y reproducible (se consume
primero la ubicacion mas temprana en el plan maestro). Trade-off: no optimiza por
proximidad al staging; eso queda para la Iniciativa #2 (congestion/rutas). Se
documenta como decision consciente.

### 2.2 Allocation por ubicacion real (DeterministicOrderStrategy)
Se construye un **ledger en memoria** (copia mutable del snapshot) con el
`qty_free` por ubicacion. Para cada item de cada orden valida:

1. `requested = item.quantity`.
2. Recorrer las ubicaciones del SKU (orden pick_sequence). Para cada una con
   `qty_free > 0`, tomar `take = min(restante, qty_free_ubicacion)`:
   - decrementar el ledger (`qty_free -= take`),
   - acumular la reserva por `location_id` (`reservations[location_id] += take`),
   - aplicar el split por capacidad de operario con
     `_validar_y_ajustar_cantidad(sku, take, work_area_de_la_ubicacion)`,
   - crear una WorkOrder por cada chunk con la ubicacion REAL (`legacy_x/y`),
     `pick_sequence` real, `work_area`/`equipment_required` de ESA ubicacion, y
     `location_id`.
3. Si al agotar las ubicaciones queda `restante > 0` => backorder
   (`unfilled_demand`), igual que hoy pero ahora por falta de stock fisico real.

Notas:
- `item.work_area` (si viene en la orden) pasa a ser **filtro/preferencia
  opcional**: si se especifica, solo se consideran ubicaciones de ese area; si
  tras filtrar no hay stock, se hace fallback a cualquier ubicacion del SKU
  (registrando el ajuste). El area "real" de la WO es la de la ubicacion elegida.
- Se eliminan/deprecan `_get_location_for_area` y `_get_default_work_area` del
  camino determinista (el area ya no se adivina por volumen: sale de la ubicacion
  fisica).
- Dos splits ortogonales y componibles: primero por **disponibilidad por
  ubicacion**, luego por **capacidad de operario** dentro de cada trozo.

### 2.3 Reservas persistentes e idempotentes (DataManager)
Al terminar la allocation se comprometen las reservas en la BD:
- `reset_reservations()` -> `UPDATE inventory SET qty_reserved = 0` (todas las
  filas) para que re-ejecutar la sim no acumule reservas viejas.
- `commit_reservations(reservations: Dict[location_id, qty])` -> set ABSOLUTO
  `UPDATE inventory SET qty_reserved = ? WHERE location_id = ?`.
- Ambas en una sola transaccion. Resultado idempotente: cada corrida deja
  `qty_reserved` reflejando exactamente las WOs de esa corrida; `v_inventory_full`
  muestra `qty_free` correcto.

Trade-off: la allocation reserva sobre `qty_available` (set fresco cada corrida),
no sobre `qty_free` preexistente, porque el pipeline headless asigna el lote
completo en una pasada. Se documenta; si en el futuro hay multiples lotes
concurrentes, se cambiara a consumir `qty_free`.

### 2.4 WorkOrder.location_id
Atributo opcional `location_id` (default None) + en `to_dict`. Permite trazar la
ubicacion real, liberar reservas al pickear (futuro) y validar el picking.

---

## 3. PASOS NUMERADOS (CHECKLIST)

| # | Paso | Estado |
|---|------|--------|
| P0 | Escribir este plan y obtener OK del Director | HECHO |
| P1 | `data_manager.get_inventory_by_location()` (snapshot por ubicacion) | HECHO |
| P2 | `data_manager.reset_reservations()` + `commit_reservations()` (idempotente) | HECHO |
| P3 | `WorkOrder.location_id` (init + to_dict) en `warehouse.py` | HECHO |
| P4 | Reescribir `DeterministicOrderStrategy.generate_work_orders` (allocation por ubicacion) | HECHO |
| P5 | Cablear commit de reservas tras la generacion de WOs | HECHO |
| P6 | Validacion end-to-end headless + evidencia (picking real + qty_reserved escrito) | HECHO |

**TODOS LOS PASOS HECHOS.** Iniciativa #1 implementada y validada end-to-end.

Leyenda: PENDIENTE / EN PROGRESO / HECHO.

---

## 4. COMO SE VALIDARA (validacion empirica)

1. Script de inspeccion: tras correr la allocation, comprobar que cada WO tiene
   `location_id` y que su `(x,y)` coincide con la fila de `inventory`/`locations`
   que tiene ese SKU (no aleatoria).
2. `SELECT SUM(qty_reserved) FROM inventory` debe ser > 0 y == total de unidades
   asignadas (allocation_summary.total_qty_allocated).
3. Para cada `location_id`: `qty_reserved <= qty_available` (no sobre-reserva).
4. Pipeline headless `entry_points/run_generate_replay.py` corre end-to-end y
   genera `.jsonl` + Excel sin errores. Si falta el archivo de ordenes
   determinista en el sandbox, se usa modo stochastic y se aclara (la reserva por
   ubicacion solo aplica al modo determinista; en stochastic se valida que no se
   rompe el pipeline).
5. Reproducibilidad: dos corridas dejan el mismo `qty_reserved` (idempotencia).

---

## 5. BITACORA (que se cambio en cada archivo)

- (P0) Creado `docs/PLAN_INICIATIVA_1.md`. OK del Director recibido (3 decisiones aprobadas).
- (P1) `data_manager.py`: añadido `get_inventory_by_location()` tras
  `get_all_available_stock`. Una query JOIN inventory+locations (PICKING),
  agrupa por sku_code -> lista de ubicaciones {location_id, x, y, pick_sequence,
  work_area, equipment_required, qty_available, qty_reserved, qty_free},
  ordenadas por pick_sequence ASC.
  NOTA: el archivo se TRUNCO en disco (bug host->mount, quedo a 681 lineas).
  Se reparo reescribiendo el tramo final via heredoc directo al mount.
  Sintaxis OK (827 lineas). Queda backup `data_manager.py.bak_trunc` que el
  shell no pudo borrar (permiso denegado) -> el Director debe eliminarlo a mano.
- (P2) `data_manager.py`: añadidos `commit_reservations()` (reset a 0 + set
  absoluto por location_id en una transaccion -> idempotente) y
  `reset_reservations()`. Validado contra warehouse.db: 50 SKUs, SKU042 en 14
  ubicaciones ordenadas asc; recommit deja suma=7 (no acumula); reset deja 0.
  Backup `.bak_trunc` vaciado a 0 bytes (rm sin permiso); el Director puede
  borrarlo o ignorarlo (esta vacio).
- (P3) `warehouse.py`: `WorkOrder.__init__` ahora acepta `location_id=None`,
  lo guarda en `self.location_id` y lo expone en `to_dict()`. Editado via heredoc
  directo al mount (para evitar el bug host->mount). Sintaxis OK (+4 lineas).
- (P4) `order_strategies.py`: reescrita la allocation determinista.
  * Carga ledger por ubicacion (`get_inventory_by_location`) en vez de stock
    agregado (`get_all_available_stock`).
  * Nuevo helper `_allocate_across_locations(sku_locations, requested,
    preferred_area)`: FCFS por pick_sequence, consume `qty_free` (mutando el
    ledger), filtro opcional por work_area con fallback.
  * Cada WO se crea con ubicacion/work_area/pick_sequence/location_id REALES;
    split por capacidad de operario se mantiene por trozo.
  * Construye dict `reservations {location_id: qty}` y lo guarda en
    `self._pending_reservations`; summary enriquecido con
    `locations_reserved`/`total_units_reserved`.
  * `_get_location_for_area`/`_get_default_work_area`/`_build_picking_points_index`
    quedan SIN USO en el camino determinista (siguen definidos, inofensivos).
  Validado con almacen stub + warehouse.db real:
  pedir 55 de SKU042 -> WO 45@LOC-021 + WO 10@LOC-042 (ubicaciones reales,
  FCFS seq 21<42), reservas suma 55 = asignado. Backorder: 733 pedidos / 683
  libres -> 683 asignados en 14 ubicaciones, unfilled 50, rate 93.2%.
- (P5) `order_strategies.py`: al final de `generate_work_orders` se llama
  `almacen.data_manager.commit_reservations(reservations)` (idempotente: resetea
  qty_reserved a 0 y escribe los absolutos de esta corrida). Validado con
  warehouse.db real: 2 ordenes de SKU042 (55+10) -> LOC-021 reserva 45/45 y
  LOC-042 reserva 20/32 (las dos ordenes compiten por el mismo stock via ledger
  compartido), SUM(qty_reserved)=65, 0 sobre-reservas, re-correr deja 65
  (idempotente). Reset deja 0.
- (P6) VALIDACION END-TO-END HEADLESS.
  * El archivo de ordenes de produccion `uploads/orders_ordenes_prueba_real.json`
    NO existe en el sandbox (dir uploads/ vacio). Se genero un archivo de prueba
    `uploads/orders_test_init1.json` (4 ordenes con SKUs reales: split
    multi-ubicacion, competencia por stock y backorder forzado) + config temporal
    `config_init1_test.json`, y se corrio `run_generate_replay.py --config
    config_init1_test.json` en modo DETERMINISTA.
  * Resultado: 600 uds asignadas, 1 backorder (25 uds, rate 96%), 17 WorkOrders,
    reservas persistidas (16 ubicaciones, 600 uds). DB: SUM(qty_reserved)=600,
    0 sobre-reservas (qty_reserved<=qty_available en todas).
  * Pipeline completo OK: genero replay .jsonl (642KB), raw_events.json,
    simulation_report.json, simulation_report.xlsx y heatmap .png.
  * Picking REAL: los 341 eventos de picking del .jsonl ocurren en las 16
    ubicaciones reales que contienen los SKUs (antes: ubicacion aleatoria).
  * Tras validar se reseteo qty_reserved a 0 (estado limpio para el Director).

## 7. PENDIENTES DE LIMPIEZA (para el Director)
- Borrar archivos de prueba (quedaron VACIOS, el shell del sandbox no tuvo
  permiso de rm): `config_init1_test.json`, `uploads/orders_test_init1.json`,
  `src/subsystems/simulation/data_manager.py.bak_trunc`.
- El config de PRODUCCION (`config.json`) sigue apuntando a
  `uploads/orders_ordenes_prueba_real.json` (modo deterministic). En tu PC ese
  archivo existe; la corrida real validara la reserva por ubicacion con tus
  ordenes reales.
- (Opcional, Iniciativa #5) propagar `unfilled_demand`/backorders y
  `qty_reserved` a /api/metrics y al dashboard.
- (Siguiente paso natural, fuera de alcance) liberar la reserva y decrementar
  `qty_available` al pickear durante la sim.

---

## 6. NOTAS / DECISIONES ABIERTAS

- FCFS por `pick_sequence` (no por proximidad). Optimizacion de proximidad ->
  Iniciativa #2.
- Reserva sobre `qty_available` con reset previo (idempotente para corrida unica
  de lote). Multi-lote concurrente -> consumir `qty_free` (futuro).
- No se toca el schema (qty_reserved ya existe). No se hacen commits de git.
- El decremento REAL de `qty_available` al pickear (liberar reserva -> bajar
  stock) NO entra en esta iniciativa; aqui solo se RESERVA en fase pre-sim.
  Se deja anotado como siguiente paso natural.

---

# FASE 2 — DECREMENTO DE STOCK EN SIMULACION (al pickear)

> Aprobado por el Director. Lo que en Fase 1 quedo fuera de alcance: durante la
> corrida, cuando el operario RECOGE fisicamente el item, bajar `qty_available`
> y liberar la `qty_reserved` correspondiente, sin negativos y manteniendo
> consistencia. Mismo rigor y mismo flujo de doc vivo que la Fase 1.

## F2.1 DIAGNOSTICO (donde ocurre el pick)

El "pick real" ocurre en `src/subsystems/simulation/operators.py`, en el
`agent_process`, en el momento en que el operario termina el picking de una WO:
- **GroundOperator** (~lin 429-433): tras `yield timeout(picking_duration)` se
  hace `self.cargo_volume += wo.calcular_volumen_restante()`, luego
  `wo.status = 'picked'` y `wo.cantidad_restante = 0`.
- **Forklift** (~lin 820-831): identico patron (con LIFT_TIME extra);
  `wo.cantidad_restante = 0` (lin 824) y `wo.status = 'picked'` (lin 831).

La cantidad efectivamente recogida de esa WO = `wo.cantidad_inicial`
(`cantidad_restante` arranca en `cantidad_inicial` y pasa a 0). Cada WO ya lleva
`wo.location_id` (Fase 1) en modo determinista; en stochastic es `None`.

Hoy NINGUN punto del motor decrementa `qty_available` ni libera `qty_reserved`
durante la sim (confirmado: solo el allocation pre-sim escribe `qty_reserved`).

## F2.2 DISEÑO

### a) `DataManager.consume_stock(location_id, qty)`
UPDATE atomico de una fila de `inventory`:
- `qty_available = MAX(0, qty_available - qty)` (guard anti-negativo; si fuera a
  quedar negativo, log [WARN] y cap a 0).
- `qty_reserved  = MAX(0, qty_reserved - qty)` (libera la reserva consumida).
- `last_updated = <sim_now>` (timestamp SimPy).
Devuelve (new_available, new_reserved) o None si error. Una conexion por llamada
(coherente con el patron actual de get_available_stock; volumen de WOs bajo).

### b) `AlmacenMejorado.consumir_stock_picking(wo, sim_now)`
Wrapper fino llamado desde operators:
- Si no hay data_manager, o `wo.location_id` es None (modo stochastic), o
  `wo.cantidad_inicial <= 0` -> NO-OP (silencioso/log debug).
- Si no, delega en `data_manager.consume_stock(wo.location_id, wo.cantidad_inicial)`
  y loguea `[STOCK] pick LOC qty -> avail/reserved` (ASCII, Ley 4).
Centraliza la logica para no duplicar en Ground/Forklift (solo 1 llamada c/u).

### c) Reproducibilidad / idempotencia (igual filosofia que Fase 1)
Problema: si persistimos el decremento en la MISMA BD canonica, re-correr la sim
agotaria el stock acumulativamente y el ledger de la siguiente corrida leeria
`qty_available` ya mermado.
Solucion (RECOMENDADA): `DataManager.restore_inventory_baseline()`:
- Asegura tabla `inventory_baseline(location_id PK, qty_baseline)`. Si esta
  vacia, la puebla con el `qty_available` ACTUAL (snapshot baseline; la BD hoy
  tiene stock completo y qty_reserved=0, asi que el baseline = stock full).
- Restaura `UPDATE inventory SET qty_available = (baseline), qty_reserved = 0`.
Se llama al INICIO del allocation determinista (ANTES de
`get_inventory_by_location`), de modo que cada corrida arranca del baseline ->
idempotente y reproducible, igual que el reset de reservas en Fase 1.
- Trade-off / nota: si el Director re-importa con `run_migration` (recarga
  `inventory`), el baseline deberia refrescarse. Se documenta; opcional anadir un
  `restore_inventory_baseline(force=True)` o limpiar la tabla baseline en el
  importer (fuera de alcance salvo que se pida).
- ALTERNATIVA (descartada): no persistir y llevar el consumo solo en memoria. Se
  descarta porque el Director pidio que `qty_available` REFLEJE el consumo real
  tras la corrida (verificable en BD).

## F2.3 PASOS (CHECKLIST FASE 2)

| # | Paso | Estado |
|---|------|--------|
| F2.P0 | Escribir esta seccion y obtener OK del Director | HECHO |
| F2.P1 | `DataManager.consume_stock()` + `restore_inventory_baseline()` | HECHO |
| F2.P2 | `AlmacenMejorado.consumir_stock_picking(wo, sim_now)` (wrapper) | HECHO |
| F2.P3 | Llamar `restore_inventory_baseline()` al inicio del allocation determinista | HECHO |
| F2.P4 | Insertar la llamada de consumo en operators (Ground + Forklift) en el pick | HECHO |
| F2.P5 | Validacion end-to-end (qty_available consumido, reservas liberadas, sin negativos, pipeline OK) | HECHO |

**FASE 2 COMPLETA.** Decremento de stock en simulacion implementado y validado.

## F2.4 COMO SE VALIDARA
1. Correr headless determinista (archivo de prueba si el real no esta en sandbox).
2. Comparar baseline vs final: `SUM(baseline.qty_baseline) - SUM(inventory.qty_available)`
   == unidades realmente pickeadas (== total asignado si todas las WOs se pickean).
3. `SUM(qty_reserved)` final ~ 0 (todas las reservas de WOs pickeadas liberadas).
4. `COUNT(*) WHERE qty_available < 0` == 0 (sin negativos).
5. Idempotencia: dos corridas dejan el mismo estado final (gracias al baseline).
6. Pipeline genera `.jsonl` + `.xlsx` + heatmap sin errores.

## F2.5 BITACORA FASE 2
- (F2.P0) Anadida seccion Fase 2 al doc. OK del Director (enfoque baseline aprobado).
- (F2.P1) `data_manager.py`: anadidos `consume_stock(location_id, qty, sim_now)`
  (UPDATE: qty_available=MAX(0,..-qty), qty_reserved=MAX(0,..-qty), last_updated;
  no-op si location None/qty<=0/loc inexistente; log [STOCK][WARN] si pick>avail)
  y `restore_inventory_baseline()` (tabla aux `inventory_baseline` autocreada con
  CREATE TABLE IF NOT EXISTS, snapshot lazy del qty_available actual, y restore
  qty_available<-baseline + qty_reserved=0). Validado vs warehouse.db: stock total
  20736; consume(10)->(53,0) ts=42.0; guard topa a 0 sin negativos; restore vuelve
  a 20736 y reserved=0; no-op confirmado.
- (F2.P2) `warehouse.py`: anadido `AlmacenMejorado.consumir_stock_picking(wo,
  sim_now)` tras `get_order_validation_result`. Delega en
  `data_manager.consume_stock(wo.location_id, wo.cantidad_inicial, sim_now)`;
  NO-OP si no hay data_manager / wo sin location_id (stochastic) / qty<=0. Log
  ASCII `[STOCK] Pick ...`.
- (F2.P3) `order_strategies.py`: en `generate_work_orders` (determinista) se
  llama `restore_inventory_baseline()` JUSTO ANTES de `get_inventory_by_location()`
  para que el ledger arranque del baseline.
- (F2.P4) `operators.py`: insertada
  `self.almacen.consumir_stock_picking(wo, self.env.now)` en el momento del pick
  en GroundOperator (tras status='picked'+cantidad_restante=0) y en Forklift
  (tras status='picked'). 2 llamadas.
- (F2.P5) VALIDACION END-TO-END (modo determinista, archivo de prueba ya que el
  de produccion no esta en el sandbox). Run headless completo:
  * Allocation 600 uds (17 WOs, 1 backorder 25 uds), reservas 600 en 16 ubic.
  * Picks en sim: cada WO baja qty_available y libera qty_reserved (logs [STOCK]).
  * DB tras corrida: baseline 20736 -> avail 20136 => CONSUMIDO=600 (== asignado).
  * reservas finales = 0 (todas las WOs pickeadas liberaron su reserva).
  * 0 negativos en qty_available / qty_reserved.
  * IDEMPOTENCIA: 2a corrida -> mismo consumido 600, mismo avail final 20136.
  * Pipeline OK: genero json + jsonl + png + xlsx.
  * Estado limpio: BD restaurada a baseline (20736, reserved 0) tras validar.

## 8. NOTA TABLA AUXILIAR (Fase 2)
- Se creo la tabla `inventory_baseline(location_id, qty_baseline)` (360 filas,
  snapshot del stock full = 20736 uds). NO toca el schema canonico. Si re-importas
  con `run_migration`, conviene vaciarla para refrescar el baseline
  (`DELETE FROM inventory_baseline;` o `DROP TABLE inventory_baseline;` -> se
  re-crea sola en la siguiente corrida).
- Archivos de prueba quedaron VACIOS (rm sin permiso en sandbox), borrar a mano:
  `config_init1_test.json`, `uploads/orders_test_init1.json`,
  `src/subsystems/simulation/data_manager.py.bak_trunc`.
