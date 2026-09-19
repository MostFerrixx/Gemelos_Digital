# PROPUESTA — Circulacion en zonas de descarga y modelo de layout

> Respuesta al encargo `docs/CONSULTA_DISENO_CIRCULACION_Y_LAYOUT.md`.
> Consultor externo (Fable 5.1), 2026-09-19. Solo analisis y propuesta: no se
> toco codigo. Todo lo que se afirma del motor se leyo en el repositorio
> (rama `qa/configuracion-web`) y se cita como `archivo:funcion`. Donde no
> pude verificar algo, lo digo.

---

## 1. Resumen ejecutivo (para el Director, sin jerga)

**Que pasa.** Cuando varios operarios llegan a descargar a la misma zona, los
que esperan turno se paran justo en las tres celdas por donde el que esta
descargando tiene que salir. Nadie puede moverse. Despues de diez minutos de
reintentos el simulador "se rinde" y deja que un operario pise a otro. Eso es
fisica imposible y, por el principio rector, un bug. Con la flota grande (4+4)
es escandaloso (hasta 6 operarios en una celda, y duplicar la flota casi no
acorta la jornada). **Pero no es solo un problema de flota grande:** en 4
corridas web con la flota normal (2+2) y semilla libre, 3 de 4 tuvieron
operarios pisandose en la descarga (hasta 3 en la misma celda). Con la semilla
42 del gate no pasa por casualidad; por eso se creia resuelto.

**Por que pasa.** Encontre tres causas, una encima de la otra:

1. **Un error del planificador de rutas** (nuevo, no estaba en la mesa): cuando
   un operario tiene que esperar en una celda, el simulador le reserva ademas
   la celda de la que vino, durante toda la espera. Es decir, el que espera
   ocupa DOS celdas en vez de una. Consecuencias: (a) el que espera frente a
   la descarga tapa tambien el pasillo de atras; (b) como esa doble reserva
   choca con las reservas de otros, el planificador rechaza planes que eran
   perfectamente validos, una y otra vez (en las corridas 2+2 rechazo entre el
   85% y el 95% de los planes que armo; en la 4+4, 50.643 esperas). Lo
   reproduje con un script de 25 lineas (seccion 2.2).
2. **Nadie garantiza la salida.** La zona de descarga no es un "puesto con
   turno": cada operario simplemente camina hasta ella y, si esta ocupada,
   espera en la celda mas cercana que encuentra, que es justamente la salida
   del otro. Es lo que el Director diagnostico.
3. **El "me rindo" pisa a otro.** El ultimo recurso del motor es avanzar por la
   ruta fija aunque la celda este ocupada. Eso convierte un atasco (real,
   medible) en una superposicion (imposible).

**Que propongo.** Tratar cada zona de descarga como una **estacion con turno**,
como lo hacen los simuladores profesionales y los almacenes reales:

- La estacion tiene **puestos** (hoy 1; configurable), **una entrada**, **una o
  dos salidas de un solo sentido** por donde solo se sale (la idea del
  Director) y una **fila corta** de espera que arranca en la entrada.
- El operario **pide turno antes de acercarse**. Si hay puesto libre, entra; si
  no, ocupa su lugar en la fila; si la fila esta llena, espera en el
  **pulmon** (las zonas de espera que ya existen) y se lo llama por orden de
  llegada. Nadie espera nunca en una salida.
- El turno se libera recien cuando el que descargo **ya salio fisicamente**.
  Asi el bloqueo circular no puede formarse: es una garantia de construccion,
  no una esperanza.
- Entrada, salidas y fila **se deducen solas** para cualquier mapa; el cliente
  las ve en el visor y las puede corregir desde la web, con validacion que
  dice que celda rompe la circulacion y por que.

Y antes que nada, **corregir el error del planificador** (es un cambio chico y
aislado, pero mueve el baseline: hay que actualizarlo a proposito).

**Orden.** Primero esto (H-15), despues INIT-10. Razones: (1) H-15 es un bug de
realismo en la configuracion por defecto del producto, visible en el visor;
INIT-10 es semanas de trabajo y no arregla la fisica. (2) La logica de
"estacion con turno, entrada, salida y fila" es exactamente lo que INIT-11 F3
va a necesitar para los puntos de transferencia y las estaciones de empaque,
asi que no es trabajo tirado: es un cimiento compartido. (3) Las reglas se
guardan en un bloque `circulacion` de `config.json` cuyo esquema es ya el del
modelo de INIT-10 (estaciones + aristas dirigidas, alineado con el estandar
LIF), asi que migran sin redisenar. La etapa 1 de INIT-10 (validar mapa contra
Excel) se puede hacer en paralelo: es medio dia y no toca nada de esto.

**Con el muelle activo (outbound encendido)** el problema cambia de forma pero
no de fondo. Verifique como se arman los carriles: cada zona se expande en una
mancha de 8 celdas alrededor de su ancla, las 7 manchas tapan las filas 28 y
29 enteras, y el pasillo frontal queda reducido a la fila donde desembocan los
pasillos de picking. Ademas, en 6 de las 7 zonas una de las "entradas" a un
carril cae dentro de la zona vecina, asi que el operario se teletransporta.
Eso no es un carril de staging real (un rectangulo de un ancho de grua y
varios pallets de fondo, con un anden de circulacion delante). La estacion
con turno sirve igual para este modo (un carril es un ramal ciego: se entra y
se sale por el mismo lugar, y la espera es afuera), pero para que el muelle de
WH1 sea realista hace falta un mapa con anden y carriles definidos a mano.
Hoy la jornada con muelle activo dura el doble (16.091 s) y no es por los
camiones: es porque cada tarea se convierte en un pallet que se deposita uno
por uno y el carril es el cuello.

**Que decidir.** Hay 10 preguntas para el Director en la seccion 7. Las cuatro
que mas pesan: si aceptamos mover el baseline por la correccion del
planificador; cuantos puestos simultaneos admite la zona 1 (realismo dice 2 en
un carril de varios metros; hoy es 1); con el muelle activo, si "un pallet por
tarea" se reemplaza por "un contenedor por pedido"; y si se le da a WH1 un
anden de muelle o el muelle activo queda como demostracion.

**Donde discrepo con lo conversado.** Cinco puntos, resumidos en la seccion 8:
la fila larga frente a la zona no es realista (mejor fila de 1-2 y pulmon); la
capacidad de la zona no conviene diferirla; el "sentido unico por celda" solo
no alcanza (hace falta el concepto de estacion); los pasillos de un solo
sentido (Fase B) conviene disenarlos ahora pero no implementarlos todavia; y
la causa raiz principal en numeros no era la que estaba sobre la mesa.

---

## 2. Diagnostico verificado en el codigo

### 2.1 Como llega hoy un operario a descargar (outbound apagado)

`operators.py:_execute_pick_tour` (PASO 4): agrupa las tareas por zona, ordena
las zonas por distancia Manhattan (`_ordenar_stagings_por_distancia`), pide al
A* estatico un camino hasta la celda de la zona (`pathfinder.find_path`) y lo
recorre con `_recorrer_tramo(..., goal_dwell=self._staging_dwell_estimate())`.
Con la capa anti-colision activa (canonico), `_recorrer_tramo` llama a
`_timewindow_execute_plan`, que pide a `spacetime_planner.plan_and_reserve` un
plan espacio-temporal cuyo destino es la celda de descarga con una estadia
reservada (descarga + paso de salida, BK-15 C2/C3). Si no hay plan
reservable, espera `replan_wait_s` (0,5 s) reservando su celda actual y
reintenta hasta `replan_max_retries` (1.200) veces; en el ultimo intento cae
a la ruta estatica sin garantias (`fallback=True`), que se recorre con
`_set_pos` sin mirar si la celda esta ocupada. **1.200 x 0,5 s = 600 s: los
"10 minutos simulados" del hallazgo son exactamente ese tope.**

No existe ningun recurso "zona de descarga": el turno emerge de las reservas
en la `ReservationTable`. El A* (`spacetime_planner.find_path_st`) busca la
llegada mas temprana; cuando el destino esta reservado por la estadia de otro,
la solucion optima es **esperar en la celda adyacente** (`earliest_free` salta
al fin de la estadia). Por eso los que esperan quedan pegados a la zona: no es
un accidente, es lo que el algoritmo optimiza.

Cuando el que descarga termina, planifica su siguiente tramo desde (3,29). Sus
tres vecinos (2,29), (4,29), (3,28) estan reservados por los que esperan; y el
intercambio simultaneo "yo salgo a (3,28) mientras vos entras a (3,29)" lo
rechaza `reservation_table.can_swap` (conflicto frontal). El que espera tiene
un plan que dice "entro a (3,29) en t" pero al ejecutar encuentra al otro
fisicamente ahi: `_timewindow_execute_plan` lo detecta (`exec_blocked`),
suelta el plan y replanifica. Ciclo cerrado. Es el bloqueo circular del
hallazgo, y la explicacion del Director es correcta.

### 2.2 Causa nueva: sobre-reserva del origen durante una espera (bug)

`spacetime_planner._reconstruct` devuelve el plan como `[(celda, t)]` donde,
por construccion de `_relax`, `t` es el instante de **salida** de cada celda
(en un movimiento retrasado estilo SIPP, `pt = t_free`). Luego
`_plan_reserve_core` reserva, para cada par consecutivo, `prev_cell` en
`[prev_t, t]` y `cell` en `[prev_t, t]` (BK-15 C2: "el origen sigue ocupado
hasta llegar al vecino"). Pero `t` es la salida de `cell`, no la llegada: si
el agente **espera** en `cell`, el origen queda reservado durante toda esa
espera, aunque el A* solo lo valido hasta `t_llegada + dur` (`here_ok`).

Reproduccion (script que corri en el repositorio, sin tocar nada):

```python
import sys; sys.path.insert(0, 'src')
from subsystems.simulation.reservation_table import ReservationTable
from subsystems.simulation.spacetime_planner import SpaceTimePlanner
class Pasillo:  # 10x3, vecinos cardinales (mismo stub que tests/unit/test_bk15_anticolision.py)
    def is_walkable(self, x, y): return 0 <= x < 10 and 0 <= y < 3
    def heuristic(self, a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
    def get_neighbors(self, c):
        return [((c[0]+dx, c[1]+dy), 1) for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))
                if self.is_walkable(c[0]+dx, c[1]+dy)]
tabla = ReservationTable(0.05)
pl = SpaceTimePlanner(Pasillo(), tabla, 0.1, 0.1, 20000, False)
pl.plan_and_reserve((0,0), (3,0), 0.0, 'Z', 1.0, goal_dwell=60.0)   # Z descarga 60 s en (3,0)
tabla.reserve((1,0), 5.0, 5.1, 'X')                                # X pasa por (1,0) en t=5
plan = pl.plan_and_reserve((1,0), (3,0), 0.5, 'Y', 1.0, goal_dwell=5.0)
print(plan, pl.shadow_metrics['plans_rejected_unreservable'])
```

Resultado: `None 1`. Y esta fisicamente en (2,0) desde t=0,6 hasta t=60,45
esperando a Z; su plan es valido; pero el motor intenta reservar (1,0) —la
celda de la que salio en t=0,5— hasta t=60,45, choca con X en t=5 y **descarta
el plan entero**. Sin la reserva de X, el plan se acepta y la tabla muestra la
reserva de Y en (1,0) = `[0.5, 60.45]`: sesenta segundos en una celda que dejo
a los 0,1 s.

Evidencia en las corridas reales (leida de `timewindow_shadow_report_*.json`):

| Corrida (2+2, semilla libre) | segmentos planificados | planes rechazados por reserva | `reserve_overlaps` | `replan_waits` | `exec_fallbacks` | co-ocupaciones (fuera del arranque) |
|---|---|---|---|---|---|---|
| `simulation_20260919_012605` | 5.602 | 5.154 (92%) | 5.154 | 5.215 | 1 | 1 |
| `simulation_20260919_012803` | 13.747 | 13.108 (95%) | 13.108 | 13.356 | 8 | 6 |
| `simulation_20260919_020157` | 5.027 | 4.607 (92%) | 4.607 | 4.623 | 2 | 3 |
| `simulation_20260919_023549` | 454 | 7 | 8 | 14 | 0 | 0 |

`plans_rejected_unreservable == reserve_overlaps` en las cuatro: cada plan
rechazado tuvo exactamente un solape, la firma de este bug (un unico
intervalo, el del origen, que el A* no valido). En la 4+4 del hallazgo, las
50.643 esperas de replanificacion son la misma mecanica multiplicada.

Efectos: (a) cada operario que espera bloquea DOS celdas (la suya y la de
atras): frente a la zona 1 eso significa tapar (3,27), (2,28) o (4,28), el
pasillo transversal; (b) planes validos se rechazan en cadena hasta agotar los
1.200 reintentos; (c) el "me rindo" final produce la co-ocupacion.
**Este bug amplifica el atasco pero no lo crea:** sin el, el bloqueo circular
de 2.1 sigue existiendo (los tres vecinos ocupados y el `can_swap`). Hay que
corregir las dos cosas.

Correccion (F0 del plan): que el plan lleve llegada y salida por celda
(`(celda, t_llegada, t_salida)`) y que el origen se reserve solo
`[t_salida_origen, t_llegada_destino]`. El ejecutor
(`_timewindow_execute_plan`) no cambia de semantica (sigue avanzando con los
tiempos de salida). El primer paso anclado a `t0` (`path[0]`) pierde hoy el
instante real de salida del origen; con la terna se conserva. **Mueve el
baseline** del gate: hay que actualizarlo con `--update-baseline --yes` en el
mismo commit, tras medir.

### 2.3 La regla de "nunca congelar" hoy termina en fisica imposible

`_recorrer_tramo` (rama timewindow): en el intento `ultimo`, `fallback=True`
reserva la ruta estatica best-effort y la recorre igual. Por el principio
rector, un KPI logrado pisando a otro es un artefacto. Propuesta: el ultimo
recurso debe ser **retroceder** a la celda libre mas cercana (contado como
`retrocesos`) o seguir esperando con aviso `[WARN]`, nunca entrar a una celda
ocupada. Con la estacion con turno (seccion 3) ese ultimo recurso deberia
medir 0 en todos los escenarios de prueba; si no mide 0, es un bug nuevo, no
un caso aceptable.

### 2.4 Otros supuestos fijos que encontre (afectan la deduccion en mapas arbitrarios)

- `operators.py:agent_process`: `depot_location = staging_locs.get(1, (3, 29))`
  y `_ordenar_stagings_por_distancia`: `staging_locs.get(staging_id, (3, 29))`.
  Coordenada de WH1 hardcodeada como fallback.
- `operators.py:_execute_pick_tour` (F2.d fix) y `_outbound_discharge_lanes`:
  `_exit_cell = (x, y - 1)` / `_entry = (fc[0], fc[1] - 1)`: asumen que la
  zona se aborda **desde arriba** (y-1). En un mapa con las zonas en el borde
  superior o lateral, la "entrada" cae fuera del mapa o en un rack.
- `outbound.py:StagingZone`: carriles = columnas (`x`), llenado de `y` mayor a
  menor: misma orientacion fija.
- El A* estatico (`pathfinder.get_neighbors`) usa 8 direcciones; el
  planificador espacio-temporal del canonico usa 4 (`allow_diagonal: false`).
  La ruta estatica de fallback puede cortar esquinas que el planificador nunca
  cortaria, y las distancias de asignacion se calculan con diagonales que no se
  ejecutan. Conviene unificar (una sola fuente de vecindad).
- `idle_zones.GestorZonasEspera.motivo_invalida` ya conoce el concepto
  "acceso a una zona de descarga" (Manhattan <= 1) y
  `_sin_cortar_el_mapa` ya hace una verificacion de conectividad. Son la base
  a generalizar, no a duplicar.

### 2.5 Con el muelle activo (outbound encendido) el modelo tiene sus propios problemas

Corrida `simulation_20260919_023347` (canonico + `outbound.enabled=true`):
duracion 16.091 s (x2,1), 50% del tiempo de agente en `unloading`,
`lane_full_wait_events` 343 con 29.483 s acumulados esperando **dentro del
carril** a que un camion libere un slot, camiones cada ~96 s con 3,9 pallets
de 8. Leido en `operators._outbound_discharge_lanes` y `outbound.StagingZone`:

1. **Un pallet por tarea (WO).** 618 WOs -> 618 pallets, cada uno depositado
   uno por uno en el fondo del carril, con espera dentro del carril si la
   columna esta llena. En un almacen real el operario deja **su carga**
   (un pallet, o un carro de totes) en una sola maniobra, y la unidad que
   viaja es el contenedor del pedido, no la linea de pick. Este es el motivo
   del x2,1, no el camion. Es una decision de modelado (seccion 7, D3) y
   coincide con el pilar P3 (contenedores) de `docs/PLAN_INIT11_TASK_PATH.md`.
2. **Un operario por carril** es razonable (un carril de 1 celda de ancho no
   admite dos gruas), pero el carril entero es "propiedad" del que entra: con
   2 columnas por zona la capacidad efectiva ya es 2 puestos. Es decir, el
   modelo con outbound encendido YA tiene puestos multiples; el de outbound
   apagado tiene 1. Unificar los dos bajo "estacion con N puestos" (seccion 3)
   elimina la duplicacion.
3. **Teletransporte.** El movimiento intra-carril es `_jump_to` (52 saltos de
   2-3 celdas en la corrida): no pasa por el planificador ni reserva las celdas
   intermedias. Y la espera "fuera" del carril (`while lane is None: yield
   timeout(dt)`) **no reserva la celda actual** (`_tw_reserve_dwell` no se
   llama en ese lazo): el que espera es invisible para los demas planes. Son
   dos fugas de la garantia de BK-15 que el gate no ve (canonico = outbound
   apagado).
4. **Spawn dentro del carril** (BK-29): las celdas del carril se bloquean
   despues de que `_spawn_lane` eligio las posiciones iniciales.
5. **La geometria de los carriles no es realista, y en WH1 es inviable.**
   Reproduje `outbound.build_zone_cells` sobre WH1 con `zone_capacity_default
   = 8`: cada ancla se expande en **anillos de Chebyshev** a una mancha de 8
   celdas (zona 1 = (3,29),(2,29),(4,29),(2,28),(3,28),(4,28),(1,29),(5,29))
   que `StagingZone` agrupa en **5 columnas** (x=1..5: tres de 2 celdas y dos
   de 1), no en "2 carriles" como dice el docstring de
   `_outbound_discharge_lanes`. Las 7 zonas juntas bloquean las filas 28 y 29
   de x=1 a x=29: el pasillo frontal de 3 filas queda reducido a **la fila
   27, que es la fila de las bocas de pasillo**. Y en 6 de las 7 zonas hay una
   columna cuya "entrada" (`(x, y-1)`) es una celda de la zona vecina, no
   caminable tras F2.d: `_outbound_nav_to` no encuentra camino y **teletransporta
   siempre** (zona 1 columna 5: entrada (5,28), que es slot de la zona 2; zona
   2 columna 9 -> (9,28) de la zona 3; y asi hasta la 6). Ahi estan buena
   parte de los 52 saltos. Ademas, en la mancha las celdas laterales (2,29) y
   (4,29) —las "salidas" de la idea del Director— son slots de pallet: con
   outbound encendido la idea original no tiene donde aplicarse tal cual.
   En un almacen real un carril de staging es un **rectangulo perpendicular
   al muelle** (1 grua de ancho, varios pallets de fondo), separado de los
   pasillos de almacenamiento por un **anden de circulacion** de 9 a 18 m
   (las guias de muelles piden 30-60 pies del muelle a la primera columna).
   WH1 tiene 3 m entre el muelle y los racks: no hay anden; cualquier staging
   de mas de una celda de fondo se come la circulacion. Es un limite del
   **layout**, no del motor.
6. **Camiones con 7 de 8** en 3 corridas: no lo investigue a fondo. Hipotesis
   verificable: `_outbound_discharge_lanes` hace `slot.assign(...)` al llegar y
   el camion solo carga pallets `staged` (los ya depositados), asi que mientras
   un operario esta dentro del carril (casi siempre, con 343 esperas dentro)
   un slot esta tomado pero no cargable. Con `truck_interval` 600 s la corrida
   dura 63.016 s: el cuello es el espacio del carril, coherente con el punto 1.
   Nota: al cerrar este documento habia en el working tree un cambio ajeno a
   esta consulta, sin commitear (QA H-26, `warehouse.py:simulacion_ha_terminado`
   + `tests/unit/test_qa_h26_fin_con_camiones.py`): la corrida ya no termina
   hasta que el ultimo camion carga los pallets en espera. Alarga la duracion
   medida con outbound encendido; las cifras de 6.6 para ese modo deben
   re-tomarse con H-26 aplicado.

Con la estacion de la seccion 3, los carriles pasan a ser puestos de la
estacion, la entrada/salida/fila se deducen igual, el movimiento intra-carril
lo planifica el planificador (celdas privadas: caminables solo para quien tiene
el turno de ese puesto) y la espera fuera se hace en la fila/pulmon con
reserva. Eso cierra 2, 3 y 4. El punto 1 es decision del Director (D3). El
punto 5 requiere dos cosas: definir los carriles como rectangulos explicitos
(la BD ya soporta varias celdas por `staging_id`:
`data_manager.outbound_staging_zone_cells`; la expansion automatica en anillos
debe reemplazarse por "rectangulo de 1 columna x k de fondo, perpendicular al
borde") y, para simular el muelle con realismo en WH1, un mapa con anden
(D10). Mientras no lo haya, el motor debe avisar: `[WARN] outbound: las zonas
de staging dejan una sola fila de circulacion (y=27) frente a los pasillos; la
entrada de la columna x=5 de la zona 1 cae dentro de la zona 2`.

---

## 3. Solucion recomendada para H-15: estacion de descarga con turno explicito

### 3.1 Que hacen los almacenes reales y los simuladores profesionales

- **Almacenes reales.** Las guias de diseno de muelles y de trafico interior
  coinciden en tres cosas: circulacion **en un solo sentido y circular** donde
  se pueda, carriles de staging **marcados** por puerta/ruta, y **zonas de
  espera (buffer) separadas** para que las gruas hagan cola sin tapar los
  pasillos activos ("dedicated buffer zones ... allowing forklifts to queue
  without blocking main traffic", guia de trafico 2026 de A Lot of Striping).
  Nadie espera nose-to-tail en la boca de la puerta. Fuentes al final.
- **FlexSim (redes AGV).** Los vehiculos avanzan asignandose por adelantado
  "control points" y "control areas" con capacidad; si no pueden asignarse
  **todo** lo que necesitan para el proximo tramo, no se asignan nada (regla
  todo-o-nada anti-deadlock); y la receta habitual ante bloqueos es agregar
  puntos de control (para soltar antes) y **carriles de un solo sentido**.
  Es decir: recurso explicito con turno + salida garantizada + sentido unico.
- **AnyLogic (Material Handling Library).** Los transportadores circulan por
  una red de `Path` (bidireccional u opcional de un solo sentido); un bloque
  `Queue` coloca a los agentes a lo largo de un path con la cabeza en el
  extremo; el "seize" del recurso (estacion) se hace antes de moverse
  (`SeizeTransporter` / `MoveByTransporter`). Mismo patron: la cola es un
  lugar fisico con orden, y el destino se toma como recurso.
- **Literatura de MAPF (lo que hace nuestro planificador).** El
  `SpaceTimePlanner` es una planificacion priorizada con intervalos seguros
  (SIPP, Phillips & Likhachev 2011). Se sabe que la planificacion priorizada
  **no es completa en general** (puede quedar sin solucion aunque exista), pero
  **si lo es en "infraestructuras bien formadas"**: paraf. de Cap, Novak,
  Kleiner y Selecky (IEEE T-ASE 2015), una infraestructura es bien formada
  cuando cada punto donde un agente puede detenerse (inicio, destino, espera)
  se puede alcanzar desde cualquier otro sin atravesar los demas puntos de
  detencion; en ese caso un agente parado en su punto nunca bloquea a los
  otros. El resultado equivalente para el caso "lifelong" (tareas que llegan
  todo el dia, como aca) es Ma, Li, Kumar y Koenig (AAMAS 2017): los
  algoritmos de token passing "solve all well-formed MAPD instances". No pude
  extraer el texto exacto de la definicion del PDF (sin lector de PDF en esta
  maquina); la parafrasis es fiel al resultado que se cita habitualmente.

Traducido a nuestro problema: **el deadlock aparece porque las celdas donde los
operarios se detienen (la zona de descarga y las celdas donde esperan turno)
estan en el camino de los demas**. BK-15 ya aplico esta idea a los ociosos
(zonas de espera fuera de la circulacion, `idle_zones.py`). Falta aplicarla a
la descarga: puestos, entrada, salidas y fila como puntos de detencion
**fuera del paso de los otros**, y un turno explicito para que nadie se acerque
a un puesto ocupado.

### 3.2 El mecanismo

Una **estacion** (clase nueva `Estacion`, modulo
`src/subsystems/simulation/stations.py`) tiene:

| Elemento | Que es | Regla |
|---|---|---|
| `puestos` | celdas donde se descarga (hoy `[(3,29)]`; con outbound activo, las celdas del carril agrupadas por columna) | 1 operario por puesto; estadia reservada como hoy (`goal_dwell`) |
| `entrada` | unica celda por la que se entra a un puesto | por ella se entra y solo se entra; es la cabeza de la fila |
| `salidas` | 1..n celdas por las que se sale | `no_detenerse` + solo se entra a ellas **desde un puesto**; nadie las usa para ir a otro lado |
| `cola` | lista ordenada de celdas de espera, `cola[0] == entrada` | reserva abierta mientras se espera (mismo mecanismo que `idle_zones`); nunca una salida, nunca la celda siguiente a una salida, nunca boca de pasillo |
| `pulmon` | las `zonas_espera` (o automaticas) | cuando la fila esta llena; se los llama por turno |
| `turnos` | cola FIFO de pedidos `(t_pedido, agent_id)` con capacidad = `len(puestos)` | determinista; sin inanicion |

Ciclo del operario (`operators._execute_pick_tour`, PASO 4, reemplaza el bloque
"Navegar al staging + descarga granular"):

1. **Pedir turno** al terminar el ultimo pick (antes de acercarse). La
   estacion responde con uno de tres estados: `puesto` (hay puesto libre y
   nadie antes en la fila), `cola k` (posicion k en la fila fisica) o
   `pulmon` (fila llena).
2. **Ir a donde toca** con el planificador normal, con `goal_dwell` abierto
   (`ESPERA_ABIERTA_S`) si es fila o pulmon: los demas lo rodean.
3. **Avanzar en la fila** cuando la estacion avisa (evento SimPy por agente,
   no polling): de `cola[k]` a `cola[k-1]`, del pulmon a la ultima celda libre
   de la fila. Cada avance es un tramo planificado de 1-2 celdas.
4. **Entrar al puesto** solo cuando la estacion le concede el turno: tramo
   `entrada -> puesto` (1 celda), estadia = descarga de todas sus tareas +
   paso de salida (como hoy).
5. **Salir por una salida**: al terminar, planifica `puesto -> salida ->
   siguiente celda` ANTES de liberar el puesto. Como las salidas son
   `no_detenerse` y nadie las toma como destino, el unico conflicto posible es
   de transito (cortos, los resuelve el planificador con esperas de decimas de
   segundo). Si la salida elegida esta en transito ajeno, prueba la otra.
6. **Liberar el turno** cuando `current_position` ya no es el puesto (ni la
   salida, si se quiere margen: parametro `liberar_al_salir_de: "puesto" |
   "salida"`). Recien entonces la estacion concede el turno al primero de la
   fila. **Por construccion no hay intercambio frontal** entre el que sale y
   el que entra: uno usa la salida, el otro la entrada, y no se solapan en el
   tiempo.
7. Si el operario tiene tareas para varias zonas (`Tour Mixto`), repite 1-6
   por zona; el orden de zonas usa distancia por camino (seccion 4.3), no
   Manhattan.

Garantias que se pueden probar con tests:

- **Salida siempre libre**: ninguna reserva abierta (fila, pulmon,
  estacionamiento, spawn) cae en una salida ni en la primera celda despues de
  una salida. (`GestorZonasEspera.motivo_invalida` se extiende con esa regla.)
- **Nadie se acerca a un puesto ocupado**: el tramo `entrada -> puesto` solo se
  planifica con turno concedido.
- **Sin espera adyacente sin turno**: un operario sin turno nunca tiene por
  destino una celda vecina de un puesto salvo `entrada` (y solo como
  `cola[0]`).
- **Infraestructura bien formada**: validador (seccion 4.4) que comprueba que
  puestos, entrada, cola, salidas, zonas de espera, estacionamientos y picks no
  cortan la conectividad entre si.

### 3.3 Integracion con el planificador espacio-temporal

- Los cambios en `spacetime_planner.py` son pocos: (a) la correccion 2.2;
  (b) un filtro de vecinos por reglas (`rules.permitido(desde, hasta)`,
  seccion 4.1) y (c) la regla `no_detenerse`: en `find_path_st` no se genera el
  sucesor "salida retrasada" (`t_free`) desde una celda `no_detenerse`, y
  `reserve_dwell` rechaza con `[WARN]` cualquier estadia > 1 paso en ellas.
- El resto es **fuera** del planificador: el turno es una estructura SimPy
  (cola FIFO + `env.event()` por agente), y el planificador ve el puesto
  ocupado solo por la estadia reservada del que descarga, como hoy.
- La `ReservationTable` no cambia. `can_swap` sigue vigente para el resto del
  mapa.
- Fallback (2.3): con estacion, el A* siempre tiene destino libre (puesto
  concedido, celda de fila libre por construccion o pulmon libre por
  construccion). Si igual no encuentra plan (transito), la espera con
  replanificacion sigue como hoy; el ultimo recurso pasa a ser "retroceder a
  la celda libre mas cercana" y nunca "avanzar por encima".
- **Outbound encendido — el mismo objeto, otro caso de la deduccion.** Un
  carril es un **ramal ciego**: se entra y se sale por la misma celda (la
  grua entra de frente y sale marcha atras). En el modelo es exactamente el
  caso degenerado "rincon" de 4.5: `entrada == salida`, `salidas: []`,
  `liberar_al_salir_de: "entrada"`, y la fila no puede empezar en la entrada.
  Concretamente: cada columna del carril es un **puesto** con profundidad
  (sus slots); la `entrada` del puesto es la celda transitable contigua al
  slot delantero que **no pertenece a ninguna zona** (deducida por BFS, no
  `(x, y-1)`; si no existe, el puesto se declara inaccesible con `[ERROR]` y
  no se usa: hoy eso pasaria con la columna x=5 de la zona 1); las celdas del
  carril son **privadas**, caminables solo para el agente con turno en ese
  puesto (`rules.permitido` recibe `agent_id`), asi el planificador planifica
  el avance slot a slot con reservas y desaparece `_jump_to`; la espera por
  columna llena (camion) se hace **fuera**, en fila/pulmon con reserva, y el
  turno se pide antes de acercarse. En WH1 con la geometria actual la fila
  queda vacia (la unica celda a distancia 2 de la entrada es un rack) y todos
  esperan en el pulmon; como el pulmon valido queda lejos (fila 27 esta casi
  toda excluida por ser boca de pasillo o acceso a zona), el motor debe avisar
  `[WARN] el pulmon de DESCARGA-1 esta a N celdas: la espera fisica sera
  larga` en vez de degradar en silencio. Es la forma honesta de mostrar que el
  layout no tiene anden (2.5, punto 5).
- **Coherencia entre modos**: con outbound apagado la zona es un puesto de una
  celda con entrada y salidas laterales (la idea del Director); con outbound
  encendido es un conjunto de puestos-ramal con entrada unica cada uno. La
  clase `Estacion`, el turno, la fila, el pulmon, las validaciones y la capa
  del visor son los mismos; solo cambia lo que devuelve la deduccion 4.5. No
  hay dos implementaciones de "esperar para descargar".

### 3.4 Alternativas consideradas y por que no

| Alternativa | Por que se descarta |
|---|---|
| **Solo la idea original (salidas de un sentido + esperar en la entrada), sin turno** | Con 2 o mas esperando, el segundo se para donde el A* lo deje: en la salida o en el pasillo. Sin turno, el que espera sigue teniendo como destino el puesto ocupado y el planificador sigue optimizando "pegarse". Y no corrige la sobre-reserva (2.2). Es necesaria pero no suficiente. |
| **Fila larga fisica frente a la zona (complemento del asistente)** | En WH1 la fila solo puede crecer por (3,28) -> (3,27) -> pasillo transversal, o lateralmente por la fila 28, tapando bocas de pasillo y el paso hacia las otras 6 zonas. En un almacen real la cola frente a una puerta es de 1-2 gruas; el resto espera en un pulmon. Recomiendo `cola_max` por defecto 1 (solo la entrada) y pulmon. |
| **Subir `replan_max_retries` / bajar `replan_wait_s`** | Cambia cuando se rinde, no si se rinde. Con el bug 2.2, mas reintentos = mas tiempo perdido. |
| **Prioridad al que sale (cesion): el que espera retrocede una celda cuando el de adentro quiere salir** | Es la solucion "reactiva" (FlexSim la evita con la asignacion todo-o-nada). Funciona a veces, pero con 3 esperando alrededor no hay a donde retroceder sin planificacion global. La conservo solo como ultimo recurso (retroceso), no como mecanismo principal. |
| **Zona de descarga con capacidad infinita ("todos entran")** | Es lo que hacia el modelo pre-MEJ-4: mejora los KPIs con fisica imposible. Contrario al principio rector. |
| **Reservas de estadia mas largas / margen (`clearance`) mayor** | No ataca ninguna de las tres causas; alarga esperas. |
| **Recurso SimPy `Resource` puro sin fila fisica** (el que espera se queda donde termino su ultimo pick) | Un operario quieto en un punto de pick bloquea ese pasillo (BK-15 lo demostro). La espera tiene que ser en un lugar bien formado. |

---

## 4. Reglas de circulacion generales y su esquema de datos

### 4.1 Semantica minima (sirve para la Fase B sin redisenar)

Dos reglas por celda y una por estacion:

1. **`sentido`** (N | S | E | O): en una celda con sentido `d` se prohiben los
   movimientos en la direccion **opuesta** a `d` (entrar o salir moviendose en
   `-d`). Los movimientos perpendiculares quedan permitidos (para girar hacia
   una boca de pasillo). Con esto un pasillo de un solo sentido es una franja
   de celdas con el mismo `sentido`. Un sentido "solo se sale" no se expresa
   asi; es la regla 3.
2. **`no_detenerse`** (bool): ninguna reserva abierta, ninguna espera
   planificada mayor a un paso, ninguna estadia. El A* estatico no cambia
   (no sabe de tiempo); el SIPP no genera esperas ahi; el gestor de zonas de
   espera y de estacionamientos las rechazan como candidatas.
3. **Salida de estacion** (`salidas` de la estacion): `no_detenerse` + solo se
   puede **entrar** a la celda desde un puesto de esa estacion. Es una regla de
   arista, no de celda, y vive en la estacion, no en `reglas_celda`.

Implementacion: un objeto `ReglasCirculacion` (`src/core/circulation.py`,
puro, sin SimPy) con `permitido(desde, hasta, agent_id=None) -> bool`,
`puede_detenerse(celda) -> bool`, `vecinos(celda, agent_id)` y
`motivo_prohibido(desde, hasta) -> str` (para los mensajes). Lo consumen:

- `pathfinder.get_neighbors` (A* estatico): filtra por `permitido`. Con
  diagonales, un movimiento diagonal se permite solo si sus dos componentes
  cardinales lo estarian (evita "colarse" en diagonal por una salida).
- `spacetime_planner._neighbors`: el mismo filtro (y `no_detenerse` en la
  rama de salida retrasada). Como el planificador reusa
  `pathfinder.get_neighbors`, basta que el pathfinder reciba las reglas: un
  solo lugar.
- `reservation_table`: **no cambia**. Las reglas reducen aristas; la tabla
  sigue garantizando disjuncion por celda y `can_swap` por arista.
- `idle_zones`, `parking`, `stations`: usan `puede_detenerse` en sus
  validaciones.

Con `circulacion` ausente, todo es permitido y detenible: **byte-identico**
salvo por la correccion 2.2 (que es intencional).

### 4.2 Esquema de datos concreto (bloque `circulacion` en `config.json`)

```json
"circulacion": {
  "version": 1,
  "estaciones": {
    "DESCARGA-1": {
      "tipo": "descarga",
      "zona": 1,
      "puestos": "auto",
      "entrada": "auto",
      "salidas": "auto",
      "cola": "auto",
      "cola_max": 1,
      "liberar_al_salir_de": "puesto"
    },
    "DESCARGA-2": {"tipo": "descarga", "zona": 2,
                   "entrada": [7, 28], "salidas": [[6, 29], [8, 29]],
                   "cola": [[7, 28]], "cola_max": 1}
  },
  "reglas_celda": [
    {"desde": [2, 29], "hasta": [2, 29], "no_detenerse": true},
    {"desde": [1, 3],  "hasta": [2, 26], "sentido": "S"}
  ],
  "validacion": {"conectividad_fuerte": "error"}
}
```

Decisiones de diseno del esquema:

- **Coordenadas de celda hoy, ids de nodo manana.** Cada `[x, y]` es un nodo
  del grafo de movimiento; en INIT-10 la misma estructura se serializa con
  `nodeId` (LIF) sin cambiar de forma. Un rectangulo `desde/hasta` es la forma
  compacta que ya usan `zonas_espera` (`x, y, ancho, alto`); uso `desde/hasta`
  para no ambiguar con `sentido`, pero se puede unificar con el formato de
  `zonas_espera` si el Director prefiere (D7).
- **`"auto"`** = deducido al cargar (seccion 4.5). El motor imprime lo deducido
  (`[INFO][CIRCULACION] DESCARGA-1: puestos (3,29); entrada (3,28); salidas
  (2,29) (4,29); cola (3,28)`), lo escribe en la metadata del `.jsonl` (para el
  visor y el A/B) y la web lo muestra con una capa en el mapa. Solo lo que el
  cliente cambia a mano se guarda explicito. Las claves ausentes valen
  `"auto"`; una estacion ausente para una zona que existe en `staging_areas`
  se crea entera en `auto`.
- **`puestos: "auto"`** = la celda ancla de `staging_areas` (outbound apagado)
  o las columnas del carril (`build_zone_cells`, outbound encendido). Para
  admitir 2 puestos con outbound apagado (D2) se listan las celdas:
  `"puestos": [[3, 29], [4, 29]]` (y entonces (4,29) deja de ser salida; la
  deduccion recalcula).
- **Los puestos siguen viniendo del Excel/BD** (`staging_areas`), como hoy: el
  bloque `circulacion` describe **como se circula alrededor** de lo que el
  layout ya define. No duplica coordenadas de zonas; las referencia por
  `zona`. El validador avisa si `zona` no existe en la BD.
- **Registro en `src/core/config_schema.py`**: `CirculacionConfig`,
  `EstacionCirculacionConfig`, `ReglaCeldaConfig` con `extra="allow"` y
  deteccion de claves desconocidas, como el resto (MEJ-3). La web valida con
  el mismo gestor que usa el motor (patron `_validar_zonas_espera` en
  `web_prototype/config_manager.py`).
- **Round-trip JS**: enteros donde JS los produce (coordenadas, `cola_max`);
  las claves `auto` no se emiten. Misma regla de INIT-8.

**Por que `config.json` y no el TMX, el Excel o esperar a INIT-10:**

| Lugar | A favor | En contra | Veredicto |
|---|---|---|---|
| `config.json` (bloque `circulacion`) | Unica fuente de verdad editable desde la web (Ley #3); ya hay esquema, validacion, metadata en el `.jsonl`, round-trip probado; `zonas_espera` y `estacionamientos` viven ahi | Son hechos del layout, no de la operacion: cuando exista el modelo propio deberan mudarse | **Recomendado ahora**; el esquema es ya un fragmento del modelo de INIT-10 |
| Capas de objetos del `.tmx` | Es "el mapa" | Fuera de la web; Tiled esta en salida (INIT-10); el motor hoy ignora las capas de objetos; sin validacion | No |
| Hoja del Excel | Junto a `OutboundStaging` | El motor no lee el Excel sino `warehouse.db` (regla del proyecto); un cambio no aplica hasta reimportar: invisibilidad del tipo que ya causo H-19 | No |
| Modelo propio de INIT-10 | Es el destino final | No existe todavia; esperarlo deja el bug de realismo abierto semanas | Destino, no punto de partida |

### 4.3 Distancias asimetricas (armado y orden de recorridos)

Que cambia y que no, verificado:

- **No cambia**: `route_calculator.calculate_route` ya calcula cada tramo con
  el A* **en el sentido del viaje** (`find_path(actual, siguiente)`) y el
  regreso aparte (`return_to_start`). Con reglas de sentido, los tramos
  ejecutados respetan la direccion sin tocar esa funcion: basta que el
  pathfinder filtre vecinos.
- **Cambia** (asumen simetria o linea recta): `operators._ordenar_stagings_por_distancia`
  (Manhattan), `assignment_calculator` (euclidea como heuristica, y A* cuando
  puede: linea 287), `dispatcher._estrategia_cercania` (radio en linea recta,
  BK-24) y el orden por `pick_sequence` (`order_work_orders_by_sequence`), que
  viene del Excel y no sabe de sentidos.
- Propuesta: un **oraculo de distancias dirigidas** (`DistanciasDirigidas`,
  en `core/circulation.py`): BFS dirigido desde cada origen con cache
  (el mapa tiene 900 celdas y 360 picks + 7 zonas: 367 BFS de 900 nodos, menos
  de un segundo, se calcula una vez al cargar y se reutiliza). `d(a, b) !=
  d(b, a)` es natural en el BFS dirigido. Todos los lugares de arriba lo
  consumen en vez de Manhattan/euclidea. Y un aviso en el validador: si el
  `pick_sequence` de un area obliga a recorrer un pasillo contra su sentido,
  `[WARN] Area_X: la secuencia de picking 12 -> 13 va contra el sentido del
  pasillo x=1..2; el recorrido real dara la vuelta (+N celdas)`.
- **Efecto en el baseline**: ninguno mientras no haya reglas (BFS dirigido sin
  reglas = distancias de siempre... con una salvedad: hoy se mezclan Manhattan
  y euclidea con el camino real. Si se unifica, cambian decisiones de despacho
  y el baseline. Recomiendo NO unificar en H-15: dejar el oraculo opt-in
  (solo cuando hay `circulacion`) y unificar en INIT-10 etapa 2 con baseline
  nuevo.

### 4.4 Conectividad fuerte y como explicarle al cliente que celda la rompe

- Grafo dirigido: nodos = celdas transitables, aristas = movimientos
  `permitido`. Componentes fuertemente conexas (Tarjan/Kosaraju, lineal).
- Regla: **todos los puntos de detencion** (picks, puestos, entradas, colas,
  salidas, zonas de espera, estacionamientos, muelles, celdas de spawn) deben
  estar en **la misma componente**. Con `validacion.conectividad_fuerte:
  "error"` bloquea Run/Aplicar; con `"warn"` avisa.
- Explicacion: para cada punto fuera de la componente principal se listan (a)
  si puede llegar pero no volver o al reves, y (b) **las aristas de frontera**
  entre su componente y la principal que estan prohibidas por una regla, con
  la regla que las prohibe. Ejemplo de mensaje: `Ubicacion (2,10)
  [Area_Ground] puede llegar a la zona 1 pero no volver. La vuelta se corta en
  (2,26)->(2,27): la regla 'sentido S' de la franja (1,3)-(2,26) lo prohibe.
  Corregir: dar sentido N al pasillo x=5..6 o quitar la regla.` Es barato:
  las aristas de frontera de una componente se enumeran en el mismo recorrido.
- **Bien formada** (3.1): ademas de fuerte, para cada par de puntos de
  detencion debe existir un camino que no pase por ningun otro punto de
  detencion (tratados como bloqueados). Es la generalizacion de
  `idle_zones._sin_cortar_el_mapa`; se calcula con el mismo BFS bloqueando el
  conjunto de puntos. Si falla: `[WARN] la celda de espera (3,27) deja sin
  paso a la entrada de DESCARGA-1` y la celda se descarta (auto) o se rechaza
  (config).

### 4.5 Deduccion automatica en layouts arbitrarios

Entrada: puestos `P` (1..n celdas), mapa transitable, picks, otras estaciones,
muelles.

1. **Vecinos utiles** de `P`: vecinos cardinales transitables que no son
   puestos de esta ni de otra estacion.
2. **Entrada** = el vecino util que minimiza la distancia BFS al conjunto de
   picks (sin pasar por `P`); empate -> el de mas vecinos transitables (el mas
   "abierto"); empate -> orden `(y, x)` (determinista). En WH1 zona 1: (3,28)
   [4 vecinos] gana a (2,29) y (4,29) [3 vecinos] con distancia igual.
3. **Salidas** = los demas vecinos utiles que tienen al menos una celda
   siguiente transitable distinta de `P` y de la entrada. En WH1: (2,29) ->
   (1,29)/(2,28) y (4,29) -> (5,29)/(4,28).
4. **Cola** = `[entrada]` y luego, hasta `cola_max`, celdas contiguas que se
   alejan de `P` y cumplen: transitables, no vecinas de un pick (boca de
   pasillo), no salida ni celda siguiente a una salida, no de otra estacion,
   y que no rompen la infraestructura bien formada (4.4). En WH1 con
   `cola_max: 1` es solo (3,28).
5. **Casos degenerados** (cada uno con su aviso, nunca silencio):
   - *Zona en rincon / pasillo de 1 celda*: un solo vecino util -> la entrada
     es tambien la salida (`salidas: []`, `entrada_bidireccional: true`). La
     fila NO puede empezar en la entrada (el que sale la necesita): `cola[0]`
     se pone a distancia 2 si existe una celda valida; si no, `cola: []` y
     todos esperan en el pulmon. El turno se libera al salir de la **entrada**
     (`liberar_al_salir_de: "entrada"` forzado). Es exactamente el patron de
     "punto de control" de FlexSim para un ramal ciego, y es el caso normal
     de **todo carril de staging con outbound encendido** (3.3).
   - *Zonas pegadas entre si* (puestos adyacentes): se excluyen mutuamente
     como vecinos utiles; si comparten el unico acceso, se fusionan en una
     estacion de N puestos con entrada comun (`[WARN] las zonas 3 y 4
     comparten acceso: se tratan como una estacion de 2 puestos`).
   - *Sin entrada valida* (puesto encerrado, o la entrada rompe la
     conectividad): `[ERROR]` con la celda y el motivo; con outbound apagado
     el motor puede seguir en modo "sin estacion" (comportamiento actual) solo
     si el Director acepta la degradacion (D8); yo recomiendo error bloqueante
     en la web y `[WARN]` + modo degradado en consola.
   - *Puesto en el borde con un vecino fuera del mapa*: simplemente no es
     vecino; cubierto por 1.
6. **Manual sobre automatico**: cualquier clave explicita reemplaza a la
   deducida, pasa por las mismas validaciones y se explica igual.

---

## 5. Orden de trabajo: H-15 antes que INIT-10 (etapa 2)

Recomendacion: **H-15 primero**, con el alcance F0-F2 de la seccion 6 (y F3 si
el Director decide sobre el muelle). INIT-10 etapa 1 (validar mapa contra
Excel, medio dia) en paralelo o inmediatamente. INIT-10 etapa 2 despues,
consumiendo el bloque `circulacion` tal cual.

Justificacion:

1. **Severidad real, no percibida.** Con la nueva evidencia, H-15 ocurre con la
   flota canonica en 3 de 4 corridas con semilla libre, y la relacion es 1:1
   entre rendiciones del planificador y episodios de superposicion. El
   producto, en su configuracion por defecto, muestra en el visor a dos o tres
   operarios en la misma celda. Por el principio rector (realismo primero),
   eso es un bug de la version que usa el cliente, y el gate no lo cubre
   (semilla 42 da 0 por azar). No es razonable dejarlo semanas debajo de una
   migracion de formato.
2. **Independencia del formato.** Nada de lo propuesto lee el `.tmx` de otra
   forma: consume `collision_matrix`, `staging_areas` y `config.json`. Cuando
   INIT-10 reemplace la fuente del mapa, `ReglasCirculacion` y `Estacion`
   reciben el mismo grafo desde otro cargador.
3. **Trabajo compartido con INIT-11.** El plan v2 de Task Path (F3
   `puntos_transferencia` con `capacidad` y `sobrecupo`, F4 `estaciones` con
   `puestos`) necesita exactamente "estacion con puestos, cola, entrada y
   salida". Hacer `Estacion` ahora para la descarga es hacer el 60% de INIT-11
   F3/F4. Diferir H-15 es construir dos veces.
4. **Riesgo de INIT-10.** Etapa 2 es un cambio de cargador + modelo de datos +
   visor; hacerlo con el motor arrastrando un deadlock conocido mezcla dos
   fuentes de cambio en el baseline y complica atribuir regresiones. Mejor
   cerrar H-15 con su baseline nuevo y arrancar INIT-10 sobre motor sano.
5. **Costo de la etapa 1 de INIT-10** es trivial y cierra un riesgo distinto
   (desalineacion mapa/Excel). No compite por recursos.

Si igual el Director prefiriera INIT-10 primero, el **esqueleto minimo** del
modelo que ya contemple la circulacion es:

```
almacen
 +- niveles[]
 |   +- grilla / red_movimiento      nodos (celdas) y ARISTAS DIRIGIDAS (LIF: startNodeId/endNodeId)
 |   +- almacenamiento               ubicaciones (hoy del Excel)
 |   +- estaciones[]                 {id, tipo, puestos[], entrada, salidas[], cola[], capacidad}
 |   +- zonas[]                      espera (pulmon), estacionamientos, areas
 +- reglas_circulacion[]             sentido / no_detenerse por nodo o arista
```

y el bloque `circulacion` de 4.2 es su serializacion de hoy. LIF (VDMA, v1.0.0,
MIT) aporta el vocabulario de red y estaciones (`nodes`, `edges` dirigidas
con `vehicleTypeEdgeProperties`, `stations` con `interactionNodeIds` y
`stationPosition`, todo en metros) pero **no tiene concepto de cola ni de
capacidad** ("does not describe any logical processes"): eso es nuestro y se
guarda como extension de la estacion. Alinearse con LIF en la red y extender
en la estacion es compatible con lo propuesto.

---

## 6. Plan por fases

Cada fase se cierra con `python -m pytest -q` verde, `python
scripts/regression_gate.py` (PASS o baseline actualizado a proposito en el
mismo commit) y las mediciones de 6.6.

### F0 — Corregir la sobre-reserva del origen (1 dia)

- **Archivos**: `src/subsystems/simulation/spacetime_planner.py`
  (`_reconstruct` devuelve `(celda, t_llegada, t_salida)`; `_plan_reserve_core`
  reserva el origen `[t_salida_origen, t_llegada_destino]` y la celda
  `[t_llegada, t_salida]`; `reserve_path_best_effort` y `plan_and_reserve`
  adaptan tipos), `operators.py:_timewindow_execute_plan` (lee `t_salida`
  como hoy lee `t`), `tests/unit/test_bk15_anticolision.py` (adaptar
  `test_ac03` a la nueva semantica: el origen sigue ocupado hasta la LLEGADA
  al vecino, no hasta la salida del vecino).
- **Tests nuevos**: `test_bk25_f0_planner.py`: (1) el script de 2.2 como test
  (plan aceptado, reserva del origen = `[0.5, 0.6]`); (2) el que espera ocupa
  UNA celda (ninguna reserva propia fuera de la celda de espera durante la
  espera); (3) espera inicial en el origen (primer paso retrasado) reservada
  correctamente.
- **Riesgo**: mueve el baseline (canonico incluido, porque hay esperas en el
  canonico). Se mide antes de actualizarlo; se espera que `replan_waits` y
  `plans_rejected_unreservable` caigan a decenas y la duracion no empeore.
- **Medicion**: tabla de 6.6, filas "2+2 libre x4", "4+4 s42", "60 s".

### F1 — Estacion de descarga con turno (outbound apagado) (3-4 dias)

- **Archivos nuevos**: `src/subsystems/simulation/stations.py` (`Estacion`,
  `GestorEstaciones`: deduccion 4.5, turno FIFO, cola, llamado desde el
  pulmon, metricas), `src/core/circulation.py` (`ReglasCirculacion` con las 3
  reglas de 4.1; validadores 4.4; sin SimPy, testeable en aislamiento).
- **Archivos tocados**: `warehouse.py` (construye reglas y estaciones DESPUES
  del outbound y ANTES de `GestorZonasEspera`, y le pasa a este las celdas
  reservadas de estaciones; expone `almacen.estaciones`), `operators.py`
  (PASO 4 de `_execute_pick_tour` segun 3.2; `_esperar_sin_estorbar` reusa el
  mismo "ir a una celda con reserva abierta"; ultimo recurso = retroceso, 2.3),
  `idle_zones.py` (`motivo_invalida`: salidas y sus celdas siguientes, colas,
  puestos; `puede_detenerse`), `pathfinder.py` y `spacetime_planner.py`
  (filtro de vecinos por reglas; `no_detenerse`), `src/core/config_schema.py`
  (bloque `circulacion`), `web_prototype/config_manager.py`
  (`_validar_circulacion`, mismo gestor que el motor), `src/core/replay_utils.py`
  + `src/engines/event_generator.py` (metricas de estacion en metadata y en
  el reporte de congestion: `turnos_concedidos`, `espera_turno_total_s`,
  `max_en_cola`, `llamados_desde_pulmon`, `salidas_bloqueadas`,
  `retrocesos`), visor (capa "circulacion": puestos, entrada, salidas, cola;
  en `web_prototype/static/...` donde se dibujan hoy las zonas),
  `docs/MANUAL_CONFIGURACION.md` (nuevo card en la pestana Layout y Datos u
  Outbound: "Circulacion en la descarga").
- **Tests** (`test_bk25_f1_estacion.py`, `test_bk25_reglas.py`):
  - deduccion en grillas sinteticas: WH1 real (entrada (3,28), salidas (2,29)
    y (4,29)); rincon (1 vecino -> entrada bidireccional, cola a distancia 2);
    pasillo ciego de 1 celda (cola vacia, pulmon); zonas pegadas (fusion);
    puesto encerrado (error con motivo);
  - turno: FIFO determinista; capacidad N; nunca dos con turno en el mismo
    puesto; el turno no se libera hasta que `current_position != puesto`;
  - invariantes: ninguna reserva abierta en salidas ni en sus celdas
    siguientes; ningun agente sin turno tiene destino vecino de un puesto
    salvo `cola[0]`; `no_detenerse` sin esperas en planes;
  - validador: conectividad fuerte con explicacion (celda + regla culpable);
    bien formada;
  - integracion (marcada lenta, ~1 min, estilo
    `tests/unit/test_qa_h19_espera_con_outbound.py`): WH1 canonico 4+4 seed
    42 -> 0 co-ocupaciones fuera de la ventana de arranque, 0
    `exec_fallbacks`, 0 `retrocesos`; idem 2+2 con descarga 60 s.
- **Riesgos**: (a) el orden de llamada desde el pulmon debe ser determinista
  (clave `(t_pedido, agent_id)`); (b) estacion sin solucion en mapas
  personalizados -> modo degradado con aviso (D8); (c) la fila de 1 celda
  puede aumentar la espera media vs "todos pegados": es realismo, se reporta
  el trade-off; (d) Tour Mixto con varias zonas: pedir turno por zona, en
  orden por camino dirigido.

### F2 — Reglas de circulacion editables + visor + oraculo dirigido (2-3 dias)

- Pestana web: card "Circulacion" (estaciones con auto/manual, `cola_max`,
  reglas de celda por rectangulo con sentido/no_detenerse), con validacion en
  vivo (mensajes 4.4) y la capa del visor de configuracion (pintar flechas y
  celdas prohibidas sobre el mapa que ya dibuja `/api/layout`).
- `DistanciasDirigidas` opt-in (solo con reglas), consumido por
  `_ordenar_stagings_por_distancia`, `assignment_calculator`, Cercania.
- Aviso de `pick_sequence` contra sentido.
- Tests: round-trip web (patron `test_config_save_roundtrip.py`), validador
  desde la web, distancias asimetricas en grilla sintetica, A* estatico y SIPP
  respetan sentido (mismo mapa, misma respuesta).
- **Fase B (pasillos de un sentido) queda LISTA de infraestructura pero sin
  reglas en el canonico**: no cambia el baseline. Activarla en WH1 es una
  decision de negocio (D5); en WH1 los pasillos tienen 2 celdas de ancho y el
  cruce frontal se resuelve solo, asi que el beneficio esperado es bajo.

### F3 — Muelle activo sobre la misma estacion (3-4 dias + decisiones D3 y D10)

- **Carriles explicitos y rectangulares.** `warehouse.py` deja de expandir en
  anillos (`build_zone_cells`) y toma las celdas de `staging_areas` cuando la
  BD trae varias por `staging_id` (ya soportado por `data_manager`); si trae
  una sola, la expansion automatica pasa a ser un rectangulo de 1 columna x
  `zone_capacity_default` de fondo, **perpendicular al borde mas cercano** y
  solo si no invade la fila de bocas de pasillo ni otra zona; si no cabe,
  `[ERROR]` con la celda que sobra (en WH1: no cabe; ver D10). La edicion de
  celdas de zona desde la web ya existe (`routers/master_data.py`): se
  extiende a "carril de k celdas".
- `_outbound_discharge_lanes` se reescribe sobre `Estacion` (puestos =
  columnas; celdas privadas del carril; sin `_jump_to`; espera con reserva en
  fila/pulmon; entrada deducida, nunca dentro de otra zona). Spawn nunca
  dentro de un carril (BK-29): los agentes arrancan en celdas de fila/pulmon
  (resuelve tambien la co-ocupacion de arranque en (3,28) que aparece en
  todas las corridas: `cooccupation_events_startup_window` 1-2).
- Unidad de staging segun D3 (contenedor por pedido/tour o pallet por WO).
- Verificar la hipotesis del "7 de 8" (2.5, punto 6) y, si se confirma, que
  el slot en descarga no cuente como ocupado para el camion o que el camion
  espere al deposito en curso (decision menor, se resuelve en la fase).
- Tests: 0 saltos de posicion > 1 celda en el `.jsonl` (herramienta
  `scripts/qa/analizar_replay.py` ya cuenta posiciones); 0 co-ocupaciones
  incluida la ventana de arranque; ninguna entrada de puesto dentro de otra
  zona; duracion re-medida con D3 decidido; camiones cargan hasta 8.

### F4 — INIT-10 etapa 1 (medio dia, en paralelo)

Validar mapa contra Excel al aplicar y corregir la guia. Sin relacion de
codigo con F0-F3.

### 6.6 Como medir el exito

Metricas ya disponibles (sin codigo nuevo): `congestion_report_*.json`
(`cooccupation_events_total`, `cooccupation_events_startup_window`,
`max_concurrent_any_cell`, `top_hotspots`), `timewindow_shadow_report_*.json`
(`exec_fallbacks`, `exec_blocked`, `plans_rejected_unreservable`,
`replan_waits`, `dwell_conflicts`, `reserve_overlaps`), duracion (timestamp de
`SIMULATION_END` en el `.jsonl`; `scripts/qa/esperar_corrida.py` ya lo exige) y
`scripts/qa/analizar_replay.py` para posiciones/co-ocupaciones desde el replay.
Metricas nuevas de F1: `espera_turno_total_s`, `max_en_cola`,
`llamados_desde_pulmon`, `salidas_bloqueadas`, `retrocesos`.

| Escenario | Hoy (medido) | Objetivo tras F0 | Objetivo tras F1 |
|---|---|---|---|
| Canonico 2+2, seed 42 (gate) | 0 co-oc. fuera de arranque; duracion ~7.300-7.800 s | 0; `replan_waits` de miles a decenas; duracion no peor | 0; `exec_fallbacks` 0; `retrocesos` 0; duracion no peor |
| Canonico 2+2, semilla libre x4 (las 4 corridas de 2.2) | co-oc. 1/6/3/0; fallbacks 1/8/2/0; rechazos 5.154/13.108/4.607/7 | rechazos < 100 en todas | co-oc. 0 en las 4; fallbacks 0; rechazos < 100 |
| 4+4, seed 42 (QA-5.2) | 28 rendiciones; 32 co-oc. (26 en (3,29), hasta 6); 50.643 esperas; 7.178 s | rendiciones y esperas caen >90%; co-oc. < 5 | 0 / 0 / esperas < 1.000; duracion claramente menor que 2+2 (referencia BK-09: 2+4 dio -35%; con 4+4 y una sola zona el tope es la propia zona, esperar al menos -25%) |
| 2+2, descarga 60 s (QA-5.5) | 21 co-oc.; 16 rendiciones | < 5 / < 5 | 0 / 0; `max_en_cola` <= 1; `llamados_desde_pulmon` > 0 |
| 2+2 + outbound ON (023347) | 16.091 s; 50% `unloading`; 52 saltos; 2 co-oc. de arranque; camiones max 7/8; 343 esperas dentro del carril (29.483 s) | (sin cambio) | F3: 0 saltos; 0 co-oc. incluida la de arranque; 0 esperas dentro del carril (todas afuera, con reserva); camiones hasta 8; duracion segun D3 y D10 |

Criterio de "exito" global: en TODOS los escenarios, co-ocupaciones fuera de
la ventana de arranque = 0, `exec_fallbacks` = 0 y `retrocesos` = 0 (es decir,
la garantia es por construccion, no por suerte de semilla), y la duracion de
4+4 mejora sobre 2+2. Si un escenario no da 0, no se cierra H-15: se
investiga.

---

## 7. Decisiones que necesita tomar el Director

- **D1. Aceptar mover el baseline en F0** (correccion del planificador). Es un
  cambio de comportamiento intencional y medido. Recomendacion: si.
- **D2. Puestos simultaneos en la zona 1 con outbound apagado.** Hoy 1.
  Realismo: un carril de staging de varios metros admite 2 gruas. Con
  outbound encendido ya son 2 (columnas). Recomendacion: dejar 1 por defecto
  para no mezclar efectos en la medicion de F1, y hacerlo configurable en F1
  (no diferirlo); medir 1 vs 2 en el A/B y elegir el canonico despues.
- **D3. Unidad de staging con outbound encendido**: un pallet por tarea (hoy)
  o un contenedor por pedido/recorrido. Recomendacion: contenedor por pedido
  (alineado con INIT-11 P3); hasta entonces, avisar en la UI que "un pallet
  por tarea" duplica la jornada. Es una decision de modelado, no un bug.
- **D4. `cola_max` por defecto** (recomiendo 1) y politica de llamado desde
  el pulmon (recomiendo FIFO por tiempo de pedido; alternativa: el mas
  cercano, menos justo, mas rapido).
- **D5. Fase B (pasillos de un sentido)**: disenar y dejar la infraestructura
  lista (F2) pero no activar reglas en WH1. Recomendacion: si, y revisitar con
  un layout de cliente con pasillos angostos.
- **D6. Ultimo recurso del motor**: retroceder / seguir esperando con aviso,
  nunca pisar. Recomendacion: retroceder + `[WARN]` + metrica `retrocesos`,
  con objetivo 0.
- **D7. Forma del bloque `circulacion`**: `desde/hasta` vs el formato
  `x, y, ancho, alto` de `zonas_espera`. Preferencia del Director; propongo
  `desde/hasta` por legibilidad de flechas, pero unificar es razonable.
- **D8. Mapa sin solucion de circulacion** (puesto encerrado): error
  bloqueante en la web y modo degradado con `[WARN]` en consola, o error en
  ambos. Recomendacion: la primera.
- **D9 (ya en el backlog, la agrava)**: `outbound_staging_distribution` 100% a
  la zona 1. Repartir entre zonas reduce el problema pero no lo resuelve; la
  medicion de 6.6 debe hacerse con 100% a la zona 1 (peor caso) y con el
  reparto real.
- **D10. Anden de muelle en WH1.** Con 3 filas entre racks y muelle, un
  staging de varias celdas de fondo se come la circulacion (2.5, punto 5). Si
  el muelle activo debe simularse con realismo en WH1, hace falta un mapa con
  anden (por ejemplo 6-8 filas mas entre la fila 27 y las zonas) y carriles
  rectangulares definidos en la BD. Opciones: (a) editar `WH1.tmx` ahora (una
  tarde, y actualizar el Excel de zonas con las celdas de cada carril);
  (b) esperar al editor de INIT-10 etapa 3 y, mientras, dejar el outbound
  como esta con el `[WARN]` de 2.5; (c) declarar que WH1 con outbound
  encendido es una configuracion "de demostracion" y documentarlo.
  Recomendacion: (a) si el cliente va a ver el muelle en corto plazo; si no,
  (b). En cualquier caso F3 no se cierra con la geometria actual.

---

## 8. Donde discrepo con lo que ya estaba sobre la mesa

1. **La causa principal en numeros no era la conversada.** La sobre-reserva
   del origen (2.2) explica el 85-95% de los planes rechazados y los "10
   minutos" de rendicion; sin corregirla, salidas de un sentido y fila
   mejoran menos de lo esperado, y el que espera seguira tapando dos celdas.
2. **La idea del Director es correcta pero incompleta**: garantiza la salida,
   no el turno. Sin turno explicito, el segundo y el tercero en llegar siguen
   teniendo como destino el puesto ocupado y el planificador los pega a la
   zona (o a la fila, con el mismo efecto sobre el pasillo). Hace falta el
   recurso "estacion" (como FlexSim/AnyLogic), y la evidencia de MAPF dice que
   con puntos de detencion bien formados la garantia es de construccion.
3. **Fila larga fisica: no.** En WH1 solo cabe tapando el pasillo transversal
   o las bocas de pasillo; en la realidad la cola frente a una puerta es de
   1-2 y el resto espera en un pulmon. Fila de 1 (la entrada) + pulmon con
   llamado por turno (el complemento del asistente, pero como regla, no como
   desborde).
4. **Puestos simultaneos: no diferir.** Es un parametro trivial de la
   estacion, ya existe de hecho con outbound encendido (columnas), y es la
   palanca realista para que 4+4 rinda. Diferirlo es diferir la respuesta a
   "por que duplicar la flota no sirve".
5. **Fase B: disenar si, implementar todavia no.** La infraestructura (reglas
   por arista, validador de conectividad fuerte, distancias dirigidas) sale
   casi gratis de F1/F2; activar sentidos en WH1 (pasillos de 2 celdas) no
   tiene beneficio medible y si riesgo de trampas. Esperar a un layout que lo
   necesite.
6. **Orden: coincido con hacer H-15 antes que INIT-10 etapa 2**, pero con un
   argumento mas fuerte que "no depende del formato": la estacion es el
   cimiento de INIT-11 F3/F4, y H-15 es un bug de la configuracion por
   defecto, no un caso extremo de flota grande.
7. **"Sentido unico por celda" como primitiva unica: no alcanza.** Las salidas
   de la zona necesitan "solo se entra desde el puesto", que es una regla de
   arista ligada a la estacion. Propongo tres primitivas (sentido,
   no_detenerse, salida de estacion), no una.
8. **Con outbound encendido, las salidas laterales no existen.** Las celdas
   (2,29) y (4,29) son slots de pallet en ese modo, y el carril es un ramal
   ciego. La idea del Director aplica al modo "punto de descarga" (outbound
   apagado); para los carriles la garantia viene del turno + espera afuera,
   y la geometria de WH1 necesita un anden para ser realista (D10).

---

## 9. Fuentes

Codigo (rama `qa/configuracion-web`, leido el 2026-09-19): `operators.py`
(`_execute_pick_tour`, `_recorrer_tramo`, `_timewindow_execute_plan`,
`_esperar_sin_estorbar`, `_outbound_nav_to`, `_outbound_discharge_lanes`,
`_spawn_lane`, `_ordenar_stagings_por_distancia`), `spacetime_planner.py`
(`find_path_st`, `_reconstruct`, `_plan_reserve_core`, `plan_and_reserve`,
`reserve_dwell`), `reservation_table.py` (`is_free`, `earliest_free`,
`can_swap`), `pathfinder.py` (`get_neighbors`, `find_path`),
`idle_zones.py`, `parking.py`, `outbound.py`, `warehouse.py` (constructor),
`route_calculator.py` (`calculate_route`), `congestion_manager.py`,
`config_schema.py`, `web_prototype/config_manager.py`
(`_validar_zonas_espera`), `warehouse.db` (`staging_areas`, `inbound_docks`,
solo lectura), `layouts/WH1.tmx` (grilla impresa con `LayoutManager(...,
headless=True)`), reportes en `output/simulation_20260919_{012605, 012803,
020157, 023549, 023347}`.

Externas:

- VDMA, Layout Interchange Format (LIF) v1.0.0, MIT:
  https://github.com/Intralogistics-2X-LIF/Layout-Interchange-Format
  (aristas dirigidas `startNodeId`/`endNodeId`, `stations` con
  `interactionNodeIds`, metros; sin concepto de cola ni capacidad).
- FlexSim, redes AGV (control points / control areas, asignacion
  todo-o-nada, carriles de un sentido):
  https://docs.flexsim.com/en/21.2/WorkingWithTasks/AGVNetworks/BuildingAGVLogic/BuildingAGVLogic.html ,
  https://docs.flexsim.com/en/21.2/Reference/Tools/AGVNetworkTool/AccumulationTypes/AccumulationTypes.html ,
  https://answers.flexsim.com/questions/125062/agv-deadlock-avoidance.html ,
  https://forums.autodesk.com/t5/flexsim-forum/agv-deadlock-avoidance/m-p/13541348
  (las paginas de documentacion respondieron 403/404 al consultor; se cita lo
  que devolvio la busqueda y el foro).
- AnyLogic, Material Handling Library (`Path`, `Queue` sobre path,
  `SeizeTransporter`/`MoveByTransporter`):
  https://anylogic.help/markup/path-mhl.html ,
  https://www.anylogic.com/blog/transporters-learning-to-use-the-material-handling-library-part-2/
  (idem: 403 al consultor; se cita la busqueda).
- Cap, Novak, Kleiner, Selecky, "Prioritized Planning Algorithms for
  Trajectory Coordination of Multiple Mobile Robots", IEEE T-ASE 12(3), 2015:
  https://arxiv.org/abs/1409.2399 (infraestructuras bien formadas; parafrasis,
  ver 3.1).
- Ma, Li, Kumar, Koenig, "Lifelong Multi-Agent Path Finding for Online Pickup
  and Delivery Tasks", AAMAS 2017: https://arxiv.org/abs/1705.10868 ,
  http://idm-lab.org/bib/abstracts/Koen17d.html ("solve all well-formed MAPD
  instances").
- Phillips, Likhachev, "SIPP: Safe Interval Path Planning for Dynamic
  Environments", ICRA 2011:
  https://www.semanticscholar.org/paper/7dba986bfff6cb4c7bffed3675a8cfbf0d08c1f9
- Diseno de muelles y trafico interior: McGuire Dock Planning Guide
  https://www.wbmcguire.com/design/dock-planning-guide ; A Lot of Striping,
  Warehouse Traffic Flow Management Plan Guide (2026)
  https://www.alotofstriping.com/the-ultimate-warehouse-traffic-flow-management-plan-guide-2026/ ;
  Precision Integrators, Staging Area Design
  https://www.precisionintegrators.com/blog-posts/staging-area-design-reducing-bottlenecks-at-receiving-and-shipping ;
  ENCOR Advisors, Warehouse Docking Design
  https://encoradvisors.com/warehouse-docking-design/
