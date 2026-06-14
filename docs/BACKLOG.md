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

## BK-02 — (reservado para proximos items)

---

*Este documento se actualiza al detectar nuevos items en sesiones de desarrollo.
Para retomar BK-01, leer: `dispatcher.py` lineas 252-273 (router de estrategias)
y `web_prototype/static/web_configurator/index.html` (selector dispatch-strategy).*
