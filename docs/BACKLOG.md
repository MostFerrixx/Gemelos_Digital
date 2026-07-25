# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-07-12 · Responsable: Cerebellum

*(INIT-7 INBOUND completa F0-F5 el 2026-07-10; INIT-8 TIEMPOS completa F1-F4
el 2026-07-11 -> ambas en CHANGELOG. Auditoria de INIT-8 el 2026-07-11:
los 4 hallazgos AUD8-1..4 quedaron APLICADOS el 2026-07-12, ver CHANGELOG.)*

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| BK-06 — capacidad por area vs. flota heterogenea (BUG de motor) | PLAN PROPUESTO (2026-07-25) | **Alta** | Medio-Alto | Aprobacion del plan por el Director |
| BK-05 — guard de flota vacia bloquea guardar el canonico desde la UI | ABIERTO (hallazgo 2026-07-12) | Baja-Media (UX) | ~1 h (opcion a) | Opcion (b) BLOQUEADA por BK-06 |
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| INIT-3 v3 — capacidades por agente en el optimizador | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-6 Opcion C — clustering geografico de destinos | DIFERIDO | Baja | Alto (no estimado) | Requiere datos reales de geolocalizacion de clientes |
| Distribucion real de `outbound_staging_distribution` en config canonico | PENDIENTE DECISION | -- | Trivial (config) | Decision de negocio del Director, no un bug |

---

## BK-06 — capacidad por area vs. flota heterogenea (BUG de motor)

**Hallazgo 2026-07-25, al intentar BK-05 opcion (b).** Plan completo con RCA,
alternativas de semantica y validacion: `docs/PLAN_BK06_CAPACIDAD_AREA.md`.

La clave `capacity` de `agent_types` alimenta dos cosas distintas: la capacidad
fisica del operario y el divisor que dimensiona WOs por area
(`warehouse._validar_y_ajustar_cantidad`). Con el canonico (`agent_types: []`)
la segunda via queda ciega: `operator_capacities = {}` y todo se dimensiona a
150, aunque los montacargas se instancien con capacidad 1000 (verificado en la
corrida canonica). Las WOs de `Area_High`/`Area_Special` se dimensionan a 1/6,6
de la capacidad real del equipo que las mueve; 40 WOs divididas en el canonico.

Poblar `agent_types` de forma ingenua NO lo arregla: rompe la simulacion. El
`work_area_priorities` del ground incluye `Area_High`/`Area_Special`, asi que
recibe WOs dimensionadas para montacargas (1000) que nunca puede levantar (150)
-> `_seleccionar_primera_wo` devuelve la WO oversized y
`_construir_tour_por_secuencia` la rechaza, en bucle.

**Medicion (2 corridas, seed 42):** canonico 666 WOs / 7440 s / 0 errores vs.
`agent_types` ingenuo 626 WOs (-40) / 7955 s (+6,9%) / **9.341**
`[DISPATCHER ERROR]` sobre 5 WOs huerfanas.

**Causa raiz:** `work_area_equipment` ya declara que equipo sirve cada area
(MEJ-3 QA-3) y lo consultan 3 capas (event_generator, config_manager,
fleet-manager.js), pero **el hot-path de simulacion no lo mira**: el motor
decide compatibilidad solo por `work_area_priorities`, que puede contradecirlo.

Rompe el baseline byte-identico de forma intencional (no hay version que lo
preserve). Bloquea BK-05 opcion (b) e INIT-3 v3.

---

## BK-05 — guard de flota vacia al guardar el canonico desde la UI

**Hallazgo colateral de la tarea de UI de tiempos (2026-07-12), PRE-EXISTENTE.**
El config canonico usa `agent_types: []` + los contadores legacy
(`num_operarios_terrestres`/`num_montacargas`) como fallback de flota. La UI
de Flota solo representa GRUPOS (`agent_types`), asi que al serializar el
canonico produce `agent_types: []` y el validador web lo rechaza ("flota
vacia") aunque el motor correria perfectamente con el fallback. Consecuencia:
NO se puede guardar el canonico desde el configurador sin antes crear grupos.
Opciones: (a) el validador acepta flota vacia si los contadores legacy > 0;
(b) la UI materializa los contadores como grupos visibles al cargar (y el
canonico migra a agent_types explicito = cambio de baseline); (c) dejarlo y
documentar. Decision de diseno del Director.

**ACTUALIZACION 2026-07-25: la opcion (b) esta BLOQUEADA por BK-06.** Se
intento y se midio: migrar el canonico a `agent_types` explicito sobre la
semantica actual degrada la simulacion (-40 WOs, +6,9% de makespan, 9.341
errores de dispatcher). No es una migracion cosmetica. La opcion (a) sigue
disponible y NO depende de BK-06.

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
