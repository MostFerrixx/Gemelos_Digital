# INVESTIGACION - SOLUCIONES A CONGESTION / DEADLOCK (Iniciativa #2)

> Rama: feature/allocation-layer-v12.1
> Autor: Cerebellum (Arquitecto Senior / Logistica de Almacenes)
> Tipo: INVESTIGACION + ANALISIS COMPARATIVO. NO se implementa nada aqui.
> Objetivo: decidir la arquitectura de solucion a la congestion/deadlock mas
>   robusta a futuro, reuniendo el MAXIMO de enfoques posibles (incluso cambios
>   de arquitectura) y comparandolos, sin encasillarse en una sola opcion.
> ASCII puro a proposito (Ley #4 / convencion de los otros docs).
> DOCUMENTO VIVO: se escribe incrementalmente. El indice/checklist de abajo dice
>   que enfoques ya estan investigados y cuales faltan, para retomar si me corto.

---

## 0. INDICE / CHECKLIST DE PROGRESO

Leyenda: [ ] pendiente  [~] en progreso  [x] hecho

- [x] 1. Causa raiz del deadlock (anclada en codigo real)
- [x] 2. Catalogo de enfoques de solucion (15 enfoques: que es, encaje, pros, contras, esfuerzo, riesgo, robustez)
  - [x] 2.1  Cesion por prioridad + aging + backoff (deadlock recovery local)
  - [x] 2.2  Deteccion de deadlock + recovery (grafo wait-for / watchdog activo)
  - [x] 2.3  Deadlock AVOIDANCE (banker's algorithm / orden total de recursos)
  - [x] 2.4  Reduccion de presion del embudo (cap-k en depot, dispersion, cola de salida)
  - [x] 2.5  Reglas de trafico: pasillos direccionales / one-way / lanes
  - [x] 2.6  Semaforos de interseccion / control por nodos criticos
  - [x] 2.7  Capacidad-k en cuellos + muelles de staging como Resource (colas FIFO)
  - [x] 2.8  Cooperative A* / WHCA* (reserva espacio-temporal, ventana movil)
  - [x] 2.9  Conflict-Based Search (CBS) (MAPF optimo de dos niveles)
  - [x] 2.10 Prioritized Planning (MAPF priorizado, plan secuencial)
  - [x] 2.11 Time-window routing / reserva de intervalos (AGV, almacenes reales)
  - [x] 2.12 Campos de potencial / flow fields (descentralizado, navegacion por campo)
  - [x] 2.13 Reserva de RUTA vs reserva de CELDA (granularidad)
  - [x] 2.14 Centralizado vs descentralizado (eje transversal de decision)
  - [x] 2.15 Repathing dinamico reactivo (rodear atascos; ya previsto como F4)
- [x] 3. Tabla comparativa (robustez, fidelidad, esfuerzo, riesgo, encaje F1/F2)
- [x] 4. Recomendacion final (robusta a futuro) + plan de migracion por fases
- [x] 5. Opcion minima viable (desbloqueo rapido) + trade-off
- [x] 6. Referencias

---

## 1. CAUSA RAIZ DEL DEADLOCK (anclada en codigo real)

### 1.1 El modelo de movimiento actual (que hace el codigo hoy)

Cadena viva verificada por lectura directa (rama feature/allocation-layer-v12.1):

- **Mapa estatico**: `layout_manager.py::_build_collision_matrix()` produce
  `collision_matrix[y][x]` (bool, caminable/bloqueado) UNA vez al cargar el TMX.
  Nunca cambia en runtime.
- **Pathfinding estatico y puramente espacial**: `pathfinder.py::find_path(start, goal)`
  es A* 8-direccional (cardinales coste 1.0, diagonales sqrt(2)), heuristica octile.
  `is_walkable(x,y)` consulta SOLO `collision_matrix` + limites. NO conoce a ningun
  otro agente, NO tiene dimension temporal. La firma es `find_path(start, goal)`:
  no admite "evitar estas celdas" ni un instante `t` (dato clave para 2.8-2.11).
- **Ruta precalculada por tour**: `route_calculator.py::calculate_route()` calcula
  `segment_paths` (una lista A* por WorkOrder + retorno) UNA sola vez al inicio del
  tour. No se recalcula a mitad de tour.
- **Lazo de movimiento unico (refactor F0)**: `operators.py::BaseOperator._recorrer_tramo`
  recorre `segment_path[1:]` celda a celda. Es el unico punto donde se mueve un agente.
- **Capa de ocupacion dinamica (Iniciativa #2)**: `congestion_manager.py::CongestionManager`
  vive aparte del mapa estatico. En `mode:instrument` solo observa co-ocupaciones.
  En `mode:cell` media la exclusion con RESERVA PEREZOSA: `owner: {(x,y): agent_id}`
  (cap 1) + `release_events: {(x,y): simpy.Event}` creados on-demand.

### 1.2 La rama F3 (cell mode) paso a paso, y por que produce deadlock

El nucleo es el lazo F3 de `_recorrer_tramo` (operators.py ~377-421). Por cada celda:

```
nxt = siguiente celda del path; cur = current_position
while not cm.try_acquire(self.id, nxt):     # nxt ocupada por otro
    rel = cm.release_event(nxt)
    yield rel | self.env.timeout(W)          # ESPERA: o se libera nxt, o vence W
    ... (si waited >= hard_cap: registra incidente y SIGUE esperando)
self._set_pos(nxt)                           # ya tengo nxt
yield self.env.timeout(time_per_cell*speed)
cm.release(self.id, cur)                      # recien ahora suelto cur
```

Observacion clave: el agente **adquiere `nxt` ANTES de soltar `cur`** (linea 415 vs
421). Esto es deliberado (anti-F10: nunca quedarse sin celda). Pero es exactamente
**hold-and-wait**: el agente RETIENE su celda actual mientras ESPERA la siguiente.

### 1.3 Las cuatro condiciones de Coffman estan TODAS presentes

Un deadlock requiere las cuatro condiciones de Coffman simultaneamente. La F3 las
cumple todas:

1. **Exclusion mutua**: cada celda es cap 1 (`owner` dict). CONFIRMADO por diseno.
2. **Hold-and-wait**: el agente conserva `cur` mientras hace `yield` esperando `nxt`
   (operators.py: `_set_pos(nxt)` y `release(cur)` van DESPUES del wait-loop).
3. **No preemption**: `try_acquire` jamas le quita una celda a su dueno; `release`
   solo lo llama el propio dueno. No hay cesion forzada. El watchdog F3 es solo
   DETECTOR (deja traza, no resuelve) -> `congestion_manager.py::watchdog_proc`.
4. **Espera circular**: confirmada empiricamente en el embudo del depot.

### 1.4 Evidencia empirica del ciclo (del PROGRESO, RESULTADO F3)

Stress 20 agentes (14 Ground + 6 Forklift), mode:cell, embudo del depot (~celdas
(0..6, 26..29)). Grafo wait-for observado:

```
GroundOp-01 @(4,28) espera (4,27) <- la tiene GroundOp-13
GroundOp-02 @(2,29) espera (2,28) <- la tiene GroundOp-06
GroundOp-03 @(3,28) espera (3,27) <- la tiene GroundOp-07
Forklift-01 @(6,29) espera (5,29) <- la tiene GroundOp-09
```

8 agentes quedan ACTIVOS sin moverse; el watchdog dispara STALL en bucle; la sim
NO termina (`terminated=False`, `freeze=True` por cap de wallclock). El reloj de
SIM se dispara a t~60000 porque los `timeout(W)` siguen avanzando el tiempo sin que
nadie progrese (pista: el tiempo avanza pero `total_moves` se estanca).

La exclusion MECANICA es correcta: co-ocupaciones reales cayeron de 62 (baseline
F2) a 1 (y esa 1 es un sub-bug de carrera de spawn-claim del ancla idx0, no de
transito). El problema NO es la exclusion: es que **introdujo reserva de recurso
con 3 de las 4 condiciones de Coffman y SIN ninguna de las tres salvaguardas que
el propio plan exige** (timeout-con-resolucion, cesion/backoff, y reduccion de
presion del embudo). El timeout W existe pero NO resuelve nada: al vencer, el
agente simplemente vuelve a esperar la MISMA celda (no cede, no repathea, no
retrocede). Es un timeout sin politica de salida => espera infinita disfrazada.

### 1.5 Sintesis de la causa raiz

> El deadlock NO es un bug de implementacion de la exclusion (esa funciona). Es un
> deadlock ESTRUCTURAL: 20 agentes nacen dispersos en un bloque ~7x4 pero deben
> DRENAR por el mismo embudo de 1-celda-de-ancho hacia/desde el depot. Con
> exclusion cap-1 + hold-and-wait + sin preemption, una espera circular en ese
> embudo es inevitable. Romperlo exige eliminar AL MENOS una condicion de Coffman:
>   - quitar hold-and-wait (soltar cur al esperar) -> arriesga I1 y "perder" celda,
>   - meter preemption (cesion por prioridad / retroceso) -> rompe el ciclo,
>   - prevenir la espera circular por construccion (orden total / reglas de trafico
>     direccionales / planificacion espacio-temporal que nunca genera el ciclo),
>   - o reducir la densidad para que el ciclo no llegue a formarse (paliativo).
>
> La eleccion entre estas vias ES la decision de arquitectura que esta investigacion
> debe resolver.

---

## 2. CATALOGO DE ENFOQUES DE SOLUCION

Cada enfoque se documenta con: QUE ES, ENCAJE en esta arquitectura SimPy/grilla,
QUE RESUELVE, PROS, CONTRAS, ESFUERZO, RIESGO, ROBUSTEZ/ESCALABILIDAD A FUTURO.
Marco mental: un deadlock necesita las 4 condiciones de Coffman; cada enfoque
ataca una o varias (exclusion / hold-and-wait / no-preemption / espera circular),
o reduce la probabilidad de que el ciclo se forme.

Eje transversal (ver 2.14): CENTRALIZADO (un planificador conoce todos los planes
y los hace compatibles antes de moverse) vs DESCENTRALIZADO (cada agente decide
local en runtime y se resuelven conflictos reactivamente). La F3 actual es
descentralizada reactiva pura. Casi todas las tecnicas "fuertes" de MAPF son
centralizadas o semi-centralizadas.

---

### 2.1  Cesion por prioridad + aging + backoff (deadlock RECOVERY local)

QUE ES. Cuando un agente lleva esperando una celda mas de W y detecta contencion
mutua (el dueno de `nxt` tambien esta esperando), se comparan claves
`(prioridad_efectiva, agent_id)`. El "perdedor" CEDE: suelta su celda y retrocede
a una celda libre adyacente, dejando pasar al ganador. `prioridad_efectiva`
incorpora AGING (sube con el tiempo esperado) para que nadie quede en starvation
(F4). Backoff con jitter al reintentar para romper sincronias (anti-livelock F3).
Ataca la condicion de Coffman de NO-PREEMPTION (introduce preemption suave) y, via
backoff, la espera circular.

ENCAJE. Es justo lo que el plan asigna a FASE 5 (seccion 4.7 del PLAN). Encaja de
lleno en el lazo F3 ya existente: dentro del `while not try_acquire(nxt)`, tras
vencer W, anadir la rama de cesion. Requiere: (a) que `CongestionManager` exponga
"quien posee nxt y en que estado esta" (ya tiene `owner`; falta exponer status del
dueno), (b) una operacion atomica retroceder = `release(cur)+_set_pos(prev_libre)+
claim(prev_libre)` (ya existe `_jump_to`, reutilizable), (c) clave de prioridad
determinista (work_area_priorities ya existe + agent_id; aging por tiempo de sim).

QUE RESUELVE. Rompe la espera circular YA FORMADA: es deadlock recovery. Es la red
que el propio RESULTADO F3 identifico como la cura formal del freeze observado.

PROS. Maxima fidelidad de simulacion (modela el "alguien cede el paso" real de un
almacen). Descentralizado: no necesita un planador global. Encaja incrementalmente
sobre F1/F2/F3 sin reescribir nada. Con aging garantiza I2 (sin freeze) y no
starvation. Determinista si los desempates son por tupla ordenada (I5).

CONTRAS. Es la pieza mas delicada (el Director ya fallo aqui una vez). La cesion mal
hecha genera LIVELOCK (dos ceden a la vez, rechocan) -> exige jitter + asimetria por
(prioridad,agent_id). El retroceso necesita una celda libre adyacente; si no hay
(boxed-in, CB11) hay que encadenar cesiones (efecto domino) o esperar en sitio. En
embudos de 1-celda-de-ancho con 8 agentes en cadena, la cesion puede requerir mover
a varios "aguas atras" en orden -> hay que ordenar el rescate del ciclo, no solo
del par. Resolver pares no basta para un ciclo de longitud N.

ESFUERZO. MEDIO. ~1 fase (la F5 planeada). Mucho del andamiaje ya esta (owner,
release_events, watchdog detector, _jump_to, prioridades).

RIESGO. MEDIO-ALTO. Es el punto historicamente fragil. Mitigable con: tests de
estres deterministas (ya existen), watchdog que valida progreso monotono, y un
"deadlock resolver" que opere sobre el CICLO detectado (no solo el par).

ROBUSTEZ A FUTURO. BUENA pero no total. Recovery reactivo escala a mas agentes en
densidad MEDIA. En densidad MUY alta (embudo saturado permanente) la tasa de
cesiones/livelock-risk sube; conviene combinar con reduccion de presion (2.4) y/o
reglas de trafico (2.5) que evitan que el ciclo se forme. Es decir: excelente como
RED DE SEGURIDAD universal, subuptima como UNICA estrategia.

---

### 2.2  Deteccion de deadlock + recovery por grafo wait-for (watchdog ACTIVO)

QUE ES. Mantener un grafo wait-for explicito (arista A->B si A espera una celda
cuyo dueno es B). Periodicamente (o al entrar en wait) buscar CICLOS en el grafo;
si hay ciclo, romperlo eligiendo una victima (menor prioridad) y forzando su
cesion/retroceso/repath. Es la version "global y consciente" del watchdog: el F3
actual solo detecta STALL global (no movimiento) pero NO sabe QUIEN espera a QUIEN
ni rompe nada.

ENCAJE. `CongestionManager` ya tiene `owner` y sabe quien espera (puede registrar
`waiting_on: {agent_id: cell}`). Construir el grafo es O(agentes). El watchdog ya
es un proceso SimPy (`watchdog_proc`); se le anade la deteccion de ciclos + la
orden de cesion. Encaja sobre F3 sin tocar el lazo de movimiento (la cesion la
ejecuta el agente victima via un Event que el watchdog dispara).

QUE RESUELVE. Deadlock de espera circular de cualquier longitud N (no solo pares):
ataca el ciclo completo. Es deteccion+recovery clasica (reactiva), barata en
overhead diario, con coste solo cuando hay deadlock.

PROS. Resuelve ciclos largos que la cesion local por pares (2.1) puede no romper.
Garantiza I2 por construccion (todo ciclo detectado se rompe). Diagnostico
riquisimo (loguea el ciclo exacto -> ya lo hace a medias el RESULTADO F3).
Complementa 2.1: 2.1 es la accion local, 2.2 es el cerebro que decide la victima
correcta en un ciclo.

CONTRAS. La "ventana" de deteccion introduce latencia (la sim avanza algo en
deadlock antes de resolver). Elegir bien la victima en ciclos enlazados (varios
ciclos compartiendo aristas) no es trivial. Sigue siendo recovery: deja que el
deadlock OCURRA y luego lo cura -> menos elegante que avoidance (2.3) o prevencion
(2.5).

ESFUERZO. MEDIO (sobre 2.1; comparten infraestructura). Solo deteccion = BAJO;
deteccion+recovery robusto = MEDIO.

RIESGO. MEDIO. La recovery comparte fragilidad con 2.1. La deteccion sola es de
bajo riesgo (solo observa).

ROBUSTEZ A FUTURO. ALTA como salvaguarda. Es el estandar industrial AGV de
"detection + recovery" cuando la prevencion pura es demasiado restrictiva. Escala
bien si el numero de agentes en deadlock simultaneo es acotado. Recomendado SIEMPRE
como red de ultima instancia, combinado con una estrategia que reduzca la
frecuencia de deadlocks (2.3/2.4/2.5).

---

### 2.3  Deadlock AVOIDANCE (banker's algorithm / orden total de recursos)

QUE ES. En vez de detectar y curar, CONCEDER una celda solo si el estado resultante
sigue siendo SEGURO (existe un orden en que todos los agentes pueden terminar). El
banker's algorithm (Dijkstra) exige que cada proceso declare su demanda maxima de
recursos por adelantado y simula la asignacion para verificar que queda una
secuencia segura. Variante mas simple y aplicable: ORDEN TOTAL de adquisicion de
recursos (todos adquieren celdas en orden lexicografico (x,y)), que elimina por
construccion la espera circular (una de las 4 de Coffman).

ENCAJE. Banker's PURO encaja MAL: requiere conocer por adelantado TODAS las celdas
que cada agente va a necesitar (su demanda maxima). Aqui la ruta se precalcula por
tour (`route_calculator`), asi que SI se conoce el path completo del tramo -> es
factible declarar la demanda. Pero verificar "estado seguro" sobre un grid con N
agentes y rutas largas es caro y conservador (deniega muchos avances seguros). El
ORDEN TOTAL si encaja barato, pero solo aplica cuando un agente adquiere VARIAS
celdas a la vez (swaps, diagonal+ortogonal); para la adquisicion de UNA celda por
paso (caso comun) el orden total no previene nada (el ciclo se forma entre pasos de
distintos agentes, no dentro de una adquisicion multiple).

QUE RESUELVE. Elimina el deadlock ANTES de que ocurra (proactivo). En su version
fuerte (banker), garantiza ausencia total de deadlock sin necesidad de recovery.

PROS. Garantia formal de no-deadlock (no "casi nunca", sino nunca). Sin livelock de
cesion. Atractivo teorico.

CONTRAS. Banker es CONSERVADOR: rechaza avances que en realidad eran seguros ->
baja throughput y puede serializar de mas (sintoma F9). Caro de computar en grid
grande con muchos agentes (chequeo de secuencia segura por cada concesion). Requiere
declarar demanda maxima -> acopla la capa de espacio con el route_calculator de
forma rigida. El orden total por celda NO resuelve el caso comun de este deadlock
(es contencion entre pasos atomicos de agentes distintos, no adquisicion multiple).
Poco usado en MAPF moderno justamente por conservador.

ESFUERZO. ALTO (banker real) / BAJO (orden total, pero de impacto limitado aqui).

RIESGO. MEDIO-ALTO: el riesgo no es el freeze sino la PERDIDA DE THROUGHPUT y la
complejidad de calibrar para que no serialice.

ROBUSTEZ A FUTURO. TEORICAMENTE alta (cero deadlocks), PRACTICAMENTE limitada por
el coste y el conservadurismo. Mejor como CONCEPTO que inspira la prevencion por
reglas (2.5) que como algoritmo banker literal. El orden total si conviene
adoptarlo como invariante barato para adquisiciones multiples (swap/diagonal).

---

### 2.4  Reduccion de presion del embudo (cap-k depot, dispersion, cola de salida)

QUE ES. Atacar la DENSIDAD, no el deadlock directamente: si por el embudo nunca hay
suficientes agentes a la vez como para cerrar un ciclo, el deadlock no se forma. F2
ya hizo parte (stagger temporal + andenes de salida distintos). Falta: (a) modelar
la SALIDA del depot como recurso de capacidad k (solo k agentes "en transito de
salida" simultaneos; el resto espera en una cola FIFO en su anden, fuera del
embudo), (b) dispersar mas los andenes (no en un bloque 7x4 pegado al cuello),
(c) liberar agentes por oleadas.

ENCAJE. Encaja muy bien y es de bajo acoplamiento. `simpy.Resource(capacity=k)`
para la "boca" del embudo; el agente hace `yield request` antes de entrar a la zona
de cuello y lo libera al salir. Reusa el stagger F2 y `_compute_departure_lanes`.
No toca el lazo de movimiento ni la exclusion por celda.

QUE RESUELVE. La CAUSA PROXIMA del freeze observado (20 agentes drenando por 1
cuello). Reduce drasticamente la probabilidad de espera circular sin necesidad de
cesion. Es exactamente la recomendacion (B) del RESULTADO F3 de Cerebellum.

PROS. Simple, robusto, bajo riesgo, idiomatico SimPy. Modela algo REAL (un muelle/
puerta no deja salir a 20 a la vez). Reduce la carga sobre cualquier mecanismo de
recovery posterior. Calibrable por un solo parametro (k).

CONTRAS. Es PALIATIVO, no cura: con suficientes agentes o un layout con cuellos
internos (no solo el del depot), el deadlock puede reaparecer aguas adentro. No
garantiza I1 por si solo (es ortogonal a la exclusion). Mal calibrado (k muy bajo)
serializa y baja throughput; (k muy alto) no previene nada. Mueve el problema:
puede crear cola larga que se propague hacia atras (F8) si no se ubica fuera de
flujo.

ESFUERZO. BAJO-MEDIO. Reusa F2.

RIESGO. BAJO. Es aditivo y gateado; flag off = identico.

ROBUSTEZ A FUTURO. MEDIA por si solo (no es garantia), ALTA como COMPONENTE de una
solucion combinada: baja la presion para que el mecanismo de exclusion + recovery
opere en regimen comodo. Casi siempre vale la pena tenerlo.

---

### 2.5  Reglas de trafico: pasillos direccionales / one-way / lanes

QUE ES. Imponer SENTIDO a los pasillos: ciertas filas/columnas son one-way (solo
se transita en una direccion). En layouts de almacen reales con pasillos estrechos,
el sentido es fijo (literatura AGV). Esto ELIMINA POR CONSTRUCCION el head-on (F6) y
rompe la simetria que genera la mayoria de las esperas circulares (no puede haber
A->B y B->A en el mismo pasillo si el pasillo es one-way).

ENCAJE. Requiere METADATA por celda/arista: una direccion permitida. Se puede
derivar del TMX (capa nueva de "direccion") o de config. El pathfinder A* tendria
que respetar el sentido: `get_neighbors` filtraria vecinos segun la direccion de la
arista. Es un cambio en el grafo de busqueda (de no dirigido a DIRIGIDO), no en la
mecanica de exclusion. Encaja con la exclusion por celda (2.1-2.2) que sigue siendo
la red de seguridad para los cruces (donde el one-way no aplica).

QUE RESUELVE. Head-on en ancho 1 (F6, irresoluble por espera simple) y gran parte
de la espera circular en pasillos. Convierte el problema dificil (bidireccional) en
uno facil (flujo dirigido tipo circuito).

PROS. PREVENTIVO y muy robusto: el ciclo no se forma en los pasillos. Es como
operan los almacenes y los sistemas AGV reales -> ALTA fidelidad. Reduce
muchisimo la carga sobre recovery. Escala excelente (mas agentes = mas flujo
ordenado, no mas deadlocks). Determinista.

CONTRAS. Requiere definir las direcciones (trabajo de modelado del layout; puede
necesitar editar el TMX o una capa de config). Alarga algunas rutas (no puedes ir
"contra" el sentido -> rodeos tipo manzana de ciudad). No elimina conflictos en los
CRUCES/intersecciones (ahi sigue hace falta 2.1/2.2/2.6). Si el layout tiene
callejones sin salida one-way mal puestos, puede desconectar el grafo -> hay que
validar conectividad dirigida. Cambia el pathfinder (de no dirigido a dirigido):
toca codigo "sano" actual.

ESFUERZO. MEDIO-ALTO. Modelado de direcciones + pathfinder dirigido + validacion de
conectividad. Pero es trabajo ACOTADO y de una sola vez.

RIESGO. MEDIO. Toca el pathfinder (codigo vivo). Mitigable: gatear por config, y si
no hay capa de direccion definida, comportamiento = no dirigido actual.

ROBUSTEZ A FUTURO. MUY ALTA. Es la estrategia que mejor escala y la mas usada en
almacenes/AGV reales. La inversion de modelado se amortiza: cada agente nuevo
circula ordenado. Combinada con exclusion por celda en cruces + recovery, es
practicamente a prueba de deadlock.

---

### 2.6  Semaforos de interseccion / control por nodos criticos (token/reserva)

QUE ES. Tratar cada CRUCE (celda de grado >= 3) como una interseccion controlada:
solo un agente (o k, segun ancho) puede estar "dentro" de la interseccion a la vez,
admitido por un TOKEN/reserva. Es el paradigma de Autonomous Intersection Management
(AIM): los vehiculos piden y reciben un slot/token para cruzar; una politica de
admision basada en token decide quien pasa. Discretizar el espacio de la
interseccion de modo que dos no ocupen la misma sub-celda.

ENCAJE. Identificar cruces del grid (analisis de grado del grafo, una vez). Cada
cruce = `simpy.Resource(capacity=k_cruce)` o un token gestionado por
`CongestionManager`. El agente hace `yield request` del token del cruce antes de
entrar y lo libera al salir. Encaja sobre la exclusion por celda como capa
ESPECIALIZADA en los puntos calientes (los cruces son los hotspots reales, ver F1:
hotspots en cruces/pasillos).

QUE RESUELVE. Conflictos en intersecciones (el punto donde one-way no ayuda). Con
una politica de admision deadlock-free (existen algoritmos AIM probados deadlock- y
starvation-free), garantiza progreso en los cruces.

PROS. Granularidad quirurgica: control fuerte SOLO donde hace falta (cruces),
dejando los pasillos libres. Modela bien la realidad (semaforos/cruces regulados).
Combina perfecto con one-way (2.5): one-way en pasillos + semaforo en cruces =
cobertura completa. Hay teoria probada de deadlock-freeness.

CONTRAS. Hay que identificar y modelar los cruces. La politica de admision
deadlock-free no es trivial (un token por cruce evita colision DENTRO del cruce,
pero un agente que toma un cruce y espera el siguiente puede volver a crear espera
circular ENTRE cruces -> necesita orden o reserva de la cadena de cruces). Mas
entidades que gestionar.

ESFUERZO. MEDIO. (Mas si se quiere la politica de admision con garantia formal.)

RIESGO. MEDIO. Aditivo y gateable.

ROBUSTEZ A FUTURO. ALTA, especialmente combinado con 2.5. Escala bien (el control
es local a cada cruce). Es el complemento natural de los pasillos direccionales.

---

### 2.7  Capacidad-k en cuellos + muelles de staging como Resource (colas FIFO)

QUE ES. Modelar explicitamente los puntos de DESCARGA (staging) y otros cuellos
como `simpy.Resource(capacity=k)` con cola FIFO, donde k = numero de celdas de
muelle. Los agentes que convergen a descargar hacen cola ORDENADA en vez de
apilarse y trabarse. Es el tratamiento canonico de F8 (cuello de staging) del plan.

ENCAJE. SimPy idiomatico puro. `Resource(capacity=k)` por staging; `yield request`
antes de aproximar, release tras descargar. Las celdas de aproximacion se modelan
como zona de espera fuera del flujo. Encaja sobre todo lo demas sin conflicto.

QUE RESUELVE. La cola de descarga (F8) y, en general, cualquier cuello donde la
contencion es por un RECURSO de servicio (no por transito puro). Evita que la cola
de staging se propague hacia atras y congele pasillos.

PROS. Idiomatico, simple, alta fidelidad (las colas de muelle son reales y
DESEABLES de simular: son justo lo que el Director quiere medir). Bajo riesgo.

CONTRAS. Especifico de los puntos de servicio (no resuelve el transito general ni
el embudo del depot por si solo, aunque 2.4 es su gemelo en el lado de SALIDA). Hay
que calibrar k y ubicar las zonas de espera fuera de flujo (si no, la cola misma
bloquea, F8).

ESFUERZO. BAJO-MEDIO.

RIESGO. BAJO.

ROBUSTEZ A FUTURO. ALTA para lo suyo. Es un componente que casi seguro forma parte
de la solucion final (modela la realidad que el gemelo debe capturar). No es una
estrategia anti-deadlock global por si sola.

---

### 2.8  Cooperative A* / WHCA* (reserva ESPACIO-TEMPORAL, ventana movil)

QUE ES. La familia MAPF descentralizada-secuencial mas conocida (Silver 2005).
Cooperative A* (HCA*) planifica los agentes UNO A UNO en un orden dado; cuando
encuentra el path del agente i lo escribe en una TABLA DE RESERVA global indexada
por (x, y, t): ningun agente posterior puede ocupar una celda-tiempo ya reservada.
WHCA* (Windowed HCA*) limita la cooperacion a una VENTANA temporal movil (planifica
en detalle solo los proximos W pasos, repasa periodicamente), repartiendo el computo
y adaptandose a cambios. CO-WHCA* coloca la ventana solo alrededor de conflictos
conocidos. La clave: el path se busca en el espacio-tiempo, asi que la reserva
PREVIENE el conflicto antes de mover (incluye esperas "wait in place" como accion).

ENCAJE. Es un CAMBIO DE ARQUITECTURA del pathfinding. El `pathfinder` actual es
A* PURAMENTE ESPACIAL (`find_path(start, goal)` sobre `collision_matrix`, sin t).
WHCA* exige: (a) un A* espacio-temporal (nodos = (x,y,t), accion "esperar" valida),
(b) una tabla de reserva (x,y,t) compartida, (c) un orden de planificacion entre
agentes, (d) replanificacion por ventana. El `route_calculator` (precalcula la ruta
una vez por tour) tendria que volverse incremental/por-ventana. Es bastante codigo
nuevo, pero la reserva (x,y,t) reutiliza la idea del `owner` dict de
`CongestionManager` extendido con el eje t.

QUE RESUELVE. Conflictos de celda Y de swap por construccion dentro de la ventana:
no hay co-ocupacion porque la reserva la impide al planificar. Reduce muchisimo (no
elimina del todo) los deadlocks: WHCA* puede aun trabarse fuera de la ventana o en
cuellos muy saturados, por eso existen variantes y a veces se combina con recovery.

PROS. Tecnica MADURA y probada (juegos RTS, robotica). Previene en vez de curar.
La ventana acota el coste (no planifica todo el espacio-tiempo). Maneja "esperar"
como ciudadano de primera clase. Buen equilibrio calidad/coste para muchos agentes.

CONTRAS. NO es completa ni optima (puede fallar en instancias muy acopladas; el
orden de prioridad importa y mal elegido degrada). Reescribe pathfinder +
route_calculator (toca codigo sano y central). La tabla (x,y,t) puede crecer; hay
que acotarla por ventana. La nocion de "t discreto" choca un poco con SimPy (tiempo
continuo por eventos): habria que discretizar el tiempo en pasos de celda para la
reserva, o mapear t a indices de paso. Determinismo exige orden de planificacion
fijo.

ESFUERZO. ALTO. Nuevo A* espacio-temporal + tabla de reserva + integracion con el
lazo SimPy + replanificacion por ventana. Es una reescritura del subsistema de
routing, no un parche.

RIESGO. MEDIO-ALTO (mucho codigo nuevo en el corazon). Pero gateable por flag.

ROBUSTEZ A FUTURO. MUY ALTA en calidad de simulacion y escalabilidad a decenas de
agentes; es "lo que hace la industria de juegos/robotica" para movimiento
cooperativo. El costo es la reescritura. Si el proyecto aspira a cientos de agentes
con movimiento realista, esta es la inversion de fondo. Para 20 agentes en un
almacen con cuellos, puede ser sobre-ingenieria frente a 2.5+2.1.

---

### 2.9  Conflict-Based Search (CBS) (MAPF de dos niveles, optimo)

QUE ES. Solver MAPF completo y optimo (Sharon et al. 2015). Dos niveles: el ALTO
mantiene un arbol de restricciones; planifica cada agente con A* ignorando a los
demas; cuando dos planes colisionan en (x,y,t), genera dos ramas imponiendo a cada
agente la restriccion de NO estar en esa celda-tiempo, y re-planifica solo a ese
agente. Repite hasta un conjunto de planes sin conflicto. Variantes suboptimas
acotadas (ECBS, CBS-Budget, CBSw/P) cambian optimalidad por velocidad.

ENCAJE. ENCAJE POBRE con la filosofia actual. CBS es CENTRALIZADO y de PLANIFICACION
GLOBAL OFF-LINE (calcula planes compatibles ANTES de mover). Aqui el modelo es
reactivo en runtime, los destinos se generan dinamicamente (WorkOrders, allocation
layer) y los agentes salen/llegan continuamente -> habria que re-resolver CBS cada
vez que cambia el conjunto de tareas, lo cual es caro. Requeriria el mismo A*
espacio-temporal que 2.8 ademas del arbol de restricciones de alto nivel.

QUE RESUELVE. Da planes GLOBALMENTE conflict-free y OPTIMOS (minima suma de costes)
cuando existe solucion. Es el "gold standard" de calidad MAPF.

PROS. Completo y optimo (garantias fuertes). Excelente calidad de solucion. Mucha
literatura y variantes.

CONTRAS. Computacionalmente intensivo; "a menudo impractico para aplicaciones reales
por su coste" (literatura). Centralizado y batch -> choca con el flujo dinamico y
event-driven de esta sim. Reescritura mayor. Sobredimensionado para el problema
real (no se necesita OPTIMALIDAD, se necesita que NO se congele y que el throughput
sea plausible). El esfuerzo/beneficio es malo aqui.

ESFUERZO. MUY ALTO.

RIESGO. ALTO (complejidad + reescritura + posible coste de runtime prohibitivo con
re-planificacion frecuente).

ROBUSTEZ A FUTURO. ALTA en garantias teoricas, BAJA en encaje practico con esta
arquitectura. RECHAZADO como via principal: la optimalidad no es un requisito y el
coste/encaje no compensan. Util solo como referencia conceptual (el modelo de
restricciones (x,y,t) inspira la reserva de 2.8/2.11).

---

### 2.10  Prioritized Planning (MAPF priorizado)

QUE ES. Asignar un orden total de prioridad a los agentes; planificar de mayor a
menor, cada uno evitando los planes ya fijados de los anteriores (sobre tabla de
reserva espacio-temporal). Es esencialmente HCA* (2.8) sin la ventana movil: rapido,
secuencial, pero sin garantias de completitud ni de suboptimalidad acotada.

ENCAJE. Igual que 2.8 necesita A* espacio-temporal y tabla de reserva. Mas simple
que WHCA* (no hay ventana ni replanificacion continua), pero por eso mas fragil ante
dinamismo. Encaja como version "lite" de 2.8.

QUE RESUELVE. Genera planes sin conflicto si el orden de prioridad es "afortunado".
Barato y rapido.

PROS. Simple y veloz (el mas rapido de los MAPF). Funciona bien en baja densidad y
acoplamiento ligero (literatura: "best suited to light coupling, low densities").
Determinista por orden de prioridad.

CONTRAS. NO completo: en escenarios densamente acoplados (justo el embudo de este
problema) "su fragilidad y suboptimalidad se amplifican". Puede no encontrar plan
para los agentes de baja prioridad aunque exista. Mismo coste de reescritura
(espacio-temporal) que 2.8 pero con menos garantias. En el cuello del depot saturado
(alto acoplamiento) es donde PEOR se comporta.

ESFUERZO. ALTO (espacio-temporal), aunque menor que WHCA*/CBS.

RIESGO. MEDIO-ALTO: la fragilidad en alta densidad es justo el caso que hay que
resolver.

ROBUSTEZ A FUTURO. MEDIA. Mejor que F3 actual, peor que WHCA* o que una combinacion
de prevencion por reglas + recovery. Si se va a pagar el coste del espacio-temporal,
conviene pagar un poco mas y tener la ventana (WHCA*, 2.8). No recomendado como
destino final por su fragilidad en cuellos.

---

### 2.11  Time-window routing / reserva de INTERVALOS (AGV, almacenes reales)

QUE ES. El estandar de la INVESTIGACION OPERATIVA de almacenes/AGV (Mohring et al.).
Cada arista/celda lleva una lista de VENTANAS DE TIEMPO LIBRES; al rutear un AGV se
le reserva un intervalo [t_in, t_out] en cada celda de su camino, garantizando que
no se solape con otra reserva -> conflict-free por construccion. Se combina con
Dijkstra/A* sobre el grafo de ventanas libres. Detecta y evita los tipos clasicos
de conflicto (punto/cara a cara/cruce) usando las ventanas + prioridades. Es la
version "tiempo continuo" de la reserva espacio-temporal (2.8 usa t discreto;
time-windows usa intervalos reales).

ENCAJE. EXCELENTE conceptualmente con SimPy (que es tiempo CONTINUO por eventos):
las ventanas [t_in,t_out] encajan natural con el reloj continuo de SimPy, mejor que
el t discreto de WHCA*. `CongestionManager` pasaria de `owner: {(x,y):agent}` a
`reservations: {(x,y): [intervalos]}`. El A* tendria que rutear sobre ventanas
libres (cambio de pathfinder). Es la opcion MAPF mas "nativa" para este motor.
Encaja con one-way (2.5) y muelles (2.7) sin friccion.

QUE RESUELVE. Conflict-free de punto, head-on y cruce por construccion, en tiempo
continuo. Es justo el problema (AGV en almacen con cuellos) que esta tecnica fue
disenada para resolver -> maxima pertinencia de dominio.

PROS. Disenada EXACTAMENTE para almacenes/AGV (alta fidelidad y pertinencia).
Tiempo continuo = encaje natural con SimPy. Previene en vez de curar. Madura, con
decadas de literatura OR. Escala a flotas grandes (es lo que usan WMS reales).

CONTRAS. Reescritura del routing (A* sobre ventanas + gestor de reservas por
intervalos). Las velocidades distintas (Ground 1.0 vs Forklift 0.8) complican el
calculo de [t_in,t_out] (hay que modelar la duracion de ocupacion por agente). El
dinamismo (tareas que aparecen) obliga a re-rutear con reservas vigentes. Reservar
intervalos a futuro asume que el agente cumple su horario; si se desvia (espera
imprevista) hay que invalidar/recalcular reservas -> complejidad de mantenimiento.

ESFUERZO. ALTO. Comparable a 2.8 pero mejor encajado.

RIESGO. MEDIO-ALTO (reescritura central), gateable por flag.

ROBUSTEZ A FUTURO. MUY ALTA y la MAS PERTINENTE AL DOMINIO. Si el objetivo es un
gemelo digital de almacen serio y escalable a muchas AGVs, esta es la arquitectura
"de libro". El costo es la reescritura del routing. Es la principal candidata
"cambio de arquitectura" frente a la via incremental (2.5+2.1+2.2).

---

### 2.12  Campos de potencial / flow fields (descentralizado por campo)

QUE ES. Navegacion reactiva: un campo ATRACTIVO hacia el destino + campos
REPULSIVOS alrededor de otros agentes/obstaculos; el agente sigue el gradiente.
Flow fields = un campo de direccion precalculado hacia un destino comun que muchos
agentes siguen (comun en juegos con multitudes). No hay planificacion de ruta por
agente; emerge del campo.

ENCAJE. POBRE con un modelo de grid discreto + SimPy event-driven + celdas cap-1.
Los campos de potencial son de espacio/tiempo CONTINUO y movimiento por fuerzas;
mapearlos a "una celda por paso con exclusion" desvirtua la tecnica. Reemplazaria
el A* + el lazo de movimiento por completo. Choca con la fidelidad de "celdas del
TMX".

QUE RESUELVE. Movimiento fluido de muchas entidades hacia destinos comunes, barato
por agente. Bueno para multitudes/hordas.

PROS. Muy escalable en numero de agentes (coste casi independiente de N si el flow
field es compartido). Simple de razonar. Sin planificacion costosa.

CONTRAS. SUFRE LOCAL MINIMA Y DEADLOCK de forma notoria (literatura: "APF se atasca
en minimos locales y oscilaciones; enfoques descentralizados tipo ORCA/CBF pueden
deadlockear"). Para escapar minimos locales hacen falta hibridos (wall-follower,
terminos cineticos, RL) -> complejidad que reintroduce el problema que queriamos
evitar. Baja fidelidad para un almacen con pasillos estrechos (los campos brillan en
espacios abiertos, no en laberintos de ancho 1). No garantiza exclusion de celda.

ESFUERZO. ALTO (reescritura del movimiento) y de bajo retorno aqui.

RIESGO. ALTO (cambia el paradigma y trae sus propios deadlocks).

ROBUSTEZ A FUTURO. BAJA para ESTE dominio (almacen, grid, pasillos estrechos, pocas
decenas de agentes con exclusion estricta). RECHAZADO salvo que el proyecto pivotara
a multitudes en espacios abiertos. Util solo como heuristica de repulsion auxiliar,
no como arquitectura.

---

### 2.13  Reserva de RUTA vs reserva de CELDA (eje de granularidad)

QUE ES. Mas que un enfoque, un EJE de decision que cruza a los demas. (A) Reserva
por CELDA (lo actual): granularidad maxima, maximo paralelismo. (B) Reserva de RUTA
COMPLETA: el agente reserva TODAS las celdas de su tramo antes de moverse (o un
sub-tramo critico). (C) Reserva de ZONA/segmento de pasillo con aforo.

ENCAJE. (A) es lo implementado. (B) encaja como refuerzo para tramos criticos
cortos (p.ej. cruzar un pasillo de ancho 1 completo de una vez = reservar todo el
pasillo): previene head-on por construccion (nadie entra si esta reservado). (C)
encaja con one-way/corredores (2.5) y con cap-k (2.4/2.7).

QUE RESUELVE. (B) previene deadlock por construccion en el tramo reservado (si se
adquiere en orden total) -> mata head-on y espera circular DENTRO del tramo. (C)
controla aforo de corredores.

PROS (B). Garantia local fuerte (un pasillo reservado no se traba). Simple de
razonar para cuellos concretos. PROS (C): pocas entidades, modela corredores.

CONTRAS (B). HOLD-AND-WAIT masivo: una ruta larga reservada bloquea media nave,
mata el paralelismo, tiende a F9 (serializacion). Por eso el plan la RECHAZA como
base y solo la admite para tramos criticos CORTOS. CONTRAS (C): granularidad gruesa,
define mal los cruces, riesgo F9 si mal calibrada.

ESFUERZO. BAJO-MEDIO (sobre la infraestructura de celda ya existente).

RIESGO. MEDIO (B mal usada serializa).

ROBUSTEZ A FUTURO. (A) celda como base es correcto. (B) reserva de tramo corto es un
COMPLEMENTO util y barato para pasillos de ancho 1 (alternativa/companera de 2.5).
(C) zona es la base de one-way/corredores. Conclusion: mantener celda como base,
usar reserva de tramo corto en pasillos criticos. No es una solucion global por si.

---

### 2.14  Centralizado vs descentralizado (eje transversal de decision)

QUE ES. El eje arquitectonico de fondo. CENTRALIZADO: un planificador conoce todos
los agentes/tareas y produce planes mutuamente compatibles antes de mover (CBS 2.9,
prioritized 2.10, WHCA* 2.8 es semi, time-window 2.11). DESCENTRALIZADO: cada agente
decide localmente en runtime y los conflictos se resuelven reactivamente (F3 actual,
cesion 2.1, potencial 2.12). Hibrido: reglas globales estaticas (one-way 2.5,
semaforos 2.6) + decision local + recovery global (2.2).

ENCAJE / IMPLICACIONES. La arquitectura ACTUAL es descentralizada reactiva y
event-driven (SimPy), con tareas dinamicas (WorkOrders/allocation). Esto favorece:
(a) soluciones descentralizadas + reglas globales estaticas (hibrido) por encaje
natural, y (b) penaliza los planificadores centralizados batch (CBS) que asumen
conjunto de tareas conocido y estable. Un cambio a centralizado seria un giro
arquitectonico grande (y discutible: el realismo de un almacen es justamente que los
operarios deciden local, no que un oraculo planifica todo).

QUE RESUELVE. Es el marco para decidir CUANTA inteligencia global meter. La leccion
del campo: hibrido (estructura global estatica + autonomia local + red de recovery)
suele ganar en sistemas reales por robustez y simplicidad operativa.

PROS/CONTRAS. Centralizado: optimo/garantias, pero fragil al dinamismo, caro,
single-point. Descentralizado puro: simple y escalable, pero deadlock-prone (es
EXACTAMENTE el fallo F3). Hibrido: combina prevencion estructural barata con
autonomia y recovery -> el "sweet spot" para almacenes/AGV.

ESFUERZO/RIESGO/ROBUSTEZ. El hibrido es el de mejor relacion robustez/esfuerzo para
este motor. Es la base de la recomendacion (seccion 4).

---

### 2.15  Repathing dinamico reactivo (rodear atascos; ya previsto como F4)

QUE ES. Cuando un agente lleva esperando demasiado una celda persistentemente
ocupada, RECALCULA su ruta pidiendo evitar el conjunto de celdas ocupadas
"persistentes" (tratarlas como no-caminables temporalmente, sin mutar
collision_matrix). Acepta la nueva ruta solo si su coste <= coste_actual * FACTOR.
Limite MAX_REPATH por tramo; agotado, espera en sitio. Es la Fase 4 ya planeada.

ENCAJE. Encaja sobre F3: dentro del lazo, tras vencer W repetido, invocar
`find_path` con un set de celdas a evitar. PERO: el `pathfinder.find_path(start,
goal)` actual NO acepta "evitar celdas" -> hay que anadir un parametro (set de
celdas temporalmente bloqueadas) o un wrapper. Cambio acotado al pathfinder.

QUE RESUELVE. Atascos LOCALIZADOS y evitables (hay ruta alterna). Mejora throughput
(agentes rodean en vez de esperar). NO resuelve el deadlock del embudo de 1 celda:
si NO hay ruta alterna (cuello unico), el repath no encuentra nada y cae a esperar
-> el deadlock persiste. Es complemento, no cura del caso F3.

PROS. Mejora throughput y realismo (la gente rodea atascos). Reactivo, encaja
incremental. Acotado por MAX_REPATH/FACTOR (anti-F5 repathing infinito).

CONTRAS. Inutil donde no hay alternativa (el embudo del depot es cuello unico ->
repath no salva el deadlock alli). Riesgo de repathing infinito si no se acota
(F5). Coste de A* repetido. Requiere tocar el pathfinder (param evitar-celdas).

ESFUERZO. MEDIO.

RIESGO. MEDIO (toca pathfinder; acotable).

ROBUSTEZ A FUTURO. MEDIA como COMPLEMENTO. Sube throughput y realismo donde hay
alternativas, pero NO es una salvaguarda anti-deadlock (no garantiza I2). Debe ir
SIEMPRE acompanado de un mecanismo que cubra el cuello sin alternativa (2.1/2.2 o
2.5/2.6).

---

## 3. ANALISIS COMPARATIVO

### 3.1 Tabla de puntuacion

Escala 1-5 (5 = mejor). "Encaje F1/F2/F3" = cuanto reutiliza lo ya construido sin
reescribir el routing. "Garantia I2" = que tan fuerte garantiza ausencia de freeze.
"Fidelidad" = realismo de almacen. "Esfuerzo" 5 = poco esfuerzo. "Riesgo" 5 = poco
riesgo de regresion. "Escala" = a muchos agentes/cuellos.

| # | Enfoque | Garantia I2 | Fidelidad | Esfuerzo(5=poco) | Riesgo(5=poco) | Encaje F1-F3 | Escala | Rol |
|---|---------|:----:|:----:|:----:|:----:|:----:|:----:|-----|
| 2.1 | Cesion+aging+backoff (recovery local) | 4 | 5 | 3 | 2 | 5 | 3 | Curativo local |
| 2.2 | Deteccion grafo wait-for + recovery | 5 | 4 | 3 | 3 | 5 | 4 | Red de seguridad |
| 2.3 | Avoidance / banker / orden total | 5 | 2 | 2 | 2 | 3 | 2 | Conceptual |
| 2.4 | Reduccion presion embudo (cap-k) | 3 | 4 | 4 | 5 | 5 | 3 | Paliativo clave |
| 2.5 | One-way / pasillos direccionales | 4 | 5 | 2 | 3 | 3 | 5 | Preventivo estructural |
| 2.6 | Semaforos de interseccion (token) | 4 | 5 | 3 | 3 | 4 | 5 | Preventivo en cruces |
| 2.7 | Cap-k muelles staging (FIFO) | 3 | 5 | 4 | 5 | 4 | 4 | Componente realista |
| 2.8 | WHCA* (espacio-temporal, ventana) | 4 | 4 | 1 | 2 | 1 | 5 | Reescritura routing |
| 2.9 | CBS (optimo centralizado) | 5 | 3 | 1 | 1 | 1 | 2 | Rechazado |
| 2.10 | Prioritized planning | 3 | 3 | 2 | 2 | 1 | 3 | No recomendado |
| 2.11 | Time-window routing (AGV/OR) | 5 | 5 | 1 | 2 | 1 | 5 | Reescritura "de libro" |
| 2.12 | Potential/flow fields | 2 | 2 | 2 | 1 | 1 | 4 | Rechazado (dominio) |
| 2.13 | Reserva ruta/tramo corto | 4 | 4 | 4 | 3 | 4 | 3 | Complemento pasillos |
| 2.14 | (eje centralizado/descentralizado) | - | - | - | - | - | - | Marco de decision |
| 2.15 | Repathing reactivo (F4) | 2 | 4 | 3 | 3 | 4 | 3 | Throughput, no anti-deadlock |

### 3.2 Lectura de la tabla

- Ningun enfoque UNICO maximiza todo. Los de mayor garantia+fidelidad+escala
  (2.11 time-window, 2.8 WHCA*, 2.6 semaforos, 2.5 one-way) cuestan esfuerzo y
  encajan peor con lo ya hecho (reescriben routing) o requieren modelado de layout.
- Los de mejor encaje+bajo riesgo (2.4, 2.7, 2.1, 2.2) son incrementales sobre
  F1/F2/F3 pero ninguno SOLO garantiza robustez total a futuro: son curativos o
  paliativos.
- Los MAPF centralizados puros (2.9 CBS, 2.10 prioritized, 2.12 fields) salen mal
  parados por encaje y/o dominio: RECHAZADOS como via principal.
- => La respuesta robusta NO es un enfoque, es una COMBINACION por capas.

### 3.3 Combinaciones candidatas (lo que realmente se decide)

COMBO A - "Incremental hibrido" (sobre la arquitectura actual, sin reescribir
routing): 2.4 (reduccion de embudo) + 2.7 (muelles) + 2.1 (cesion+aging) + 2.2
(deteccion grafo wait-for como red) + 2.15 (repathing) + opcional 2.13 (reserva de
tramo en pasillos de ancho 1). Mantiene celda como base, descentralizado + recovery.

COMBO B - "Preventivo estructural" (toca el pathfinder para hacerlo dirigido):
2.5 (one-way) + 2.6 (semaforos en cruces) + 2.1/2.2 (recovery como red minima) +
2.7 (muelles) + 2.4 (embudo). El deadlock casi no se forma; recovery es respaldo.

COMBO C - "Reescritura de fondo" (cambio de arquitectura del routing): 2.11
(time-window routing, tiempo continuo, nativo SimPy) como motor principal, con 2.7
(muelles) y 2.2 (deteccion) como red. Conflict-free por construccion; es la
arquitectura "de libro" para gemelos de almacen/AGV a gran escala.

Estas tres son el verdadero menu de decision. WHCA* (2.8) es una variante de C con
tiempo discreto (peor encaje SimPy que 2.11). CBS/fields quedan fuera.

---

## 4. RECOMENDACION FINAL (robusta a futuro)

### 4.1 Recomendacion: COMBO B como destino, llegando por capas, con red de COMBO A

La opcion mas robusta a largo plazo NO es la mas exotica (CBS) ni la mas barata
(solo cesion). Es un HIBRIDO con PREVENCION ESTRUCTURAL:

> DESTINO: pasillos direccionales (one-way, 2.5) + control de cruces por token
> (semaforos, 2.6), sobre la base de exclusion por celda ya existente, con muelles
> de staging como Resource (2.7) y reduccion de presion del embudo (2.4); y SIEMPRE
> con una red de recovery (deteccion por grafo wait-for 2.2 + cesion por aging 2.1)
> que garantiza I2 aunque algo se escape.

POR QUE (justificacion honesta):

1. Ataca la causa raiz por PREVENCION, no por curacion. El deadlock observado es
   espera circular en un cuello bidireccional. One-way ELIMINA la bidireccionalidad
   -> el ciclo no puede formarse en pasillos; los semaforos cubren los cruces. Curar
   (solo 2.1/2.2) siempre llega tarde y es fragil bajo alta densidad; prevenir
   escala mejor (mas agentes = mas flujo ordenado, no mas deadlocks).
2. Es lo que hacen los almacenes y sistemas AGV reales (alta fidelidad: el gemelo
   gana realismo, justo lo que el Director quiere medir). La literatura OR/AGV
   confirma one-way + time-windows + prioridades como practica estandar.
3. Conserva la inversion F0-F3: la exclusion por celda, el CongestionManager, el
   stagger F2 y el watchdog NO se tiran; se reusan como base y como red. No es una
   reescritura: es anadir una capa de direccion al grafo + control de cruces.
4. Mantiene el paradigma descentralizado+reglas-globales (encaje natural con SimPy
   event-driven y tareas dinamicas), evitando el giro a planificacion central batch
   (CBS) que choca con el dinamismo de WorkOrders/allocation.
5. La red de recovery (2.2+2.1) garantiza I2 SIEMPRE: aunque una calibracion de
   one-way deje un caso raro, el grafo wait-for lo detecta y la cesion lo rompe.
   Defensa en profundidad: prevenir primero, curar como ultimo recurso.

QUE IMPLICA REESCRIBIR (acotado, no de fondo):
- pathfinder: de grafo NO dirigido a DIRIGIDO. `get_neighbors` filtra por la
  direccion permitida de la arista; `find_path` busca sobre el grafo dirigido.
  Anadir validacion de conectividad dirigida al cargar el layout.
- una CAPA DE DIRECCION del layout: nueva (capa en el TMX o bloque en config) que
  asigna sentido a pasillos. Es modelado de datos, no algoritmia.
- CongestionManager: anadir gestion de tokens de cruce (Resource por interseccion)
  y el grafo wait-for + resolver de ciclos (extender el watchdog detector actual).
- operators: anadir, dentro del lazo F3 ya existente, la rama de cesion por aging
  (tras vencer W con contencion mutua) y la peticion/liberacion de token de cruce.
- NO se reescribe route_calculator ni se introduce espacio-tiempo (eso seria COMBO C).

POR QUE NO COMBO C (time-window) como destino inmediato, aunque sea "de libro":
Es la arquitectura mas potente y la mas pertinente al dominio a MUY gran escala,
pero exige reescribir el routing a reserva por intervalos (alto esfuerzo y riesgo
sobre codigo central) y su beneficio marginal sobre COMBO B aparece recien con
flotas grandes (decenas-cientos de AGVs coordinadas). Para el horizonte realista de
este proyecto (operarios en un almacen con cuellos, ~decenas de agentes), COMBO B da
~la misma robustez con mucho menos riesgo. RECOMENDACION: dejar COMBO C como
NORTE arquitectonico documentado; migrar a el SOLO si el proyecto escala a flotas
grandes o si COMBO B muestra limites empiricos. La capa de direccion (2.5) y los
tokens (2.6) de COMBO B son ademas un peldano natural hacia COMBO C.

### 4.2 Plan de migracion por fases (hacia COMBO B, sin romper la cadena viva)

Todo gateado por `congestion.mode` / flags nuevos; `enabled:false` siempre = actual.

- FASE A (red de seguridad PRIMERO, desbloquea F3): deteccion por grafo wait-for
  (2.2) + cesion por prioridad con aging y backoff con jitter (2.1) dentro del lazo
  F3 existente. Criterio: el stress de 20 agentes TERMINA (0 freezes), I1 sigue ~0,
  determinismo OK. Esto convierte el watchdog detector en watchdog RESOLUTOR.
  >>> Con solo esta fase, F3 deja de congelarse. Es tambien la "opcion minima
  >>> viable" (seccion 5) si el Director quiere desbloquear ya.
- FASE B (reduccion de presion, paliativo robusto): cap-k en la salida del depot
  (2.4) + muelles de staging como Resource (2.7). Baja la frecuencia de deadlocks y
  modela colas reales. Bajo riesgo, alto valor.
- FASE C (prevencion estructural, el salto de robustez): capa de direccion del
  layout + pathfinder dirigido (2.5). Validar conectividad dirigida. Aqui el
  deadlock en pasillos deja de poder formarse. Mantener la red de FASE A activa.
- FASE D (cruces): tokens/semaforos de interseccion (2.6) en celdas de grado>=3.
  Cierra el unico hueco que one-way deja (los cruces).
- FASE E (throughput + pulido): repathing reactivo (2.15, requiere param evitar-
  celdas en pathfinder) + reserva de tramo corto en pasillos criticos (2.13) +
  calibracion de k y de aging con las metricas del plan (curva throughput vs N).
- FASE F (opcional, futuro): si la escala lo exige, evaluar migracion del routing a
  time-window (COMBO C, 2.11).

Orden pensado para que el RIESGO crezca despacio y SIEMPRE haya retorno verde: la
red de recovery va primero (garantiza I2 desde ya), luego paliativos baratos, y la
reescritura del pathfinder (lo mas invasivo) solo cuando la red ya protege.

---

## 5. OPCION MINIMA VIABLE (desbloqueo rapido) + TRADE-OFF

Si el Director prefiere DESBLOQUEAR YA F3 con el minimo trabajo, la MVP es la
FASE A sola: deteccion por grafo wait-for (2.2) + cesion por prioridad con aging
(2.1), reusando todo el andamiaje F3 (owner, release_events, watchdog, _jump_to,
work_area_priorities).

Que se hace, en concreto:
- CongestionManager registra `waiting_on: {agent_id: cell}` al entrar en wait.
- El watchdog (ya existe) pasa de DETECTOR a RESOLUTOR: construye el grafo wait-for,
  busca ciclos, y para cada ciclo elige la victima por `(prioridad_efectiva,
  agent_id)` (aging incluido) y dispara su cesion via un Event.
- El agente victima, al ser despertado en su rama de espera, ejecuta un retroceso
  atomico (`_jump_to` a una celda libre adyacente) y reintenta. Backoff con jitter
  sembrado para anti-livelock.
- Cota dura de aging para que nadie quede en starvation (I2/F4).

Criterio de exito MVP: stress 20 agentes TERMINA (0 freezes), I1 ~0, determinismo
2 corridas identicas, flag off byte-identico.

TRADE-OFF honesto (que se gana y que NO):
- GANA: desbloqueo rapido y bajo (no toca pathfinder ni route_calculator; todo el
  andamiaje ya existe). Garantiza I2 (sin freeze). Esfuerzo ~1 fase.
- NO resuelve la CAUSA (el cuello bidireccional sigue ahi): bajo alta densidad
  habra MUCHAS cesiones/retrocesos -> throughput posiblemente bajo y "nervioso"
  (agentes que avanzan y retroceden). Es curar, no prevenir.
- Riesgo: la cesion es la pieza historicamente fragil (causa del freeze previo).
  Mitigacion: resolver sobre el CICLO completo (no solo pares), jitter sembrado,
  aging con cota dura, y el stress determinista como gate de no-regresion.
- Es, ademas, la FASE A del plan robusto: NO es trabajo tirado. La MVP es el primer
  peldano del COMBO B. Si luego se quiere robustez de fondo, se sigue con B/C/D.

Recomendacion de Cerebellum: hacer la MVP (Fase A) para desbloquear y validar I2 YA,
pero NO detenerse ahi: planificar Fase B (cap-k embudo + muelles) inmediatamente
despues, porque es barata y baja la presion que hace sufrir a la cesion. La
prevencion estructural (Fase C one-way) es la que da la robustez verdadera a futuro
y deberia ser el objetivo de medio plazo.

---

## 6. REFERENCIAS

Codigo (rama feature/allocation-layer-v12.1), verificado por lectura directa:
- src/subsystems/simulation/congestion_manager.py (owner/release_events,
  try_acquire/release/claim, watchdog_proc detector).
- src/subsystems/simulation/operators.py (_recorrer_tramo rama F3 ~377-421;
  _claim_spawn, _jump_to, _spawn_lane, _compute_departure_lanes).
- src/subsystems/simulation/pathfinder.py (A* 8-dir octile, find_path(start,goal)
  espacial puro, sin t ni evitar-celdas).
- src/subsystems/simulation/route_calculator.py (ruta precalculada por tour).
- docs/PLAN_INICIATIVA_2_CONGESTION.md (diseno, secciones 4.x, F1-F14, fases 0-5).
- docs/PROGRESO_INICIATIVA_2.md (RESULTADO F3: grafo wait-for empirico, deadlock).

Literatura (web, junio 2026):
- D. Silver, "Cooperative Pathfinding" (HCA*/WHCA*, reserva espacio-temporal).
  https://www.semanticscholar.org/paper/Cooperative-Pathfinding-Silver/03ef7f3a962319a8d97cacb6afa5380948eba1be
- Bnaya & Felner, "Conflict-Oriented Windowed Hierarchical Cooperative A*" (CO-WHCA*).
  https://tzin.bgu.ac.il/~felner/2014/COWA6p.pdf
- Sharon et al., "Conflict-based search for optimal multi-agent pathfinding".
  https://www.sciencedirect.com/science/article/pii/S0004370214001386
- CBS with Priorities (CBSw/P) / suboptimal CBS (tradeoffs prioritized vs CBS).
  https://www.emergentmind.com/topics/conflict-based-search-with-priorities-cbsw-p
- Mohring et al. / conflict-free real-time AGV routing (time-window routing).
  https://www.researchgate.net/publication/221563267_Conflict-free_Real-time_AGV_Routing
- "Multi-AGV conflict-free path planning based on grid time windows" (MDPI 2024).
  https://www.mdpi.com/2076-3417/14/8/3341
- "Hierarchical Traffic Management of Multi-AGV Systems With Deadlock Prevention".
  https://www.researchgate.net/publication/371019271_Hierarchical_Traffic_Management_of_Multi-AGV_Systems_With_Deadlock_Prevention_Applied_to_Industrial_Environments
- Deadlock avoidance / banker's algorithm (avoidance vs detection+recovery).
  https://www.sciencedirect.com/topics/computer-science/deadlock-avoidance
- Autonomous Intersection Management (reserva/token, deadlock-free DICA).
  https://arxiv.org/html/2311.17681v2
- "Escaping Local Minima: Hybrid APF with Wall-Follower" (limites de potential fields).
  https://arxiv.org/html/2409.10332

---

_Fin de la investigacion. Cerebellum sincronizado. Esperando decision del Director:
MVP (Fase A) para desbloquear ya, o arranque del plan robusto COMBO B por fases._

 