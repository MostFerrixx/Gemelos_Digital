# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-07-05 · Responsable: Cerebellum

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| `_legacy/web_dashboard/` — conservar/reparar/eliminar | PENDIENTE DECISION | Baja | Depende | Director quiere revisarla primero |
| INIT-3 v3 — capacidades por agente en el optimizador | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-4b — KPI de SLA vencido en reporte/visor | PENDIENTE | Baja | Bajo | Ninguno, listo para tomar |
| INIT-6 Opcion C — clustering geografico de destinos | DIFERIDO | Baja | Alto (no estimado) | Requiere datos reales de geolocalizacion de clientes |
| Distribucion real de `outbound_staging_distribution` en config canonico | PENDIENTE DECISION | -- | Trivial (config) | Decision de negocio del Director, no un bug |

---

## INIT-6 Opcion C — clustering geografico automatico

**Contexto:** INIT-6 (Opciones A+B, staging por zona real + destino->staging_id)
esta HECHO -- ver `docs/CHANGELOG.md` 2026-07-05. Esto es solo la extension
opcional que quedo afuera.

Clustering geografico automatico de destinos -> staging_id. Requiere:
coordenadas reales de destino por pedido (hoy no existen), algoritmo de
clustering (ej. k-means) corrido al inicio de cada corrida/wave, y decidir si
las 7 zonas fisicas son suficientes o hace falta redefinir el layout. No
estimado -- depende de si el negocio va a tener datos reales de geolocalizacion.

---

## Distribucion real de `outbound_staging_distribution`

Ahora que el camion respeta la zona (INIT-6 Opcion A), tiene sentido repartir
el trafico entre las 7 zonas reales en vez de mandar 100% a la zona 1 (asi
esta el `config.json` canonico hoy). Es una decision de tuning de negocio del
Director, no un bug — cambiarla intencionalmente rompe el baseline byte-identico
y requeriria `--update-baseline --yes`.

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
