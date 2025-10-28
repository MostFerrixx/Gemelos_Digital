# AUDITORIA: Problemas con KPIs del Dashboard

**Fecha:** 2025-10-27  
**Estado:** Pendiente de Correccion

---

## PROBLEMAS IDENTIFICADOS

### 1. WIP nunca disminuye (58/58 siempre)

**Sintoma:** El KPI de WIP muestra siempre "58/58" y nunca cambia.

**Causa Raiz:**
En `_calcular_metricas_modern_dashboard()` (lineas 786-796 de `replay_engine.py`), el codigo busca work orders completadas en `estado_visual["work_orders"]`, pero **este diccionario NUNCA se actualiza** durante el replay.

- Linea 514-520: Los eventos `work_order_update` se envían al dashboard_communicator pero **NO se actualizan en estado_visual["work_orders"]**
- `estado_visual["work_orders"]` solo se inicializa al inicio (linea 294)
- Las actualizaciones de estado van solo a `self.dashboard_wos_state` (linea 520)

**Codigo Problematico:**
```python
# Lineas 513-520
if event_type == 'work_order_update':
    wo_id = evento.get('id')
    if not wo_id:
        continue
    
    # Update internal state cache
    self.dashboard_wos_state[wo_id] = evento.copy()  # <- Solo actualiza dashboard_wos_state
    
    # Forward to dashboard
    if not silent and self.dashboard_communicator:
        self.dashboard_communicator._send_message_with_retry(evento, max_retries=1, timeout=0.1)
        
    # FALTA: NO se actualiza estado_visual["work_orders"][wo_id]
```

**Solucion:**
Agregar actualizacion de `estado_visual["work_orders"]` en el procesamiento de eventos:

```python
if event_type == 'work_order_update':
    wo_id = evento.get('id')
    if not wo_id:
        continue
    
    # Update internal state cache
    self.dashboard_wos_state[wo_id] = evento.copy()
    
    # CRITICAL FIX: Actualizar estado_visual para que las metricas funcionen
    if wo_id not in estado_visual["work_orders"]:
        estado_visual["work_orders"][wo_id] = {}
    estado_visual["work_orders"][wo_id].update(evento)
    
    # Forward to dashboard
    if not silent and self.dashboard_communicator:
        self.dashboard_communicator._send_message_with_retry(evento, max_retries=1, timeout=0.1)
```

---

### 2. Util vuelve a 0 inmediatamente

**Sintoma:** El KPI de Utilizacion aumenta momentaneamente cuando los operarios comienzan a trabajar, pero luego inmediatamente vuelve a 0.

**Causa Raiz:**
En `_calcular_metricas_tiempo()` de `state.py` (lineas 380-424), se calcula la utilizacion contando operarios en estados 'working' o 'traveling'. Sin embargo, los estados de operarios en el replay pueden tener nombres diferentes o no sincronizarse correctamente.

**Posibles Causas:**
1. Los eventos `estado_agente` pueden tener nombres de status diferentes
2. `actualizar_metricas_tiempo()` se llama en linea 471, pero puede que los estados no sean correctos
3. El estado 'idle' puede estar sobrescribiendo los estados activos

**Codigo de Referencia:**
```python
# state.py lineas 400-424
def actualizar_metricas_tiempo(operarios_dict):
    idle_count = 0
    working_count = 0
    traveling_count = 0
    
    for operario in operarios_dict.values():
        status = operario.get('status', 'idle')
        
        if status in ['idle', 'Esperando tour']:
            idle_count += 1
        elif status in ['working', 'Trabajando']:
            working_count += 1
        elif status in ['traveling', 'moving', 'Moviendose']:
            traveling_count += 1
    
    total_operarios = len(operarios_dict)
    if total_operarios > 0:
        utilizacion = ((working_count + traveling_count) / total_operarios) * 100.0
    else:
        utilizacion = 0.0
    
    estado_visual["metricas"]["utilizacion_promedio"] = utilizacion
```

**Solucion:**
Agregar debug para verificar que estados reales se estan usando y ajustar la logica de conteo:

```python
# Agregar en _process_event_batch despues de actualizar estado_agente
# Debug para verificacion
if event_type == 'estado_agente':
    agent_id = evento.get('agent_id')
    data = evento.get('data', {})
    
    if agent_id:
        # ... codigo existente ...
        
        # NUEVO: Debug de utilizacion
        if 'status' in data:
            status = data['status']
            print(f"[DEBUG-UTIL] {agent_id} ahora es: {status}")
```

---

### 3. T/put siempre vacio

**Sintoma:** El KPI de Throughput siempre muestra "-" (vacio).

**Causa Raiz:**
En `_calcular_throughput_min()` (lineas 802-811), el calculo depende de:
1. `self.playback_time` (tiempo de simulacion)
2. `workorders_completadas` (que depende del problema #1)

Si `workorders_completadas` siempre es 0 porque `estado_visual["work_orders"]` no se actualiza (Problema #1), entonces throughput siempre sera 0, y el dashboard mostrara "-" porque es 0.

**Codigo:**
```python
def _calcular_throughput_min(self, estado_visual):
    if "metricas" not in estado_visual:
        estado_visual["metricas"] = {}
    tiempo = self.playback_time
    completadas = estado_visual["metricas"].get("workorders_completadas", 0)
    if tiempo > 0:
        estado_visual["metricas"]["throughput_min"] = (completadas / max(tiempo, 1e-6)) * 60.0
    else:
        estado_visual["metricas"]["throughput_min"] = 0.0
```

**Solucion:**
Una vez que se corrija el Problema #1, el throughput deberia calcularse correctamente. Sin embargo, hay un problema adicional: el throughput deberia calcularse como WOs completadas desde el inicio hasta ahora, no como un promedio instantaneo.

**Mejora sugerida:**
```python
def _calcular_throughput_min(self, estado_visual):
    if "metricas" not in estado_visual:
        estado_visual["metricas"] = {}
    
    tiempo = self.playback_time
    completadas = estado_visual["metricas"].get("workorders_completadas", 0)
    
    # Calcular throughput: WOs por minuto
    if tiempo > 0:
        throughput = (completadas / tiempo) * 60.0
    else:
        throughput = 0.0
    
    estado_visual["metricas"]["throughput_min"] = throughput
    
    # DEBUG: Imprimir cada segundo para verificar
    if int(tiempo) % 1 == 0 and int(tiempo) > 0:
        print(f"[DEBUG-THROUGHPUT] T={tiempo:.1f}s, WO={completadas}, T/put={throughput:.2f} WO/min")
```

---

## RESUMEN DE CORRECCIONES NECESARIAS

### 1. Actualizar estado_visual["work_orders"] en procesamiento de eventos
**Archivo:** `src/engines/replay_engine.py`  
**Linea:** ~520  
**Cambio:** Agregar actualizacion de `estado_visual["work_orders"]` al procesar eventos `work_order_update`

### 2. Agregar debug para Utilizacion
**Archivo:** `src/engines/replay_engine.py`  
**Linea:** ~562  
**Cambio:** Agregar logging para verificar estados reales de operarios

### 3. Mejorar calculo de Throughput
**Archivo:** `src/engines/replay_engine.py`  
**Linea:** ~802  
**Cambio:** Agregar debug y verificar que se calcula correctamente

---

## ORDEN DE IMPLEMENTACION

1. **Primero:** Corregir Problema #1 (actualizar estado_visual["work_orders"])
   - Esto deberia resolver tanto WIP como T/put

2. **Segundo:** Investigar Problema #2 (Utilizacion)
   - Agregar debug para entender que estados se estan enviando
   - Ajustar logica de conteo en `state.py`

3. **Tercero:** Validar que T/put funciona despues de la correccion #1
   - Agregar debug si es necesario

---

## PRUEBAS A REALIZAR

Despues de las correcciones, verificar:

1. **WIP:** Debe disminuir progresivamente (ej: 58/58 -> 45/58 -> 20/58 -> 0/58)
2. **Util:** Debe mantenerse en valores > 0% cuando los operarios estan activos
3. **T/put:** Debe mostrar un valor numerico (ej: "2.5/min") mientras avanza la simulacion
