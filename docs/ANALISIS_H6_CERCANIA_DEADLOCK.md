# ANÁLISIS H-6 — Deadlock de Cercanía con Radio Restrictivo
# Propuesta de solución orientada a operación real de almacén

**Fecha:** 2026-06-15
**Estado:** RESUELTO — Fix implementado y commiteado en `8a2fe86` (2026-06-15)
**Archivos involucrados:** `src/subsystems/simulation/dispatcher.py`
**Bug documentado en:** `docs/VALIDACION_UI_WEB.md` (sección VAL-COMP-3, Prueba B)

---

## 1. El problema: qué pasa y por qué

### Flujo de ejecución actual

Cuando el dispatcher recibe una solicitud de asignación bajo la estrategia Cercanía,
ejecuta `_estrategia_cercania(operator)`:

```python
# dispatcher.py — _estrategia_cercania(), líneas 743-773
for wo in self.work_orders_pendientes:
    if not operator.can_handle_work_area(wo.work_area):
        continue
    distance = math.sqrt((wo_x - op_x)**2 + (wo_y - op_y)**2)
    if distance <= self.radio_cercania:          # ← filtro DURO
        candidatos.append(wo)

return candidatos[:self.max_wos_por_tour * 2]   # ← puede retornar []
```

Si no hay ninguna WO dentro del radio, retorna una lista vacía. El caller en
`solicitar_asignacion()` lo detecta y retorna `None` al operario (línea 200–204):

```python
if not candidatos:
    print("[DISPATCHER] No hay candidatos viables para ...")
    return None
```

El operario, al recibir `None`, hace esto (operators.py, líneas 849–855):

```python
if tour is None:
    if self.almacen.simulacion_ha_terminado():
        break
    yield self.env.timeout(0.5)   # espera medio segundo simulado
    continue                       # vuelve a pedir asignación
```

### El bucle infinito

Cada operario repite este ciclo cada 0.5 segundos simulados:

```
solicitar_asignacion → _estrategia_cercania → [] → None → espera 0.5s → repite
```

`simulacion_ha_terminado()` verifica si hay WOs pendientes — y las hay (están fuera
del radio). Por eso nunca devuelve `True`. El resultado: la simulación corre
indefinidamente con el reloj SimPy avanzando en pasos de 0.5s mientras los operarios
giran en loop, las WOs pendientes siguen en la cola, y el sistema nunca termina.

### Evidencia de la prueba VAL-COMP (radio=15)

```
[DISPATCHER] t=135249.0s | Pending: 25 | Assigned: 0 | InProgress: 0 | Completed: 10
[DISPATCHER] No hay candidatos viables para GroundOperator_GroundOp-01
[DISPATCHER] No hay candidatos viables para GroundOperator_GroundOp-02
```

10 WOs completadas (las que estaban dentro del radio=15 desde la posición inicial).
25 WOs congeladas para siempre. Los 4 operarios solicitando cada 0.5s.

### Por qué ocurre: la raíz conceptual

El radio se codificó como un **filtro duro**: o la WO está dentro del radio o no
existe para el dispatcher. Esto tiene un defecto de diseño: si el radio se agota
(ya no quedan WOs pendientes dentro de él), el operario se "queda sin trabajo"
aunque haya trabajo disponible en el resto del almacén.

En una operación real, **el radio nunca sería un límite absoluto** — es una
preferencia de asignación, no una restricción de acceso.

---

## 2. La pregunta real: ¿qué haría un operario de verdad?

Imaginemos a Luís, un picador en el almacén, que trabaja bajo una política de
"asignación por cercanía": le asignan productos que están cerca de donde está parado,
para que no camine de más.

Luís termina su tour. Se para en el punto de descarga. El supervisor ve la lista de
pendientes y constata que todos los productos restantes están en el otro extremo del
almacén (a 20 metros de Luís, pero el radio configurado es 10 metros).

¿Qué hace Luís?

- **¿Se queda parado esperando que aparezca algo dentro de sus 10 metros?**
  Imposible. Ningún supervisor lo permitiría. Eso es tiempo muerto pagado.
- **¿Va directamente a buscar el producto más cercano aunque esté fuera de su "zona"?**
  Sí, eso es lo más natural. "No hay nada aquí, voy a lo más cercano".
- **¿Busca primero en su zona ampliada, luego más lejos si hace falta?**
  También plausible, especialmente si hay compañeros activos: "dejo que Marta lleve
  las cosas de su zona; si en 5 minutos no aparece nada para mí, voy yo también".
- **¿Prioriza las órdenes más urgentes o más antiguas en la cola aunque estén lejos?**
  Podría. Un supervisor diría: "lleva las de alta prioridad aunque estén lejos".

La respuesta correcta depende de la política del almacén. Pero lo que NUNCA haría
Luís es: quedarse parado para siempre. El sistema actual modela exactamente eso.

---

## 3. Opciones de solución

### Opción A — Radio Blando: Expansión Gradual del Radio

**Concepto:** Cuando el filtro por radio no encuentra candidatos, el dispatcher
expande el radio automáticamente en pasos (`factor_expansion`) hasta encontrar WOs
o hasta alcanzar un número máximo de expansiones. Si agota las expansiones, usa
todas las WOs compatibles (equivalente a radio=infinito).

**Pseudocódigo conceptual:**
```
radio_actual = radio_cercania
while no hay candidatos Y expansiones < max_expansiones:
    radio_actual = radio_actual * factor_expansion
    candidatos = filtrar_por_radio(radio_actual)
si aún vacío: usar todas las WOs compatibles (FIFO de área)
```

**Parámetros de configuración nuevos:**
```json
"radio_expansion_factor": 1.5,
"radio_max_expansiones": 3
```
Con `radio=15` y `factor=1.5`: expansiones en 22.5 → 33.75 → 50.6 → todas.

**Analogía real:** Luís revisa primero su pasillo, luego los dos pasillos adyacentes,
luego toda su sección, luego todo el almacén. Busca de más cercano a más lejano.

**Ventajas:**
- Modela fielmente el comportamiento humano de búsqueda en anillos concéntricos.
- Preserva el espíritu de Cercanía: el operario prioriza lo más próximo siempre.
- Genera analítica útil: ¿cuántas veces el operario tuvo que "salir de su zona"?
- Totalmente configurable sin cambiar la lógica de tour.

**Desventajas:**
- Más complejo de implementar (bucle de expansión, nuevos parámetros de config).
- Si el factor es agresivo, la primera expansión ya puede cubrir todo el almacén,
  anulando la diferencia con "ir al más cercano".
- El usuario tiene que entender y calibrar dos parámetros nuevos.

**Impacto en código:** Modificar solo `_estrategia_cercania()` (~10 líneas).
Agregar 2 campos a `config.json` y `config_manager.py`.

---

### Opción B — Fallback a la WO Más Cercana (Cercanía Garantizada)

**Concepto:** El radio es una preferencia de primer nivel. Si no hay candidatos
dentro del radio, el dispatcher abandona el filtro y selecciona la **única WO
compatible más cercana** (por distancia Euclidea) como âncora del tour. Desde esa
âncora, construye el tour normal por doble barrido.

**Pseudocódigo conceptual:**
```
candidatos = filtrar_por_radio(radio_cercania)
si candidatos vacío:
    wo_mas_cercana = min(work_orders_compatibles, key=distancia_al_operario)
    candidatos = [wo_mas_cercana]  ← âncora mínima garantizada
```

**Parámetros nuevos:** Ninguno. Opcional: un flag `cercania_fallback: true/false`
en config.json para quien quiera el comportamiento actual (deadlock incluido).

**Analogía real:** "No hay nada en mi zona — voy a la orden más cercana que quede
en el almacén." Es la decisión más natural e inmediata de un operario.

**Ventajas:**
- Elimina el deadlock con el mínimo de complejidad.
- Sin parámetros nuevos.
- El âncora fallback es siempre la WO óptima para minimizar la caminata inicial.
- La lógica de tour (doble barrido desde âncora) sigue intacta.
- Ya existe un método casi listo: `calculate_greedy_nearest_neighbor()` en
  `route_calculator.py` (BK-03), aunque para esta Opción solo necesitamos el
  primer elemento (la WO más cercana), no el tour completo.

**Desventajas:**
- Pierde granularidad: no hay etapas intermedias entre "dentro del radio" y
  "cualquier lugar del almacén". Un operario real podría preferir buscar primero
  en una zona intermedia.
- El cambio de comportamiento puede ser brusco si el radio se agota justo después
  del primer tour: pasa de "trabajo local" a "trabajo en el extremo opuesto".

**Impacto en código:** 4-6 líneas adicionales en `_estrategia_cercania()`.
Sin nuevos parámetros de config.

---

### Opción C — Radio como Peso, no Filtro (Scoring Continuo)

**Concepto:** En lugar de filtrar con un umbral duro, se puntúa TODAS las WOs
compatibles con una función que combina distancia y urgencia, donde las WOs cercanas
reciben un mejor puntaje. El radio pasa a ser el punto de inflexión de la función,
no el límite.

**Fórmula conceptual:**
```
score(WO) = distancia_al_operario + penalizacion_si_fuera_del_radio
penalizacion = max(0, distancia - radio) * factor_penalizacion
```
O equivalentemente, un multiplicador de costo: WOs dentro del radio cuestan `1x`,
fuera del radio cuestan `3x` o `10x`. El dispatcher siempre tiene candidatos.

**Analogía real:** "Prefiero fuertemente lo cercano, pero si no hay otra opción,
acepto lo lejano — con la penalización que eso implica en tiempo de viaje."

**Ventajas:**
- Nunca hay deadlock por diseño: siempre hay candidatos (score ≥ 0 para todos).
- Modela un continuo realista: no hay un salto brusco entre "dentro" y "fuera".
- Permite afinar el comportamiento con el factor de penalización.
- Es la formulación arquitectónicamente más correcta para una estrategia de
  optimización: transforma Cercanía en un problema de minimización de costo
  con preferencia local, igual que Optimización Global pero con función de
  costo diferente.

**Desventajas:**
- Requiere refactorizar más profundamente `_estrategia_cercania()` y su
  integración con `_seleccionar_mejor_batch()`.
- Introduce un parámetro de penalización que el usuario debe calibrar.
- La semántica del "radio" cambia: ya no es "solo trabajo de aquí adentro" sino
  "trabajo de aquí adentro preferido". Puede confundir si el usuario espera
  que el radio sea una restricción de zona.

**Impacto en código:** Refactor medio. Afecta `_estrategia_cercania()` y
potencialmente `_seleccionar_mejor_batch()` (~20-30 líneas).

---

## 4. Comparativa de opciones

| Criterio | A: Expansión Gradual | B: Fallback Más Cercana | C: Radio como Peso |
|---|---|---|---|
| Fidelidad al comportamiento real | Alta | Media-Alta | Alta |
| Simplicidad de implementación | Media | Alta | Baja |
| Parámetros nuevos de config | 2 | 0 | 1 |
| Preserva semántica de "radio" | Sí (zona preferida) | Parcialmente | No (pasa a preferencia continua) |
| Elimina deadlock | Sí | Sí | Sí |
| Analítica del comportamiento | Rica (expansiones registrables) | Simple | Rica (scores registrables) |
| Riesgo de regresión | Bajo | Muy bajo | Medio |

---

## 5. Recomendación de Cerebellum

**Recomendación: Opción B (Fallback a WO Más Cercana) como implementación inmediata,
con Opción A en el radar para el futuro.**

**Razonamiento:**

El problema central no es de sofisticación del algoritmo — es que el radio actúa
como un filtro que puede vaciarse. La solución correcta es garantizar que siempre
haya un resultado, y "ir a la WO más cercana disponible" es exactamente eso: el
mínimo de caminata cuando no hay nada local.

La Opción B es la traducción directa de la decisión más natural en el mundo real:
*"no hay nada aquí, me voy a lo más cercano"*. No requiere configuración, no cambia
la arquitectura del tour, y el impacto en código es mínimo y quirúrgico.

La Opción A (expansión gradual) agrega riqueza analítica y matiz, pero introduce
complejidad de calibración. Es ideal para una segunda iteración si el Director quiere
poder observar cuántas veces los operarios "salen de su zona" y por cuánto.

La Opción C, aunque arquitectónicamente elegante, cambia la semántica del radio de
forma que puede confundir (el usuario configura "radio=15 celdas" esperando que el
operario solo trabaje en ese radio, y en realidad significa algo más difuso). Es la
solución para cuando se quiera refactorizar la estrategia en profundidad.

**Sprint estimado para Opción B:** ~30 minutos (4-6 líneas de código + test headless).
**Sprint estimado para Opción A:** ~2 horas (lógica de expansión + 2 campos de config + tests).

---

## 6. Preguntas para el Director antes de implementar

1. **¿El radio es una preferencia o una restricción de zona?**
   - Si preferencia → Opción B o C.
   - Si restricción (operario NO debe salir de su zona nunca) → el deadlock es
     correcto y la solución es otra: detectar zona agotada y re-asignar operario
     a otra zona, o esperar nuevas órdenes en su zona.

2. **¿Interesa saber cuántas veces un operario "salió de su radio"?**
   - Si sí → Opción A (la expansión se puede registrar como evento en el JSONL).
   - Si no → Opción B es suficiente.

3. **¿Se mantiene el radio como parámetro de zona o se repiensa como intensidad
   de preferencia local?**
   - Si zona → B o A.
   - Si intensidad → C (refactor más profundo, decisión de diseño mayor).

---

*Documento generado por Cerebellum. Sin cambios en código. Listo para decisión del Director.*
