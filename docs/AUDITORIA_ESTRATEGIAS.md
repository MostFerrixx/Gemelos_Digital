# AUDITORÍA DE ESTRATEGIAS — Gemelo Digital de Almacén
**Fecha:** 2026-06-14
**Autores:** Cerebellum (análisis de código) + Director (validación)
**Alcance:** Todas las estrategias de despacho, generación de órdenes y construcción de tours
**Archivos analizados:**
- `src/subsystems/simulation/dispatcher.py` (1318 líneas)
- `src/subsystems/simulation/order_strategies.py` (762 líneas)
- `src/subsystems/simulation/route_calculator.py`
- `src/tools/optimizer.py`
- `src/core/config_utils.py`
**Método:** Lectura directa del código fuente + rastreo de llamadas + E2E empírico con logs

---

## RESUMEN EJECUTIVO

| # | Estrategia | Tipo | Estado | En UI | Conservar? |
|---|---|---|---|---|---|
| D1 | FIFO Estricto | Despacho | **VÁLIDA** | NO | SÍ (simple, útil como baseline) |
| D2 | Optimización Global | Despacho | **VÁLIDA** | SÍ ✅ | SÍ (estrategia principal) |
| D3 | Ejecución de Plan | Despacho | **VÁLIDA** pero inaccesible (bug H-5) | NO ❌ | SÍ (corregir el bug) |
| D4 | Cercanía | Despacho | **VÁLIDA** | SÍ ✅ | SÍ (caso de uso real) |
| T1 | Tour Mixto (Multi-Destino) | Tour | **VÁLIDA** | SÍ ✅ | SÍ (modo por defecto) |
| T2 | Tour Simple (Un Destino) | Tour | **VÁLIDA** | SÍ ✅ | SÍ (staging único) |
| R1 | Greedy Nearest-Neighbor | Ruta | **MUERTA** (no se llama) | NO | A revisar |
| F1 | FIFO Simple | Fantasma | **FANTASMA** (no implementada) | NO | ELIMINAR referencia |
| F2 | Proximity-Based | Fantasma | **FANTASMA** (no implementada) | NO | ELIMINAR referencia |
| F3 | Zoning and Snake | Fantasma | **HUÉRFANA** (campo incorrecto) | NO | ELIMINAR referencia |
| G1 | Stochastic (generación) | Generación | **VÁLIDA** | SÍ ✅ | SÍ (modo por defecto) |
| G2 | Deterministic (generación) | Generación | **VÁLIDA** | SÍ ✅ | SÍ (producción real) |

---

## SECCIÓN A — ESTRATEGIAS DE DESPACHO (dispatcher.py)

Estas estrategias determinan **cómo el dispatcher elige qué WorkOrders asignar
a cada operario** cuando este queda disponible.

### D1 — FIFO Estricto

| Campo | Valor |
|---|---|
| Archivo | `dispatcher.py` línea 275 |
| Función | `_estrategia_fifo(operator)` |
| Router | `self.estrategia == "FIFO Estricto"` |
| Estado | **VÁLIDA — código completo y funcional** |
| En UI | **NO** — no hay opción en el selector |

**Código clave:**
```python
candidatos = [wo for wo in self.work_orders_pendientes
             if operator.can_handle_work_area(wo.work_area)]
selected = []
volume_acumulado = 0
for wo in candidatos[:self.max_wos_por_tour]:
    wo_volume = wo.calcular_volumen_restante()
    if volume_acumulado + wo_volume <= operator.capacity:
        selected.append(wo)
        volume_acumulado += wo_volume
    else:
        break
return selected
```

**Qué hace en términos simples:**
El operario agarra las primeras WorkOrders de la cola (en el orden en que llegaron),
sin importar dónde están ubicadas ni cuánto tendría que caminar. Llena su carro hasta
que no cabe más, de adelante hacia atrás de la lista. Es la estrategia más simple
posible: sin inteligencia, solo orden de llegada.

**Cuándo sirve:**
- Como baseline de comparación para medir cuánto mejoran las otras estrategias.
- Cuando el almacén tiene poco stock y cualquier orden de picking es aceptable.
- En pruebas rápidas donde queremos que el sistema procese WOs lo más predeciblemente posible.

**Nota:** El nombre en el código es "FIFO Estricto". El optimizer.py menciona
"FIFO Simple" — ese string NO es reconocido por el dispatcher (ver F1).

---

### D2 — Optimización Global

| Campo | Valor |
|---|---|
| Archivo | `dispatcher.py` línea 303 |
| Función | `_estrategia_optimizacion_global(operator)` |
| Router | `self.estrategia == "Optimizacion Global"` |
| Estado | **VÁLIDA — estrategia principal del sistema** |
| En UI | **SÍ** — primera opción del selector, marcada "(Recomendado)" |

**Qué hace en términos simples:**
El operario tiene que elegir qué llevar en su próximo viaje. Esta estrategia hace dos cosas:

1. **Elige el primer producto de forma inteligente:** calcula cuánto cuesta (en distancia)
   ir a buscar cada producto desde donde está parado el operario ahora mismo. Elige el
   que queda más cerca y es del área de trabajo prioritaria para ese operario.

2. **Llena el resto del carro en orden lógico:** a partir de ese primer producto, agrega
   más productos del mismo pasillo siguiendo la secuencia de picking del Excel (de
   izquierda a derecha o del número más chico al más grande). Si sobra espacio, también
   busca productos de las pasadas anteriores del pasillo que se saltó (el "segundo barrido").

**Cuándo sirve:** Es la estrategia más inteligente para reducir distancias recorridas
cuando las WorkOrders están dispersas por distintos pasillos. Equilibra bien la
distancia de acceso con el aprovechamiento del carro.

---

### D3 — Ejecución de Plan

| Campo | Valor |
|---|---|
| Archivo | `dispatcher.py` línea 346 |
| Función | `_estrategia_ejecucion_plan(operator)` |
| Router | `self.estrategia == "Ejecucion de Plan (Filtro por Prioridad)"` |
| Estado | **VÁLIDA — código completo, pero INACCESIBLE por bug H-5** |
| En UI | **NO** (la UI envía `"Ejecucion de Plan"` sin el sufijo; el dispatcher no lo reconoce) |

**El bug:** La UI envía `"Ejecucion de Plan"` pero el dispatcher compara contra
`"Ejecucion de Plan (Filtro por Prioridad)"`. El string no coincide → WARN → fallback
a Optimización Global. El usuario cree que está usando esta estrategia pero en realidad
no. Ver H-5 en VALIDACION_UI_WEB.md.

**Qué hace en términos simples:**
Es casi igual a Optimización Global, pero con **una diferencia clave en cómo elige
el primer producto:** en lugar de calcular costos de distancia, simplemente toma el
producto con el número de secuencia más bajo dentro del área de mayor prioridad del
operario. Es decir: "empieza siempre por el producto número 1 de la lista, sin importar
dónde estés parado".

**Cuándo sirve:** Cuando hay un plan de picking predefinido (el Excel) y se quiere que
los operarios lo sigan al pie de la letra, sin que el sistema decida por sí solo
dónde arrancar. Útil en operaciones donde el supervisor ya ordenó las prioridades.

**Diferencia clave vs Optimización Global:**
- Optimización Global: primer producto = el más cercano al operario (según costos).
- Ejecución de Plan: primer producto = el de menor número de secuencia en la lista.
El resto del tour se construye igual en ambas.

---

### D4 — Cercanía

| Campo | Valor |
|---|---|
| Archivo | `dispatcher.py` línea 735 |
| Función | `_estrategia_cercania(operator)` |
| Router | `self.estrategia == "Cercania"` |
| Estado | **VÁLIDA — código completo y funcional** |
| En UI | **SÍ** — tercera opción del selector, con campo `radio_cercania` (BK-01) |

**Qué hace en términos simples:**
El operario solo considera los productos que están dentro de un radio determinado
desde donde está parado ahora mismo. Si hay productos a 200 metros y el radio es 100
celdas, esos productos directamente no existen para esta vuelta. Con los que quedan
dentro del radio, elige el mejor conjunto usando una función de costo (como Optimización
Global, pero solo entre los vecinos).

**Cuándo sirve:** Cuando el almacén es muy grande y tiene productos dispersos, y se
prefiere que cada operario "trabaje su zona" en lugar de cruzar todo el depósito para
buscar un solo producto. Reduce los trayectos largos a costa de potencialmente dejar
productos sin piquear si nadie pasa cerca.

**Parámetro:** `radio_cercania` (default 100 celdas). Si el operario no tiene
posición conocida, hace fallback a FIFO Estricto.

---

## SECCIÓN B — MÉTODOS INTERNOS DE CONSTRUCCIÓN DE TOUR (dispatcher.py)

Estos no son "estrategias seleccionables" sino helpers internos que implementan
el algoritmo de construcción del tour una vez que se eligió la primera WorkOrder.

### TC1 — Doble Barrido por Secuencia (`_construir_tour_por_secuencia`)

| Campo | Valor |
|---|---|
| Archivo | `dispatcher.py` línea 509 |
| Estado | **VÁLIDA — algoritmo principal de construcción de tours** |
| Usada por | D2 (Optimización Global) y D3 (Ejecución de Plan) |

**Qué hace:** Una vez elegida la primera WorkOrder del tour, este algoritmo llena el
resto del carro con dos pasadas:
- **Pasada 1 (progresiva):** agrega productos con número de secuencia mayor o igual
  al de la primera WO, avanzando hacia adelante en el pasillo.
- **Pasada 2 (circular):** si sobra espacio, vuelve al inicio del pasillo y busca
  productos que quedaron atrás (con número de secuencia menor). Minimiza retrocesos.

**Por qué existe:** Maximiza la utilización del carro (menos viajes = más throughput)
manteniendo una ruta sensata (no zigzaguea hacia atrás innecesariamente).

### TC2 — Tour Final (`_construir_tour`)

| Campo | Valor |
|---|---|
| Archivo | `dispatcher.py` línea 833 |
| Estado | **VÁLIDA — wrapper final que delega en RouteCalculator** |
| Usada por | Todas las estrategias (D1-D4) vía `asignar_trabajo()` |

**Qué hace:** Recibe la lista de WOs seleccionadas y las envía a `RouteCalculator`
para calcular la ruta física real (qué camino recorre el operario en el mapa TMX).
También aplica `preserve_first=True` cuando la estrategia es Optimización Global
(para que la WO más barata elegida por costo no se reordene).

### TC3 — Selección por Costo (`_seleccionar_mejor_batch`)

| Campo | Valor |
|---|---|
| Archivo | `dispatcher.py` línea 766 |
| Estado | **VÁLIDA — helper de scoring por costo** |
| Usada por | D4 (Cercanía) y fallback genérico |

**Qué hace:** De una lista de candidatos, elige el mejor subconjunto usando la
función de costo `AssignmentCostCalculator` (distancia + prioridad). Maneja el caso
borde de WOs cuyo volumen excede la capacidad del operario (las marca como staged
para evitar deadlocks).

---

## SECCIÓN C — CÓDIGO MUERTO / FANTASMA

### R1 — Greedy Nearest-Neighbor (`calculate_greedy_nearest_neighbor`)

| Campo | Valor |
|---|---|
| Archivo | `route_calculator.py` línea 319 |
| Estado | **MUERTA — implementada pero nunca se llama** |
| En UI | NO |

**Qué debía hacer:** Reordenar WorkOrders usando el heurístico del vecino más
cercano: desde la posición actual, siempre ir al producto más cercano, y desde ahí
al siguiente más cercano, y así sucesivamente. Un TSP greedy básico.

**Por qué está muerta:** El comentario en el código dice "May be used if
config.dispatch_strategy == 'Cercania'" pero esa integración nunca se hizo.
La estrategia Cercanía (D4) filtra por radio y luego usa `_seleccionar_mejor_batch`,
no este método. No hay ningún `import` ni llamada a `calculate_greedy_nearest_neighbor`
en ningún otro archivo del proyecto.

**Recomendación:** Evaluar si conviene integrarla como una variante del tour de
Cercanía (reordenar por vecino más cercano en lugar de por costo), o eliminarla.
No es urgente.

---

### F1 — "FIFO Simple" (referencia fantasma)

| Campo | Valor |
|---|---|
| Archivo | `optimizer.py` línea 117 |
| Estado | **FANTASMA — string en optimizer que no existe en dispatcher** |
| En UI | NO |

El optimizer Optuna prueba `"FIFO Simple"` como valor de `dispatch_strategy`.
El dispatcher no tiene ningún `elif self.estrategia == "FIFO Simple"` → cae al
`else` → `[DISPATCHER WARN]` → ejecuta Optimización Global silenciosamente.

El optimizer está optimizando con una estrategia que **nunca se aplica realmente**.
La estrategia equivalente que SÍ existe es `"FIFO Estricto"` (D1).

**Recomendación:** Corregir el optimizer para usar `"FIFO Estricto"` en lugar de
`"FIFO Simple"`.

---

### F2 — "Proximity-Based" (referencia fantasma)

| Campo | Valor |
|---|---|
| Archivo | `optimizer.py` línea 118 |
| Estado | **FANTASMA — string en optimizer que no existe en dispatcher** |
| En UI | NO |

Igual que F1: el optimizer prueba `"Proximity-Based"` pero el dispatcher no la
reconoce. Al ejecutarse, silenciosamente usa Optimización Global. La estrategia
equivalente que SÍ existe es `"Cercania"` (D4).

**Recomendación:** Corregir el optimizer para usar `"Cercania"` en lugar de
`"Proximity-Based"`.

---

### F3 — "Zoning and Snake" (campo huérfano)

| Campo | Valor |
|---|---|
| Archivo | `src/core/config_utils.py` línea 21 |
| Estado | **HUÉRFANA — en campo incorrecto, nunca leída** |
| En UI | NO |

Está en `config_utils.py` bajo la clave `'strategy'` (no `'dispatch_strategy'`).
El dispatcher lee `configuracion.get('dispatch_strategy', ...)` — nunca lee `'strategy'`.
Además, `config_utils.py` es parte del código considerado muerto/legacy según
`CLAUDE.md` (fuera del árbol vivo). Nunca se implementó esta estrategia en ningún dispatcher.

**Recomendación:** Ignorar. Al limpiar config_utils.py en la fase de poda, desaparece sola.

---

## SECCIÓN D — ESTRATEGIAS DE GENERACIÓN DE ÓRDENES (order_strategies.py)

Estas estrategias determinan **de dónde vienen las WorkOrders** al inicio de la
simulación. Son independientes de las estrategias de despacho.

### G1 — Stochastic (aleatoria)

| Campo | Valor |
|---|---|
| Archivo | `order_strategies.py` línea 114 |
| Clase | `StochasticOrderStrategy` |
| Activación | `order_generation_mode: "stochastic"` (default) |
| Estado | **VÁLIDA — funciona correctamente** |
| En UI | SÍ (modo por defecto) |

**Qué hace:** Genera WorkOrders aleatorias basándose en la configuración: número
total de órdenes, distribución por tamaño (pequeño/mediano/grande) y distribución
de staging. Ideal para pruebas y demostraciones donde no se tiene un pedido real.

---

### G2 — Deterministic (desde archivo)

| Campo | Valor |
|---|---|
| Archivo | `order_strategies.py` línea 229 |
| Clase | `DeterministicOrderStrategy` |
| Activación | `order_generation_mode: "deterministic"` + `order_file_path` |
| Estado | **VÁLIDA — código completo y robusto** |
| En UI | SÍ (requiere cargar archivo JSON/CSV) |

**Qué hace:** Lee un archivo de órdenes reales (JSON o CSV), las valida contra el
catálogo de SKUs del almacén, y genera WorkOrders concretas. Soporta dos políticas
de cumplimiento: `ship_partial` (enviar lo que hay) y `fill_or_kill` (todo o nada).
Es la estrategia para producción con pedidos reales de clientes.

---

## SECCIÓN E — ESTRATEGIAS DE TIPO DE TOUR (dispatcher.py)

Estos no son estrategias de selección sino restricciones de construcción de tour.

### TT1 — Tour Mixto (Multi-Destino)

| Estado | En UI |
|---|---|
| **VÁLIDA** | SÍ ✅ |

Sin restricción de staging: el carro puede llevar productos para distintas zonas de
descarga en el mismo viaje. Maximiza la utilización del carro.

### TT2 — Tour Simple (Un Destino)

| Estado | En UI |
|---|---|
| **VÁLIDA** | SÍ ✅ |

Todas las WorkOrders del tour deben ir al mismo staging_id. El dispatcher filtra
por staging_id y valida consistencia. Útil cuando hay una zona de descarga específica
que debe completarse primero.

---

## TABLA RESUMEN PARA EL DIRECTOR

### Estrategias de despacho — estado actual

| Estrategia | Código | ¿Funciona si la llamas? | En UI | Acción sugerida |
|---|---|---|---|---|
| **FIFO Estricto** | D1 — completa | SÍ (si usas el string exacto) | NO | Exponer en UI (opción simple) |
| **Optimización Global** | D2 — completa | SÍ ✅ | SÍ ✅ | Conservar |
| **Ejecución de Plan** | D3 — completa | NO ❌ (bug H-5) | NO ❌ | Corregir string (bug H-5) |
| **Cercanía** | D4 — completa | SÍ ✅ | SÍ ✅ | Conservar |

### Código muerto / fantasmas — acción recomendada

| Elemento | Archivo | Acción |
|---|---|---|
| `calculate_greedy_nearest_neighbor` | `route_calculator.py:319` | Integrar o eliminar (no urgente) |
| `"FIFO Simple"` en optimizer | `optimizer.py:117` | Cambiar a `"FIFO Estricto"` |
| `"Proximity-Based"` en optimizer | `optimizer.py:118` | Cambiar a `"Cercania"` |
| `"Zoning and Snake"` | `config_utils.py:21` | Ignorar (código muerto) |

---

## RECOMENDACIÓN FINAL

**Conservar sin tocar:** D2 (Optimización Global), D4 (Cercanía), G1, G2, TT1, TT2, TC1, TC2, TC3 — todas funcionan correctamente.

**Prioridad alta (bug funcional):**
- **H-5:** Corregir el string de Ejecución de Plan para que la UI funcione. La estrategia está completamente implementada; solo falla el matching de string. Impacto: cualquier usuario que haya seleccionado "Ejecución de Plan" ha estado corriendo Optimización Global sin saberlo.

**Prioridad media (limpieza):**
- Corregir `optimizer.py` para usar `"FIFO Estricto"` y `"Cercania"` en lugar de los strings fantasma. El optimizer lleva tiempo optimizando con valores inválidos.
- Decidir si exponer FIFO Estricto en la UI (es útil como baseline de comparación).

**Prioridad baja:**
- Integrar o eliminar `calculate_greedy_nearest_neighbor` de route_calculator.


---

## APÉNDICE — CAMBIOS APLICADOS EN ESTA SESIÓN

> Fecha: 2026-06-14

### Fix H-5 — "Ejecucion de Plan" ahora funciona desde la UI

**Archivos modificados:** `src/subsystems/simulation/dispatcher.py`

Se añadieron dos alias en el dispatcher para que el string corto `"Ejecucion de Plan"`
(lo que envía la UI) sea reconocido correctamente:

**Punto 1 — Router de estrategias (línea ~266):** Se cambió el `elif` de comparación
exacta a un `in (...)` que acepta tres variantes: el alias corto, el string largo sin
tilde y el string largo con tilde.

**Punto 2 — Step 3 de asignación (línea ~209):** Se añadió `"Ejecucion de Plan"` al
tuple de estrategias que usan el tour preconstruido (en lugar de `_seleccionar_mejor_batch`).

**Validación:** simulación headless confirmada con log
`[DISPATCHER] Inicializado con estrategia: 'Ejecucion de Plan'` y construcción de
tour por doble barrido correcta. Sin WARN de estrategia desconocida.

---

### Fix Optimizer — strings fantasma reemplazados

**Archivos modificados:** `src/tools/optimizer.py`

El espacio de búsqueda de Optuna tenía 3 estrategias, 2 de ellas fantasmas:

| Antes (fantasma) | Después (real) |
|---|---|
| `"Ejecucion de Plan (Filtro por Prioridad)"` | `"Ejecucion de Plan"` (alias corto) |
| `"FIFO Simple"` | `"FIFO Estricto"` |
| `"Proximity-Based"` | `"Cercania"` |
| *(no existía)* | `"Optimizacion Global"` (añadida) |

Ahora Optuna prueba las 4 estrategias reales. Antes, 2 de las 3 opciones caían
silenciosamente a Optimización Global, sesgando los resultados.

---

### Limpieza de referencias fantasma

**Archivos modificados:** `src/core/config_utils.py`, `src/tools/optimizer.py`,
`src/subsystems/simulation/route_calculator.py`

- `config_utils.py`: eliminado campo `'strategy': 'Zoning and Snake'` (key huérfana
  que ningún módulo leeía). Actualizado `dispatch_strategy` default al alias corto.
- `optimizer.py`: actualizado fallback `dispatch_strategy` default al alias corto.
- `route_calculator.py`: documentado `calculate_greedy_nearest_neighbor` con
  instrucciones de integración futura (conservado sin activar).

---

### Estado de estrategias POST-SESIÓN

| Estrategia | Estado | En UI | Funciona si la llamas |
|---|---|---|---|
| Optimización Global | VÁLIDA | SÍ ✅ | SÍ ✅ |
| Ejecución de Plan | VÁLIDA | SÍ ✅ (H-5 corregido) | SÍ ✅ |
| FIFO Estricto | VÁLIDA | NO (candidata a exponer) | SÍ ✅ |
| Cercanía | VÁLIDA | SÍ ✅ | SÍ ✅ |

