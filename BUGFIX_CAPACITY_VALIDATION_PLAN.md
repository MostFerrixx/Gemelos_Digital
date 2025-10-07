# BUGFIX PLAN: Validacion de Capacidad en Generacion de WorkOrders

**Fecha:** 2025-10-06
**Issue:** Deadlock de simulacion - WorkOrders generadas con volumen mayor a capacidad de operarios
**Estrategia:** Validacion y ajuste automatico de cantidad en punto de creacion
**Estado:** PLAN APROBADO - Pendiente de implementacion

---

## 1. DIAGNOSTICO DEL PROBLEMA

### Problema Identificado
El sistema genera WorkOrders con volumenes que exceden logicamente la capacidad de los operarios disponibles, causando un deadlock donde:

1. WorkOrder generada: `cantidad=5, sku.volumen=80` → volumen_total = **400**
2. GroundOperator disponible: `capacidad=150`
3. Resultado: **WorkOrder imposible de asignar** → bucle infinito

### Causa Raiz
**Ubicacion:** `src/subsystems/simulation/warehouse.py:227`

```python
# Linea 227 - PROBLEMA: Cantidad aleatoria sin validacion de capacidad
cantidad=random.randint(1, 5),
```

La cantidad se genera **antes** de validar si el volumen total es realizable.

### Impacto
- Simulacion no termina (bucle infinito)
- WorkOrders quedan en estado "pending" permanentemente
- No se genera archivo .jsonl de replay
- Prueba de aceptacion TPRF falla

---

## 2. ESTRATEGIA DE SOLUCION

### Regla de Negocio
**Al momento de crear cada WorkOrder:**

1. **Calcular volumen total:** `volumen_total = sku.volumen * cantidad`
2. **Determinar capacidad maxima:** Obtener capacidad del tipo de operario requerido
3. **Validar viabilidad:** Si `volumen_total > capacidad_maxima`:
   - Ajustar cantidad automaticamente: `cantidad = floor(capacidad_maxima / sku.volumen)`
   - Garantizar `cantidad >= 1` (minimo 1 unidad)

### Ventajas de esta Estrategia
✅ **No modifica arquitectura:** Solo ajusta datos de entrada
✅ **Garantiza viabilidad:** Todas las WorkOrders son asignables
✅ **Automatico:** No requiere intervencion manual
✅ **Conserva volumen maximo:** Usa toda la capacidad disponible
✅ **Evita deadlocks:** Eliminacion completa del problema

---

## 3. ANALISIS DE CODIGO

### 3.1. Punto de Generacion de WorkOrders

**Archivo:** `src/subsystems/simulation/warehouse.py`
**Metodo:** `_generar_flujo_ordenes()` (lineas 172-242)

**Codigo Actual (lineas 221-231):**
```python
# Create work order
work_order = WorkOrder(
    work_order_id=f"WO-{wo_counter:04d}",
    order_id=f"ORD-{order_counter:04d}",
    tour_id=f"TOUR-{order_counter:04d}",
    sku=sku,
    cantidad=random.randint(1, 5),  # <-- PROBLEMA AQUI
    ubicacion=ubicacion,
    work_area=work_area,
    pick_sequence=wo_counter
)
```

**Cambio Requerido:**
Reemplazar la generacion aleatoria de `cantidad` con logica de validacion.

---

### 3.2. Fuentes de Informacion de Capacidad

#### Opcion A: Usar configuracion de agent_types
**Archivo:** `config.json`
**Estructura:**
```json
"agent_types": [
    {
        "type": "GroundOperator",
        "capacity": 150,
        ...
    },
    {
        "type": "Forklift",
        "capacity": 1000,
        ...
    }
]
```

**Ventaja:** Fuente centralizada de verdad
**Desventaja:** Requiere parsear agent_types en warehouse.py

#### Opcion B: Consultar operarios creados
**Codigo:** `self.operarios` (lista de operarios)
**Ventaja:** Capacidades reales de operarios instanciados
**Desventaja:** Los operarios se crean DESPUES de las WorkOrders (problema de orden)

#### **DECISION: Opcion A** (agent_types de configuracion)
**Razon:** Disponible en el momento de generar WorkOrders, antes de crear operarios.

---

### 3.3. Mapeo de WorkArea a Equipment Type

**Problema:** Las WorkOrders tienen `work_area` pero necesitamos saber que tipo de operario las maneja.

**Fuente de Informacion:** `data/layouts/Warehouse_Logic.xlsx` - columna `equipment_required`

**Ubicacion en Codigo:**
- `src/subsystems/simulation/data_manager.py:256` - Carga `equipment_required` del Excel
- `self.data_manager.puntos_de_picking_ordenados[i]['equipment_required']` contiene el tipo

**Flujo Actual:**
1. WorkOrder se crea con `ubicacion` (tuple de coordenadas)
2. `ubicacion` viene de `picking_points[pick_idx]` (linea 218)
3. `picking_points` viene de `puntos_de_picking_ordenados` (linea 182)

**Conclusion:** Podemos obtener `equipment_required` del punto de picking correspondiente.

---

## 4. PLAN DE IMPLEMENTACION DETALLADO

### BUGFIX #11: Validacion de Capacidad en Generacion de WorkOrders

**Archivo a Modificar:** `src/subsystems/simulation/warehouse.py`
**Metodo:** `_generar_flujo_ordenes()` (lineas 172-242)

---

#### PASO 1: Construir Mapa de Capacidades (antes del loop)

**Ubicacion:** Linea 184 (despues de obtener picking_points)

**Logica:**
```python
# BUGFIX #11: Build capacity map from agent_types config
agent_types_config = self.configuracion.get('agent_types', [])
capacidades_por_tipo = {}

for agent_config in agent_types_config:
    agent_type = agent_config.get('type')
    capacity = agent_config.get('capacity', 150)  # Default 150

    # Store max capacity for each type (in case multiple agents of same type)
    if agent_type in capacidades_por_tipo:
        capacidades_por_tipo[agent_type] = max(
            capacidades_por_tipo[agent_type], capacity
        )
    else:
        capacidades_por_tipo[agent_type] = capacity

print(f"[ALMACEN] Capacidades por tipo de operario: {capacidades_por_tipo}")
```

**Resultado:**
```python
capacidades_por_tipo = {
    'GroundOperator': 150,
    'Forklift': 1000
}
```

---

#### PASO 2: Obtener Equipment Required para cada WO

**Ubicacion:** Linea 219 (despues de seleccionar ubicacion)

**Logica:**
```python
# Select picking location
pick_idx = wo_counter % len(picking_points)
ubicacion = picking_points[pick_idx]
work_area = work_areas[pick_idx] if pick_idx < len(work_areas) else "Area_Ground"

# BUGFIX #11: Get equipment type required for this location
equipment_required = "GroundOperator"  # Default
if self.data_manager and self.data_manager.puntos_de_picking_ordenados:
    if pick_idx < len(self.data_manager.puntos_de_picking_ordenados):
        punto_info = self.data_manager.puntos_de_picking_ordenados[pick_idx]
        equipment_required = punto_info.get('equipment_required', 'GroundOperator')
```

---

#### PASO 3: Calcular Cantidad Maxima Valida

**Ubicacion:** Linea 227 (reemplazar `cantidad=random.randint(1, 5)`)

**Logica:**
```python
# BUGFIX #11: Validate quantity against operator capacity
cantidad_deseada = random.randint(1, 5)  # Initial desired quantity
volumen_unitario = sku.volumen
capacidad_operario = capacidades_por_tipo.get(equipment_required, 150)

# Calculate max units that fit in operator capacity
cantidad_maxima = capacidad_operario // volumen_unitario

if cantidad_maxima < 1:
    # SKU is too big even for 1 unit - force 1 and log warning
    cantidad_ajustada = 1
    print(f"[ALMACEN] WARNING: SKU {sku.id} volumen ({volumen_unitario}) "
          f"excede capacidad de {equipment_required} ({capacidad_operario}). "
          f"Generando WO con 1 unidad (sobredimensionada).")
else:
    # Use desired quantity but cap at maximum
    cantidad_ajustada = min(cantidad_deseada, cantidad_maxima)

# If we had to reduce quantity, log it
if cantidad_ajustada < cantidad_deseada:
    print(f"[ALMACEN] INFO: WO {wo_counter} cantidad reducida de "
          f"{cantidad_deseada} a {cantidad_ajustada} para ajustar a capacidad "
          f"de {equipment_required} ({capacidad_operario})")
```

---

#### PASO 4: Crear WorkOrder con Cantidad Validada

**Ubicacion:** Linea 222 (modificar constructor)

**Logica:**
```python
# Create work order with validated quantity
work_order = WorkOrder(
    work_order_id=f"WO-{wo_counter:04d}",
    order_id=f"ORD-{order_counter:04d}",
    tour_id=f"TOUR-{order_counter:04d}",
    sku=sku,
    cantidad=cantidad_ajustada,  # BUGFIX #11: Use validated quantity
    ubicacion=ubicacion,
    work_area=work_area,
    pick_sequence=wo_counter
)
```

---

### PASO 5: Metricas de Validacion (opcional pero recomendado)

**Ubicacion:** Linea 241 (despues de agregar todas las WOs)

**Logica:**
```python
# BUGFIX #11: Report validation metrics
if hasattr(self, '_wo_validation_stats'):
    print(f"[ALMACEN] Estadisticas de validacion de capacidad:")
    print(f"  - WorkOrders ajustadas: {self._wo_validation_stats['ajustadas']}")
    print(f"  - WorkOrders sobredimensionadas: {self._wo_validation_stats['sobredimensionadas']}")
    print(f"  - WorkOrders sin cambios: {self._wo_validation_stats['sin_cambios']}")
```

---

## 5. CAMBIOS EN ARCHIVOS

### Resumen de Modificaciones

| Archivo | Lineas | Tipo de Cambio | Descripcion |
|---------|--------|----------------|-------------|
| `warehouse.py` | 184-192 | Nuevo codigo | Construir mapa de capacidades |
| `warehouse.py` | 219-226 | Nuevo codigo | Obtener equipment_required |
| `warehouse.py` | 227-242 | Modificacion | Validar y ajustar cantidad |
| `warehouse.py` | 222-231 | Modificacion | Usar cantidad_ajustada |

**Total Lineas Nuevas:** ~35 lineas
**Total Lineas Modificadas:** ~8 lineas

---

## 6. CASOS DE PRUEBA

### Caso 1: WorkOrder Valida (sin ajuste)
**Input:**
- SKU volumen: 5
- Cantidad deseada: 3
- Capacidad operario: 150

**Calculo:**
- volumen_total = 5 * 3 = 15
- cantidad_maxima = 150 / 5 = 30
- cantidad_ajustada = min(3, 30) = **3**

**Resultado:** ✅ Sin cambios

---

### Caso 2: WorkOrder Requiere Ajuste
**Input:**
- SKU volumen: 80
- Cantidad deseada: 5
- Capacidad operario: 150

**Calculo:**
- volumen_total = 80 * 5 = 400 (EXCEDE 150)
- cantidad_maxima = 150 / 80 = 1
- cantidad_ajustada = min(5, 1) = **1**

**Resultado:** ✅ Ajustada de 5 a 1 (log generado)

---

### Caso 3: WorkOrder Sobredimensionada (1 unidad no cabe)
**Input:**
- SKU volumen: 200
- Cantidad deseada: 2
- Capacidad operario: 150

**Calculo:**
- volumen_total = 200 * 2 = 400 (EXCEDE 150)
- cantidad_maxima = 150 / 200 = 0
- cantidad_ajustada = **1** (forzada, con warning)

**Resultado:** ⚠️ Sobredimensionada - se genera con 1 unidad (warning logueado)

**Nota:** Este caso REQUIERE manejo especial en dispatcher (BUGFIX #11b - opcional).

---

## 7. MANEJO DE CASOS ESPECIALES

### Caso Especial: SKU > Capacidad (1 unidad no cabe)

**Problema:** Que hacer cuando `sku.volumen > capacidad_operario`?

**Opciones:**

#### Opcion A: Generar WO con 1 unidad (sobredimensionada) ⚠️
**Pros:** No se pierden WorkOrders, datos completos
**Cons:** Dispatcher debe manejar caso especial (puede causar otro deadlock)

#### Opcion B: Saltar esta WO (no generarla) ❌
**Pros:** Solo genera WOs viables
**Cons:** Se pierden datos, simulacion incompleta

#### **DECISION: Opcion A con validacion en Dispatcher**
**Razon:** Mantener integridad de datos, delegar manejo especial a dispatcher.

**Implementacion Adicional Requerida (BUGFIX #11b):**
- Modificar `dispatcher.py:_seleccionar_mejor_batch()`
- Si `wo_volume > operator.capacity`, asignar de todas formas pero marcar como "oversized"
- Operario procesa esta WO sola (sin batch)

---

## 8. METRICAS DE EXITO

### Criterios de Aceptacion

✅ **Criterio 1:** Todas las WorkOrders generadas tienen `volumen_total <= capacidad_maxima` (excepto caso especial)
✅ **Criterio 2:** No hay WorkOrders en estado "pending" por tiempo infinito
✅ **Criterio 3:** La simulacion termina exitosamente (todas las WOs completadas)
✅ **Criterio 4:** Se genera archivo .jsonl de replay
✅ **Criterio 5:** Logs muestran cuantas WOs fueron ajustadas

### Metricas de Validacion

**Durante la generacion:**
```
[ALMACEN] Capacidades por tipo de operario: {'GroundOperator': 150, 'Forklift': 1000}
[ALMACEN] INFO: WO 0015 cantidad reducida de 5 a 1 para ajustar a capacidad de GroundOperator (150)
[ALMACEN] WARNING: SKU SKU-GRA-003 volumen (200) excede capacidad de GroundOperator (150). Generando WO con 1 unidad (sobredimensionada).
[ALMACEN] Generadas 600 WorkOrders
[ALMACEN] Estadisticas de validacion de capacidad:
  - WorkOrders ajustadas: 42
  - WorkOrders sobredimensionadas: 3
  - WorkOrders sin cambios: 555
```

**Durante la simulacion:**
```
[DISPATCHER] Tour asignado a GroundOperator_GroundOp-01: 4 WOs, distancia: 18.2
[GroundOp-01] t=0.0 Tour asignado: 4 WOs, distancia: 18.2
...
[DISPATCHER-PROCESS] Simulacion finalizada en t=1842.5
[DISPATCHER-PROCESS] WorkOrders completadas: 600/600
```

---

## 9. ROLLBACK PLAN

### Si el BUGFIX causa problemas:

**Accion de Emergencia:**
1. Revertir cambios en `warehouse.py` a version anterior
2. Restaurar `cantidad=random.randint(1, 5)` original
3. Ajustar `config.json` manualmente (reducir volumenes de SKUs)

**Comando Git:**
```bash
git checkout HEAD -- src/subsystems/simulation/warehouse.py
```

---

## 10. IMPLEMENTACION PASO A PASO

### Secuencia Recomendada

1. ✅ **PASO 1:** Implementar construccion de mapa de capacidades
2. ✅ **PASO 2:** Implementar obtencion de equipment_required
3. ✅ **PASO 3:** Implementar validacion de cantidad
4. ✅ **PASO 4:** Modificar constructor de WorkOrder
5. ✅ **PASO 5:** Agregar metricas de validacion
6. ✅ **TEST:** Ejecutar simulacion headless con 50 ordenes
7. ✅ **VALIDAR:** Verificar que termina exitosamente
8. ✅ **ESCALAR:** Incrementar a 300 ordenes y re-validar
9. ✅ **OPCIONAL:** Implementar BUGFIX #11b (oversized handling en dispatcher)

---

## 11. DEPENDENCIAS Y RIESGOS

### Dependencias
- ✅ `config.json` debe tener `agent_types` definido
- ✅ `data_manager` debe tener `puntos_de_picking_ordenados` cargados
- ✅ `Warehouse_Logic.xlsx` debe tener columna `equipment_required`

### Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|--------------|---------|------------|
| agent_types vacio | Baja | Alto | Usar defaults (GroundOperator: 150) |
| equipment_required faltante | Media | Medio | Default "GroundOperator" |
| SKUs sobredimensionados | Alta | Medio | Implementar BUGFIX #11b |
| Orden de inicializacion | Baja | Alto | Validar que config esta cargado |

---

## 12. CODIGO ASCII

**Validacion:** Todos los archivos Python deben usar solo caracteres ASCII (7-bit).

**Caracteres NO permitidos:**
- Tildes: á, é, í, ó, ú → usar a, e, i, o, u
- Ñ → usar N o n
- Simbolos especiales: ¿, ¡, €, etc.

**Ejemplo de Conversion:**
```python
# ANTES (con tildes):
print(f"[ALMACEN] Generación de órdenes completada")

# DESPUES (ASCII-only):
print(f"[ALMACEN] Generacion de ordenes completada")
```

---

## 13. RESUMEN EJECUTIVO

### Problema
WorkOrders generadas con volumenes imposibles de asignar → deadlock de simulacion

### Solucion
Validacion automatica de capacidad en punto de creacion de WorkOrders

### Ubicacion
`src/subsystems/simulation/warehouse.py:172-242` (metodo `_generar_flujo_ordenes`)

### Cambios Requeridos
1. Construir mapa de capacidades desde config.json
2. Obtener equipment_required del punto de picking
3. Calcular cantidad maxima valida: `cantidad_maxima = capacidad / volumen_sku`
4. Ajustar cantidad: `cantidad = min(cantidad_deseada, cantidad_maxima)`
5. Generar WorkOrder con cantidad validada

### Impacto
- **~35 lineas nuevas** de codigo
- **~8 lineas modificadas**
- **1 archivo** modificado
- **Tiempo estimado:** 30-45 minutos de implementacion

### Resultado Esperado
✅ Simulacion termina exitosamente
✅ Todas las WorkOrders son asignables
✅ Se genera archivo .jsonl de replay
✅ Prueba TPRF pasa

---

**PLAN STATUS:** ✅ LISTO PARA IMPLEMENTACION
**APROBACION REQUERIDA:** Si - Esperar confirmacion del usuario
**PRIORIDAD:** ALTA (bloqueante para TPRF)

---

**Generado:** 2025-10-06
**Autor:** Claude Code (BUGFIX Session 4 - Capacity Validation)
**Siguiente Paso:** Esperar aprobacion para implementar BUGFIX #11
