# 🔴 PROBLEMA CRÍTICO: OPERARIOS NO SE MUEVEN EN REPLAY

**Fecha:** 2025-10-12  
**Estado:** ❌ BUG CRÍTICO ENCONTRADO  
**Severidad:** 🔴 ALTA - Funcionalidad básica no funciona

---

## 🔍 DESCRIPCIÓN DEL PROBLEMA

Con `USE_EVENT_SOURCING=true`, los operarios **NO SE MUEVEN** en el layout visual de Pygame durante el replay. El dashboard PyQt6 podría funcionar, pero la visualización principal (la ventana de Pygame con el mapa) NO muestra el movimiento de los agentes.

---

## 📊 EVIDENCIA

### **Logs del Usuario:**
```
[METRICAS] WO: 0/56, Tareas: 0, Tiempo: 0.2s
[METRICAS] WO: 0/56, Tareas: 0, Tiempo: 0.3s
[METRICAS] WO: 0/56, Tareas: 0, Tiempo: 0.4s
...
```

**Problema:** NO aparecen logs `[DEBUG-AGENT] Updated position for ...`

### **Contenido del Archivo .jsonl:**
El archivo SÍ contiene eventos `estado_agente`:
```json
{"type": "estado_agente", "timestamp": 0, "agent_id": "GroundOp-01", "data": {"position": [3, 29], ...}}
{"type": "estado_agente", "timestamp": 0.1, "agent_id": "GroundOp-01", "data": {"position": [5, 28], ...}}
{"type": "estado_agente", "timestamp": 0.2, "agent_id": "GroundOp-01", "data": {"position": [6, 27], ...}}
```

**Conclusión:** Los eventos existen, pero NO se procesan.

---

## 🐛 CAUSA RAÍZ

### **Análisis del Código:**

En `src/engines/replay_engine.py`, método `_process_event_batch()`:

```python
def _process_event_batch(self, eventos_a_procesar):
    """Process batch of events and emit granular typed events."""
    for event_index, evento in eventos_a_procesar:
        event_type = evento.get('type')
        
        # ===== WorkOrder Events ===== ✅
        if event_type == 'work_order_update':
            # ... código que SÍ procesa work_order_update
            self._emit_event(WorkOrderStatusChangedEvent(...))
        
        # ===== Agent Events ===== ❌ FALTA!
        # NO HAY CÓDIGO PARA PROCESAR 'estado_agente'
        # elif event_type == 'estado_agente':
        #     # FALTA IMPLEMENTAR
```

**Problema:** Jules implementó el procesamiento de eventos `work_order_update` pero **OLVIDÓ** implementar el procesamiento de eventos `estado_agente`.

---

## 🎯 IMPACTO

### **Funcionalidades Afectadas:**

1. ❌ **Visualización de operarios en Pygame** - No se mueven
2. ❌ **Logs de debug de agentes** - No aparecen
3. ⚠️ **Dashboard PyQt6** - Podría funcionar (no validado)
4. ⚠️ **Work Orders** - Podrían actualizarse (no validado)

### **Funcionalidades NO Afectadas:**

1. ✅ **Carga del archivo .jsonl** - Funciona
2. ✅ **Renderizado del mapa** - Funciona
3. ✅ **Dashboard World-Class lateral** - Funciona (muestra métricas)

---

## 🔧 SOLUCIÓN REQUERIDA

### **Opción 1: Procesar eventos de agentes en modo Event Sourcing** ⭐ RECOMENDADO

Modificar `_process_event_batch()` en `src/engines/replay_engine.py`:

```python
def _process_event_batch(self, eventos_a_procesar):
    """Process batch of events and emit granular typed events."""
    for event_index, evento in eventos_a_procesar:
        self.processed_event_indices.add(event_index)
        event_type = evento.get('type')
        timestamp = evento.get('timestamp', 0.0)
        
        # ===== WorkOrder Events ===== ✅ YA EXISTE
        if event_type == 'work_order_update':
            # ... código existente ...
            self._emit_event(WorkOrderStatusChangedEvent(...))
        
        # ===== Agent Events ===== ⭐ AGREGAR ESTO
        elif event_type == 'estado_agente':
            agent_id = evento.get('agent_id')
            data = evento.get('data', {})
            
            if agent_id and 'position' in data:
                # Actualizar estado visual (Pygame)
                if agent_id not in estado_visual["operarios"]:
                    estado_visual["operarios"][agent_id] = {}
                
                estado_visual["operarios"][agent_id].update(data)
                
                # Log de debug
                position = data.get('position', [0, 0])
                print(f"[DEBUG-AGENT] Updated position for {agent_id}: {position}")
                
                # Opcional: Emitir evento para Dashboard PyQt6
                # self._emit_event(OperatorPositionUpdatedEvent(...))
        
        # Update internal state
        if event_type == 'work_order_update':
            wo_id = evento.get('id')
            if wo_id:
                self.dashboard_wos_state[wo_id] = evento.copy()
```

**Beneficios:**
- ✅ Operarios se mueven en Pygame
- ✅ Logs de debug aparecen
- ✅ Compatible con Event Sourcing
- ✅ Mínimo cambio de código

---

### **Opción 2: Desactivar Event Sourcing por defecto**

```python
# En src/engines/replay_engine.py
USE_EVENT_SOURCING = os.getenv('USE_EVENT_SOURCING', 'false').lower() == 'true'
```

**Problema:** Ya está así, solo funciona si se activa explícitamente.

**Conclusión:** El código legacy (sin Event Sourcing) SÍ funciona correctamente.

---

## 🧪 VALIDACIÓN NECESARIA

### **Test 1: Verificar con Event Sourcing desactivado**

```powershell
# NO setear USE_EVENT_SOURCING (usa legacy mode)
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

**Resultado esperado:**
- ✅ Operarios SE MUEVEN
- ✅ Logs `[DEBUG-AGENT]` aparecen

### **Test 2: Verificar con Event Sourcing activado (después del fix)**

```powershell
$env:USE_EVENT_SOURCING='true'
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

**Resultado esperado:**
- ✅ Operarios SE MUEVEN
- ✅ Logs `[DEBUG-AGENT]` aparecen
- ✅ Dashboard PyQt6 funciona
- ✅ Work Orders se actualizan

---

## 📋 CHECKLIST DE CORRECCIÓN

Para Jules o para implementar nosotros:

- [ ] Modificar `_process_event_batch()` en `src/engines/replay_engine.py`
- [ ] Agregar bloque `elif event_type == 'estado_agente':`
- [ ] Actualizar `estado_visual["operarios"]` con datos del evento
- [ ] Agregar log `[DEBUG-AGENT] Updated position for ...`
- [ ] Ejecutar test con `USE_EVENT_SOURCING=true`
- [ ] Verificar que operarios se mueven visualmente
- [ ] Verificar que logs aparecen en consola
- [ ] Validar que dashboard PyQt6 funciona (presionar 'O')
- [ ] Validar que Work Orders se actualizan en dashboard

---

## 🤔 ANÁLISIS: ¿POR QUÉ JULES NO LO IMPLEMENTÓ?

### **Hipótesis:**

1. **Enfoque en Dashboard PyQt6:** Jules se enfocó en implementar el Event Consumer del dashboard PyQt6, no en la visualización de Pygame.

2. **Falta de especificación:** En mi prompt técnico, NO especifiqué explícitamente que los eventos `estado_agente` deben procesarse para Pygame.

3. **Arquitectura separada:** Jules podría haber asumido que:
   - Event Sourcing → Dashboard PyQt6 (eventos)
   - Legacy mode → Visualización Pygame (estado directo)

4. **Testing incompleto:** Jules no ejecutó el replay visual para verificar que los operarios se mueven.

---

## 📊 COMPARACIÓN: Legacy vs Event Sourcing

| Aspecto | Legacy Mode | Event Sourcing (Actual) | Event Sourcing (Esperado) |
|---------|------------|------------------------|--------------------------|
| **Operarios en Pygame** | ✅ Se mueven | ❌ NO se mueven | ✅ Deberían moverse |
| **Work Orders en Pygame** | ✅ Actualizan | ⚠️ No validado | ✅ Deberían actualizar |
| **Dashboard PyQt6** | ✅ Funciona | ⚠️ Debería funcionar | ✅ Debería funcionar |
| **Logs de agentes** | ✅ Aparecen | ❌ NO aparecen | ✅ Deberían aparecer |

---

## 🎯 DECISIÓN REQUERIDA

### **Opción A: Corregir Event Sourcing ahora** ⭐ RECOMENDADO

- **Tiempo:** 15-30 minutos
- **Complejidad:** Baja
- **Beneficio:** Event Sourcing 100% funcional

### **Opción B: Usar Legacy Mode temporalmente**

- **Tiempo:** Inmediato
- **Complejidad:** Ninguna
- **Beneficio:** Sistema funciona, pero sin Event Sourcing

### **Opción C: Pedir a Jules que lo corrija**

- **Tiempo:** Variable
- **Complejidad:** Depende de Jules
- **Beneficio:** Jules aprende del error

---

## 💡 RECOMENDACIÓN FINAL

**IMPLEMENTAR OPCIÓN A INMEDIATAMENTE:**

1. Es un cambio simple (10-15 líneas de código)
2. Completa la implementación de Event Sourcing
3. Permite validar todo el sistema end-to-end
4. No requiere esperar a Jules

**Código exacto a agregar:**

```python
# En _process_event_batch(), después del bloque de work_order_update:

elif event_type == 'estado_agente':
    agent_id = evento.get('agent_id')
    data = evento.get('data', {})
    
    if agent_id and 'position' in data:
        # Update visual state for Pygame rendering
        if agent_id not in estado_visual["operarios"]:
            estado_visual["operarios"][agent_id] = {}
        
        estado_visual["operarios"][agent_id].update(data)
        
        # Debug log
        position = data.get('position', [0, 0])
        print(f"[DEBUG-AGENT] Updated position for {agent_id}: {position}")
```

---

**¿Implemento la corrección ahora o prefieres otra opción?** 🤔

