# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-07-05 · Responsable: Cerebellum

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| INIT-6 — Staging multi-destino por ruta | PENDIENTE | Alta | Alto | Necesita decisiones de alcance del Director (ver abajo) |
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| `_legacy/web_dashboard/` — conservar/reparar/eliminar | PENDIENTE DECISION | Baja | Depende | Director quiere revisarla primero |
| MEJ-2 v2 — KPI de nivel de servicio en experiment runner | DIFERIDO | Media | Bajo | Ninguno, listo para tomar |
| INIT-3 v2 — capacidades/zonas en el optimizador + UI web | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-4b — KPI de SLA vencido en reporte/visor | PENDIENTE | Baja | Bajo | Ninguno, listo para tomar |

---

## INIT-6 — Staging multi-destino por ruta

**Origen:** el hallazgo de makespan +55% de MEJ-4 (ver CHANGELOG 2026-07-04)
fue redefinido por el Director el 2026-07-05: no es un problema de tuning de
congestion, es que el dominio no modela destino ni ruta de entrega.

### El problema real
En un almacen real, cada pedido tiene un destino (tienda o domicilio de
cliente) y el staging deberia consolidar por grupo de ruta (tiendas cercanas
para un camion, domicilios por zona de reparto) — no volcar todo a una celda
unica indiferenciada. Sin esto, cualquier metrica de staging mide un cuello de
botella artificial, no el real.

### Preguntas de alcance que el Director debe contestar ANTES de planificar
1. ¿Existe ya un campo de destino (tienda/domicilio/direccion) en el esquema
   de pedidos de entrada, o hay que incorporarlo?
2. En `outbound.py`, ¿como se define hoy el/los staging? ¿Hay mas de una zona
   fisica dibujada en `layouts/WH1.tmx`, o solo una?
3. ¿Que se entiende operativamente por "ruta"? ¿Agrupamiento estatico
   (config) o clustering geografico calculado por corrida?

### Que NO hacer
No parchar con `outbound_staging_distribution` o `discharge_time` sueltos —
son curitas sobre un modelo sin concepto de destino/ruta. Solo tienen sentido
despues de decidir el diseño de consolidacion multi-staging.

**Estimacion:** Alto. Toca esquema de pedidos, `outbound.py`, posiblemente el
layout TMX. Necesita su propia sesion de diseño antes de estimar en detalle.

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

## MEJ-2 v2 — KPI de nivel de servicio en el experiment runner

Extender `export_optimization_metrics()` (`event_generator.py`) con
`service_level` (fill-rate/backorders, mismo patron que INIT-5:
`core/replay_utils.build_service_level_summary()`), y agregar la clave a
`ALL_KPI_KEYS` en `scripts/experiment_runner.py`. Diferido en MEJ-2 v1 porque
toca el motor (nuevo campo en metadata del `.jsonl`) y dispara el gate/baseline;
v1 se mantuvo deliberadamente sin riesgo. Cuando se retome: actualizar baseline
con `--update-baseline --yes`.

---

## INIT-3 v2 — capacidades por agente + prioridades de zona + UI web

Dos piezas diferidas de INIT-3 (ver CHANGELOG 2026-07-05):
1. **Capacidades por tipo de agente en el espacio de busqueda del optimizador**:
   requiere que el optimizador arme un `agent_types` explicito por trial en
   vez de usar el fallback legacy (`num_operarios_terrestres`/`num_montacargas`),
   ya que la capacidad esta hardcodeada en el fallback de `operators.py` (150
   ground / 1000 forklift, no leida de config). Cambio de representacion mas
   grande, no un fix.
2. **UI minima en el configurador** para lanzar/ver el estudio de optimizacion
   desde el navegador. Los 3 endpoints (`/api/optimization/start|status|stop`)
   ya funcionan via HTTP directo (curl/Postman); falta el panel visual.

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
