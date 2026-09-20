# ADENDA 2 — Atascos en los pasillos de picking, zonificacion y reparto de carga

> Tercera consulta del Director sobre `docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md`
> y `docs/PROPUESTA_DISENO_CEDER_EL_PASO.md`. Consultor externo (Fable 5.1),
> 2026-09-20. Solo analisis; no se toco codigo. Lei
> `docs/PLAN_BK25_ESTACION_DESCARGA.md` (F1 cerrada, canonico en `WH1 v3`,
> 32x43, 384 ubicaciones) y el replay `output/simulation_20260920_022055`
> (solo lectura). Todo lo afirmado del motor se leyo en la rama actual y se
> cita como `archivo:funcion`.

---

## 0. Resumen ejecutivo (para el Director, sin jerga)

**Lo que paso en el pasillo no es lo que parecia.** Mire el replay celda por
celda. Los cinco operarios trabados en el pasillo de las columnas 9-10 tenian
**cada uno una tarea distinta en la MISMA ubicacion, la celda (10,18)**: cinco
pedidos que pedian el mismo producto del mismo hueco, repartidos a cinco
personas a la vez. Es el hallazgo BK-23 del backlog ("el despacho manda un
segundo equipo a una ubicacion ocupada"), que hasta ahora se creia un caso
raro de pocos productos. En esa corrida hubo 61 ubicaciones con dos o mas
operarios asignados al mismo tiempo, 7 con tres o mas, y esa con cinco.

Y una vez ahi, se repitio **exactamente el bloqueo de la descarga** que ya
resolvimos con la estacion: GroundOp-07 tomo su pick en (10,18) entre los
segundos 244 y 301, y **no pudo salir hasta el segundo 6.301** (una hora y
media simulada), porque los otros cuatro esperaban pegados a el, tapandole
las tres salidas. A los 6.000 segundos el motor se rindio, lo dejo pasar por
encima de otro, y el siguiente (GroundOp-08) repitio el ciclo hasta el
segundo 12.410. Las dos "rendiciones" de la tabla son exactamente esos dos
momentos. Los otros tres terminaron en dos minutos cuando ya no habia nadie
tapando.

**Tiene razon el Director en que mi cesion por solicitud no lo resuelve**: los
cinco tenian tarea. Pero no hay que extenderla a los que tienen tarea, porque
en ese pasillo no habia a donde correrse (cinco personas en seis celdas). Lo
que falta son dos reglas que en un almacen real existen y aca no:

1. **Una ubicacion, un operario a la vez.** El despacho no debe mandar a un
   segundo operario a un hueco donde ya hay uno trabajando; y quien va a un
   hueco se lleva todas las lineas pendientes de ese hueco que le quepan
   (como hace un picker real). Esto solo elimina el 90% del problema y es un
   dia de trabajo.
2. **Cupo por pasillo.** Cada pasillo de picking es una "estacion" con
   capacidad (2 en un pasillo de 2 celdas de ancho): el tercero no entra. Y en
   vez de hacer cola en la boca, **saltea ese pasillo y va primero al
   siguiente de su recorrido**, que es lo que hace una persona cuando ve un
   pasillo lleno; si no tiene nada mas que hacer, espera en el pulmon y se lo
   llama por turno. Con 2 adentro en un pasillo de 2 de ancho, demuestro que
   el bloqueo circular es imposible. Tres o cuatro dias.

**Zonificacion (la idea del Director).** Es el "zone picking" clasico y es
realista: cada operario o pareja se queda con un grupo de pasillos, camina
menos y no se amontona. Conviene hacerla, pero como **tercera capa**, no en
lugar de las dos anteriores: la zona baja la probabilidad del choque; el cupo
lo hace imposible. Su costo conocido es el **desbalance**: si un pasillo tiene
mucha demanda y otro poca, uno trabaja y otro mira. Por eso propongo una regla
de **ayuda entre zonas** ("robo de trabajo"): cuando a un operario no le queda
nada en su zona (o le queda menos de un umbral), toma trabajo de la zona mas
atrasada, empezando **por el extremo opuesto** al que esta recorriendo el dueño,
para no chocarse con el. Con un solo operario, la zona es todo el almacen y
nada cambia.

Para configurarla recomiendo **un concepto nuevo, "zonas de picking", en la
configuracion y editable en la web** (una zona = una lista de pasillos, que el
simulador numera solo a partir del mapa), asignada a cada grupo de operarios
con prioridades, igual que hoy se asignan las areas. **No reutilizar la
columna `WorkGroup`**: vive en el Excel (cambiarla exige reimportar), hoy es
una copia del area y una zona es una decision de turno, no un dato maestro.

Decisiones para el Director: 8, en la seccion 6.

---

## 1. Diagnostico verificado en el replay y el codigo

### 1.1 Que paso en (10,18)

Del `.jsonl` (`work_order_update` con `status: assigned` / `in_progress` y
`estado_agente`):

| Operario | Tarea en (10,18) | Asignada en t | Picking en (10,18) | Sale de (10,18) |
|---|---|---|---|---|
| GroundOp-07 | WO-0166 | 242 | 244,2 - 301,1 | **6.301,1** (rendicion 1) |
| GroundOp-08 | WO-0196 | 258 | 6.306,5 - 6.359,8 | **12.410,0** (rendicion 2) |
| GroundOp-05 | WO-0116 | 270 | 12.468,2 - 12.498,5 | 12.498,5 |
| GroundOp-06 | WO-0553 | 326 | 12.498,7 - 12.528,9 | 12.528,9 |
| GroundOp-04 | WO-0506 | 290 | 12.529,2 - 12.602,1 | 12.602,1 |

Cinco tareas distintas (cinco pedidos del mismo SKU) en la misma celda,
asignadas a cinco operarios en 84 segundos. Mientras uno pickeaba, los otros
cuatro esperaban en las celdas vecinas: (9,17), (9,18), (9,19), (10,17),
(10,19), que son las unicas salidas del que esta en (10,18). Es el mismo
patron de H-15: **el que espera tapa la salida del que trabaja**, y el
planificador espacio-temporal (`spacetime_planner.find_path_st`) lo produce
por diseno, porque la llegada mas temprana al destino ocupado es esperar en la
celda adyacente (`earliest_free`). El "6.301" es `replan_max_retries` (1.200)
x `espera_extra_factor` (10) x `replan_wait_s` (0,5) = 6.000 s de
`ultimo_recurso: esperar` (`operators._tw_replan_params`, `_recorrer_tramo`).

Concurrencia de asignaciones en esa corrida (calculada del replay: para cada
ubicacion, maximo de operarios con una WO asignada ahi en el mismo instante):
212 ubicaciones con 1, **54 con 2, 4 con 3, 2 con 4, 1 con 5**. No es un caso
raro de "pocos SKUs": con 300 pedidos sobre 50 SKUs y 384 ubicaciones, es la
norma. En el codigo, `dispatcher._marcar_asignados` no registra la ubicacion
como comprometida y ninguna estrategia (`_estrategia_ejecucion_plan`,
`_construir_tour_por_secuencia`) mira si otro tour ya va a ese hueco: BK-23,
tal como esta descripto en el backlog.

### 1.2 Por que "Ejecucion de Plan" amontona a todos al principio

`_estrategia_ejecucion_plan` elige como primera WO la de **menor
`pick_sequence`** del area de mayor prioridad, para todos los operarios por
igual. Con 8 operarios a pie, los 8 primeros recorridos arrancan en el
pasillo 1: verificado en el replay (GroundOp-01..04 tienen su primera tarea en
(1,3), (1,8), (1,8), (1,8)). El doble barrido (`_construir_tour_por_secuencia`)
despues los lleva a todos por la misma serpiente. Es una fuente estructural
de amontonamiento que la zonificacion corrige de raiz (cada uno arranca en su
zona) y que el cupo por pasillo contiene.

### 1.3 Literatura: esto tiene nombre

Parikh y Meller (2010) distinguen **"in-the-aisle blocking"** (no pueden
cruzarse en un pasillo angosto) de **"pick-point blocking"** (dos quieren el
mismo hueco). Lo de (10,18) es pick-point blocking llevado al extremo por un
despacho que no mira el hueco. Gue, Meller y Skufca (2006) muestran que el
bloqueo crece con la variacion de la densidad de picks por pasillo, y que el
batching por distancia lo reduce al estabilizar los picks por pasillo. La
literatura de zone picking (resumida por Optioryx y el estudio de simulacion
del IJSIMM 2018) coincide en el trade-off: menos caminata y menos congestion
a cambio de **desbalance entre zonas**, que hay que corregir activamente.

---

## 2. Pregunta 1 — Atasco entre agentes que TODOS tienen tarea

### 2.1 Las opciones, evaluadas

| Opcion | Resuelve (10,18)? | Resuelve 5 tareas distintas en un pasillo? | Costo | Riesgo |
|---|---|---|---|---|
| (a) Cupo por pasillo (pasillo = estacion con capacidad) | Si, si el cupo es 2: el tercero no entra, y con 2 adentro no hay bloqueo (2.4) | **Si**: es la unica que lo garantiza | 3-4 dias | Cola en la boca mal ubicada tapa el pasillo transversal: por eso propongo saltear, no hacer cola |
| (b) Extender la cesion a agentes con tarea | **No**: en (10,18) no habia celda libre a donde correrse (5 en 6 celdas). Ademas, para que el de adentro salga hay que correr a 3 a la vez, coordinados: es push-and-rotate, no una cesion local | Parcial | Alto | Livelock real (el Director ya lo vio colapsar) |
| (c) Prevencion en el despacho: no asignar tareas de un pasillo con N agentes | Parcial: un recorrido cruza varios pasillos y el "N" cambia mientras camina; hay que predecir donde estara cada uno | No garantiza nada | 2 dias | Falsos negativos (tareas que nadie toma) |
| (d) **Una ubicacion, un operario a la vez + consolidar por ubicacion** (BK-23) | **Si, de raiz**: los otros cuatro nunca habrian ido | No por si sola (5 tareas en 5 huecos del mismo pasillo siguen siendo posibles) | 1 dia | Ninguno de deadlock; una WO puede esperar al proximo recorrido |
| (e) Esperar "no adyacente" en el planificador (prohibir esperas a distancia 1 de un destino ocupado) | Mueve el problema una celda: en un pasillo de 2 de ancho, dos que esperan a distancia 2 lo tapan igual | No | 1 dia | Deadlock desplazado |

**Recomendacion: (d) + (a), en ese orden, y la zonificacion (pregunta 2) como
tercera capa.** (d) elimina la causa de la corrida medida; (a) es la garantia
para cualquier otra combinacion (cinco tareas distintas, mezcla de gruas y
pickers, mapas ajenos). Ninguna requiere ceder el paso con tarea. La cesion
(F2 del plan) sigue valiendo para ociosos y fila; no la extenderia.

### 2.2 (d) Una ubicacion, un operario a la vez — diseno

- **Ubicaciones comprometidas**: `dispatcher` mantiene
  `ubicaciones_comprometidas: {celda: operator_id}`; se cargan en
  `_marcar_asignados` (por cada WO del tour) y se liberan en
  `notificar_completado_individual` (cuando la WO deja de estar en
  progreso) y en `finalizar_tour` / `_abort_tour` (limpieza).
- **Filtro**: `_estrategia_ejecucion_plan`, `_estrategia_optimizacion_global`
  y `_estrategia_cercania` excluyen de `candidatos_compatibles` toda WO cuya
  ubicacion este comprometida por OTRO operario. FIFO tambien (es un filtro
  comun: `_candidatos_sin_ubicacion_ajena`).
- **Consolidar por ubicacion** (realismo, y evita que las 4 WOs restantes
  queden huerfanas hasta el proximo recorrido): en
  `_construir_tour_por_secuencia`, al agregar una WO, agregar tambien las
  demas WOs pendientes de la **misma ubicacion** que quepan en capacidad y en
  `max_wos_por_tour`, antes de seguir la secuencia. Un picker real que llega a
  un hueco toma todas las lineas de ese hueco (es batch picking a nivel de
  ubicacion). `_estadia_en_ubicacion` (BK-15 C1) ya suma tareas consecutivas
  en la misma celda: la estadia se reserva completa.
- **Regla de espera legitima**: si a un operario no le queda ninguna WO
  elegible porque todas sus ubicaciones estan comprometidas, no se queda
  dando vueltas: `solicitar_asignacion` devuelve None y el operario espera
  en el pulmon (comportamiento actual de "sin trabajo").
- **Config**: `despacho.una_ubicacion_un_operario` (bool, default `true`) y
  `despacho.consolidar_por_ubicacion` (bool, default `true`), registradas en
  `config_schema.py`. Con `false` ambas, comportamiento historico exacto.
  Como el default cambia el canonico, es baseline nuevo (D-B1).
- **Efecto esperado**: en la corrida 8+8 repartida, las 61 ubicaciones con
  concurrencia pasan a 0 por construccion; la jornada deberia acercarse a la
  de los montacargas (2.574 s) porque los cinco a pie dejan de perder 12.000 s.
  En el canonico 2+2: BK-23 ya midio +53% de jornada en el caso "100% extra
  grande" por este motivo; aca deberia dar una mejora clara.
- **Test**: `test_bk23_una_ubicacion.py`: dos operarios piden trabajo con 2
  WOs en la misma celda -> el segundo recibe otra ubicacion; consolidacion:
  un operario que va a (x,y) se lleva las N WOs de (x,y) que caben; la
  ubicacion se libera al completar; con el flag off, comportamiento anterior
  (misma seleccion que hoy).

### 2.3 (a) Cupo por pasillo — diseno

**Deduccion del pasillo** (modulo nuevo `src/subsystems/simulation/aisles.py`,
puro, sin SimPy, mismo estilo que `stations.py`):

- Pasillo = componente conexa (vecindad cardinal) del conjunto {celdas de
  pick} U {celdas transitables cuyos vecinos cardinales transitables estan
  todos dentro de la misma "franja" entre racks}. En WH1 v3 da 8 pasillos:
  x=1-2, 5-6, ..., 29-30, filas 3-26. Generico para cualquier mapa: se apoya
  en los picks (base de datos) y en `collision_matrix`.
- **Bocas** = celdas del pasillo con un vecino transitable fuera del pasillo
  (en v3: fila 3 hacia el corredor superior y fila 26 hacia el inferior).
- **Ancho** = minimo corte transversal (2 en v3). **Capacidad** por defecto =
  ancho (`pasillos.capacidad_default`), con override por pasillo
  (`pasillos.capacidad: {"3": 1}`) y aviso si la capacidad configurada supera
  el ancho ("puede haber bloqueo") o si un pasillo mide 1 y la capacidad es 1
  ("nadie se cruza: solo entra uno").
- El simulador **numera** los pasillos de izquierda a derecha (o de arriba
  abajo) y lo imprime; la web y el visor muestran el numero sobre el mapa.
  Es la misma numeracion que usa la zonificacion (seccion 3).

**Protocolo de entrada** (`operators._execute_pick_tour`, antes de cada
tramo):

1. Para el proximo pick del recorrido, se calcula el camino y se detecta si
   cruza una boca hacia un pasillo del que el agente no esta adentro.
2. Se pide cupo a `GestorPasillos.entrar(pasillo, agent_id)`. Si hay cupo,
   entra (el cupo se descuenta al **cruzar la boca**, no al pedirlo, para no
   reservar de mas mientras camina por el corredor).
3. Si no hay cupo: **saltear** (`pasillos.si_lleno: "saltear"`, default):
   se elige la siguiente WO del recorrido cuyo pasillo tiene cupo (en orden
   de `pick_sequence`, para no deshacer la serpiente), se recalcula el tramo
   desde la posicion actual (`route_calculator.pathfinder.find_path`) y se
   vuelve al pasillo salteado mas tarde. El agente queda anotado en la cola
   FIFO del pasillo lleno (`t_pedido, agent_id`), asi que cuando el pasillo se
   libera se lo llama primero si sigue necesitandolo.
4. Si TODAS las WOs restantes estan en pasillos llenos: va al pulmon (las
   zonas de espera de BK-15, con reserva abierta) y espera el llamado por
   turno (evento SimPy por agente, como en la estacion). Alternativa
   configurable `si_lleno: "esperar_en_boca"`: una celda de espera por boca,
   en el corredor, reservada; en v3 hay 3 filas de corredor abajo y 3 arriba,
   asi que cabe sin cortar el paso. No la recomiendo por defecto: una boca
   ocupada es media entrada menos.
5. **Salida**: al cruzar una boca hacia afuera se libera el cupo
   (`GestorPasillos.salir`). Si el agente cambia de pasillo por dentro (no
   pasa en v3: los pasillos no se comunican por dentro), se cuenta salida +
   entrada.

**Que pasa con los que ya estan adentro cuando se llena**: nada. El cupo se
controla en la boca; adentro nadie es desalojado. "Lleno" significa
"alcanzo la capacidad", nunca "por encima". Los de adentro terminan sus
picks y salen; el planificador espacio-temporal sigue resolviendo los cruces
entre los dos de adentro como hoy (pasillo de 2: siempre queda una columna
libre para pasar al lado del que pickea).

**Interaccion con (d)**: con (d) activo, dos agentes adentro nunca quieren la
misma celda; el unico caso de espera adentro es "quiero pasar por la celda
donde el otro pickea", que se resuelve por la otra columna.

### 2.4 Por que con cupo = ancho no hay bloqueo en un pasillo de 2 (argumento)

Sea un pasillo de 2 columnas, N filas, con a lo sumo 2 agentes adentro.
(i) Un agente parado (pickeando) ocupa 1 celda de una fila; en esa fila la otra
columna queda libre. (ii) Un agente en movimiento que encuentra ocupada la
celda siguiente de su columna cambia a la otra columna en su propia fila
(libre por (i), porque el unico otro agente esta en una sola celda) y sigue.
(iii) El unico modo de que un agente no pueda moverse es que sus 2 o 3
vecinos transitables esten ocupados: hacen falta 2 o 3 otros agentes, y solo
hay 1. (iv) Si los dos pickean en la misma fila (las dos columnas), ninguno
esta bloqueado: cada uno sale por su columna. Luego no existe configuracion
de 2 agentes en la que alguno quede sin movimiento posible; el planificador
espacio-temporal, que es completo cuando existe una ruta con esperas finitas,
la encuentra. Con 3 agentes el argumento (iii) falla (dos parados + uno que
quiere pasar por su fila... sigue pudiendo si estan en filas distintas; falla
si dos pickean en la misma fila y el tercero necesita cruzar esa fila): por
eso la capacidad por defecto es el ancho, no ancho+1. Para un pasillo de
ancho 1, capacidad 1 es la unica libre de bloqueo (dos no se cruzan): es lo
que paso en el pasillo del borde antes de corregir el mapa.

Este argumento se convierte en tests: pasillo sintetico 2xN con 2 agentes en
todas las combinaciones (parado/parado, parado/moviendose, misma fila,
columnas cruzadas) -> los dos terminan; con 3 agentes y capacidad 3 -> existe
una combinacion que no termina sin rendicion (documenta por que el default
es 2).

### 2.5 Determinismo, gate, metricas, costo

- Sin `pasillos.enabled` (default `false` hasta medir; recomiendo `true` en
  el canonico despues de la medicion, D-B2) no cambia un byte. Las decisiones
  usan orden fijo (`pick_sequence`, `(t, agent_id)`), sin azar.
- Metricas nuevas (en `timewindow_shadow_report` o bloque `pasillos` del
  reporte de congestion, copiadas a la metadata por `replay_utils`):
  `pasillo_entradas`, `pasillo_salteos`, `pasillo_esperas`,
  `pasillo_tiempo_espera_s`, `max_en_pasillo` (por pasillo, debe ser <=
  capacidad), `bloqueos_en_pasillo` (planes sin solucion con el agente
  adentro de un pasillo: debe tender a 0). Mas las existentes:
  `plans_failed`, `replan_waits`, `exec_blocked`, rendiciones,
  co-ocupaciones.
- Escenarios de exito (semilla 42, una corrida por vez, como aprendio el
  equipo): 8+8 repartido: de 12.666 s, 23.910 planes sin solucion y 2
  rendiciones a **0 rendiciones, 0 co-ocupaciones fuera del arranque,
  `max_en_pasillo` <= 2 y jornada del orden de la de los montacargas
  (~2.600-3.500 s)**; 4+4 repartido (4.450 s) y 2+2 (8.769 s): sin
  empeorar; 100% extra grande (BK-23, 57.168 s): mejora clara.
- Archivos: `aisles.py` (nuevo, ~250 lineas), `operators.py`
  (`_execute_pick_tour`: orden dinamico + cupo; hook de llamado por turno
  reutilizando el de la estacion), `warehouse.py` (instanciar; pasar bocas a
  `GestorZonasEspera`, que ya excluye "boca de pasillo"), `dispatcher.py`
  (solo para (d)), `config_schema.py` (`despacho`, `pasillos`),
  `web_prototype/config_manager.py` (validar capacidad vs ancho), card en la
  web + capa del visor con numeros de pasillo, `replay_utils.py`,
  `MANUAL_CONFIGURACION.md`, tests (`test_bk23_una_ubicacion.py`,
  `test_pasillos_cupo.py`, `test_pasillos_deduccion.py`).
- Costo: (d) 1 dia; (a) 3-4 dias. Riesgo principal de (a): el orden dinamico
  del recorrido toca `_execute_pick_tour`, que es el corazon del motor; se
  mitiga con el flag y con el gate.

---

## 3. Pregunta 2 — Zonificacion (zone picking)

### 3.1 Que es y como encaja en este modelo

Zone picking: el almacen se divide en zonas y cada picker (o pareja) trabaja
solo en la suya. Hay dos variantes: **secuencial** (pick-and-pass: el
contenedor del pedido viaja de zona en zona) y **paralela** (cada zona
pickea sus lineas y se consolidan despues). El modelo actual ya es, sin
saberlo, la variante paralela: cada WO (linea) se lleva por separado a la
zona de descarga y el pedido queda completo cuando todas sus lineas estan
`staged` (`dispatcher.notificar_completado_individual`). Es decir, la
consolidacion ocurre en el carril: **no hay que construir nada nuevo para que
la zonificacion "cierre" los pedidos**. La variante secuencial es INIT-11 F3
(puntos de transferencia), otra iniciativa.

### 3.2 Zonificacion contra cupo por pasillo

| Criterio | Cupo por pasillo (2.3) | Zonificacion | Juntas |
|---|---|---|---|
| Garantia contra el bloqueo | **Si** (por construccion) | No: dos de la misma zona (pareja) o un ladron pueden coincidir; y las gruas cruzan todas las zonas | Si |
| Caminata por tarea | Igual que hoy | **Menor**: cada recorrido cubre 2-3 pasillos, no 8; la serpiente por `pick_sequence` es corta | Menor |
| Congestion | Contenida, no reducida | **Reducida** (menos agentes por pasillo, arranques repartidos: corrige 1.2) | Reducida y contenida |
| Balance de carga | No aplica | **Peor**: zona cargada vs zona vacia (literatura, 1.3) | Con robo de trabajo (seccion 4) |
| Realismo | Alto (nadie entra a un pasillo lleno) | Alto (es la organizacion mas comun con muchos pickers) | Alto |
| Configuracion | 1 numero (capacidad) | Zonas + asignacion por grupo | Ambas |
| Un solo operario | Sin efecto | Sin efecto (su zona es todo) | Sin efecto |
| Costo | 3-4 dias | 2-3 dias (sin robo) + 1-2 (robo) | 6-9 dias |

Conclusion: **no son alternativas, son capas**. El cupo es la red de
seguridad fisica; la zona es la organizacion del trabajo. Con zonas bien
dimensionadas el cupo casi nunca actua (y `pasillo_esperas` lo mide); sin
zonas, el cupo evita el desastre pero no la caminata larga.

### 3.3 `WorkGroup` o un concepto nuevo

Verificado: `locations.work_group` existe en la base (`WG_A/WG_B/WG_C`),
`WorkOrder.work_group` lo lleva (`warehouse.py:112`, resuelto por
`_obtener_work_group`), viaja en todos los eventos `work_order_update`, y
**ningun lector del despacho lo usa** (`dispatcher.py` solo lo copia a los
eventos; el reparto es por `work_area_priorities` via
`core.work_areas.effective_work_area_priorities`). Hoy es 1:1 con el area
(A=Ground, B=High, C=Special, 154/154/76), y la creacion de las 24 ubicaciones
nuevas lo replico asi.

| Opcion | A favor | En contra |
|---|---|---|
| Reusar `WorkGroup` como zona | Columna, atributo de WO y eventos ya existen; el visor ya lo muestra | Es **dato maestro** (Excel -> reimportar para cambiar un turno); hoy es una copia del area (habria que reescribir 384 filas y romper su significado actual); una zona es por pasillos, que se deducen del mapa, no por ubicacion suelta; no se puede asignar "pasillos 1-3" sin editar celda por celda |
| Concepto nuevo `zonas_picking` en `config.json` | Es una decision **operativa** (cambia por turno/flota), editable en la web sin reimportar; se define por pasillos (unidad natural, deducida y numerada por el simulador) o por rectangulos; se valida contra el mapa como `zonas_espera`; encaja con el modelo INIT-10 (zonas como capa) | Un concepto mas; `WorkGroup` queda como esta (informativo) |

**Recomendacion: concepto nuevo.** `WorkGroup` no se toca ahora; en INIT-10
etapa 2 se decide si desaparece o pasa a significar "zona de datos maestros"
(por ejemplo, para importar zonas desde un WMS que las traiga).

### 3.4 Esquema y edicion web

```json
"zonas_picking": {
  "enabled": true,
  "zonas": {
    "Z1": {"pasillos": [1, 2, 3]},
    "Z2": {"pasillos": [4, 5, 6]},
    "Z3": {"pasillos": [7, 8]},
    "ZR": {"rectangulo": {"desde": [1, 3], "hasta": [10, 14]}}
  },
  "robo_de_trabajo": { ... ver seccion 4 ... }
}
```

y en cada grupo de la flota (`agent_types[i]` / `personas[i]`), al lado de
`work_area_priorities`:

```json
"zone_priorities": {"Z1": 1, "Z2": 2}
```

- Una ubicacion pertenece a la zona del pasillo que la contiene (o del
  rectangulo). Ubicaciones sin zona = "sin zonificar": las toma cualquiera
  (aviso `[WARN] 24 ubicaciones no estan en ninguna zona`). Superposicion de
  zonas = error con la celda repetida.
- Grupo sin `zone_priorities` = todas las zonas con prioridad 1 (compatible
  hacia atras; el canonico no cambia). Gruas: por defecto todas las zonas
  (las areas High/Special estan mezcladas en todos los pasillos: verificado
  en el mapa, patron `HH/GG/SH...` por bloques de 2 filas), pero pueden
  zonificarse igual si el Director quiere gruas por sector.
- **Pareja** = dos grupos (o un grupo de `cantidad: 2`) con el mismo
  `zone_priorities`. Con el cupo por pasillo de 2, la pareja nunca bloquea.
- Web: en la card "Equipo por Area" del tab Flota, una tabla "Zonas" con los
  pasillos numerados sobre una miniatura del mapa (la misma que dibuja
  `/api/layout`), boton "Repartir pasillos en N zonas iguales" (genera
  Z1..ZN), y por grupo un selector de zonas con prioridad, con la misma
  validacion de cobertura que hoy tienen las areas ("pasillo 4 sin ningun
  grupo": bloquea Run/Aplicar). `MANUAL_CONFIGURACION.md` con el card nuevo.
- Motor: `core/zones.py` (deduccion de pasillos compartida con `aisles.py`,
  mapa ubicacion -> zona, prioridades efectivas: mismo patron que
  `core.work_areas.effective_work_area_priorities`, con `[WARN]` por zona
  declarada que no existe); `dispatcher`: nuevo filtro
  `_filtrar_por_zona_prioridad` aplicado despues del de area en las 4
  estrategias, y el pool del doble barrido restringido a la zona (asi el
  recorrido no se va de la zona por `pick_sequence`); `operators`: nada.
  `config_schema.py`: `ZonasPickingConfig`, `zone_priorities` en
  `AgentTypeConfig` y `PersonaGrupoConfig`.

### 3.5 Rendimiento esperado y como medirlo

En el canonico estocastico la demanda es uniforme por ubicacion, asi que el
desbalance sera pequeno y la ganancia de caminata deberia verse directa:
menos pasillos por recorrido, arranques repartidos, menos `replan_waits`.
Con pedidos reales (deterministas, ABC), el desbalance aparece y ahi se mide
el robo de trabajo. Escenarios A/B (semilla 42, uno por vez):

| Escenario | Sin zonas | Con 4 zonas de 2 pasillos (8 a pie: parejas) | Con zonas + robo |
|---|---|---|---|
| 8+8 repartido, estocastico | 12.666 s hoy; objetivo tras (d)+(a): ~3.000 s | menor caminata por tarea; jornada <= la anterior | igual o mejor |
| 4+4 repartido | 4.450 s | 2 zonas de 4 pasillos; medir | medir |
| Determinista con demanda sesgada (un archivo de pedidos con el 60% de las lineas en los pasillos 1-3) | referencia | **desbalance visible**: Z1 termina mucho despues; ociosidad de Z2/Z3 alta | el robo lo corrige; medir cuanto |

Metricas: jornada; por operario `% tiempo ocioso` y `tareas`; por zona
`backlog(t)` (pendientes en el tiempo) y `t_fin_zona`; `celdas por tarea`
(caminata); `tareas_robadas` y `% tiempo fuera de zona`; congestion
(`replan_waits`, `pasillo_esperas`, co-ocupaciones). Criterio de "zonas bien
dimensionadas": `max(t_fin_zona) - min(t_fin_zona)` chico respecto de la
jornada (por ejemplo < 10%).

---

## 4. Pregunta 3 — Equilibrio de carga: robo de trabajo

### 4.1 Regla recomendada

Cuando un operario pide trabajo (`solicitar_asignacion`) y en sus zonas no
queda nada elegible, o queda menos que `umbral_propio` tareas:

1. Se elige la zona **mas atrasada**: mayor `backlog / operarios_asignados`
   (pendientes por persona), desempate por cercania (distancia por camino
   desde la posicion actual a la boca del pasillo mas cercano de esa zona).
   `preferencia: "mas_atrasada" | "mas_cercana"`.
2. Dentro de esa zona se toma trabajo **desde el extremo opuesto** al que
   recorre el dueño: si el dueño barre por `pick_sequence` ascendente, el
   ladron arma su recorrido desde el `pick_sequence` **maximo** hacia abajo
   (`desde: "final_de_secuencia"`). Asi los dos avanzan uno hacia el otro y se
   encuentran una sola vez, en vez de perseguirse. Con (d) activo nunca
   quieren el mismo hueco; con el cupo, nunca son mas de 2 en un pasillo.
3. El ladron arma un recorrido **corto** (`max_tareas_robadas`, default =
   `max_wos_por_tour / 2`) para volver pronto a su zona si aparece trabajo
   (olas, pedidos nuevos).
4. **Nunca se roba a una zona cuyo backlog por persona sea menor que el
   propio** (si no, dos zonas se roban mutuamente: livelock de reparto). Es un
   orden total sobre las zonas en cada instante: sin ciclos.
5. Un solo operario: sin `zonas_picking`, o con todas las zonas en su
   `zone_priorities`, el filtro es la identidad y el robo nunca se dispara.

```json
"robo_de_trabajo": {
  "enabled": true,
  "umbral_propio": 0,
  "preferencia": "mas_atrasada",
  "desde": "final_de_secuencia",
  "max_tareas_robadas": 10
}
```

Alternativas consideradas: **zonas dinamicas** (recalcular limites de zona
cada N minutos segun backlog): mas balance, pero pierde el sentido operativo
de "mi zona" y es dificil de explicar al cliente; queda para despues de
medir. **Sin robo** (zonas estrictas): es lo que hacen algunos almacenes con
pick-and-pass y colas entre zonas; en la variante paralela deja ociosos: no
recomendada como default, si como opcion (`enabled: false`).

### 4.2 Como se mide el trade-off

Con los escenarios de 3.5: (i) jornada y `t_fin_zona` maximo-minimo (balance);
(ii) `tareas_robadas`, `% tiempo fuera de zona` (cuanto se viola la
organizacion); (iii) `celdas por tarea` del ladron vs del dueño (el robo
cuesta caminata); (iv) `pasillo_esperas` y `replan_waits` con y sin robo (el
robo aumenta encuentros; el cupo los contiene). El A/B del proyecto
(experimentos con semillas pareadas) sirve tal cual: A = zonas sin robo, B =
zonas con robo, 5 replicas.

---

## 5. Orden de trabajo sugerido

1. **(d) BK-23: una ubicacion, un operario + consolidar por ubicacion** (1
   dia; baseline nuevo). Es la causa medida y es realismo puro.
2. **(a) Cupo por pasillo con salteo** (3-4 dias), medir 8+8 repartido: 0
   rendiciones, `max_en_pasillo` <= 2.
3. **Zonificacion + robo** (4-5 dias), medir con demanda uniforme y sesgada.
4. Cesion por solicitud (F2 del plan) queda como estaba: ociosos y fila.
   Despues de 1-3 medir si todavia hace falta.

El cupo y la zona comparten la deduccion y numeracion de pasillos: hacerla
una sola vez (`aisles.py`) y que `zones.py` la consuma.

---

## 6. Decisiones que necesita tomar el Director

- **D-B1. BK-23 encendido por defecto** (una ubicacion, un operario +
  consolidar por ubicacion). Mueve el baseline. Recomendacion: si.
- **D-B2. Cupo por pasillo**: capacidad por defecto = ancho del pasillo (2 en
  v3); encender en el canonico tras medir. Recomendacion: si.
- **D-B3. Que hace el que encuentra un pasillo lleno**: saltear al siguiente
  pasillo de su recorrido y volver (recomendado) o esperar en una celda de la
  boca (1 por boca, en el corredor).
- **D-B4. Zonificacion como concepto nuevo `zonas_picking` en config + web**,
  sin reutilizar `WorkGroup`. Recomendacion: si; `WorkGroup` se revisa en
  INIT-10.
- **D-B5. Unidad de la zona**: pasillos numerados por el simulador
  (recomendado) y, opcional, rectangulos.
- **D-B6. Gruas zonificadas o libres**: por defecto libres (todas las zonas);
  el cliente puede zonificarlas.
- **D-B7. Robo de trabajo encendido por defecto** con `umbral_propio: 0`,
  `mas_atrasada`, `final_de_secuencia`. Recomendacion: si, y medir con
  demanda sesgada antes de fijar los valores.
- **D-B8. Estrategia por defecto**: "Ejecucion de Plan" manda a todos al
  pasillo 1 al arrancar (1.2). Con zonas deja de importar; sin zonas,
  considerar "Optimizacion Global" (primera WO por costo desde la posicion)
  como default del canonico. Es un cambio de negocio: solo si el Director lo
  quiere.

---

## 7. Fuentes

Codigo leido: `dispatcher.py` (`solicitar_asignacion`, `_asignar_picks`,
`_seleccionar_work_orders_candidatos`, `_estrategia_ejecucion_plan`,
`_filtrar_por_area_prioridad`, `_construir_tour_por_secuencia`,
`_marcar_asignados`, `notificar_completado_individual`, `finalizar_tour`),
`operators.py` (`_execute_pick_tour`, `_recorrer_tramo`, `_tw_replan_params`,
`_tomar_turno_estacion`, `_esperar_sin_estorbar`), `stations.py`,
`spacetime_planner.py`, `idle_zones.py`, `core/work_areas.py`,
`warehouse.py` (`WorkOrder.work_group`, `_obtener_work_group`),
`data_manager.py` (columna `WorkGroup`), `config_schema.py`, `layouts/WH1
v3.tmx` + `warehouse.db` (mapa 32x43 impreso con areas por celda; 384
ubicaciones, `pick_sequence` en serpiente por pasillo: columna 9 ascendente
97..120, columna 10 descendente 144..121), replay
`output/simulation_20260920_022055` (`replay_*.jsonl`,
`timewindow_shadow_report_*.json`: 25.532 segmentos, 23.910 sin plan, 2
`exec_fallbacks`, 676 `exec_blocked`; `congestion_report_*.json`: 4
co-ocupaciones, hotspots (3,29) arranque, (10,17), (10,19), (11,27)),
`docs/PLAN_BK25_ESTACION_DESCARGA.md`, `docs/BACKLOG.md` (BK-23).

Externas:

- Parikh, Meller, "A note on worker blocking in narrow-aisle order picking
  systems when pick time is non-deterministic" y "Estimating picker blocking
  in wide-aisle order picking systems" (IIE Transactions, 2010/2009):
  https://www.researchgate.net/publication/232913232_Estimating_picker_blocking_in_wide-aisle_order_picking_systems
  (tipos de bloqueo: in-the-aisle vs pick-point:
  https://www.researchgate.net/figure/Types-of-picker-blocking-a-in-the-aisle-picker-blocking-and-b-pick-point-blocking_fig2_272119361).
- Gue, Meller, Skufca, "The effects of pick density on order picking areas
  with narrow aisles", IIE Transactions 38(10), 2006:
  https://www.semanticscholar.org/paper/c67b800ae5fd6d7e38bd0d67196f6ad81c28ed09
- Hong, Johnson, Peters, "Batch picking in narrow-aisle order picking systems
  with consideration for picker blocking", EJOR 2012:
  https://www.researchgate.net/publication/257196172
- Simulacion de picking con congestion y balance entre zonas (IJSIMM 17(3),
  2018): http://www.ijsimm.com/Full_Papers/Fulltext2018/text17-3_431-443.pdf
- Zone vs batch picking, desbalance de carga (Optioryx):
  https://www.optioryx.com/blog/batch-vs-zone-picking ; seleccion entre
  batch y zone picking en un centro de distribucion:
  https://www.researchgate.net/publication/222686248
- Analisis basado en agentes del bloqueo de pickers (AnyLogic, paper):
  https://www.anylogic.com/upload/iblock/474/474285c60acd56d748ba8fe7d5950371.pdf
- Adendas previas del consultor (estacion con turno; cesion por solicitud):
  `docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md`,
  `docs/PROPUESTA_DISENO_CEDER_EL_PASO.md`.
