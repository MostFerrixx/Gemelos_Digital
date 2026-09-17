# PLAN INIT-11 — Task Path: descomponer el outbound en pasos

**Estado:** PROPUESTO — pendiente de aprobacion del Director. NO se toco codigo.
**Fecha:** 2026-09-16
**Pedido del Director:** "descomponer las tareas de outbound en distintos pasos:
tras pickear, dejar lo pickeado en un lugar para que lo tome otro usuario que
tiene asignado ese tipo de tarea, lo lleve a otra parte para que hagan una
actividad, y asi sucesivamente hasta llegar al outbound staging."

---

## 1. Como se llama esto

| Sistema | Nombre |
|---|---|
| **Manhattan WMOS** | **Task Path** (la secuencia de tramos de una tarea) + **Task Groups** (que usuario puede hacer que tipo de tarea) |
| Infor WMS | Pick and Drop (P&D) |
| Oracle WMS Cloud | Task Zone Movement (con drop zones) |
| Nombre generico | Multi-step picking, pick-and-pass, relay picking |

La ubicacion intermedia donde se deja la carga se suele llamar **P&D location**
(pickup & drop) o **drop zone**. En este plan: **punto de transferencia**.

---

## 2. Como funciona HOY (verificado en el codigo)

Un solo tramo. El operario:

1. pide un recorrido al despachador (`dispatcher.solicitar_asignacion`);
2. pickea todas las ordenes del recorrido (`_execute_pick_tour`);
3. va **directo** a la zona de salida y descarga (`determinar_staging_destino`,
   `_tiempo_descarga_final`).

Estados de una orden de trabajo: `released -> assigned -> in_progress ->
picked -> staged -> shipped`.

No existe ningun paso intermedio, ninguna actividad entre el pick y la salida,
ni la idea de que distintas personas hagan distintas partes del trabajo.

---

## 3. HALLAZGO: el patron ya existe en el motor (para la recepcion)

La recepcion de mercaderia (INIT-7) ya resuelve exactamente la mecanica de un
tramo con transferencia:

| Pieza de INIT-7 | Que hace | Equivalente en el Task Path |
|---|---|---|
| `putaway_pendientes` | Cola propia de tareas, separada de los picks | Cola por cada tramo |
| `pallet_ready` | La carga ya esta en el buffer y se puede tomar | La carga llego al punto de transferencia |
| `tiempo_pallet_listo` | Cuando quedo lista: FIFO y medicion de espera | Igual |
| `tour_type: 'putaway'` | Tipo de recorrido propio en el operario | `tour_type: 'traslado'` |
| `putaway_priority` | Quien manda cuando la flota es compartida | Igual, por tramo |
| KPI `avg_putaway_wait` | Cuanto espera la carga en el buffer, comparable en A/B | Espera en cada punto de transferencia |

**No hay que inventar la mecanica: hay que generalizarla.** Eso reduce mucho el
riesgo, porque ese codigo ya esta probado y auditado.

---

## 4. MODELO CONCEPTUAL

Un **Task Path** es una lista ordenada de pasos. Ejemplo:

```
PICK  -> deja en  PT-A (punto de transferencia)       [rol: picker]
TRASLADO PT-A -> PACKING, actividad "empaque" 30 s    [rol: runner]
TRASLADO PACKING -> STAGING                            [rol: runner]
```

Piezas nuevas:

1. **Puntos de transferencia**: lugares del mapa donde se deja la carga, con
   **capacidad** (cuantas cargas entran).
2. **Estaciones de actividad**: empaque, consolidacion, control de calidad,
   etiquetado, etc. Tienen **tiempo de proceso** y **cantidad de puestos**.
3. **Roles** (el "Task Group" de Manhattan): que tipos de paso puede hacer cada
   grupo de agentes. Un agente puede tener varios roles.
4. **Unidad de carga**: lo que viaja entre pasos (ver decision D1).
5. **Tipo de recorrido nuevo** (`traslado`) en el despachador y el operario.
6. **Estados nuevos** de la carga: `en_transferencia`, `en_traslado`,
   `en_estacion`, `procesada`, antes de `staged`.

### Que pasa si un punto de transferencia se llena

Lo realista es que el picker **espere** hasta que haya lugar (en la operacion
real el pasillo se tapa). Eso genera exactamente el cuello de botella que el
simulador tiene que mostrar: si faltan runners, se acumulan cargas y los
pickers se frenan.

---

## 5. CONFIGURACION PROPUESTA (opt-in, apagada por defecto)

```json
"task_path": {
  "enabled": false,
  "unidad_de_carga": "tour",
  "puntos_transferencia": {
    "PT-A":   {"x": 10, "y": 28, "capacidad": 6}
  },
  "estaciones": {
    "PACKING": {"x": 15, "y": 28, "puestos": 2, "actividad": "empaque",
                "tiempo_s": 30, "rol_operador": "packer"}
  },
  "pasos": [
    {"tipo": "pick",     "deja_en": "PT-A",              "rol": "picker"},
    {"tipo": "traslado", "desde": "PT-A", "hasta": "PACKING", "rol": "runner"},
    {"tipo": "traslado", "desde": "PACKING", "hasta": "STAGING", "rol": "runner"}
  ]
}
```

Y en la flota, un atributo nuevo por grupo:

```json
{"type": "GroundOperator", "roles": ["runner"], ...}
```

**Sin el bloque, o con `enabled: false`, la simulacion es IDENTICA a hoy**
(mismo criterio que INIT-7): el gate debe dar PASS byte-identico.

Un grupo sin `roles` se comporta como hoy (puede pickear y llevar a staging),
para no romper ninguna configuracion existente.

Las coordenadas de puntos y estaciones: hoy en el config (editables desde la
web). Cuando exista el modelo de almacen propio (INIT-10) pasan a vivir ahi.

---

## 6. CAMBIOS EN EL MOTOR

| Archivo | Cambio |
|---|---|
| `warehouse.py` | Leer el bloque; crear puntos de transferencia (con capacidad) y estaciones (recursos SimPy con N puestos) |
| `dispatcher.py` | Colas por tramo; `_asignar_traslado()` generalizando `_asignar_putaway()`; filtrar por **rol** ademas de area |
| `operators.py` | Rol por agente; el tour de pick termina en el punto de transferencia (no en staging) si el path esta activo; nuevo `_execute_traslado_tour()`; espera si el punto esta lleno |
| Estacion de actividad | Proceso nuevo: la carga ocupa un puesto, se procesa `tiempo_s` y queda lista para el siguiente tramo |
| `config_schema.py` | Registrar `task_path` y `roles` (Ley MEJ-3) |
| `replay_utils.py` | KPIs nuevos en la metadata |

---

## 7. KPIs NUEVOS

- **Espera en cada punto de transferencia** (media y maxima): el indicador
  directo de si faltan runners.
- **Ocupacion de cada punto** (cuantas veces se lleno, tiempo lleno).
- **Tiempo en cola y utilizacion de cada estacion**: si faltan puestos de empaque.
- **Tiempo total de la orden desglosado por paso**: donde se va el tiempo.
- **Pickers bloqueados esperando lugar**: el costo del cuello de botella.

Todos comparables en Experimentos A/B (por ejemplo: 2 runners contra 3).

---

## 8. UI

Pestana nueva **"Flujo de Salida"** (o dentro de Outbound Staging):
- activar el Task Path;
- definir puntos de transferencia y estaciones (con su ubicacion en el mapa,
  validada contra el `.tmx` como ya se hace con zonas y muelles);
- armar la lista de pasos (agregar, quitar, reordenar);
- en Flota, asignar **roles** a cada grupo.

En el visor: mostrar las cargas esperando en cada punto y el estado de cada
estacion.

---

## 9. FASES

| Fase | Que | Gate |
|---|---|---|
| **F0** | Andamiaje: esquema de config, lectura, estructuras vacias. Nada se activa | PASS byte-identico |
| **F1** | Un solo paso intermedio: pick -> punto de transferencia -> staging, con roles | PASS con el flag apagado |
| **F2** | Estaciones de actividad (tiempo de proceso + puestos) | PASS con el flag apagado |
| **F3** | Capacidad de los puntos y espera del picker (backpressure) | PASS con el flag apagado |
| **F4** | KPIs + comparacion A/B | PASS con el flag apagado |
| **F5** | UI (configuracion + visor) | PASS con el flag apagado |

Cada fase se entrega y valida por separado. Referencia de tamano: INIT-7
(recepcion) fueron 5 fases parecidas. **Estimacion: 1,5 a 2 semanas.**

---

## 10. DECISIONES QUE NECESITO DEL DIRECTOR

**D1 — Que es lo que viaja entre pasos.**
(a) cada orden de trabajo por separado;
(b) **el recorrido completo del picker** como una unidad (su carro o tote);
(c) contenedores con capacidad propia que agrupan varias ordenes.
**Recomiendo (b)** para empezar: es lo que pasa en la realidad (el picker deja
su carro lleno) y es simple. (c) es mas realista pero bastante mas trabajo.

**D2 — Un camino o varios.**
Un solo Task Path para todo, o distintos segun el tipo de pedido, el area o la
clase de producto (por ejemplo, los pesados van directo a staging y los chicos
pasan por empaque).
**Recomiendo** empezar con uno solo, pero con el esquema preparado para varios.

**D3 — Quien trabaja en las estaciones.**
(a) personal propio fijo en cada estacion (rol `packer`);
(b) la misma persona que llevo la carga hace la actividad.
**Recomiendo (a):** es como funciona un almacen real, y permite ver si faltan
empacadores independientemente de los runners.

**D4 — Si se llena un punto de transferencia.**
(a) el picker espera (realista, muestra el cuello de botella);
(b) se permite sobrecupo.
**Recomiendo (a)**, por el principio rector de realismo.

**D5 — Que actividades concretas necesitas.**
Empaque, consolidacion, control de calidad, etiquetado, valor agregado... El
modelo las trata a todas igual (tiempo + puestos), pero conviene saber cuales
para los nombres, los valores por defecto y la documentacion.

---

## 11. VALIDACION

1. `python -m pytest -q` verde tras cada fase.
2. `python scripts/regression_gate.py` **PASS byte-identico en todas las fases**
   con el Task Path apagado (es opt-in).
3. Con el Task Path encendido y **un solo paso trivial** (punto de transferencia
   con capacidad infinita y un runner), las ordenes completadas y el volumen
   deben coincidir con la corrida sin Task Path: solo cambia el tiempo.
4. Pruebas de cuello de botella: con 1 runner los puntos se llenan y los pickers
   esperan; con mas runners la espera baja. Si no pasa eso, el modelo esta mal.
5. Tests nuevos por fase (roles, colas, capacidad, estaciones, KPIs).

---

## Fuentes

- Infor WMS, Pick and Drop: https://docs.infor.com/wms/2022.x/en-us/useradminlib/scepadug/net1612893806986.html
- Oracle WMS Cloud, Task Zone Movement: https://docs.oracle.com/en/cloud/saas/warehouse-management/23c/owmol/task-zone-movement-rule.html
- Manhattan WMOS (task paths, task groups): https://www.maxmunus.com/page/Manhattan-WMS-Training
- Manhattan SCALE, flujos de trabajo: https://www.techtarget.com/searcherp/feature/Define-warehouse-workflows-and-processes-with-Manhattan-SCALE
