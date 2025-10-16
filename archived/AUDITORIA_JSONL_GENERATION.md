# AUDITORIA: Generacion de Archivos .jsonl y Output

**Fecha:** 2025-10-07  
**Problema Reportado:** No se genera carpeta en `output/` con archivos `.jsonl` tras ejecutar simulacion  
**Estado:** AUDITORIA COMPLETADA - PROBLEMA IDENTIFICADO

---

## 1. ARQUITECTURA ACTUAL

### 1.1 Flujo Esperado de Generacion
```
[SimPy Simulation]
  └─> AlmacenMejorado.registrar_evento('work_order_update', datos)
      └─> event_log.append(evento)  // Solo almacena en event_log
  
[Operarios]
  └─> ??? NO HAY CAPTURA DE EVENTOS estado_agente ???

[SimulationEngine.ejecutar()]
  └─> Modo Visual/Headless
      └─> self.replay_buffer (ReplayBuffer instance)
      └─> volcar_replay_a_archivo(self.replay_buffer, output_file, ...)
```

### 1.2 Componentes Clave

**ReplayBuffer** (`src/shared/buffer.py`):
- Clase que almacena eventos de replay
- Metodos: `add_event()`, `get_events()`, `clear()`, `__len__()`
- Usado en: `SimulationEngine.__init__()`

**volcar_replay_a_archivo** (`src/core/replay_utils.py`):
- Funcion que escribe el buffer a archivo `.jsonl`
- Ubicacion: `output/simulation_{timestamp}/replay_{timestamp}.jsonl`
- Se ejecuta en: `SimulationEngine.ejecutar()` linea 1380-1385

**registrar_evento** (`src/subsystems/simulation/warehouse.py:368`):
- Metodo que captura eventos de simulacion
- PROBLEMA: Solo escribe a `self.event_log` (para analytics)
- NO CONECTADO a `replay_buffer`

---

## 2. PROBLEMA IDENTIFICADO

### 2.1 Diagnostico Principal

**PROBLEMA CRITICO:** `AlmacenMejorado.registrar_evento()` NO está conectado al `replay_buffer`

```python
# ESTADO ACTUAL (warehouse.py:368-381)
def registrar_evento(self, tipo: str, datos: Dict[str, Any]):
    evento = {
        'timestamp': self.env.now,
        'tipo': tipo,
        **datos
    }
    self.event_log.append(evento)  # SOLO VA A EVENT_LOG
    # FALTA: self.replay_buffer.add_event(evento) 
```

### 2.2 Impacto del Problema

1. **work_order_update events**: Se capturan en `event_log` pero NO en `replay_buffer`
2. **estado_agente events**: NO se capturan en NINGUN lado
3. **replay_buffer**: Se crea pero permanece VACIO
4. **volcar_replay_a_archivo()**: Se ejecuta pero con buffer vacio
5. **Archivo .jsonl**: Se crea pero solo tiene SIMULATION_START y SIMULATION_END (sin eventos)

---

## 3. EVENTOS QUE DEBEN CAPTURARSE

### 3.1 Eventos work_order_update
**Origen:** `src/subsystems/simulation/dispatcher.py:492`
```python
self.almacen.registrar_evento('work_order_update', {
    'id': wo.id,
    'order_id': wo.order_id,
    'status': 'staged',
    ...
})
```
**Estado:** Se captura en event_log, FALTA en replay_buffer

### 3.2 Eventos estado_agente
**Origen:** Operarios (GroundOperator, Forklift)
```python
# DEBERIA HABER:
self.almacen.registrar_evento('estado_agente', {
    'agent_id': self.id,
    'tipo': self.type,
    'position': self.current_position,
    'status': self.status,
    ...
})
```
**Estado:** NO SE CAPTURA en ningun lado

---

## 4. ARQUITECTURA MODO HEADLESS vs VISUAL

### 4.1 Modo Visual (Productor-Consumidor)
```
[Proceso SimPy Productor]
  └─> visual_event_queue.put({'type': 'estado_agente', ...})
      └─> [Proceso Consumidor Visual]
          └─> self.event_buffer.append(mensaje)
          └─> ??? NO SE COPIA A replay_buffer ???
```

### 4.2 Modo Headless
```
[SimPy en proceso principal]
  └─> AlmacenMejorado.registrar_evento()
      └─> self.event_log.append(evento)
      └─> ??? NO VA A replay_buffer ???
```

**PROBLEMA:** En AMBOS modos el replay_buffer NO se llena

---

## 5. ARCHIVOS QUE SE GENERAN CORRECTAMENTE

Revisando carpetas existentes en `output/simulation_20250928_003114/`:
```
✅ raw_events_20250928_003114.json          // event_log del almacen
✅ simulacion_completada_20250928_003114.json  // metricas basicas
✅ simulation_report_20250928_003114.xlsx   // analytics engine
✅ warehouse_heatmap_20250928_003114.png    // heatmap
✅ replay_20250928_003114.jsonl             // ESTE EXISTE!
```

**NOTA IMPORTANTE:** El archivo `.jsonl` SI se crea, pero puede estar VACIO o con pocos eventos

---

## 6. PLAN DE REPARACION

### FASE 1: Conectar registrar_evento() con replay_buffer
**Archivo:** `src/subsystems/simulation/warehouse.py`
**Cambio:** Pasar replay_buffer al AlmacenMejorado y escribir eventos

### FASE 2: Agregar captura de eventos estado_agente
**Archivos:** 
- `src/subsystems/simulation/operators.py` (GroundOperator, Forklift)
**Cambio:** Llamar registrar_evento('estado_agente') en puntos clave

### FASE 3: Sincronizar modo Productor-Consumidor
**Archivo:** `src/engines/simulation_engine.py`
**Cambio:** Copiar eventos de visual_event_queue a replay_buffer

### FASE 4: Validar escritura de archivo
**Verificar:** volcar_replay_a_archivo() escribe correctamente eventos

### FASE 5: Testing completo
**Comando:** 
```bash
python entry_points/run_live_simulation.py --headless
```
**Validar:** 
- Se crea carpeta `output/simulation_YYYYMMDD_HHMMSS/`
- Archivo `replay_YYYYMMDD_HHMMSS.jsonl` tiene eventos
- Replay viewer puede cargar el archivo

---

## 7. DIAGNOSTICO DETALLADO POR COMPONENTE

### 7.1 ReplayBuffer (src/shared/buffer.py)
**Estado:** ✅ CORRECTO - Implementacion completa
**Problema:** NO - La clase funciona bien

### 7.2 AlmacenMejorado.__init__() (src/subsystems/simulation/warehouse.py:81)
**Estado:** ❌ FALTA replay_buffer
**Linea 109:** Recibe `visual_event_queue` pero NO `replay_buffer`
**Problema:** No tiene referencia al replay_buffer del simulador

### 7.3 AlmacenMejorado.registrar_evento() (warehouse.py:368)
**Estado:** ⚠️ INCOMPLETO
**Problema:** Solo escribe a event_log, no a replay_buffer

### 7.4 DispatcherV11.notificar_completado() (dispatcher.py:492)
**Estado:** ✅ CORRECTO - Llama registrar_evento
**Problema:** NO - El dispatcher hace su parte

### 7.5 Operarios (operators.py)
**Estado:** ❌ NO CAPTURA estado_agente
**Problema:** No llama registrar_evento para posiciones

### 7.6 SimulationEngine.ejecutar() (simulation_engine.py:1380)
**Estado:** ✅ CORRECTO - Llama volcar_replay_a_archivo
**Problema:** NO - La escritura se intenta

### 7.7 volcar_replay_a_archivo() (replay_utils.py:15)
**Estado:** ✅ CORRECTO - Implementacion completa
**Problema:** NO - Funciona bien con buffer poblado

---

## 8. ROOT CAUSE ANALYSIS

**CAUSA RAIZ:** Desconexion arquitectonica entre:
1. Sistema de eventos del Almacen (`event_log`)
2. Sistema de replay (`replay_buffer`)

**DECISION DE DISENO ORIGINAL:**
- `event_log`: Para analytics (AnalyticsEngine)
- `replay_buffer`: Para replay viewer

**PROBLEMA:** Los dos sistemas NO se comunicaron

---

## 9. SOLUCION PROPUESTA

### Opcion A: Unificar en registrar_evento() [RECOMENDADA]
```python
def registrar_evento(self, tipo: str, datos: Dict[str, Any]):
    evento = {
        'timestamp': self.env.now,
        'tipo': tipo,
        **datos
    }
    self.event_log.append(evento)
    
    # NUEVO: Tambien agregar a replay_buffer si esta disponible
    if self.replay_buffer:
        self.replay_buffer.add_event(evento)
```

**Ventajas:**
- Cambio minimo
- Un solo punto de captura
- Funciona para ambos modos

### Opcion B: Captura separada
- Mantener event_log para analytics
- Crear sistema separado para replay
**Desventajas:**
- Mas complejidad
- Duplicacion de logica

---

## 10. PROXIMOS PASOS

1. ✅ **COMPLETADO:** Auditar arquitectura completa
2. ⏳ **SIGUIENTE:** Implementar FASE 1 - Conectar replay_buffer
3. ⏳ **PENDIENTE:** Implementar FASE 2 - Eventos estado_agente
4. ⏳ **PENDIENTE:** Implementar FASE 3 - Sincronizar Productor-Consumidor
5. ⏳ **PENDIENTE:** Testing completo end-to-end

---

## 11. PREGUNTAS PARA EL USUARIO

1. ¿Confirma que actualmente NO se genera el archivo .jsonl?
2. ¿O se genera pero esta vacio/incompleto?
3. ¿Necesita capturar posiciones de agentes en tiempo real?
4. ¿Prefiere modo headless o visual para testing?

---

**FIN DE AUDITORIA**

