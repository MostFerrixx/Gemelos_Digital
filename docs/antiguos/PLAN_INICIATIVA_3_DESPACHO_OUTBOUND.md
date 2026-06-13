# PLAN INICIATIVA #3 — SUBSISTEMA OUTBOUND: AFORO DE STAGING + DESPACHO REAL

> Documento de PLANIFICACION. NO contiene codigo definitivo (Ley #1: PLAN ANTES
> QUE CODIGO). Requiere el OK del Director antes de escribir codigo.
> Rama de trabajo sugerida: `feature/outbound-dispatch-v13`.
> Continua la linea de la Iniciativa #2 (Opcion C, time-window routing) y se
> apoya en el analisis de `docs/ANALISIS_STAGING_AFORO.md`.
>
> Decision del Director ya tomada: modelar el outbound con la **Opcion 3**
> (proceso de despacho REAL: pallets que permanecen + camion/expedicion que los
> retira), NO con rotacion infinita implicita ni con auto-liberacion temporizada.

---

## CHECKLIST INTERNO DE REDACCION (documentacion viva)
- [x] 0. Anclaje: el codigo real (verificado por lectura/medicion)
- [x] 1. Objetivo y filosofia
- [x] 2. Modelo conceptual del outbound (entidades, estados, politica)
- [x] 3. Diseno arquitectonico (zona, slot reservable, proceso camion)
- [x] 4. Integracion con la Opcion C (anti-deadlock: el punto critico)
- [x] 5. Aforo / dimensionamiento como funcion de la politica
- [x] 6. Plan de implementacion por fases
- [x] 7. Casos borde (exhaustivo)
- [x] 8. Riesgos, complejidad, rollback
- [x] 9. Punteros de codigo (anti-alucinacion)
- [x] 10. Relacion con la vision de producto

---

## 0. ANCLAJE: EL CODIGO REAL (verificado esta sesion)

Hechos contra los que se construye el plan (no suposiciones):

**Definicion del staging:** la ubicacion la fija la hoja `OutboundStaging` de
`layouts/Warehouse_Logic.xlsx`, leida por
`src/subsystems/simulation/data_manager.py::_process_outbound_staging`
(API `get_outbound_staging_locations() -> {staging_id: (x,y)}`). Hay **7
staging de UNA sola celda** cada uno, todos en `y=29`:
(3,29)(7,29)(11,29)(15,29)(19,29)(23,29)(27,29). El escenario de estres
(`config_stress_tw_exec.json`) enruta el **100% a staging 1 = (3,29)**
(`outbound_staging_distribution: {"1":100, resto:0}`).

**Descarga actual (NO hay pallet persistente):** en `operators.py`, tras el
picking el agente agrupa WOs por staging, navega al staging y entra a un bucle
"V12 GRANULAR DISCHARGE": por cada WO hace `status="unloading"`,
`yield env.timeout(self.discharge_time)` (=5s), decrementa cargo, marca la WO
`staged` (terminal via `dispatcher.notificar_completado_individual`) y **se va a
idle**. No queda ningun objeto ocupando la celda. La mercancia "se evapora".

**NO existe despacho/expedicion:** verificado en `operators.py`, `warehouse.py`,
`dispatcher.py`, `order_strategies.py`. El unico "ship" es
`fulfillment_policy="ship_partial"` (surtido parcial de lineas, NO salida
fisica). El `dispatcher.py` (DispatcherV11) reparte TRABAJO a operarios (tours),
NO expide mercancia. Conclusion: hoy el staging se comporta como **rotacion
infinita e instantanea** (la celda se libera al irse el agente).

**Estado dinamico / reserva (Opcion C):** `congestion_manager.py` +
`reservation_table.py` (`ReservationTable`: intervalos disjuntos por celda;
`is_free`, `reserve`, `reserve_dwell`, `release_agent`, `can_swap`) +
`spacetime_planner.py` (`SpaceTimePlanner.find_path_st`, A* espacio-temporal;
`plan_and_reserve`). Choke point de posicion: `operators.py::_set_pos`. Ejecucion
del plan: `_recorrer_tramo` / `_timewindow_execute_plan`. Flag en
`config.json["congestion"]["mode"]="timewindow"`, sub-bloque `timewindow`.

**Medicion de referencia (corrida determinista, 20 agentes, 40 ordenes):**
126 pallets (WorkOrders) depositados en (3,29); **pico simultaneo descargando =
6** (hasta 8 agentes presentes en la celda); sim_end_t=268s; deposito medio
~0.47 pallets/s. El I1!=0 documentado en la Fase 2/2b de la Opcion C se debe
EXACTAMENTE al apilamiento de descargas sobre 1 celda (permanencia no reservada).

**Geometria libre para ampliar:** el muelle inferior `y=27,28,29` son **90
celdas contiguas, todas caminables y hoy vacias**. Cabe una zona de aforo sin
agrandar el TMX.

---

## 1. OBJETIVO Y FILOSOFIA

### 1.1 El objetivo
Reemplazar la "rotacion infinita implicita" por un **subsistema outbound
explicito y fiel**: (a) cada posicion de staging sostiene UN pallet
(capacidad 1 por celda); (b) los pallets PERMANECEN tras la descarga; (c) un
proceso de DESPACHO (camion/expedicion) los retira por politica configurable,
liberando posiciones; (d) cuando la zona se llena, el sistema aplica
**backpressure realista** (el agente espera una posicion libre) SIN reintroducir
los freezes que la Opcion C elimino.

### 1.2 El cambio de filosofia
De un staging que es un PUNTO de servicio transitorio (la mercancia desaparece)
a un staging que es un BUFFER FINITO con entrada (descarga) y salida (despacho).
Esto convierte el muelle en un segundo cuello de botella REAL y medible —que es
justo lo que un gemelo digital serio debe modelar— en lugar de esconderlo.

### 1.3 La invariante economica que gobierna todo
El muelle es un buffer. Por la ley de Little, el numero medio de pallets en el
muelle = tasa_de_deposito x dwell_medio. El sistema NO colapsa si y solo si la
**tasa sostenida de despacho >= tasa sostenida de deposito**. El aforo `k`
(numero de posiciones) cubre el PICO de backlog transitorio. Por tanto: `k`,
politica de camion y tasa de deposito son **tres perillas acopladas**; ninguna
se decide aislada. Este principio es el corazon del plan.

---

## 2. MODELO CONCEPTUAL DEL OUTBOUND

### 2.1 Entidades nuevas
- **Pallet (carga depositada)**: objeto persistente que nace cuando un agente
  descarga una WO en el staging. Atributos: `id`, `wo_id`/`order_id`,
  `staging_id`, `cell (x,y)` (su posicion fisica en la zona), `t_staged`,
  `volumen`, `status`. HOY NO EXISTE; es la adicion central.
- **DockSlot (posicion de aforo)**: una celda caminable de la zona de staging
  con capacidad 1. Tiene `cell`, `occupied_by (pallet_id|None)`. El conjunto de
  slots de un `staging_id` = su "zona de aforo".
- **OutboundProcess / Truck (expedicion)**: proceso SimPy que, segun politica,
  retira pallets `staged`, los marca `shipped` y libera sus slots.

### 2.2 Ciclo de vida del pallet
`staged` (depositado, ocupa slot) -> `awaiting_load` (elegido por un camion) ->
`loading` (durante `loading_time`) -> `shipped` (retirado; el slot queda libre).
Para el MVP se puede colapsar `awaiting_load`+`loading` en una sola transicion
temporizada por el camion. El slot se libera al pasar a `shipped`.

### 2.3 Politicas de despacho (parametrizables, en config.json)
- **Por tiempo (interarrival)**: un camion llega cada `T` segundos y retira hasta
  `C` pallets. tasa_despacho = C/T.
- **Por lote/llenado (trigger)**: el camion sale cuando hay `>= C` pallets
  acumulados (o cuando la zona supera un umbral de ocupacion).
- **Por horario (schedule)**: lista de instantes de llegada (citas de camion).
- **Hibrida**: lo que ocurra primero (tiempo o llenado).
MVP recomendado: **por tiempo (T, C)**, por ser el mas simple, determinista y
suficiente para estudiar el acoplamiento k<->despacho.

### 2.4 Que es "un pallet" (consistencia con el modelo)
Se mantiene la convencion del analisis: **1 WorkOrder depositada = 1 pallet**
(la descarga ya es granular por WO). Una orden multi-linea genera varios pallets.
(Opcional fase posterior: consolidar varias WO pequenas de la misma orden en un
pallet por volumen; se documenta pero no entra al MVP.)

---

## 3. DISENO ARQUITECTONICO

### 3.1 De staging-punto a staging-zona
- **Definicion de la zona**: cada `staging_id` deja de ser 1 celda y pasa a un
  CONJUNTO EXPLICITO de celdas. Recomendacion: lista de celdas por `staging_id`
  (no un rectangulo implicito), para no atarse a formas y poder esquivar
  obstaculos. Fuente de verdad: ampliar la hoja `OutboundStaging`
  (`staging_id, x, y` con varias filas por id) o un bloque en `config.json`. Como
  la geometria es dato del layout, lo natural es la hoja Excel; `data_manager`
  pasa de `{id:(x,y)}` a `{id: [(x,y), ...]}`.
- **Tamano por defecto**: zona de **8 posiciones (2x4) anclada en (3,29)**
  usando `y=28,29` y `x=2..5` (cabe en el muelle libre; ver analisis). `k`
  definitivo se calibra contra la politica (seccion 5).

### 3.2 El DockSlot como recurso RESERVABLE (clave de la integracion)
El slot es una celda; ocuparla con un pallet = una **reserva de permanencia**
en la `ReservationTable` que dura hasta que el camion retira el pallet. Diferencia
con la Fase 2b fallida de la Opcion C: alli la reserva se hacia AL LLEGAR (tarde)
y la meta era 1 celda compartida. Aqui:
1. el agente, AL PLANIFICAR su ruta de retorno, **solicita y reserva un slot
   LIBRE concreto** de la zona (no la celda generica), de modo que el planner ya
   serializa correctamente si la zona esta llena;
2. la reserva del slot es "hasta `shipped`" (fin no conocido a priori): se modela
   como reserva abierta que el evento de camion CIERRA con `release` cuando retira
   el pallet. Esto exige una pequena extension a `ReservationTable`
   (reserva de duracion abierta + release explicito por id de pallet/slot).

### 3.3 Asignacion de slot y backpressure
- Al terminar el picking, el agente pide a la zona del `staging_id` destino un
  slot libre. Si hay -> lo reserva y rutea hacia esa celda exacta.
- Si NO hay slot libre -> **backpressure**: el agente ejecuta la accion "esperar"
  reservada de la Opcion C (quedarse en una celda segura por `dt`, reintentar),
  hasta que un camion libere un slot. NO es espera reactiva ni busy-wait: es la
  misma primitiva conflict-free del time-window. Asi el muelle lleno produce cola
  realista, no freeze.

### 3.4 El proceso de camion (OutboundProcess)
Proceso SimPy arrancado en `event_generator` (junto al watchdog), gateado por
`config.json["outbound"]["enabled"]`:
```
loop:
  esperar segun politica (timeout T  /  evento de llenado)
  seleccionar hasta C pallets 'staged' (FIFO por t_staged; determinista)
  marcar 'loading'; yield timeout(loading_time)
  marcar 'shipped'; release del slot de cada pallet (ReservationTable + DockSlot)
  emitir eventos (truck_arrived, pallet_loading, truck_departed)
```
MVP: **camion ABSTRACTO** (no se mueve por la grilla; solo consume y libera). Es
suficiente para el aforo y mucho mas simple/determinista. Fidelidad posterior
(Fase 3): camion FISICO que llega a una puerta de muelle (celda outbound) y
ocupa esa celda durante la carga.

### 3.5 Contrato de eventos (headless -> jsonl -> viewer)
Eventos nuevos a `registrar_evento`, para que el viewer pueda dibujar el muelle
vivo: `pallet_staged` (aparece pallet en slot), `pallet_shipped` (desaparece),
`truck_arrived`/`truck_departed`. Mantiene la cadena viva intacta (Ley #6); el
render de pallets/camiones en el viewer es trabajo de una fase posterior.

### 3.6 Determinismo
Politica de camion determinista (T fijo o schedule fijo; seed fijo si hay
aleatoriedad). Seleccion de pallets por orden total (t_staged, desempate por
pallet_id). Asignacion de slot por orden fijo de celdas de la zona. Resultado:
mismo config + mismas ordenes => mismo `.jsonl`. Se valida con doble corrida.

---

## 4. INTEGRACION CON LA OPCION C (ANTI-DEADLOCK: EL PUNTO CRITICO)

Es el mayor riesgo: introducir un buffer finito puede REINTRODUCIR la clase de
freeze que la Opcion C elimino. Defensa por construccion:

### 4.1 El slot lleno se modela como espera RESERVADA, no reactiva
Un agente sin slot no hace busy-wait ni timeout reactivo (eso era F3, jubilado):
reserva "quedarme en celda segura por dt" y reintenta planificar. Es una accion
valida del planner espacio-temporal, conflict-free por construccion.

### 4.2 El pallet es un OBSTACULO DINAMICO reservado
Un pallet en un slot ocupa esa celda en la tabla de reservas mientras existe; el
planner enruta a los demas agentes ESQUIVANDOLO (no lo atraviesa). Esto resuelve
de raiz el I1!=0 de la Fase 2b: la permanencia (ahora del pallet, no del agente)
SI esta reservada, y reservada al planificar, no al llegar.

### 4.3 Condicion de progreso (no-colapso) — explicita y verificable
El dwell de un pallet es finito si y solo si un camion lo retira. Por tanto la
terminacion ya NO la garantiza solo el orden total de la Opcion C: exige
**tasa_despacho_sostenida >= tasa_deposito_sostenida**. Si la politica de camion
no la cumple, el backlog crece sin cota, los slots nunca se liberan y los agentes
esperan indefinidamente -> starvation/freeze. Mitigaciones:
1. La politica debe dimensionarse para cumplir la desigualdad (seccion 5).
2. El watchdog (degradado a detector en la Opcion C) VIGILA espera-por-slot: si
   un agente espera mas de `slot_wait_alert`, registra incidente (no crashea).
3. Metrica de ocupacion de muelle y backlog en el reporte, para detectar
   saturacion antes de que sea freeze.

### 4.4 El camion y el orden total de planificacion
El camion abstracto (MVP) no se mueve por la grilla -> no participa en el A*
espacio-temporal; solo LIBERA reservas (release de slots). Un release nunca crea
conflicto (solo abre huecos), asi que no rompe las garantias de la Opcion C. El
camion fisico (Fase 3) si seria un agente mas en la tabla y se planifica en el
orden total como cualquiera.

### 4.5 Interaccion con el parking/idle (la otra mitad del aforo)
Tras depositar, el agente va a idle. Hoy el idle se apila en el depot (parte del
I1 residual). El mismo principio de slot reservable aplica al PARKING: el agente
idle reserva una celda de aparcamiento (fuera del corredor de trafico). Se
referencia aqui pero el foco de esta iniciativa es el OUTBOUND; el aforo de
parking puede ser una sub-fase o iniciativa hermana.

---

## 5. AFORO / DIMENSIONAMIENTO COMO FUNCION DE LA POLITICA

`k` no es un numero fijo: `k >= max_t (depositados(t) - despachados(t))` = pico de
backlog. Metodo:
- Con politica por tiempo (cada `T`, retira `C`): tasa_despacho = C/T. En el
  escenario de referencia, deposito medio ~0.47 pallets/s (126 en 268s). Para
  no acumular en regimen: `C/T >= 0.47`. El PICO de backlog ademas depende de la
  rafaga (burstiness) del deposito y del desfase de los camiones.
- **Procedimiento empirico (recomendado)**: barrer (T, C) en simulacion con
  pallets persistentes y medir, para cada combinacion, el backlog maximo
  observado -> ese es el `k` minimo para no desbordar. Producir la curva
  "frecuencia/capacidad de despacho vs. posiciones necesarias" para que el
  Director elija el punto de operacion. Esto es exactamente lo que la Fase 1/2
  miden (seccion 6).
- Cota de cordura: con despacho instantaneo ideal, `k` = pico simultaneo de
  descarga = 6 -> `k=8` con margen. Con despacho mas lento/por lotes, `k` sube.

---

## 6. PLAN DE IMPLEMENTACION POR FASES (detras de flag, reversible, validado)

Principio rector (Ley #6 + disciplina F0-F3): cada fase detras de
`config.json["outbound"]["enabled"]`; con el flag off, comportamiento
**byte-identico** al actual. Validacion empirica por fase (Ley #2) antes de
avanzar. Importante (acordado con el Director): se valida primero el MECANISMO en
el mapa ACTUAL (WH1) con muelle ensanchado; el layout a escala real es una fase
POSTERIOR y separada, no se mezcla.

### Fase 0 — Andamiaje y flag (riesgo casi nulo)
- Bloque `config.json["outbound"]` (enabled, policy, T, C, loading_time,
  zona/aforo). Entidades `Pallet` y `DockSlot` (firmas, sin logica). `data_manager`
  soporta multiples celdas por `staging_id` (lee, no cambia comportamiento si la
  hoja sigue con 1 celda/id). Puntos de injerto gateados por `outbound.enabled`.
- Validar: flag off => `.jsonl` byte-identico al baseline; imports OK; sim termina.

### Fase 1 — Pallets persistentes + zona de aforo (SIN camion aun)
- Al descargar, crear `Pallet` persistente que ocupa un `DockSlot` y RESERVA su
  celda (dwell abierto). Asignacion de slot libre al planificar el retorno;
  backpressure (espera reservada) si la zona esta llena. SIN camion: para no
  colapsar en validacion, usar un release temporal de prueba (o correr con pocas
  ordenes) SOLO para medir backlog. Objetivo real de la fase: **demostrar I1=0
  con permanencia reservada** (resolver el residual de la Fase 2b) y MEDIR el
  backlog/pico real -> insumo para dimensionar (seccion 5).
- Validar: I1=0 (co-ocupacion), planner sin solapes, determinismo, coste planner.

### Fase 2 — Proceso de camion (el despacho real)
- `OutboundProcess` abstracto con politica (T, C). Libera slots al expedir.
  Backpressure plenamente activo. Eventos `pallet_*`/`truck_*` al jsonl.
- Validar (escenario estres, 20 agentes): **no-colapso** (tasa_despacho cubre
  deposito), **no-deadlock / no-freeze** (sim termina sola, watchdog limpio),
  I1=0, throughput vs baseline, ocupacion de muelle y espera-por-slot razonables.
  Barrido (T,C) -> curva de `k`.

### Fase 3 — Camion fisico en puerta(s) de muelle (fidelidad, opcional)
- Camion como agente en la grilla que llega a una/varias puertas outbound, ocupa
  la celda durante `loading_time`, integrado al orden total del time-window.
  Multiples puertas = paralelismo de carga.
- Validar: igual que Fase 2 + el camion no introduce conflictos (I1=0).

### Fase 4 — Escala real (layout + datos) y ventana movil
- SOLO tras Fases 1-3 validadas: construir layout a escala WMS + datos escalados
  (SKUs, ubicaciones, perfiles de orden, puertas, horario de camion). Revalidar
  flujos y **coste del planner**; probablemente detona la VENTANA MOVIL (WHCA*,
  Fase 4 de la Opcion C) por el tamano del espacio-tiempo. Linkea ambas iniciativas.

### Fase 5 — Viewer + limpieza + docs
- Render de pallets en slots y camiones en el viewer; actualizar `AUDITORIA.md`/
  README; decidir consolidacion.

### Regla transversal por fase
1. No-regresion byte-identica con flag off (diff `.jsonl`).
2. Estres: termina, I1=0, watchdog limpio, no-colapso del muelle.
3. Determinismo: doble corrida identica.
4. Evidencia: logs `[OK]` (Ley #4 ASCII) + capturas del viewer.
5. Backup de archivos vivos + commit local por fase.

---

## 7. CASOS BORDE (EXHAUSTIVO)

1. **Muelle lleno permanentemente** (despacho insuficiente): backpressure ->
   agentes en cola -> el watchdog detecta espera-por-slot excesiva y alerta; el
   reporte muestra ocupacion 100% sostenida. No crashea; es diagnostico de mala
   politica, no bug. (Condicion 4.3.)
2. **Camion llega y no hay pallets**: idle del camion; no error.
3. **Pallet parcial / backorder** (Allocation Layer V12.1): un pallet de WO
   parcial (`is_partial`) se deposita igual; el despacho no distingue. Documentar
   si el backorder afecta el conteo de pallets.
4. **Multiples staging con distribucion repartida**: cada zona tiene su propio
   aforo y su propio (o compartido) proceso de camion. El analisis cambia por
   staging; el pico por zona baja al repartir el flujo.
5. **Determinismo con eventos de camion**: T fijo o schedule fijo; sin `set`/`dict`
   no ordenado en la seleccion de pallets.
6. **Pallet en celda que es ruta de paso**: cubierto por la reserva (obstaculo
   dinamico); el planner lo esquiva. Cuidado: si la zona bloquea el unico pasillo,
   puede aislar celdas -> validar conectividad de la zona (no tapar corredores
   criticos). El muelle inferior (y=27,28 libres) deja paso por encima de y=29.
7. **Agente tras depositar**: va a idle/parking; referenciar aforo de parking
   (4.5) para no recrear el apilamiento en el depot.
8. **Zona se queda sin slots Y el agente carga para varias WOs del mismo staging**:
   necesita tantos slots como pallets lleve para ese staging; si no caben, debe
   poder depositar parcialmente y esperar (o reservar varios slots de golpe).
   Decision de diseno a fijar en Fase 1.
9. **Flag off**: comportamiento actual exacto (rotacion infinita); rollback de 1
   linea de config.

---

## 8. RIESGOS, COMPLEJIDAD, ROLLBACK

**Riesgos:**
1. **Reintroducir freeze via muelle lleno** (riesgo central). Mitiga: slot
   reservable (espera del time-window), condicion de no-colapso explicita (4.3),
   watchdog como detector, metricas de saturacion.
2. **Acoplamiento con la Opcion C**: la reserva de dwell abierto + release por
   evento es una extension nueva de `ReservationTable`; probar aislada.
3. **Acoplamiento con la escala**: a mapa grande, el coste del planner crece ->
   ventana movil. Por eso la escala es fase separada y posterior.
4. **Scope**: es un subsistema nuevo (entidades + proceso + eventos + viewer), no
   un parche. Es la mayor expansion de alcance del proyecto hasta ahora.
5. **Determinismo fragil** si entra aleatoriedad sin seed o iteracion no ordenada.

**Complejidad:** ALTA (subsistema nuevo acoplado a la capa de reserva). Por eso
el plan es estrictamente incremental, detras de flag, y separa mecanismo (WH1) de
escala (mapa real).

**Rollback:** por capas. Inmediato: `outbound.enabled=false` => comportamiento
actual. Por fase: commit/tag; revert a la fase anterior. Estructural: las
entidades nuevas gateadas quedan dormidas sin afectar la cadena viva.

---

## 9. PUNTEROS DE CODIGO (anti-alucinacion, Ley #5)

- **Definicion de zona**: `layouts/Warehouse_Logic.xlsx` hoja `OutboundStaging`
  (varias filas por `staging_id`); `data_manager.py::_process_outbound_staging`
  (pasar de `{id:(x,y)}` a `{id:[(x,y),...]}`), `get_outbound_staging_locations`.
- **Entidad Pallet / proceso outbound / config**: `warehouse.py` (clase nueva
  `Pallet`; instanciar `OutboundProcess`; leer `config.json["outbound"]`).
- **Descarga / asignacion de slot / backpressure**: `operators.py` (bucle "V12
  GRANULAR DISCHARGE" ~L852; crear pallet y reservar slot; pedir slot libre al
  planificar el retorno ~L779-835; espera reservada si lleno).
- **Reserva de slot (dwell abierto + release)**: `reservation_table.py`
  (`reserve_dwell` existente; anadir reserva abierta + `release_slot/release_pallet`),
  `spacetime_planner.py` (asignacion de celda destino concreta).
- **Arranque del proceso de camion + eventos**: `event_generator.py`
  (arranque junto al watchdog ~L166; escritura de reporte ~L259).
- **Flag/config**: `config.json` bloque nuevo `"outbound"`; lectura en
  `warehouse.py::AlmacenMejorado.__init__`.
- **Viewer (fase posterior)**: `replay_engine.py` / dashboards (render de
  pallets/camiones a partir de los eventos `pallet_*`/`truck_*`).
- **BUG a resolver si se toca data a escala (Fase 4)**: `Warehouse_Logic.xlsx`
  duplicado entre la RAIZ y `data/layouts/` (`run_migration.py:75`); unificar la
  fuente canonica antes de autorar datos a escala.

---

## 10. RELACION CON LA VISION DE PRODUCTO

Esta iniciativa es la **Capa 2** del roadmap de `docs/VISION_PRODUCTO.md`
(outbound real + aforo + despacho). Desbloquea preguntas de negocio que el twin
debe contestar: cuantas posiciones de muelle, cuantas puertas, que politica de
camion, donde esta el cuello entre picking y expedicion. Y es el forzante natural
de la Capa 3 (escala real) y de la ventana movil de la Opcion C.

> NOTA (Ley #1): este documento es PLAN, no implementacion. Requiere OK del
> Director. Sugerencia de arranque: aprobar Fase 0 + Fase 1 (andamiaje +
> pallets persistentes + zona, sin camion), que ya permite MEDIR el backlog real
> y dimensionar el despacho con datos antes de construirlo.

<!-- FIN_DOCUMENTO -->
