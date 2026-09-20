# ADENDA — Ceder el paso, donde esperar y puestos por carril (WH1 v2)

> Segunda consulta del Director sobre `docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md`.
> Consultor externo (Fable 5.1), 2026-09-19. Solo analisis; no se toco codigo.
> Mapa de trabajo: `layouts/WH1 v2.tmx` (30x42), verificado por mi con
> `LayoutManager(..., headless=True)` y leyendo el `.tmx`, el `.tsx` y
> `layouts/Warehouse_Logic_v2.xlsx` (seccion 1).

---

## 0. Resumen ejecutivo (para el Director, sin jerga)

**El mapa nuevo resuelve el problema de espacio.** WH1 v2 tiene un anden de
muelle de 13 filas debajo de los racks: 7 carriles de descarga de 2 columnas
por 10 de fondo, columnas libres de 2 celdas entre carril y carril, un bloque
libre de 3 columnas a la izquierda, 1 columna a la derecha y 3 filas libres
detras. La franja de circulacion delante de los carriles tiene 2 filas. Con
eso, la estacion con turno de la propuesta anterior se arma sin inventar
nada: cada carril son 2 puestos (uno por columna), se entra por el frente y
—como pidio el Director— la columna izquierda sale por la izquierda y la
derecha por la derecha, usando las columnas libres como salidas de un solo
sentido. Nada del mapa hace falta editar para esto (secciones 3 y 4).

**Ceder el paso (pregunta 1).** Hoy el que espera es un mueble: reserva su
celda "para siempre" y los demas lo rodean o se traban. Propongo lo que hacen
los gestores de flota reales: la reserva del que espera es **blanda**. Cuando
otro operario con trabajo no encuentra camino (o el desvio es grande) porque
un ocioso le tapa el paso, le **pide que se corra**; el ocioso suelta su celda,
da dos o tres pasos a una celda libre que no estorbe, y el otro sigue. Reglas
que evitan que dos se corran mutuamente para siempre: **solo cede quien no
tiene trabajo** (o quien espera turno, sin perder su lugar en la fila); quien
cede **nunca pide** que otro se corra; quien se mueve con un plan **nunca
cede**; y un mismo ocioso se corre como maximo N veces seguidas y despues se
queda (con aviso). Es determinista (nada de azar, orden fijo de decisiones),
se prende con una llave de configuracion (apagada = comportamiento identico
al de hoy, el gate no cambia), y se mide con metricas nuevas: cesiones
pedidas, concedidas, rechazadas y tiempo perdido por cederse. Costo: 3 a 4
dias sobre archivos concretos (seccion 2.8). Descarte con razones las
alternativas academicas (push-and-swap, PIBT, etc.): resuelven otro problema
o exigirian reemplazar el planificador actual.

**Realismo de quien cede.** Un operario **sin trabajo** cede siempre. Uno que
**espera turno** (con o sin carga) cede si tiene a donde correrse y conserva
su turno. Uno **en medio de un pick o de una descarga** no cede: en la
realidad el otro espera esos segundos (el planificador ya lo hace). Uno **en
movimiento con plan** no cede: ya esta coordinado.

**Donde esperan los que no tienen turno (pregunta 2).** Recomiendo: fila de
**una celda por puesto** (la entrada, en la fila 28) y **pulmon en el bloque
libre izquierdo (x=0..1, filas 29..41)**, que no es paso de nadie. Las
columnas entre carriles NO sirven de pulmon: son las salidas. La franja
delantera NO sirve: es el paso principal y tiene 2 filas. Las filas 39..41
son el anden de carga (lado camion): defendible como pulmon secundario, pero
es decision del Director. La distancia pesa poco (a 0,1 s por celda, cruzar
todo el anden son 3 s; a 1 s por celda, 30 s, contra descargas de 5-60 s y
esperas de minutos); el estorbo pesa mucho. **No hace falta editar el mapa**;
si el trafico se reparte entre los 7 carriles y el perfil es "Real",
conviene agregar 2 columnas libres a la derecha para un pulmon simetrico
(edicion menor, opcional).

**Puestos y fila (pregunta 3).** 2 puestos por carril (uno por columna),
salida por su costado, fila de 1 por puesto (2 esperando frente a cada
carril), el resto al pulmon por orden de llegada. Con 4+4 y todo a la zona 1:
2 en fila + hasta 4 en el pulmon (que tiene 26 celdas).

**Consolidar o repartir (D9 corregida).** El reparto por destino ya existe
(`destino_staging_map` + campo `destino` del pedido, modo determinista). El
100% a la zona 1 del canonico viene del modo estocastico con
`outbound_staging_distribution` 1:100. Regla: con pedidos reales que traen
destino, **consolidar por destino** (un carril = un camion/ruta, es lo que
hace un muelle real; la cola que genera es real y la resuelve la estacion,
no el reparto). Sin destino (estocastico), **repartir** segun la cadencia
esperada de camiones por carril, y que el validador avise cuando un carril
recibe mas del 50% con 7 definidos.

Decisiones nuevas para el Director: 6, en la seccion 6.

---

## 1. Geometria verificada de WH1 v2

Leido de `layouts/WH1 v2.tmx` (Tiled 1.11, 30x42, una capa de baldosas, sin
capas de objetos) y `layouts/custom_warehouse_tileset.tsx` (baldosa 4 =
`type: depot`, `walkable: true`; baldosa 3 = `parking`; baldosa 5 =
`inbound`):

```
y=0..2    pasillo superior libre (3 filas)
y=3..26   racks (x=0,3,4,7,8,...,27,28) y picking (x=1,2 / 5,6 / ... / 25,26 / 29): 360 picks, iguales a WH1
y=27..28  franja delantera libre (2 filas); las bocas de pasillo dan a la fila 27
y=29..38  7 carriles 'depot' de 2 columnas x 10 filas: x=3-4, 7-8, 11-12, 15-16, 19-20, 23-24, 27-28
          columnas libres entre carriles: x=5-6, 9-10, 13-14, 17-18, 21-22, 25-26 (2 de ancho, 13 de largo)
          bloque libre izquierdo x=0..2 (3 de ancho); columna libre derecha x=29 (1 de ancho)
y=39..41  3 filas libres detras de los carriles (lado del muelle/camion)
```

Hechos que condicionan el diseno:

- **Todo el anden es transitable** (`collision_matrix` True en las filas
  27..41): los carriles no son obstaculos del mapa; los hace "privados" el
  outbound (F2.d en `warehouse.py` los marca no caminables) o, en mi
  propuesta, la estacion.
- **Las columnas libres entre carriles prolongan los pasillos de picking**:
  el pasillo x=5-6 (picks) sigue recto por x=5-6 (libre) desde la fila 27
  hasta la 41. Es la geometria ideal para "la columna derecha del carril 1
  sale por x=5 y la izquierda del carril 2 sale por x=6".
- **`layouts/Warehouse_Logic_v2.xlsx`** ya define las 20 celdas de cada
  carril en `OutboundStaging` (staging 1 = (3..4, 29..38), etc.). La base
  `warehouse.db` actual tiene **solo las anclas** (fila 29): fue migrada del
  Excel v1 (`config.json` apunta a `layouts/Warehouse_Logic.xlsx`;
  `run_migration.find_excel_file` respeta `sequence_file`). Adoptar v2 exige
  reimportar con el Excel v2 (desde la web: subir -> validar -> Aplicar).
  Con las 20 celdas en la base, `warehouse.py` las usa tal cual
  (`if len(cells) > 1: zcells = cells`), `StagingZone` las agrupa en **2
  columnas = 2 carriles** y las llena de atras (y=38) hacia adelante:
  exactamente los 2 puestos por columna que confirmo el Director.
- Sin estacionamientos (`parking`) ni recepcion (`inbound`) en el v2
  (BK-31): INIT-11 F2 e INIT-7 no se prueban sobre el hasta que se agreguen
  (una tarde en Tiled o en la futura web).
- Con este mapa, `_outbound_discharge_lanes` deja de teletransportar a la
  entrada (la celda delantera menos 1 es (3,28), caminable), pero **sigue
  teletransportando dentro del carril** (`_jump_to(slot.cell)`, hasta 9
  celdas) y sigue esperando fuera **sin reservar** su celda. Ambas cosas las
  cierra F3 de la propuesta anterior.

---

## 2. Pregunta 1 — "Inteligencia para ceder el paso"

### 2.1 Que hay hoy

- El ocioso va a una celda de espera y la **reserva sin fin**
  (`operators._esperar_sin_estorbar` -> `_recorrer_tramo(goal_dwell=
  ESPERA_ABIERTA_S)`; `idle_zones.GestorZonasEspera.asignar`). Los demas la
  ven como pared movil: `spacetime_planner.find_path_st` no la atraviesa.
- El ocioso se despierta cada 0,5 s (`agent_process`: `yield timeout(0.5)`)
  solo para pedir trabajo. **No hay canal por el que otro le pida que se
  mueva.**
- Quien no encuentra plan espera 0,5 s reservando su celda y reintenta
  (`_recorrer_tramo`, `replan_wait_s`/`replan_max_retries`). Si la pared movil
  es la causa, reintenta hasta 1.200 veces.
- Las celdas de espera se eligen para no estorbar (`motivo_invalida` +
  `_sin_cortar_el_mapa`), pero "no cortar el mapa" no es "no alargar el
  camino": una celda de borde en un pasillo de 2 obliga a los demas a pasar
  en fila india, y en la franja delantera de v2 (2 filas) eso es todo el
  ancho.

### 2.2 Tecnicas que existen y cuales encajan en este motor

| Tecnica | Que es | Encaja aqui? |
|---|---|---|
| **Push and Swap** (Luna & Bekris, 2011) / **Push and Rotate** (de Wilde, ter Mors, Witteveen, JAIR 2014) | Resolutores completos de "pebble motion": primitivas *push* (empujar a otro a una celda vacia), *swap* (intercambiar dos por un vertice libre), *rotate* (girar un ciclo). Completos con >= 2 celdas vacias. | Son **algoritmos enteros**, sincronicos y discretos (todos avanzan un paso a la vez): reemplazarian al SIPP de tiempo continuo, las estadias y la tabla de reservas. La primitiva *push* si es la idea correcta; el resolutor no. |
| **PIBT** (Okumura et al., IJCAI 2019) | Planificacion de UN paso por tick con herencia de prioridad y backtracking: si un agente de mayor prioridad necesita tu celda, heredas su prioridad y te corres. Garantia de llegada en tiempo finito solo en grafos **biconexos**. | Mismo problema: sustituye al planificador (un paso por tick, sin reservas de estadia ni tiempos continuos). Ademas los carriles son ramales ciegos: el grafo NO es biconexo, la garantia no aplica. La idea de **herencia de prioridad** si la tomo prestada (2.5). |
| **RHCR** (Li et al., AAAI 2021) | Replanificar a TODOS los agentes cada h pasos con ventana w; los ociosos reciben destinos ficticios. Escala a 1.000 robots. | Centralizado y acoplado; nuestro motor planifica por agente al vuelo (SimPy). Cambio de arquitectura, no de feature. |
| **Planificacion priorizada entre obstaculos movibles** (M-PAMO, 2025) | Extiende PP y CBS a entornos con obstaculos que se pueden mover. | Investigacion; el espacio de estados "crece exponencialmente". No. |
| **FAR / highways** (Wang & Botea, 2008) | Anotar direcciones en el grafo para reducir cruces. | Es la Fase B (sentido unico). Complementaria, no sustituye ceder. |
| **Puntos de detencion fuera del paso** (Cap et al. 2015; Ma et al. 2017, token passing sobre instancias bien formadas) | Los agentes parados nunca bloquean a otros porque sus puntos de espera estan fuera de las rutas. | Es lo que ya hace BK-15 y lo que propone la estacion. Hace **menos necesario** ceder, pero no lo elimina: en pasillos de 2 y con muchos ociosos siempre hay estorbo residual. |
| **Reserva blanda + solicitud de desalojo** (practica de gestores de flota: un vehiculo ocioso recibe la orden de ir a otro nodo de parking; en FlexSim el equivalente son los "control points" que un AGV suelta al ser requerido) | El que espera tiene una reserva que otro puede pedir liberar; el que espera se reubica a un punto de parking alternativo. | **Encaja directo**: la tabla ya distingue agentes (`ignore_agents`), el ocioso ya tiene un lazo de espera donde enganchar un evento, y las celdas alternativas ya las sabe elegir `idle_zones`. Es local, acotado y determinista. **Recomendada.** |

### 2.3 Recomendacion: "cesion por solicitud" (reserva blanda)

Protocolo, con los archivos donde vive cada paso:

1. **Reserva blanda.** Las reservas abiertas de espera (ociosos en pulmon,
   operarios en fila) se marcan blandas: `ReservationTable.reserve(...,
   blanda=True)` y un conjunto `blandos: {agent_id}` (`reservation_table.py`).
   `is_free` ya acepta `ignore_agents`; no cambia su logica.
2. **Deteccion del estorbo.** En `SpaceTimePlanner.plan_and_reserve`
   (`spacetime_planner.py`), si el plan estricto falla o llega mas tarde que
   `umbral_desvio_s` respecto de un plan **que ignora a los blandos**
   (segunda busqueda con `ignore_agents=blandos`, solo cuando la primera
   fallo o cuando la heuristica geometrica dice que el desvio supera el
   umbral: dos A* como maximo por tramo), se extraen los blandos cuyas celdas
   aparecen en ese plan dentro del `horizonte_s` inicial. Ese plan NO se
   reserva ni se ejecuta: es solo para saber a quien pedirle.
3. **Solicitud.** El solicitante llama a `almacen.cesiones.solicitar(
   solicitante, [(agente_blando, celda)])` (`GestorCesiones` nuevo en
   `stations.py` o modulo propio `cesiones.py`). El gestor encola la
   solicitud por `(t, agent_id)` y dispara el `env.event()` del blando.
   El solicitante espera `replan_wait_s` (como hoy) y replanifica.
4. **Cesion.** El blando esta en su lazo de espera, que pasa de
   `yield timeout(0.5)` a `yield evento_cesion | timeout(0.5)`
   (`operators.agent_process` / `_esperar_sin_estorbar`; y el lazo de fila de
   la estacion). Al despertar por cesion, `_ceder_el_paso()`: (a) pide a
   `GestorZonasEspera.alternativa(agent, evitar=celdas_solicitadas |
   celdas_del_camino_del_solicitante | blandas_ajenas)` la celda libre valida
   mas cercana (`idle_zones.py`, misma regla `motivo_invalida` + no cortar el
   mapa); (b) si existe: libera su reserva blanda, planifica ESTRICTO el
   tramo corto (1-3 celdas) con `_recorrer_tramo(goal_dwell=abierta,
   blanda=True)`, emite el evento `cesion` al `.jsonl` (status
   `"cediendo"` para el visor), incrementa `cesiones_concedidas`; (c) si no
   existe: responde "no puedo" (`cesiones_rechazadas`), se queda, y el
   solicitante sigue con el mecanismo actual (espera/replanifica/retrocede).
5. **Tiempo de reaccion** (realismo, configurable): `tiempo_reaccion_s`
   (default 1,0 s; 0 = instantaneo) antes de moverse, contado en
   `tiempo_en_cesion_s`.
6. **Vuelta.** El que cedio NO vuelve a su celda original: se queda en la
   alternativa (menos movimiento, menos ping-pong). Si estaba en fila,
   conserva su **posicion logica** en el turno (la fila es FIFO por
   `t_pedido`, no por celda): cuando le toca, va desde donde este.

Configuracion (registrar en `src/core/config_schema.py`, editar en la web,
documentar en `MANUAL_CONFIGURACION.md`):

```json
"congestion": {
  "cesion": {
    "enabled": false,
    "quien_cede": "ociosos_y_fila",       // ociosos | ociosos_y_fila
    "umbral_desvio_s": 2.0,               // pedir solo si el desvio supera esto
    "horizonte_s": 5.0,                   // solo blandos que estorban en los proximos N s del plan
    "tiempo_reaccion_s": 1.0,
    "max_cesiones_seguidas": 3,           // anti ping-pong: despues se queda y avisa
    "radio_alternativa": 4                // celdas maximas para correrse
  }
}
```

`enabled: false` (default) = ninguna linea nueva se ejecuta = gate
byte-identico. Encenderlo en el canonico es una decision (D-A1) y mueve el
baseline.

### 2.4 Quien cede (realismo primero)

| Estado del que estorba | Cede? | Por que |
|---|---|---|
| Ocioso en pulmon o en celda de espera | **Siempre** (si tiene a donde) | Es lo que hace una persona sin tarea. Costo real: 2-3 s. |
| Esperando turno en la fila, con o sin carga | **Si**, conservando el turno | Un operario cargado se corre igual (empuja el carro 2 m); lo que no pierde es su lugar en la cola. Config `quien_cede: ociosos_y_fila`. |
| En medio de un pick (estadia en la ubicacion) | **No** | Interrumpir un pick y retomarlo no es realista a esta escala; el otro espera esos segundos (el SIPP ya espera el fin de la estadia con `earliest_free`). |
| Descargando en el puesto | **No** | Idem; y el puesto es un ramal: el otro no deberia estar ahi sin turno. |
| En movimiento ejecutando un plan | **No** | Ya esta coordinado por reservas; pedirle que ceda romperia su plan y el de los que planificaron alrededor. |
| Cambiando de equipo en un estacionamiento (INIT-11 F2) | **No** | Estadia con tiempo definido; igual que un pick. |
| Ya cedio `max_cesiones_seguidas` veces | **No** (y avisa) | Anti livelock. `[WARN] GroundOp-02 cedio 3 veces seguidas en (1,30): se queda.` |

Un operario **cargado y ocioso** no existe (descarga antes de quedar ocioso),
salvo los casos de aborto de tour (`_abort_tour` vacia la carga). Si INIT-11
F3 introduce esperas cargadas en puntos de transferencia, aplican como "en
fila".

### 2.5 Deadlock y livelock: por que no aparecen

- **Orden estricto de roles** (herencia de prioridad a la PIBT, pero sin su
  planificador): *solicitante* = tiene plan/tarea; *cedente* = no tiene
  destino propio. Un cedente **nunca solicita**; un solicitante **nunca
  cede**. Dos que se corren mutuamente para siempre requiere que ambos sean
  solicitantes y cedentes a la vez: imposible por construccion.
- **Sin cadenas**: el tramo del cedente se planifica ESTRICTO (respeta todas
  las reservas, incluidas las blandas ajenas) y solo hacia celdas no
  solicitadas y no blandas. Un cedente no empuja a un tercero. Profundidad de
  la cadena = 1.
- **Ping-pong acotado**: A pide, Y se corre a c2; B pide c2, Y vuelve a c1;
  A pide... `max_cesiones_seguidas` lo corta; Y se queda y los solicitantes
  caen al mecanismo actual (que ya termina: espera acotada + retroceso). La
  metrica `cesiones_rechazadas_por_tope` hace visible si el mapa es tan
  angosto que esto pasa seguido.
- **Sin destino imposible**: si no hay alternativa valida, el cedente
  rechaza; no se genera una espera nueva.
- **Deadlock preexistente**: la cesion no introduce esperas circulares (el
  cedente no espera a nadie: se mueve o rechaza). El unico deadlock posible es
  el que ya existia sin cesion; con la estacion (propuesta anterior) ese
  tambien desaparece.

### 2.6 Determinismo y gate

- Ninguna decision usa azar: las solicitudes se ordenan por `(t, agent_id)`,
  las alternativas por `(distancia, y, x)`, los blandos culpables por orden
  de aparicion en el plan.
- Los eventos SimPy de cesion se disparan desde el proceso del solicitante en
  su instante de planificacion; SimPy procesa eventos del mismo instante en
  orden de programacion, que es determinista dado el mismo programa y la
  misma semilla. Igual que las esperas de BK-15.
- Con `enabled: false` no cambia un byte. Con `enabled: true` en el canonico:
  nuevo baseline, en el mismo commit, con las metricas de 2.7 en la
  metadata del `.jsonl` (sin wall-clock, regla BN-05/IN-43).
- Test de reproducibilidad: dos corridas con `WAREHOUSE_SEED=42` y
  `cesion.enabled=true` -> `.jsonl` identico (patron de
  `scripts/regression_gate.py`).

### 2.7 Como se mide

Metricas nuevas (en `timewindow_shadow_report` o en un bloque `cesiones` del
reporte de congestion; `src/core/replay_utils.py` las copia a la metadata):

| Metrica | Que dice |
|---|---|
| `cesiones_pedidas` / `concedidas` / `rechazadas` / `rechazadas_por_tope` | Cuantas veces se pidio, se cumplio, no se pudo, se corto por ping-pong |
| `celdas_cedidas_total` | Cuanto se movieron los que cedieron |
| `tiempo_en_cesion_s` | Tiempo de agente gastado en correrse (reaccion + caminata) |
| `desvio_evitado_s` | Suma de (llegada con estorbo - llegada sin estorbo) de los solicitantes atendidos: cuanto tiempo se ahorro |
| `max_cesiones_seguidas_observado` | Si llega al tope, el mapa tiene un cuello |
| Existentes: `replan_waits`, `exec_blocked`, `exec_fallbacks`, co-ocupaciones | Deben bajar o quedar en 0 |

Escenario de prueba especifico: WH1 v2, 4+4, 100% a la zona 1, perfil "Real"
(1 s/celda, donde el desvio duele): comparar `enabled` false/true en
duracion, `replan_waits` y `desvio_evitado_s`. Y un test sintetico de pasillo
de ancho 2 con un ocioso en el medio.

### 2.8 Costo en este codigo

| Archivo | Cambio | Tamano |
|---|---|---|
| `reservation_table.py` | flag `blanda` en `reserve`, conjunto `blandos`, `release_agent` lo limpia | chico |
| `spacetime_planner.py` | segunda busqueda con `ignore_agents=blandos` bajo condicion; extraccion de culpables; metricas | mediano (~60 lineas) |
| `idle_zones.py` | `alternativa(agent, evitar, radio)`; contador de cesiones seguidas por agente | chico |
| `operators.py` | lazo de espera con `evento | timeout`; `_ceder_el_paso()`; hook de solicitud en `_recorrer_tramo` cuando el plan falla o desvia; evento `cesion` y status `cediendo` | mediano |
| `stations.py` (nuevo en F1 de la propuesta anterior) o `cesiones.py` | `GestorCesiones`: registro agente -> evento, cola de solicitudes, rechazo por tope | chico |
| `warehouse.py` | instanciar el gestor cuando `cesion.enabled` | trivial |
| `config_schema.py`, `web_prototype/config_manager.py`, card en la web, `MANUAL_CONFIGURACION.md` | bloque `congestion.cesion` | chico |
| `replay_utils.py`, visor | metricas; dibujar `cediendo` | chico |
| Tests `test_bk25_cesion.py` | roles, tope, determinismo, alternativa valida, fila conserva turno, gate con flag off | mediano |

Estimacion: **3-4 dias** si se hace despues de F1 (estacion), 4-5 si antes
(porque la fila todavia no existe). Recomiendo el orden F0 (bug de
sobre-reserva) -> F1 (estacion) -> cesion -> F2/F3.

---

## 3. Pregunta 2 — Donde esperan los que no tienen turno

Distancias medidas sobre el mapa (Manhattan, que en este anden coincide con el
camino): de la entrada del carril 1 (3,28) al bloque izquierdo (1,30): 4
celdas; a las filas traseras (3,40): via x=2, 14 celdas; del carril 7 (27,28)
al bloque izquierdo: ~28 celdas; a la columna derecha (29,30): 3 celdas (pero
es salida). A 0,1 s/celda (canonico "Demo") 28 celdas = 2,8 s; a 1 s/celda
("Real") = 28 s. Una descarga dura 5-60 s y una espera de turno, minutos.
**La distancia es secundaria; el estorbo es primario.**

| Opcion | Estorbo | Distancia | Realismo | Veredicto |
|---|---|---|---|---|
| (a) Pulmon al costado de cada carril, en las columnas libres x=5-6, 9-10... | **Alto**: esas columnas son las **salidas** (columna derecha del carril k sale por su x par... ver seccion 4) y de un solo sentido; un ocioso ahi tapa la salida de una fila del carril | Minima | Un forklift no espera en la salida de otro | **No** (salvo la variante a' de abajo) |
| (a') Pulmon en el bloque libre izquierdo x=0..1, filas 29..41 (26 celdas; x=2 queda como salida de la columna izquierda del carril 1) | **Nulo**: no es paso de nadie | 4 celdas del carril 1; hasta 28 del carril 7 | Es un area de espera junto al muelle, lo normal | **Recomendada** |
| (b) Franja delantera, filas 27-28 | **Muy alto**: es el paso principal, tiene 2 filas, la 27 es la de las bocas de pasillo; ademas la fila 28 ya aloja las celdas de fila (entradas) | Minima | Nadie estaciona en el pasillo principal | **No** (solo la fila de 1 por puesto) |
| (c) Filas traseras 39..41 (90 celdas) | Bajo hoy (no hay cargador modelado); en la realidad es el **anden de carga**, donde trabaja el cargador y maniobra al camion | 13-15 celdas via los bloques laterales | Discutible: los forklifts si esperan en el anden de carga, pero fuera de la puerta activa | **Secundaria**, opt-in (D-A3), reservando las 2 filas mas cercanas a la puerta activa |
| (d) Editar el mapa: agregar filas entre la 26 y la 29 | Reduce el estorbo en la franja delantera (3 filas permiten 2 sentidos + fila) | Igual | Un anden de 3 m de circulacion delante de los carriles es tipico | **No necesario para esperar**; util para la Fase B (bucle de un sentido: fila 27 hacia el este, fila 28 hacia el oeste) |

Recomendacion: **(a')** como pulmon principal, deducido automaticamente por
la regla de la propuesta anterior (celdas transitables, fuera de carriles,
entradas, salidas y sus prolongaciones, bocas de pasillo y franja delantera;
ordenadas por distancia a la estacion; que no corten el mapa). Con
`quien_cede: ociosos_y_fila`, el pulmon ademas se corre si estorba.

Editar el mapa: **no hace falta** para esto. Dos ediciones opcionales, si
el Director quiere: (1) agregar 2 columnas libres a la derecha (x=30..31)
para un pulmon simetrico cuando el trafico se reparte entre los 7 carriles y
el perfil es "Real" (28 s de caminata por espera se notan); (2) una fila mas
en la franja delantera para el bucle de un sentido de la Fase B. Ninguna es
prerequisito de H-15.

---

## 4. Pregunta 3 — D2 y D4 actualizados: puestos, salidas, fila

### 4.1 Como queda la estacion en WH1 v2 (carril 1 como ejemplo)

```
          x= 0  1  2  3  4  5  6  7
y=27         .  .  .  .  .  .  .  .     paso principal (bocas de pasillo)
y=28         .  .  .  E  E  .  .  .     E = entrada/fila (1 celda por puesto)
y=29         p  p  s  L  R  s  s  L2    p = pulmon (x=0..1)   s = salida, un solo sentido NORTE, no_detenerse
...          p  p  s  L  R  s  s  L2    L/R = puesto izquierdo/derecho del carril 1 (x=3 / x=4), 10 slots cada uno
y=38         p  p  s  L  R  s  s  L2    L2 = puesto izquierdo del carril 2 (sale por x=6)
y=39..41     anden de carga (opcional pulmon secundario, D-A3)
```

- **Puestos**: 2 por carril, uno por columna (x=3 y x=4 en el carril 1). Cada
  puesto tiene 10 slots (y=29..38) que se llenan de atras hacia adelante,
  como hoy (`StagingZone.deepest_empty_cell`). Confirmado por el Director.
- **Entrada**: una por puesto, la celda delantera (3,28) y (4,28). Se entra
  solo por ahi, de frente, bajando por la columna hasta el slot libre mas
  profundo. Las celdas del puesto son **privadas** del que tiene el turno.
- **Salidas laterales, una por puesto**: el puesto izquierdo (x=3) sale hacia
  el OESTE a x=2, el derecho (x=4) hacia el ESTE a x=5, **desde la fila en la
  que quedo** (cardinal, sin diagonales), y sube por esa columna libre hasta
  la fila 28. Las columnas x=2, x=5, x=6, x=9, ... x=26 y x=29 son
  `no_detenerse` con `sentido: N` (solo se sube) y **solo se entra a ellas
  desde un puesto** (regla de salida de estacion). Cada columna libre de 2
  celdas sirve a dos carriles vecinos sin cruzarse: x=5 al carril 1
  derecho, x=6 al carril 2 izquierdo.
- **Fila**: `cola_max = 1` por puesto = la entrada. Dos esperando como
  maximo frente a cada carril, en la fila 28, que deja libre la fila 27 para
  el paso. Con `quien_cede: ociosos_y_fila` se corren si hace falta.
- **Pulmon**: (a'), x=0..1 filas 29..41, FIFO por `t_pedido`. Con 4+4 y todo
  al carril 1: 2 en fila + hasta 4 en el pulmon; caminata de vuelta 4-6
  celdas.
- **Liberacion del turno**: `liberar_al_salir_de: "puesto"` (cuando el
  agente ya esta en la celda de salida). Como el siguiente entra por la
  fila 28 bajando por la columna y el que sale ya esta en la columna
  lateral, no se cruzan nunca.
- **Camion**: con 2 puestos y 10 slots por puesto, `truck_capacity` 8 y
  `truck_interval` 90 s, el carril NO se llena si la unidad es contenedor
  por pedido (D3 anterior); con pallet por WO se llena (618 en ~7.000 s =
  5,3/min contra 5,3/min de capacidad de camion: justo en el limite, por
  eso hoy hay 343 esperas dentro del carril).

Bloque `circulacion` resultante (todo deducible; se muestra explicito para
que se vea que es lo que se guardaria si el cliente lo toca):

```json
"circulacion": {
  "version": 1,
  "estaciones": {
    "DESCARGA-1": {
      "tipo": "descarga", "zona": 1,
      "puestos": {"IZQ": {"columna": 3, "filas": [29, 38], "entrada": [3, 28], "salida": "O"},
                  "DER": {"columna": 4, "filas": [29, 38], "entrada": [4, 28], "salida": "E"}},
      "cola_max": 1,
      "liberar_al_salir_de": "puesto",
      "pulmon": "auto"
    }
  },
  "reglas_celda": [
    {"desde": [2, 29], "hasta": [2, 38], "sentido": "N", "no_detenerse": true},
    {"desde": [5, 29], "hasta": [6, 38], "sentido": "N", "no_detenerse": true}
  ],
  "anden_carga": {"desde": [0, 39], "hasta": [29, 41], "uso": "reservado"}
}
```

`salida: "O"|"E"` es la forma corta de "columna libre contigua en esa
direccion"; la deduccion la resuelve a la columna x=2 / x=5. `anden_carga`
con `uso: "reservado"` excluye las filas 39..41 del pulmon automatico;
`"pulmon_secundario"` las habilita (D-A3).

### 4.2 D2 y D4 actualizadas

- **D2 (puestos)**: 2 por carril, uno por columna. Ya no es "diferir": es lo
  que el mapa y `StagingZone` ya expresan. Con outbound apagado sobre v2, la
  "zona" sigue siendo el ancla (3,29) de una celda; recomiendo que en v2 el
  modo apagado tambien use los 2 puestos (la estacion no depende del
  outbound; solo cambia si se crean pallets persistentes o no).
- **D4 (fila)**: `cola_max = 1` por puesto (la entrada). No hay lugar
  realista para mas en una franja de 2 filas, y con el pulmon a 4 celdas no
  hace falta.

---

## 5. D9 corregida — consolidar por destino o repartir por carga

Lo que dije en D9 ("repartir entre zonas es decision de negocio") queda
incompleto: el reparto por destino **ya existe** (INIT-6 Opcion B, verificado
en `warehouse._resolver_staging_id`: 1. `order.staging_id` explicito, 2.
`order.destino` via `destino_staging_map`, 3. `_seleccionar_staging_id`
aleatorio ponderado por `outbound_staging_distribution`). El 100% a la zona
1 del canonico viene de que el modo es estocastico (paso 3) con la
distribucion `1: 100`.

Cuando conviene cada cosa:

| Situacion | Regla | Por que |
|---|---|---|
| Modo determinista con `destino` en los pedidos | **Consolidar por destino** (`destino_staging_map`) | Un carril de staging real es "un camion / una ruta / una hora de salida" (guias de muelle: organizar el staging por carrier, ruta o salida). Mezclar destinos en un carril obliga a reordenar al cargar. La cola que se forma en el carril del destino con mas pedidos es **real** y la debe resolver la estacion (turno, fila, pulmon, 2 puestos), no el reparto. |
| Modo determinista sin `destino` y sin `staging_id` | Avisar en la vista previa (`[WARN] N pedidos sin destino: se repartiran al azar segun outbound_staging_distribution`) | Hoy cae al azar en silencio (solo un print por pedido si el destino no mapea). |
| Modo estocastico (el canonico) | **Repartir** con una distribucion que represente rutas/camiones esperados por carril; el validador avisa si un carril recibe > 50% habiendo 7 definidos | En estocastico no hay destino: la distribucion ES el modelo de la demanda por ruta. `1: 100` modela "un solo camion/ruta para todo el almacen", que solo es realista si el cliente lo dice. |
| Dimensionar el muelle (cuantos carriles, cuantos puestos) | Consolidar por destino y medir `espera_turno_total_s` y `max_en_cola` por carril | Es la pregunta de negocio que el simulador deberia responder; repartir por carga la esconde. |
| Estres de la estacion (QA) | 100% a un carril, 4+4 | Peor caso; es el escenario de exito de la propuesta anterior (6.6). |

Recomendacion concreta para el canonico: mantener `1: 100` mientras se cierra
H-15 (es el peor caso y la base de comparacion) y, al adoptar v2 (BK-31),
fijar una distribucion canonica realista (por ejemplo 7 rutas con pesos
distintos: 30/20/15/10/10/10/5) y un preset "1 ruta" para el estres.

---

## 6. Decisiones nuevas para el Director

- **D-A1. Cesion por solicitud**: implementar segun 2.3, apagada por defecto;
  encenderla en el canonico tras medir (mueve el baseline). Recomendacion:
  si, despues de F0 y F1.
- **D-A2. Quien cede**: `ociosos_y_fila` (recomendado) u `ociosos`
  solamente. Nunca picks, descargas ni movimientos con plan.
- **D-A3. Filas 39..41**: anden de carga reservado (recomendado) o pulmon
  secundario. Si el Director quiere modelar al cargador o la maniobra del
  camion mas adelante, reservarlas ahora evita rehacer.
- **D-A4. Ediciones opcionales del mapa v2**: 2 columnas libres a la derecha
  (pulmon simetrico) y/o 1 fila mas en la franja delantera (bucle de un
  sentido, Fase B). Ninguna bloquea H-15.
- **D-A5. Adopcion de v2 como canonico** (BK-31): implica reimportar el Excel
  v2 (20 celdas por carril), agregar estacionamientos y recepcion al mapa, y
  nuevo baseline. Recomiendo hacerlo junto con F1: probar la estacion sobre
  la geometria definitiva y no dos veces.
- **D-A6. Distribucion canonica de destinos** al adoptar v2 (seccion 5).

---

## 7. Fuentes

Codigo leido: `operators.py` (`agent_process`, `_esperar_sin_estorbar`,
`_recorrer_tramo`, `_timewindow_execute_plan`, `_outbound_discharge_lanes`),
`idle_zones.py`, `reservation_table.py` (`is_free` con `ignore_agents`),
`spacetime_planner.py`, `outbound.py` (`StagingZone`), `warehouse.py`
(`_resolver_staging_id`, `_seleccionar_staging_id`, bloque outbound),
`run_migration.find_excel_file`, `layouts/WH1 v2.tmx`,
`layouts/custom_warehouse_tileset.tsx`, `layouts/Warehouse_Logic_v2.xlsx`
(hoja `OutboundStaging`), `warehouse.db` (solo lectura), `docs/BACKLOG.md`
(BK-30, BK-31).

Externas:

- Luna, Bekris, "Push and Swap: Fast Cooperative Path-Finding with
  Completeness Guarantees", IJCAI 2011:
  https://www.researchgate.net/publication/220815024_Push_and_Swap_Fast_Cooperative_Path-Finding_with_Completeness_Guarantees
- de Wilde, ter Mors, Witteveen, "Push and Rotate: a Complete Multi-agent
  Pathfinding Algorithm", JAIR 2014:
  https://jair.org/index.php/jair/article/download/10913/26020
- Okumura, Machida, Defago, Tamura, "Priority Inheritance with Backtracking
  for Iterative Multi-agent Path Finding", IJCAI 2019:
  https://www.ijcai.org/proceedings/2019/0076.pdf , https://kei18.github.io/pibt2/
  (garantia en grafos biconexos; herencia de prioridad).
- Li et al., "Lifelong Multi-Agent Path Finding in Large-Scale Warehouses",
  AAAI 2021 (RHCR): https://arxiv.org/abs/2005.07371
- "Conflict-Based Search and Prioritized Planning for Multi-Agent Path
  Finding Among Movable Obstacles" (M-PAMO), 2025:
  https://arxiv.org/abs/2509.26050
- Wang, Botea, "Fast and Memory-Efficient Multi-Agent Pathfinding" (FAR),
  ICAPS 2008 (via https://arxiv.org/pdf/1906.03992).
- Cap, Novak, Kleiner, Selecky, IEEE T-ASE 2015: https://arxiv.org/abs/1409.2399 ;
  Ma, Li, Kumar, Koenig, AAMAS 2017: https://arxiv.org/abs/1705.10868
  (instancias bien formadas; ver propuesta anterior, 3.1).
- FlexSim, control points / control areas y deadlocks AGV:
  https://answers.flexsim.com/questions/125062/agv-deadlock-avoidance.html ,
  https://forums.autodesk.com/t5/flexsim-forum/agv-deadlock-avoidance/m-p/13541348
- Staging por carrier/ruta/salida y buffers de espera para forklifts:
  https://www.precisionintegrators.com/blog-posts/staging-area-design-reducing-bottlenecks-at-receiving-and-shipping ,
  https://www.alotofstriping.com/the-ultimate-warehouse-traffic-flow-management-plan-guide-2026/
