# PLAN DE IMPLEMENTACIÓN: DESCARGA MÚLTIPLE EN STAGINGS

**Fecha:** 2025-10-27  
**Tipo:** Feature Enhancement  
**Prioridad:** MEDIA  
**Objetivo:** Implementar descarga realista donde cada WO se descarga en su staging específico

---

## 📋 PROBLEMA ACTUAL

### Comportamiento Actual (Subóptimo):
```
Tour pickea WOs:
  - WO-001 (staging 1)
  - WO-002 (staging 3)  
  - WO-003 (staging 5)

Descarga actual:
  1. Operador navega a staging 1
  2. Descarga TODAS las WOs (WO-001, WO-002, WO-003) ← INCORRECTO
  3. Fin del tour
```

### Comportamiento Deseado (Realista):
```
Tour pickea WOs:
  - WO-001 (staging 1)
  - WO-002 (staging 3)
  - WO-003 (staging 5)

Descarga deseada:
  1. Operador navega a staging 1 → descarga solo WO-001
  2. Operador navega a staging 3 → descarga solo WO-002
  3. Operador navega a staging 5 → descarga solo WO-003
  4. Fin del tour
```

---

## 🎯 SOLUCIÓN PROPUESTA

### Estrategia:
1. **Agrupar WOs por staging_id** después del picking
2. **Visitar cada staging** en orden óptimo (minimizar distancia)
3. **Descargar solo las WOs** correspondientes a cada staging
4. **Actualizar cargo_volume** progresivamente en cada descarga

### Cambios Necesarios:

#### 1. Modificar `operators.py` - Método `agent_process()`

**Ubicación:** Sección de descarga (después del picking, antes de return to depot)

**Lógica actual (líneas ~410-460):**
```python
# PASO 4: Navegar a staging area para descarga
staging_id, depot_location = determinar_staging_destino(work_orders, self.almacen.data_manager)
# ... navegar a depot_location ...
# ... descargar TODO ...
self.cargo_volume = 0  # Limpiar TODO de una vez
```

**Lógica nueva:**
```python
# PASO 4: Agrupar WOs por staging y descargar en cada uno
staging_groups = self._agrupar_wos_por_staging(work_orders)
ordered_stagings = self._ordenar_stagings_por_distancia(staging_groups, self.current_position)

for staging_id, staging_wos in ordered_stagings:
    # Calcular volumen a descargar en este staging
    volumen_staging = sum(wo.calcular_volumen_restante() for wo in staging_wos)
    
    # Navegar al staging
    staging_location = self.almacen.data_manager.get_outbound_staging_locations().get(staging_id)
    # ... pathfinding ...
    
    # Descargar solo WOs de este staging
    self.status = "discharging"
    yield self.env.timeout(self.discharge_time * len(staging_wos))
    
    # Actualizar cargo_volume parcialmente
    self.cargo_volume -= volumen_staging
    
    # Registrar evento de descarga parcial
    self.almacen.registrar_evento('partial_discharge', {
        'agent_id': self.id,
        'staging_id': staging_id,
        'wos_descargadas': [wo.id for wo in staging_wos],
        'volumen_descargado': volumen_staging,
        'cargo_restante': self.cargo_volume
    })

# PASO 5: Limpiar cargo final (por seguridad)
self.cargo_volume = 0
```

---

## 📝 CÓDIGO DETALLADO A IMPLEMENTAR

### Archivo: `src/subsystems/simulation/operators.py`

#### Paso 1: Agregar métodos auxiliares a la clase `BaseOperator`

```python
def _agrupar_wos_por_staging(self, work_orders: List[Any]) -> Dict[int, List[Any]]:
    """
    Agrupa WorkOrders por staging_id
    
    Args:
        work_orders: Lista de WorkOrders del tour
        
    Returns:
        Dict[staging_id: int, wos: List[WorkOrder]]
    """
    from collections import defaultdict
    staging_groups = defaultdict(list)
    
    for wo in work_orders:
        staging_id = wo.staging_id
        staging_groups[staging_id].append(wo)
    
    return dict(staging_groups)

def _ordenar_stagings_por_distancia(self, staging_groups: Dict[int, List[Any]], 
                                      start_position: Tuple[int, int]) -> List[Tuple[int, List[Any]]]:
    """
    Ordena stagings por distancia desde posición actual para minimizar desplazamientos
    
    Args:
        staging_groups: Dict[staging_id -> List[WorkOrder]]
        start_position: Posición actual del operador (x, y)
        
    Returns:
        List[(staging_id, wos)] ordenada por distancia
    """
    staging_locs = self.almacen.data_manager.get_outbound_staging_locations()
    
    # Calcular distancia a cada staging
    staging_distances = []
    for staging_id, wos in staging_groups.items():
        staging_pos = staging_locs.get(staging_id, (3, 29))
        distance = abs(staging_pos[0] - start_position[0]) + abs(staging_pos[1] - start_position[1])
        staging_distances.append((distance, staging_id, wos))
    
    # Ordenar por distancia (más cercano primero)
    staging_distances.sort(key=lambda x: x[0])
    
    # Retornar sin la distancia
    return [(staging_id, wos) for _, staging_id, wos in staging_distances]
```

#### Paso 2: Modificar el método `agent_process()` de `GroundOperator`

**Buscar líneas ~410-460** (sección de navegación a staging)

**Código actual a REEMPLAZAR:**
```python
# PASO 4: Navegar a staging area para descarga usando pathfinding paso a paso
# Determine correct staging based on work orders
staging_id, depot_location = determinar_staging_destino(work_orders, self.almacen.data_manager)
print(f"[{self.id}] Navegando a staging {staging_id} en ubicación {depot_location}")

if hasattr(self.almacen, 'route_calculator') and self.almacen.route_calculator:
    try:
        return_path = self.almacen.route_calculator.pathfinder.find_path(self.current_position, depot_location)
        if return_path and len(return_path) > 1:
            self.status = "moving"
            # ... código de navegación ...
            
# PASO 5: Descargar
self.status = "discharging"
# ... código de descarga ...
self.cargo_volume = 0  # ← Limpia TODO de una vez
```

**Código NUEVO:**
```python
# PASO 4: Agrupar WOs por staging y descargar en cada uno
print(f"[{self.id}] Agrupando WOs por staging para descarga multiple")
staging_groups = self._agrupar_wos_por_staging(work_orders)
print(f"[{self.id}] Tour requiere visitar {len(staging_groups)} stagings: {list(staging_groups.keys())}")

# Ordenar stagings por distancia desde posición actual
ordered_stagings = self._ordenar_stagings_por_distancia(staging_groups, self.current_position)
staging_locs = self.almacen.data_manager.get_outbound_staging_locations()

# Visitar cada staging en orden
for idx, (staging_id, staging_wos) in enumerate(ordered_stagings, 1):
    staging_location = staging_locs.get(staging_id, (3, 29))
    volumen_staging = sum(wo.calcular_volumen_restante() for wo in staging_wos)
    
    print(f"[{self.id}] [{idx}/{len(ordered_stagings)}] Navegando a staging {staging_id} "
          f"en {staging_location} para descargar {len(staging_wos)} WOs ({volumen_staging}L)")
    
    # Navegar al staging
    if hasattr(self.almacen, 'route_calculator') and self.almacen.route_calculator:
        try:
            return_path = self.almacen.route_calculator.pathfinder.find_path(
                self.current_position, staging_location
            )
            
            if return_path and len(return_path) > 1:
                self.status = "moving"
                
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': None,
                    'cargo_volume': self.cargo_volume
                })
                
                print(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                      f"(path: {len(return_path)} pasos)")
                
                for step_idx, step_position in enumerate(return_path[1:], 1):
                    self.current_position = step_position
                    
                    self.almacen.registrar_evento('estado_agente', {
                        'agent_id': self.id,
                        'agent_type': self.type,
                        'position': self.current_position,
                        'status': self.status,
                        'current_task': None,
                        'cargo_volume': self.cargo_volume
                    })
                    
                    yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                    
                    if step_idx % 5 == 0:  # Log cada 5 pasos
                        print(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                              f"paso {step_idx}/{len(return_path)-1}")
                
                self.total_distance_traveled += len(return_path) - 1
            else:
                self.current_position = staging_location
        except Exception as e:
            print(f"[{self.id}] ERROR en pathfinding a staging {staging_id}: {e}")
            self.current_position = staging_location
    
    # DESCARGAR en este staging
    self.status = "discharging"
    
    self.almacen.registrar_evento('estado_agente', {
        'agent_id': self.id,
        'agent_type': self.type,
        'position': self.current_position,
        'status': self.status,
        'current_task': None,
        'cargo_volume': self.cargo_volume
    })
    
    print(f"[{self.id}] t={self.env.now:.1f} Descargando en staging {staging_id}")
    discharge_duration = self.discharge_time * len(staging_wos)
    yield self.env.timeout(discharge_duration)
    
    # Actualizar cargo_volume PARCIALMENTE (solo lo descargado)
    self.cargo_volume -= volumen_staging
    print(f"[{self.id}] t={self.env.now:.1f} Descargados {volumen_staging}L en staging {staging_id}, "
          f"cargo restante: {self.cargo_volume}L")
    
    # Registrar evento de descarga parcial
    self.almacen.registrar_evento('partial_discharge', {
        'agent_id': self.id,
        'staging_id': staging_id,
        'wos_descargadas': [wo.id for wo in staging_wos],
        'volumen_descargado': volumen_staging,
        'cargo_restante': self.cargo_volume,
        'timestamp': self.env.now
    })

# PASO 5: Limpiar cargo final (por seguridad)
self.cargo_volume = 0
print(f"[{self.id}] t={self.env.now:.1f} Descarga completa en todos los stagings")
```

#### Paso 3: Aplicar el mismo cambio a `Forklift`

El método `agent_process()` de `Forklift` tiene la misma estructura. Aplicar el mismo cambio en la sección de descarga.

---

## 🧪 TESTING Y VALIDACIÓN

### Script de Validación

```python
"""
Validar que los operarios descargan en múltiples stagings
"""
import json
from collections import defaultdict

jsonl_file = "output/simulation_[TIMESTAMP]/replay_[TIMESTAMP].jsonl"

staging_visits = defaultdict(lambda: defaultdict(int))  # {agent_id: {staging_id: count}}
agent_tours = defaultdict(list)

with open(jsonl_file, 'r', encoding='utf-8') as f:
    first_line = f.readline()
    
    for line in f:
        event = json.loads(line)
        event_type = event.get('type')
        
        # Detectar eventos de descarga parcial
        if event_type == 'partial_discharge':
            agent_id = event['agent_id']
            staging_id = event['staging_id']
            staging_visits[agent_id][staging_id] += 1
            
            print(f"[{agent_id}] Descarga en staging {staging_id}: "
                  f"{len(event['wos_descargadas'])} WOs, "
                  f"{event['volumen_descargado']}L")

print("\n" + "="*80)
print("RESUMEN DE DESCARGAS POR STAGING")
print("="*80)

for agent_id, stagings in staging_visits.items():
    print(f"\n{agent_id}:")
    print(f"  Stagings visitados: {len(stagings)}")
    for staging_id, count in sorted(stagings.items()):
        print(f"    Staging {staging_id}: {count} descargas")

print("\n✅ VALIDACIÓN: Si cada agente visita múltiples stagings, el fix funciona correctamente")
```

### Criterios de Éxito

- ✅ Tours con WOs de múltiples stagings visitan cada staging
- ✅ Cada staging recibe solo las WOs correspondientes
- ✅ `cargo_volume` se reduce progresivamente
- ✅ Evento `partial_discharge` se registra para cada staging
- ✅ No hay errores en la simulación

---

## ⚠️ CONSIDERACIONES

### 1. Impacto en Tiempos de Simulación
- **Antes:** 1 navegación al staging + 1 descarga
- **Después:** N navegaciones (una por staging) + N descargas
- **Estimación:** Tours con 3 stagings tomarán ~2-3x más tiempo

### 2. Compatibilidad con Tour Simple
- **Tour Simple (Un Destino):** Ya limita a un staging, no afectado
- **Tour Mixto (Multi-Destino):** Beneficiado por este cambio

### 3. Orden de Visita de Stagings
- Se ordena por distancia desde última posición
- Minimiza desplazamientos totales
- Alternativa futura: Ordenar por staging_id numérico

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Código:
- [ ] Agregar `_agrupar_wos_por_staging()` a `BaseOperator`
- [ ] Agregar `_ordenar_stagings_por_distancia()` a `BaseOperator`
- [ ] Modificar `agent_process()` en `GroundOperator` (líneas ~410-460)
- [ ] Modificar `agent_process()` en `Forklift` (líneas similares)
- [ ] Verificar que `import` de `defaultdict` existe

### Testing:
- [ ] Generar simulación con configuración actual
- [ ] Ejecutar script de validación
- [ ] Verificar logs del dispatcher
- [ ] Confirmar múltiples visitas a stagings
- [ ] Validar eventos `partial_discharge`

### Documentación:
- [ ] Actualizar `HANDOFF.md` con cambio
- [ ] Actualizar `ACTIVE_SESSION_STATE.md`
- [ ] Commit de git

---

## 🚀 ESTIMACIÓN DE TIEMPO

- **Modificación de código:** 20 minutos
- **Testing:** 15 minutos
- **Validación:** 10 minutos
- **Documentación:** 10 minutos
- **TOTAL:** ~55 minutos

---

## 📝 COMMIT MESSAGE

```
feat: Implementar descarga multiple en stagings para Tour Mixto

Problema:
- Operarios descargaban todas las WOs en un solo staging
- Productos terminaban en staging incorrecto

Solucion:
- Agrupar WOs por staging_id despues del picking
- Visitar cada staging en orden optimo
- Descargar solo WOs correspondientes a cada staging
- Actualizar cargo_volume progresivamente

Cambios:
- Agregados metodos _agrupar_wos_por_staging() y _ordenar_stagings_por_distancia()
- Modificado agent_process() en GroundOperator y Forklift
- Agregado evento partial_discharge para tracking

Comportamiento:
- Tour con WOs de stagings [1, 3, 5]:
  * Visita staging 1 -> descarga solo WOs staging 1
  * Visita staging 3 -> descarga solo WOs staging 3
  * Visita staging 5 -> descarga solo WOs staging 5

Archivos modificados:
- src/subsystems/simulation/operators.py
```

---

**FIN DEL PLAN**

