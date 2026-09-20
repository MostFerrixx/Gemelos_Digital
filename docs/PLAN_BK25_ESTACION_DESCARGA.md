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

- **En curso: F1.a** — que la base de datos guarde TODAS las celdas de cada
  carril (hoy guarda una sola por zona).
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
| **F1.a** | La base guarda todas las celdas de cada carril (hoy solo una por zona) | EN CURSO |
| **F1.b** | Adoptar `WH1 v3`: reimportar el Excel v3, estacionamientos y muelles en el mapa, canonico y baseline nuevos | Siguiente |
| **F1.c** | Estacion con turno: puestos por columna, entrada, fila, salidas de un sentido, pulmon; deduccion automatica y validacion; metricas | Siguiente |
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
