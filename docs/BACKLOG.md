# BACKLOG — Gemelo Digital de Almacen
# Inventario de iniciativas: hechas y pendientes

Documento creado: 2026-06-14 · Actualizado: 2026-07-04
Responsable: Cerebellum

## Indice de estado (de un vistazo)

| Item | Estado |
|------|--------|
| BK-01 — Estrategias ocultas (Cercania) en UI | HECHO (2026-06-14) |
| BK-02 — FIFO Estricto en UI | EN REPENSAR (Director) |
| BK-03 — Greedy nearest-neighbor en Cercania | DESCARTADO con evidencia |
| BK-04 — Flota sin work_area + outbound colgado | RESUELTO (2026-06-20) |
| BK-05 — Botones E6/E7 stub | ELIMINADO (2026-06-27) |
| INIT-4 — Prioridad/SLA/olas + tiempos de pick | HECHO (2026-06-29) |
| INIT-5 — Nivel de servicio / backorders | RESUELTO (2026-06-21) |
| **INIT-4 → KPI de SLA vencido** | **PENDIENTE** (diferido de INIT-4) |
| INIT-1 — Picking por ubicacion real (alcance redefinido: solo modo Stochastic) | HECHO (2026-07-05) |
| **INIT-3 — Reparar optimizador Optuna** | **PENDIENTE** (bajo-medio) |
| WOs sobredimensionadas — fix defensivo | HECHO (2026-07-05) |
| **`_legacy/web_dashboard/`** — conservar/reparar/eliminar | **PENDIENTE DECISION** |
| MEJ-1 — Red de seguridad automatizada (tests + gate) | HECHO (2026-07-04, F1-F5 completas) |
| MEJ-2 — Experiment runner con replicas + comparacion A/B | HECHO v1 (2026-07-04) — v2 (nivel de servicio) diferido |
| MEJ-3 — Esquema unico de config (pydantic) + purga de claves | HECHO (2026-07-04) |
| MEJ-4 — Completar anti-colisiones (dwell + fallback visible) | HECHO (2026-07-04) |
| **INIT-6 — Staging multi-destino por ruta (redefine el hallazgo makespan +55%)** | **PENDIENTE** (alto, sin sprint asignado) |

---

## BK-01 — Exponer estrategias de despacho ocultas en el configurador web

**Estado:** IMPLEMENTADO — 2026-06-14
**Commit:** ver rama feature/allocation-layer-v12.1 (incluido en BK-01 commit)
**Evidencia:**
- `[DISPATCHER] Inicializado con estrategia: 'Cercania'`
- `[DISPATCHER] Radio cercania: 80`
- `[DISPATCHER] Estrategia 'Cercania' selecciono 27 candidatos`

**Archivos modificados:**
- `web_prototype/static/web_configurator/index.html` — nueva `<option value="Cercania">` + div `#radio-cercania-group`
- `web_prototype/static/web_configurator/app.js` — `_updateRadioCercaniaVisibility()`, load/serialize `radio_cercania`, listener `dispatch-strategy`
- `web_prototype/config_manager.py` — validacion `radio_cercania` (int 1-500), default en `_get_default_config()`
- `config.json` — campo `radio_cercania: 100` agregado
**Prioridad:** Media
**Origen:** Investigacion de H-1 (sesion 2026-06-14). El Director confirmo que las
             estrategias tienen proposito real y deben ser seleccionables.

### Descripcion del problema

El configurador web (tab "Estrategias", selector `dispatch-strategy`) solo ofrece
dos opciones visibles al usuario:
- "Optimizacion Global" (usa AssignmentCostCalculator para la primera WO, luego doble barrido)
- "Ejecucion de Plan (Filtro por Prioridad)" (primera WO por pick_sequence minimo, luego doble barrido)

Sin embargo, `dispatcher.py` (`DispatcherV11._seleccionar_work_orders_candidatos`) tiene
implementadas cuatro estrategias, de las cuales dos NO estan expuestas en la UI:

### Estrategias existentes en dispatcher.py (estado actual)

| Estrategia              | Metodo                        | En UI | Descripcion |
|-------------------------|-------------------------------|-------|-------------|
| FIFO Estricto           | `_estrategia_fifo()`          | NO    | Toma las primeras N WorkOrders de la cola, sin optimizacion |
| Optimizacion Global     | `_estrategia_optimizacion_global()` | SI  | Primera WO por menor costo (distancia+area), resto por pick_sequence |
| Ejecucion de Plan       | `_estrategia_ejecucion_plan()` | SI   | Primera WO por pick_sequence minimo en area prioritaria |
| **Cercania**            | `_estrategia_cercania()`      | **NO** | Filtra WOs dentro de un radio en celdas del operario actual |

### Estrategia de Cercania — detalle

**Proposito del Director:** El operario elige el siguiente producto a piquear segun la
ubicacion mas cercana a donde esta parado en ese momento. Reduce la distancia total
recorrida cuando las WorkOrders estan dispersas por el almacen.

**Implementacion actual** (`dispatcher.py`, linea ~735):
```python
def _estrategia_cercania(self, operator):
    # Filtra WOs dentro de radio `radio_cercania` (default 100 celdas) desde
    # la posicion actual del operario. Luego `_seleccionar_mejor_batch()` elige
    # por costo entre las candidatas de proximidad.
    op_x, op_y = operator.current_position
    for wo in self.work_orders_pendientes:
        if not operator.can_handle_work_area(wo.work_area):
            continue
        distance = math.sqrt((wo_x - op_x)**2 + (wo_y - op_y)**2)
        if distance <= self.radio_cercania:
            candidatos.append(wo)
    return candidatos[:self.max_wos_por_tour * 2]
```

**Parametro de config relevante:** `radio_cercania` (int, en celdas de grilla).
Ya existe en `config.json` (default 100). Si se expone la estrategia, conviene mostrar
este campo en el configurador condicionado a que "Cercania" este seleccionada.

### Doble barrido por secuencia — detalle

**Proposito del Director:** El operario recorre los pasillos de forma lineal del primero
al ultimo, y luego vuelve a empezar desde el primero en una segunda pasada para piquear
todo lo que no logro en el primer recorrido.

**Estado actual:** Este comportamiento ya esta implementado como algoritmo interno de
construccion de tour (`_construir_tour_por_secuencia()`), y se usa en AMBAS estrategias
activas (Optimizacion Global y Ejecucion de Plan). NO es una estrategia de despacho
independiente — es el paso de construccion del tour que ocurre DESPUES de seleccionar
la primera WorkOrder.

El doble barrido tiene dos pasadas:
1. **Barrido 1 (Progresivo):** WOs con `pick_sequence >= min_seq`. Avanza en orden.
2. **Barrido 2 (Circular):** WOs con `pick_sequence < min_seq`. Vuelve al inicio para
   maximizar la utilizacion de carga del viaje.

**Conclusion para el backlog:** El doble barrido NO necesita exponerse como estrategia
adicional — ya esta activo siempre. Lo que puede documentarse mejor es su existencia
en la UI (quizas un tooltip explicando que las estrategias usan doble barrido).

### Que se debe hacer para implementar BK-01

**Paso 1 — Agregar "Cercania" al selector HTML:**
En `web_prototype/static/web_configurator/index.html`, select `#dispatch-strategy`:
```html
<option value="Cercania">Cercania (Asignacion por Proximidad)</option>
```

**Paso 2 — Exponer el parametro radio_cercania condicionalmente:**
En `index.html`, agregar un campo numerico `#radio-cercania` debajo del selector,
que solo sea visible cuando la estrategia seleccionada es "Cercania". Ejemplo:
```html
<div id="radio-cercania-group" class="form-group" style="display:none;">
  <label>Radio de cercania (celdas)</label>
  <input type="number" id="radio-cercania" min="1" max="500" value="100">
  <span class="help-text">El operario solo considera WOs dentro de este radio.</span>
</div>
```

**Paso 3 — Cablear en app.js:**
En `loadConfigToForm()`: leer `config.radio_cercania` y poblar el campo.
En `serializeConfig()`: incluir `radio_cercania: parseInt(...)`.
Agregar listener al selector para mostrar/ocultar el grupo de campo segun estrategia.

**Paso 4 — Validar en config_manager.py:**
En el bloque de validacion de campos, agregar:
```python
'radio_cercania': (int, 1, 500)
```

**Paso 5 — Verificar en el motor:**
`dispatcher.py` ya lee `configuracion.get('radio_cercania', 100)`. Sin cambios en el motor.

**Paso 6 — Agregar "FIFO Estricto" al selector (opcional):**
Si el Director quiere exponer tambien FIFO, agregar:
```html
<option value="FIFO Estricto">FIFO Estricto (Cola simple)</option>
```
No requiere parametros adicionales.

### Estimacion de esfuerzo

- HTML: ~10 lineas
- app.js: ~15 lineas (load/serialize + listener de visibilidad)
- config_manager.py: ~2 lineas
- Prueba en navegador: ~10 min

Total: 1 sprint corto (~1-2 horas), sin tocar el motor de simulacion.

---

## Nota de bug detectado durante BK-01 (RESUELTO)

**RESUELTO en commit `c4c772f` (Fix H-5, 2026-06-14).**
El dispatcher ahora reconoce el alias corto "Ejecucion de Plan" que envia la UI,
ademas del string largo "Ejecucion de Plan (Filtro por Prioridad)".
El bug ya no existe en la rama activa ni en main.

---

## BK-02 — Exponer "FIFO Estricto" en el selector de estrategia de la UI

**Estado:** EN REPENSAR — diseño pendiente (decision del Director, 2026-06-15)
**Prioridad:** Baja (bloqueado hasta redefinicion)
**Origen:** Auditoria de estrategias (sesion 2026-06-14)

> **Nota del Director (2026-06-15):** No exponer todavía. Hay que repensar qué
> debería hacer FIFO Estricto para que tenga sentido como herramienta real de
> operación, antes de exponerlo en la UI. El motor ya lo implementa correctamente;
> la pregunta es sobre el diseño de uso, no la implementación técnica.

### Contexto

La estrategia `_estrategia_fifo()` ("FIFO Estricto") esta completamente implementada
en `dispatcher.py` (linea 275) y funciona correctamente cuando el dispatcher la recibe
via el string exacto `"FIFO Estricto"`. Sin embargo, no esta expuesta en el configurador
web: el selector de dispatch-strategy solo muestra Optimizacion Global, Ejecucion de Plan
y Cercania.

### Valor

- Permite usar FIFO como **linea base de comparacion**: si las estrategias inteligentes
  no superan a FIFO en throughput, el diseño del almacen o la distribucion de WOs tiene
  un problema mas profundo.
- Util en pruebas de regresion donde se quiere comportamiento deterministico y simple.
- Costo de implementacion: 1 linea de HTML.

### Plan de implementacion

**Paso 1 — HTML (`index.html`):**
```html
<option value="FIFO Estricto">FIFO Estricto (Cola de llegada)</option>
```
Agregar en el `<select id="dispatch-strategy">` antes de las opciones existentes
(ya que es la mas simple y sirve como baseline).

**Paso 2 — app.js:**
No requiere cambios: `serializeConfig()` ya lee el value del select directamente.
`loadConfigToForm()` ya llama a `setSelectValue` que manejara el nuevo valor.

**Paso 3 — config_manager.py:**
Agregar `"FIFO Estricto"` a la lista de valores validos en la validacion de
`dispatch_strategy`.

**Paso 4 — Verificar:**
Seleccionar "FIFO Estricto", correr simulacion, confirmar en logs:
`[DISPATCHER] Inicializado con estrategia: 'FIFO Estricto'`
y que los operarios toman WOs en orden de llegada sin logica de distancia.

### Estimacion de esfuerzo

- HTML: 1 linea
- config_manager.py: 1 linea de validacion
- Prueba: 5 min
Total: sprint ultra-corto (~15 min)

---

## BK-03 — Evaluar integracion de Greedy Nearest-Neighbor en el tour de Cercania

**Estado:** DESCARTADO con evidencia — experimento ejecutado 2026-06-15
**Prioridad:** N/A
**Origen:** Auditoria de estrategias (sesion 2026-06-14)

### Resultado del experimento (2026-06-15)

Experimento ejecutado: 3 corridas Cercania/cost + 3 corridas Cercania/greedy_nn
(radio=100, 300 WOs, 2 operarios terrestres, 0 montacargas).

| Metrica            | COST (baseline) | GREEDY_NN  | Delta      |
|--------------------|-----------------|------------|------------|
| Distancia total    | 188,576 px      | 178,635 px | -5.27%     |
| WOs completadas    | 614.7           | 591.3      | **-3.80%** |
| Tiempo simulacion  | 3,409.5 s       | 3,293.4 s  | -3.40%     |
| **Distancia/WO**   | 306.8 px        | 302.1 px   | **-1.54%** |

**Conclusion:** El -5.27% en distancia total es un artefacto: greedy_nn hace menos
trabajo (-3.8% WOs) en menos tiempo (-3.4%), acumulando menos distancia porque
hace menos recorridos. La metrica real de eficiencia (distancia por WO completada)
solo mejora un -1.54%, que con N=3 esta dentro del ruido estadistico.

**Decision: NO integrar.** La flag `cercania_tour_mode` queda en el codigo con
default `"cost"` (comportamiento original) y documentada en caso de que el Director
quiera retomar el experimento con N mayor o con distancia real de pathfinder.

### Contexto original

En `src/subsystems/simulation/route_calculator.py` (linea 319) existe el metodo
`calculate_greedy_nearest_neighbor()` completamente implementado pero sin callers.
El comentario original dice "May be used if dispatch_strategy == Cercania".

### Que hace

Una vez que la estrategia Cercania filtra los candidatos dentro del radio, actualmente
los ordena por costo (`AssignmentCostCalculator`). La alternativa greedy-nearest-neighbor
ordenaria esos mismos candidatos por vecino mas cercano: desde la posicion actual, siempre
ir al producto mas proximo, luego al siguiente mas proximo desde ahi, y asi sucesivamente.

### Ventaja potencial

En escenarios donde el operario queda parado en un punto arbitrario del layout (no al inicio
del pasillo), el vecino mas cercano puede reducir el total de caminata mas que el ordenamiento
por costo actual. La diferencia seria mayor en layouts con alta densidad de WOs dispersas.

### Riesgo

- El metodo usa distancia euclidea, no la distancia real del pathfinder (que evita obstaculos).
  Para que sea util, habria que opcionalmente usar distancia de pathfinder (mas costosa en CPU).
- No esta probado en produccion: necesita prueba E2E antes de activar.

### Plan de evaluacion (antes de integrar)

1. Correr la misma simulacion con Cercania actual vs Cercania+greedy-NN (via flag de config).
2. Medir: total de distancia recorrida por operario, throughput de WOs, tiempo de simulacion.
3. Si la mejora es > 5% en distancia sin impacto en CPU, integrar. Si no, descartar.

### Codigo a tocar si se decide integrar

- `dispatcher.py`: en `_construir_tour()`, cuando `tour_type == "Cercania"`,
  llamar `route_calculator.calculate_greedy_nearest_neighbor(operator.position, selected_wos)`
  para reordenar antes de calcular la ruta fisica.
- `config.json`: opcionalmente agregar `"cercania_tour_mode": "greedy_nn"` vs `"cost"`.

---

## BK-04 — Flota por defecto deja Forklift sin work_area + outbound no termina

**Estado:** RESUELTO (preventivo) 2026-06-20 — solucion A + Fix 1 rehecho + C.
**Prioridad:** Media-Alta (bloqueaba correr con outbound + flota por defecto desde la UI)
**Origen:** Ronda en vivo navegador (docs/VALIDACION_UI_WEB.md, secciones 2026-06-19/20)

### Solucion implementada (2026-06-20)
Enfoque PREVENTIVO acordado con el Director (sin watchdog que corte la sim):
- **A — validacion backend bloqueante** (`web_prototype/config_manager.py::validate_config`):
  con `agent_types` explicito, toda area real del layout (`extract_work_areas`) debe
  estar cubierta por algun grupo; si no, rechaza guardado/run nombrando el area. Con
  `agent_types` vacio NO valida (el motor usa flota fallback que cubre todo => sin
  regresion). El run tambien queda frenado: `index.html::startSimulation` aborta si el
  auto-guardado devuelve `success:false`.
- **Fix 1 rehecho** (`fleet-manager.js::_executeDefaultFleet`): la flota por defecto usa
  las areas REALES (`this.workAreas`), no nombres hardcodeados; reparte piso->Ground,
  resto->Forklift, cubriendo todas por construccion.
- **C — indicador en vivo** (`#area-coverage-panel` + `updateAreaCoverage`): marca en
  rojo las areas sin agente y se recalcula ante cualquier cambio de flota.
- Tambien se corrigio la lista fallback stale en `app.js` (Area_Rack/Area_Piso_L1 ->
  areas reales Area_Ground/Area_High/Area_Special).

Validado en vivo: flota por defecto cubre todo y la corrida con outbound TERMINA
(exit 0, Pending=0, 44 trucks / 153 pallets); dejar un area huerfana => C en rojo + A
bloquea Apply y Run con el mensaje; flota vacia sigue valida (sin regresion). Ver
docs/VALIDACION_UI_WEB.md (seccion 2026-06-20).

> NOTA (no bloqueante): el Fix 2 defensivo (watchdog de terminacion del OutboundProcess)
> fue DESCARTADO por el Director. El `while True` de OutboundProcess sigue ahi.

### Hardening QA (2026-06-21) — cierre de grietas QA-1/QA-2/QA-3
Un QA adversarial (docs/VALIDACION_UI_WEB.md) hallo 3 grietas sobre A+Fix1+C; el Director
aprobo cerrarlas (sin watchdog):
- **QA-2:** `validate_config` exige >=1 agente tambien con `agent_types` vacio (flota
  vacia / 0 agentes ya NO pasa).
- **QA-1:** chequeo preventivo al ARRANQUE del motor (`event_generator._validar_flota_
  cubre_areas`, antes de `env.run`): si no hay agentes / no hay WOs / un area sin agente
  capaz, ABORTA con mensaje (exit 1) en vez de colgarse. Cubre el bypass del motor
  (config.json a mano, `--config`, optimizer, presets viejos).
- **QA-3:** validacion y motor exigen el TIPO de agente capaz por area. C marca el tipo
  incorrecto en naranja. **(2026-06-21, Opcion B)** la fuente de verdad del tipo por area
  paso de la convencion por nombre a un mapa EXPLICITO `work_area_equipment` en config.json,
  editable en la UI, validado por completitud; la convencion queda solo como fallback de
  migracion. Ver docs/VALIDACION_UI_WEB.md (seccion "QA-3 ROBUSTO (Opcion B)").
Re-test adversarial confirmo: los vectores que antes colgaban ahora abortan en ~2s; las
configs validas de siempre siguen funcionando (no-regresion). El `while True` sigue, pero
ya no se alcanza por estas vias. Si aparece OTRO deadlock de asignacion no cubierto por
estos chequeos, reconsiderar el watchdog.

---

### (Diagnostico original, 2026-06-19)

### Sintoma
Tras "Generar Flota por Defecto" en el configurador y correr con outbound ON, la
simulacion NO termina: corre indefinidamente emitiendo camiones vacios (en una prueba,
22.358 "truck sale vacio", t > 1.5M s) hasta timeout.

### Causa raiz (dos partes)
1. **Forklift sin work_area_priorities:** "Generar Flota por Defecto" crea los grupos
   Forklift con `work_area_priorities: {}` (vacio). Las WorkOrders de Area_High /
   Area_Special (que solo manejan forklifts) nunca se asignan -> quedan Pending para
   siempre (en la prueba: Completed=72 congelado, Pending=99). Los GroundOperator si
   reciben Area_Ground (priority 1), por eso completan su parte.
2. **OutboundProcess no termina:** `outbound.py::OutboundProcess.run()` es un
   `while True: yield timeout(truck_interval)`. Mientras viva, SimPy siempre tiene un
   evento futuro -> `env.run()` nunca se queda sin eventos -> la sim no finaliza aunque
   los operarios esten idle. Sin outbound, una sim con WOs imposibles terminaria al
   agotarse los eventos (incompleta); con outbound queda colgada para siempre.

### Evidencia
- 181343 (replay valido, 40 trucks / 226 pallets) uso una config con `agent_types: []`,
  donde el motor asigna areas por defecto a los forklifts -> SI completan Area_High.
- La config guardada por la UI tiene `agent_types` explicito con Forklift
  `work_area_priorities: {}` -> deadlock.

### Plan propuesto (a confirmar con el Director)
- **Fix 1 (UI):** que "Generar Flota por Defecto" asigne areas a los Forklift
  (p.ej. Area_High + Area_Special) en `fleet-manager.js`, en lugar de `{}`.
- **Fix 2 (motor, defensivo):** watchdog de terminacion: si N camiones consecutivos
  salen vacios y no hay progreso de WOs durante X tiempo, cortar la sim (o que
  OutboundProcess termine cuando no quedan pallets ni WOs asignables). Evita el hang
  infinito ante cualquier deadlock de asignacion.
- **Fix 3 (UX):** que el configurador advierta si hay WorkAreas sin ningun agente capaz.

### Nota
NO lo causa el cambio de `truck_interval` (bajar el default a 90 solo hizo el hang mas
ruidoso). El feature truck_interval quedo validado de forma independiente.

---

## INIT-5 — Exponer nivel de servicio / backorders en visor y reportes

**Estado:** RESUELTO 2026-06-21
**Origen:** docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md (Top-5, #5). Idea pendiente del Director.

### Que era
El allocation layer ya calculaba la demanda no cubierta (`qty_requested` vs `qty_allocated`,
`unfilled_demand`, fill-rate en `allocation_summary`) pero ese dato NO llegaba al usuario:
se quedaba dentro del motor.

### Que se implemento (plomeria, sin tocar la logica del motor)
- **Fuente unica:** `core/replay_utils.build_service_level_summary(almacen)` arma el resumen
  desde `almacen.get_order_validation_result()`. En modo estocastico (sin validacion de
  stock) -> `available=False` (la UI muestra N/A).
- **.jsonl:** `volcar_replay_a_archivo` adjunta `service_level` a la metadata `SIMULATION_START`.
- **API:** `server.py` lee `service_level` de la metadata y lo expone en `/api/snapshot`
  (top-level y dentro de `metrics`), `/api/state` y `/api/metrics`.
- **Visor:** nuevo KPI **"Servicio"** en la barra de metricas (`metric-service`, fill-rate %;
  N/A en estocastico) — `web_prototype/static/app.js`.
- **Excel:** hoja nueva **"Nivel de servicio"** anexada al reporte (`exporter_v2`), con
  resumen (pedido/servido/faltante/fill-rate/pedidos cortos) + desglose por pedido/SKU + total.

### Validacion (corrida determinista con backorders: pedir 500 de SKU026 con stock 171, etc.)
- `.jsonl`: `service_level` = available True, fill 44.6%, pedido 803, servido 358, deuda 445,
  2 pedidos cortos, con desglose (ORD-A SKU026 req500/got171/falta329, ORD-B 300/184/116).
- API: `/api/snapshot` (top y metrics), `/api/state`, `/api/metrics` devuelven el mismo resumen.
- Excel: hoja "Nivel de servicio" presente junto a las existentes (no las rompe).
- Estocastico (control): `available=False` -> N/A, sin romper.
> Nota: el KPI visual en el navegador quedo sin captura en vivo (extension Chrome
> desconectada); validado por API/JSONL/Excel y la logica JS es trivial (lee metrics.service_level).

---

## BK-05 — Botones E6/E7 ("Generar Plantilla TMX" / "Poblar SKUs Aleatorios")

**Estado:** ELIMINADO — 2026-06-27
**Motivo:** Eran stubs sin backend (mostraban un toast "Funcionalidad en desarrollo").
El nombre "TMX" era incorrecto (hubieran generado un .xlsx, no un mapa Tiled).
"Poblar SKUs" mencionaba CSV pero la fuente real es .xlsx. Specs incoherentes +
cero implementacion = UI enganiosa. Eliminados limpiamente.

**Lo que se quito:**
- `index.html`: 2 elementos `<button disabled>` de la tarjeta "Acciones de Datos"
- `app.js`: 2 `addEventListener` + 2 metodos `generateTemplate()` / `populateSKUs()`
- Tarjeta queda con el unico boton funcional: `btn-load-work-areas`

**Si en el futuro se decide construir algo equivalente:**
- Definir spec claro primero (columnas del Excel, rangos de SKUs, etc.)
- Crear endpoint FastAPI + funcion Python generadora
- El frontend ya sabe que la fuente canonica es `layouts/Warehouse_Logic.xlsx`

---

## INIT-1 — Inventario y picking por ubicacion real + reservas

**Estado:** HECHO (alcance real) — 2026-07-05, en `main`.
**Prioridad:** Alta (correctitud fundacional del simulador)
**Origen:** docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md, item #1

### Root cause real (revision 2026-07-05) -- el alcance original estaba desactualizado
Al investigar, el problema descrito NO aplicaba donde el backlog decia:
- **`DeterministicOrderStrategy`** (pedidos por archivo, `order_generation_mode`
  != stochastic) **YA usaba ubicacion real**: la Allocation Layer V12.1
  (`data_manager.get_inventory_by_location()` + `_allocate_across_locations()`)
  asigna cada WO a una ubicacion real con stock real de ese SKU. Nada que hacer aca.
- **`StochasticOrderStrategy`** (modo default de `config.json`, el que genera
  el baseline byte-identico) SI tenia el bug: elegia un SKU al azar por
  categoria de tamaño, y por separado elegia la ubicacion via round-robin
  sobre TODOS los puntos de picking mezclados -- sin relacion con el SKU
  elegido. El catalogo de SKUs y el inventario agregado SI eran reales (de
  BD/Excel); la ubicacion de cada WO, no.
- `_get_location_for_area()` / `_get_default_work_area()` /
  `_build_picking_points_index()` (mencionados en el plan original) resultaron
  ser **codigo muerto** dentro de `DeterministicOrderStrategy` -- sin
  callers, remanente de una implementacion anterior a la Allocation Layer.
  No se tocaron (candidato a poda en una fase de limpieza futura).

### Fix aplicado
En `StochasticOrderStrategy.generate_work_orders()` (`order_strategies.py`):
indice `points_by_sku` construido desde `data_manager.puntos_de_picking_ordenados`
(campo `sku_initial`, que ya existia). Al elegir el SKU de la WO, se busca entre
SUS puntos reales (`random.choice` sobre esos, no sobre todos) y se usa la
`ubicacion_grilla` / `WorkArea` / `pick_sequence` real de ese punto. Fallback
(round-robin viejo + `[STOCHASTIC][WARN]`) solo si el SKU no tiene ningun punto
real asociado (dato inconsistente; no ocurre en el catalogo real).

**Cambio incondicional** (no opt-in): es la correccion de un bug de
correctitud, no una feature nueva -- decision del Director, mismo criterio que
MEJ-4. Baseline actualizado con `--update-baseline --yes`.

### Validacion
- 3 tests nuevos (`tests/unit/test_stochastic_location.py`): WO va a la unica
  ubicacion real del SKU; con multiples puntos del mismo SKU, siempre elige
  entre esos (nunca el de otro SKU); fallback no crashea si un SKU no tiene
  punto real. Suite: **85 passed, 0 skipped**.
- Gate de regresion: cambio detectado (esperado) -- sha256 nuevo
  `5f1f4adc...`, tamaño 4.919.513 bytes (antes 5.118.303, -3.9%). Makespan
  se mantuvo practicamente igual (3122s vs 3121s del baseline MEJ-4) --
  el fix cambia QUE ubicaciones exactas se visitan, no la dinamica general
  del sistema. Baseline actualizado y gate re-verificado PASS.
- **Nota de transparencia:** el reporte del planner mostro 1 plan fallido de
  348 (antes 0 en el baseline MEJ-4), resuelto por el fallback visible que
  ya construyo MEJ-4 (reserva best-effort + WARN, no crashea). Es esperable:
  el patron espacial cambio (WOs de un mismo SKU ahora se concentran en sus
  puntos reales en vez de dispersarse), lo que puede generar picos de
  conflicto puntuales distintos a los del baseline anterior. No bloqueante.

### Diferido / fuera de alcance de este fix
- `qty_reserved` explicito por ubicacion en modo Stochastic: el modo
  estocastico sigue tratando el inventario como "suficiente" (no consume
  stock real por WO, a diferencia del modo Deterministico que si lo hace via
  Allocation Layer). Si se quiere que Stochastic tambien refleje agotamiento
  de stock por ubicacion, es una ampliacion futura a evaluar con el Director
  (cambia la semantica de "modo estocastico" de forma mas profunda).
- Poda del codigo muerto (`_get_location_for_area` y compañia) -- candidato
  para una fase de limpieza explicita, no se toco aqui.

### Archivos tocados
- `src/subsystems/simulation/order_strategies.py`:
  `StochasticOrderStrategy.generate_work_orders()`.
- `tests/unit/test_stochastic_location.py` (nuevo).
- `tests/baseline.json` (actualizado).

---

## INIT-3 — Reparar y ampliar el optimizador Optuna

**Estado:** PENDIENTE — sin sprint asignado
**Prioridad:** Media-Alta (feature estrella del producto, hoy posiblemente no-op)
**Origen:** docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md, item #3

### El problema
El optimizador (`src/tools/optimizer.py`) puede estar probando:
(a) Nombres de estrategia que no coinciden con los del dispatcher.
(b) Parametros que se mapean a claves legacy que el motor ignora (p.ej.
    `num_operarios_terrestres` en vez de `agent_types`).
(c) `export_optimization_metrics` lee `num_operarios_terrestres`/`num_montacargas`
    para `resource_costs`; si el config usa `agent_types`, esos contadores son 0.

### Que hay que hacer
1. Alinear nombres de `dispatch_strategy` con los del dispatcher (Fix H-5 ya lo hizo para la UI; revisar si el optimizador lo heredo).
2. Traducir los parametros sugeridos a `agent_types` reales.
3. Ampliar el espacio de busqueda: capacidades, `max_wos_por_tour`, prioridades de zona.
4. Exponer el mejor resultado en la web (`/api/optimization`).

### Archivos a tocar
- `src/tools/optimizer.py`
- `src/engines/event_generator.py` (export_optimization_metrics)
- `web_prototype/server.py` (endpoint de resultado)

### Estimacion de esfuerzo
Bajo-Medio (1 sesion para alineacion basica; otra para ampliar espacio).

---

## INIT-4 — Prioridad de ordenes / SLA / olas + fidelidad de tiempos de pick

**Estado:** HECHO — 2026-06-29 (commits 91dd6c0, c27dacb, fd0a41d)
**Prioridad:** Media
**Origen:** docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md, item #4
**Plan y pruebas:** docs/PLAN_INIT4.md (Fase A/B + checklist completo)

Implementado en 3 fases, cada una opt-in con defaults neutros y gate de
no-regresion byte-identico (REG-1, WAREHOUSE_SEED=42 -> SHA a4ae8d4e...).

- **C1 — Tiempos de pick realistas** (`91dd6c0`): `BaseOperator._compute_pick_time`
  escala el tiempo por cantidad/volumen (`base + por_unidad*cant + por_volumen*vol`,
  cota `minimo`). Bloque OPCIONAL `config["tiempos"]["pick_time_model"]`. Neutro ->
  comportamiento historico. E2E: tiempo_picking varia 8..24 segun cantidad.
- **C2 — Prioridad de pedido / SLA** (`c27dacb`, Opcion C del Director): `WorkOrder`
  gana priority/due_time; parser JSON/CSV los lee (coercion defensiva). Flag
  `priority_dispatch_enabled`. Prioridad fuerte "limpia": mientras haya urgentes,
  el tour se arma solo con urgentes (no se diluyen). E2E: urgentes t_fin 18.8 vs
  71.2 (~4x); ranking medio 5.6 vs 20.8. Costo: llenado -33%, throughput intacto.
- **C3 — Olas (waves)** (`fd0a41d`): release diferido por ola. `WorkOrder.wave_id`;
  bloque `config["waves"]` (enabled + release_times). `_wo_elegible_por_ola` en las
  4 estrategias. Terminacion sin cambio (las WOs de olas futuras ya cuentan en
  total). E2E: ola2 respeta release; WAVE-TERM (release>fin natural) no cuelga.

Pruebas: REG-1 byte-identico en cada fase; PICK-1..6, PRIO-1..7, WAVE (unit+E2E),
INT-1 (olas manda sobre prioridad) -- todas PASAN.

**Diferido (no bloqueante):** KPI de incumplimiento de SLA (due_time vencido) en
el reporte Excel/visor. La info existe en la WO; falta cablearla al reporte.

---

## WOs sobredimensionadas — Fix defensivo en _validar_y_ajustar_cantidad

**Estado:** HECHO — 2026-07-05 (en `main`).
**Prioridad:** Baja-Media (falsificaba KPIs silenciosamente)
**Origen:** docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md, Apendice quick-fixes

### El problema (ya resuelto)
En `warehouse.py::_validar_y_ajustar_cantidad`:
Si `sku.volumen > max_capacity_del_operario`, `unidades_por_viaje` truncaba a 0
y el `while` de division nunca decrementaba `cantidad_restante` -> **bucle
infinito** (peor de lo documentado originalmente: no solo "cuenta como
completada", podia colgar la simulacion entera). `tests/unit/test_warehouse_cantidades.py::test_wh04` lo tenia
documentado como `@pytest.mark.skip` para no ejecutarlo hasta el fix.

### Fix aplicado
Guard temprano en `_validar_y_ajustar_cantidad`: si `sku.volumen > max_capacity`
(imposible de cargar aunque sea 1 unidad, dado que `work_area_equipment`
asigna un unico tipo de equipo por area -- MEJ-3 QA-3 -- no hace falta
comparar contra "todos los operarios del area", `max_capacity` YA es esa cota),
loguea `[ALMACEN][WARN]` con el detalle y devuelve `[]` (no se crea ninguna
WorkOrder para esa cantidad; queda como backorder implicito, sin qty=0 fantasma
ni bucle). Ambos callers (`order_strategies.py`, generacion sintetica y
allocation layer) ya iteran la lista devuelta con un `for`, por lo que una
lista vacia no crea WOs sin requerir cambios adicionales alli.

**No se implemento** la opcion "marcar como 'failed' + registrar backorder
explicito" (item 2 del plan original) porque el guard ya elimina el daño real
(bucle infinito + KPI falso) sin necesidad de tocar `order_strategies.py`;
esa pieza queda disponible para retomar si el Director quiere que este caso
aparezca en el resumen de nivel de servicio (INIT-5) junto a los backorders
por falta de stock.

### Validacion
- `test_wh04_sku_mas_grande_que_capacidad_no_cuelga` (unskipped) +
  `test_wh04b_borde_exacto_sku_igual_a_capacidad_no_es_imposible` (nuevo,
  caracteriza el borde `volumen == max_capacity`, que SI debe procesarse).
  Suite: **82 passed, 0 skipped** (antes 1 skip documentado).
- Gate de regresion: PASS, byte-identico (`c6f129ef...`) -- el escenario
  canonico nunca dispara este path (SKU max 80 < capacidad default 150), asi
  que no hizo falta actualizar el baseline.

### Archivos tocados
- `src/subsystems/simulation/warehouse.py`: `_validar_y_ajustar_cantidad()`.
- `tests/unit/test_warehouse_cantidades.py`: test WH04 unskipped + WH04b nuevo.

---

## INIT-4b — KPI de SLA vencido en el reporte/visor (unico punto diferido de INIT-4)

**Estado:** PENDIENTE — diferido de INIT-4 (no bloqueante)
**Prioridad:** Baja
**Origen:** INIT-4 C2 (prioridad/SLA). Ver docs/PLAN_INIT4.md.

### Que es y por que queda
INIT-4 C2 anadio `due_time` (plazo de entrega) a la WorkOrder y lo usa como
criterio de desempate, pero **no se mide ni se muestra** cuantos pedidos incumplen
su SLA (se completan despues de su `due_time`). El dato ya existe en la WO; falta
cablearlo a la salida. Se difirio para cerrar INIT-4 sin ampliar el alcance.

### Que hay que hacer
1. Al completar cada pedido, comparar tiempo de completado vs `due_time`.
2. Agregar un resumen (pedidos a tiempo / vencidos / % cumplimiento SLA).
3. Exponerlo en el reporte Excel y en el visor web, reusando el patron de INIT-5
   (`core/replay_utils.build_service_level_summary` + metadata del `.jsonl`).

### Archivos a tocar
- `core/replay_utils.py` (resumen SLA), `event_generator.py` (metadata),
  `web_prototype/server.py` (API), `static/app.js` (KPI), `analytics/exporter_v2.py` (hoja).

---

## web_dashboard — Decision: conservar / reparar / eliminar

**Estado:** PENDIENTE DECISION DEL DIRECTOR
**Prioridad:** Baja (no afecta la cadena viva)
**Ubicacion:** `_legacy/web_dashboard/` (archivada, no en la raiz)

### Contexto
App web independiente (FastAPI, puerto 8001) que mostraba una **tabla de
WorkOrders** del replay. Esta **huerfana y rota**: apunta a un `.jsonl` de prueba
que ya no existe (hardcodeado, nov-2025) y usa rutas viejas. Su funcion ya la
cubre el panel de WorkOrders del **viewer web vigente** (`web_prototype`), por lo
que es una version peor y duplicada.

### Opciones (recomendacion de Cerebellum: eliminar)
- **Conservar** tal cual: no aporta (rota + duplicada); ya aislada en `_legacy/`.
- **Reparar**: arreglar rutas es rapido, pero mantendria dos UIs que hacen lo
  mismo -> esfuerzo sin premio. No recomendado.
- **Eliminar** (recomendado): antes, un vistazo de 2 min a su tabla por si hay
  alguna idea de presentacion que llevar al panel del viewer web; si no, fuera.

El Director quiere revisarla antes de decidir. NO tocar sin su visto bueno.

---

## MEJ-1 — Red de seguridad automatizada: suite pytest + gate de regresion en un comando

**Estado:** HECHO — 2026-07-04 (F1-F5 completas, rama `feature/mej-1-red-seguridad`).
Plan: `docs/PLAN_MEJORA_1_RED_SEGURIDAD.md`.
**Evidencia de cierre:**
- `python -m pytest -q` -> 58 passed, 1 skipped (bug WOs sobredimensionadas
  documentado), 1 deselected (gate), ~1.3 s.
- `python scripts/regression_gate.py` -> `[OK] GATE PASS` byte-identico modulo
  EOL (sha normalizado `4a208831…`, 5.367.492 bytes; equivale al historico
  `a4ae8d4e…` con CRLF) en ~13-17 s.
- CI GitHub Actions EN VERDE (ubuntu): pytest + run_migration + gate. El SHA
  normalizado de Windows == el de Linux (determinismo multiplataforma probado).
- Prueba de fuego (sabotaje `max_wos_por_tour` 20->19): suite en ROJO
  (`assert 19 == 20`), revertido, verde de nuevo. El sabotaje ademas destapo y
  corrigio un test debil (ES-01 ahora cubre defaults con config vacio).
- `git diff src/` vacio: el motor NO se toco.
**Piezas:** `pytest.ini`, `tests/conftest.py`, `tests/unit/*` (7 modulos, 59 tests),
`tests/baseline.json`, `scripts/regression_gate.py`, `tests/test_gate_smoke.py`
(marker `gate`), targets `make test` / `make gate` / `run test` / `run gate`,
CI `.github/workflows/tests.yml` (F5). Legacy en `_legacy/tests_gui/`.
**Prioridad:** Alta (protege todas las demas mejoras; primera en el orden acordado 1 -> 3 -> 2)
**Origen:** Revision independiente de Cerebellum (2026-07-04), no derivada del backlog previo.

### El problema
El proyecto no tiene NINGUNA prueba automatizada funcional. `tests/` es 100% legacy
(tests del dashboard PyQt6, del viewer Pygame y de la tecla "O" — todo archivado o
borrado). La unica proteccion real es el gate byte-identico (`WAREHOUSE_SEED=42` ->
SHA `a4ae8d4e…`) ejecutado A MANO cada vez. Todo el valor acumulado (Allocation Layer,
INIT-4, capa de congestion) depende de disciplina manual: un refactor descuidado en
`dispatcher.py` pasaria inadvertido.

### Que se hara (resumen; detalle en el plan)
1. Cuarentena del `tests/` legacy (git mv a `_legacy/tests_gui/`).
2. Suite pytest nueva y minima pero real: unit tests de dispatcher (estrategias,
   prioridad C2, olas C3), allocation (coerciones, asignacion multi-ubicacion),
   validacion de config web.
3. `scripts/regression_gate.py`: corre la sim con semilla 42 y compara SHA256 del
   `.jsonl` contra el baseline registrado. Un comando, veredicto PASS/FAIL.
4. (Opcional, decision del Director) workflow de GitHub Actions.

---

## MEJ-2 — Rigor estadistico: experiment runner con replicas y comparacion A/B

**Estado:** HECHO (v1) — 2026-07-04, en `main`. `scripts/experiment_runner.py`.
**Evidencia de cierre v1:**
- Modo `run`: N replicas (default 5, `--base-seed` default 1000) via subprocess
  aislado a `entry_points/run_generate_replay.py` (mismo patron que
  `regression_gate.py`), cada una con `WAREHOUSE_SEED` distinto y
  `--output-metrics`. Agrega media/desviacion muestral/IC 95% (t-Student,
  `scipy.stats.t`) por KPI.
- Modo `compare`: dos configs (A/B), semillas pareadas, `scipy.stats.ttest_rel`
  por KPI -> veredicto "DIFERENCIA SIGNIFICATIVA" (p<0.05) / "RUIDO" / caso
  borde "IDENTICO" o "constante" cuando la varianza de las diferencias es 0
  (el t-test da 0/0=nan; se detecta explicitamente para no reportar "ruido"
  de forma enganosa).
- KPIs v1 (cero cambios al motor, cero riesgo de gate): reusa literal
  `export_optimization_metrics()` ya existente — completadas, fallidas,
  tiempo de simulacion, tiempo promedio de completado; agrega
  `throughput_wo_per_s` derivado.
- Salida: tabla ASCII en consola + `--output archivo.xlsx` opcional (hojas
  Replicas_A/B, Resumen_A, Comparacion_AB via pandas/openpyxl).
- Limpieza automatica de `output/simulation_*` por replica (salvo
  `--keep-output`), igual que el gate.
- Dependencia nueva: `scipy>=1.10.0` (requirements.txt) para IC 95%/t-test
  real (decision del Director: preferido sobre implementar tablas t a mano).
- Tests: `tests/unit/test_experiment_runner.py` (7 tests, agregacion
  estadistica con datos sinteticos, sin correr la sim). Suite 80 passed.
  Gate re-verificado PASS (`c6f129ef…`, motor intacto).
- Validado manualmente: `run` con 3 replicas de una config reducida (20
  ordenes) y `compare` con dos variantes (una identica -> "IDENTICO"; una con
  menos operarios -> diferencia real detectada, p>0.05 a N=4 replicas — el
  caso de uso exacto que BK-03 necesitaba y no tuvo).

**Diferido a v2 (decision del Director, 2026-07-04):** extender
`export_optimization_metrics()` con `service_level` (fill-rate/backorders,
mismo patron que INIT-5) para que `compare` pueda dar veredicto estadistico
tambien sobre nivel de servicio, no solo throughput/tiempo. No se hizo en v1
porque toca el motor (nuevo campo en el .jsonl via metadata) y dispara el
gate/baseline; v1 se mantuvo deliberadamente sin riesgo para el motor.
Cuando se retome: reusar `core/replay_utils.build_service_level_summary()`
dentro de `export_optimization_metrics()`, actualizar baseline con
`--update-baseline --yes`, y agregar la clave a `ALL_KPI_KEYS` en
`experiment_runner.py`.

**Prioridad:** Alta (valor de producto: convierte corridas-anecdota en decisiones)
**Origen:** Revision independiente de Cerebellum (2026-07-04).

### El problema
El proposito del producto es tomar decisiones (detectar cuellos de botella, comparar
configuraciones), pero en modo produccion la sim es estocastica y cada corrida es una
anecdota de N=1. El propio experimento BK-03 sufrio esto: con N=3 la conclusion quedo
"dentro del ruido estadistico". Ademas el runner web mata la sim a los 600 s
(`web_prototype/simulation_runner.py`, TIMEOUT_SECONDS), inservible para lotes.

### Que se hara (a planificar cuando llegue su turno)
- Experiment runner (CLI primero): correr N replicas de una config con semillas
  distintas, agregar KPIs (media, desviacion, IC 95%).
- Modo comparacion: dos configs (A/B), mismas semillas pareadas, veredicto
  estadistico (diferencia significativa o ruido) por KPI.
- Salida: tabla resumen (consola + Excel); integracion web despues (fuera del
  timeout de 600 s del runner interactivo).
- Reusar `WAREHOUSE_SEED` y `--config` / `--output-metrics` ya existentes en
  `entry_points/run_generate_replay.py`.

---

## MEJ-3 — Esquema unico de configuracion (pydantic) + purga de claves duplicadas/muertas

**Estado:** HECHO — 2026-07-04 (rama `feature/mej-3-config-schema`).
**Evidencia de cierre:**
- `src/core/config_schema.py`: esquema pydantic unico con cada clave anotada con
  su LECTOR real. Consumido por el motor (`core/config_manager.py`, loguea
  `[CONFIG][SCHEMA][WARN/ERROR]`, no muta ni bloquea) y por la web
  (`web_prototype/config_manager.validate_config`: tipos invalidos BLOQUEAN el
  guardado; claves desconocidas/legacy -> warning en log).
- Un typo tipo `priority_dispatch_enable` ya NO pasa en silencio.
- **Purga ejecutada** (config.json + defaults core/web + app.js + index.html):
  `num_operarios`, `num_ground_operators`, `num_forklifts`, `num_work_orders`,
  `tareas_zona_a/b`, `assignment_rules`, `capacidad_montacargas`,
  `tiempo_descarga_por_tarea`, y DOS CONTROLES DE UI QUE NO HACIAN NADA:
  "Capacidad del Carro" (`capacidad_carro`) y "Escala del Mapa" (`map_scale`) —
  el motor jamas los leyo. En `congestion`: purgadas las 9 claves F3 del enfoque
  jubilado (`wait_timeout`, `wait_hard_cap`, `backoff_*`, `max_repath`,
  `repath_cost_factor`, `watchdog_window`, `allow_swap`, `aging_rate`);
  conservadas las vivas (`staggered_start`, `spawn_offset`, `timewindow.*`).
- CONSERVADAS: `num_operarios_terrestres`/`num_montacargas` (fallback vivo del
  motor con `agent_types: []`) y `num_operarios_total` (legacy-informativa,
  exigida por `REQUIRED_KEYS`).
- **El gate ATRAPO la purga** (FAIL inicial): el `.jsonl` incrusta el config en
  la metadata `SIMULATION_START`. Verificado que los 11.879 eventos son
  identicos (sha sin linea 1 = `98cc021b…` en ambos) -> cambio solo de metadata,
  baseline regenerado (`662ed5e3…`) con el flujo documentado.
- Suite: 67 passed (9 tests nuevos de esquema SC-01..09) + gate PASS.
**Prioridad:** Media-Alta (correctitud: mata una clase entera de bugs silenciosos)
**Origen:** Revision independiente de Cerebellum (2026-07-04). Es la causa raiz bajo INIT-3.

### El problema
`config.json` arrastra claves solapadas y parcialmente muertas:
`num_operarios_terrestres` vs `num_ground_operators` vs `num_operarios` vs
`num_operarios_total`; `num_work_orders` vs `total_ordenes`; `tareas_zona_a/b`;
`assignment_rules` vacio. El motor lee todo con `.get()` y defaults silenciosos.
Consecuencias reales:
- El optimizador Optuna solo ajusta claves legacy (`num_operarios_terrestres`)
  mientras la UI escribe `agent_types` — la causa profunda de INIT-3.
- Cualquier flag mal escrito (`priority_dispatch_enable` sin la "d") se ignora sin aviso.
- Viola el espiritu de la Ley #3: una sola fuente de verdad, pero con cuatro dialectos.

### Que se hara (a planificar cuando llegue su turno)
- Modelo pydantic unico (pydantic ya esta en requirements por FastAPI) compartido
  por motor (`core/config_manager.py`) y web (`web_prototype/config_manager.py`).
- Warning (o rechazo) de claves desconocidas; inventario y purga de claves muertas
  del `config.json` canonico.
- Validado con el gate byte-identico de MEJ-1 (por eso va despues de MEJ-1).
- Alinea de paso al optimizador con el esquema real (adelanta parte de INIT-3).

---

## MEJ-4 — Completar el sistema anti-colisiones: dwell + fallback visible

**Estado:** HECHO — 2026-07-04 (rama `feature/mej-4-anticolisiones`, mergeada a
`main` por fast-forward el mismo dia). Analisis, iteraciones y resultados
completos: `docs/PLAN_MEJORA_4_ANTICOLISIONES.md` §4.
**Resultado:** co-ocupaciones 28 -> 9 (cero amontonamientos, max 2 por celda),
planner reescrito estilo SIPP (salto al primer hueco + dominancia por intervalo;
0 fallos, coste 0.7 ms/plan, MEJOR que el original), fallback visible, clearance
0.05, parking idle disperso, invariante de tabla en 0. Baseline `c6f129ef…`.
**HALLAZGO makespan +55% (2011 -> 3121 s): REDEFINIDO como INIT-6, no como
tuning.** El Director aclaro (2026-07-04) que la causa raiz no es "un unico
staging mal dimensionado" sino que **el dominio no modela destino/ruta**: cada
pedido deberia tener destino real (tienda o domicilio) y el staging deberia
consolidar por grupo de ruta (tiendas cercanas para un camion, o domicilios
para una ruta de reparto), no volcar todo a una celda unica. Ver **INIT-6**
mas abajo para el detalle. No se ataca con `outbound_staging_distribution` ni
`discharge_time` sueltos — esos serian parches sobre un modelo incompleto.
**Prioridad:** Alta (realismo del cuello de botella de staging/pasillos)
**Origen:** Analisis independiente de Cerebellum del sistema anti-colisiones
(Iniciativa 2 Opcion C), pedido por el Director el 2026-07-04.

### Resumen del diagnostico
La arquitectura (Cooperative A* + tabla de reservas espacio-temporales) es la
CORRECTA para esta escala — no se reemplaza. Pero esta incompleta: modela el
transito y NO la permanencia (dwell). Evidencia (corrida canonica seed 42):
**28 co-ocupaciones reales**; el staging 1 (celda 3,29) acumula 22 con hasta
los 4 agentes superpuestos descargando a la vez. `reserve_dwell()` existe en
`spacetime_planner.py` pero NO tiene callers (nunca se cableo). Consecuencia de
negocio: la congestion de staging — el cuello de botella mas realista — es
invisible y el throughput se sobreestima.

### Que se hara (detalle en el plan)
1. Cablear `reserve_dwell()` en picking/descarga/lifting (F1).
2. Fallback estatico visible: reserva best-effort + WARN (F2).
3. Spawn reservado (F3) y `clearance` expuesto en UI (F4, opcional).
4. Validacion: co-ocupaciones 28 -> ~0, cola visible en staging, baseline
   actualizado con el flujo del gate (F5).

---

## INIT-6 — Staging multi-destino por ruta (redefine el hallazgo makespan +55% de MEJ-4)

**Estado:** PENDIENTE — sin sprint asignado. Requiere Analisis de Causa Raiz +
Plan de Implementacion propios antes de tocar codigo (Ley #1).
**Prioridad:** Alta (correctitud fundacional del modelo de negocio outbound)
**Origen:** Decision del Director (2026-07-04) al cerrar el hallazgo de
makespan +55% de MEJ-4.

### El problema real (segun el Director)
El makespan +55% post-MEJ-4 no es un problema de tuning de congestion: es sintoma
de que **el dominio no modela destino ni ruta de entrega**. Hoy (verificar en
`outbound.py` / `order_strategies.py`) todo pedido completado va a un staging
unico e indiferenciado, sin importar a donde deberia salir fisicamente.

En un almacen real:
- Cada pedido tiene un **destino especifico**: una tienda (reposicion B2B) o el
  domicilio de un cliente (ultima milla B2C).
- El staging existe para **consolidar por ruta de camion**: pedidos de tiendas
  geograficamente cercanas se agrupan para que un solo camion las recorra en una
  ruta; pedidos de domicilios se agrupan por zona de reparto.
- Consecuencia: **no deberia existir "el staging"**, sino tantas
  zonas/colas de consolidacion como rutas activas, y la asignacion pedido ->
  staging deberia depender del destino/ruta asociado al pedido, no ser fija.

### Por que importa
Sin esto, cualquier metrica de staging (makespan, colas, co-ocupaciones) mide
un cuello de botella artificial (un solo punto de consolidacion) en vez del
cuello de botella real de un almacen con logistica de ultima milla o distribucion
a tiendas. Es una precondicion de correctitud para cualquier conclusion futura
sobre outbound, no solo un ajuste de KPI.

### Que hay que investigar antes de plantear el plan (Analisis de Causa Raiz)
1. `order_strategies.py` / archivo de ordenes: ¿existe ya algun campo de
   destino (tienda/domicilio/direccion) en los pedidos de entrada, o hay que
   incorporarlo al esquema?
2. `outbound.py`: como se define hoy el/los staging (¿celda fija en el TMX?
   ¿configuracion?) y como se le asigna una WO/pedido completado.
3. Layout (`layouts/WH1.tmx`): ¿hay mas de una zona de staging fisica ya
   dibujada en el mapa, o solo una?
4. Que se entiende operativamente por "ruta": ¿un agrupamiento estatico
   (config) de destinos, o algo que se calcula (clustering geografico) por
   corrida? Esto lo debe definir el Director antes de disenar el mecanismo de
   asignacion pedido -> staging.

### Que NO hacer todavia
No implementar parches sueltos (`outbound_staging_distribution`, `discharge_time`)
como sustituto de esto: serian curitas sobre un modelo que no tiene el concepto
de destino/ruta. Ese tipo de ajuste solo tiene sentido *despues* de decidir el
diseño de consolidacion multi-staging.

### Estimacion de esfuerzo
Alto — toca esquema de pedidos (destino), `outbound.py` (multi-staging),
posiblemente el layout TMX (nuevas zonas de staging), y la logica de asignacion
pedido->ruta->staging. Necesita su propia sesion de diseño con el Director antes
de estimar en detalle.

---

*Este documento se actualiza al detectar nuevos items en sesiones de desarrollo.
Para retomar BK-01, leer: `dispatcher.py` (router de estrategias)
y `web_prototype/static/web_configurator/index.html` (selector dispatch-strategy).
Para los INIT items, ver: `docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md`.*
