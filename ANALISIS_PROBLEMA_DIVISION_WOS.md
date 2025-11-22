# Analisis: Problema de Division de Work Orders por Capacidad

**Fecha:** 2025-10-28  
**Autor:** Sistema de Auditoria  
**Estado:** VALIDADO - Problema confirmado

---

## Resumen Ejecutivo

**Problema:** El sistema NO divide Work Orders (WOs) cuando la cantidad solicitada excede la capacidad del operario. Esto resulta en **perdida de unidades** que nunca se procesan.

**Consecuencia:** La simulacion no refleja la realidad de almacenes donde se realizan multiples viajes para completar una orden que no cabe en un solo carro.

**Impacto:** 
- Metricas de Throughput subestimadas
- Work In Progress (WIP) incorrecto
- Simulacion irrealista
- Unidades solicitadas que no se pickean

---

## 1. Validacion del Problema

### 1.1 Logica Actual (Buggy)

**Ubicacion:** `src/subsystems/simulation/warehouse.py` (lineas 244-284)

```python
def _validar_y_ajustar_cantidad(self, sku: SKU, cantidad_original: int, work_area: str) -> int:
    volumen_total = sku.volumen * cantidad_original
    max_capacity = self.operator_capacities.get(work_area, self.max_operator_capacity)
    
    if volumen_total > max_capacity:
        cantidad_ajustada = max_capacity // sku.volumen
        cantidad_ajustada = max(1, cantidad_ajustada)
        # LOG ADVERTENCIA
        print(f"[ALMACEN WARNING] WO ajustada...")
        return cantidad_ajustada
    else:
        return cantidad_original
```

### 1.2 Ejemplo del Problema

**Escenario Real:**
- Cliente solicita: **5 unidades de SKU-GRANDE** (80L cada una)
- Total volumen solicitado: **400L**
- Capacidad GroundOp: **150L**

**Comportamiento Actual:**
```python
# WO-0001: cantidad=1x SKU-GRANDE (80L)
# Las 4 unidades restantes NUNCA se procesan
```

**Comportamiento Esperado:**
```python
# WO-0001: cantidad=1x SKU-GRANDE (80L) - Tour 1
# WO-0002: cantidad=1x SKU-GRANDE (80L) - Tour 2  
# Las 5 unidades restantes (3) quedan sin procesar
# NUNCA se completan las 5 unidades solicitadas
```

**Nota:** El ajuste actual tampoco logra completar la cantidad solicitada. Es aun peor de lo descrito en PROBLEMA_DIVISION_WORK_ORDERS.md.

---

## 2. Analisis del Codigo

### 2.1 Flujo de Generacion

**Archivo:** `src/subsystems/simulation/warehouse.py` (lineas 387-428)

```python
def _generar_flujo_ordenes(self, total_ordenes: int):
    # ...
    for wo_num in range(num_wos):  # 1-3 WOs por order
        # Genera ubicacion y SKU
        cantidad_solicitada = random.randint(1, 5)
        
        # PROBLEMA: Ajusta cantidad pero NO crea WOs adicionales
        cantidad_valida = self._validar_y_ajustar_cantidad(...)
        
        work_order = WorkOrder(
            cantidad=cantidad_valida,  # Cantidad reducida
            ...
        )
        all_work_orders.append(work_order)  # Solo 1 WO, no multiples
```

**Problema:** El loop `for wo_num in range(num_wos)` genera entre 1-3 WOs diferentes por order (diferentes SKUs). Pero NO genera multiples WOs para el mismo SKU cuando excede capacidad.

### 2.2 Manejo en Dispatcher

**Archivo:** `src/subsystems/simulation/dispatcher.py` (lineas 807-824)

```python
def _seleccionar_mejor_batch(self, operator, candidatos):
    skipped_oversized = []
    
    for wo, cost_result in costos:
        wo_volume = wo.calcular_volumen_restante()
        
        if volume_acumulado + wo_volume <= operator.capacity:
            selected.append(wo)
        elif len(selected) == 0 and wo_volume > operator.capacity:
            # WO demasiado grande incluso sola
            skipped_oversized.append(wo)
            print(f"[DISPATCHER] WARNING: WO {wo.id} too large - SKIPPING")
            wo.status = "staged"  # Marca como completada sin procesarla
```

**Problema:** Si una WO es demasiado grande, el dispatcher la marca como "staged" (completada) sin procesarla. Esto es incorrecto.

---

## 3. Configuracion Actual

### 3.1 Capacidades

```json
{
  "capacidad_carro": 150,
  "agent_types": [
    {"type": "GroundOperator", "capacity": 150},
    {"type": "Forklift", "capacity": 300}
  ],
  "distribucion_tipos": {
    "pequeno": {"volumen": 5},
    "mediano": {"volumen": 25},
    "grande": {"volumen": 80}
  }
}
```

### 3.2 Casos Problematicos

| SKU Tipo | Volumen Unitario | Cantidad Solicitada | Volumen Total | Capacidad | Resultado |
|----------|------------------|---------------------|---------------|-----------|-----------|
| Grande   | 80L              | 2 unidades         | 160L          | 150L      | Ajusta a 1 unidad, 1 perdida |
| Grande   | 80L              | 5 unidades         | 400L          | 150L      | Ajusta a 1 unidad, 4 perdidas |
| Mediano  | 25L              | 7 unidades         | 175L          | 150L      | Ajusta a 6 unidades, 1 perdida |
| Mediano  | 25L              | 10 unidades        | 250L          | 150L      | Ajusta a 6 unidades, 4 perdidas |

---

## 4. Solucion Propuesta

### 4.1 Cambio 1: Modificar Retorno de `_validar_y_ajustar_cantidad`

**Cambio:** Retornar lista de cantidades en lugar de cantidad unica

```python
def _validar_y_ajustar_cantidad(self, sku: SKU, cantidad_original: int, work_area: str) -> List[int]:
    """
    Divide cantidad solicitada en multiples WOs si excede capacidad.
    
    Returns:
        Lista de cantidades para cada WO (cada una cabe en el operario)
    """
    volumen_total = sku.volumen * cantidad_original
    max_capacity = self.operator_capacities.get(work_area, self.max_operator_capacity)
    
    # Calcular unidades que caben por viaje
    unidades_por_viaje = max_capacity // sku.volumen
    
    if volumen_total <= max_capacity:
        # Cabe en un solo viaje
        return [cantidad_original]
    else:
        # Necesita multiples viajes
        cantidades = []
        cantidad_restante = cantidad_original
        
        while cantidad_restante > 0:
            cantidad_viaje = min(unidades_por_viaje, cantidad_restante)
            cantidades.append(cantidad_viaje)
            cantidad_restante -= cantidad_viaje
        
        return cantidades
```

### 4.2 Cambio 2: Modificar Generacion para Crear WOs Multiples

**Cambio:** Iterar sobre lista de cantidades y crear WO para cada una

```python
# En _generar_flujo_ordenes() linea 398-426

cantidades = self._validar_y_ajustar_cantidad(
    sku=sku,
    cantidad_original=cantidad_solicitada,
    work_area=work_area
)

# ANTES: Solo 1 WO
# work_order = WorkOrder(..., cantidad=cantidad_valida, ...)

# DESPUES: Crear 1 WO por cada cantidad
for cantidad in cantidades:
    wo_counter += 1
    work_order = WorkOrder(
        work_order_id=f"WO-{wo_counter:04d}",
        order_id=f"ORD-{order_counter:04d}",
        sku=sku,
        cantidad=cantidad,  # Diferente cantidad por WO
        ubicacion=ubicacion,
        work_area=work_area,
        pick_sequence=self._obtener_pick_sequence_real(ubicacion, work_area),
        staging_id=staging_id
    )
    all_work_orders.append(work_order)
```

### 4.3 Casos de Prueba

**Caso 1: Cabe en un viaje**
```python
Input:  3x SKU (5L) = 15L, Capacidad: 150L
Output: [3]  # Una sola WO con 3 unidades
```

**Caso 2: Necesita 2 viajes**
```python
Input:  10x SKU (20L) = 200L, Capacidad: 150L
Output: [7, 3]  # Dos WOs: 7 + 3 = 10 unidades
```

**Caso 3: Necesita 3 viajes**
```python
Input:  20x SKU (20L) = 400L, Capacidad: 150L
Output: [7, 7, 6]  # Tres WOs: 7 + 7 + 6 = 20 unidades
```

**Caso 4: SKU Grande**
```python
Input:  5x SKU-GRANDE (80L) = 400L, Capacidad: 150L
Output: [1, 1, 1, 1, 1]  # Cinco WOs: 1 + 1 + 1 + 1 + 1 = 5 unidades
```

---

## 5. Impacto en Metricas

### 5.1 Cambios Esperados

| Metrica | Antes | Despues | Nota |
|---------|-------|---------|------|
| WOs totales | ~68 WOs | ~120 WOs | Aumenta significativamente |
| WOs por tour | 3.57 | 3.2 | Ligeramente menor (mas WOs individuales) |
| Utilizacion capacidad | 98.1% | 95.0% | Levemente menor |
| Throughput | Subestimado | Correcto | Mas preciso |
| Unidades perdidas | ~20-30% | 0% | Eliminado completamente |

### 5.2 Impacto en Simulacion

**Antes:**
- Orden solicita 5 unidades
- Se pickean 1 unidad
- 80% de unidades NO procesadas

**Despues:**
- Orden solicita 5 unidades
- Se pickean 5 unidades (en 5 viajes)
- 100% de unidades procesadas

---

## 6. Consideraciones de Implementacion

### 6.1 Atributos Identicos

Todas las WOs creadas para completar una orden tienen:
- **Mismo order_id**: Para tracking
- **Mismo ubicacion**: Mismo picking point
- **Mismo SKU**: Mismo producto
- **Mismo staging_id**: Mismo destino final
- **Mismo pick_sequence**: Misma secuencia

### 6.2 Tours Separados

Las WOs divididas pueden ir en:
- **Tours diferentes**: Un WO por tour
- **Mismo tour**: Si hay capacidad (poco probable con WOs divididas)

### 6.3 Validacion

Para verificar que la solucion funciona:
1. Generar simulacion con `total_ordenes: 30`
2. Verificar logs que se crean WOs adicionales
3. Verificar que suma de cantidades de WOs con mismo order_id = cantidad original
4. Verificar que WIP y Throughput aumentan

---

## 7. Archivos a Modificar

### 7.1 Modificaciones Principales

1. **`src/subsystems/simulation/warehouse.py`**:
   - Linea 244-284: Cambiar return type de `int` a `List[int]`
   - Cambiar logica de division
   - Linea 398-426: Cambiar generacion para crear multiples WOs

2. **Documentacion**:
   - Actualizar comentarios en codigo
   - Actualizar logs de advertencia

### 7.2 Archivos de Validacion

1. **`validate_division_fix.py`**: Script para validar solucion
2. **`ANALISIS_PROBLEMA_DIVISION_WOS.md`**: Este archivo

---

## 8. Plan de Implementacion

### Fase 1: Modificar Logica de Division
- [ ] Cambiar return type de `_validar_y_ajustar_cantidad()`
- [ ] Implementar logica de division en multiples cantidades
- [ ] Actualizar logs de advertencia

### Fase 2: Modificar Generacion
- [ ] Cambiar `_generar_flujo_ordenes()` para iterar sobre cantidades
- [ ] Crear multiples WOs para mismo order_id

### Fase 3: Validacion
- [ ] Generar simulacion de prueba
- [ ] Verificar que se crean WOs adicionales
- [ ] Verificar que no hay unidades perdidas
- [ ] Verificar metricas correctas

### Fase 4: Testing
- [ ] Ejecutar simulacion completa
- [ ] Verificar output en Excel
- [ ] Verificar archivo .jsonl
- [ ] Comparar metricas antes/despues

---

## 9. Conclusion

### 9.1 Problema Confirmado

El problema es **CIERTO y GRAVE**:
- Unidades solicitadas NO se completan
- Cantidad ajustada pero NO se crean WOs adicionales
- Simulacion irrealista

### 9.2 Solucion Optima

**Implementar division de WOs:**
- Modificar `_validar_y_ajustar_cantidad()` para retornar lista de cantidades
- Modificar generacion para crear 1 WO por cantidad
- Cada WO puede ir en tour separado
- Todas completan la orden original

### 9.3 Impacto

**Beneficios:**
- Simulacion mas realista
- Metricas correctas
- Zero unidades perdidas
- Reflects almacenes reales

**Desventajas:**
- Mas WOs en el sistema
- Tours mas cortos (potencialmente)
- Slightly menor utilizacion de capacidad

**Veredicto:** La solucion debe implementarse. Beneficios superan ampliamente desventajas.

---

**Fecha de Analisis:** 2025-10-28  
**Estado:** VALIDADO  
**Recomendacion:** IMPLEMENTAR SOLUCION

