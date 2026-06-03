# PLAN INICIATIVA #2 - CONGESTION Y CONTENCION DE RECURSOS ENTRE OPERARIOS

> Rama: `feature/allocation-layer-v12.1`
> Autor: Cerebellum (Arquitecto Senior / Logistica de Almacenes)
> Fecha: 2026-06-01
> Estado: PLAN APROBADO PARA REVISION DEL DIRECTOR (NO implementado todavia)
> Alcance: motor SimPy headless (`src/subsystems/simulation/`). NO toca live simulation (eliminada a proposito). NO push.
> Documento ASCII puro a proposito (Ley #4: consola Windows cp1252). No usar emojis ni acentos en codigo/prints.

---

## 0. RESUMEN EJECUTIVO (TL;DR para el Director)

Hoy la simulacion NO modela congestion: los operarios se atraviesan. Las "colisiones"
que se ven en el viewer son puramente visuales; el motor no tiene ninguna nocion de
ocupacion de celdas. Queremos que dos agentes no puedan ocupar la misma celda al mismo
tiempo, que esperen cuando el camino esta ocupado, y que el throughput refleje los
atascos reales de un almacen.

El intento anterior fracaso por un motivo concreto y reproducible: al arrancar, TODOS
los operarios nacen apilados en la misma celda del depot (`staging 1`, fallback `(3,29)`)
y arrancan su proceso a la vez en `t=0`. Al anadir reservas de celda SIN manejo de
deadlock, ninguno podia avanzar (todos querian la misma celda contigua, espera circular)
y el sistema se congelo.

La REGLA DE ORO de este plan: **un agente que no encuentra ruta o celda libre ESPERA y
REINTENTA; nunca se congela, nunca aborta el tour por bloqueo temporal.** El estado
"bloqueado" debe ser siempre un estado transitorio del que se sale con tiempo, backoff y,
si hace falta, cesion por prioridad.

Estrategia de entrega: incremental y verificable en 5 fases. Empezamos por INSTRUMENTAR
(medir colisiones sin cambiar comportamiento), luego ARRANQUE ESCALONADO (mata el choque
de spawn), luego EXCLUSION POR CELDA con espera simple, luego REPATHING DINAMICO, y por
ultimo RESOLUCION DE DEADLOCK formal. Cada fase es desplegable y reversible por su cuenta.

---

## 1. OBJETIVO Y FILOSOFIA

### 1.1 Objetivo funcional
Modelar la contencion fisica de recursos (espacio transitable) entre agentes para que la
simulacion capture cuellos de botella reales de circulacion: pasillos estrechos, cruces,
colas frente a staging, y zonas de alta densidad. El resultado esperado es un throughput
que se degrada de forma plausible con mas agentes (no lineal), permitiendo al Director
dimensionar flota y layout.

### 1.2 Invariantes que el sistema debe garantizar
- **I1 - Exclusion espacial:** en cualquier instante de simulacion, una celda transitable
  es ocupada por como maximo un agente. (Definicion base; ver 4.3 para celda vs. swap.)
- **I2 - Sin freeze global:** la simulacion siempre progresa. Nunca todos los agentes
  quedan permanentemente en `waiting`. Si el reloj de SimPy avanza, al menos un agente
  debe poder actuar dentro de un horizonte acotado.
- **I3 - Sin abort por bloqueo temporal:** quedarse sin ruta o sin celda libre NUNCA
  termina el tour con error. Solo errores estructurales (origen/destino intransitables en
  el mapa estatico, datos corruptos) pueden abortar, y aun esos con fallback seguro.
- **I4 - Terminacion garantizada:** la condicion de fin de simulacion
  (`simulacion_ha_terminado()`) sigue alcanzandose; el modelo de congestion no debe crear
  procesos que nunca mueran ni impedir el drenaje final de WorkOrders.
- **I5 - Determinismo opcional:** con semilla fija y misma config, dos corridas producen
  el mismo `.jsonl`. La resolucion de empates de contencion debe ser determinista
  (orden por prioridad y luego por agent_id, nunca por orden de hash/dict no estable).

### 1.3 Filosofia de diseno
1. **Esperar es legitimo, congelarse no.** Un agente bloqueado es un agente que ya tiene
   un plan para desbloquearse (timeout + reintento + escalado). El "estado terminal" de un
   agente es `idle` o `finished`, jamas `stuck`.
2. **Empezar por medir, no por arreglar.** No se anade ninguna regla de exclusion hasta
   tener instrumentacion que cuente colisiones y co-ocupaciones. Sin baseline no hay forma
   de saber si una fase mejora o empeora.
3. **Incremental y reversible.** Cada fase es un commit aislado detras de un flag de config
   (`congestion.enabled`, `congestion.mode`). Si una fase rompe el throughput, se apaga el
   flag y volvemos al comportamiento anterior sin revertir codigo.
4. **El mapa estatico es la verdad del espacio; la ocupacion dinamica es una capa encima.**
   No tocamos `collision_matrix` (TMX). Anadimos una capa de ocupacion en tiempo de
   simulacion que vive aparte y se consulta ademas del mapa estatico.
5. **Preferir el modelo SimPy idiomatico.** SimPy ya tiene primitivas de recurso
   (`Resource`, `Container`, `Store`, eventos) hechas para exactamente esto. Reservar
   espacio = adquirir un recurso. Esperar = hacer `yield request`. Es mas robusto que
   inventar locks manuales con diccionarios.

---

## 2. DIAGNOSTICO DEL MODELO DE MOVIMIENTO ACTUAL (anclado en codigo real)

Todo lo de esta seccion fue verificado por lectura directa del codigo en
`src/subsystems/simulation/` en la rama `feature/allocation-layer-v12.1`.

### 2.1 Colision: SOLO estatica
- `LayoutManager._build_collision_matrix()` (layout_manager.py ~80) construye
  `self.collision_matrix`: una matriz booleana `[y][x]` derivada del TMX. `True` =
  caminable, `False` = bloqueado. Es estatica: se calcula una vez al cargar el mapa y no
  cambia durante la simulacion.
- `Pathfinder.__init__(collision_matrix)` (pathfinder.py ~22) guarda esa matriz.
  `is_walkable(x,y)` (pathfinder.py ~45) consulta solo `collision_matrix[y][x]` y los
  limites del grid. **No conoce a ningun otro agente.**
- `Pathfinder.get_neighbors()` (pathfinder.py ~65) genera 8 vecinos (cardinales +
  diagonales) filtrando por `is_walkable`. `find_path()` (pathfinder.py ~145) es A* con
  heuristica octile. Devuelve `None` si origen/destino estan fuera de limites, bloqueados,
  o si las regiones estan desconectadas.

**Consecuencia:** dos agentes pueden estar en la misma celda en el mismo instante sin que
nada lo impida. Las colisiones del viewer son cosmeticas.

### 2.2 Origen del choque al arranque (spawn stacking)
- En `agent_process` (operators.py ~273 para Ground, ~654 para Forklift) cada agente se
  inicializa con:
  `depot_location = staging_locs.get(1, (3,29)); self.current_position = depot_location`.
  Es decir, TODOS arrancan en la celda del staging 1 (o el fallback `(3,29)`).
- `crear_operarios()` (operators.py ~1000) hace `env.process(operator.agent_process())`
  para cada agente en un bucle, sin escalonar. En SimPy todos esos procesos quedan listos
  para ejecutarse en `t=0`.
- **Resultado:** en `t=0` hay N agentes apilados en una sola celda, todos pidiendo salir a
  la vez. Cualquier regla de exclusion ingenua aqui produce contencion maxima desde el
  primer instante. Este es el epicentro del fracaso previo.

### 2.3 Movimiento: ruta precalculada por tour, sin reverificacion
- `RouteCalculator.calculate_route()` (route_calculator.py ~37) precalcula `segment_paths`:
  una lista de caminos A*, uno por cada WorkOrder del tour, mas el retorno. Lo hace UNA
  VEZ, al inicio del tour (route_calculator.py 110-145).
- Si CUALQUIER tramo da `find_path() == None`, `calculate_route` devuelve
  `success: False` con caminos parciales y `errors` (route_calculator.py 117-129). El
  retorno a origen `None` solo se loguea, no es fatal (route_calculator.py 151-152).
- En `agent_process` (operators.py 320-381) el agente recorre `segment_path[1:]` celda a
  celda:
  ```
  for step_idx, step_position in enumerate(segment_path[1:], 1):
      self.current_position = step_position
      ... registrar_evento('estado_agente', ...)
      yield self.env.timeout(TIME_PER_CELL * self.default_speed)   # TIME_PER_CELL = 0.1
  ```
  **No hay ninguna comprobacion de ocupacion antes de pisar `step_position`.** El agente
  asume que la celda esta libre porque el mapa estatico dice que es caminable.
- La ruta NO se recalcula a mitad de tour. `segment_paths` es fijo para todo el tour.
- En el tramo de descarga a staging (operators.py 482-510) se llama a `find_path` en vivo;
  si devuelve `None`/corto, se hace un **teletransporte silencioso**
  (`self.current_position = staging_location`) y se continua. Esto hoy enmascara fallos de
  ruta, pero rompe I1 si lo dejamos cuando haya congestion.

### 2.4 Sin fallback ante bloqueo
- Hoy `find_path == None` en un tramo de picking aborta el tour (via `success: False`
  aguas arriba). No hay "esperar y reintentar". El unico camino alterno es el teletransporte
  del tramo de staging (2.3), que es semanticamente incorrecto.
- `default_speed`: Ground = 1.0, Forklift = 0.8 (operators.py 253, 631). `TIME_PER_CELL`
  = 0.1 hardcodeado dentro de `agent_process` (operators.py 270, 670). El paso temporal por
  celda es la granularidad natural donde insertar la espera por congestion.

### 2.5 Duplicacion estructural relevante para el plan
- `GroundOperator.agent_process` (~256-600) y `Forklift.agent_process` (~639-960) son
  ~95% identicos (solo cambian lifting y velocidad). **Cualquier cambio al lazo de
  movimiento hay que hacerlo en DOS sitios** salvo que primero extraigamos el lazo a un
  helper compartido en `BaseOperator`. Ver fase 0 (refactor de bajo riesgo) en 6.1.

### 2.6 Tabla de hechos confirmados
| Hecho | Archivo:linea | Implicacion para Iniciativa #2 |
|-------|---------------|--------------------------------|
| Colision solo estatica | pathfinder.py 45, 63; layout_manager.py 80 | Hay que anadir capa de ocupacion dinamica |
| Spawn apilado | operators.py 273-274, 654-655 | Arranque escalonado + dispersion de depots |
| Procesos en t=0 sin escalonar | operators.py 1051, 1070, 1102, 1123 | Stagger de arranque |
| Ruta precalculada por tour | route_calculator.py 110-145 | Necesario repathing dinamico |
| Paso celda a celda sin chequeo | operators.py 340-379 | Punto exacto de insercion de la espera |
| Abort si find_path None | route_calculator.py 117-129 | Cambiar a esperar/reintentar |
| Teletransporte a staging | operators.py 510-512 | Eliminar; sustituir por espera real |
| Lazo duplicado Ground/Forklift | operators.py 256, 639 | Extraer helper antes de tocar el lazo |

---

## 3. ANALISIS DEL FRACASO PREVIO Y CATALOGO DE MODOS DE FALLO

### 3.1 Que paso la vez anterior (reconstruido)
El Director anadio reservas de celda encima del modelo de 2.x SIN manejo de deadlock. Con
todos los agentes apilados en el depot en `t=0` (2.2), cada uno intentaba reservar la
siguiente celda para salir. Como todos competian por el mismo embudo de celdas contiguas
al depot, se formo una **espera circular**: A espera la celda que ocupa B, B espera la que
ocupa C, C espera la de A. Sin temporizacion ni cesion, nadie soltaba su celda y nadie
avanzaba. El sistema dejo de moverse (freeze/deadlock). Sintoma observado: "se chocaban al
salir, colapsaban y dejaban de moverse porque no encontraban a donde moverse".

Causa raiz: **se introdujo adquisicion de recurso (reserva) sin las tres salvaguardas
obligatorias**: (a) timeout en la espera, (b) politica de cesion/backoff, (c) arranque
escalonado que evita la contencion maxima inicial. Reservar sin liberar-bajo-presion es la
receta canonica del deadlock (condiciones de Coffman: exclusion mutua + hold-and-wait +
no-preemption + espera circular, las cuatro presentes a la vez).

### 3.2 Catalogo exhaustivo de modos de fallo (y como los neutraliza este plan)

**F1 - Choque al spawn (stacking inicial).**
N agentes en una celda en `t=0`. Mitigacion: arranque escalonado (cada agente arranca con
un `yield env.timeout(offset_i)`) + dispersion de posiciones iniciales (repartir depots o
celdas de espera previas). Ver 4.6.

**F2 - Deadlock por espera circular (Coffman completo).**
Ciclo de agentes esperandose mutuamente, ninguno cede. Mitigacion en capas:
(a) prevencion por orden total de adquisicion de celdas (4.5);
(b) deteccion por timeout de espera + (c) resolucion por backoff aleatorio y cesion por
prioridad (el de menor prioridad libera y re-planifica). Ver 4.5 y 4.7.

**F3 - Livelock.**
Agentes que ceden a la vez, vuelven a chocar, ceden otra vez, en bucle, sin progreso pese
a estar "activos". Mitigacion: backoff con jitter aleatorio (desincroniza), y cesion
asimetrica por prioridad/agent_id (rompe la simetria que causa el livelock). Ver 4.7.

**F4 - Starvation.**
Un agente de baja prioridad nunca consigue avanzar porque siempre cede ante otros.
Mitigacion: aging - la prioridad efectiva de espera sube con el tiempo esperado, de modo
que tras esperar suficiente, gana. Cota dura de espera maxima. Ver 4.7.

**F5 - Repathing infinito.**
Un agente recalcula ruta una y otra vez sin avanzar (cada nueva ruta vuelve a estar
ocupada). Mitigacion: limite de reintentos de repathing por tramo; tras el limite, pasar a
"esperar en sitio" en vez de seguir recalculando; y cota de coste para no repathear si la
ruta alterna es absurdamente larga. Ver 4.4 y 4.8.

**F6 - Pasillos de un solo sentido / corredores estrechos (ancho 1).**
Dos agentes en sentidos opuestos en un pasillo de una celda de ancho: head-on irresoluble
por espera simple (ninguno puede apartarse). Mitigacion: detectar el head-on (cada uno
quiere la celda del otro = swap), y forzar que UNO retroceda hasta el nodo de bifurcacion
mas cercano (celda con grado >= 3) para ceder paso, elegido por prioridad. Opcional:
modelar pasillos como recurso de capacidad 1 con direccion. Ver 4.3 (swap) y 5.

**F7 - Agente atrapado (boxed-in).**
Un agente rodeado de celdas ocupadas/bloqueadas sin vecino libre. Mitigacion: es un estado
TRANSITORIO valido. El agente espera en su celda (no aborta) hasta que un vecino se libere;
con cota de espera dispara repathing y, en ultimo extremo, alarma de instrumentacion (no
crash). Ver 4.4.

**F8 - Cuello en staging (cola de descarga).**
Multiples agentes convergen al mismo staging a descargar y se apilan en las celdas de
acceso. Mitigacion: modelar el punto de descarga como recurso con cola FIFO
(`simpy.Resource(capacity=k)` donde k = celdas de muelle), y celdas de aproximacion como
zona de espera. La cola es deseable (refleja la realidad), pero no debe propagarse hacia
atras hasta congelar pasillos: cota de longitud de cola + puntos de espera fuera del
flujo. Ver 4.6 y 5.

**F9 - Capacidad mal calibrada que congela todo.**
Si la granularidad del recurso es demasiado gruesa (p.ej. un Resource por toda una zona con
capacity=1) un solo agente bloquea zonas enteras y el sistema se serializa o se congela.
Mitigacion: granularidad por celda como base; recursos de zona solo como capa opcional con
capacidad calibrada y validacion de que capacity >= 1 siempre, y nunca menor que el numero
de celdas de entrada obligadas. Tests de calibracion en fase 5. Ver 4.2 y 7.

**F10 - Interbloqueo destino-ocupado-por-quien-espera (hold-and-wait clasico).**
A ya ocupa su celda y pide la siguiente; el ocupante de la siguiente esta esperando una
celda que necesita A. Es F2 a escala local. Mitigacion: la espera SIEMPRE conserva la celda
actual (no la suelta hasta tener la siguiente confirmada) salvo durante una cesion explicita
por prioridad, que es atomica (suelta y retrocede a una celda libre conocida). Ver 4.5.

**F11 - Terminacion bloqueada (la sim no acaba).**
Si un agente queda en espera perpetua, `simulacion_ha_terminado()` podria no dispararse o
el `.jsonl` no drena. Mitigacion: I2/I4 - watchdog global que, si detecta T segundos de
sim sin que NINGUN agente cambie de celda, fuerza resolucion de deadlock global (cesion del
de menor prioridad) y lo registra como evento. Ver 4.7 y 7.

**F12 - Explosion de eventos / log gigante.**
Anadir esperas y reintentos puede multiplicar los `registrar_evento` y los `print` del hot
path (ya hoy hay cientos de prints por tour, ver AUDITORIA). Mitigacion: registrar eventos
de espera de forma agregada (un evento al entrar en `waiting` y otro al salir, con
duracion), no uno por tick; prints detras de flag de debug. Ver 6 y 7.

**F13 - No determinismo.**
Resolver empates de contencion por orden de iteracion de un dict o por hash rompe I5.
Mitigacion: todo desempate por tupla (prioridad, agent_id) y todo jitter por un RNG con
semilla derivada de la global. Ver 4.7 y 7.

**F14 - Deadlock con el modelo de stock/reservas de Iniciativa #1.**
La Iniciativa #1 ya introdujo reservas de STOCK. No confundir con reservas de ESPACIO. Hay
que garantizar que un agente que espera por espacio no mantenga indefinidamente una reserva
de stock que bloquee a otros, ni viceversa. Mitigacion: las dos capas de recurso son
ortogonales pero el orden de adquisicion debe ser fijo (primero stock, luego espacio, o al
reves, pero SIEMPRE el mismo) para no crear un deadlock cruzado entre recursos heterogeneos.
Ver 4.5 y riesgos en 8.

---

## 4. DISENO DE LA SOLUCION (decisiones de arquitectura)

### 4.1 Capa de ocupacion dinamica (no tocar el mapa estatico)
Se introduce un objeto nuevo, p.ej. `CongestionManager` (archivo nuevo
`src/subsystems/simulation/congestion_manager.py`), inyectado en el `almacen` junto a
`pathfinder`/`route_calculator`. Responsabilidad unica: saber que celdas estan ocupadas en
tiempo de simulacion y mediar las adquisiciones/liberaciones. El `collision_matrix` estatico
sigue intacto y se sigue usando para A*; la capa dinamica es un filtro adicional.

### 4.2 Eleccion de granularidad: celda como recurso base (RECOMENDADO)
Opciones evaluadas:

- **(A) Reserva por CELDA.** Cada celda transitable es un recurso de capacidad 1.
  Pros: granularidad maxima = maximo paralelismo, modelo fisico fiel, calibracion trivial
  (capacity siempre 1). Contras: muchos recursos, mas eventos, requiere cuidado con swaps y
  diagonales. **RECOMENDADA como base.**
- (B) Reserva de RUTA completa (reservar todas las celdas del tramo antes de moverse).
  Pros: previene deadlock por construccion si se adquiere en orden total. Contras: enormes
  hold-and-wait, mata el paralelismo, una ruta larga bloquea media nave -> tiende a F9.
  **Rechazada como base; util solo para tramos criticos cortos.**
- (C) Reserva por ZONA/PASILLO (recurso por segmento de pasillo con capacity = aforo).
  Pros: pocas entidades, modela bien corredores. Contras: granularidad gruesa, riesgo F9,
  define mal los cruces. **Adoptada como capa OPCIONAL encima de (A) para pasillos de ancho
  1 (F6) y muelles de staging (F8), no como base.**

Decision: **base por celda (A)**, con recurso de pasillo direccional (C) solo donde el
ancho del corredor sea 1 (detectado del layout), y recurso de muelle (Resource con
capacity=numero de celdas de descarga) para staging.

Implementacion sugerida: en vez de un `simpy.Resource` por celda (costoso si el grid es
grande y la mayoria de celdas nunca se usan), usar **reserva perezosa**: un dict
`occupied: Dict[(x,y), agent_id]` + un dict de eventos SimPy por celda creados on-demand
para las celdas en disputa. Adquirir = marcar ocupada o, si esta ocupada, `yield` sobre el
evento de liberacion de esa celda con timeout. Esto da la semantica de `Resource(cap=1)`
sin instanciar millones de recursos. Alternativa idiomatica pura: `simpy.Resource` creado
on-demand y cacheado por celda. Ambas validas; preferir la que pase los tests de F2/F8 con
menos codigo.

### 4.3 Modelo de paso atomico (lo que reemplaza al lazo de 2.3)
El nuevo "paso de una celda" es:
1. El agente ESTA en `cur` (ya la posee). Quiere ir a `nxt` (siguiente celda del path).
2. Intentar adquirir `nxt`:
   - Si libre -> adquirir `nxt`, mover (`current_position = nxt`, `yield timeout(...)`),
     liberar `cur`. (Conserva la celda actual hasta tener la siguiente: evita F10.)
   - Si ocupada -> entrar en `waiting`: `yield` sobre la liberacion de `nxt` con un timeout
     de espera `W`. Si se libera antes de `W`, adquirir y mover. Si vence `W`, escalar
     (4.4 repathing / 4.7 resolucion).
3. **Swap / head-on (F6):** detectar si el ocupante de `nxt` quiere `cur` simultaneamente
   (intercambio). Permitir el swap atomico solo si esta explicitamente habilitado y es
   seguro (dos agentes intercambian celda en el mismo instante); por defecto, NO permitir
   swap (dos cuerpos no se cruzan en un pasillo de ancho 1) y resolver por cesion (uno
   retrocede). El swap atomico es comodo pero fisicamente irreal en ancho 1; mantener
   desactivado salvo en cruces de ancho >= 2.
4. **Diagonales:** A* permite diagonales (2.1). Una diagonal cruza la esquina de dos celdas
   ortogonales. Para no permitir "corner cutting" a traves de dos obstaculos, al moverse en
   diagonal de `cur` a `nxt` exigir que al menos una de las dos celdas ortogonales
   compartidas este libre/caminable (regla estandar de no-corner-cutting). Para congestion,
   decidir politica: por defecto, una diagonal solo requiere reservar `nxt` (simple); como
   refuerzo opcional, reservar tambien la celda ortogonal compartida para evitar dos
   diagonales que se cruzan en X. Empezar simple; endurecer si F-tests lo piden.

### 4.4 Politica "sin ruta / sin celda libre -> esperar y reintentar, NUNCA congelar"
Regla de oro operacional. Pseudocodigo del tramo:
```
intentos_repath = 0
while not en_destino_tramo:
    nxt = siguiente_celda(path_actual)
    ok = intentar_adquirir(nxt, timeout=W)        # 4.3
    if ok:
        mover_y_liberar_anterior()
        continue
    # vencio la espera por nxt
    intentos_repath += 1
    if intentos_repath <= MAX_REPATH:
        nuevo = pathfinder.find_path(cur, destino, evitando=ocupadas_persistentes)
        if nuevo and coste(nuevo) <= coste_actual * FACTOR_MAX:
            path_actual = nuevo
            intentos_repath_reset_parcial()
            continue
    # no hay repath util -> esperar en sitio con backoff y, si procede, ceder por prioridad
    esperar_en_sitio(backoff_con_jitter())        # 4.7
    # el bucle NUNCA hace 'return error'; solo sale al llegar o por cesion controlada
```
Puntos clave:
- `find_path` con `None` deja de ser fatal. Se traduce en "espera y reintenta".
- Repathing acotado por `MAX_REPATH` y por coste relativo `FACTOR_MAX` (evita F5).
- Tras agotar repathing, el agente ESPERA EN SITIO (no aborta, no recalcula en bucle).
- El tramo de staging deja de teletransportar (2.3); usa el mismo bucle.

### 4.5 Prevencion de espera circular por orden total (anti-deadlock estructural)
Cuando un agente necesita adquirir MAS de una celda a la vez (p.ej. swap, o reservar
celda+diagonal-ortogonal, o un mini-tramo critico), las adquiere SIEMPRE en un orden total
fijo (p.ej. orden lexicografico por `(x,y)`). Adquirir recursos heterogeneos (stock de
Iniciativa #1 vs espacio) tambien en orden fijo de tipos (F14). Esto elimina por
construccion una de las cuatro condiciones de Coffman (espera circular) en las
adquisiciones multiples. Para la adquisicion de UNA sola celda por paso (caso comun), la
prevencion estructural la dan el timeout + la cesion (4.7), no el orden total.

Regla hold-and-wait: nunca soltar la celda actual antes de tener la siguiente (4.3.2),
EXCEPTO en una cesion atomica por prioridad, donde soltar+retroceder es un solo acto
indivisible hacia una celda libre ya identificada.

### 4.6 Arranque escalonado y dispersion inicial (mata F1)
Dos medidas combinadas en `crear_operarios` y/o en el preludio de `agent_process`:
1. **Stagger temporal:** cada agente `i` arranca con `yield env.timeout(spawn_offset * i)`
   antes de su primer movimiento. `spawn_offset` configurable (p.ej. 1-3 * TIME_PER_CELL).
   Desincroniza el embudo de salida del depot.
2. **Dispersion espacial:** repartir las posiciones iniciales. Opciones: (a) si hay varios
   stagings, repartir agentes entre ellos; (b) precomputar N celdas de espera caminables
   contiguas al depot ("anden de salida") y asignar una distinta a cada agente; (c) celda de
   depot como recurso de capacidad k con cola, de modo que los agentes salgan en orden.
   Recomendado: (b) andenes de salida distintos + (1) stagger. Asi en `t=0` no hay dos
   agentes en la misma celda.

Esto ataca el epicentro del fracaso previo ANTES de introducir cualquier exclusion dura.

### 4.7 Deteccion y resolucion de deadlock (timeout + backoff + cesion por prioridad)
Capas defensivas, de mas barata a mas cara:
1. **Espera con timeout `W` por celda** (4.3): convierte cualquier bloqueo en transitorio.
2. **Backoff con jitter:** al reintentar, esperar `base * 2^k + rand(0, jitter)` (cota
   superior `W_max`). El jitter rompe sincronias (anti-F3 livelock). RNG con semilla
   derivada de la global (I5/F13).
3. **Cesion por prioridad (preemption suave):** si tras `W` el agente sigue bloqueado y
   detecta contencion mutua (el que ocupa `nxt` tambien esta `waiting`), se compara
   `(prioridad_efectiva, agent_id)`. El "perdedor" CEDE: retrocede a una celda libre
   conocida (la que acaba de dejar u otra adyacente libre) y deja pasar al "ganador". La
   prioridad efectiva incorpora **aging** (sube con el tiempo esperado) para evitar
   starvation (F4).
4. **Watchdog global (anti-F11):** un proceso SimPy vigia que el conjunto de
   `current_position` cambie. Si pasan `T_watchdog` segundos de sim sin que NINGUN agente
   cambie de celda, declara deadlock global, fuerza la cesion del de menor prioridad de cada
   ciclo detectado, y registra un evento `congestion_deadlock_resuelto`. Es la red de
   ultima instancia que garantiza I2.

Cota dura: todo agente tiene un `WAIT_HARD_CAP`. Si lo alcanza, dispara repathing forzado y,
si aun nada, log de incidente + continua esperando en ciclos acotados (jamas crash).

### 4.8 Repathing dinamico
- Disparadores: vencimiento de `W` repetido en la misma celda, o deteccion de que la celda
  ocupada lo esta de forma "persistente" (sigue ocupada tras varios `W`).
- `find_path` se invoca pidiendo evitar el conjunto de celdas ocupadas persistentes (pasar
  un set de celdas a tratar como no-caminables temporalmente, sin mutar `collision_matrix`).
- Aceptar la nueva ruta solo si su coste <= `coste_restante_actual * FACTOR_MAX` (evita
  rodeos absurdos). Si no, esperar en sitio.
- Limite `MAX_REPATH` por tramo. Agotado, se deja de recalcular y se espera (anti-F5).

### 4.9 Parametros de configuracion (todo en config.json, Ley #3)
Nuevo bloque `congestion` en `config.json` (la web solo lo edita, el motor solo lo lee):
```
"congestion": {
  "enabled": false,            // master switch; false = comportamiento actual exacto
  "mode": "cell",              // "off" | "instrument" | "cell" | "cell+corridor"
  "wait_timeout": 0.5,         // W: espera por celda antes de escalar
  "wait_hard_cap": 30.0,       // cota dura de espera de un agente
  "backoff_base": 0.1,
  "backoff_jitter": 0.1,
  "max_repath": 3,             // reintentos de repathing por tramo
  "repath_cost_factor": 2.0,   // FACTOR_MAX
  "spawn_offset": 0.3,         // stagger temporal por agente
  "watchdog_window": 5.0,      // T_watchdog
  "allow_swap": false,         // swap atomico en cruces anchos
  "aging_rate": 1.0            // cuanto sube la prioridad efectiva por seg esperado
}
```
`enabled:false` debe reproducir el `.jsonl` actual byte a byte (gate de no-regresion).

---

## 5. CASOS BORDE EXHAUSTIVOS (con mitigacion concreta)

| ID | Caso borde | Mitigacion |
|----|-----------|-----------|
| CB1 | N agentes en la misma celda de depot en t=0 | Stagger temporal + andenes de salida distintos (4.6) |
| CB2 | Pasillo ancho 1, dos agentes de frente (head-on) | Detectar swap; el de menor prioridad retrocede al nodo de grado>=3 mas cercano (4.3, F6) |
| CB3 | Ciclo de 3+ agentes esperandose (espera circular) | Timeout + cesion por prioridad + watchdog (4.7) |
| CB4 | Agente totalmente rodeado (boxed-in) | Estado transitorio: espera en sitio, no aborta; repath al liberarse vecino (F7) |
| CB5 | Cola larga frente a un staging | Muelle como Resource(cap=celdas); puntos de espera fuera del flujo (F8) |
| CB6 | Repath devuelve siempre ruta ocupada | MAX_REPATH; tras agotar, esperar en sitio (F5) |
| CB7 | Repath devuelve rodeo absurdo (10x) | Rechazar por repath_cost_factor; esperar (4.8) |
| CB8 | Dos diagonales que se cruzan en X | No-corner-cutting + reserva opcional de celda ortogonal (4.3.4) |
| CB9 | find_path None por destino temporalmente "rodeado" de agentes | Tratar como espera, no como abort (4.4) |
| CB10 | Destino de picking ocupado por otro agente parado pickeando | Esperar a que el otro termine y se mueva; cota por wait_hard_cap |
| CB11 | Agente cede, retrocede, y la celda de retroceso tambien se ocupo | Buscar siguiente celda libre adyacente; si ninguna, esperar en sitio (sigue conservando su celda) |
| CB12 | Starvation de un agente de baja prioridad | Aging de prioridad efectiva (4.7 / F4) |
| CB13 | Livelock: dos agentes ceden a la vez, vuelven a chocar | Jitter aleatorio + cesion asimetrica por (prioridad, agent_id) (F3) |
| CB14 | Un solo agente en toda la nave (caso degenerado) | Sin contencion posible; comportamiento identico al actual + overhead minimo |
| CB15 | Grid 1xN (todo pasillo) | corridor mode; serializa pero progresa (sin freeze) |
| CB16 | Capacidad de zona mal puesta (cap=0) | Validacion al cargar config: cap >= 1; abortar arranque con error claro, no en runtime (F9) |
| CB17 | Interaccion con reservas de stock (Iniciativa #1) | Orden total de adquisicion de tipos de recurso (F14, 4.5) |
| CB18 | Forklift (speed 0.8) y Ground (1.0) compartiendo celda en instantes distintos | La exclusion es por instante de ocupacion, independiente de la velocidad; timeouts en unidades de sim, no de pasos |
| CB19 | Teletransporte a staging heredado (2.3) bajo congestion | Eliminar el teletransporte; sustituir por el bucle de 4.4 |
| CB20 | Watchdog dispara con sim casi terminada (pocos agentes vivos) | Watchdog ignora agentes en `finished`/`idle`; solo cuenta los `moving`/`waiting` |
| CB21 | Explosion de eventos de waiting | Evento agregado entrar/salir de waiting con duracion, no por tick (F12) |
| CB22 | No determinismo por dicts | Desempates por tupla ordenada; RNG sembrado (F13) |
| CB23 | Agente cuyo tour fue calculado con success:False (ruta parcial) | Con congestion, calculate_route ya no aborta por None; entrega tramos validos y el resto se resuelve por espera/repath en vivo |

---

## 6. PLAN DE IMPLEMENTACION POR FASES (incremental y verificable)

Cada fase = un commit aislado, detras del flag `congestion.mode`. Orden pensado para que el
riesgo crezca despacio y siempre haya un punto de retorno verde.

### Fase 0 - Refactor de bajo riesgo (preparacion, SIN cambio de comportamiento)
- Extraer el lazo de movimiento celda-a-celda de `GroundOperator.agent_process` y
  `Forklift.agent_process` a un metodo compartido en `BaseOperator`
  (p.ej. `_recorrer_tramo(segment_path, contexto)`), para no duplicar la logica de
  congestion luego (2.5).
- Anadir el bloque `congestion` a `config.json` con `enabled:false` y leerlo (sin usarlo).
- **Prueba:** corrida headless antes/despues; `diff` del `.jsonl` debe ser VACIO
  (byte-identico). Gate de no-regresion.

### Fase 1 - Instrumentacion (medir, no cambiar)
- `mode: "instrument"`. Sin alterar movimiento, registrar cada vez que dos agentes ocupan
  la misma celda en el mismo instante (co-ocupacion) y construir un mapa/heatmap de
  hotspots de colision. Nuevo evento `congestion_observada` o contador agregado.
- **Prueba:** correr el escenario tipico; obtener baseline de N co-ocupaciones y sus celdas.
  Esto da el "antes" para comparar y confirma cuantitativamente que hoy se atraviesan.

### Fase 2 - Arranque escalonado + dispersion (mata F1, sin exclusion aun)
- Implementar stagger temporal y andenes de salida (4.6). Aun NO hay exclusion de celda.
- **Prueba (PRUEBA DE ESTRES DE ARRANQUE - reproduce el fallo original):**
  escenario con el MAXIMO de agentes que la flota permita, todos arrancando del mismo depot.
  Metrica: co-ocupaciones en `t in [0, 5]` debe caer drasticamente vs Fase 1. Confirmar que
  ningun agente arranca en la misma celda que otro. Este test se conserva como regresion
  permanente para todas las fases siguientes.

### Fase 3 - Exclusion por celda con espera simple (corazon)
- `mode: "cell"`. Implementar `CongestionManager` (4.1/4.2) y el paso atomico (4.3) con
  espera por timeout `W` (4.4), conservando celda actual (anti-F10). Repathing y cesion
  TODAVIA no; solo "espera y reintenta" + watchdog basico como red.
- Eliminar teletransporte a staging (CB19) usando el bucle nuevo.
- **Prueba:** repetir prueba de estres de arranque (Fase 2) ahora CON exclusion. Criterio
  duro: **0 freezes** (el reloj de sim avanza hasta el final), I1 se cumple (0 co-ocupaciones
  reales), y la sim termina. Si aparece deadlock, el watchdog debe resolverlo y dejar traza.
  Comparar throughput vs baseline (debe bajar algo, no a 0).

### Fase 4 - Repathing dinamico (rodea atascos)
- `mode` sigue "cell" pero activa repathing (4.8) con `MAX_REPATH` y `repath_cost_factor`.
- **Prueba:** escenario con un cruce muy disputado; verificar que algunos agentes eligen
  rutas alternas en vez de esperar, que el repathing no entra en bucle (F5), y que el
  throughput mejora respecto a Fase 3 sin violar I1/I2.

### Fase 5 - Resolucion de deadlock formal + corredores/muelles (robustez)
- Cesion por prioridad con aging + backoff con jitter (4.7), head-on en ancho 1 (F6),
  muelle de staging como Resource (F8), y `mode: "cell+corridor"` opcional.
- Calibracion de capacidades de zona (F9) con validacion de config (CB16).
- **Pruebas:**
  - Estres de deadlock: layout en cuello (embudo) con muchos agentes; criterio **0 deadlocks
    no resueltos** (todos los detectados los cierra cesion/watchdog), 0 starvation (todo
    agente avanza dentro de `wait_hard_cap`), 0 livelock (progreso monotono).
  - Determinismo: misma semilla -> `.jsonl` identico en dos corridas (I5).
  - Regresion completa: re-correr Fases 2-4.

### Resumen de fases
| Fase | Que entrega | Flag | Criterio de paso |
|------|-------------|------|------------------|
| 0 | Refactor + config leida | enabled:false | jsonl byte-identico |
| 1 | Instrumentacion/baseline | instrument | mapa de co-ocupaciones |
| 2 | Stagger + dispersion | (spawn) | caida de co-ocupacion en t=[0,5] |
| 3 | Exclusion + espera | cell | 0 freezes, I1, sim termina |
| 4 | Repathing | cell | mejora throughput, sin F5 |
| 5 | Deadlock + corredores | cell+corridor | 0 deadlocks no resueltos, determinismo |

---

## 7. CRITERIOS DE EXITO Y METRICAS

**Criterios duros (binarios, bloqueantes):**
- **0 freezes:** en todos los escenarios de test el reloj de SimPy avanza hasta la condicion
  de fin; ninguna corrida queda colgada (I2).
- **0 deadlocks no resueltos:** todo deadlock detectado se cierra por cesion o watchdog y
  queda registrado; ninguno persiste (I2/F2/F11).
- **Exclusion (I1):** 0 co-ocupaciones reales de celda en `mode: cell` (medido por la
  instrumentacion de Fase 1, ahora en verde).
- **Sin abort por bloqueo (I3):** ningun tour termina con error por "no path"/"sin celda";
  los logs solo muestran esperas/repaths, no abortos por contencion.
- **Terminacion (I4):** `simulacion_ha_terminado()` se alcanza; el `.jsonl` drena completo.
- **No regresion (Fase 0):** con `enabled:false`, `.jsonl` byte-identico al actual.
- **Determinismo (I5):** misma semilla y config -> `.jsonl` identico en repeticiones.

**Metricas de calidad (continuas, para calibrar):**
- Throughput (WOs/tiempo): debe degradarse de forma plausible al subir agentes/densidad,
  NUNCA a 0. Reportar curva throughput vs N agentes.
- Tiempo medio y P95 de espera por agente: distribuciones plausibles (sin colas que crezcan
  sin cota; P95 < `wait_hard_cap`).
- Numero de cesiones, repaths y activaciones de watchdog por corrida: deben ser bajos y
  estables; un pico indica mala calibracion.
- Utilizacion de celdas/hotspots: el heatmap de congestion debe coincidir con los cuellos
  intuitivos del layout (cruces, accesos a staging).
- Overhead de runtime y tamano del `.jsonl`: el coste de la capa de congestion debe ser
  acotado (eventos de waiting agregados, F12).

**Evidencia empirica a entregar al Director por fase (Ley #2):** log de exito + captura del
heatmap/curva + el comando exacto para reproducir, por cada fase.

---

## 8. RIESGOS Y ROLLBACK

| Riesgo | Prob/Impacto | Mitigacion | Rollback |
|--------|--------------|-----------|----------|
| Re-introducir el freeze del intento previo | Media/Alto | Regla de oro (4.4) + stagger (4.6) antes de exclusion + watchdog (4.7); prueba de estres de arranque como gate | `congestion.enabled=false` -> comportamiento actual exacto, sin revertir codigo |
| Deadlock cruzado stock(Init#1) x espacio | Media/Alto | Orden total de adquisicion por tipo de recurso (4.5/F14) | Apagar mode a "instrument" (sin exclusion); el stock sigue funcionando |
| Caida de throughput a niveles inutiles | Media/Medio | Repathing (Fase 4) + calibracion (Fase 5) + metricas de curva | Volver a Fase 3 o a flag off |
| Explosion de eventos/log gigante (F12) | Media/Medio | Eventos de waiting agregados; prints tras flag debug | Bajar verbosidad por config |
| No determinismo (F13) | Baja/Medio | Desempates por (prioridad, agent_id); RNG sembrado | Test de determinismo en CI manual |
| Coste de instanciar recursos por celda en grids grandes (F9/perf) | Media/Medio | Reserva perezosa on-demand (4.2), no un Resource por celda fijo | Cambiar a estrategia de dict+eventos |
| Romper el lazo duplicado solo en un operador | Media/Alto | Fase 0 extrae helper compartido ANTES de tocar el lazo | Revert del commit de Fase 0 (aislado) |
| Calibracion de capacidad de zona congela todo (F9) | Baja/Alto | Validacion de config (CB16) + base por celda, zona opcional | Desactivar corridor mode |

**Estrategia de rollback global:** todo vive detras de `congestion.mode`. El estado seguro
por defecto es `enabled:false` (identico al actual). Cada fase es un commit aislado y
reversible. NUNCA se toca `collision_matrix` ni la cadena headless->jsonl->viewer, asi que
el peor caso es apagar el flag y quedar exactamente como hoy.

---

## 9. CHECKLIST DE ARRANQUE DE LA IMPLEMENTACION (cuando el Director de luz verde)

1. Confirmar que la red de seguridad de Iniciativa #1 esta intacta (commit `df64a0c` +
   backup `_backup_pre_iniciativa2/`).
2. Crear rama de trabajo a partir de `feature/allocation-layer-v12.1` (no tocar main).
3. Implementar Fase 0 y validar `.jsonl` byte-identico ANTES de cualquier otra cosa.
4. Avanzar fase a fase, cerrando cada una con su evidencia empirica.
5. No introducir exclusion (Fase 3) hasta que la prueba de estres de arranque (Fase 2)
   este en verde. Esa es la leccion del fracaso previo.

---

## 10. APENDICE - REFERENCIAS DE CODIGO (para implementar sin alucinar, Ley #5)

- Lazo de movimiento a reemplazar: `operators.py` 340-381 (Ground), 721-762 (Forklift).
- Init de posicion (spawn): `operators.py` 273-274 (Ground), 654-655 (Forklift).
- Arranque de procesos (stagger): `operators.py` 1051, 1070, 1102, 1123 (`crear_operarios`).
- Teletransporte a staging a eliminar: `operators.py` ~510-512 (Ground), ~901-913 (Forklift).
- Ruta precalculada / abort por None: `route_calculator.py` 110-145 (cambiar 117-129).
- A* y caminabilidad estatica: `pathfinder.py` 45-100, 145+.
- Matriz de colision estatica (NO tocar): `layout_manager.py` 80-134.
- Punto de inyeccion del CongestionManager: junto a `pathfinder`/`route_calculator` en el
  `almacen` (warehouse.py, constructor ~137) y en `crear_operarios` (params ya existen:
  `pathfinder`, `layout_manager`).

---

_Fin del plan. Cerebellum sincronizado. Esperando luz verde del Director para Fase 0._
