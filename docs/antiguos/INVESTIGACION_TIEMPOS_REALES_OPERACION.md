# INVESTIGACION — TIEMPOS REALES DE OPERACION DE ALMACEN (calibracion del simulador)

> Documento de INVESTIGACION + ANALISIS. No implementa nada. Su proposito es
> servir de FUENTE DE VERDAD para calibrar los tiempos del simulador
> (config.json y constantes del motor), de modo que las estadisticas (makespan,
> throughput, utilizacion, esperas) representen una operacion real.
> Redactado: 2026-06-10. Fuentes al final. Convenciones: ASCII.

---

## 1. COMO ESTA EL SIMULADOR HOY (radiografia, verificada en codigo)

| Parametro | Donde | Valor actual | Significado |
|---|---|---|---|
| `TIME_PER_CELL` | operators.py L763/L1169 (constante local x2) | 0.1 s/celda | tiempo base de moverse 1 celda |
| `default_speed` Ground | operators.py L746 | 1.0 | multiplicador de TIEMPO (0.1 s/celda) |
| `default_speed` Forklift | operators.py L1150 | 0.8 | 0.08 s/celda (MAS RAPIDO que Ground) |
| `tiempo_descarga_por_tarea` / `discharge_time` | config.json | 5 s | se usa para PICKING y para DESCARGA |
| `picking_duration` | operators.py L912/L1327 | = discharge_time | el picking dura lo mismo que descargar |
| `LIFT_TIME` (horquilla) | operators.py L1170 | 2.0 s | subir o bajar horquilla (Forklift) |
| `outbound.dwell_scaffold` | config.json | 10 s | vida del pallet en el muelle (scaffold F1) |
| `outbound.truck_interval` | config.json | 20 s | cada cuanto llega camion (Fase 2) |
| `outbound.truck_capacity` | config.json | 8 pallets | capacidad del camion |
| `outbound.loading_time` | config.json | 2 s | carga del camion completa |
| `_outbound_nav_to` | operators.py L632 | 0.1 s/celda fijo | movimiento dentro del muelle |

Hallazgos importantes:
1. **No hay escala espacial definida.** Ninguna parte del codigo declara cuantos
   metros mide una celda. Es el prerequisito de TODO lo demas.
2. **Velocidad ~10x la real.** Si 1 celda ~ 1 m, hoy un operario "camina" a
   10 m/s (36 km/h). Real: ~1.0-1.2 m/s efectivo en picking.
3. **Comentario invertido en Forklift.** L1165 dice "Velocidad mas lenta
   (default_speed = 0.8)" pero el 0.8 multiplica al TIEMPO -> el montacargas es
   MAS RAPIDO. Direccionalmente esta bien (un montacargas ES mas rapido que un
   peaton), pero el comentario confunde y el ratio real es mayor (ver 3.1).
4. **Picking y descarga comparten constante** (5 s). En la realidad son
   operaciones distintas con tiempos distintos.
5. **El camion de Fase 2 (T=20s, carga 2s) es ~100x mas rapido que uno real.**

---

## 2. ESCALA ESPACIAL PROPUESTA (decision previa)

Los racks del layout son celdas individuales con pasillos de 1 celda. En un
almacen real: modulo de rack ~2.7-3.0 m de frente (3 pallets), profundidad
~1.1 m, pasillo de montacargas contrapesado ~3.5-4.0 m, pasillo de pallet jack
~2.4-3.0 m. La celda del simulador mezcla esos conceptos; la convencion mas
practica y defendible es:

> **1 celda = 1.0 m, 1 segundo de simulacion = 1 segundo real.**

Es la misma convencion de la literatura de simulacion de picking (agentes a
1 celda/s ~ 1 m/s). Mapa WH1 v2 (30x42) => almacen de 30 m x 42 m = 1,260 m2
(bodega chica/mediana, coherente con 7 muelles abajo).
Alternativa: 1 celda = 1.5 m (almacen de 45x63 m); todos los tiempos de viaje
escalan x1.5. ELEGIR UNA y documentarla en config (`cell_size_m`).

---

## 3. BENCHMARKS REALES (investigacion, con fuentes)

### 3.1 Velocidades de desplazamiento

| Recurso | Real (rango) | Tipico para simular | Nota |
|---|---|---|---|
| Operario a pie picking (con carro, paradas) | 0.7 - 1.2 m/s | **1.0 m/s** | estudios de simulacion usan 0.7-1.0 m/s |
| Operario caminata pura sin carga | 1.3 - 1.4 m/s | 1.3 m/s | techo, no sostenible picando |
| Pallet jack electrico (walkie, a pie) | 4.8 - 6.4 km/h = 1.3-1.8 m/s | **1.5 m/s** | va al paso del operario |
| Pallet jack rider (montado) | 9 - 14 km/h cargado/vacio | 2.5 m/s | si se modela rider |
| Montacargas en pasillo/zona mixta | 5 - 8 km/h = 1.4-2.2 m/s | **2.0 m/s** | limite seguro tipico interior |
| Montacargas pasillo abierto sin peatones | 8 - 12 km/h = 2.2-3.3 m/s | 2.8 m/s | maximo razonable interior |

Ratio Forklift/Ground REAL: el montacargas viaja ~2x mas rapido que el operario
(no 1.25x como el 0.8 actual). Multiplicador de tiempo correcto: **~0.5**.

### 3.2 Picking (tomar el item/caja del rack)

| Concepto | Real | Nota |
|---|---|---|
| Tasa global case-picking (incluye viaje) | 80 - 150 lineas/hora | B2B pesado: 40-70 |
| Tasa global each-picking (incluye viaje) | 60 - 120 lineas/hora | ecommerce manual |
| **Tiempo FIJO por linea (sin viaje)**: identificar, alcanzar, tomar, colocar en carro, confirmar/escanear | **10 - 20 s** caja estandar | MTM: alcance+agarre ~5 s/item + confirmacion 5-7 s; cajas pesadas o altas: 20-30 s |
| Pallet completo desde piso (montacargas) | 15 - 30 s | insertar horquilla, elevar, salir |
| Pallet desde rack alto (montacargas) | 30 - 90 s | posicionamiento + elevacion (ver 3.3) |

Cifra de control: con viaje promedio de 25 m a 1 m/s (25 s) + pick fijo 15 s
= 40 s/linea = 90 lineas/hora -> cae EXACTO en el benchmark global. Coherente.

### 3.3 Montacargas: horquilla y manejo de pallet

| Operacion | Real | Actual sim |
|---|---|---|
| Subir/bajar horquilla a nivel bajo (<2 m) | 5 - 10 s | LIFT_TIME=2 s |
| Posicionar + tomar pallet de rack medio/alto | 20 - 45 s el ciclo completo | 2+5+2 = 9 s |
| Depositar pallet en piso (staging) | 10 - 20 s | 5 s |
| Velocidad de elevacion tipica | 0.3 - 0.5 m/s | n/a |

### 3.4 Empaque (packing) — HOY NO EXISTE en el simulador

| Concepto | Real |
|---|---|
| Orden ecommerce simple (1-3 items, caja estandar) | 30 - 90 s/orden |
| Solo documentacion/etiqueta tras escanear | 5 - 12 s |
| Embalaje custom (inserto, doble cinta) | +8 - 12 s/orden |

Si se agrega estacion de empaque al flujo (entre picking y staging), estos son
los tiempos. Por ahora, referencia para una fase futura.

### 3.5 Carga / descarga de camion (muelle)

| Concepto | Real | Para el sim (Fase 2) |
|---|---|---|
| Capacidad trailer 53 ft (USA) | 26 pallets sin estibar / 52 a doble altura | `truck_capacity: 26` |
| Capacidad trailer europeo 13.6 m | 33 europallets | alternativa: 33 |
| Cargar trailer completo con montacargas (live load) | 30 - 45 min | -> **~75-90 s por pallet** |
| Por pallet individual (montacargas dock-trailer) | 60 - 120 s | `loading_time` |
| Turnaround total del camion en puerta (docking, papeles, carga, salida) | 45 - 90 min | `truck_interval` >= 2700 s si hay 1 puerta |
| Descarga de trailer (a piso/staging) | 20 - 40 min | simetrico a la carga |

### 3.6 Distribucion del tiempo de un picker (sanity check global)
Regla de oro de la industria: el operario de picking pasa ~50-60% del turno
VIAJANDO, ~15-25% buscando/tomando, el resto en tareas auxiliares. Tras
calibrar, las estadisticas del simulador (Tiempo_Viaje vs Tiempo_Picking del
reporte Excel) deberian aproximarse a esa proporcion: es el TEST DE REALISMO.

---

## 4. PROPUESTA DE CALIBRACION (mapeo directo a parametros)

Con la convencion 1 celda = 1 m, 1 s sim = 1 s real:

| Parametro | Hoy | Propuesto | Justificacion |
|---|---|---|---|
| `TIME_PER_CELL` (Ground) | 0.1 s | **1.0 s** | 1.0 m/s picking a pie (3.1) |
| `default_speed` Ground | 1.0 | 1.0 | queda como multiplicador neutro |
| `default_speed` Forklift | 0.8 | **0.5** | montacargas 2.0 m/s = 2x peaton (3.1); CORREGIR comentario L1165 |
| `picking_duration` | =discharge (5 s) | **separar**: `tiempo_picking_por_linea: 15 s` | 3.2; HOY el codigo no distingue: cambio de codigo menor |
| `discharge_time` (dejar caja/pallet en staging) | 5 s | **12 s** Ground (caja a piso) / **15 s** Forklift (pallet a piso) | 3.3 |
| `LIFT_TIME` | 2 s | **8 s** | elevacion real a nivel bajo-medio (3.3) |
| `outbound.dwell_scaffold` | 10 s | n/a | desaparece con Fase 2 (camion real) |
| `outbound.truck_capacity` | 8 | **26** | trailer 53 ft (3.5) |
| `outbound.loading_time` | 2 s | **90 s POR PALLET** -> 26 pallets ~ 40 min | 3.5; OJO: hoy es carga TOTAL, el plan F2 debe decidir si es por-pallet (recomendado) |
| `outbound.truck_interval` | 20 s | **3600 s** (1 camion/hora/puerta) | 3.5 turnaround + colchon |
| `cell_size_m` (NUEVO) | no existe | **1.0** | documentar la escala (seccion 2) |

### 4.1 Consecuencias practicas (que esperar al calibrar)
- La simulacion del escenario web (150 ordenes, 4 agentes) pasara de ~25 min
  simulados a varias HORAS simuladas (turno realista). El motor headless lo
  genera igual de rapido (eventos discretos); el REPLAY necesitara velocidades
  10x-60x (el selector hoy llega a 10x: agregar 30x/60x es trivial).
- El equilibrio de Fase 2 cambia de escala: deposito real con 4 agentes
  ~ 2-4 pallets/min los picos; camion de 26 pallets cada 60 min = 0.43/min
  sostenido => el STAGING AMORTIGUA rafagas, exactamente el fenomeno real que
  el Director quiere observar (backlog, ocupacion del muelle, esperas).
- Los KPI del reporte Excel (Tiempo_Viaje, Tiempo_Picking, utilizacion) pasan
  a ser comparables con benchmarks de la industria (3.6) y defendibles ante
  un cliente.

### 4.2 Cambios de codigo que la calibracion REQUIERE (no son solo config)
1. `TIME_PER_CELL` esta HARDCODEADO en 3 sitios (L763, L1169, L632) -> debe
   leerse de config (`time_per_cell` o derivado de `cell_size_m` y velocidad).
   Ley #3: config.json unica fuente de verdad.
2. Separar `tiempo_picking_por_linea` de `discharge_time` (hoy comparten).
3. `LIFT_TIME` hardcodeado -> a config.
4. Corregir comentario invertido del Forklift y recalibrar a 0.5.
5. (Fase 2) `loading_time` definir como POR PALLET.
6. Exponer en el configurador web (pestania nueva "Tiempos" o en Motor
   Avanzado) los tiempos clave, con los valores de esta tabla como defaults.

### 4.3 Perfil alternativo "rapido" (para demos)
Mantener un preset con los valores actuales (rapidos, irreales) como
"modo demo" — util para ensenar el producto sin esperar; el merge del
configurador ya permite presets sin riesgo.

---

## 5. LIMITACIONES DE ESTA INVESTIGACION
- Rangos de fuentes publicas de la industria (consultoras, fabricantes,
  estandares MTM/MOST publicados, papers); una operacion concreta del cliente
  puede diferir — los parametros quedan en config justamente para eso.
- El tiempo fijo por linea (10-20 s) es el numero con mas varianza (depende de
  peso, altura del slot, confirmacion por scanner vs voz). Si el Director tiene
  acceso a UNA operacion real, 1 hora de cronometro vale mas que esta tabla
  para ese item (plantilla de medicion: viaje / buscar / tomar / confirmar).
- Empaque (3.4) documentado pero fuera del flujo actual del simulador.

## 6. FUENTES
- Velocidad de pickers en simulacion academica (0.7-1.0 m/s):
  arxiv.org/pdf/2408.01656 (Deep RL for Dynamic Order Picking),
  arxiv.org/pdf/1909.01794 (e-commerce warehouses).
- Tasas de picking por industria: cognitops.com (Warehouse Pick Rate
  Benchmarks), fhiworks.com (Cases Per Hour Benchmarks), explorewms.com
  (labor for picking and packing), getproductiv.com (pick rate benchmarks).
- Estandares de tiempo predeterminados (MTM/MOST, ~5 s/item + confirmacion):
  strategosinc.com (Warehouse Picking Time Standards), cronometras.com
  (MTM and MOST in logistics), logisticsviewpoints.com (Predetermined Time
  Systems), sugoyaindia.com (MTM / MOST).
- Velocidades de montacargas y limites seguros (8-12 km/h max interior, 5-8
  km/h zonas mixtas; OSHA sin limite fijo): conger.com/forklift-speed,
  osha.gov (interpretacion 2004-11-04), certifyme.net, claitec.com.
- Pallet jacks (walkie 3-4 mph, rider 6-9 mph): toyotaforklift.com (Electric
  Pallet Jack FAQ), raymondcorp.com (8410 Pallet Truck), eqdepot.com.
- Carga de trailer (53 ft ~26 pallets; carga completa ~30-45 min):
  northwesttrailer.com, cowtownlogistics.com, answers.com (load time),
  inventoryops.com (Trailer Loading Techniques).
- Empaque (5-7 s documentos; 8-12 s extra por embalaje custom; 30-90 s/orden):
  peoplevox.com (quickest packing method), customlogothing.com,
  alexanderjarvis.com (Packing Time per Order), shiphero.com.
