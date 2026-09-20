# PLAN BK-25 — Estacion de descarga con turno (QA H-15 / H-27)

> **Documento vivo.** Se actualiza en cada sesion: la seccion 1 dice que se esta
> haciendo ahora, la 3 registra cada decision con su porque (incluida la opcion
> descartada) y la 5 lleva el registro de avance. Analisis de fondo:
> `docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md` y
> `docs/PROPUESTA_DISENO_CEDER_EL_PASO.md` (consultor externo, Fable 5.1).
> Hallazgos del QA que lo originaron: `docs/PLAN_QA_CONFIGURACION_WEB.md` (H-15,
> H-27) y `docs/BACKLOG.md` (BK-25, BK-30, BK-31).

**Ultima actualizacion:** 2026-09-19

## 1. Estado actual

- **En curso: F1.c2** — que las salidas sean de un solo sentido tambien para
  los buscadores de rutas.
- Hecho: **F1.a**, la base guarda todas las celdas de cada carril.
- Hecho: **F0** (el que espera ocupa una sola celda) en la rama
  `fix/bk25-estacion-descarga`, medido, sin integrar a `main` todavia.
- Hecho: **mapa WH1 v3** (anden de 3 filas) y su Excel, commit `73439bd`.

## 2. El problema en una linea

Cuando varios operarios llegan a descargar a la misma zona, los que esperan se
paran en las celdas por donde el que descarga tiene que salir; nadie se mueve,
el motor se rinde a los 10 minutos simulados y termina pisando a otro operario
(fisica imposible). Pasa tambien con la flota canonica 2+2.

## 3. Decisiones tomadas (y que se descarto)

### Del Director

| # | Decision | Por que esta, y que se descarto |
|---|---|---|
| D1 | Corregir la sobre-reserva del origen (el que espera ocupaba dos celdas) | Era un bug real del planificador, introducido por BK-15. Se descarto dejarlo: rechazaba el 92-95% de los planes validos. Mueve la corrida de referencia, aprobado |
| D2 | **2 puestos por carril**, uno por columna | El carril fisico mide 2 celdas de ancho. Se descarto dejar 1 (lo de hoy): deja media zona sin usar |
| Salidas | Cada puesto sale por **su** costado: el de la columna izquierda por la izquierda, el de la derecha por la derecha. De un solo sentido y **prohibido detenerse** | Idea del Director. Garantiza por diseno que el que descarga siempre tenga salida. Se descarto "salir por donde se entra": reproduce el atasco |
| D10 | **Anden de 3 filas** delante de los carriles, en un mapa nuevo `WH1 v3` | Con las salidas de un solo sentido, TODAS las columnas entre carriles quedan ocupadas: no queda donde esperar salvo un rincon lejano. Se descarto (a) esperar en los pasillos laterales (son las salidas), (b) pulmon unico a la izquierda (el del carril 7 queda a 28 celdas), (c) filas traseras (incomunicadas por el sentido unico) |
| D-A1 | Implementar la cesion por solicitud, apagada por defecto | Aprobada. Se enciende solo si las mediciones con flota grande la respaldan |
| D-A2 | Ceden los ociosos **y** los que esperan turno; nunca quien pickea, descarga o ejecuta un plan | Realismo: una persona que espera se corre; una que esta levantando un pallet, no |
| D-A3 | Las 3 filas detras de los carriles quedan reservadas como anden de carga | Para no rehacerlo cuando se modele al cargador o la maniobra del camion |
| D-A5 | Adoptar `WH1 v3` como mapa de trabajo, junto con F1 | Probar la estacion sobre la geometria definitiva y no dos veces |
| Orden | Estacion con turno -> medir -> cesion por solicitud -> medir, con **mucha flota** | El Director ya vio colapsar un intento anterior de cesion; se mide antes de encenderla |

### Del asistente (tecnicas, sin decision de negocio)

| Tema | Decision | Por que |
|---|---|---|
| Cesion | Protocolo local de solicitud con reserva blanda, no un resolutor MAPF global (push-and-swap, PIBT, RHCR) | Los resolutores reemplazarian al planificador espacio-temporal actual y no admiten estadias ni tiempo continuo |
| Anti-caos | Cadena de profundidad 1: el que cede nunca pide a un tercero; el que tiene tarea nunca cede; tope de cesiones seguidas con aviso | Es exactamente el colapso que el Director vio antes |
| Baseline | F0 no se integra solo a `main`: va junto con F1 | F0 solo mejora el canonico pero alarga la corrida 4+4 (deja de "hacer trampa"); el baseline se regenera una vez |
| Mapa | `WH1 v3` es copia; `WH1 v2` y el Excel v2 quedan intactos | Reversible |

### Pendientes del Director

| # | Pregunta | Recomendacion |
|---|---|---|
| D3 | Con camiones activos, un pallet por linea de pedido o un contenedor por pedido | Contenedor por pedido |
| D4 | Cuantos esperan en la fila de cada carril antes de ir al pulmon | 1 por puesto; con el anden de 3 filas cabe comodo |
| D5 | Pasillos de picking de un solo sentido | Dejar preparado, no activar |
| D6 | Que hace el que lleva 10 minutos trabado | Retroceder y avisar; nunca pisar |
| D7 | Formato de la regla en la configuracion (flecha o rectangulo) | Flecha |
| D8 | Mapa sin salida posible | La web bloquea y explica; consola corre en modo degradado con aviso |
| D9 / D-A6 | Reparto real entre los 7 muelles, o consolidacion por tienda/ruta | Con destinos reales, consolidar (ya existe `destino_staging_map`); sin ellos, repartir |
| D-A4 | Ediciones opcionales del mapa (pulmon simetrico a la derecha) | Despues de medir con los 7 carriles cargados |

## 4. Fases, en orden de prioridad

| Fase | Que incluye | Estado |
|---|---|---|
| **F0** | El que espera ocupa una sola celda (sobre-reserva del origen) | HECHO, en rama, sin integrar |
| **F1.a** | La base guarda todas las celdas de cada carril | HECHO (`442bc7e`), gate PASS |
| **F1.b** | Datos del v3 importables y medibles sin tocar los de produccion (`database_file` configurable) | HECHO; el cambio del canonico queda para F1.d |
| **F1.c** | Estacion con turno: puestos por columna, entrada, fila y salida por su costado; deduccion automatica y avisos | HECHO (`a78a98b`), apagada por defecto |
| **F1.c2** | Que la salida sea de un solo sentido y prohibido detenerse (reglas de circulacion en los dos buscadores de rutas) | EN CURSO |
| **F1.d** | Medicion con flota grande (4+4 y 8+8, todo a un carril y con reparto) | Siguiente |
| **F2** | Cesion por solicitud (apagada por defecto) + medicion con flota grande | Despues de F1 |
| **F3** | Muelle de salida sobre la misma estacion: carriles reales, sin saltos, unidad de staging segun D3 | Despues de F2 |
| **F4** | Reglas de circulacion editables desde la web + capa del visor que las muestra | Despues de F3 |
| **F5** | Pasillos de un solo sentido (D5), solo si el Director lo pide | Diferida |

Criterio de exito de cada fase: 0 co-ocupaciones fuera del arranque, 0
rendiciones del planificador, y que la flota 4+4 rinda claramente mas que la
2+2. Si un escenario no da 0, la fase no se cierra.

## 5. Registro de avance

- **2026-09-19** — F0 hecho y medido (`be65b04`). Canonico con 5 semillas:
  planes rechazados de miles a 0, rendiciones a 0, duracion igual o mejor.
  Flota 4+4: 7.178 -> 20.578 s (menos atajos imposibles, mas atasco real);
  por eso F0 no se integra solo.
- **2026-09-19** — Mapa `WH1 v3` (30x43, anden de 3 filas, carriles en las
  filas 30-39) y `Warehouse_Logic_v3.xlsx` (140 celdas de carril corridas +
  hojas SkuCatalog e InboundDocks que faltaban en el v2). Commit `73439bd`.
- **2026-09-19** — Al probar la importacion del Excel v3 aparece el problema
  de F1.a: `staging_areas` tiene clave primaria `staging_id`, asi que
  `INSERT OR REPLACE` deja una sola celda por zona (la ultima del carril).
- **2026-09-19** — F1.a hecha (`442bc7e`): clave primaria (zona, x, y),
  el importador inserta todas las celdas, las bases viejas se migran solas al
  importar y el ancla de cada zona es su primera celda (el frente del carril).
  Verificado con los tres casos (Excel v3 en base nueva, Excel canonico, y
  Excel v3 sobre una base con la tabla vieja). Gate PASS aislado de F0: el
  cambio no altera el comportamiento del motor. +3 tests (320 en total).
  DECISION de orden: el canonico y el baseline se cambian al FINAL de F1, con
  las mediciones hechas, para no regenerar el baseline dos veces.
- **2026-09-19** — F1.c hecha (`a78a98b`): modulo `stations.py` que deduce
  del mapa los puestos (uno por columna del carril), la entrada por el frente,
  la salida por su costado y la fila, y reparte los turnos; `operators` pide
  turno antes de descargar, espera en la fila si no hay puesto y suelta el
  turno recien cuando sale fisicamente. Verificado sobre el mapa v3 real
  (7 carriles, 14 puestos, entradas en la fila 29, salidas laterales, sin
  avisos) y en corrida canonica con semilla 42 (todas las tareas terminan,
  ningun turno queda tomado, sin co-ocupaciones en las celdas de descarga).
  **Apagada por defecto**: gate byte-identico verificado aparte de F0.
  +8 tests (328 en total). Falta F1.c2: que las salidas sean de un solo
  sentido tambien para los buscadores de rutas.
- **2026-09-19** — F1.b: la base de datos pasa a ser configurable
  (`database_file`); estaba fija en el codigo y no se podia correr con otros
  datos maestros sin pisar los de produccion. Se importo el Excel v3 a
  `warehouse_v3.db` (7 zonas, 140 celdas, 50 SKU) y se comprobo que los
  estacionamientos (config) y los muelles (Excel) no dependen de las celdas
  pintadas en el mapa: el v3 no pierde ninguna funcion.
- **2026-09-19** — **F1.d (primera medicion), mapa v3, semilla 42, todo al
  carril 1:**

  | Escenario | Duracion | Co-ocupaciones | Rendiciones | Esperas de replanificacion |
  |---|---|---|---|---|
  | 2+2 sin estacion | 9.145 s | 1 (arranque) | 0 | 0 |
  | 2+2 con estacion | 9.124 s | 1 (arranque) | 0 | 0 |
  | 4+4 sin estacion | 23.499 s | 19 | 16 | 39.827 |
  | **4+4 con estacion** | **5.249 s** | **2** | **1** | **3.627** |

  La flota 4+4 pasa a rendir mas que la 2+2 (5.249 s contra 9.124 s), que era
  el criterio de exito. Faltan 2 co-ocupaciones y 1 rendicion para llegar a 0:
  se atacan en F1.c2 (salidas de un solo sentido).
