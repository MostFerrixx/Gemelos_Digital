# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-09-07 · Responsable: Cerebellum

*(BK-06 CERRADA el 2026-09-07 -> CHANGELOG. De ella salieron BK-07, BK-08 y
BK-09, abiertos abajo. INIT-7 INBOUND completa F0-F5 el 2026-07-10; INIT-8
TIEMPOS completa F1-F4 el 2026-07-11 con los 4 hallazgos AUD8-1..4 aplicados
el 2026-07-12 -> todo en CHANGELOG.)*

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| BK-07 — areas mixtas (varios tipos de equipo por area) | ABIERTO (2026-07-25) | Media | Medio | Confirmar con el cliente si existen areas mixtas |
| BK-08 — confirmar work_area_equipment con el almacen real | ABIERTO (2026-07-25) | **Alta** (supuesto activo) | Trivial (config) | Lectura del almacen real (Director/cliente) |
| BK-09 — flota 2+2 sub-dimensionada (hallazgo de negocio) | ABIERTO (2026-07-25) | Media | Trivial (config) | Decision de negocio del Director |
| BK-05 — guard de flota vacia bloquea guardar el canonico desde la UI | ABIERTO (hallazgo 2026-07-12) | Baja-Media (UX) | ~1 h (opcion a) | DESBLOQUEADO: opcion (b) ya viable tras BK-06 |
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| INIT-3 v3 — capacidades por agente en el optimizador | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-6 Opcion C — clustering geografico de destinos | DIFERIDO | Baja | Alto (no estimado) | Requiere datos reales de geolocalizacion de clientes |
| Distribucion real de `outbound_staging_distribution` en config canonico | PENDIENTE DECISION | -- | Trivial (config) | Decision de negocio del Director, no un bug |

---

## BK-07 — areas mixtas (varios tipos de equipo por area)

**Hallazgo 2026-07-25 (BK-06 F1).** Hoy `work_area_equipment` es
`Dict[str, str]`: **un solo tipo de equipo por area**. Si en la operacion real
un area la atienden AMBOS tipos (p. ej. un rack bajo que puede trabajar tanto
un terrestre como un montacargas), el modelo actual no lo puede expresar: hay
que elegir uno y el otro queda excluido.

Propuesta robusta (no implementada): admitir `Dict[str, str | List[str]]` —
retrocompatible, un string sigue significando "solo ese tipo". La capacidad de
dimensionado del area ya esta preparada: `core.fleet.capacidades_por_area` toma
el **minimo** de los tipos compatibles, que es exactamente lo que corresponde
en un area mixta (toda WO debe caber en el equipo mas chico que pueda tomarla).
Habria que tocar: `work_areas.effective_work_area_priorities` (aceptar lista),
el validador web, `fleet-manager.js` y la UI del tab Flota.

Bloqueo: confirmar con el cliente si existen areas mixtas (ver BK-08). No
meterlo en BK-06 (decision del Director).

---

## BK-08 — confirmar `work_area_equipment` con el almacen real

**Supuesto activo, no verificado (2026-07-25).** Todo BK-06 asume que
`Area_High` y `Area_Special` son 100% de montacargas y `Area_Ground` 100%
terrestre, tal como dice el canonico. El Director no tiene todavia la lectura
del almacen real.

Impacto si el supuesto es falso: los numeros de BK-06 (makespan, reparto de
carga) cambian. **No requiere codigo**: se corrige editando el mapa en el tab
Flota — salvo que existan areas mixtas, que necesitan BK-07.

Accion: confirmar con el cliente que equipo atiende cada area fisicamente.

---

## BK-09 — la flota 2+2 esta sub-dimensionada (hallazgo de negocio)

**Medido en BK-06 F4 (2026-07-25), con seed 42 y el resto de la config igual.**
Variando SOLO `num_montacargas` sobre el modelo ya corregido:

| Flota | Makespan | vs baseline historico (7440 s) |
|---|---|---|
| 2+2 (canonico) | 8783 s | +18,1% |
| 2+3 | 6042 s | **-18,8%** |
| 2+4 | 4844 s | **-34,9%** |
| 2+5 | 4966 s | -33,3% (peor que 2+4: congestion) |

Con un solo montacargas mas, el modelo realista ya supera el baseline
historico; el optimo esta en 2+4. Es una decision de negocio del Director
(comprar/asignar equipos), no un bug. Cambiar el canonico rompe el baseline
intencionalmente. Insumo natural para el optimizador (INIT-3).

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

**ACTUALIZACION 2026-07-25 (a): la opcion (b) estaba BLOQUEADA por BK-06.** Se
intento y se midio: migrar el canonico a `agent_types` explicito sobre la
semantica de entonces degradaba la simulacion (-40 WOs, +6,9% de makespan,
9.341 errores de dispatcher). No era una migracion cosmetica.

**ACTUALIZACION 2026-07-25 (b): DESBLOQUEADO.** Con BK-06 F1-F3 aplicado, el
canonico y su equivalente con `agent_types` explicito dan resultados
IDENTICOS (626 WOs / 8783 s / 0 errores en ambos) — es la prueba de
equivalencia de `PLAN_BK06_CAPACIDAD_AREA.md` seccion 9.6. La opcion (b) ya es
un no-op de comportamiento. La (a) sigue siendo la mas barata si solo se
quiere destrabar la UX.

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
`num_montacargas`).

**ACTUALIZACION 2026-09-07: MUCHO MAS BARATO tras BK-06.** El bloqueo de fondo
era que la capacidad estaba HARDCODEADA en el fallback de `operators.py` (150 /
1000, no leida de config). Ya no: la flota se resuelve en
`core.fleet.resolver_flota` y las capacidades salen del bloque configurable
`fleet_defaults`. Ademas quedo probado que el canonico y su equivalente con
`agent_types` explicito dan resultados IDENTICOS, asi que el optimizador puede
generar flotas explicitas sin cambiar el comportamiento base. Sigue siendo un
cambio de representacion en `src/tools/optimizer.py`, pero ya no arrastra un
fix de motor. Insumo natural: BK-09 (la flota 2+2 esta sub-dimensionada; el
optimizador deberia encontrarlo solo).

---

*Para retomar cualquier item cerrado, buscar su commit en `docs/CHANGELOG.md`
o `git log --oneline --grep=<ITEM>`.*
