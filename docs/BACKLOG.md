# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-07-05 · Responsable: Cerebellum

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| INIT-6 — Staging multi-destino por ruta (Opciones A+B) | HECHO | Alta | Alto | Opcion C (clustering geografico) diferida, sin datos de geolocalizacion |
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| `_legacy/web_dashboard/` — conservar/reparar/eliminar | PENDIENTE DECISION | Baja | Depende | Director quiere revisarla primero |
| INIT-3 v3 — capacidades por agente en el optimizador | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-4b — KPI de SLA vencido en reporte/visor | PENDIENTE | Baja | Bajo | Ninguno, listo para tomar |

---

## INIT-6 — Staging multi-destino por ruta

**Origen:** el hallazgo de makespan +55% de MEJ-4 (ver CHANGELOG 2026-07-04)
fue redefinido por el Director el 2026-07-05: no es un problema de tuning de
congestion, es que el dominio no modela destino ni ruta de entrega.

### Investigacion de codigo (2026-07-05) -- respuestas reales a las 3 preguntas de alcance
1. **¿Campo de destino en pedidos?** No hay campo de destino (tienda/domicilio/
   direccion), pero `ParsedOrder`/el archivo de ordenes YA soporta `staging_id`
   explicito por pedido (JSON/CSV) -- hoy es un numero crudo de zona, sin
   semantica de negocio.
2. **¿Cuantas zonas de staging hay?** **7 zonas fisicas reales**, ya definidas
   en `layouts/Warehouse_Logic.xlsx` (hoja `OutboundStaging`: celdas
   (3,29)..(27,29)). El `config.json` canonico manda 100% a la zona 1 e
   ignora las otras 6 -- de ahi el makespan +55% de MEJ-4.
3. **¿Que es "ruta" hoy?** Nada: sin `staging_id` explicito, se elige al azar
   por `outbound_staging_distribution` (`_seleccionar_staging_id`), sin
   ninguna relacion con el contenido del pedido.

**Hallazgo adicional (el eslabon perdido real):** aunque un pedido termine en
la zona correcta, el CAMION no lo sabia -- `OutboundProcess` tomaba pallets
FIFO de una unica cola global (`almacen.staged_pallets`), sin filtrar por
`staging_id`, mezclando pedidos de zonas/rutas distintas en un mismo camion.
`staging_id` solo afectaba a que celda camina el operario (colisiones), sin
ninguna conexion con el despacho.

### Plan en 3 opciones (presentado y decidido con el Director, 2026-07-05)
- **Opcion A (HECHA)**: activar la infraestructura existente -- usar
  `staging_id` como "numero de ruta" (ya en el esquema) + arreglar
  `OutboundProcess` para que cada camion sirva una sola zona a la vez.
- **Opcion B (HECHA)**: agregar campo `destino` al pedido + tabla
  `destino -> staging_id` en config (mismo patron que `work_area_equipment`).
- Opcion C (clustering geografico automatico) — no elegida; requiere datos de
  geolocalizacion de clientes que hoy no existen. Queda como upgrade futuro
  si el negocio lo necesita.

### Opcion A — HECHO 2026-07-05
`OutboundProcess.run()` (`outbound.py`): el pallet mas antiguo en
`staged_pallets` (FIFO global) define la zona que sirve el camion; solo se
cargan pallets de ESA zona (hasta `truck_capacity`). Los pallets de otras
zonas quedan en cola y se sirven cuando les toque ser los mas antiguos (sin
inanicion). Eventos `truck_arrived`/`truck_departed` ahora incluyen
`staging_id`. Sin cambio al baseline (el escenario canonico tiene
`outbound.enabled: false`, el codigo queda dormido). Validado: 3 tests nuevos
(`tests/unit/test_outbound_staging_zonas.py`, confirmados como regresion real
-- fallan sin el fix) + corrida real con `outbound.enabled: true` y
distribucion en 4 zonas (`TRUCK-N despacha M pallets de staging=X`, rotando
correctamente entre zonas con backlog).

### Opcion B — HECHO 2026-07-05
Campo `ParsedOrder.destino` (opcional, parseado de JSON/CSV: `"destino":
"TIENDA_NORTE"` o columna CSV `destino`). Config nuevo `destino_staging_map`
(`{"TIENDA_NORTE": 1, ...}`, mismo patron explicito que `work_area_equipment`),
registrado en `config_schema.py` y validado en `web_prototype/config_manager.py`
(debe ser dict, valores enteros 1-7). Nuevo metodo
`AlmacenMejorado._resolver_staging_id(order)`: precedencia `staging_id`
explicito > `destino` mapeado > fallback aleatorio de siempre (sin regresion
para pedidos sin destino). Solo aplica a `DeterministicOrderStrategy` (modo
archivo) -- el modo Stochastic no tiene "pedidos reales" con destino.
Validado: 6 tests nuevos (`tests/unit/test_init6_destino_staging.py`:
precedencia, resolucion, fallback, parseo JSON/CSV) + 3 tests de validacion
web (`test_cf07..09`) + corrida real end-to-end (30 pedidos, 3 destinos ->
3 zonas, camiones respetando cada zona). Suite: 104 passed. Gate PASS sin
cambio de baseline.

### Que NO hacer
No parchar con `discharge_time` suelto como sustituto de una Opcion C futura
-- eso seria ajustar velocidad sin resolver clustering geografico real.

### Diferido (Opcion C, si el negocio lo necesita)
Clustering geografico automatico de destinos -> staging_id. Requiere:
coordenadas reales de destino por pedido (hoy no existen), algoritmo de
clustering (ej. k-means) corrido al inicio de cada corrida/wave, y decidir si
las 7 zonas fisicas son suficientes o hace falta redefinir el layout. No
estimado -- depende de si el negocio va a tener datos reales de geolocalizacion.

---

## BK-02 — FIFO Estricto en UI

**Estado:** EN REPENSAR (nota del Director, 2026-06-15): no exponer todavia.
Hay que redefinir que deberia hacer FIFO operacionalmente antes de mostrarlo
en el configurador. El motor ya lo implementa correctamente
(`dispatcher._estrategia_fifo`, string `"FIFO Estricto"`); es una decision de
diseño de uso, no un problema tecnico.

---

## `_legacy/web_dashboard/` — decision pendiente

Puerto 8001, app FastAPI independiente con tabla de WorkOrders. Huerfana y
rota (apunta a un `.jsonl` de prueba que ya no existe). Su funcion ya la cubre
el panel de WorkOrders del viewer web vigente. Recomendacion de Cerebellum:
eliminar (revisar 2 min por si hay alguna idea de presentacion que rescatar
primero). El Director quiere revisarla antes de decidir.

---

## INIT-3 v3 — capacidades por agente en el optimizador

Unica pieza diferida que queda de INIT-3 (la UI web se completo en v2, ver
CHANGELOG 2026-07-05): **capacidades por tipo de agente en el espacio de
busqueda**. Requiere que el optimizador arme un `agent_types` explicito por
trial en vez de usar el fallback legacy (`num_operarios_terrestres`/
`num_montacargas`), ya que la capacidad esta hardcodeada en el fallback de
`operators.py` (150 ground / 1000 forklift, no leida de config). Cambio de
representacion mas grande, no un fix.

---

## INIT-4b — KPI de SLA vencido en el reporte/visor

**Origen:** unico punto diferido de INIT-4 (ver CHANGELOG 2026-06-29).
`WorkOrder.due_time` existe pero no se mide/muestra cuantos pedidos incumplen
su SLA. Reusar el patron de INIT-5: al completar cada pedido comparar tiempo
de completado vs `due_time`; agregar resumen (a tiempo/vencidos/% cumplimiento)
en `core/replay_utils.py`, metadata del `.jsonl`, API, visor y hoja Excel.

---

*Para retomar cualquier item cerrado, buscar su commit en `docs/CHANGELOG.md`
o `git log --oneline --grep=<ITEM>`.*
