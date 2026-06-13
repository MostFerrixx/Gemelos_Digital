# PLAN INICIATIVA #2 — OPCION C: Ruteo por Reserva Espacio-Temporal (Time-Window Routing)

> Documento de PLANIFICACION. NO contiene codigo definitivo todavia. Es la hoja de
> ruta tecnica que el Director debe revisar y aprobar (Ley #1: PLAN ANTES QUE CODIGO)
> antes de escribir una sola linea de la implementacion.
>
> Reemplaza, como enfoque vigente de la Iniciativa #2, al plan por exclusion-de-celda
> (Combo A-B) archivado en `docs/antiguos/`. La justificacion de elegir la Opcion C
> esta en `docs/INVESTIGACION_CONGESTION_SOLUCIONES.md` (enfoque 2.11 / Combo C).

---

## CHECKLIST INTERNO DE REDACCION (documentacion viva)

Estado de cada seccion de ESTE documento (las sesiones se cortan por limite de tokens;
este checklist permite reanudar sin perder el hilo):

- [x] 0. Mapa del codigo real estudiado (anclaje)
- [x] 1. Objetivo y filosofia
- [x] 2. Que es el time-window routing y como se mapea a SimPy + grilla
- [x] 3. Diseno arquitectonico
- [x] 4. Garantia anti-deadlock y casos borde
- [x] 5. Plan de implementacion por fases
- [x] 6. Criterios de exito y metricas
- [x] 7. Riesgos, complejidad y rollback
- [x] 8. Relacion con el "norte" y degradacion a Combo A/B

---

## 0. ANCLAJE: el codigo real del movimiento (verificado por lectura)

Antes de disenar nada, se rastreo la cadena viva del movimiento. Estos son los hechos
contra los que se construye el plan (no suposiciones):

**Planificacion de ruta (estatica, hoy):**
- `src/subsystems/simulation/pathfinder.py` :: `Pathfinder.find_path(start, goal)` —
  A* clasico sobre `collision_matrix` (2D `[y][x]`, True=caminable). 8 direcciones
  (cardinales coste 1.0, diagonales coste sqrt(2)), heuristica octil. Devuelve una
  lista de celdas `[(x,y), ...]` o `None`. **No conoce el tiempo ni a los demas
  agentes**: solo geometria estatica. Este es el dato clave: hoy el grafo es estatico.
- `src/subsystems/simulation/route_calculator.py` :: `RouteCalculator.calculate_route(...)`
  encadena varios `find_path` (depot -> pick1 -> pick2 -> ... -> staging -> depot) y
  produce `segment_paths` (lista de tramos, cada uno lista de celdas) + `full_path`.
  El ordenamiento de paradas es por `pick_sequence` o nearest-neighbor.

**Ejecucion del movimiento (consumo de la ruta):**
- `src/subsystems/simulation/operators.py` :: `BaseOperator._recorrer_tramo(segment_path,
  speed, on_before, on_after, time_per_cell=0.1)` — generador SimPy que recorre el tramo
  celda a celda. Por cada celda de `segment_path[1:]`:
  1. `self._set_pos(step_position)` (mueve la posicion; unico choke point de posicion),
  2. `on_before(...)` (emite el evento de movimiento al replay_buffer / .jsonl),
  3. `yield self.env.timeout(time_per_cell * speed)` (avanza el reloj: aqui transcurre
     el tiempo de cruzar UNA celda),
  4. `on_after(...)` (prints).
  - `time_per_cell = 0.1`; `speed` = 1.0 (Ground) / 0.8 (Forklift). => coste temporal
    por celda HOY = `0.1 * speed` (Ground 0.10 s, Forklift 0.08 s) — **constante por
    celda, independiente de diagonal vs recto** (matiz a corregir/decidir en el plan).
- `_set_pos(new_cell)` notifica al `CongestionManager` (`cm.move(id, prev, new)`) ANTES
  de actualizar `current_position`. Con la capa apagada es un set directo (byte-identico
  al original). **Este es el punto de insercion natural de la reserva.**
- Spawn: `agent_process()` arranca en `depot`, llama `_spawn_lane()` (F2: anden de salida
  disperso por `spawn_index` via BFS cardinal determinista) y `_spawn_stagger()` (F2:
  espera `spawn_offset * spawn_index` antes del primer movimiento).

**Estado dinamico actual (F1-F3), en `congestion_manager.py`:**
- F1 `instrument`: OBSERVADOR pasivo. `occupied: {(x,y): set(agent_id)}`; cuenta
  co-ocupaciones (dos agentes en la misma celda el mismo instante = violacion de
  exclusion I1 que hoy ocurre porque los agentes se atraviesan). Escribe
  `congestion_report.json`.
- F2 `staggered_start`: dispersion espacial (andenes) + temporal (offset) del arranque.
- F3 `cell` / `cell+corridor`: exclusion por celda con RESERVA PEREZOSA
  `owner: {(x,y): agent_id}` (cap 1). En `_recorrer_tramo`, rama cell-mode: adquirir la
  celda SIGUIENTE antes de soltar la ACTUAL (anti hold-and-wait local), y si esta
  ocupada **esperar** con `yield release_event(cell) | env.timeout(W)` y reintentar
  (W=`wait_timeout`=0.5, `wait_hard_cap`=30). Watchdog (`watchdog_proc`) que DETECTA
  stalls (no los resuelve). **Esta es la espera reactiva por timeout que la Opcion C
  jubila** (es curativa, no preventiva; puede trabarse / serializar / livelock).

**Motor / reloj:**
- `src/engines/event_generator.py` :: SimPy es **tiempo continuo por eventos**.
  `self.env = simpy.Environment()`; el lazo es `while not simulacion_ha_terminado():
  env.run(until=env.now + 1.0)`. El `CongestionManager` se instancia en
  `warehouse.py` (`AlmacenMejorado`) leyendo el bloque `config.json["congestion"]`;
  el watchdog se arranca en cell-mode desde `event_generator`.
- `config.json["congestion"]` hoy: `{enabled, mode (off|instrument|cell|cell+corridor),
  wait_timeout, wait_hard_cap, backoff_*, max_repath, spawn_offset, watchdog_window,
  staggered_start, ...}`. **El plan ANADE un modo nuevo `timewindow` a este mismo bloque**
  (Ley #3: `config.json` es la unica fuente de verdad).

Conclusion del anclaje: la arquitectura ya separa **planificacion** (pathfinder/
route_calculator) de **ejecucion** (`_recorrer_tramo`) y tiene un **unico choke point**
de posicion (`_set_pos`) y un **unico gestor de estado dinamico** (`CongestionManager`).
Eso hace que la Opcion C sea injertable sin reescribir los `agent_process`: se cambia
QUE ruta se planifica (A* espacio-temporal) y se reemplaza la espera reactiva de F3 por
una ejecucion que simplemente SIGUE una ruta ya garantizada libre de conflictos.

---

## 1. OBJETIVO Y FILOSOFIA

### 1.1 El objetivo
Eliminar por construccion los conflictos de movimiento (co-ocupacion de celda, choques
frontales "head-on", y cruces) y, sobre todo, **los freezes/deadlocks de arranque**
(20 agentes saliendo del mismo depot), manteniendo o mejorando el throughput, SIN
reintroducir live-simulation y SIN romper la cadena headless -> .jsonl -> viewer.

### 1.2 El cambio de filosofia: de CURAR a PREVENIR
El intento F0-F3 (archivado) es **reactivo**: los agentes se mueven y, cuando chocan por
un recurso (celda), uno **espera** (timeout) y reintenta. Eso es un cerrojo distribuido:
funciona en baja contension pero, en el cuello del depot, produce esperas en cadena,
serializacion (F9), livelocks (todos esperan-reintentan-esperan) y, en el peor caso,
deadlock residual que el watchdog solo DETECTA pero no resuelve. La terminacion la
garantiza, hoy, un cap de reloj externo — no la logica.

La Opcion C invierte la logica: **se PLANIFICA el tiempo, no solo el espacio.** Antes de
que un agente se mueva, se le calcula una ruta que reserva, en cada celda de su camino,
un INTERVALO de tiempo `[t_in, t_out]` que **no se solapa con ninguna reserva existente**.
Si la ruta se reserva con exito, recorrerla es seguro por definicion: nadie mas tiene esa
celda en ese intervalo. No hay "esperar a ver si choco": el choque es imposible porque la
celda-tiempo ya estaba apartada para este agente y solo para el.

### 1.3 Por que esto GARANTIZA ausencia de conflicto y de deadlock (idea esencial)
Tres propiedades, que la seccion 4 demuestra en detalle:

1. **Ausencia de colision (exclusion espacio-temporal) por construccion.** La tabla de
   reservas mantiene el invariante "para toda celda c, sus intervalos reservados son
   disjuntos". El planificador SOLO acepta una ventana si no se solapa con las ya
   presentes. Si todo movimiento proviene de una reserva concedida, dos agentes nunca
   comparten `(c, t)`. La co-ocupacion (metrico I1 de F1) es 0 por definicion.

2. **Ausencia de deadlock por orden total de planificacion (planificacion priorizada).**
   Los agentes se planifican UNO A UNO en un orden total (prioridad + desempate
   determinista). Cuando se planifica el agente i, las reservas de los agentes ya
   planificados (1..i-1) son **fijas**; el agente i solo se acomoda a los huecos libres,
   incluyendo la accion "esperar en una celda segura" (reservar quedarse quieto). Como
   nadie con menor prioridad puede invalidar la reserva de i una vez concedida, no se
   forma el ciclo de espera mutua (hold-and-wait circular) que define el deadlock: las
   dependencias de espera siguen el orden total, que es acíclico por construccion.

3. **Ausencia de freeze (progreso garantizado) por la accion de espera reservada + un
   horizonte y un destino "absorbente".** Esperar es un movimiento valido que tambien se
   reserva; un agente siempre puede, en el peor caso, planificar "quedarme donde estoy
   un intervalo y reintentar avanzar despues", y como las celdas de destino (pick/staging/
   depot) se modelan como permanencia reservable, hay siempre al menos un plan factible
   (ver 4.x). La existencia de plan factible + ejecucion que solo sigue el plan => el
   reloj de la sim siempre avanza hasta completar las WorkOrders.

### 1.4 Pertinencia de dominio
Time-window routing es el estandar de la investigacion operativa de almacenes y AGVs
(Mohring et al.) — exactamente "vehiculos en un almacen con cuellos". Y encaja de forma
NATIVA con SimPy, que ya es tiempo CONTINUO por eventos: las ventanas `[t_in, t_out]` son
numeros reales, no ticks discretos. Es la arquitectura "de libro" para un gemelo digital
de almacen serio y escalable. (La investigacion la cataloga como el "norte" arquitectonico;
el Director eligio adoptarla ahora — ver seccion 8 sobre el trade-off frente a Combo B.)

---

## 2. QUE ES EL TIME-WINDOW / RESERVATION ROUTING Y COMO SE MAPEA AQUI

### 2.1 La idea formal
Se modela el almacen como un grafo `G=(V,E)` donde `V` = celdas caminables y `E` =
adyacencias 8-direccionales (lo mismo que hoy usa el Pathfinder). A esto se le anade el
TIEMPO: el estado de planificacion no es una celda `c`, sino un par `(c, t)` = "estar en
la celda c en el instante t" (espacio-tiempo). Una RUTA en el espacio-tiempo es una
secuencia `(c0,t0) -> (c1,t1) -> ... -> (cn,tn)` con `t0 < t1 < ... < tn`, donde cada
transicion es: o bien MOVERSE a una celda adyacente (consumiendo el tiempo de cruce de esa
celda segun la velocidad del agente), o bien ESPERAR en la misma celda (consumiendo un
intervalo de espera). 

Una **TABLA DE RESERVAS** registra, por cada celda, los intervalos de tiempo en que esa
celda esta ocupada y por quien: `reservations[c] = [ (t_in, t_out, agent_id), ... ]`,
intervalos disjuntos por celda. Rutear un agente = encontrar un camino en el espacio-tiempo
cuyas ocupaciones de celda NO se solapen con ninguna reserva existente, y luego INSERTAR
esas ocupaciones como nuevas reservas. Conflict-free por construccion.

### 2.2 De A* estatico a A* espacio-temporal (cooperative A* en tiempo continuo)
- HOY: `find_path` busca en `V` (celdas). Nodo = celda. Coste = distancia. No hay `t`.
- OPCION C: el buscador (lo llamaremos `SpaceTimePlanner` / `find_path_st`) busca en
  el espacio-tiempo. Nodo = `(celda, t_llegada)`. Sucesores de `(c, t)`:
  - **mover** a cada vecino caminable `c'`: llegada `t' = t + dur(c, c', agente)`, valido
    SOLO si el intervalo de ocupacion de `c'` `[t, t']` (o `[t', t'+eps]`, ver 2.4) no
    pisa una reserva existente en `c'`, y ademas no hay "swap" (intercambio frontal) con
    una reserva de `c` (ver 2.5 head-on).
  - **esperar** en `c`: llegada `t' = t + dt_wait`, valido si `c` sigue libre en `[t, t']`.
  - Heuristica: la misma distancia octil del Pathfinder actual (admisible y consistente:
    nunca sobreestima el tiempo restante, porque el tiempo >= distancia / velocidad_max).
    Esto mantiene A* optimo y eficiente y **reutiliza el codigo de heuristica existente**.
- Es **Cooperative A* (HCA*) en tiempo continuo**: cada agente, en su turno, planifica
  contra la tabla de reservas de todos los ya planificados. La variante "ventana movil"
  (WHCA*) es opcional (ver 2.6 y fase 4): util si el horizonte completo se vuelve caro.

### 2.3 Tiempo continuo, no discreto: por que encaja con SimPy
WHCA* clasico discretiza el tiempo en ticks. Aqui NO hace falta: SimPy ya avanza por
eventos en `float`. Las ventanas son intervalos reales `[t_in, t_out]`. Esto evita el
artefacto de "redondear a tick" y modela exactamente el coste `0.1 * speed` por celda
(y su correccion diagonal, ver 2.4). Es la razon por la que 2.11 (time-window) encaja
mejor que 2.8 (WHCA* discreto) en este motor — punto explicito de la investigacion.

### 2.4 Duracion de ocupacion por celda y por agente (el detalle que importa)
- `dur(c, c', agente)` = tiempo que el agente tarda en cruzar de `c` a `c'`. Con el modelo
  actual (`time_per_cell * speed`) es `0.1 * speed`. **Decision de diseno**: respetar la
  semantica actual EXACTA en la fase MVP (coste plano por paso, sin distinguir diagonal)
  para garantizar no-regresion byte-identica con flag off; en una fase posterior se puede
  refinar a `0.1 * speed * (sqrt(2) si diagonal else 1)` si se quiere mas fidelidad
  fisica (cambio aislado y medible).
- **Margen de seguridad (clearance) `eps`**: para que dos agentes no se "rocen" en el
  borde exacto de sus intervalos (un agente saliendo de `c` en `t_out` y otro entrando en
  `t_out`), se reserva la celda con un colchon: la ocupacion efectiva es `[t_in - eps,
  t_out + eps]` o, mas simple, se exige separacion estricta `>` en vez de `>=`. `eps` sera
  un parametro de config (`timewindow.clearance`), por defecto pequeno (p.ej. 1e-3) o 0
  con comparacion estricta. Esto se fija y se prueba en la fase de validacion.
- Velocidades distintas (Ground 1.0 vs Forklift 0.8) se manejan SOLAS: `dur` depende del
  `speed` del agente que planifica, asi que un Forklift reserva ventanas mas largas por
  celda que un Ground. No hay caso especial.

### 2.5 Tipos de conflicto que las reservas cubren (y como)
- **Conflicto de punto (vertex)**: dos agentes en la misma celda al mismo tiempo.
  Impedido directamente: el planificador rechaza una ventana que se solape en `c`.
- **Conflicto frontal (edge / head-on / swap)**: A va de `c1->c2` mientras B va de
  `c2->c1` en el mismo intervalo (se cruzan "atravesandose" sin compartir celda en el
  punto medio). Las reservas de vertice NO lo cubren solas. Se anade una **regla de swap**:
  al evaluar mover `c->c'` en `[t, t']`, rechazar si existe una reserva de algun agente
  que en ese mismo intervalo se mueva `c'->c`. En la practica, como el destino `c'` se
  reserva para `[t, t']` y el origen `c` aun esta reservado por mi hasta `t`, basta con
  exigir que `c'` no tenga una reserva entrante-desde-`c` solapada. Se documenta el chequeo
  exacto en la fase de implementacion (es un lookup acotado en la tabla por celda).
- **Conflicto de cruce (cross)**: en grid 8-direccional, dos diagonales que se cruzan en
  la "X". Si se permiten diagonales, se anade el chequeo de las dos celdas compartidas de
  la diagonal (corner-cutting). **Decision MVP**: dado que la fase 0 puede restringir a
  movimiento cardinal (4-dir) para simplificar la garantia y luego habilitar diagonales,
  se documentan ambos; el cross solo aplica con diagonales activas.

### 2.6 Centralizado vs por-agente, y la ventana movil
- La planificacion es **centralizada en intencion** (una sola tabla de reservas global,
  un orden total de agentes) pero **incremental**: no se resuelve un problema MAPF gigante
  de golpe; cada agente planifica su ruta completa (o su ventana) cuando el dispatcher le
  asigna trabajo, contra las reservas vigentes. Esto encaja con el flujo actual (las
  WorkOrders aparecen dinamicamente; los agentes piden ruta cuando reciben tarea).
- **Horizonte**: en MVP se planifica la RUTA COMPLETA del tramo asignado (depot->pick->
  staging->depot) de una vez. Si el coste/΃estado espacio-temporal crece demasiado (muchas
  reservas, rutas largas), se introduce una VENTANA movil (WHCA*): reservar solo los
  proximos `H` segundos / `K` celdas, ejecutar, y re-planificar el resto con reservas
  frescas. La ventana es una optimizacion de escala posterior, no un requisito del MVP.

---

## 3. DISENO ARQUITECTONICO

### 3.1 Componentes (que se crea, que se reusa, que se jubila)

**SE CREA:**
- `ReservationTable` (nuevo, dentro de `congestion_manager.py` o modulo hermano
  `reservation_table.py`): la estructura `reservations: {(x,y): list[Interval]}` con
  `Interval = (t_in, t_out, agent_id)`. API: `is_free(cell, t_in, t_out, ignore=agent)`,
  `reserve(cell, t_in, t_out, agent)`, `release_agent(agent)` /
  `release_before(agent, t)`, y consultas de swap/cross. Mantiene el invariante de
  intervalos disjuntos por celda. Memoria acotada (ver 4.x): se purgan intervalos con
  `t_out < env.now - margen` (ya en el pasado, irrelevantes).
- `SpaceTimePlanner` (nuevo, modulo `spacetime_planner.py` o metodo nuevo en una clase de
  planificacion): el A* espacio-temporal `find_path_st(start, goal, t0, agente,
  reservation_table)` -> lista de pasos `[(cell, t_arrival), ...]` o un fallback. Reusa
  `Pathfinder.is_walkable`, `get_neighbors` y la heuristica octil.

**SE REUSA (no se toca su semantica):**
- `Pathfinder` (grafo estatico, walkability, vecinos, heuristica) — como capa base del
  planner espacio-temporal.
- `RouteCalculator` — sigue decidiendo el ORDEN de paradas (pick_sequence / nearest), pero
  en modo timewindow delega el calculo de cada tramo al `SpaceTimePlanner` en vez de a
  `find_path` estatico. (Punto de injerto limpio: `calculate_route` ya itera tramo a tramo.)
- `CongestionManager` — se conserva TODA la instrumentacion F1 (metrico de co-ocupacion
  I1, que ahora debe leer 0) y la dispersion de spawn F2 (sigue siendo util como condicion
  inicial sana, aunque el planner ya evita el apelotonamiento). El `owner` dict de F3 y la
  espera por timeout se reemplazan por la `ReservationTable`.
- `_set_pos` / `_recorrer_tramo` — el choke point y el lazo se conservan; en modo
  timewindow, `_recorrer_tramo` NO espera por celda: simplemente EJECUTA la ruta ya
  reservada (avanza el reloj con `env.timeout` segun los `t_arrival` del plan). El metrico
  I1 se sigue alimentando via `_set_pos` para PROBAR empiricamente que da 0.

**SE JUBILA (solo activo en modos viejos; intacto para no-regresion):**
- La espera reactiva F3 en `_recorrer_tramo` (`yield release_event | timeout W`, hard_cap).
- El watchdog F3 como GARANTE de terminacion (se conserva como DETECTOR/observador de
  seguridad, pero deja de ser la red que evita el freeze: en timewindow el plan garantiza
  progreso). 

### 3.2 La tabla de reservas en detalle
- Estructura: `dict` celda -> lista ORDENADA de intervalos `(t_in, t_out, agent_id)`.
- `is_free(cell, a, b, ignore_agent)`: busca solapamiento de `[a,b]` con algun intervalo
  de `cell` cuyo `agent_id != ignore_agent`. Con la lista ordenada por `t_in` es una
  busqueda binaria + chequeo de vecinos (O(log n) amortizado). 
- `reserve(...)`: inserta manteniendo orden; opcionalmente fusiona intervalos contiguos
  del mismo agente (permanencia: pick + espera se funden).
- **Permanencia / "quedarse"**: estar quieto en una celda (durante un pick, una descarga,
  o una espera planificada) = un intervalo `[t, t+dur_perm]` reservado en esa celda.
  Las celdas de PICK y STAGING son destinos donde el agente PERMANECE: el planner reserva
  ahi un intervalo largo (el `picking_duration` / `discharge_time` que ya existen en
  `operators.py`). Asi otro agente que quiera pasar por esa celda vera la ventana ocupada
  y la rodeara o esperara — modelado uniforme, sin caso especial.
- **Liberacion**: cuando un agente termina su ruta (o su ventana), sus intervalos pasados
  se purgan. Como las reservas son a futuro y deterministas, en condiciones normales no hay
  que invalidar nada; la invalidacion solo ocurre en re-planificacion (3.4).

### 3.3 Como planifica cada agente una ruta libre de conflicto
Secuencia, cuando el dispatcher asigna trabajo a un agente en `t0` desde `start`:
1. `RouteCalculator` fija el orden de paradas (igual que hoy).
2. Para cada tramo `start_i -> goal_i`, `SpaceTimePlanner.find_path_st(start_i, goal_i,
   t_actual, agente, tabla)` busca en espacio-tiempo una secuencia de `(celda, t)` libre,
   usando acciones mover/esperar. El `t_actual` de salida del tramo i+1 es el `t` de
   llegada del tramo i (mas la permanencia en el goal si aplica).
3. Si encuentra ruta: se RESERVAN todas sus ocupaciones de celda en la tabla, y el plan
   (lista de `(celda, t)`) se entrega al agente para ejecutar.
4. El agente ejecuta con `_recorrer_tramo` en modo "seguir plan": por cada paso, emite el
   evento y hace `yield env.timeout(t_siguiente - t_actual)`. No hay adquisicion ni espera
   reactiva: el tiempo del plan YA incorpora las esperas necesarias como pasos explicitos.

### 3.4 Re-planificacion dinamica
El sistema es dinamico (WorkOrders aparecen; agentes terminan tareas en momentos no
exactamente predichos si hubiera variabilidad). Estrategia:
- **MVP determinista**: como los tiempos son deterministas (coste por celda fijo), un plan
  reservado se cumple EXACTO; no hay desvio => no hay que re-planificar dentro de un tramo.
  La unica "novedad" es la asignacion de NUEVAS tareas, que se planifican contra las
  reservas vigentes al momento de asignarse. Esto es suficiente para el objetivo (anti-
  freeze de arranque + conflict-free).
- **Robustez futura (ventana movil)**: si se introduce variabilidad (averias, tiempos
  estocasticos) o la ventana movil, se anade: al re-planificar, `release_agent(self)` de
  las reservas futuras propias y volver a planificar desde la posicion/tiempo actual. El
  orden de prioridad evita que la re-planificacion de uno invalide la de otro de mayor
  prioridad (se replanifica respetando reservas de los de mayor prioridad; los de menor
  se replanifican despues si se ven afectados — esquema priorizado clasico).

### 3.5 Integracion con el reloj continuo de SimPy
- El planner usa `env.now` como `t0`. Las reservas viven en el mismo eje temporal real.
- La ejecucion (`_recorrer_tramo` modo plan) traduce el plan a `yield env.timeout(dt)`
  exactos, de modo que la posicion del agente en tiempo de sim coincide celda-a-celda con
  lo reservado. Determinismo total (mismo seed -> mismas reservas -> mismo .jsonl), siempre
  que el ORDEN de planificacion sea determinista (ver 3.6).

### 3.6 Orden de planificacion (prioridad) y determinismo
- Se necesita un ORDEN TOTAL para planificar agente por agente. Candidatos para la
  prioridad: (a) `spawn_index` (estable, ya existe), (b) prioridad de zona/tarea, (c)
  orden de llegada de la asignacion del dispatcher. **Decision MVP**: usar el orden en que
  el dispatcher asigna las tareas, con desempate por `agent_id` (determinista). Esto se
  alinea con el flujo actual y es reproducible. La prioridad explicita (aging para evitar
  inanicion) se anade en una fase posterior si se observa starvation (ver 4.x).
- Determinismo: ningun `set`/`dict` sin ordenar en rutas criticas; vecinos en orden
  lexicografico fijo (ya lo hace `_compute_departure_lanes`); tie-break del A* por
  contador incremental (ya lo hace `Pathfinder`). Mismo config + mismas tareas => mismo
  resultado bit a bit.

### 3.7 Que se reusa y que se jubila del trabajo F0-F3 (mapa explicito)
| Pieza F0-F3 | Destino en Opcion C |
|-------------|---------------------|
| Instrumentacion I1 (co-ocupacion) en `CongestionManager` | SE REUSA como validador: debe leer 0. |
| `_set_pos` choke point + `cm.move` | SE REUSA (alimenta I1; punto de emision). |
| F2 `staggered_start` (andenes + offset) | SE REUSA como condicion inicial sana (opcional; el planner ya evita el apelotonamiento, pero dispersar el arranque reduce el tamano del problema espacio-temporal en el cuello). |
| F3 `owner` dict (cap 1) | SE JUBILA -> reemplazado por `ReservationTable` (intervalos). |
| F3 espera `release_event | timeout W` + hard_cap en `_recorrer_tramo` | SE JUBILA -> el plan ya incorpora las esperas como pasos reservados; no hay espera reactiva. |
| F3 watchdog como garante de terminacion | DEGRADA a DETECTOR de seguridad (no deberia disparar nunca; si dispara = bug, alerta util). |
| `mode: cell` / `cell+corridor` | Se conservan intactos (no-regresion); se anade `mode: timewindow` nuevo. |

---

## 4. GARANTIA ANTI-DEADLOCK / ANTI-COLISION Y CASOS BORDE (EXHAUSTIVO)

### 4.1 Argumento de correccion (por que NO hay colision ni deadlock)

**Invariante central (INV):** En todo momento, para toda celda `c`, los intervalos en
`reservations[c]` de agentes distintos son disjuntos, y la posicion fisica de cada agente
en tiempo de sim esta SIEMPRE dentro de un intervalo que ese agente reservo en esa celda.

- *INV se mantiene*: solo `reserve()` anade intervalos, y solo lo hace si `is_free`
  (no solapamiento). La ejecucion (`_recorrer_tramo` modo plan) reproduce exactamente los
  `(celda, t)` reservados (determinismo de tiempos). Luego la posicion fisica nunca sale
  de lo reservado.
- **No colision (corolario directo de INV):** si dos agentes estuvieran en `c` en el mismo
  instante `t`, ambos tendrian un intervalo conteniendo `t` en `c`, contradiciendo que son
  disjuntos. => co-ocupacion imposible. (El metrico I1 debe leer 0; es la prueba empirica.)
- **No deadlock (planificacion priorizada + orden total):** los agentes se planifican en un
  orden total fijo `a1 < a2 < ... < aN`. Cuando se planifica `ai`, las reservas de
  `a1..a(i-1)` son inmutables y `ai` solo se ACOMODA a los huecos (incluida la accion
  esperar). La relacion "ai espera por aj" solo puede ir de mayor a menor indice (ai solo
  cede ante quien ya reservo, es decir aj con j<i). Esa relacion respeta el orden total =>
  es acíclica => no hay espera circular => no hay deadlock (Coffman: se rompe la condicion
  de espera circular).
- **Progreso / no freeze:** la accion "esperar en la celda actual" siempre esta disponible
  para el agente de cualquier prioridad mientras la celda donde esta siga siendo suya (lo
  es: la reservo al llegar). Y el agente de MAYOR prioridad (a1) nunca encuentra reservas
  ajenas en su camino (es el primero): su ruta es la A* estatica pura, siempre factible si
  el grafo es conexo. Por induccion, en cada ronda al menos el de mayor prioridad pendiente
  avanza hasta su meta y libera el futuro; los demas se acomodan. => el reloj siempre avanza
  y las WorkOrders se completan (sujeto a las salvedades de 4.2-4.3).

### 4.2 Caso borde: NO hay ruta libre en el horizonte de planificacion
- *Sintoma*: el A* espacio-temporal no encuentra `(goal, t)` alcanzable sin pisar reservas
  dentro del horizonte/limite de expansiones.
- *Causa tipica*: un agente de menor prioridad cuyo unico paso esta bloqueado por una
  permanencia larga (otro haciendo picking justo en su unico pasillo) mas alla del horizonte.
- *Manejo (escalera, de preferido a ultimo recurso)*:
  1. **Esperar-y-reintentar PLANIFICADO**: insertar una espera (reservar quedarse en la
     celda segura actual) por `dt` y reintentar la busqueda desde `t+dt`. Esto NO es la
     espera reactiva de F3 (es una reserva concreta, acotada y libre de conflicto).
  2. **Ampliar horizonte** una vez (busqueda mas profunda) antes de rendirse.
  3. **Fallback de seguridad**: si aun asi no hay plan (no deberia con grafo conexo y
     permanencias finitas), degradar ESE agente a la ruta estatica + un `_jump_to`
     I1-safe documentado, registrando el incidente (igual que F3 registra hardcap). Nunca
     crashear ni congelar (regla de oro 4.4 heredada). Este fallback se INSTRUMENTA para
     saber si alguna vez ocurre.

### 4.3 Caso borde: horizonte de planificacion finito (rutas/permanencias largas)
- El A* espacio-temporal podria expandir mucho si hay esperas largas. Se acota con:
  `timewindow.max_expansions` (corte duro del A*), `timewindow.plan_horizon` (segundos
  maximos a futuro a planificar de una vez; mas alla, ventana movil). Si se corta, aplica
  la escalera de 4.2. La permanencia (picking/staging) se modela como UN intervalo, no como
  miles de pasos de espera => no explota el arbol.

### 4.4 Caso borde: inanicion / starvation (prioridad fija perjudica al de menor indice)
- Con orden total fijo, el de menor prioridad podria esperar indefinidamente si los de mayor
  prioridad saturan su pasillo para siempre. En esta sim, las tareas son FINITAS (se acaban
  las WorkOrders), asi que la saturacion no es eterna => no hay inanicion real en regimen
  finito. Aun asi, como red: `aging` (subir la prioridad efectiva de un agente cuanto mas
  lleva esperando) se anade en fase posterior si la metrica de espera-maxima lo justifica.
  Es el mismo concepto 2.1 que la investigacion ya contempla.

### 4.5 Caso borde: recalculo cuando cambian las condiciones (dinamismo)
- Nuevas WorkOrders: se planifican contra reservas vigentes (no afectan planes existentes).
- Si en el futuro se introduce variabilidad (tiempos estocasticos, averias): re-planificar
  liberando las reservas FUTURAS del agente afectado y replanificando en orden de prioridad
  (los de mayor prioridad mantienen sus reservas; los de menor se re-acomodan). MVP es
  determinista, asi que esto queda documentado pero inactivo.

### 4.6 Caso borde: celdas de pick/staging/depot como destinos con PERMANENCIA
- Un destino donde el agente se queda (pick `picking_duration`, staging `discharge_time`,
  depot idle) se modela como intervalo de permanencia reservado. Sutileza: el idle en depot
  puede ser de duracion no conocida de antemano (el agente espera nueva tarea). Manejo:
  reservar el depot "hasta nuevo aviso" se evita; en su lugar el agente idle NO reserva a
  futuro indefinido — al recibir tarea reserva desde `env.now`. El depot puede tener varios
  andenes (F2) para que el idle de varios agentes no compita por una sola celda. Si el depot
  es estrecho, se modela como zona con aforo (complemento 2.13-C, fase posterior).

### 4.7 Caso borde: agentes lentos vs rapidos (Ground 1.0 vs Forklift 0.8)
- `dur` depende del `speed` del agente -> un Forklift ocupa cada celda mas tiempo. El planner
  lo maneja sin caso especial (sus ventanas son mas anchas). El unico cuidado: el chequeo de
  swap/cross debe comparar intervalos reales (no indices de paso), porque dos agentes de
  velocidad distinta no comparten "tick". Por eso el tiempo continuo es clave.

### 4.8 Caso borde: deadlock residual si la RESERVA falla / bug de la tabla
- Si por un bug `reserve()` aceptara un solape, INV se rompe y podria haber colision. Mitiga:
  (a) `reserve()` valida con `assert is_free(...)` en modo debug; (b) el metrico I1 sigue
  corriendo como verificacion independiente END-TO-END (si I1 > 0, hay bug, alerta); (c) el
  watchdog degradado sigue detectando stalls. Defensa en profundidad: la garantia teorica +
  dos detectores independientes (I1 y watchdog).

### 4.9 Caso borde: explosion del estado espacio-temporal y como acotarla
- Nodos `(celda, t)` con `t` continuo podrian ser infinitos. Acotacion:
  - El A* solo genera sucesores por acciones discretas (mover a vecino, esperar `dt_wait`
    cuantizado), asi que el espacio de `t` alcanzables es discreto y finito por horizonte.
  - `max_expansions` y `plan_horizon` cortan duro.
  - `dt_wait` (cuanto dura una accion "esperar") es un parametro: ni tan fino que explote, ni
    tan grueso que pierda soluciones. Se calibra (p.ej. = coste de una celda) y se prueba.
  - Purga de reservas pasadas mantiene la tabla pequena.
- Coste esperado: con decenas de agentes y rutas de decenas de celdas, A* espacio-temporal es
  perfectamente tratable (es lo que usan WMS reales con flotas mayores).

### 4.10 Caso borde: determinismo / reproducibilidad
- Requisitos: (a) orden total de planificacion determinista (3.6); (b) vecinos en orden fijo;
  (c) tie-break A* por contador; (d) ninguna iteracion sobre `set`/`dict` no ordenado en
  rutas que afecten al resultado; (e) `eps`/`dt_wait` fijos por config. Resultado: mismo
  config + mismas tareas => mismo `.jsonl` byte a byte. Se valida con doble corrida y diff.

### 4.11 Caso borde: arranque masivo (20 agentes, mismo depot) — el test estrella
- Es el escenario que hoy congela. Con time-window: los 20 se planifican en orden; el primero
  sale directo, el segundo reserva un anden/lane ligeramente desfasado o una micro-espera, etc.
  Nadie pisa a nadie por construccion. F2 (dispersion de andenes) ayuda dando celdas de
  arranque distintas, reduciendo el numero de micro-esperas. Criterio de exito: 0 freezes,
  0 co-ocupaciones (I1=0), la sim TERMINA. (Detalle en seccion 5, fase de validacion.)

### 4.12 Caso borde: grafo desconectado / goal inalcanzable estaticamente
- Si `find_path` estatico ya devolveria None (goal aislado), el planner espacio-temporal
  tambien: se hereda el manejo actual (registrar error de ruta, no crashear). No es un caso
  nuevo de la Opcion C.

---

## 5. PLAN DE IMPLEMENTACION POR FASES (incremental, reversible, detras de flag)

Principio rector (Ley #6 + regla de oro de F0-F3): **cada fase detras del flag
`congestion.mode: timewindow`; con el flag en cualquier otro valor el comportamiento es
BYTE-IDENTICO al actual.** Se empieza por lo de MENOR riesgo y se valida cada fase con
evidencia empirica (Ley #2) antes de pasar a la siguiente. Todo reversible (rama + tag).

### Fase 0 — Andamiaje y flag (riesgo casi nulo, 0 cambio de comportamiento)
- **Que**: anadir `mode: "timewindow"` al enum de `congestion` en `config.json` y a
  `CongestionManager` (nueva propiedad `timewindow_active`). Crear los modulos
  `reservation_table.py` y `spacetime_planner.py` VACIOS (clases con firma, sin logica) y
  los puntos de injerto en `RouteCalculator`/`_recorrer_tramo` GATEADOS por
  `timewindow_active` (rama nueva que, de momento, cae al comportamiento estatico actual).
- **Validar**: con `mode != timewindow`, correr la sim y `diff` del `.jsonl` contra un
  baseline guardado => IDENTICO. Con `mode: timewindow` la sim corre como hoy (la rama nueva
  delega aun en la estatica). Tests de humo: import OK, sim termina.
- **Reversible**: trivial (solo codigo muerto gateado).

### Fase 1 — ReservationTable + A* espacio-temporal "shadow" (planifica pero no ejecuta)
- **Que**: implementar `ReservationTable` (insertar/consultar intervalos disjuntos, swap
  check) y `SpaceTimePlanner.find_path_st` (A* mover/esperar sobre la tabla, heuristica
  octil reutilizada). En `mode: timewindow`, para cada tramo se CALCULA el plan espacio-
  temporal y se RESERVA, pero la EJECUCION sigue usando el recorrido actual (shadow mode):
  se compara el plan ST con la ruta estatica y se loguea (longitud, esperas insertadas,
  reservas). Aun NO se cambia como se mueve el agente.
- **Validar**: el planner produce rutas validas (sin solape en la tabla, verificado por
  `assert`), termina dentro de `max_expansions`, y el metrico "reservas con solape" = 0.
  Medir coste de planificacion (ms por tramo) en el layout real. Sim sigue terminando.
- **Reversible**: el shadow no altera el movimiento; quitar el flag basta.

### Fase 2 — Ejecucion segun plan (el switch real, todavia conservador)
- **Que**: en `mode: timewindow`, `_recorrer_tramo` deja de usar la espera reactiva y
  EJECUTA el plan ST: por paso, `yield env.timeout(t_sig - t_act)` y emision de evento. Las
  esperas planificadas se ejecutan como `env.timeout` en la celda segura. Empezar con
  movimiento CARDINAL (4-dir) para simplificar la garantia (sin cross diagonal).
- **Validar (prueba de estres de arranque)**: escenario de 20 agentes desde el mismo depot
  (reusar `_stress_harness.py` / `config_stress_*`). Criterio DURO de exito:
  **0 freezes (la sim termina sola, sin cap de wallclock), 0 colisiones (I1 = 0), watchdog
  no dispara ningun stall.** Ademas: comparar throughput vs baseline y vs F3. Revisar el
  `.jsonl` en el viewer: el arranque debe verse ordenado, sin solapamientos.
- **Reversible**: flag off => recorrido clasico; rama feature.

### Fase 3 — Diagonales + chequeo de cross/swap completo
- **Que**: habilitar movimiento 8-direccional en el planner con el chequeo de
  corner-cutting (cross) y swap (head-on) completo. Parametrizar `clearance` (`eps`).
- **Validar**: re-correr estres + un layout con pasillos de ancho 1 (head-on garantizado en
  el enfoque ingenuo). Criterio: I1=0, 0 freeze, throughput >= fase 2. Diff determinismo
  (doble corrida identica).

### Fase 4 — Robustez de escala (ventana movil opcional) y aging (si hace falta)
- **Que** (solo si las metricas lo piden): ventana movil WHCA* (reservar/ejecutar/replanear
  por bloques de `plan_horizon`) para acotar coste en mapas grandes / muchas tareas; `aging`
  de prioridad si se observa espera-maxima alta de algun agente; refinamiento del coste
  diagonal `0.1*speed*sqrt(2)` si se quiere fidelidad fisica.
- **Validar**: estres + layout grande; coste de planificacion acotado; sin regresion de
  conflicto/freeze; metricas de equidad (espera maxima por agente) razonables.

### Fase 5 — Limpieza y consolidacion
- **Que**: una vez timewindow probado y elegido como default operativo, decidir con el
  Director si los modos `cell`/`cell+corridor` se conservan como legado o se jubilan; mover
  el watchdog a rol de "detector de seguridad" formal; actualizar `AUDITORIA.md`/`README`.
- **Validar**: suite completa + no-regresion con flag off.

### Regla transversal de validacion de cada fase
1. **No-regresion byte-identica con flag off**: `diff` del `.jsonl` baseline vs corrida con
   `mode != timewindow`. DEBE ser identico (es el contrato de seguridad).
2. **Prueba de estres de arranque** (desde fase 2): 20 agentes, mismo depot => 0 freeze,
   I1=0, sim termina, watchdog limpio.
3. **Determinismo**: doble corrida con mismo config => `.jsonl` identico.
4. **Evidencia**: capturas del viewer + logs `[OK]` (Ley #2 + Ley #4 ASCII).

---

## 6. CRITERIOS DE EXITO Y METRICAS

**Criterios duros (gate de aceptacion de la Opcion C):**
- **Cero co-ocupaciones (I1 = 0)** en todos los escenarios — la garantia teorica verificada
  empiricamente por el metrico independiente del `CongestionManager`.
- **Cero freezes**: la sim TERMINA por logica propia (todas las WorkOrders completadas), sin
  depender de un cap de wallclock externo. El watchdog no registra ningun `watchdog_stall`.
- **Prueba de estres de arranque** (20 agentes, mismo depot) superada: termina, I1=0, sin
  stalls, en tiempo de sim razonable.
- **No-regresion byte-identica con flag off**: `.jsonl` identico al baseline.
- **Determinismo**: dos corridas con mismo config => `.jsonl` identico.

**Metricas de calidad (para comparar con baseline y con F3):**
- Throughput (WorkOrders/seg de sim) y makespan (t de termino).
- Distancia recorrida total y por agente; sobre-coste vs ruta estatica ideal (las esperas
  insertadas anaden tiempo, no distancia: medir ambas).
- Numero y duracion de esperas planificadas (cuanto "cuesta" la coordinacion).
- Espera maxima por agente (equidad / deteccion de starvation).
- Coste de planificacion: ms por tramo, expansiones de A*, tamano de la tabla de reservas.
- Utilizacion del cuello (depot/pasillos criticos): ocupacion temporal de las celdas hotspot
  (reusar `top_hotspots` de F1, que ahora mide reservas en vez de co-ocupaciones).

**Comparativa esperada**: vs F3 (espera reactiva), la Opcion C debe dar igual o mejor
throughput SIN stalls ni hardcaps, y co-ocupacion 0 estructural (F3 podia tener I1>0 en
ventanas de carrera). El coste extra es CPU de planificacion (aceptable, headless, offline).

---

## 7. RIESGOS, COMPLEJIDAD Y PLAN DE ROLLBACK

**Riesgos principales:**
1. **Reescritura del routing = riesgo central** (toca planificacion). Mitiga: todo detras de
   flag, fases shadow antes de ejecutar, no-regresion byte-identica obligatoria, rama+tag por
   fase. El codigo viejo (estatico + modos cell) queda intacto.
2. **Coste de planificacion** (A* espacio-temporal mas caro que el estatico). Mitiga:
   `max_expansions`, `plan_horizon`, ventana movil (fase 4), purga de reservas. Headless y
   offline: hay holgura de CPU.
3. **Sutilezas de tiempo continuo** (swap/cross con velocidades distintas, `eps`/clearance,
   bordes de intervalo). Mitiga: empezar cardinal (fase 2) antes de diagonales (fase 3);
   `assert is_free` en `reserve`; el metrico I1 como verificacion E2E independiente.
4. **Explosion de estado** si `dt_wait` mal calibrado. Mitiga: calibrar y acotar (4.9).
5. **Determinismo fragil** si entra iteracion sobre estructuras no ordenadas. Mitiga: orden
   total explicito + test de doble corrida en cada fase.
6. **Dinamismo real futuro** (estocasticidad) exigiria re-planificacion robusta. MVP es
   determinista; la re-planificacion priorizada esta disenada (3.4) pero no se activa hasta
   que haga falta.

**Complejidad**: ALTA (es "cambio de arquitectura", no parche). Por eso el plan es
estrictamente incremental y cada paso es independientemente validable y reversible.

**Plan de rollback (por capas):**
- *Inmediato*: poner `congestion.mode` en `off`/`instrument`/`cell` (flag) => se vuelve al
  comportamiento previo sin tocar codigo. Es el rollback de 1 linea de config.
- *Por fase*: cada fase es un commit/tag; `git revert`/`reset` a la fase anterior si una
  rompe la no-regresion.
- *Estructural*: como el modulo nuevo (`reservation_table`, `spacetime_planner`) esta
  gateado y aislado, se puede dejar "dormido" indefinidamente sin afectar la cadena viva.

---

## 8. RELACION CON EL "NORTE" Y DEGRADACION A COMBO A/B

La investigacion (`docs/INVESTIGACION_CONGESTION_SOLUCIONES.md`, seccion 4) recomendaba
COMBO B (one-way + semaforos + recovery) como destino "suficiente" y dejaba COMBO C
(time-window) como el **norte arquitectonico** — la opcion "de libro" para un gemelo de
almacen/AGV serio y escalable, a cambio de mayor coste/riesgo. El Director eligio ir
directo al norte (Opcion C). Implicaciones que este plan asume conscientemente:

- **Por que tiene sentido ir al norte ahora**: si el objetivo es un gemelo digital escalable
  a muchas AGVs, time-window es la arquitectura final correcta; pagar el coste una vez evita
  construir COMBO B y luego migrar igual. Encaja nativo con SimPy (tiempo continuo) y previene
  en vez de curar, eliminando de raiz la clase de bug que F0-F3 solo mitigaba.
- **Red de seguridad heredada de la investigacion**: Combo C se acompaña, en la propia
  investigacion, de 2.7 (muelles/aforo de staging) y 2.2 (deteccion de wait-for) como red.
  Aqui esa "red" se materializa como: el metrico I1 + el watchdog degradado a detector +
  el fallback I1-safe de 4.2. No son necesarios para la garantia, pero dan defensa en
  profundidad mientras se gana confianza.
- **Plan de degradacion si C resultara inviable** (coste/complejidad inaceptables tras las
  fases shadow): como TODO esta detras de flag y el codigo estatico+cell queda intacto, se
  puede:
  1. Parar en la fase shadow (fase 1) sin haber tocado el movimiento, y
  2. Pivotar a COMBO B/A, que la investigacion deja completamente especificado: one-way
     (2.5) dirigiendo el pathfinder, semaforos en cruces (2.6), cesion+aging (2.1) y
     deteccion wait-for (2.2). La capa F2 (dispersion de spawn) y la instrumentacion I1 que
     este plan REUSA son utiles para CUALQUIERA de los tres combos: nada del trabajo se
     pierde si hay que degradar.
- **Peldanos compartidos**: la `ReservationTable` por intervalos y el A* espacio-temporal
  son el activo de mayor valor a largo plazo; aunque se degradara temporalmente a B, quedan
  como base para retomar C cuando el proyecto escale.

---

## APENDICE A — Punteros exactos de codigo para la implementacion (anti-alucinacion)

- Flag/config: `config.json` -> bloque `"congestion"`; lectura en
  `src/subsystems/simulation/warehouse.py` (`AlmacenMejorado.__init__`, ~L195-208).
- Estado dinamico: `src/subsystems/simulation/congestion_manager.py` (anadir `ReservationTable`
  aqui o en modulo hermano; conservar metrico I1 `enter/leave/move` y `resumen()`).
- Planificacion estatica a reusar: `src/subsystems/simulation/pathfinder.py`
  (`is_walkable`, `get_neighbors`, `heuristic`) y `route_calculator.py` (`calculate_route`,
  iteracion por tramos — punto de injerto del planner ST).
- Ejecucion del movimiento: `src/subsystems/simulation/operators.py`
  (`BaseOperator._recorrer_tramo` ~L333-421, choke point `_set_pos` ~L290-304, spawn
  `_spawn_lane`/`_spawn_stagger` ~L265-288). Rama nueva gateada por `timewindow_active`.
- Motor/arranque: `src/engines/event_generator.py` (`crear_simulacion` ~L120-191; lazo
  `ejecutar` ~L211-229; arranque del watchdog ~L166-169).
- Estres: `_stress_harness.py` + `config_stress_baseline.json` / `config_stress_f2.json` /
  `config_stress_f3.json` (anadir `config_stress_timewindow.json`).

> NOTA (Ley #1): este documento es PLAN, no implementacion. Requiere el OK del Director
> antes de escribir codigo. Sugerencia de arranque: aprobar el alcance de Fase 0+1 (flag +
> ReservationTable + planner en shadow), que es de riesgo casi nulo y ya permite medir el
> coste real del A* espacio-temporal sobre el layout de produccion.

<!-- FIN_DOCUMENTO -->

