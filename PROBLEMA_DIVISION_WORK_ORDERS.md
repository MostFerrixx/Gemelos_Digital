# Problema: Division de Work Orders por Capacidad

## Situacion Actual

### Flujo de Generacion

Cuando se crea una Work Order, el sistema valida que la cantidad solicitada quepa en el operario:

```python
# En warehouse.py linea 244-284
def _validar_y_ajustar_cantidad(self, sku: SKU, cantidad_original: int, work_area: str):
    volumen_total = sku.volumen * cantidad_original
    max_capacity = self.operator_capacities.get(work_area, self.max_operator_capacity)
    
    if volumen_total > max_capacity:
        cantidad_ajustada = max_capacity // sku.volumen  # Reduce cantidad
        return cantidad_ajustada
    else:
        return cantidad_original
```

### Ejemplo del Problema

**Caso**: Order pide 5 unidades de SKU "Grande-XXX" (80L cada uno)

```python
# Solicitado: 5x Grande-XXX = 400L
# Capacidad GroundOp: 150L

# RESULTADO ACTUAL:
WO-0001: Pick 1x Grande-XXX (80L)  # Se reduce a 1 unidad
# Las 4 unidades restantes NUNCA se pickean
```

## ¿Por Que Es Un Problema?

### Limitaciones Actuales:

1. **Perdida de unidades**: Si se solicitan 5 unidades y solo caben 3, las 2 restantes nunca se procesan.
2. **No hay re-trip logic**: No se crean Work Orders adicionales para completar la orden.
3. **Simulacion incompleta**: El simulador no refleja la realidad de almacenes donde:
   - Si no cabe todo en un viaje, se hacen múltiples viajes.
   - Cada viaje genera una WO separada.

### En Mundo Real:

```python
# LO QUE DEBERIA PASAR:
Order: Cliente pide 5x SKU-ABC de ubicacion (10,15)
Capacidad: 3 unidades por viaje

SE GENERARIAN:
  WO-0001: Pick 3x SKU-ABC @ (10,15) → Tour 1
  WO-0002: Pick 2x SKU-ABC @ (10,15) → Tour 2
```

## Ubicaciones del Codigo

### Archivo: `src/subsystems/simulation/warehouse.py`

**Linea 244-284**: Funcion `_validar_y_ajustar_cantidad()`
- Reduce cantidad pero NO divide en múltiples WOs

**Linea 387-428**: Funcion `_generar_flujo_ordenes()`
- Genera 1-3 WOs por Order
- Valida capacidad pero NO genera WOs adicionales

### Archivo: `src/subsystems/simulation/dispatcher.py`

**Linea 807-824**: Manejo de WOs que exceden capacidad
- Si un WO es demasiado grande, lo marca como "staged" (completado)
- NO intenta dividirlo

## Solucion Propuesta

### Cambios Necesarios:

#### 1. Modificar `_validar_y_ajustar_cantidad()` 

En lugar de solo reducir cantidad, retornar una lista de cantidades:

```python
def _validar_y_ajustar_cantidad(self, sku: SKU, cantidad_original: int, work_area: str) -> List[int]:
    """
    Divide la cantidad solicitada en múltiples WOs si excede capacidad.
    
    Returns:
        Lista de cantidades que debe tener cada WO
    """
    volumen_total = sku.volumen * cantidad_original
    max_capacity = self.operator_capacities.get(work_area, self.max_operator_capacity)
    
    # Calcular cuantas unidades caben por viaje
    unidades_por_viaje = max_capacity // sku.volumen
    
    if volumen_total <= max_capacity:
        # Cabe en un solo viaje
        return [cantidad_original]
    else:
        # Necesita múltiples viajes
        cantidades = []
        cantidad_restante = cantidad_original
        
        while cantidad_restante > 0:
            cantidad_viaje = min(unidades_por_viaje, cantidad_restante)
            cantidades.append(cantidad_viaje)
            cantidad_restante -= cantidad_viaje
        
        return cantidades
```

#### 2. Modificar la generacion para crear WOs multiples

```python
# En _generar_flujo_ordenes() linea 398-426

# ANTES:
cantidad_valida = self._validar_y_ajustar_cantidad(...)
work_order = WorkOrder(..., cantidad=cantidad_valida, ...)

# DESPUES:
cantidades = self._validar_y_ajustar_cantidad(...)  # Ahora retorna lista
for cantidad in cantidades:
    wo_counter += 1
    work_order = WorkOrder(
        work_order_id=f"WO-{wo_counter:04d}",
        order_id=order_id,
        sku=sku,
        cantidad=cantidad,  # Diferente cantidad por WO
        ubicacion=ubicacion,
        ...
    )
    all_work_orders.append(work_order)
```

## Casos de Prueba

### Test Case 1: Cabe en un viaje
```python
# Input: 3x SKU (5L) = 15L, Capacidad: 150L
# Output: [3]  # Una sola WO con 3 unidades
```

### Test Case 2: Necesita 2 viajes
```python
# Input: 10x SKU (20L) = 200L, Capacidad: 150L
# Output: [7, 3]  # Dos WOs: 7 + 3 = 10
```

### Test Case 3: Necesita 3 viajes
```python
# Input: 20x SKU (20L) = 400L, Capacidad: 150L
# Output: [7, 7, 6]  # Tres WOs: 7 + 7 + 6 = 20
```

## Impacto en Metricas

### WIP y Throughput:

- El numero de Work Orders aumentara (mas WOs por Order)
- WIP se calculara correctamente para unidades fraccionadas
- Throughput reflejara mejor la productividad real

### Ejemplo:

**Antes**: 30 Orders → ~68 WOs  
**Despues**: 30 Orders → ~120 WOs (si hay divisiones)

## Consideraciones

1. **Mismo order_id**: Todas las WOs creadas deben tener el mismo `order_id`
2. **Ubicacion**: Todas van a la misma ubicacion (mismo SKU, misma posicion)
3. **Staging**: Pueden tener el mismo staging_id
4. **Tour**: Pueden ir en tours separados (un WO por tour)

## Archivos a Modificar

1. `src/subsystems/simulation/warehouse.py`:
   - Linea 244-284: Cambiar return type y logica
   - Linea 398-426: Cambiar generacion para crear WOs multiples

2. **Documentacion**: Actualizar comentarios explicando la division

## Validacion

Para verificar que funciona:
1. Generar simulation con `total_ordenes: 30`
2. Verificar en logs que se crean WOs adicionales
3. Verificar que la suma de cantidades de WOs con mismo order_id = cantidad original
4. Verificar que WIP y Throughput se calculan correctamente

