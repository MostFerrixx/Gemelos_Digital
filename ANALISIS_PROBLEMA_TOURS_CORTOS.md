# ANALISIS PROFUNDO: PROBLEMA DE TOURS CORTOS EN GROUND OPERATORS

**Fecha:** 2025-10-27  
**Problema:** Ground Operators realizan tours muy cortos (1.75 WOs promedio) con baja utilizacion de capacidad (38.9%)

---

## 1. EVIDENCIA DEL PROBLEMA

### Analisis del JSONL (comportamiento real):
```
GroundOp-01:
  Total Tours: 12
  Promedio WO por tour: 1.75
  Promedio volumen por tour: 58.33L
  Promedio carga pico: 58.33L
  Utilizacion promedio: 38.9%
```

### Configuracion del Sistema:
- **Capacidad GroundOperator:** 150L (config.json indica 150L, pero agent_types indica 500L)
- **Estrategia:** "Ejecucion de Plan (Filtro por Prioridad)"
- **Tour Type:** "Tour Mixto (Multi-Destino)"
- **Max WOs por tour:** 20 (default)

### Work Orders Disponibles:
- **Total WOs iniciales:** 58
- **WOs compatibles con GroundOperator (Area_Ground):** 21 WOs
- **Volumen total disponible:** ~235L

---

## 2. CAUSA RAIZ IDENTIFICADA

### Problema en `src/subsystems/simulation/dispatcher.py`

El metodo `_construir_tour_por_secuencia()` (lineas 502-594) tiene una **logica de secuencia ciclica demasiado estricta** que causa terminacion prematura de tours.

#### Logica Actual (BUGGY):

```python
# Linea 550-591
while len(tour_wos) < self.max_wos_por_tour and volume_acumulado < operator.capacity:
    # Buscar WOs del pick_sequence actual
    candidatos_seq = []
    for wo in area_wos:
        if (wo.pick_sequence == current_sequence_position and  # <-- PROBLEMA AQUI
            wo not in usadas and
            volume_acumulado + wo.calcular_volumen_restante() <= operator.capacity):
            # ... agregar WO
    
    if candidatos_seq:
        # Agregar WO
        # ...
    else:
        # Avanzar secuencia ciclicamente
        current_sequence_position += 1
        if current_sequence_position > max_seq:
            current_sequence_position = 1
        
        # Si revisamos todos los seqs disponibles, salir del area
        if len(seq_checked) >= len(set(wo.pick_sequence for wo in area_wos)):
            break  # <-- SALIDA PREMATURA
```

#### ¿Por que falla?

**Escenario real:**
- Primera WO: `seq=1`
- WOs disponibles: `seq=1, 11, 15, 21, 38, 47, 115, 116, 139, 145...`

**Comportamiento buggy:**
1. Agrega WO con `seq=1` ✅
2. Busca WO con `seq=2` ❌ (no existe)
3. Busca WO con `seq=3` ❌ (no existe)
4. Busca WO con `seq=4` ❌ (no existe)
5. ... continua buscando...
6. Busca WO con `seq=11` ✅ (encontrada)
7. ... pero para entonces ya ha revisado 10+ secuencias
8. **CONDICION DE SALIDA:** `len(seq_checked) >= len(set(wo.pick_sequence for wo in area_wos))`
9. Sale del loop prematuramente

**Resultado:** Solo agrega 1-2 WOs antes de terminar el tour

---

## 3. SIMULACION VS REALIDAD

### Simulacion Simple (sin logica ciclica):
```
Tour final:
  Total WOs: 20
  Volume total: 220L
  Utilizacion: 44.0%
```

### Realidad (con logica ciclica buggy):
```
Tour promedio:
  Total WOs: 1.75
  Volume total: 58.33L
  Utilizacion: 38.9%
```

**CONCLUSION:** La logica ciclica esta causando que los tours terminen **10x mas corto** de lo que podrian ser.

---

## 4. PROBLEMA SECUNDARIO: DISCREPANCIA EN CAPACIDAD

Hay una **discrepancia critica** en la configuracion de capacidad:

### En `config.json`:
```json
{
    "capacidad_carro": 150,  // <-- 150L
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 500,  // <-- 500L (INCONSISTENTE!)
            ...
        }
    ]
}
```

### En codigo (operators.py):
```python
# BaseOperator recibe capacity desde agent_types
self.capacity = capacity  # Esto seria 500L
```

**PROBLEMA:** El sistema esta usando **500L de capacidad** cuando deberia usar **150L**.

Esto explica por que mi simulacion muestra 44% de utilizacion con 220L de carga:
- Si capacidad real es **500L**: 220/500 = 44% ✅
- Si capacidad deberia ser **150L**: 220/150 = 147% (overflow!)

---

## 5. IMPACTO COMBINADO

Los dos problemas se combinan:

1. **Logica ciclica buggy** limita tours a 1-2 WOs
2. **Capacidad incorrecta (500L vs 150L)** hace que incluso esos tours cortos tengan baja utilizacion

**Resultado final:**
- Tours de ~60L en una capacidad de 500L = 12% de utilizacion real
- Tours de ~60L en una capacidad de 150L = 40% de utilizacion (mas realista pero aun bajo)

---

## 6. SOLUCION PROPUESTA

### FASE 1: Corregir logica de construccion de tours

**Reemplazar logica ciclica complicada con logica secuencial simple:**

```python
def _construir_tour_por_secuencia(self, operator: Any, primera_wo: Any, candidatos: List[Any]) -> List[Any]:
    """
    Construye tour siguiendo pick_sequence desde la primera WO.
    VERSION SIMPLIFICADA SIN LOGICA CICLICA
    """
    if not primera_wo or not candidatos:
        return []
    
    # Agregar primera WO
    tour_wos = []
    volume_acumulado = 0
    primera_volume = primera_wo.calcular_volumen_restante()
    
    if primera_volume <= operator.capacity:
        tour_wos.append(primera_wo)
        volume_acumulado += primera_volume
    
    # Filtrar candidatos por area prioritaria
    candidatos_filtrados = [wo for wo in candidatos 
                            if wo != primera_wo 
                            and wo.work_area == primera_wo.work_area]
    
    # Ordenar por pick_sequence
    candidatos_ordenados = sorted(candidatos_filtrados, key=lambda wo: wo.pick_sequence)
    
    # Agregar WOs secuencialmente hasta llenar capacidad o max_wos_por_tour
    for wo in candidatos_ordenados:
        if len(tour_wos) >= self.max_wos_por_tour:
            break
        
        wo_volume = wo.calcular_volumen_restante()
        if volume_acumulado + wo_volume <= operator.capacity:
            tour_wos.append(wo)
            volume_acumulado += wo_volume
        # Si no cabe, continuar probando siguientes WOs (pueden ser mas pequenas)
    
    print(f"[DISPATCHER] Tour construido: {len(tour_wos)} WOs, "
          f"volumen: {volume_acumulado}/{operator.capacity}L "
          f"({(volume_acumulado/operator.capacity)*100:.1f}%)")
    
    return tour_wos
```

### FASE 2: Corregir discrepancia de capacidad

**Opcion A: Unificar en 150L**
```json
{
    "capacidad_carro": 150,
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 150,  // <-- CORREGIDO
            ...
        }
    ]
}
```

**Opcion B: Eliminar `capacidad_carro` redundante**
```json
{
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 150,  // <-- UNICA FUENTE DE VERDAD
            ...
        }
    ]
}
```

### FASE 3: Considerar Tour Mixto (Multi-Destino)

Actualmente el codigo filtra por `wo.work_area == primera_wo.work_area` (misma area).

Si **Tour Mixto** deberia incluir **multiples outbound stagings**, entonces:

```python
# En lugar de filtrar por area:
candidatos_filtrados = [wo for wo in candidatos if wo != primera_wo]

# Ordenar por pick_sequence GLOBAL (no por area)
candidatos_ordenados = sorted(candidatos_filtrados, key=lambda wo: wo.pick_sequence)
```

---

## 7. METRICAS ESPERADAS POST-FIX

### Antes del fix:
- Promedio WO por tour: **1.75**
- Utilizacion promedio: **38.9%** (con capacidad 150L)
- Tours totales: **12**

### Despues del fix (estimado):
- Promedio WO por tour: **8-12** (limitado por capacidad)
- Utilizacion promedio: **70-90%**
- Tours totales: **2-3** (mas eficientes)

---

## 8. PLAN DE IMPLEMENTACION

1. ✅ **Analizar codigo** - COMPLETADO
2. ✅ **Identificar causa raiz** - COMPLETADO
3. ⏳ **Corregir `_construir_tour_por_secuencia()`** - PENDIENTE
4. ⏳ **Corregir discrepancia de capacidad** - PENDIENTE
5. ⏳ **Ajustar filtro de areas para Tour Mixto** - PENDIENTE
6. ⏳ **Probar con simulacion nueva** - PENDIENTE
7. ⏳ **Validar con analisis de JSONL** - PENDIENTE
8. ⏳ **Documentar cambios** - PENDIENTE

---

## 9. ARCHIVOS A MODIFICAR

1. **`src/subsystems/simulation/dispatcher.py`**
   - Metodo: `_construir_tour_por_secuencia()`
   - Lineas: 502-594

2. **`config.json`**
   - Corregir discrepancia de capacidad
   - Unificar en 150L o eliminar `capacidad_carro`

3. **Validacion:**
   - Ejecutar simulacion
   - Analizar JSONL resultante
   - Verificar metricas de utilizacion

---

**FIN DEL ANALISIS**

