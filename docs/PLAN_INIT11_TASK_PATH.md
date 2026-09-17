# PLAN INIT-11 — Task Path: outbound en varios pasos (v2, detallado)

**Estado:** PROPUESTO — pendiente de aprobacion del Director. NO se toco codigo.
**Fecha:** 2026-09-16 (v2; reemplaza la v1 del mismo dia)
**Directriz del Director:** "tener la mayor cantidad de configuraciones posibles
para asemejarnos a lo que se puede llegar a configurar en un WMS".

---

## 0. RESUMEN EJECUTIVO

El pedido original ("tras pickear, dejar la carga para que otro la lleve a otra
actividad, hasta el staging") se amplio con las respuestas del Director a una
iniciativa de **seis pilares**:

| # | Pilar | En una frase |
|---|---|---|
| P1 | Personas y equipos separados | Una persona puede dejar la grua en un estacionamiento y trabajar a pie |
| P2 | Perfiles con prioridad | Cada persona tiene varios perfiles ordenados; al agotar uno pasa al siguiente |
| P3 | Contenedores y equipos de picking | Se pickea en pallets, totes o cajas; la capacidad depende del equipo |
| P4 | Task Path | Cadena de pasos con puntos de transferencia y estaciones de actividad |
| P5 | Motor de reglas | Que camino, contenedor y equipo usar segun producto, WG, WA, etc. |
| P6 | Politicas de sobrecupo | Esperar, dejar en una ubicacion de sobrecupo o incluso en el pasillo |

Tambien aparecio un **prerrequisito** (F0): el Work Group de cada orden esta
mal calculado hoy, y sin arreglarlo el pilar P5 no puede funcionar.

**Todo es opt-in**: con los bloques ausentes o apagados, la simulacion es
identica a la actual (mismo criterio que INIT-7 recepcion).

**Tamano:** 11 fases (F0 a F10), cada una entregable y validable por separado.
Es la iniciativa mas grande del proyecto hasta ahora (ver seccion 9).

---

## 1. VALIDACION DE LAS RESPUESTAS DEL DIRECTOR

| Decision | Respuesta del Director | ¿Tiene sentido? | Ajuste que sugiero |
|---|---|---|---|
| **D1 — Que viaja entre pasos** | Depende del equipo: en racks se pickea en pallets, en mezanina en totes; un carro lleva varios totes; al conveyor se entrega completo o unidad por unidad segun el tipo | **Si, y es como lo modelan los WMS reales** (LPN/contenedores con capacidad en cantidad, peso y volumen; carros de 4 a 6 contenedores) | Separar 3 conceptos: **tipo de contenedor**, **equipo de picking** (cuantos contenedores lleva) y **regla de entrega** por destino (completo / por contenedor / por caja). Agregar **cartonizacion** simple: elegir el contenedor segun volumen y peso |
| **D2 — Uno o varios caminos** | Estrategias por tipo de producto y por WG/WA | **Si**, es el estandar (Manhattan elige el Task Path por criterios) | Un **motor de reglas generico**: lista ordenada de reglas con condiciones y una regla por defecto obligatoria. Sirve tambien para elegir contenedor y equipo, no solo el camino |
| **D3 — Quien trabaja** | Cada persona con varios perfiles priorizados; el gruero que termina deja la grua en un estacionamiento y hace otra cosa | **Si, y tiene nombre: *task interleaving*** (Blue Yonder, Manhattan) | Requiere **separar persona de equipo** (hoy son lo mismo, ver H1). Y agregar una **regla de cambio de perfil**, porque ir a dejar y buscar la grua cuesta tiempo real (ver P2) |
| **D4 — Sobrecupo** | Opcion de esperar o de dejar en una ubicacion de sobrecupo configurada por punto; en la realidad hasta se deja en el pasillo | **Si, y es un acierto de realismo**: el operario medido por productividad no se queda parado | Politica por punto con **cadena de alternativas** (sobrecupo -> pasillo -> esperar) y **tiempo maximo de espera**. Dejar en el pasillo convierte la carga en un **obstaculo** que molesta al transito: el costo se ve en la congestion |

**Sugerencias propias**, en la linea de la directriz:

- **Prioridad por tipo de tarea**, ademas de por perfil (una reposicion urgente
  antes que un pick).
- **Task interleaving en el viaje**: al volver de dejar una carga, tomar un
  traslado que quede de camino (Blue Yonder lo hace con los grueros). Opcional,
  en una fase posterior.
- **Reposicion (replenishment)** como tipo de tarea: es el trabajo clasico del
  gruero y encaja naturalmente con los perfiles. Queda anotada como extension
  (INIT-12), no entra en este plan.

---

## 2. HALLAZGOS DEL CODIGO QUE CONDICIONAN EL DISENO (verificados)

**H1 — La persona y la maquina son la misma entidad.**
`GroundOperator` y `Forklift` son subclases de `BaseOperator`. El tipo define la
velocidad (`speed_factor_*`), el tiempo de horquilla y, desde BK-06, en que areas
puede trabajar (`work_area_equipment`). Hoy "un gruero que deja la grua" es
imposible de expresar. **Es el cambio mas profundo del plan.**

**H2 — La capacidad del recorrido es solo volumen.**
El despachador llena el recorrido mientras `volumen acumulado <= capacity` y no
supere `max_wos_por_tour`. No existen contenedores.

**H3 — El Work Group esta mal calculado (bug latente).**
`WorkOrder.work_group` esta escrito a mano en el codigo (`'Ground' -> WG_A`,
`'Piso' -> WG_B`, `'Rack' -> WG_C`, resto `WG_A`) e **ignora el Excel**, que si
trae el WG real por ubicacion. Medido el 2026-09-16:

| Area | WG en el Excel | Ubicaciones | WG que usa el motor |
|---|---|---|---|
| Area_Ground | WG_A | 144 | WG_A |
| Area_High | WG_B | 144 | **WG_A (mal)** |
| Area_Special | WG_C | 72 | **WG_A (mal)** |

**216 de 360 ubicaciones (60%) tienen el WG equivocado.** Sin arreglarlo, una
estrategia por WG no puede funcionar.

**H4 — El patron de "carga esperando en un buffer" ya existe.**
La recepcion (INIT-7) tiene cola propia (`putaway_pendientes`), marca de carga
lista (`pallet_ready`), hora de disponibilidad (`tiempo_pallet_listo`, para FIFO
y para medir esperas), tipo de recorrido propio (`tour_type: 'putaway'`),
prioridad configurable (`putaway_priority`) y KPI de espera comparable en A/B.
Se **generaliza**, no se reinventa.

**H5 — La tabla de reservas permite bloquear celdas por intervalo.**
`reservation_table.reserve(cell, t_in, t_out, agent_id)` y `release_agent()`.
Una carga dejada en el pasillo puede modelarse como una reserva abierta con un
identificador propio, liberada cuando alguien la retira. Es la base de P6.

**H6 — Mezaninas y conveyors todavia no existen** (son INIT-10). Este plan
**deja preparados** los conceptos (contenedores, reglas de entrega por destino,
tipos de estacion) pero solo implementa lo que el motor ya tiene: racks,
pallets, carros y estaciones genericas.

---

## 3. LOS SEIS PILARES EN DETALLE

### P1 — Personas y equipos separados

**Modelo.**
- **Persona**: identidad, velocidad a pie, perfiles (P2), habilitaciones (que
  equipos puede manejar).
- **Equipo**: tipo (`grua`, `transpaleta`, `carro`...), velocidad, tiempo de
  horquilla, capacidad (P3), areas donde puede operar.
- **Estacionamiento**: lugares del mapa donde se dejan los equipos, con
  capacidad y tipo de equipo admitido.

**Comportamiento.**
- Una persona trabaja **a pie** o **con un equipo**. Si su proxima tarea requiere
  un equipo que no tiene, va a un estacionamiento a buscarlo; si requiere otro,
  primero deja el que tiene.
- Las areas exigen un **tipo de equipo** (evolucion de `work_area_equipment`);
  la persona debe estar **habilitada** y **llevar** ese equipo.

**Equivalencia con hoy (clave para no romper nada).**
Un grupo de flota sin el bloque nuevo se traduce a "N personas, cada una con su
equipo fijo, sin estacionamientos". Eso reproduce exactamente el comportamiento
actual. **Gate PASS byte-identico obligatorio.**

**Codigo.** `core/fleet.py` (resolver personas y equipos), `operators.py`
(separar atributos de persona y de equipo; logica de tomar/dejar), `warehouse.py`
(estacionamientos), `core/work_areas.py` (compatibilidad por equipo).

### P2 — Perfiles con prioridad (task interleaving)

**Modelo.** Cada persona tiene una **lista ordenada de perfiles**, por ejemplo
`["gruero", "runner", "picker"]`. Cada perfil define que tipos de tarea toma y
con que equipo.

**Comportamiento.** Al terminar cada tarea, la persona recorre sus perfiles en
orden y toma la primera tarea disponible.

**Regla de cambio de perfil** (configurable), porque cambiar cuesta tiempo real:

| Modo | Que hace |
|---|---|
| `inmediato` | Vuelve al perfil principal apenas aparece trabajo |
| `agotar` | Se queda en el perfil actual hasta vaciarlo |
| `umbral` | Solo cambia si hay al menos N tareas pendientes del otro perfil |

**Codigo.** `dispatcher.solicitar_asignacion` pasa a iterar perfiles y a
consultar la cola de cada tipo de tarea. Generaliza el bloque `putaway_priority`.

### P3 — Contenedores y equipos de picking

**Modelo.**
- **Tipo de contenedor**: `pallet`, `tote`, `caja`... con capacidad maxima en
  volumen, peso y cantidad de unidades.
- **Equipo de picking**: cuantos contenedores lleva y de que tipo (una grua lleva
  1 pallet; un carro lleva 6 totes).
- **Cartonizacion simple**: al armar el recorrido, se asignan las lineas a
  contenedores respetando la capacidad; si no entra, se abre otro.
- **Regla de entrega por destino**: como se entrega en cada punto o estacion
  (`completo`, `por_contenedor`, `por_caja`), cada modalidad con su tiempo.
  Asi se modela el costo real de "meter tote por tote" al conveyor.

**Comportamiento.** El recorrido termina cuando se llena el **equipo** (todos
sus contenedores) y no solo por volumen. La unidad que viaja entre pasos es el
**contenedor** (P4).

**Equivalencia con hoy.** Sin el bloque, cada recorrido es "un contenedor
unico con la capacidad del agente": mismo resultado que el volumen actual.

**Codigo.** `dispatcher` (armado del recorrido por contenedores), entidad nueva
`Contenedor` (con su propio estado e identificador, como un LPN).

### P4 — Task Path

**Modelo.** Una **plantilla de camino** es una lista ordenada de pasos:

```
pick      -> deja en PT-A                                  (perfil: picker)
traslado  -> de PT-A a EMPAQUE, entrega por_contenedor     (perfil: runner)
actividad -> EMPAQUE, 30 s por contenedor, 2 puestos        (perfil: packer)
traslado  -> de EMPAQUE a STAGING                          (perfil: runner)
```

- **Punto de transferencia**: ubicacion con capacidad y politica de sobrecupo (P6).
- **Estacion de actividad**: tipo (empaque, consolidacion, control de calidad,
  etiquetado, valor agregado), tiempo por unidad, cantidad de puestos, perfil que
  la opera y regla de entrega.

**Comportamiento.** Cada paso terminado deja el contenedor listo para el
siguiente, que se encola para el perfil correspondiente (generalizacion de H4).

**Codigo.** `dispatcher._asignar_traslado()` (generaliza `_asignar_putaway`),
`operators._execute_traslado_tour()`, proceso SimPy por estacion (recurso con N
puestos).

### P5 — Motor de reglas

**Modelo.** Lista ordenada de reglas. Cada una tiene **condiciones** y una
**accion**; gana la primera que coincide. Regla por defecto obligatoria.

Condiciones disponibles: `clase_manejo`, `work_group`, `work_area`, prioridad
del pedido, destino, cliente. Acciones: plantilla de camino, tipo de
contenedor, equipo de picking.

```json
{"si": {"clase_manejo": ["pesado", "extra_grande"]},
 "entonces": {"camino": "DIRECTO", "contenedor": "pallet", "equipo": "grua"}}
```

**Codigo.** Modulo nuevo `core/reglas.py`, evaluado al liberar cada orden.

### P6 — Politicas de sobrecupo

**Modelo, por punto de transferencia:**

```json
"PT-A": {"capacidad": 6,
         "sobrecupo": {"alternativas": ["PT-A-OVF", "pasillo", "esperar"],
                       "espera_maxima_s": 60}}
```

| Alternativa | Que pasa | Costo que se ve |
|---|---|---|
| Ubicacion de sobrecupo | Se deja en otra ubicacion configurada (que tiene su propia capacidad) | Mas recorrido para el runner |
| `pasillo` | Se deja en la celda transitable mas cercana | **Obstaculo** en la tabla de reservas: frena el transito (H5) |
| `esperar` | El picker espera, hasta `espera_maxima_s`, y despues prueba la siguiente | Tiempo improductivo |

**KPIs propios:** usos de sobrecupo, cargas en pasillo, tiempo de bloqueo y su
efecto en la congestion.

---

## 4. CONFIGURACION COMPLETA (ejemplo)

Todos los bloques son opcionales. Ausentes = comportamiento actual.

```json
"personas": [
  {"id": "Juan", "perfiles": ["gruero", "runner"], "habilitaciones": ["grua"]}
],
"equipos": {
  "grua": {"cantidad": 2, "velocidad": 0.8, "horquilla_s": 8,
           "contenedores": {"tipo": "pallet", "cantidad": 1}},
  "carro": {"cantidad": 4, "velocidad": 1.0,
            "contenedores": {"tipo": "tote", "cantidad": 6}}
},
"estacionamientos": {"EST-1": {"x": 2, "y": 28, "capacidad": 4, "admite": ["grua"]}},
"contenedores": {
  "pallet": {"volumen": 1000, "peso": 800, "unidades": null},
  "tote":   {"volumen": 50,   "peso": 20,  "unidades": 30}
},
"perfiles": {
  "gruero": {"tareas": ["pick"],     "equipo": "grua"},
  "runner": {"tareas": ["traslado"], "equipo": null},
  "packer": {"tareas": ["actividad"], "equipo": null}
},
"cambio_de_perfil": {"modo": "umbral", "umbral": 3},
"task_path": {
  "enabled": true,
  "puntos_transferencia": {"PT-A": {"x": 10, "y": 28, "capacidad": 6,
                                    "sobrecupo": {"alternativas": ["pasillo", "esperar"],
                                                  "espera_maxima_s": 60}}},
  "estaciones": {"EMPAQUE": {"x": 15, "y": 28, "tipo": "empaque", "puestos": 2,
                             "tiempo_por_unidad_s": 30, "perfil": "packer",
                             "entrega": "por_contenedor"}},
  "caminos": {
    "CON_EMPAQUE": [
      {"tipo": "pick", "deja_en": "PT-A"},
      {"tipo": "traslado", "desde": "PT-A", "hasta": "EMPAQUE"},
      {"tipo": "actividad", "en": "EMPAQUE"},
      {"tipo": "traslado", "desde": "EMPAQUE", "hasta": "STAGING"}
    ],
    "DIRECTO": [{"tipo": "pick", "deja_en": "STAGING"}]
  },
  "reglas": [
    {"si": {"clase_manejo": ["pesado", "extra_grande"]},
     "entonces": {"camino": "DIRECTO", "contenedor": "pallet", "equipo": "grua"}},
    {"si": {}, "entonces": {"camino": "CON_EMPAQUE", "contenedor": "tote", "equipo": "carro"}}
  ]
}
```

Toda clave nueva se registra en `src/core/config_schema.py` (MEJ-3). Las
coordenadas se validan contra el mapa, como ya se hace con zonas y muelles.

---

## 5. CAMBIOS POR ARCHIVO

| Archivo | Cambio | Fase |
|---|---|---|
| `warehouse.py` | `WorkOrder.work_group` desde el dato real | F0 |
| `core/fleet.py` | Resolver personas, equipos y equivalencia con la flota actual | F1 |
| `core/work_areas.py` | Compatibilidad area-equipo (en vez de area-agente) | F1 |
| `operators.py` | Separar persona/equipo; tomar y dejar equipo; recorridos de traslado; espera y sobrecupo | F1-F7 |
| `warehouse.py` | Estacionamientos, puntos de transferencia, estaciones | F1, F3, F4 |
| `dispatcher.py` | Perfiles, colas por tipo de tarea, contenedores, `_asignar_traslado` | F2-F5 |
| `core/reglas.py` (nuevo) | Motor de reglas | F6 |
| `reservation_table.py` | Reservas abiertas para cargas en el pasillo | F8 |
| `config_schema.py` | Registrar todas las claves nuevas | Todas |
| `replay_utils.py` + visor | KPIs y visualizacion | F9 |
| Configurador web | Pestanas y editores | F10 |

---

## 6. ESTRATEGIA DE DESARROLLO

### Principios

1. **Opt-in estricto.** Cada fase termina con **GATE PASS byte-identico** con
   todo apagado. La unica excepcion es F0 (ver abajo), que se hace aislada.
2. **Equivalencia antes que funcionalidad.** Cada pilar primero se implementa
   de forma que su configuracion "trivial" reproduzca exactamente el
   comportamiento actual; recien despues se habilita lo nuevo.
3. **Generalizar lo probado.** El buffer de recepcion (H4) es la base; se
   refactoriza para servir a ambos flujos, con tests de la recepcion intactos.
4. **Una fase, un commit, una validacion.** Se entrega y se muestra evidencia
   antes de pasar a la siguiente.

### Orden de las fases y por que

| Fase | Contenido | Depende de | Por que en este lugar |
|---|---|---|---|
| **F0** | Arreglar el Work Group (H3) | — | Bug independiente; cambia el baseline, asi que se hace **solo**, verificando que lo unico que cambie sea ese campo |
| **F1** | Personas y equipos separados, con equivalencia exacta | F0 | Es el cimiento de P2 y el cambio mas riesgoso: conviene hacerlo con todo lo demas quieto |
| **F2** | Perfiles con prioridad + regla de cambio + estacionamientos | F1 | Necesita la separacion persona/equipo |
| **F3** | Task Path basico: pick -> punto de transferencia -> staging | F2 | Necesita perfiles para distinguir picker de runner |
| **F4** | Estaciones de actividad | F3 | Es un paso mas del camino |
| **F5** | Contenedores, equipos de picking, cartonizacion y reglas de entrega | F3 | Cambia la unidad que viaja por el camino |
| **F6** | Motor de reglas (por producto, WG, WA...) | F0, F5 | Elige camino, contenedor y equipo: necesita que existan |
| **F7** | Sobrecupo: esperar + ubicacion de sobrecupo + tiempo maximo | F3 | Politica sobre los puntos de transferencia |
| **F8** | Sobrecupo en el pasillo (obstaculo en la tabla de reservas) | F7 | Toca la capa de congestion: se aisla por ser la mas delicada |
| **F9** | KPIs completos + comparacion A/B | F3-F8 | Mide todo lo anterior |
| **F10** | UI: configuracion y visor | F9 | Con el modelo ya estable, la pantalla no se rehace |

### Puntos de control con el Director

Se propone **mostrar evidencia y pedir OK** al terminar F1, F3, F6 y F8, que son
las fases que cambian el modelo de forma visible. Las demas se reportan al
cerrar.

---

## 7. RIESGOS Y MITIGACIONES

| Riesgo | Mitigacion |
|---|---|
| F1 (separar persona/equipo) rompe comportamientos sutiles | Equivalencia exacta + gate byte-identico antes de agregar nada nuevo |
| F0 cambia el baseline | Hacerlo aislado y verificar que el unico campo que cambia en los eventos es `work_group` |
| La recepcion (INIT-7) se rompe al generalizar su buffer | Sus tests y la demo de cross-dock deben seguir pasando en cada fase |
| F8 (pasillo) introduce bloqueos permanentes en la congestion | Tiempo de vida de la reserva + deteccion de bloqueo con el watchdog existente |
| Alcance que crece sin control | Fases cerradas; lo nuevo que aparezca va al backlog, no a la fase en curso |
| Configuracion demasiado compleja para el usuario | Valores por defecto neutros + plantillas de ejemplo + validacion con mensajes claros (principio rector 3) |

---

## 8. VALIDACION

**En cada fase:**
1. `python -m pytest -q` verde (hoy: 244).
2. `python scripts/regression_gate.py` **PASS byte-identico** con todo apagado.
3. Tests nuevos de la fase.

**Pruebas de equivalencia** (las mas importantes):
- F1: flota actual expresada como personas+equipos -> **mismo `.jsonl`**.
- F3: camino de un solo paso "pick -> staging" -> **mismo resultado** que sin
  Task Path.
- F5: un contenedor unico con la capacidad del agente -> **mismo resultado**.

**Pruebas de comportamiento esperado** (si no pasan, el modelo esta mal):
- Con 1 runner, los puntos de transferencia se llenan y aumenta la espera; con
  mas runners, baja.
- Con 1 puesto de empaque se forma cola; con 2, se reduce.
- Un gruero sin trabajo de grua deja el equipo en el estacionamiento y hace
  traslados; al aparecer trabajo de grua, vuelve segun la regla configurada.
- Con sobrecupo `pasillo`, aumentan las esperas por congestion en esa zona.
- Productos pesados siguen el camino directo; los chicos pasan por empaque.

---

## 9. ESFUERZO

Referencia real del proyecto: la recepcion (INIT-7, 5 fases) tomo unos 3 dias de
trabajo; los tiempos realistas (INIT-8, 4 fases) unos 2.

| Fases | Estimacion |
|---|---|
| F0 | medio dia |
| F1 | 2 a 3 dias (la mas delicada) |
| F2 | 1 a 2 dias |
| F3 + F4 | 2 dias |
| F5 | 2 dias |
| F6 | 1 dia |
| F7 + F8 | 2 dias |
| F9 + F10 | 2 a 3 dias |

**Total: aproximadamente 2,5 a 3,5 semanas de trabajo**, entregable por partes.
Despues de F3 ya hay un flujo de varios pasos funcionando y medible.

---

## 10. DECISIONES MENORES QUE QUEDAN (se pueden resolver en cada fase)

1. ¿Las personas se definen una por una (con nombre) o por grupos ("5 personas
   con estos perfiles")? Sugerencia: **por grupos**, con nombres opcionales.
2. Modo por defecto del cambio de perfil. Sugerencia: **`umbral`** con 3 tareas.
3. Actividades de estacion a incluir de fabrica. Sugerencia: empaque,
   consolidacion, control de calidad, etiquetado y valor agregado.
4. ¿El "pasillo" busca la celda mas cercana o una celda de pasillo marcada? 
   Sugerencia: **la mas cercana transitable que no este reservada**.

---

## Fuentes

- Task interleaving (definicion): https://sgsystemsglobal.com/glossary/task-interleaving/
- Blue Yonder WMS (interleaving, habilidades y equipos): https://concentrus.com/blue-yonder-wms/
- Tipos de LPN y contenedores: https://racklify.com/encyclopedia/types-of-lpns-and-how-lpn-relates-to-sku-sscc-and-serial-numbers/
- Oracle, cartonizacion y consolidacion (carros de 4 a 6 contenedores): https://docs.oracle.com/cd/E18727_01/doc.121/e13433/T211976T430469.htm
- Infor WMS, configuracion de cartonizacion: https://docs.infor.com/wms/2023.x/en-us/useradminlib/sceconfigug/vrf1612894175905.html
- Infor WMS, Pick and Drop: https://docs.infor.com/wms/2022.x/en-us/useradminlib/scepadug/net1612893806986.html
- Oracle WMS Cloud, Task Zone Movement: https://docs.oracle.com/en/cloud/saas/warehouse-management/23c/owmol/task-zone-movement-rule.html
- Manhattan WMOS (task paths, task groups): https://www.maxmunus.com/page/Manhattan-WMS-Training
