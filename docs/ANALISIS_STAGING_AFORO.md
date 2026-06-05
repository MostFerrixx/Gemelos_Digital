# ANALISIS DE AFORO DEL STAGING / MUELLE  (Iniciativa #2 - Opcion A)

> INVESTIGACION + analisis de diseno. NO contiene implementacion (Ley #1).
> Pregunta a responder con DATOS: bajo el modelo "1 pallet por celda"
> (capacidad 1 por posicion de staging), hay que AMPLIAR el layout del muelle
> para que quepan todos los pallets, y cuanto?
>
> Rama: `feature/allocation-layer-v12.1`. Escenario de medicion:
> `config_stress_tw_exec.json` (timewindow, 20 agentes, layout real WH1,
> ordenes `uploads/orders_test_sandbox.json`, modo determinista).
> Todo lo de abajo esta VERIFICADO leyendo el codigo/datos y corriendo la sim,
> no supuesto.

---

## CHECKLIST DE REDACCION
- [x] 1. Geometria actual del staging/muelle (TMX + data_manager)
- [x] 2. Demanda de pallets (corrida determinista: total + pico simultaneo)
- [x] 3. Existe rotacion / despacho?
- [x] 4. Calculo de dimensionamiento (sin rotacion vs con rotacion)
- [x] 5. Recomendacion de diseno (sin implementar)
- [x] 6. Resumen ejecutivo

---

## 1. GEOMETRIA ACTUAL DEL STAGING / MUELLE

### 1.1 De donde sale la ubicacion del staging (la verdad del codigo)
La ubicacion de los staging NO la define el tipo de tile del TMX, sino la hoja
`OutboundStaging` de `layouts/Warehouse_Logic.xlsx`, leida por
`src/subsystems/simulation/data_manager.py::_process_outbound_staging`
(`get_outbound_staging_locations()` -> `{staging_id: (x,y)}`).

Contenido real de esa hoja (verificado):

| staging_id | x | y |
|-----------:|--:|--:|
| 1 | 3 | 29 |
| 2 | 7 | 29 |
| 3 | 11| 29 |
| 4 | 15| 29 |
| 5 | 19| 29 |
| 6 | 23| 29 |
| 7 | 27| 29 |

Hay **7 posiciones de staging definidas**, todas en la ultima fila `y=29`
(el muelle inferior), separadas cada 4 celdas en X.

### 1.2 (3,29) es unica o parte de una zona?
Cada staging es **UNA sola celda de grilla**. No hay concepto de "zona de
aforo": cada `staging_id` es un unico punto `(x,y)`. El `DepotPoint` del TMX
(objeto Logistics en pixel `113.33, 940` ~= celda `(3,29)`) coincide con el
staging 1 y se usa como depot por defecto en `operators.py`
(`staging_locs.get(1, (3,29))`).

**Punto clave del escenario de prueba:** `config_stress_tw_exec.json` trae
`"outbound_staging_distribution": {"1": 100, "2":0, ... "7":0}`. Es decir, el
**100% de las WorkOrders se enrutan al staging 1 = celda (3,29)**. Los otros 6
stagings existen pero reciben 0% -> en la practica TODO el flujo converge en
**una unica celda**. Ese es el embudo descrito en `PROGRESO_OPCION_C.md`.

### 1.3 Geometria del muelle y espacio libre para ampliar
Mapa WH1: grilla `30 x 30`, tile 32px. Walkability por tipo de tile
(rack = NO caminable; floor/picking/parking/depot/inbound = caminable).

Estructura vertical (verificada parseando el CSV del TMX):
- `y=0`: parking/depot (fila de estacionamiento/arranque).
- `y=1,2`: pasillo horizontal superior (floor, 30 celdas caminables).
- `y=3..26`: campo de racks + pasillos de picking (patron
  `rack,pick,pick,rack,...`); cada fila tiene 15 celdas caminables y 15 racks.
- `y=27`: **pasillo inferior, 30/30 caminable (floor).**
- `y=28`: **pasillo inferior, 30/30 caminable (floor).**
- `y=29`: **fila de muelle, 30/30 caminable** (floor + las 14 celdas tile
  "inbound" donde se posan los 7 staging en x=3,4,7,8,...).

=> El **bloque inferior `y=27,28,29` son 90 celdas contiguas, TODAS
caminables y hoy practicamente vacias** (solo se usan de paso). Es espacio
libre inmediato alrededor de (3,29) para construir una zona de aforo SIN
agrandar el mapa: hacia arriba (y=28, y=27) y a los lados (x=0..5 estan libres;
el siguiente staging esta en x=7, deja 2-3 celdas de holgura entre clusters).

Resumen geometria: hoy el staging activo es **1 celda** (3,29); el muelle
fisico disponible para convertirlo en zona es de hasta **90 celdas libres
contiguas** (3 filas x 30) sin tocar racks ni ampliar el TMX.

---

## 2. DEMANDA DE PALLETS (corrida determinista de referencia)

### 2.1 Escenario y ordenes
- Config: `config_stress_tw_exec.json` (20 agentes: 14 GroundOperator + 6
  Forklift; modo timewindow ejecucion).
- Ordenes: `uploads/orders_test_sandbox.json` -> **40 ordenes, 120 lineas de
  item (SKU), 1440 unidades totales**. (El `total_ordenes:150` del config se
  ignora en modo deterministic: se lee el archivo.)

### 2.2 Que es "un pallet" aqui?
En el modelo NO existe un objeto "pallet" persistente. La unidad atomica de
deposito es la **WorkOrder**: cada WO = mover la cantidad de UN SKU desde su
rack hasta el staging. La descarga es **granular por WO**
(`operators.py`, bucle "V12 GRANULAR DISCHARGE": un `env.timeout(discharge_time)`
por WO, con `discharge_time = 5 s`). Una WO puede agregar varias unidades del
mismo SKU, pero un cliente (orden) con varias lineas genera varias WOs.

=> La lectura mas fiel es **1 WorkOrder = 1 deposito = 1 "pallet"**
(un bulto/unidad de carga puesto en el muelle). Una orden multi-linea deposita
varios pallets.

### 2.3 Cifras medidas (corrida instrumentada, sim_end_t = 268 s)
| Metrica | Valor |
|---|---|
| WOs depositadas (staged) en el staging | **126** |
| Ubicacion de TODAS ellas | (3,29) (staging 1, 100% distribucion) |
| Tiempo de descarga por WO | 5 s |
| Tiempo total de ocupacion-descarga en (3,29) | 630 agente-segundo |
| Ocupacion media continua de (3,29) | ~2.35 agentes |
| **PICO de agentes DESCARGANDO a la vez en (3,29)** | **6** (en t~177.5) |
| Pico de agentes PRESENTES (cualquier estado) en (3,29) | **8** (max_concurrent del CongestionManager) |

(126 WOs concuerda con el throughput=126 ya registrado en
`PROGRESO_OPCION_C.md` para esta misma config.)

Interpretacion: a lo largo de la corrida **se depositan 126 pallets**, pero
nunca hay mas de **6 descargando simultaneamente** (hasta 8 presentes contando
los que esperan/pasan) sobre esa unica celda. Ese apilamiento de 6-8 sobre 1
celda es exactamente la causa del I1!=0 documentado en la Fase 2/2b.

---

## 3. EXISTE ROTACION / DESPACHO?

**NO.** Verificado leyendo `operators.py`, `warehouse.py`, `dispatcher.py` y
`order_strategies.py`:

1. **No hay evento de expedicion / carga a camion.** El unico "ship" del
   codigo es `fulfillment_policy = "ship_partial"`, que es la politica de
   surtido PARCIAL de lineas de orden (cuanto stock se asigna), NO un evento
   fisico de salida de mercancia. No existe camion, ni cola de outbound, ni
   liberacion temporizada del muelle.

2. **Tampoco hay acumulacion fisica de pallets.** Esto es lo sutil: cuando un
   agente llega al staging, pone `status="unloading"`, gasta `discharge_time`
   por WO, marca la WO como `staged` (terminal) y **se va**. La mercancia
   "desaparece" del modelo; no queda ningun objeto ocupando la celda despues
   de que el agente se retira.

=> El staging hoy es un **punto de servicio transitorio**, no un buffer. Se
comporta como si tuviera **rotacion instantanea e infinita**: la posicion se
libera en el instante en que el agente termina de descargar y se aleja. Por eso
"cuantos pallets hay en el staging" hoy = "cuantos agentes estan descargando en
ese instante" (pico 6), y NO 126.

Esto es justo lo que rompe el realismo que busca la Opcion A: el modelo actual
ni acumula (irreal: la mercancia no se evapora) ni despacha (no hay camion).
Para modelar "1 pallet por celda" hay que decidir QUE de estas dos realidades
se introduce.

---

## 4. CALCULO DE DIMENSIONAMIENTO ("1 pallet por celda")

Celdas de staging hoy en uso efectivo: **1** (la (3,29)).
Celdas de staging definidas (con 0% de flujo): 7.
Espacio libre contiguo en el muelle inferior (y=27-29): **90 celdas**.

### Escenario (a) - SIN rotacion (acumulacion total hasta fin de corrida)
Si cada pallet depositado PERMANECE en su posicion hasta el final (no hay
camion que lo retire), se necesita **1 posicion por cada pallet de la corrida**:

> **Posiciones necesarias (a) = 126**  (= total de WOs depositadas)

Comparacion: 126 posiciones **NO caben** en las 90 celdas libres del muelle
inferior, y mucho menos en 1. Habria que comerse los pasillos de picking o
**agrandar fisicamente el TMX** (anadir filas de muelle). Conclusion dura:
**la acumulacion total es inviable en el footprint actual**; ademas es poco
realista (un muelle real expide). Este escenario, por si solo, queda descartado.

### Escenario (b) - CON rotacion (dimensionar al pico simultaneo)
Si hay despacho/rotacion que retira pallets, basta cubrir el numero maximo de
pallets presentes a la vez:

> **Posiciones necesarias (b) = pico simultaneo = 6**
> (margen recomendado a 8, que es el pico de agentes PRESENTES en la celda).

Comparacion: **6-8 posiciones caben holgadamente** en el muelle inferior (90
celdas libres). No hay que agrandar el mapa; basta declarar una zona de
~8 celdas alrededor de (3,29).

### Sensibilidad
- El pico (6) y el total (126) escalan con la flota y las ordenes. Con 20
  agentes y 100% del flujo a un solo staging, el pico de 6 es estable
  (lo limita el embudo de aproximacion al muelle, no la celda). Si se repartiera
  el flujo entre los 7 stagings, el pico por staging bajaria (~1-2 c/u).
- discharge_time=5s: bajarlo reduce ocupacion media (630 ag-s) pero no el pico
  de aproximacion; subirlo si elevaria el pico.

---

## 5. RECOMENDACION DE DISENO (sin implementar)

Hay tres palancas; la pregunta del Director ("hay que ampliar el muelle y
cuanto") se responde combinando dos de ellas.

### (i) Ampliar el muelle a N posiciones (zona de aforo en el TMX/definicion)
- **Que**: dejar de tratar el staging 1 como 1 celda y declararlo un CLUSTER de
  k celdas caminables. NO hace falta agrandar el mapa: caben en el bloque libre
  y=27-29. Ejemplo de cluster de **8** alrededor de (3,29):
  `(2,29),(3,29),(4,29),(5,29)` + `(2,28),(3,28),(4,28),(5,28)` (2 filas x 4),
  dejando x=6 como holgura antes del staging 2 (x=7).
- **Pros**: hace honesto el "1 pallet por celda" para el pico (6 caben en 8);
  elimina el apilamiento sobre 1 celda (causa del I1!=0); barato en layout.
- **Contras**: por si solo NO resuelve la acumulacion (si no hay rotacion, 8
  posiciones se llenan y el sistema se serializa). Solo dimensiona el pico.
- **Toca**: definicion de zona de staging (hoy 1 punto en la hoja
  `OutboundStaging` / `data_manager`); logica de asignacion de posicion en
  `operators.py` (elegir una celda LIBRE del cluster al llegar, en vez de ir
  siempre a `staging_location` fija); reserva del dwell AL PLANIFICAR para que
  el planner serialice cuando el cluster este lleno (esto es exactamente la
  "Opcion A (RECOMENDADA)" ya esbozada en `PROGRESO_OPCION_C.md`, Fase 2b).

### (ii) Anadir despacho/rotacion que libere posiciones
- **Que**: un evento de salida (camion/outbound) que retira pallets del muelle
  cada cierto tiempo o por lote, liberando posiciones.
- **Pros**: es lo que hace realista el muelle; permite aforo pequeno (8) aun
  con 126 pallets totales; modela el throughput real de expedicion.
- **Contras**: anade un subsistema nuevo (cola outbound, politica de camion);
  mas piezas que parametrizar y validar; si la frecuencia de camion es baja, el
  buffer requerido sube por encima del pico de descarga.
- **Toca**: un proceso SimPy nuevo en `warehouse.py`/`dispatcher.py` que
  consuma pallets `staged` y libere su celda; un estado/objeto "pallet en
  muelle" persistente (hoy no existe).

### (iii) Combinacion (i)+(ii)  <-- RECOMENDADA
- Zona de **k = 8 posiciones** (cubre el pico 6 con margen) **mas** un mecanismo
  de rotacion que vacie el muelle. Es la unica opcion **fiel y robusta**:
  - La zona de 8 hace fisico el "1 pallet por celda" para la concurrencia real.
  - La rotacion evita el absurdo de 126 posiciones y modela la expedicion.
  - Juntas dan I1=0 honesto sin colapsar el throughput (cuando la zona se llena
    porque el camion tarda, el planner espera-reservando: serializa de forma
    realista, no por bug).

### Respuesta directa a "hay que ampliar el muelle, y cuanto?"
- **Fisicamente (TMX), NO hace falta agrandar el mapa.** Hay 90 celdas libres
  contiguas en y=27-29; la zona cabe ahi.
- **Logicamente, SI: el staging debe pasar de 1 celda a ~8 posiciones** para ser
  honesto con "1 pallet por celda" al pico medido (6 simultaneos, 8 presentes).
- **126 posiciones (acumulacion total) es inviable y se descarta**: la via
  realista no es poner 126 huecos, sino zona de ~8 + rotacion que despache.
- Cifra concreta recomendada: **zona de 8 posiciones (2 filas x 4) anclada en
  (3,29)** + evento de despacho. Si se quiere margen para repartir el flujo o
  subir la flota, los 7 stagings x ~8 = hasta 56 posiciones caben aun en el
  muelle inferior sin ampliar el TMX.

### Que NO tocar (recordatorio de arquitectura)
- `config.json` sigue siendo la unica fuente de verdad (la distribucion y el k
  de la zona se configuran ahi; la geometria, en la hoja OutboundStaging).
- No reintroducir live-sim; el despacho seria otro proceso headless -> .jsonl.

---

## 6. RESUMEN EJECUTIVO

- **Geometria hoy**: 7 stagings de **1 celda** cada uno en `y=29`; el escenario
  manda **100% a (3,29)** -> embudo de 1 sola celda. Muelle inferior (y=27-29)
  = **90 celdas libres contiguas** disponibles para ampliar sin tocar el mapa.
- **Demanda (corrida determinista, 20 agentes, 40 ordenes)**: **126 pallets
  (WOs)** depositados; **pico simultaneo = 6** descargando (8 presentes).
  1 WO = 1 pallet; las ordenes multi-linea depositan varios.
- **Rotacion**: **NO existe**. Tampoco acumulacion fisica: el staging es un
  punto de servicio transitorio con "rotacion instantanea" implicita (el agente
  descarga y se va, la mercancia se evapora). No hay camion ni buffer.
- **Dimensionamiento "1 pallet/celda"**:
  - (a) sin rotacion = **126 posiciones** -> NO caben en 90; **inviable**.
  - (b) con rotacion = **6 (recomendado 8) posiciones** -> caben de sobra.
- **Recomendacion**: zona de aforo de **~8 posiciones** anclada en (3,29)
  (cabe en el muelle actual, sin agrandar el TMX) **+** un mecanismo de
  despacho/rotacion. Es la combinacion fiel y robusta; la acumulacion pura se
  descarta. Cambios futuros (no en este doc): definicion de zona en
  OutboundStaging/data_manager, asignacion de celda libre + reserva de dwell al
  planificar en operators.py, y un proceso de expedicion en warehouse/dispatcher.

<!-- FIN_DOCUMENTO -->
