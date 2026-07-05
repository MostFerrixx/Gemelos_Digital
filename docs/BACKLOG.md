# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-07-05 · Responsable: Cerebellum

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| MEJ-BOTTLENECK — panel de cuellos de botella (SIGUIENTE, aprobada) | APROBADA | Alta | Medio | Ninguno -- revisar primero reportes CSV/JSON existentes (pedido del Director) |
| MEJ-SLA-OPT — optimizador penaliza SLA vencido (replanteada) | APROBADA | Media | Bajo-Medio | Despues de MEJ-BOTTLENECK (orden acordado 3->1->2) |
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| INIT-3 v3 — capacidades por agente en el optimizador | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-6 Opcion C — clustering geografico de destinos | DIFERIDO | Baja | Alto (no estimado) | Requiere datos reales de geolocalizacion de clientes |
| Distribucion real de `outbound_staging_distribution` en config canonico | PENDIENTE DECISION | -- | Trivial (config) | Decision de negocio del Director, no un bug |

---

## MEJ-BOTTLENECK — Panel de cuellos de botella (aprobada, SIGUIENTE)

**Origen:** terna de mejoras propuesta por Cerebellum y aprobada por el
Director (2026-07-05), orden acordado: comparador A/B web (HECHO) -> esta ->
MEJ-SLA-OPT.

El motor YA calcula por corrida los datos de cuellos de botella (hotspots de
congestion con celda y max concurrentes en `congestion_report_*.json`,
metricas del planner en `timewindow_shadow_report_*.json`, esperas de
slot/carril y ocupacion pico por zona en `outbound_metrics`) pero quedan
enterrados en JSONs sueltos por corrida que nadie consolida. Consolidarlos en
un lugar visible: hoja Excel y/o panel del visor web.

**Pedido explicito del Director:** ANTES de construir, revisar los
reportes/archivos que ya se generan por corrida (CSV/JSON/Excel existentes) y
decidir si se mejoran los existentes o se rehace y se eliminan los viejos.
No duplicar.

---

## MEJ-SLA-OPT — El optimizador penaliza SLA vencido (replanteada)

**Origen:** propuesta 2 de la terna, REPLANTEADA tras la observacion correcta
del Director: el fill-rate NO depende de la config (la asignacion de stock
ocurre antes de simular, invariante a flota/estrategia). Lo que SI depende es
el **SLA**: con `due_time` en los pedidos (INIT-4 C2), una config mas lenta
completa igual pero VENCIDA. Hoy `SimulationOptimizer.calculate_score` solo
mira throughput/costo/WOs fallidas -- podria recomendar una config "optima"
que hace vencer pedidos sin que nadie lo note. Fix: incorporar
`sla_summary.orders_late` (ya exportado por INIT-4b via
`export_optimization_metrics`... verificar si esta; si no, agregarlo como se
hizo con `fill_rate_pct`) como penalizacion en el score. Solo aplica cuando
los pedidos traen due_time; sin SLA el score queda identico (no-regresion).

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

## INIT-3 v3 — capacidades por agente en el optimizador

Unica pieza diferida que queda de INIT-3 (la UI web se completo en v2, ver
CHANGELOG 2026-07-05): **capacidades por tipo de agente en el espacio de
busqueda**. Requiere que el optimizador arme un `agent_types` explicito por
trial en vez de usar el fallback legacy (`num_operarios_terrestres`/
`num_montacargas`), ya que la capacidad esta hardcodeada en el fallback de
`operators.py` (150 ground / 1000 forklift, no leida de config). Cambio de
representacion mas grande, no un fix.

---

*Para retomar cualquier item cerrado, buscar su commit en `docs/CHANGELOG.md`
o `git log --oneline --grep=<ITEM>`.*
