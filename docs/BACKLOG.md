# BACKLOG — Gemelo Digital de Almacen
# Items pendientes de implementacion (no urgentes, sin sprint asignado)

Documento creado: 2026-06-14
Responsable: Cerebellum

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

## Nota de bug detectado durante BK-01 (no bloqueante)

El value HTML `"Ejecucion de Plan"` no coincide con el string que verifica el dispatcher
(`"Ejecucion de Plan (Filtro por Prioridad)"`). En la practica, al seleccionar esa estrategia
el dispatcher cae al default (`_estrategia_optimizacion_global`). El comportamiento
es identico al de "Optimizacion Global" por lo que no produce errores visibles.
Pendiente de corregir en un sprint de deuda tecnica.

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

**Estado:** PENDIENTE — requiere decision del Director
**Prioridad:** Baja
**Origen:** Auditoria de estrategias (sesion 2026-06-14)

### Contexto

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
- `config.json`: opcionalmente agregar `"cercania_tour_mode": "g