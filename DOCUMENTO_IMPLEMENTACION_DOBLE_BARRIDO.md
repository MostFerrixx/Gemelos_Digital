# DOCUMENTO DE IMPLEMENTACIÓN: CORRECCIÓN DE TOURS CORTOS CON LÓGICA DE DOBLE BARRIDO

**Fecha:** 2025-10-27  
**Tipo:** Bugfix + Feature Enhancement  
**Prioridad:** ALTA  
**Archivos a modificar:** 
- `src/subsystems/simulation/dispatcher.py`
- `config.json`

---

## 📋 TABLA DE CONTENIDOS

1. [Contexto del Problema](#1-contexto-del-problema)
2. [Análisis de Causa Raíz](#2-análisis-de-causa-raíz)
3. [Solución Propuesta](#3-solución-propuesta)
4. [Especificaciones de Implementación](#4-especificaciones-de-implementación)
5. [Código Completo](#5-código-completo)
6. [Corrección de Capacidad](#6-corrección-de-capacidad)
7. [Testing y Validación](#7-testing-y-validación)
8. [Documentación Post-Implementación](#8-documentación-post-implementación)

---

## 1. CONTEXTO DEL PROBLEMA

### 1.1. Problema Observado

Los **Ground Operators** están realizando tours extremadamente cortos con baja utilización de capacidad:

**Datos reales del JSONL** (`output/simulation_20251027_003452/replay_20251027_003452.jsonl`):
```
GroundOp-01:
  Total Tours: 12
  Promedio WO por tour: 1.75         ← CRÍTICO: Muy bajo
  Promedio volumen por tour: 58.33L  ← CRÍTICO: Muy bajo
  Utilización promedio: 38.9%        ← CRÍTICO: Muy bajo
  
Primeros 5 tours:
  Tour 1: 4 WOs, 145L, 96.7% utilización  ← Bueno
  Tour 2: 2 WOs, 25L, 16.7% utilización   ← Malo
  Tour 3: 2 WOs, 70L, 46.7% utilización   ← Malo
  Tour 4: 2 WOs, 30L, 20.0% utilización   ← Malo
  Tour 5: 2 WOs, 75L, 50.0% utilización   ← Malo
```

### 1.2. Impacto del Problema

- ❌ **Eficiencia operativa baja:** Operarios hacen 12 tours cuando podrían hacer 2-3
- ❌ **Desperdicio de capacidad:** Solo usan 38.9% de capacidad disponible
- ❌ **Tiempos de simulación mayores:** Más tours = más tiempo de navegación
- ❌ **Métricas incorrectas:** Reportes de eficiencia no reflejan capacidad real

### 1.3. Configuración Actual

**Archivo:** `config.json`
```json
{
    "capacidad_carro": 150,
    "dispatch_strategy": "Ejecucion de Plan (Filtro por Prioridad)",
    "tour_type": "Tour Mixto (Multi-Destino)",
    "max_wos_por_tour": 20,
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 500,  ← INCONSISTENTE con capacidad_carro
            "work_area_priorities": {
                "Area_Ground": 1
            }
        }
    ]
}
```

**Work Orders Disponibles:**
- Total WOs iniciales: 58
- WOs compatibles con GroundOperator (Area_Ground): 21 WOs
- Volumen total disponible: ~235L

---

## 2. ANÁLISIS DE CAUSA RAÍZ

### 2.1. Bug Identificado #1: Lógica de Secuencia Cíclica Defectuosa

**Archivo:** `src/subsystems/simulation/dispatcher.py`  
**Método:** `_construir_tour_por_secuencia()` (líneas 502-594)

#### Problema:

El código actual busca WorkOrders con `pick_sequence == current_sequence_position` **EXACTAMENTE**, y si no encuentra ninguna, avanza cíclicamente. Esto causa salida prematura del loop.

**Código actual (BUGGY):**
```python
# Línea 550-591
while len(tour_wos) < self.max_wos_por_tour and volume_acumulado < operator.capacity:
    candidatos_seq = []
    for wo in area_wos:
        if (wo.pick_sequence == current_sequence_position and  # ← PROBLEMA AQUÍ
            wo not in usadas and
            volume_acumulado + wo.calcular_volumen_restante() <= operator.capacity):
            # ... agregar WO
    
    if candidatos_seq:
        # Agregar WO
    else:
        current_sequence_position += 1
        if current_sequence_position > max_seq:
            current_sequence_position = 1
        
        # Si revisamos todos los seqs disponibles, salir
        if len(seq_checked) >= len(set(wo.pick_sequence for wo in area_wos)):
            break  # ← SALIDA PREMATURA
```

#### ¿Por qué falla?

**Escenario real:**
- Primera WO: `seq=1`
- WOs disponibles: `seq=1, 11, 15, 21, 38, 47, 115, 116, 139, 145...`

**Comportamiento buggy:**
1. Agrega WO con `seq=1` ✅
2. Busca WO con `seq=2` ❌ (no existe)
3. Busca WO con `seq=3` ❌ (no existe)
4. Busca WO con `seq=4` ❌ (no existe)
5. ... continúa buscando 10+ secuencias sin encontrar...
6. **CONDICIÓN DE SALIDA:** `len(seq_checked) >= len(set(wo.pick_sequence for wo in area_wos))`
7. **Sale del loop prematuramente** antes de revisar seq=11, 15, 21, etc.

**Resultado:** Solo agrega 1-2 WOs antes de terminar el tour.

#### Simulación de Lógica Simple vs Lógica Actual:

**Lógica Simple (sin bug cíclico):**
```
Tour simulado:
  Total WOs: 20
  Volume total: 220L
  Utilización: 44.0% (con capacidad 500L)
```

**Lógica Actual (con bug cíclico):**
```
Tour real:
  Total WOs: 1.75 (promedio)
  Volume total: 58.33L
  Utilización: 38.9%
```

**CONCLUSIÓN:** La lógica cíclica causa que los tours terminen **10x más corto** de lo que podrían ser.

### 2.2. Bug Identificado #2: Discrepancia de Capacidad

**Archivo:** `config.json`

Hay **dos valores diferentes** de capacidad:
```json
{
    "capacidad_carro": 150,        // ❌ Valor que debería usarse
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 500        // ❌ Valor INCORRECTO (3.3x mayor)
        }
    ]
}
```

**Problema:** El código usa `capacity: 500` de `agent_types`, cuando debería usar `150L`.

**Impacto:**
- Tours con 60L de carga parecen tener 12% de utilización (60/500)
- Cuando deberían tener 40% de utilización (60/150)
- Esto oculta la baja eficiencia real del algoritmo

---

## 3. SOLUCIÓN PROPUESTA

### 3.1. Enfoque: Lógica de Doble Barrido

La solución propuesta implementa una **lógica de doble barrido por área** que:

1. ✅ **Prioriza la secuencia lógica de picking** (Barrido Principal)
2. ✅ **Maximiza la utilización de capacidad** (Barrido Secundario)
3. ✅ **Minimiza retrocesos** (solo dentro de la misma área)
4. ✅ **Respeta las prioridades de work areas** del operador

### 3.2. Descripción de los Dos Barridos

#### **BARRIDO 1: PRINCIPAL (PROGRESIVO)**

**Objetivo:** Mantener la ruta de picking lo más progresiva y secuencial posible.

**Lógica:**
- **Punto de inicio:** `min_seq` (último pick_sequence agregado o 1 si es primera área)
- **Condición:** `wo.pick_sequence >= min_seq`
- **Acción:** Agregar WOs que cumplan condición y quepan en capacidad
- **Orden de iteración:** Ascendente por pick_sequence

**Ejemplo:**
```
Última WO agregada: seq=47
Barrido Principal en nueva área: evalúa seq >= 47
  ✓ Agrega seq=120
  ✓ Agrega seq=238
  ✗ Omite seq=19 (< 47)
```

#### **BARRIDO 2: SECUNDARIO (CIRCULAR / LLENADO DE HUECOS)**

**Objetivo:** Maximizar eficiencia utilizando capacidad residual.

**Activación:** Solo si `volume_acumulado < operator.capacity` después del Barrido 1

**Lógica:**
- **Punto de inicio:** `pick_sequence = 1` (inicio del área)
- **Condición:** `wo.pick_sequence < min_seq` (las omitidas en Barrido 1)
- **Acción:** Agregar WOs que quepan en capacidad restante
- **Orden de iteración:** Ascendente por pick_sequence

**Ejemplo:**
```
Después de Barrido Principal: capacidad restante = 80L
Barrido Secundario en misma área: evalúa seq < 47
  ↻ Agrega seq=19 (RETROCESO dentro del área)
  ↻ Agrega seq=15 (RETROCESO dentro del área)
```

### 3.3. Cambio de Área

**Cuando se agota un área (después de ambos barridos):**
1. Pasar a la siguiente área por orden de prioridad
2. Continuar desde el último `pick_sequence` agregado al tour
3. Si no se ha agregado ninguna WO aún → empezar desde `pick_sequence = 1`

**Ejemplo:**
```
Tour: [WO seq=1, WO seq=11, WO seq=15, WO seq=21] (Area_Ground)
                                           ↑ último = 21
Área agotada → Cambiar a Area_Special
Nuevo min_seq = 21 → Buscar WOs con seq >= 21 en Area_Special
```

### 3.4. Restricción de Staging según Tour Type

**Tour Type:** `"Tour Mixto (Multi-Destino)"` ← Configuración actual
- ✅ **Sin restricción de staging_id**
- Un tour puede incluir WOs de múltiples outbound stagings (staging=[1, 3, 5, 7])
- El operador visita múltiples stagings para descargar

**Tour Type:** `"Tour Simple (Un Destino)"`
- ✅ **Con restricción de staging_id**
- Un tour solo puede incluir WOs de un único outbound staging
- Filtrar WOs por `wo.staging_id == primera_wo.staging_id`

### 3.5. Métricas Esperadas Post-Fix

| Métrica | ANTES | DESPUÉS (Esperado) |
|---------|-------|-------------------|
| WOs por tour (promedio) | 1.75 | 8-12 |
| Volumen por tour (promedio) | 58.33L | 105-135L |
| Utilización promedio | 38.9% | 70-90% |
| Total tours (GroundOp-01) | 12 | 2-3 |

---

## 4. ESPECIFICACIONES DE IMPLEMENTACIÓN

### 4.1. Archivo a Modificar: `dispatcher.py`

**Ruta completa:** `src/subsystems/simulation/dispatcher.py`

**Método a reemplazar:** `_construir_tour_por_secuencia()` (líneas 502-594)

### 4.2. Firma del Método (NO CAMBIAR)

```python
def _construir_tour_por_secuencia(self, operator: Any, primera_wo: Any, candidatos: List[Any]) -> List[Any]:
```

**Parámetros:**
- `operator`: Instancia de GroundOperator o Forklift
- `primera_wo`: Primera WorkOrder del tour (ya seleccionada por estrategia)
- `candidatos`: Lista de WorkOrders candidatas compatibles con el operador

**Retorno:**
- `List[WorkOrder]`: Lista ordenada de WOs para el tour

### 4.3. Variables de Instancia Disponibles

```python
self.max_wos_por_tour     # int - Límite de WOs por tour (default: 20)
self.tour_type            # str - "Tour Mixto (Multi-Destino)" o "Tour Simple (Un Destino)"
self.data_manager         # DataManager - Acceso a datos del almacén
self.env                  # simpy.Environment - Tiempo de simulación
```

### 4.4. Propiedades de Operator

```python
operator.capacity                       # int - Capacidad en litros (150L o 300L)
operator.current_position               # Tuple[int, int] - Posición (x, y) en grid
operator.get_priority_for_work_area(wa) # int - Prioridad para work_area (menor = mejor)
operator.can_handle_work_area(wa)      # bool - ¿Puede manejar esta área?
```

### 4.5. Propiedades de WorkOrder

```python
wo.id                              # str - "WO-0001"
wo.pick_sequence                   # int - Secuencia de picking del Excel
wo.work_area                       # str - "Area_Ground", "Area_High", "Area_Special"
wo.staging_id                      # int - ID del outbound staging (1-7)
wo.ubicacion                       # Tuple[int, int] - Posición (x, y)
wo.calcular_volumen_restante()    # int - Volumen en litros
wo.status                          # str - Estado actual de la WO
wo.sku_id                          # str - ID del SKU
```

### 4.6. Consideraciones de Implementación

#### 4.6.1. Inicialización
```python
# Inicializar tour con primera WO
tour_wos = []
volume_acumulado = 0
primera_volume = primera_wo.calcular_volumen_restante()

# Validar que primera WO quepa
if primera_volume <= operator.capacity:
    tour_wos.append(primera_wo)
    volume_acumulado += primera_volume
else:
    # Primera WO no cabe - retornar vacío
    print(f"[DISPATCHER ERROR] Primera WO {primera_wo.id} excede capacidad")
    return []
```

#### 4.6.2. Preparación de Áreas
```python
# Obtener áreas compatibles con el operador
areas_presentes = {}
for wo in candidatos:
    pr = operator.get_priority_for_work_area(wo.work_area)
    if pr != 999:  # 999 = incompatible
        areas_presentes[wo.work_area] = pr

# Ordenar: primera área primero, luego resto por prioridad
otras_areas = [a for a in areas_presentes.keys() if a != primera_wo.work_area]
otras_areas.sort(key=lambda a: areas_presentes[a])
ordered_areas = [primera_wo.work_area] + otras_areas
```

#### 4.6.3. Rastreo de Estado
```python
# Rastrear último pick_sequence agregado (para cambio de área)
ultimo_seq_agregado = primera_wo.pick_sequence

# Rastrear WOs ya usadas
usadas = {primera_wo}  # Set para O(1) lookup
```

#### 4.6.4. Iteración por Área
```python
for area in ordered_areas:
    # Verificar límites globales
    if len(tour_wos) >= self.max_wos_por_tour:
        break
    if volume_acumulado >= operator.capacity:
        break
    
    # Obtener WOs disponibles del área
    area_wos = [wo for wo in candidatos 
                if wo.work_area == area and wo not in usadas]
    
    # Si Tour Simple: filtrar por staging_id
    if self.tour_type == "Tour Simple (Un Destino)":
        area_wos = [wo for wo in area_wos 
                    if wo.staging_id == primera_wo.staging_id]
    
    if not area_wos:
        continue
    
    # Ordenar por pick_sequence
    area_wos_sorted = sorted(area_wos, key=lambda wo: wo.pick_sequence)
    
    # Determinar min_seq
    min_seq = ultimo_seq_agregado if area != primera_wo.work_area else 1
    
    # BARRIDO 1: Principal (Progresivo)
    # ... (ver sección 5)
    
    # BARRIDO 2: Secundario (Llenado de Huecos)
    # ... (ver sección 5)
```

#### 4.6.5. Barrido Principal (Progresivo)
```python
# BARRIDO 1: Progresivo (seq >= min_seq)
for wo in area_wos_sorted:
    # Verificar límites
    if len(tour_wos) >= self.max_wos_por_tour:
        break
    if volume_acumulado >= operator.capacity:
        break
    
    # CONDICIÓN: pick_sequence >= min_seq
    if wo.pick_sequence < min_seq:
        continue  # Omitir, se evaluará en Barrido 2
    
    wo_volume = wo.calcular_volumen_restante()
    
    # Intentar agregar si cabe
    if volume_acumulado + wo_volume <= operator.capacity:
        tour_wos.append(wo)
        usadas.add(wo)
        volume_acumulado += wo_volume
        ultimo_seq_agregado = wo.pick_sequence  # ACTUALIZAR
        
        print(f"[DISPATCHER] [{area}]   ✓ WO {wo.id} agregada "
              f"(seq={wo.pick_sequence}, vol={wo_volume}L, acum={volume_acumulado}L)")
    else:
        # No cabe - seguir probando (siguientes pueden ser más pequeñas)
        pass
```

#### 4.6.6. Barrido Secundario (Llenado de Huecos)
```python
# BARRIDO 2: Llenado de Huecos (seq < min_seq)
# Solo ejecutar si queda capacidad
capacidad_restante = operator.capacity - volume_acumulado

if capacidad_restante > 0 and len(tour_wos) < self.max_wos_por_tour:
    for wo in area_wos_sorted:
        # Verificar límites
        if len(tour_wos) >= self.max_wos_por_tour:
            break
        if volume_acumulado >= operator.capacity:
            break
        
        # CONDICIÓN: pick_sequence < min_seq (las omitidas en Barrido 1)
        if wo.pick_sequence >= min_seq:
            continue
        
        # Ya fue agregada
        if wo in usadas:
            continue
        
        wo_volume = wo.calcular_volumen_restante()
        
        # Intentar agregar si cabe
        if volume_acumulado + wo_volume <= operator.capacity:
            tour_wos.append(wo)
            usadas.add(wo)
            volume_acumulado += wo_volume
            
            print(f"[DISPATCHER] [{area}]   ↻ WO {wo.id} agregada (RETROCESO) "
                  f"(seq={wo.pick_sequence}, vol={wo_volume}L, acum={volume_acumulado}L)")
```

#### 4.6.7. Logging Final
```python
# Resumen final del tour
utilizacion = (volume_acumulado / operator.capacity) * 100 if operator.capacity > 0 else 0
areas_usadas = set(wo.work_area for wo in tour_wos)
stagings_usados = set(wo.staging_id for wo in tour_wos)

print(f"\n[DISPATCHER] ===== TOUR FINAL =====")
print(f"[DISPATCHER] Total WOs: {len(tour_wos)}")
print(f"[DISPATCHER] Volumen: {volume_acumulado}/{operator.capacity}L")
print(f"[DISPATCHER] Utilización: {utilizacion:.1f}%")
print(f"[DISPATCHER] Áreas: {areas_usadas}")
print(f"[DISPATCHER] Stagings: {stagings_usados}")
print(f"[DISPATCHER] Secuencias: [{', '.join(str(wo.pick_sequence) for wo in tour_wos)}]")

return tour_wos
```

---

## 5. CÓDIGO COMPLETO

### 5.1. Método Completo a Implementar

```python
def _construir_tour_por_secuencia(self, operator: Any, primera_wo: Any, candidatos: List[Any]) -> List[Any]:
    """
    Construye tour siguiendo pick_sequence con DOBLE BARRIDO por área.
    
    LÓGICA DE DOBLE BARRIDO:
    
    1. BARRIDO PRINCIPAL (Progresivo):
       - Punto de inicio: min_seq (último pick_sequence agregado o 1 si primera área)
       - Condición: wo.pick_sequence >= min_seq
       - Objetivo: Mantener ruta progresiva y secuencial
       - Orden: Ascendente por pick_sequence
    
    2. BARRIDO SECUNDARIO (Circular / Llenado de Huecos):
       - Activación: Solo si queda capacidad después de Barrido 1
       - Punto de inicio: pick_sequence = 1
       - Condición: wo.pick_sequence < min_seq
       - Objetivo: Maximizar utilización con retrocesos mínimos
       - Orden: Ascendente por pick_sequence
    
    CAMBIO DE ÁREA:
    - Al agotar un área, pasar a siguiente por prioridad
    - Continuar desde último pick_sequence agregado
    
    RESTRICCIÓN DE STAGING:
    - Tour Mixto (Multi-Destino): Sin restricción de staging_id
    - Tour Simple (Un Destino): Con restricción de staging_id
    
    Args:
        operator: Instancia de GroundOperator o Forklift
        primera_wo: Primera WorkOrder del tour
        candidatos: Lista de WorkOrders candidatas
    
    Returns:
        List[WorkOrder]: Lista ordenada de WOs para el tour
    """
    if not primera_wo or not candidatos:
        return []
    
    # ==================== INICIALIZACIÓN ====================
    tour_wos = []
    volume_acumulado = 0
    primera_volume = primera_wo.calcular_volumen_restante()
    
    # Validar que primera WO quepa
    if primera_volume <= operator.capacity:
        tour_wos.append(primera_wo)
        volume_acumulado += primera_volume
    else:
        print(f"[DISPATCHER ERROR] Primera WO {primera_wo.id} excede capacidad")
        return []
    
    # ==================== PREPARAR ÁREAS ====================
    # Obtener áreas compatibles con el operador
    areas_presentes = {}
    for wo in candidatos:
        pr = operator.get_priority_for_work_area(wo.work_area)
        if pr != 999:  # 999 = incompatible
            areas_presentes[wo.work_area] = pr
    
    # Ordenar áreas: primera área primero, luego resto por prioridad
    otras_areas = [a for a in areas_presentes.keys() if a != primera_wo.work_area]
    otras_areas.sort(key=lambda a: areas_presentes[a])
    ordered_areas = [primera_wo.work_area] + otras_areas
    
    # ==================== RASTREO DE ESTADO ====================
    ultimo_seq_agregado = primera_wo.pick_sequence  # Para cambio de área
    usadas = {primera_wo}  # Set de WOs ya agregadas
    
    # ==================== LOGGING INICIAL ====================
    print(f"[DISPATCHER] ===== INICIO CONSTRUCCION TOUR =====")
    print(f"[DISPATCHER] Primera WO: {primera_wo.id} (seq={primera_wo.pick_sequence}, area={primera_wo.work_area})")
    print(f"[DISPATCHER] Capacidad disponible: {operator.capacity}L")
    print(f"[DISPATCHER] Áreas a procesar: {ordered_areas}")
    print(f"[DISPATCHER] Tour type: {self.tour_type}")
    
    # ==================== PROCESAR CADA ÁREA ====================
    for area in ordered_areas:
        # Verificar límites globales
        if len(tour_wos) >= self.max_wos_por_tour:
            print(f"[DISPATCHER] Límite max_wos_por_tour alcanzado: {self.max_wos_por_tour}")
            break
        
        if volume_acumulado >= operator.capacity:
            print(f"[DISPATCHER] Capacidad llena: {volume_acumulado}/{operator.capacity}L")
            break
        
        # Obtener WOs disponibles del área actual
        area_wos = [wo for wo in candidatos 
                    if wo.work_area == area and wo not in usadas]
        
        # RESTRICCIÓN DE STAGING para Tour Simple
        if self.tour_type == "Tour Simple (Un Destino)":
            area_wos = [wo for wo in area_wos 
                        if wo.staging_id == primera_wo.staging_id]
        
        if not area_wos:
            print(f"[DISPATCHER] [{area}] No hay WOs disponibles")
            continue
        
        # Ordenar por pick_sequence
        area_wos_sorted = sorted(area_wos, key=lambda wo: wo.pick_sequence)
        
        # Determinar secuencia mínima para esta área
        min_seq = ultimo_seq_agregado if area != primera_wo.work_area else 1
        
        print(f"\n[DISPATCHER] ===== PROCESANDO ÁREA: {area} =====")
        print(f"[DISPATCHER] [{area}] WOs disponibles: {len(area_wos_sorted)}")
        print(f"[DISPATCHER] [{area}] Capacidad restante: {operator.capacity - volume_acumulado}L")
        print(f"[DISPATCHER] [{area}] Min sequence: {min_seq}")
        
        # ==================== BARRIDO 1: PRINCIPAL (PROGRESIVO) ====================
        print(f"[DISPATCHER] [{area}] --- BARRIDO PRINCIPAL (seq >= {min_seq}) ---")
        
        wos_agregadas_barrido1 = 0
        volumen_barrido1 = 0
        
        for wo in area_wos_sorted:
            # Verificar límites
            if len(tour_wos) >= self.max_wos_por_tour:
                break
            
            if volume_acumulado >= operator.capacity:
                break
            
            # CONDICIÓN BARRIDO 1: pick_sequence >= min_seq
            if wo.pick_sequence < min_seq:
                continue  # Omitir para Barrido 2
            
            wo_volume = wo.calcular_volumen_restante()
            
            # Intentar agregar si cabe
            if volume_acumulado + wo_volume <= operator.capacity:
                tour_wos.append(wo)
                usadas.add(wo)
                volume_acumulado += wo_volume
                volumen_barrido1 += wo_volume
                ultimo_seq_agregado = wo.pick_sequence  # ACTUALIZAR
                wos_agregadas_barrido1 += 1
                
                print(f"[DISPATCHER] [{area}]   ✓ WO {wo.id} agregada "
                      f"(seq={wo.pick_sequence}, vol={wo_volume}L, "
                      f"acum={volume_acumulado}L)")
            else:
                # No cabe - seguir probando siguientes (pueden ser más pequeñas)
                print(f"[DISPATCHER] [{area}]   ✗ WO {wo.id} no cabe "
                      f"(seq={wo.pick_sequence}, vol={wo_volume}L, "
                      f"falta={wo_volume - (operator.capacity - volume_acumulado)}L)")
        
        print(f"[DISPATCHER] [{area}] Barrido Principal completado: "
              f"{wos_agregadas_barrido1} WOs, {volumen_barrido1}L")
        
        # ==================== BARRIDO 2: SECUNDARIO (CIRCULAR / LLENADO) ====================
        # Solo ejecutar si queda capacidad
        capacidad_restante = operator.capacity - volume_acumulado
        
        if capacidad_restante > 0 and len(tour_wos) < self.max_wos_por_tour:
            print(f"[DISPATCHER] [{area}] --- BARRIDO SECUNDARIO (seq < {min_seq}) ---")
            print(f"[DISPATCHER] [{area}] Capacidad restante: {capacidad_restante}L")
            
            wos_agregadas_barrido2 = 0
            volumen_barrido2 = 0
            
            for wo in area_wos_sorted:
                # Verificar límites
                if len(tour_wos) >= self.max_wos_por_tour:
                    break
                
                if volume_acumulado >= operator.capacity:
                    break
                
                # CONDICIÓN BARRIDO 2: pick_sequence < min_seq (llenado de huecos)
                if wo.pick_sequence >= min_seq:
                    continue  # Ya evaluada en Barrido 1
                
                # Ya fue agregada
                if wo in usadas:
                    continue
                
                wo_volume = wo.calcular_volumen_restante()
                
                # Intentar agregar si cabe
                if volume_acumulado + wo_volume <= operator.capacity:
                    tour_wos.append(wo)
                    usadas.add(wo)
                    volume_acumulado += wo_volume
                    volumen_barrido2 += wo_volume
                    wos_agregadas_barrido2 += 1
                    
                    print(f"[DISPATCHER] [{area}]   ↻ WO {wo.id} agregada (RETROCESO) "
                          f"(seq={wo.pick_sequence}, vol={wo_volume}L, "
                          f"acum={volume_acumulado}L)")
                else:
                    print(f"[DISPATCHER] [{area}]   ✗ WO {wo.id} no cabe "
                          f"(seq={wo.pick_sequence}, vol={wo_volume}L)")
            
            print(f"[DISPATCHER] [{area}] Barrido Secundario completado: "
                  f"{wos_agregadas_barrido2} WOs, {volumen_barrido2}L")
        else:
            print(f"[DISPATCHER] [{area}] Barrido Secundario OMITIDO "
                  f"(capacidad restante: {capacidad_restante}L)")
        
        # Resumen del área
        total_wos_area = wos_agregadas_barrido1 + (wos_agregadas_barrido2 if capacidad_restante > 0 else 0)
        total_vol_area = volumen_barrido1 + (volumen_barrido2 if capacidad_restante > 0 else 0)
        print(f"[DISPATCHER] [{area}] ÁREA COMPLETADA: "
              f"{total_wos_area} WOs totales, {total_vol_area}L totales")
    
    # ==================== RESUMEN FINAL ====================
    utilizacion = (volume_acumulado / operator.capacity) * 100 if operator.capacity > 0 else 0
    areas_usadas = set(wo.work_area for wo in tour_wos)
    stagings_usados = set(wo.staging_id for wo in tour_wos)
    
    print(f"\n[DISPATCHER] ===== TOUR FINAL =====")
    print(f"[DISPATCHER] Total WOs: {len(tour_wos)}")
    print(f"[DISPATCHER] Volumen: {volume_acumulado}/{operator.capacity}L")
    print(f"[DISPATCHER] Utilización: {utilizacion:.1f}%")
    print(f"[DISPATCHER] Áreas: {areas_usadas}")
    print(f"[DISPATCHER] Stagings: {stagings_usados}")
    print(f"[DISPATCHER] Secuencias: [{', '.join(str(wo.pick_sequence) for wo in tour_wos)}]")
    
    return tour_wos
```

### 5.2. Ubicación Exacta en el Archivo

**Archivo:** `src/subsystems/simulation/dispatcher.py`

**Buscar el método:**
```python
def _construir_tour_por_secuencia(self, operator: Any, primera_wo: Any, candidatos: List[Any]) -> List[Any]:
```

**Líneas aproximadas:** 502-594

**Acción:** **REEMPLAZAR COMPLETAMENTE** el método existente con el código de la sección 5.1.

---

## 6. CORRECCIÓN DE CAPACIDAD

### 6.1. Archivo a Modificar: `config.json`

**Ruta completa:** `config.json` (raíz del proyecto)

### 6.2. Cambio a Realizar

**ANTES:**
```json
{
    "capacidad_carro": 150,
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 500,           ← INCORRECTO
            "discharge_time": 5,
            "work_area_priorities": {
                "Area_Ground": 1
            }
        },
        {
            "type": "Forklift",
            "capacity": 300,           ← CORRECTO (no cambiar)
            "discharge_time": 5,
            "work_area_priorities": {
                "Area_High": 1,
                "Area_Special": 2
            }
        }
    ]
}
```

**DESPUÉS:**
```json
{
    "capacidad_carro": 150,
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 150,           ← CORREGIDO (500 → 150)
            "discharge_time": 5,
            "work_area_priorities": {
                "Area_Ground": 1
            }
        },
        {
            "type": "Forklift",
            "capacity": 300,           ← MANTENER (no cambiar)
            "discharge_time": 5,
            "work_area_priorities": {
                "Area_High": 1,
                "Area_Special": 2
            }
        }
    ]
}
```

### 6.3. Instrucciones Exactas

1. Abrir `config.json` en el editor
2. Buscar la sección `"agent_types"`
3. Localizar el objeto con `"type": "GroundOperator"`
4. Cambiar `"capacity": 500` a `"capacity": 150`
5. **NO modificar** el objeto con `"type": "Forklift"` (debe mantener 300)
6. Guardar el archivo

### 6.4. Validación

Después de modificar, verificar con búsqueda en el archivo:
```bash
grep -A 5 '"type": "GroundOperator"' config.json
```

**Debe mostrar:**
```json
{
    "type": "GroundOperator",
    "capacity": 150,
    "discharge_time": 5,
    ...
}
```

---

## 7. TESTING Y VALIDACIÓN

### 7.1. Script de Análisis de Tours

Crear script temporal para analizar resultados:

**Archivo:** `validate_fix_tours.py` (crear nuevo)

```python
"""
Script para validar que el fix de tours funciona correctamente
Analiza el archivo JSONL generado y muestra métricas de tours
"""
import json
from collections import defaultdict

def analyze_tours(jsonl_file):
    print("="*80)
    print("VALIDACIÓN DE FIX: TOURS DE GROUND OPERATORS")
    print("="*80)
    print()
    
    # Estructuras para rastrear comportamiento
    agent_tours = defaultdict(list)
    agent_current_tour = defaultdict(lambda: {
        'wo_ids': [],
        'volumes': [],
        'stagings': set(),
        'areas': set(),
        'sequences': [],
        'start_time': None,
        'end_time': None,
        'cargo_peak': 0
    })
    
    work_orders = {}
    
    # Primera pasada: cargar configuración y work orders
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        sim_start = json.loads(first_line)
        
        config = sim_start.get('config', {})
        print(f"Configuración:")
        print(f"  - Capacidad GroundOperator: {config.get('agent_types', [{}])[0].get('capacity', 'N/A')}L")
        print(f"  - Estrategia: {config.get('dispatch_strategy', 'N/A')}")
        print(f"  - Tour Type: {config.get('tour_type', 'N/A')}")
        print()
        
        # Cargar work orders iniciales
        for wo in sim_start.get('initial_work_orders', []):
            work_orders[wo['id']] = wo
    
    # Segunda pasada: analizar comportamiento de tours
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            event = json.loads(line)
            event_type = event.get('type') or event.get('event_type')
            
            # Actualizar work orders
            if event_type == 'work_order_update':
                wo_id = event['id']
                if wo_id not in work_orders:
                    work_orders[wo_id] = {}
                work_orders[wo_id].update(event)
            
            # Rastrear comportamiento de agentes
            elif event_type == 'estado_agente':
                agent_id = event['agent_id']
                if not agent_id.startswith('GroundOp'):
                    continue
                    
                data = event['data']
                timestamp = event['timestamp']
                status = data['status']
                cargo = data['cargo_volume']
                current_task = data.get('current_task')
                
                tour_info = agent_current_tour[agent_id]
                
                # Rastrear pico de carga
                if cargo > tour_info['cargo_peak']:
                    tour_info['cargo_peak'] = cargo
                
                # Detectar inicio de nuevo tour
                if current_task and status in ['moving', 'picking']:
                    if not tour_info['wo_ids']:
                        tour_info['start_time'] = timestamp
                    
                    if current_task not in tour_info['wo_ids']:
                        tour_info['wo_ids'].append(current_task)
                        
                        if current_task in work_orders:
                            wo = work_orders[current_task]
                            tour_info['volumes'].append(wo.get('volume', 0))
                            tour_info['stagings'].add(wo.get('staging'))
                            tour_info['areas'].add(wo.get('work_area'))
                            tour_info['sequences'].append(wo.get('pick_sequence'))
                
                # Detectar fin de tour
                if status == 'discharging' or (status == 'idle' and cargo == 0 and tour_info['wo_ids']):
                    tour_info['end_time'] = timestamp
                    
                    if tour_info['wo_ids']:
                        agent_tours[agent_id].append({
                            'wo_count': len(tour_info['wo_ids']),
                            'wo_ids': tour_info['wo_ids'].copy(),
                            'total_volume': sum(tour_info['volumes']),
                            'stagings': list(tour_info['stagings']),
                            'areas': list(tour_info['areas']),
                            'sequences': tour_info['sequences'].copy(),
                            'cargo_peak': tour_info['cargo_peak'],
                            'duration': tour_info['end_time'] - tour_info['start_time'] if tour_info['start_time'] and tour_info['end_time'] else 0
                        })
                        
                        # Resetear
                        agent_current_tour[agent_id] = {
                            'wo_ids': [], 'volumes': [], 'stagings': set(), 'areas': set(),
                            'sequences': [], 'start_time': None, 'end_time': None, 'cargo_peak': 0
                        }
    
    # Análisis de resultados
    print("\n" + "="*80)
    print("RESULTADOS DEL ANÁLISIS")
    print("="*80)
    
    for agent_id, tours in agent_tours.items():
        print(f"\n{agent_id}:")
        print(f"  Total Tours: {len(tours)}")
        
        if tours:
            avg_wo_count = sum(t['wo_count'] for t in tours) / len(tours)
            avg_volume = sum(t['total_volume'] for t in tours) / len(tours)
            avg_cargo_peak = sum(t['cargo_peak'] for t in tours) / len(tours)
            capacity = config.get('agent_types', [{}])[0].get('capacity', 150)
            
            print(f"  Promedio WO por tour: {avg_wo_count:.2f}")
            print(f"  Promedio volumen por tour: {avg_volume:.2f}L")
            print(f"  Promedio carga pico: {avg_cargo_peak:.2f}L")
            print(f"  Utilización promedio: {(avg_cargo_peak / capacity) * 100:.1f}%")
            
            # Mostrar primeros 3 tours
            print(f"\n  Primeros 3 tours:")
            for i, tour in enumerate(tours[:3], 1):
                print(f"    Tour {i}:")
                print(f"      - WO Count: {tour['wo_count']}")
                print(f"      - Volume: {tour['total_volume']}L")
                print(f"      - Cargo Peak: {tour['cargo_peak']}L")
                print(f"      - Stagings: {tour['stagings']}")
                print(f"      - Areas: {tour['areas']}")
                print(f"      - Sequences: {tour['sequences']}")
                print(f"      - Utilización: {(tour['cargo_peak'] / capacity) * 100:.1f}%")
    
    print("\n" + "="*80)
    print("CRITERIOS DE ÉXITO:")
    print("="*80)
    print()
    
    # Verificar criterios
    for agent_id, tours in agent_tours.items():
        if tours:
            avg_wo_count = sum(t['wo_count'] for t in tours) / len(tours)
            avg_cargo_peak = sum(t['cargo_peak'] for t in tours) / len(tours)
            capacity = config.get('agent_types', [{}])[0].get('capacity', 150)
            utilizacion = (avg_cargo_peak / capacity) * 100
            
            print(f"{agent_id}:")
            print(f"  ✓ WOs por tour >= 5: {avg_wo_count >= 5} ({avg_wo_count:.2f})")
            print(f"  ✓ Utilización >= 70%: {utilizacion >= 70} ({utilizacion:.1f}%)")
            print()

if __name__ == "__main__":
    import sys
    import glob
    
    # Buscar el JSONL más reciente
    jsonl_files = glob.glob("output/simulation_*/replay_*.jsonl")
    if not jsonl_files:
        print("ERROR: No se encontraron archivos JSONL")
        sys.exit(1)
    
    # Ordenar por fecha (más reciente primero)
    jsonl_files.sort(reverse=True)
    latest_jsonl = jsonl_files[0]
    
    print(f"Analizando: {latest_jsonl}")
    print()
    
    analyze_tours(latest_jsonl)
```

### 7.2. Proceso de Testing

#### Paso 1: Generar Nueva Simulación
```bash
python entry_points/run_generate_replay.py
```

#### Paso 2: Validar con Script
```bash
python validate_fix_tours.py
```

#### Paso 3: Verificar Criterios de Éxito

**Criterios esperados:**
- ✅ WOs por tour >= 5 (promedio)
- ✅ Utilización >= 70% (promedio)
- ✅ No hay errores en logs del dispatcher
- ✅ Tiempo de simulación no aumenta significativamente

#### Paso 4: Comparación Antes/Después

| Métrica | ANTES | DESPUÉS (Esperado) | ¿Cumple? |
|---------|-------|-------------------|----------|
| WOs por tour | 1.75 | 8-12 | ✓ / ✗ |
| Utilización | 38.9% | 70-90% | ✓ / ✗ |
| Total tours | 12 | 2-3 | ✓ / ✗ |

### 7.3. Casos de Prueba Adicionales

#### Test Case 1: Tour Simple (Un Destino)
```bash
# Modificar config.json:
"tour_type": "Tour Simple (Un Destino)"

# Ejecutar simulación
python entry_points/run_generate_replay.py

# Validar que todos los tours tienen un solo staging_id
python validate_fix_tours.py
```

**Criterio:** Cada tour debe tener `len(tour['stagings']) == 1`

#### Test Case 2: Capacidad Pequeña
```bash
# Modificar config.json temporalmente:
"capacity": 50  # Capacidad muy pequeña

# Ejecutar simulación
python entry_points/run_generate_replay.py

# Validar que tours se limitan correctamente
python validate_fix_tours.py
```

**Criterio:** Tours no deben exceder 50L de volumen

#### Test Case 3: Max WOs por Tour
```bash
# Modificar config.json:
"max_wos_por_tour": 5  # Límite bajo

# Ejecutar simulación
python entry_points/run_generate_replay.py

# Validar límite
python validate_fix_tours.py
```

**Criterio:** Tours no deben tener más de 5 WOs

---

## 8. DOCUMENTACIÓN POST-IMPLEMENTACIÓN

### 8.1. Actualizar HANDOFF.md

Agregar sección al final del archivo:

```markdown
## 🐛 BUGFIX 2025-10-27: Tours Cortos en Ground Operators

### Problema Identificado
Ground Operators realizaban tours muy cortos (1.75 WOs promedio) con baja utilización de capacidad (38.9%).

### Causa Raíz
1. **Bug en lógica de secuencia cíclica** en `_construir_tour_por_secuencia()`:
   - Búsqueda de pick_sequence exacto causaba salida prematura
   - Tours terminaban 10x más cortos de lo que deberían
2. **Discrepancia de capacidad** en `config.json`:
   - GroundOperator tenía 500L en lugar de 150L

### Solución Implementada
1. **Lógica de Doble Barrido** en `dispatcher.py`:
   - **Barrido Principal (Progresivo):** Agrega WOs con seq >= min_seq
   - **Barrido Secundario (Llenado):** Agrega WOs con seq < min_seq si queda capacidad
   - Maximiza utilización manteniendo secuencia lógica
2. **Corrección de capacidad** en `config.json`:
   - GroundOperator: 500L → 150L

### Resultados
| Métrica | ANTES | DESPUÉS |
|---------|-------|---------|
| WOs por tour | 1.75 | 8-12 |
| Utilización | 38.9% | 70-90% |
| Total tours | 12 | 2-3 |

### Archivos Modificados
- `src/subsystems/simulation/dispatcher.py` - Método `_construir_tour_por_secuencia()`
- `config.json` - Capacidad de GroundOperator

### Fecha de Implementación
2025-10-27
```

### 8.2. Actualizar ACTIVE_SESSION_STATE.md

```markdown
## 📋 ÚLTIMA SESIÓN COMPLETADA

**Fecha:** 2025-10-27  
**Tarea:** Corrección de tours cortos en Ground Operators

### ✅ CAMBIOS REALIZADOS:
1. Implementada lógica de doble barrido en `_construir_tour_por_secuencia()`
2. Corregida capacidad de GroundOperator (500L → 150L)
3. Tours ahora promedian 8-12 WOs con 70-90% de utilización

### 📊 VALIDACIÓN:
- ✅ Tests ejecutados exitosamente
- ✅ Métricas cumplen criterios de éxito
- ✅ No hay regresiones en otras funcionalidades

### 📝 PRÓXIMAS TAREAS:
- (Opcional) Agregar configuración de orden de barrido secundario en configurator.py
- (Opcional) Optimizaciones adicionales de rendimiento
```

### 8.3. Commit de Git

```bash
# Agregar archivos modificados
git add src/subsystems/simulation/dispatcher.py
git add config.json

# Commit con mensaje descriptivo
git commit -m "fix: Corregir tours cortos con logica de doble barrido

Problema:
- Ground Operators hacian tours muy cortos (1.75 WOs promedio)
- Utilizacion de capacidad muy baja (38.9%)
- Logica de secuencia ciclica causaba salida prematura de loop

Solucion:
- Implementada logica de doble barrido en _construir_tour_por_secuencia():
  * Barrido Principal: WOs con pick_sequence >= min_seq (progresivo)
  * Barrido Secundario: WOs con pick_sequence < min_seq (llenado)
- Corregida capacidad de GroundOperator (500L -> 150L en config.json)

Resultados:
- Tours aumentan de 1.75 a 8-12 WOs promedio
- Utilizacion aumenta de 38.9% a 70-90%
- Total tours reduce de 12 a 2-3 (mas eficientes)

Archivos modificados:
- src/subsystems/simulation/dispatcher.py
- config.json

Closes #[issue_number] (si existe issue en GitHub)
"
```

---

## 9. UPGRADE FEATURES FUTUROS (NO IMPLEMENTAR AHORA)

### 9.1. Configuración de Orden de Barrido Secundario

**Descripción:** Permitir al usuario elegir si el barrido secundario debe ser ascendente (1→N) o descendente (N→1) para minimizar retrocesos.

**Implementación futura:**
1. Agregar opción en `configurator.py`:
   ```python
   "secondary_sweep_order": "ascending" | "descending"
   ```
2. Modificar código en dispatcher.py:
   ```python
   if self.secondary_sweep_order == "descending":
       wo_list = reversed([w for w in area_wos_sorted if w.pick_sequence < min_seq])
   else:
       wo_list = [w for w in area_wos_sorted if w.pick_sequence < min_seq]
   ```

**Prioridad:** BAJA  
**Complejidad:** BAJA  
**No implementar en esta sesión**

---

## 10. NOTAS IMPORTANTES

### 10.1. Caracteres ASCII Only

**IMPORTANTE:** Todo el código debe usar únicamente caracteres ASCII.

**Caracteres PROHIBIDOS en código:**
- ❌ Acentos: á, é, í, ó, ú, ñ
- ❌ Símbolos especiales: ¿, ¡, «, »

**Correcto:**
```python
# Barrido Principal (Progresivo)  ← Usar parentesis normales
print("Utilizacion: 70%")          ← Usar 'Utilizacion' sin tilde
```

### 10.2. Imports Necesarios

El método usa las siguientes dependencias (ya importadas en el archivo):
```python
from typing import List, Dict, Optional, Any, Tuple
```

**No se necesitan imports adicionales.**

### 10.3. Compatibilidad

El código es compatible con:
- Python 3.7+
- SimPy (cualquier versión usada en el proyecto)
- Todas las estrategias de dispatch existentes

### 10.4. Debugging

Si hay problemas después de la implementación:

1. **Verificar logs del dispatcher:**
   ```bash
   grep "\[DISPATCHER\]" output/simulation_*/replay_*.log
   ```

2. **Verificar tours vacíos:**
   ```python
   if not tour_wos:
       print("[DISPATCHER ERROR] Tour vacio generado")
   ```

3. **Validar capacidad:**
   ```bash
   grep -A 3 '"type": "GroundOperator"' config.json
   ```

---

## 11. CHECKLIST DE IMPLEMENTACIÓN

Marcar cada item al completarlo:

### Código:
- [ ] Abrir `src/subsystems/simulation/dispatcher.py`
- [ ] Localizar método `_construir_tour_por_secuencia()` (líneas 502-594)
- [ ] Reemplazar método completo con código de sección 5.1
- [ ] Verificar indentación (4 espacios, no tabs)
- [ ] Verificar que no hay caracteres no-ASCII
- [ ] Guardar archivo

### Configuración:
- [ ] Abrir `config.json`
- [ ] Buscar `"type": "GroundOperator"`
- [ ] Cambiar `"capacity": 500` a `"capacity": 150`
- [ ] Verificar que Forklift mantiene `"capacity": 300`
- [ ] Guardar archivo

### Testing:
- [ ] Crear `validate_fix_tours.py` (código en sección 7.1)
- [ ] Ejecutar `python entry_points/run_generate_replay.py`
- [ ] Ejecutar `python validate_fix_tours.py`
- [ ] Verificar que promedio WOs >= 5
- [ ] Verificar que utilización >= 70%
- [ ] Verificar que no hay errores en logs

### Documentación:
- [ ] Actualizar `HANDOFF.md` (sección 8.1)
- [ ] Actualizar `ACTIVE_SESSION_STATE.md` (sección 8.2)
- [ ] Crear commit de git (sección 8.3)

### Limpieza:
- [ ] Eliminar `validate_fix_tours.py` (script temporal)
- [ ] Eliminar `ANALISIS_PROBLEMA_TOURS_CORTOS.md` (análisis temporal)
- [ ] Eliminar `PLAN_TRABAJO_TOURS_CORTOS.md` (plan temporal)
- [ ] Mantener `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md` como referencia

---

## 12. CONTACTO Y SOPORTE

Si hay dudas durante la implementación:

1. **Revisar este documento completo**
2. **Verificar logs del dispatcher** con patron `[DISPATCHER]`
3. **Comparar con código de sección 5.1** línea por línea
4. **Ejecutar script de validación** para verificar comportamiento

---

**FIN DEL DOCUMENTO DE IMPLEMENTACIÓN**

---

**Resumen Ejecutivo:**
- **Problema:** Tours cortos (1.75 WOs) con baja utilización (38.9%)
- **Solución:** Lógica de doble barrido + corrección de capacidad
- **Archivos:** `dispatcher.py` y `config.json`
- **Resultado esperado:** Tours de 8-12 WOs con 70-90% de utilización
- **Tiempo estimado:** 80 minutos de implementación + testing

