# PLAN DE TRABAJO: CORRECCION DE TOURS CORTOS EN GROUND OPERATORS

**Fecha:** 2025-10-27  
**Problema:** Ground Operators realizan tours con baja utilizacion de capacidad  
**Causa Raiz:** Logica de secuencia ciclica buggy en `_construir_tour_por_secuencia()`

---

## RESUMEN EJECUTIVO

El Ground Operator esta haciendo tours de **1.75 WOs** en promedio con **38.9% de utilizacion**, cuando podria hacer tours de **8-12 WOs** con **70-90% de utilizacion**.

### Causa Identificada:
1. **Bug principal:** Logica de secuencia ciclica en `dispatcher.py` termina tours prematuramente
2. **Bug secundario:** Discrepancia de capacidad (150L vs 500L) en `config.json`

---

## FASE 1: CORRECCION DE LOGICA DE CONSTRUCCION DE TOURS ⚠️ CRITICO

### Archivo: `src/subsystems/simulation/dispatcher.py`
### Metodo: `_construir_tour_por_secuencia()` (lineas 502-594)

#### Problema Actual:
La logica busca WOs con `pick_sequence == current_sequence_position` exactamente, y si no encuentra ninguna, avanza ciclicamente. Esto causa salida prematura del loop cuando hay "saltos" en los numeros de secuencia.

#### Solucion:
Reemplazar logica ciclica complicada con logica secuencial simple que:
1. Ordena WOs por `pick_sequence`
2. Agrega WOs consecutivamente hasta llenar capacidad
3. No usa logica de busqueda de secuencia especifica

#### Codigo Propuesto:

```python
def _construir_tour_por_secuencia(self, operator: Any, primera_wo: Any, candidatos: List[Any]) -> List[Any]:
    """
    Construye tour siguiendo pick_sequence desde la primera WO.
    VERSION SIMPLIFICADA: Ordena por pick_sequence y llena capacidad.
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
    else:
        # Primera WO no cabe - retornar vacio
        print(f"[DISPATCHER ERROR] Primera WO {primera_wo.id} excede capacidad")
        return []
    
    # Preparar candidatos del area de la primera WO
    candidatos_misma_area = [wo for wo in candidatos 
                              if wo != primera_wo 
                              and wo.work_area == primera_wo.work_area]
    
    # Ordenar por pick_sequence
    candidatos_ordenados = sorted(candidatos_misma_area, 
                                   key=lambda wo: wo.pick_sequence)
    
    # Agregar WOs secuencialmente hasta llenar capacidad o max_wos_por_tour
    for wo in candidatos_ordenados:
        # Verificar limites
        if len(tour_wos) >= self.max_wos_por_tour:
            print(f"[DISPATCHER] Tour alcanzó max_wos_por_tour: {self.max_wos_por_tour}")
            break
        
        wo_volume = wo.calcular_volumen_restante()
        
        # Intentar agregar si cabe
        if volume_acumulado + wo_volume <= operator.capacity:
            tour_wos.append(wo)
            volume_acumulado += wo_volume
            print(f"[DISPATCHER] + WO {wo.id} agregada (seq={wo.pick_sequence}, vol={wo_volume}L, total={volume_acumulado}L)")
        else:
            print(f"[DISPATCHER] x WO {wo.id} no cabe (seq={wo.pick_sequence}, vol={wo_volume}L, sobra={operator.capacity - volume_acumulado}L)")
            # NO break aqui - seguir probando WOs mas pequenas
    
    # Logging final
    utilizacion = (volume_acumulado / operator.capacity) * 100 if operator.capacity > 0 else 0
    print(f"[DISPATCHER] Tour construido: {len(tour_wos)} WOs, "
          f"volumen: {volume_acumulado}/{operator.capacity}L "
          f"(utilizacion: {utilizacion:.1f}%)")
    
    return tour_wos
```

#### Cambios Clave:
1. ✅ **Eliminada logica ciclica** que buscaba secuencias especificas
2. ✅ **Ordenamiento simple** por `pick_sequence`
3. ✅ **Agregado secuencial** hasta llenar capacidad
4. ✅ **Sin salida prematura** - prueba todas las WOs disponibles
5. ✅ **Logging detallado** para debugging

#### Impacto Esperado:
- Tours pasaran de **1.75 WOs** a **8-12 WOs**
- Utilizacion pasara de **38.9%** a **70-90%**
- Numero de tours se reducira de **12** a **2-3** (mas eficientes)

---

## FASE 2: CORRECCION DE DISCREPANCIA DE CAPACIDAD ⚠️ IMPORTANTE

### Archivo: `config.json`

#### Problema Actual:
```json
{
    "capacidad_carro": 150,  // Valor legacy no usado
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 500,  // VALOR INCORRECTO
            ...
        }
    ]
}
```

#### Solucion Opcion A (RECOMENDADA): Unificar en 150L
```json
{
    "capacidad_carro": 150,
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 150,  // CORREGIDO
            "discharge_time": 5,
            "work_area_priorities": {
                "Area_Ground": 1
            }
        },
        {
            "type": "Forklift",
            "capacity": 300,  // MANTENER
            "discharge_time": 5,
            "work_area_priorities": {
                "Area_High": 1,
                "Area_Special": 2
            }
        }
    ]
}
```

#### Solucion Opcion B: Eliminar `capacidad_carro` redundante
```json
{
    // Eliminar "capacidad_carro": 150,
    "agent_types": [
        {
            "type": "GroundOperator",
            "capacity": 150,  // UNICA FUENTE DE VERDAD
            ...
        }
    ]
}
```

#### Recomendacion:
**Usar Opcion A** para mantener compatibilidad con codigo legacy que pueda leer `capacidad_carro`.

---

## FASE 3: CONSIDERACION DE TOUR MIXTO (Multi-Destino) 🔄 OPCIONAL

### Contexto:
La configuracion actual usa `"tour_type": "Tour Mixto (Multi-Destino)"`, pero el codigo filtra WOs por `wo.work_area == primera_wo.work_area`, lo cual limita a una sola area.

### Pregunta para el Usuario:
**¿Que deberia hacer "Tour Mixto (Multi-Destino)"?**

#### Opcion A: Mixto significa multiples OUTBOUND STAGINGS
- Un tour puede incluir WOs con diferentes `staging_id`
- El operador visita multiples outbound stagings para descargar
- **Cambio de codigo:** Eliminar filtro de `work_area` en construccion de tour

```python
# En lugar de:
candidatos_misma_area = [wo for wo in candidatos 
                          if wo != primera_wo 
                          and wo.work_area == primera_wo.work_area]

# Usar:
candidatos_disponibles = [wo for wo in candidatos if wo != primera_wo]
# Ordenar por pick_sequence GLOBAL
candidatos_ordenados = sorted(candidatos_disponibles, 
                               key=lambda wo: wo.pick_sequence)
```

#### Opcion B: Mixto significa multiples WORK AREAS
- Un tour puede incluir WOs de diferentes `work_area` (Area_Ground + Area_Special)
- Pero todas descargan en el mismo `staging_id`
- **Cambio de codigo:** Filtrar por `staging_id` en lugar de `work_area`

```python
# Filtrar por staging_id comun
primera_staging = primera_wo.staging_id
candidatos_mismo_staging = [wo for wo in candidatos 
                             if wo != primera_wo 
                             and wo.staging_id == primera_staging]
```

#### Opcion C: Mixto = comportamiento actual (misma area)
- Tours se limitan a una sola `work_area`
- "Mixto" solo significa que el operador puede trabajar en diferentes areas en diferentes tours
- **Sin cambios de codigo**

### Recomendacion:
**Opcion A** - Permitir multiples outbound stagings para maximizar utilizacion.

---

## FASE 4: TESTING Y VALIDACION 🧪

### 4.1. Generar Nueva Simulacion
```bash
python entry_points/run_generate_replay.py
```

### 4.2. Analizar JSONL Resultante
```bash
python analyze_ground_operator_tours.py
```

### 4.3. Metricas Esperadas

| Metrica | ANTES | DESPUES (Esperado) |
|---------|-------|-------------------|
| WOs por tour (promedio) | 1.75 | 8-12 |
| Volumen por tour (promedio) | 58.33L | 105-135L |
| Utilizacion promedio | 38.9% | 70-90% |
| Total tours (GroundOp-01) | 12 | 2-3 |

### 4.4. Criterios de Exito
- ✅ Tours tienen **≥ 5 WOs** en promedio
- ✅ Utilizacion **≥ 70%** en promedio
- ✅ No hay errores en logs del dispatcher
- ✅ Tiempos de simulacion no aumentan significativamente

---

## FASE 5: DOCUMENTACION 📝

### 5.1. Actualizar HANDOFF.md
Agregar seccion:
```markdown
## BUGFIX 2025-10-27: Tours Cortos en Ground Operators

**Problema:** Ground Operators hacian tours muy cortos (1.75 WOs) con baja utilizacion (38.9%)

**Solucion:**
1. Simplificada logica de `_construir_tour_por_secuencia()` en `dispatcher.py`
2. Corregida discrepancia de capacidad en `config.json` (500L -> 150L)
3. Tours ahora promedian 8-12 WOs con 70-90% de utilizacion

**Archivos modificados:**
- `src/subsystems/simulation/dispatcher.py`
- `config.json`
```

### 5.2. Actualizar ACTIVE_SESSION_STATE.md
Marcar tarea como completada y documentar cambios.

### 5.3. Commit de Git
```bash
git add src/subsystems/simulation/dispatcher.py config.json
git commit -m "fix: Corregir logica de construccion de tours en dispatcher

- Simplificada logica de _construir_tour_por_secuencia() eliminando busqueda ciclica
- Tours ahora agregan WOs secuencialmente por pick_sequence hasta llenar capacidad
- Corregida capacidad de GroundOperator de 500L a 150L
- Utilizacion de tours aumenta de 38.9% a 70-90%
- Promedio de WOs por tour aumenta de 1.75 a 8-12

Issue: Tours cortos con baja utilizacion de capacidad"
```

---

## RIESGOS Y CONSIDERACIONES ⚠️

### Riesgo 1: Tiempos de Picking
- **Descripcion:** Tours mas largos pueden aumentar tiempo total de simulacion
- **Mitigacion:** Monitorear tiempos de ejecucion en testing
- **Severidad:** BAJA

### Riesgo 2: Compatibilidad con Estrategias
- **Descripcion:** Cambio puede afectar otras estrategias (Optimizacion Global, FIFO)
- **Mitigacion:** Probar todas las estrategias de despacho
- **Severidad:** MEDIA

### Riesgo 3: Violacion de Capacidad
- **Descripcion:** Si capacidad se corrige a 150L, algunos tours pueden exceder capacidad
- **Mitigacion:** Validacion estricta en loop de agregado de WOs
- **Severidad:** BAJA (ya implementada en codigo propuesto)

---

## CRONOGRAMA ESTIMADO ⏱️

| Fase | Duracion | Dependencias |
|------|----------|--------------|
| FASE 1: Correccion de logica | 30 min | - |
| FASE 2: Correccion de capacidad | 5 min | - |
| FASE 3: Tour Mixto (si aplica) | 15 min | Fase 1 |
| FASE 4: Testing | 20 min | Fases 1-3 |
| FASE 5: Documentacion | 10 min | Fase 4 |
| **TOTAL** | **80 min** | - |

---

## DECISION DEL USUARIO 🤔

**Antes de proceder, necesito tu aprobacion para:**

1. ✅ **FASE 1:** ¿Proceder con simplificacion de logica de construccion de tours?
2. ✅ **FASE 2:** ¿Corregir capacidad de 500L a 150L?
3. ❓ **FASE 3:** ¿Que debe hacer "Tour Mixto"? (Opcion A, B o C)

**Por favor confirma para proceder con la implementacion.**

---

**FIN DEL PLAN DE TRABAJO**

