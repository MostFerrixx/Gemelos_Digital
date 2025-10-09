# PLAN DE IMPLEMENTACIÓN - ESTRATEGIAS DE DESPACHO Y TIPOS DE TOUR

**Proyecto:** Simulador de Gemelo Digital de Almacén  
**Fecha:** 2025-10-09  
**Estado:** ⏳ PLANIFICACIÓN COMPLETADA - LISTO PARA IMPLEMENTACIÓN  
**Objetivo:** Implementar estrategias de despacho correctas basadas en pick_sequence y tipos de tour funcionales

---

## 📋 REGLAS DE CONSTRUCCIÓN DE TOUR

### REGLAS FUNDAMENTALES:

1. **Primera WO del tour**: AssignmentCostCalculator solo para la primera WO de cada tour
2. **Evaluación consecutiva**: Evaluar el siguiente pick_sequence (posición + 1)
3. **Regla de prioridad**: Omitir WOs de menor prioridad si hay pendientes de mayor prioridad
4. **Cambio de prioridad**: Al agotar la prioridad actual, continuar desde la misma posición en pick_sequence
5. **Ciclo completo**: Al llegar al final, reiniciar desde pick_sequence = 1
6. **Capacidad y límites**: Respetar capacidad del operario y máximo de WOs por tour

### LÓGICA DE EVALUACIÓN:

- **Estado de evaluación**: Mantener posición actual en pick_sequence y prioridad actual
- **Búsqueda consecutiva**: Buscar la siguiente WO en pick_sequence (posición + 1)
- **Ciclo completo**: Si no hay más WOs hacia adelante, reiniciar desde pick_sequence = 1
- **Cambio de prioridad**: Al agotar una prioridad, continuar desde la misma posición (NO reiniciar)
- **Validación de prioridad**: Solo agregar WOs de la prioridad actual si no hay pendientes de mayor prioridad

---

## 🎯 RESUMEN EJECUTIVO

### **PROBLEMA IDENTIFICADO:**
Las estrategias de despacho actuales no utilizan correctamente el `pick_sequence` del archivo `Warehouse_Logic.xlsx`, que es fundamental para la optimización de tours. Además, el parámetro `tour_type` no afecta el comportamiento del sistema.

### **SOLUCIÓN DISEÑADA:**
1. **Optimización Global:** Usar AssignmentCostCalculator solo para la primera WO, luego seguir pick_sequence
2. **Ejecución de Plan:** Usar pick_sequence desde la primera WO, con filtro por prioridad de área de trabajo
3. **Tour Simple:** Consolidar WOs de una sola ubicación de outbound staging
4. **Limpieza:** Eliminar estrategias FIFO Estricto y Cercanía no utilizadas

### **BENEFICIOS ESPERADOS:**
- ✅ Tours optimizados siguiendo la secuencia parametrizada en Excel
- ✅ Estrategias diferenciadas que realmente afecten el comportamiento
- ✅ Tour Simple para reducir movimientos entre staging areas
- ✅ Código más limpio sin estrategias obsoletas

---

## 📋 ANÁLISIS DEL SISTEMA ACTUAL

### **1. ARCHIVO WAREHOUSE_LOGIC.XLSX**

#### **Estructura Esperada:**
```
Hoja: PickingLocations
Columnas:
- x, y: Coordenadas de ubicación
- pick_sequence: Secuencia óptima de picking (1, 2, 3, ...)
- WorkArea: Área de trabajo (Area_Ground, Area_Piso_L1, Area_Rack)
- Otros campos de configuración
```

#### **Carga Actual:**
```python
# En src/subsystems/simulation/data_manager.py
def _process_picking_locations(self, sheet):
    # Lee pick_sequence desde Excel
    # Almacena en self.puntos_de_picking_ordenados
    # Cada punto tiene: {'x': x, 'y': y, 'pick_sequence': seq, 'WorkArea': area}
```

#### **Uso en WorkOrders:**
```python
# En src/subsystems/simulation/warehouse.py
work_order = WorkOrder(
    work_order_id=f"WO-{wo_counter:04d}",
    order_id=f"ORD-{order_counter:04d}",
    tour_id=f"TOUR-{order_counter:04d}",
    sku=sku,
    cantidad=cantidad_valida,
    ubicacion=ubicacion,
    work_area=work_area,
    pick_sequence=wo_counter  # ⚠️ PROBLEMA: Usa wo_counter en lugar de pick_sequence real
)
```

### **2. ESTRATEGIAS ACTUALES**

#### **A. "Optimización Global" (Implementada Incorrectamente)**
```python
# En dispatcher.py líneas 267-289
def _estrategia_optimizacion_global(self, operator):
    # Filtra por compatibilidad de área de trabajo
    candidatos = [wo for wo in self.work_orders_pendientes
                 if operator.can_handle_work_area(wo.work_area)]
    
    # Retorna todos los candidatos - el cálculo de costo pasa en _seleccionar_mejor_batch
    return candidatos[:self.max_wos_por_tour * 3]  # Evalúa más opciones
```

**Problema:** Usa AssignmentCostCalculator para todas las WOs, no solo la primera.

#### **B. "Ejecución de Plan (Filtro por Prioridad)" (No Implementada)**
```python
# En dispatcher.py líneas 228-237
if self.estrategia == "FIFO Estricto":
    return self._estrategia_fifo(operator)
elif self.estrategia == "Optimizacion Global":
    return self._estrategia_optimizacion_global(operator)
elif self.estrategia == "Cercania":
    return self._estrategia_cercania(operator)
else:
    # Default to FIFO if unknown strategy
    print(f"[DISPATCHER WARN] Estrategia desconocida '{self.estrategia}', usando FIFO")
    return self._estrategia_fifo(operator)
```

**Problema:** No existe implementación para "Ejecucion de Plan (Filtro por Prioridad)".

#### **C. "FIFO Estricto" y "Cercanía" (Obsoletas)**
```python
# En dispatcher.py líneas 239-320
def _estrategia_fifo(self, operator):
    # Toma las primeras N WorkOrders que caben en capacidad
    # Sin optimización de distancia ni costos

def _estrategia_cercania(self, operator):
    # Filtra WorkOrders dentro de radio de proximidad
    # Luego optimiza con AssignmentCostCalculator
```

**Problema:** Nunca se utilizaron, código muerto.

### **3. TIPOS DE TOUR**

#### **A. "Tour Mixto (Multi-Destino)" (Comportamiento Actual)**
```python
# En dispatcher.py líneas 389-426
def _construir_tour(self, operator, work_orders):
    # Siempre construye tours multi-destino
    route_result = self.route_calculator.calculate_route(
        start_position=start_pos,
        work_orders=work_orders,  # Múltiples WorkOrders
        return_to_start=True
    )
```

**Comportamiento:** Siempre múltiples WorkOrders, sin importar tour_type.

#### **B. "Tour Simple (Un Destino)" (No Implementado)**
**Objetivo:** Todas las WOs asignadas a un operario deben ser para una sola ubicación de outbound staging.

---

## 🏗️ PLAN DE IMPLEMENTACIÓN DETALLADO

### **FASE 1: ANÁLISIS Y PREPARACIÓN (30 minutos)**

#### **FASE 1.1: Analizar archivo Warehouse_Logic.xlsx (15 min)**
```bash
# Comando para inspeccionar estructura del Excel
python -c "
import openpyxl
wb = openpyxl.load_workbook('data/layouts/Warehouse_Logic.xlsx', read_only=True)
print('Hojas disponibles:', wb.sheetnames)
if 'PickingLocations' in wb.sheetnames:
    ws = wb['PickingLocations']
    print('Columnas PickingLocations:', [cell.value for cell in ws[1]])
    print('Primeras 5 filas:')
    for row in ws.iter_rows(max_row=6):
        print([cell.value for cell in row])
wb.close()
"
```

**Objetivo:** Confirmar estructura exacta del archivo Excel y mapeo de pick_sequence.

#### **FASE 1.2: Crear backup del código actual (15 min)**
```bash
# Crear backup del dispatcher actual
cp src/subsystems/simulation/dispatcher.py src/subsystems/simulation/dispatcher.py.backup

# Crear backup del warehouse actual
cp src/subsystems/simulation/warehouse.py src/subsystems/simulation/warehouse.py.backup
```

**Objetivo:** Tener rollback disponible en caso de problemas.

### **FASE 2: CORRECCIÓN DE PICK_SEQUENCE (45 minutos)**

#### **FASE 2.1: Corregir generación de WorkOrders (30 min)**
```python
# En src/subsystems/simulation/warehouse.py
# Línea 354 - Cambiar:
pick_sequence=wo_counter  # ❌ Incorrecto

# Por:
pick_sequence=self._obtener_pick_sequence_real(ubicacion, work_area)  # ✅ Correcto
```

**Implementación:**
```python
def _obtener_pick_sequence_real(self, ubicacion: tuple, work_area: str) -> int:
    """
    Obtiene el pick_sequence real desde Warehouse_Logic.xlsx
    
    Args:
        ubicacion: (x, y) coordenadas de la ubicación
        work_area: Área de trabajo
        
    Returns:
        pick_sequence real desde Excel, o fallback si no se encuentra
    """
    if not self.data_manager or not hasattr(self.data_manager, 'puntos_de_picking_ordenados'):
        return 999  # Fallback para compatibilidad
    
    # Buscar en puntos de picking ordenados
    for punto in self.data_manager.puntos_de_picking_ordenados:
        if (punto.get('x') == ubicacion[0] and 
            punto.get('y') == ubicacion[1] and 
            punto.get('WorkArea') == work_area):
            return punto.get('pick_sequence', 999)
    
    # Si no se encuentra, usar fallback
    print(f"[WAREHOUSE WARN] No se encontró pick_sequence para {ubicacion} en {work_area}")
    return 999
```

#### **FASE 2.2: Validar pick_sequence en DataManager (15 min)**
```python
# En src/subsystems/simulation/data_manager.py
# Verificar que _process_picking_locations carga correctamente pick_sequence
def _process_picking_locations(self, sheet):
    # ... código existente ...
    
    # Validar que pick_sequence se carga correctamente
    for punto in self.puntos_de_picking_ordenados:
        if 'pick_sequence' not in punto:
            print(f"[DATA-MANAGER ERROR] pick_sequence faltante en punto {punto}")
            punto['pick_sequence'] = 999  # Fallback
```

### **FASE 3: IMPLEMENTACIÓN DE ESTRATEGIAS CORRECTAS (90 minutos)**

#### **FASE 3.1: Implementar "Optimización Global" Correcta (30 min)**
```python
# En src/subsystems/simulation/dispatcher.py
def _estrategia_optimizacion_global(self, operator: Any) -> List[Any]:
    """
    Optimización Global CORRECTA:
    1. Filtrar WOs del área de trabajo con MAYOR prioridad
    2. Usar AssignmentCostCalculator solo para la PRIMERA WO entre esas
    3. Para el resto del tour, seguir pick_sequence del Excel (solo del mismo área)
    """
    # Paso 1: Filtrar por compatibilidad de área de trabajo
    candidatos_compatibles = [wo for wo in self.work_orders_pendientes
                             if operator.can_handle_work_area(wo.work_area)]
    
    if not candidatos_compatibles:
        return []
    
    # Paso 2: Filtrar solo WOs del área de trabajo con MAYOR prioridad
    candidatos_area_prioridad = self._filtrar_por_area_prioridad(operator, candidatos_compatibles)
    
    if not candidatos_area_prioridad:
        return []
    
    # Paso 3: Usar AssignmentCostCalculator para encontrar la MEJOR primera WO
    best_first_wo = self._encontrar_mejor_primera_wo(operator, candidatos_area_prioridad)
    if not best_first_wo:
        return []
    
    # Paso 4: Construir tour siguiendo pick_sequence desde la primera WO (solo mismo área)
    tour_wos = self._construir_tour_por_secuencia(operator, best_first_wo, candidatos_area_prioridad)
    
    return tour_wos

def _encontrar_mejor_primera_wo(self, operator: Any, candidatos: List[Any]) -> Optional[Any]:
    """Encuentra la mejor primera WO usando AssignmentCostCalculator"""
    if not candidatos:
        return None
    
    # Calcular costos para todas las candidatas
    costos = []
    current_pos = operator.current_position or (0, 0)
    
    for wo in candidatos:
        cost_result = self.assignment_calculator.calculate_cost(operator, wo, current_pos)
        costos.append((wo, cost_result))
    
    # Ordenar por costo total (menor es mejor)
    costos.sort(key=lambda x: x[1].total_cost)
    
    # Retornar la mejor WO que quepa en capacidad
    for wo, cost_result in costos:
        if wo.calcular_volumen_restante() <= operator.capacity:
            return wo
    
    return None

def _filtrar_por_area_prioridad(self, operator: Any, candidatos: List[Any]) -> List[Any]:
    """Filtra candidatos del área de trabajo con MAYOR prioridad"""
    if not candidatos:
        return []
    
    # Filtrar solo WOs de áreas de trabajo con prioridad definida (excluir prioridad 999 = incompatible)
    candidatos_con_prioridad = [
        wo for wo in candidatos 
        if operator.get_priority_for_work_area(wo.work_area) != 999
    ]
    
    if not candidatos_con_prioridad:
        return []
    
    # Encontrar la prioridad más alta (menor número)
    prioridades = [operator.get_priority_for_work_area(wo.work_area) for wo in candidatos_con_prioridad]
    prioridad_mas_alta = min(prioridades)
    
    # Filtrar solo WOs del área con prioridad más alta
    candidatos_area_prioridad = [
        wo for wo in candidatos_con_prioridad 
        if operator.get_priority_for_work_area(wo.work_area) == prioridad_mas_alta
    ]
    
    return candidatos_area_prioridad

def _construir_tour_por_secuencia(self, operator: Any, primera_wo: Any, candidatos: List[Any]) -> List[Any]:
    """
    Construye tour siguiendo pick_sequence desde la primera WO, evaluando prioridad de área.
    
    REGLAS DE CONSTRUCCIÓN DE TOUR:
    1. Primera WO del tour: AssignmentCostCalculator solo para la primera WO de cada tour
    2. Evaluación consecutiva: Evaluar el siguiente pick_sequence (posición + 1)
    3. Regla de prioridad: Omitir WOs de menor prioridad si hay pendientes de mayor prioridad
    4. Cambio de prioridad: Al agotar la prioridad actual, continuar desde la misma posición en pick_sequence
    5. Ciclo completo: Al llegar al final, reiniciar desde pick_sequence = 1
    6. Capacidad y límites: Respetar capacidad del operario y máximo de WOs por tour
    """
    tour_wos = [primera_wo]
    volume_acumulado = primera_wo.calcular_volumen_restante()
    
    # Obtener todas las WOs disponibles (no solo las del área de mayor prioridad)
    todas_las_wos = [wo for wo in self.work_orders_pendientes
                    if operator.can_handle_work_area(wo.work_area) and 
                       operator.get_priority_for_work_area(wo.work_area) != 999]
    
    # Filtrar candidatos restantes (excluyendo la primera WO)
    candidatos_restantes = [wo for wo in todas_las_wos if wo != primera_wo]
    
    # Ordenar por pick_sequence (ascendente)
    candidatos_restantes.sort(key=lambda wo: wo.pick_sequence)
    
    # Obtener la prioridad más alta (menor número)
    prioridades = [operator.get_priority_for_work_area(wo.work_area) for wo in candidatos_restantes]
    prioridad_mas_alta = min(prioridades)
    
    # Estado de evaluación consecutiva
    prioridad_actual = operator.get_priority_for_work_area(primera_wo.work_area)
    posicion_actual = primera_wo.pick_sequence
    
    # Agregar WOs evaluando pick_sequence consecutivamente
    while len(tour_wos) < self.max_wos_por_tour:
        # Encontrar la siguiente WO en pick_sequence
        siguiente_wo = None
        siguiente_posicion = posicion_actual + 1
        
        # Buscar la siguiente WO en orden consecutivo
        for wo in candidatos_restantes:
            if wo.pick_sequence == siguiente_posicion and wo not in tour_wos:
                siguiente_wo = wo
                break
        
        # Si no encontró la siguiente WO, buscar desde el principio (ciclo completo)
        if siguiente_wo is None:
            for wo in candidatos_restantes:
                if wo.pick_sequence == 1 and wo not in tour_wos:
                    siguiente_wo = wo
                    siguiente_posicion = 1
                    break
        
        # Si no hay más WOs disponibles, terminar
        if siguiente_wo is None:
            break
        
        # Evaluar si la WO puede ser agregada según la prioridad actual
        wo_priority = operator.get_priority_for_work_area(siguiente_wo.work_area)
        wo_volume = siguiente_wo.calcular_volumen_restante()
        
        # Verificar si hay WOs de mayor prioridad pendientes
        wos_mayor_prioridad_pendientes = [
            w for w in candidatos_restantes 
            if operator.get_priority_for_work_area(w.work_area) < wo_priority and w not in tour_wos
        ]
        
        # Solo agregar si no hay WOs de mayor prioridad pendientes
        if (not wos_mayor_prioridad_pendientes and
            volume_acumulado + wo_volume <= operator.capacity):
            tour_wos.append(siguiente_wo)
            volume_acumulado += wo_volume
            posicion_actual = siguiente_posicion
        else:
            # Si hay WOs de mayor prioridad pendientes, cambiar a esa prioridad
            if wos_mayor_prioridad_pendientes:
                prioridad_actual = min(operator.get_priority_for_work_area(w.work_area) 
                                     for w in wos_mayor_prioridad_pendientes)
                # Continuar desde la misma posición (NO reiniciar)
                continue
            else:
                # No hay más WOs disponibles para la prioridad actual
                break
    
    return tour_wos
```

#### **FASE 3.2: Implementar "Ejecución de Plan (Filtro por Prioridad)" (30 min)**
```python
# En src/subsystems/simulation/dispatcher.py
def _estrategia_ejecucion_plan(self, operator: Any) -> List[Any]:
    """
    Ejecución de Plan (Filtro por Prioridad):
    ÚNICA DIFERENCIA respecto a Optimización Global:
    - En lugar de usar AssignmentCostCalculator para la primera WO,
    - Selecciona la WO con el pick_sequence más pequeño del área con mayor prioridad
    - El resto del tour se construye igual que Optimización Global
    """
    # Paso 1: Filtrar por compatibilidad de área de trabajo
    candidatos_compatibles = [wo for wo in self.work_orders_pendientes
                             if operator.can_handle_work_area(wo.work_area)]
    
    if not candidatos_compatibles:
        return []
    
    # Paso 2: Filtrar solo WOs de áreas de trabajo con prioridad definida (excluir prioridad 999 = incompatible)
    candidatos_con_prioridad = [
        wo for wo in candidatos_compatibles
        if operator.get_priority_for_work_area(wo.work_area) != 999
    ]
    
    if not candidatos_con_prioridad:
        return []
    
    # Paso 3: Encontrar la prioridad más alta (menor número) entre los candidatos con prioridad
    prioridades = [operator.get_priority_for_work_area(wo.work_area) for wo in candidatos_con_prioridad]
    prioridad_mas_alta = min(prioridades)
    
    # Paso 4: Filtrar solo WOs del área con prioridad más alta
    candidatos_area_prioridad = [
        wo for wo in candidatos_con_prioridad
        if operator.get_priority_for_work_area(wo.work_area) == prioridad_mas_alta
    ]
    
    if not candidatos_area_prioridad:
        return []
    
    # Paso 5: Seleccionar la primera WO con el pick_sequence más pequeño (ÚNICA DIFERENCIA)
    primera_wo = min(candidatos_area_prioridad, key=lambda wo: wo.pick_sequence)
    
    # Paso 6: Construir tour siguiendo pick_sequence desde la primera WO (igual que Optimización Global)
    tour_wos = self._construir_tour_por_secuencia(operator, primera_wo, candidatos_con_prioridad)
    
    return tour_wos
```

#### **FASE 3.3: Actualizar selector de estrategias (15 min)**
```python
# En src/subsystems/simulation/dispatcher.py
def _seleccionar_work_orders_candidatos(self, operator: Any) -> List[Any]:
    """Strategy-specific WorkOrder candidate selection"""
    if self.estrategia == "Optimizacion Global":
        return self._estrategia_optimizacion_global(operator)
    elif self.estrategia == "Ejecucion de Plan (Filtro por Prioridad)":
        return self._estrategia_ejecucion_plan(operator)
    else:
        # Fallback a Optimización Global si estrategia desconocida
        print(f"[DISPATCHER WARN] Estrategia desconocida '{self.estrategia}', usando Optimizacion Global")
        return self._estrategia_optimizacion_global(operator)
```

#### **FASE 3.4: Eliminar estrategias obsoletas (15 min)**
```python
# Eliminar métodos obsoletos de dispatcher.py:
# - _estrategia_fifo()
# - _estrategia_cercania()

# Actualizar imports y referencias
# Limpiar código muerto
```

### **FASE 4: IMPLEMENTACIÓN DE TOUR SIMPLE (60 minutos)**

#### **FASE 4.1: Modificar Dispatcher para soportar Tour Simple (30 min)**
```python
# En src/subsystems/simulation/dispatcher.py
def __init__(self, ...):
    # ... código existente ...
    
    # Agregar soporte para tour_type
    self.tour_type = configuracion.get('tour_type', 'Tour Mixto (Multi-Destino)')
    
    print(f"[DISPATCHER] Tour type: {self.tour_type}")

def _construir_tour(self, operator: Any, work_orders: List[Any]) -> Optional[Dict[str, Any]]:
    """Build optimal tour using RouteCalculator with tour_type support"""
    if not work_orders:
        return None
    
    # Verificar si es Tour Simple
    if self.tour_type == "Tour Simple (Un Destino)":
        return self._construir_tour_simple(operator, work_orders)
    else:
        return self._construir_tour_mixto(operator, work_orders)

def _construir_tour_simple(self, operator: Any, work_orders: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Tour Simple: Todas las WOs deben ser para una sola ubicación de staging
    """
    # Verificar que todas las WOs sean para la misma ubicación de staging
    staging_locations = set()
    for wo in work_orders:
        staging_id = wo.staging_id  # Propiedad de WorkOrder
        staging_locations.add(staging_id)
    
    if len(staging_locations) > 1:
        print(f"[DISPATCHER ERROR] Tour Simple requiere WOs de una sola ubicación de staging")
        print(f"[DISPATCHER ERROR] Encontradas ubicaciones: {staging_locations}")
        return None
    
    # Construir tour normal (todas van al mismo staging)
    return self._construir_tour_mixto(operator, work_orders)

def _construir_tour_mixto(self, operator: Any, work_orders: List[Any]) -> Optional[Dict[str, Any]]:
    """Tour Mixto: Comportamiento actual (múltiples ubicaciones de staging)"""
    # ... código existente de _construir_tour ...
```

#### **FASE 4.2: Modificar estrategias para respetar Tour Simple (30 min)**
```python
# En src/subsystems/simulation/dispatcher.py
def _estrategia_optimizacion_global(self, operator: Any) -> List[Any]:
    """Optimización Global con soporte para Tour Simple"""
    # ... código existente ...
    
    # Si es Tour Simple, filtrar por staging location
    if self.tour_type == "Tour Simple (Un Destino)":
        tour_wos = self._filtrar_por_staging_unico(operator, tour_wos)
    
    return tour_wos

def _estrategia_ejecucion_plan(self, operator: Any) -> List[Any]:
    """Ejecución de Plan con soporte para Tour Simple"""
    # ... código existente ...
    
    # Si es Tour Simple, filtrar por staging location
    if self.tour_type == "Tour Simple (Un Destino)":
        tour_wos = self._filtrar_por_staging_unico(operator, tour_wos)
    
    return tour_wos

def _filtrar_por_staging_unico(self, operator: Any, work_orders: List[Any]) -> List[Any]:
    """
    Filtra WOs para que todas sean de una sola ubicación de staging
    """
    if not work_orders:
        return []
    
    # Agrupar por staging_id
    staging_groups = {}
    for wo in work_orders:
        staging_id = wo.staging_id
        if staging_id not in staging_groups:
            staging_groups[staging_id] = []
        staging_groups[staging_id].append(wo)
    
    # Seleccionar el grupo con más WOs que quepan en capacidad
    best_group = []
    best_volume = 0
    
    for staging_id, group_wos in staging_groups.items():
        group_volume = sum(wo.calcular_volumen_restante() for wo in group_wos)
        
        if (group_volume <= operator.capacity and 
            group_volume > best_volume):
            best_group = group_wos
            best_volume = group_volume
    
    # Limitar a max_wos_por_tour
    if len(best_group) > self.max_wos_por_tour:
        best_group = best_group[:self.max_wos_por_tour]
    
    return best_group
```

### **FASE 5: TESTING Y VALIDACIÓN (45 minutos)**

#### **FASE 5.1: Crear tests unitarios (20 min)**
```python
# Crear test_dispatch_strategies.py
def test_optimizacion_global():
    """Test Optimización Global: AssignmentCostCalculator solo para primera WO"""
    # Setup
    dispatcher = DispatcherV11(...)
    dispatcher.estrategia = "Optimizacion Global"
    
    # Test
    candidatos = dispatcher._estrategia_optimizacion_global(operator)
    
    # Assertions
    assert len(candidatos) > 0
    assert candidatos[0] == mejor_wo_esperada  # Primera WO debe ser la mejor
    # Resto deben seguir pick_sequence

def test_ejecucion_plan():
    """Test Ejecución de Plan: pick_sequence desde primera WO"""
    # Setup
    dispatcher = DispatcherV11(...)
    dispatcher.estrategia = "Ejecucion de Plan (Filtro por Prioridad)"
    
    # Test
    candidatos = dispatcher._estrategia_ejecucion_plan(operator)
    
    # Assertions
    assert len(candidatos) > 0
    # Todas deben estar ordenadas por pick_sequence

def test_tour_simple():
    """Test Tour Simple: WOs de una sola ubicación de staging"""
    # Setup
    dispatcher = DispatcherV11(...)
    dispatcher.tour_type = "Tour Simple (Un Destino)"
    
    # Test
    tour_result = dispatcher._construir_tour(operator, work_orders)
    
    # Assertions
    assert tour_result is not None
    # Verificar que todas las WOs van al mismo staging
```

#### **FASE 5.2: Testing de integración (15 min)**
```bash
# Test con configuración Optimización Global
python test_quick_jsonl.py

# Test con configuración Ejecución de Plan
# Modificar config.json para cambiar estrategia
python test_quick_jsonl.py

# Test con Tour Simple
# Modificar config.json para cambiar tour_type
python test_quick_jsonl.py
```

#### **FASE 5.3: Validación de logs (10 min)**
```bash
# Verificar logs de dispatcher
grep "DISPATCHER" output/simulation_*/replay_events_*.jsonl | head -20

# Verificar que pick_sequence se usa correctamente
grep "pick_sequence" output/simulation_*/replay_events_*.jsonl | head -10
```

### **FASE 6: DOCUMENTACIÓN Y LIMPIEZA (30 minutos)**

#### **FASE 6.1: Actualizar documentación (15 min)**
```markdown
# Actualizar INSTRUCCIONES.md con:
- Descripción de estrategias correctas
- Explicación de pick_sequence
- Diferencias entre Tour Simple y Tour Mixto
- Parámetros de configuración
```

#### **FASE 6.2: Limpieza de código (15 min)**
```python
# Eliminar métodos obsoletos:
# - _estrategia_fifo()
# - _estrategia_cercania()

# Limpiar imports no utilizados
# Actualizar comentarios
# Verificar que no hay código muerto
```

---

## 📊 CRONOGRAMA DETALLADO

| Fase | Tarea | Tiempo | Dependencias | Estado |
|------|-------|--------|--------------|--------|
| 1.1 | Analizar Warehouse_Logic.xlsx | 15 min | - | ⏳ Pendiente |
| 1.2 | Crear backup del código | 15 min | - | ⏳ Pendiente |
| 2.1 | Corregir generación de WorkOrders | 30 min | 1.1 | ⏳ Pendiente |
| 2.2 | Validar pick_sequence en DataManager | 15 min | 2.1 | ⏳ Pendiente |
| 3.1 | Implementar Optimización Global correcta | 30 min | 2.2 | ⏳ Pendiente |
| 3.2 | Implementar Ejecución de Plan | 30 min | 2.2 | ⏳ Pendiente |
| 3.3 | Actualizar selector de estrategias | 15 min | 3.1, 3.2 | ⏳ Pendiente |
| 3.4 | Eliminar estrategias obsoletas | 15 min | 3.3 | ⏳ Pendiente |
| 4.1 | Modificar Dispatcher para Tour Simple | 30 min | 3.4 | ⏳ Pendiente |
| 4.2 | Modificar estrategias para Tour Simple | 30 min | 4.1 | ⏳ Pendiente |
| 5.1 | Crear tests unitarios | 20 min | 4.2 | ⏳ Pendiente |
| 5.2 | Testing de integración | 15 min | 5.1 | ⏳ Pendiente |
| 5.3 | Validación de logs | 10 min | 5.2 | ⏳ Pendiente |
| 6.1 | Actualizar documentación | 15 min | 5.3 | ⏳ Pendiente |
| 6.2 | Limpieza de código | 15 min | 6.1 | ⏳ Pendiente |

**TIEMPO TOTAL:** 4 horas (240 minutos)

---

## 🎯 CRITERIOS DE ÉXITO

### **Funcionalidades Core:**
- ✅ Optimización Global usa AssignmentCostCalculator solo para primera WO
- ✅ Ejecución de Plan usa pick_sequence desde primera WO
- ✅ Tour Simple consolida WOs de una sola ubicación de staging
- ✅ pick_sequence se carga correctamente desde Warehouse_Logic.xlsx

### **Funcionalidades Avanzadas:**
- ✅ Estrategias diferenciadas que realmente afecten el comportamiento
- ✅ Filtro por prioridad de área de trabajo en Ejecución de Plan
- ✅ Validación de Tour Simple (error si múltiples staging)
- ✅ Logs informativos para debugging

### **Calidad:**
- ✅ Tests unitarios para cada estrategia
- ✅ Tests de integración con configuraciones reales
- ✅ Código limpio sin estrategias obsoletas
- ✅ Documentación actualizada

---

## 📁 ARCHIVOS A MODIFICAR

### **Archivos Principales:**
- `src/subsystems/simulation/dispatcher.py` - Implementación de estrategias
- `src/subsystems/simulation/warehouse.py` - Corrección de pick_sequence
- `src/subsystems/simulation/data_manager.py` - Validación de carga Excel

### **Archivos de Configuración:**
- `config.json` - Parámetros de estrategias y tour_type
- `configurator.py` - UI para configurar parámetros

### **Archivos de Test:**
- `test_dispatch_strategies.py` - Tests unitarios (NUEVO)
- `test_quick_jsonl.py` - Tests de integración

### **Archivos de Documentación:**
- `INSTRUCCIONES.md` - Actualización con nuevas funcionalidades
- `ACTIVE_SESSION_STATE.md` - Referencia a este plan

---

## 🚀 PRÓXIMOS PASOS

### **Para nueva sesión de chat:**
1. **Leer este documento completo** para entender el plan
2. **Revisar ACTIVE_SESSION_STATE.md** para contexto actual
3. **Comenzar con FASE 1.1:** Analizar Warehouse_Logic.xlsx
4. **Seguir cronograma detallado** paso a paso
5. **Validar cada fase** antes de continuar

### **Comandos para testing:**
```bash
# Test rápido con configuración actual
python test_quick_jsonl.py

# Test con configurador
python configurator.py

# Verificar logs
grep "DISPATCHER" output/simulation_*/replay_events_*.jsonl | head -20
```

### **Archivos clave para implementación:**
- `PLAN_IMPLEMENTACION_ESTRATEGIAS_DESPACHO.md` - Este documento
- `src/subsystems/simulation/dispatcher.py` - Archivo principal a modificar
- `data/layouts/Warehouse_Logic.xlsx` - Archivo Excel con pick_sequence
- `config.json` - Configuración de estrategias

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### **Compatibilidad:**
- Mantener compatibilidad con configuraciones existentes
- Fallback a Optimización Global si estrategia desconocida
- Validación robusta de pick_sequence

### **Performance:**
- AssignmentCostCalculator solo para primera WO en Optimización Global
- Ordenamiento eficiente por pick_sequence
- Validación de Tour Simple sin impacto significativo

### **Debugging:**
- Logs informativos para cada estrategia
- Validación de pick_sequence en DataManager
- Errores claros para Tour Simple inválido

---

**Última actualización:** 2025-10-09  
**Estado:** Planificación Completa - Listo para Implementación  
**Próxima acción:** FASE 1.1 - Analizar Warehouse_Logic.xlsx

---

## 📚 REFERENCIAS

- `ACTIVE_SESSION_STATE.md` - Estado actual del proyecto
- `HANDOFF.md` - Overview completo del proyecto
- `INSTRUCCIONES.md` - Instrucciones técnicas del sistema
- `src/subsystems/simulation/dispatcher.py` - Implementación actual
- `data/layouts/Warehouse_Logic.xlsx` - Archivo Excel con pick_sequence
