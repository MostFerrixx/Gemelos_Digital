# PROMPT TÉCNICO PARA JULES - COMPLETAR IMPLEMENTACIÓN EVENT SOURCING

## CONTEXTO ACTUAL

Tu implementación de Event Sourcing en la rama `feature/event-sourcing-impl-1` está **estructuralmente correcta** pero **funcionalmente incompleta**. Completaste aproximadamente el 42% del trabajo. El código que implementaste funciona perfectamente, pero falta la parte crítica del **Event Consumer** en el Dashboard PyQt6.

---

## ESTADO ACTUAL DE LA IMPLEMENTACIÓN

### ✅ LO QUE YA ESTÁ IMPLEMENTADO (POR TI):

1. **`src/communication/ipc_protocols.py`** ✅ COMPLETO
   - EventType enum con 15+ tipos de eventos
   - Dataclasses: BaseEvent, StateResetEvent, StateSnapshotEvent, WorkOrderStatusChangedEvent, WorkOrderAssignedEvent, WorkOrderProgressUpdatedEvent
   - Serialización inmutable con frozen=True
   - Event IDs con UUID
   - Versionado incluido

2. **`src/communication/dashboard_communicator.py`** ✅ COMPLETO
   - Feature flag USE_EVENT_SOURCING funcional
   - Método `send_event(event: BaseEvent)` implementado
   - Método `_serialize_event(event: BaseEvent)` funcional
   - Metadata incluida (sent_timestamp)
   - Integración con ProcessLifecycleManager

3. **`src/communication/lifecycle_manager.py`** ✅ COMPLETO
   - ProcessLifecycleManager con gestión robusta
   - DashboardConfig con timeouts
   - Manejo de excepciones correcto

4. **`src/engines/replay_engine.py`** ⚠️ 90% COMPLETO
   - Método `_emit_event(event: BaseEvent)` implementado
   - Método `seek_to_time(target_time)` emite STATE_RESET y STATE_SNAPSHOT
   - Método `_compute_snapshot_from_events(events)` implementado
   - Método `_send_initial_state_snapshot()` implementado

5. **Documentación** ✅ EXCEPCIONAL
   - AUDITORIA_ARQUITECTURA_DASHBOARD_PYQT6.md (1008 líneas)
   - RESUMEN_EJECUTIVO_AUDITORIA_DASHBOARD.md (285 líneas)

---

### ❌ LO QUE FALTA IMPLEMENTAR (TU TAREA):

**CRÍTICO:** El Dashboard PyQt6 NO puede consumir eventos de Event Sourcing. Necesitas implementar el **Event Consumer Pattern** completo.

---

## TAREA ESPECÍFICA: IMPLEMENTAR EVENT CONSUMER EN DASHBOARD

### ARCHIVO A MODIFICAR:

**`src/subsystems/visualization/work_order_dashboard.py`**

Este archivo actualmente NO tiene soporte para Event Sourcing. Necesitas:

1. Agregar estado local para reconstrucción desde eventos
2. Implementar handlers para cada tipo de evento
3. Implementar protocolo de STATE_RESET + STATE_SNAPSHOT
4. Actualizar UI con eventos granulares

---

## IMPLEMENTACIÓN REQUERIDA (CÓDIGO EXACTO)

### PASO 1: Agregar Estado Local al Dashboard

En `WorkOrderDashboard.__init__()`, agregar:

```python
class WorkOrderDashboard(QMainWindow):
    def __init__(self, queue_from_sim=None, queue_to_sim=None):
        super().__init__()
        
        # ... código existente ...
        
        # ===== NUEVO: Event Sourcing State Management =====
        # Local state rebuilt from events (Event Sourcing pattern)
        self._local_wo_state: Dict[str, Dict[str, Any]] = {}
        self._local_operator_state: Dict[str, Dict[str, Any]] = {}
        self._local_metrics: Dict[str, Any] = {}
        
        # Event processing state
        self._is_rebuilding_state: bool = False
        self._last_snapshot_time: float = 0.0
        
        # Feature flag check
        self._use_event_sourcing = os.getenv('USE_EVENT_SOURCING', 'false').lower() == 'true'
        
        if self._use_event_sourcing:
            print("[DASHBOARD] Initialized in EVENT SOURCING mode")
        else:
            print("[DASHBOARD] Initialized in LEGACY mode")
        # ===== END NUEVO =====
```

---

### PASO 2: Modificar `handle_message()` para Event Sourcing

Reemplazar el método `handle_message()` existente con:

```python
def handle_message(self, message: Dict[str, Any]):
    """
    Handle incoming messages from simulation.
    Supports both legacy mode and Event Sourcing mode.
    """
    if not message:
        return
    
    message_type = message.get("type")
    
    # ===== Event Sourcing Mode =====
    if self._use_event_sourcing:
        self._handle_event_sourcing_message(message_type, message)
        return
    
    # ===== Legacy Mode =====
    self._handle_legacy_message(message_type, message)

def _handle_legacy_message(self, message_type: str, message: Dict[str, Any]):
    """Handle messages in legacy mode (existing behavior)."""
    # TODO: Mover aquí todo el código existente de handle_message()
    # Este método mantiene la funcionalidad actual sin cambios
    pass

def _handle_event_sourcing_message(self, message_type: str, message: Dict[str, Any]):
    """
    Handle messages in Event Sourcing mode.
    Routes events to specific handlers.
    """
    # State Management Events
    if message_type == "state_reset":
        self._handle_state_reset(message)
    
    elif message_type == "state_snapshot":
        self._handle_state_snapshot(message)
    
    # WorkOrder Events (Granular)
    elif message_type == "wo_status_changed":
        self._handle_wo_status_changed(message)
    
    elif message_type == "wo_assigned":
        self._handle_wo_assigned(message)
    
    elif message_type == "wo_progress_updated":
        self._handle_wo_progress_updated(message)
    
    elif message_type == "wo_completed":
        self._handle_wo_completed(message)
    
    # Time Events
    elif message_type == "time_tick":
        self._handle_time_tick(message)
    
    elif message_type == "time_seek":
        self._handle_time_seek(message)
    
    # Metrics Events
    elif message_type == "metrics_updated":
        self._handle_metrics_updated(message)
    
    else:
        print(f"[DASHBOARD-WARNING] Unknown event type: {message_type}")
```

---

### PASO 3: Implementar Handler de STATE_RESET (CRÍTICO)

```python
def _handle_state_reset(self, message: Dict[str, Any]):
    """
    Handle STATE_RESET event - Clear all local state.
    This is the first step in the scrubber time-seek protocol.
    
    Protocol: SEEK_TIME -> STATE_RESET -> STATE_SNAPSHOT -> SEEK_COMPLETE
    """
    reason = message.get('data', {}).get('reason', 'unknown')
    target_time = message.get('data', {}).get('target_time', 0.0)
    
    print(f"[DASHBOARD] STATE RESET received - reason: {reason}, target_time: {target_time:.2f}s")
    
    # Set rebuilding flag to block incremental updates
    self._is_rebuilding_state = True
    
    # Clear all local state
    self._local_wo_state.clear()
    self._local_operator_state.clear()
    self._local_metrics.clear()
    
    # Clear UI table
    self.model.beginResetModel()
    self.model._data.clear()
    self.model.endResetModel()
    
    # Update status bar
    self.statusBar().showMessage(f"Rebuilding state at time {target_time:.2f}s...")
    
    print(f"[DASHBOARD] State cleared, awaiting STATE_SNAPSHOT...")
```

---

### PASO 4: Implementar Handler de STATE_SNAPSHOT (CRÍTICO)

```python
def _handle_state_snapshot(self, message: Dict[str, Any]):
    """
    Handle STATE_SNAPSHOT event - Rebuild complete state from snapshot.
    This is the second step in the scrubber time-seek protocol.
    
    Protocol: SEEK_TIME -> STATE_RESET -> STATE_SNAPSHOT -> SEEK_COMPLETE
    """
    timestamp = message.get('timestamp', 0.0)
    data = message.get('data', {})
    
    work_orders = data.get('work_orders', [])
    operators = data.get('operators', [])
    metrics = data.get('metrics', {})
    
    print(f"[DASHBOARD] STATE SNAPSHOT received at time {timestamp:.2f}s")
    print(f"[DASHBOARD]   - WorkOrders: {len(work_orders)}")
    print(f"[DASHBOARD]   - Operators: {len(operators)}")
    print(f"[DASHBOARD]   - Metrics keys: {list(metrics.keys())}")
    
    # Rebuild local state from snapshot
    for wo in work_orders:
        wo_id = wo.get('id')
        if wo_id:
            self._local_wo_state[wo_id] = wo
    
    for op in operators:
        op_id = op.get('id')
        if op_id:
            self._local_operator_state[op_id] = op
    
    self._local_metrics = metrics
    self._last_snapshot_time = timestamp
    
    # Update UI table (batch update)
    self.model.beginResetModel()
    self.model._data = list(self._local_wo_state.values())
    self.model.endResetModel()
    
    # Update time slider if exists
    if hasattr(self, 'time_slider') and self.time_slider:
        self.time_slider.setValue(int(timestamp))
    
    # Clear rebuilding flag
    self._is_rebuilding_state = False
    
    # Update status bar
    completed_wos = sum(1 for wo in work_orders if wo.get('status') == 'completed')
    total_wos = len(work_orders)
    self.statusBar().showMessage(
        f"State rebuilt: {completed_wos}/{total_wos} WOs completed at t={timestamp:.1f}s"
    )
    
    print(f"[DASHBOARD] State rebuilt successfully: {len(work_orders)} WorkOrders")
    
    # Send SEEK_COMPLETE confirmation back to engine
    if self.queue_to_sim:
        self.queue_to_sim.put({
            'type': 'SEEK_COMPLETE',
            'timestamp': timestamp
        })
        print(f"[DASHBOARD] SEEK_COMPLETE confirmation sent")
```

---

### PASO 5: Implementar Handlers de Eventos Granulares de WorkOrder

```python
def _handle_wo_status_changed(self, message: Dict[str, Any]):
    """
    Handle WorkOrder status change event (granular update).
    Only updates the specific status field.
    """
    if self._is_rebuilding_state:
        return  # Skip during state rebuild
    
    data = message.get('data', {})
    wo_id = data.get('wo_id')
    old_status = data.get('old_status')
    new_status = data.get('new_status')
    
    if wo_id and wo_id in self._local_wo_state:
        # Update local state
        self._local_wo_state[wo_id]['status'] = new_status
        
        # Find row in table
        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            # Emit dataChanged signal for status column only
            status_column = self._get_column_index('status')
            if status_column >= 0:
                index = self.model.index(row, status_column)
                self.model.dataChanged.emit(index, index)
        
        print(f"[DASHBOARD] WO {wo_id} status: {old_status} -> {new_status}")

def _handle_wo_assigned(self, message: Dict[str, Any]):
    """
    Handle WorkOrder assignment event (granular update).
    """
    if self._is_rebuilding_state:
        return
    
    data = message.get('data', {})
    wo_id = data.get('wo_id')
    agent_id = data.get('agent_id')
    timestamp_assigned = data.get('timestamp_assigned', 0.0)
    
    if wo_id and wo_id in self._local_wo_state:
        # Update local state
        self._local_wo_state[wo_id]['assigned_agent_id'] = agent_id
        self._local_wo_state[wo_id]['timestamp_assigned'] = timestamp_assigned
        
        # Update UI cell
        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            agent_column = self._get_column_index('assigned_agent_id')
            if agent_column >= 0:
                index = self.model.index(row, agent_column)
                self.model.dataChanged.emit(index, index)
        
        print(f"[DASHBOARD] WO {wo_id} assigned to {agent_id}")

def _handle_wo_progress_updated(self, message: Dict[str, Any]):
    """
    Handle WorkOrder progress update event (granular update).
    """
    if self._is_rebuilding_state:
        return
    
    data = message.get('data', {})
    wo_id = data.get('wo_id')
    cantidad_restante = data.get('cantidad_restante')
    volumen_restante = data.get('volumen_restante')
    progress_percentage = data.get('progress_percentage', 0.0)
    
    if wo_id and wo_id in self._local_wo_state:
        # Update local state
        self._local_wo_state[wo_id]['cantidad_restante'] = cantidad_restante
        self._local_wo_state[wo_id]['volumen_restante'] = volumen_restante
        self._local_wo_state[wo_id]['progress'] = progress_percentage
        
        # Update UI (emit signal for entire row for simplicity)
        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            left_index = self.model.index(row, 0)
            right_index = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left_index, right_index)

def _handle_wo_completed(self, message: Dict[str, Any]):
    """
    Handle WorkOrder completion event.
    """
    if self._is_rebuilding_state:
        return
    
    data = message.get('data', {})
    wo_id = data.get('wo_id')
    completion_time = data.get('completion_time', 0.0)
    
    if wo_id and wo_id in self._local_wo_state:
        # Update local state
        self._local_wo_state[wo_id]['status'] = 'completed'
        self._local_wo_state[wo_id]['completion_time'] = completion_time
        self._local_wo_state[wo_id]['cantidad_restante'] = 0
        self._local_wo_state[wo_id]['volumen_restante'] = 0.0
        
        # Update UI
        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            left_index = self.model.index(row, 0)
            right_index = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left_index, right_index)
        
        print(f"[DASHBOARD] WO {wo_id} COMPLETED at t={completion_time:.2f}s")
```

---

### PASO 6: Implementar Métodos Helper

```python
def _find_row_by_wo_id(self, wo_id: str) -> int:
    """
    Find row index in table by WorkOrder ID.
    Returns -1 if not found.
    """
    for row, wo_data in enumerate(self.model._data):
        if wo_data.get('id') == wo_id:
            return row
    return -1

def _get_column_index(self, column_name: str) -> int:
    """
    Get column index by column name.
    Returns -1 if not found.
    """
    if not hasattr(self.model, 'headers'):
        return -1
    
    try:
        return self.model.headers.index(column_name)
    except (ValueError, AttributeError):
        return -1

def _handle_time_tick(self, message: Dict[str, Any]):
    """Handle periodic time update event."""
    timestamp = message.get('timestamp', 0.0)
    
    if hasattr(self, 'time_slider') and self.time_slider:
        self.time_slider.setValue(int(timestamp))

def _handle_time_seek(self, message: Dict[str, Any]):
    """Handle time seek command (user interaction)."""
    target_time = message.get('data', {}).get('target_time', 0.0)
    print(f"[DASHBOARD] TIME_SEEK command received: {target_time:.2f}s")
    # STATE_RESET and STATE_SNAPSHOT will follow

def _handle_metrics_updated(self, message: Dict[str, Any]):
    """Handle metrics update event."""
    if self._is_rebuilding_state:
        return
    
    metrics = message.get('data', {})
    self._local_metrics.update(metrics)
    
    # Update status bar with metrics
    completed = metrics.get('workorders_completadas', 0)
    total = metrics.get('total_wos', 0)
    time_sim = metrics.get('tiempo', 0.0)
    
    if total > 0:
        self.statusBar().showMessage(
            f"Progress: {completed}/{total} WOs | Time: {time_sim:.1f}s"
        )
```

---

## PASO 7: MODIFICAR ReplayEngine para Emitir Eventos Granulares

**ARCHIVO:** `src/engines/replay_engine.py`

En el método `_process_event_batch()`, agregar emisión de eventos granulares:

```python
def _process_event_batch(self, eventos_a_procesar):
    """
    Process batch of events and emit granular typed events.
    """
    for event_index, evento in eventos_a_procesar:
        event_type = evento.get('type')
        timestamp = evento.get('timestamp', 0.0)
        
        # ===== WorkOrder Events =====
        if event_type == 'work_order_update':
            wo_id = evento.get('id')
            if not wo_id:
                continue
            
            # Get previous state to detect changes
            prev_wo = self.dashboard_wos_state.get(wo_id, {})
            
            # Detect status change
            new_status = evento.get('status')
            old_status = prev_wo.get('status')
            if old_status != new_status:
                self._emit_event(WorkOrderStatusChangedEvent(
                    timestamp=timestamp,
                    wo_id=wo_id,
                    old_status=old_status or 'unknown',
                    new_status=new_status,
                    agent_id=evento.get('assigned_agent_id')
                ))
            
            # Detect assignment change
            new_agent = evento.get('assigned_agent_id')
            old_agent = prev_wo.get('assigned_agent_id')
            if new_agent and new_agent != old_agent:
                self._emit_event(WorkOrderAssignedEvent(
                    timestamp=timestamp,
                    wo_id=wo_id,
                    agent_id=new_agent,
                    timestamp_assigned=timestamp
                ))
            
            # Detect progress change
            new_cantidad = evento.get('cantidad_restante', 0)
            old_cantidad = prev_wo.get('cantidad_restante', 0)
            new_volumen = evento.get('volumen_restante', 0.0)
            old_volumen = prev_wo.get('volumen_restante', 0.0)
            
            if new_cantidad != old_cantidad or new_volumen != old_volumen:
                total_cantidad = evento.get('cantidad_total', new_cantidad)
                progress = 0.0
                if total_cantidad > 0:
                    progress = ((total_cantidad - new_cantidad) / total_cantidad) * 100.0
                
                self._emit_event(WorkOrderProgressUpdatedEvent(
                    timestamp=timestamp,
                    wo_id=wo_id,
                    cantidad_restante=new_cantidad,
                    volumen_restante=new_volumen,
                    progress_percentage=progress
                ))
            
            # Update internal state
            self.dashboard_wos_state[wo_id] = evento.copy()
```

---

## VALIDACIÓN REQUERIDA

Después de implementar, DEBES validar que:

### Test 1: STATE_RESET limpia el dashboard
```bash
USE_EVENT_SOURCING=true python entry_points/run_replay_viewer.py <replay_file>
# Mover el scrubber y verificar logs:
# [DASHBOARD] STATE RESET received - reason: seek
# [DASHBOARD] State cleared, awaiting STATE_SNAPSHOT...
```

### Test 2: STATE_SNAPSHOT reconstruye el estado
```bash
# Verificar logs:
# [DASHBOARD] STATE SNAPSHOT received at time X.XXs
# [DASHBOARD]   - WorkOrders: N
# [DASHBOARD] State rebuilt successfully: N WorkOrders
```

### Test 3: Eventos granulares actualizan UI
```bash
# Verificar logs:
# [DASHBOARD] WO WO-001 status: pending -> assigned
# [DASHBOARD] WO WO-001 assigned to GroundOp-01
# [DASHBOARD] WO WO-001 COMPLETED at t=XX.XXs
```

### Test 4: Operarios se mueven en layout
```bash
# Verificar visualmente que operarios (GroundOp, Forklift) se mueven
# Verificar logs: [DEBUG-AGENT] Updated position for ...
```

### Test 5: Scrubber funciona sin race conditions
```bash
# Mover slider rápidamente adelante y atrás
# Verificar que tabla siempre muestra estado correcto
# NO debe haber discrepancias entre WOs in_progress y operarios trabajando
```

---

## TESTS DE INTEGRACIÓN REQUERIDOS

**CREAR ESTOS ARCHIVOS:**

### `tests/integration/test_full_event_flow.py`

```python
"""
Test End-to-End Event Flow - Validación completa del flujo de eventos
"""
import os
os.environ['USE_EVENT_SOURCING'] = 'true'

def test_event_emission():
    """Test que ReplayEngine emite eventos correctamente"""
    # TODO: Implementar test

def test_event_consumption():
    """Test que Dashboard consume eventos correctamente"""
    # TODO: Implementar test

def test_state_reset_protocol():
    """Test protocolo STATE_RESET -> STATE_SNAPSHOT"""
    # TODO: Implementar test

def test_granular_updates():
    """Test que eventos granulares actualizan UI correctamente"""
    # TODO: Implementar test
```

### `tests/integration/test_scrubber_stress.py`

```python
"""
Test de Estrés del Scrubber - Validación de robustez bajo carga
"""
import os
os.environ['USE_EVENT_SOURCING'] = 'true'

def test_rapid_seeking():
    """Test arrastre rápido del slider sin race conditions"""
    # TODO: Implementar test

def test_consistency_after_seek():
    """Test que estado es consistente después de seek"""
    # TODO: Implementar test

def test_performance_benchmark():
    """Test que latencia de eventos está bajo 5ms"""
    # TODO: Implementar test
```

---

## MÉTRICAS DE ÉXITO

Tu implementación será exitosa cuando:

1. ✅ **Latencia de eventos < 5ms:** Tiempo entre emisión y recepción
2. ✅ **Scrubber seek < 50ms:** Tiempo total del protocolo STATE_RESET -> STATE_SNAPSHOT
3. ✅ **100% consistencia:** Estado siempre correcto después de seeks
4. ✅ **Operarios móviles:** Agentes se mueven visualmente en layout
5. ✅ **Work Orders actualizadas:** Tabla muestra cambios en tiempo real
6. ✅ **Sin race conditions:** No discrepancias durante navegación temporal

---

## PROBLEMAS A EVITAR

### ❌ NO HACER:

1. **NO cambiar importaciones a `src.communication`** - Usar importaciones relativas (`from communication.ipc_protocols`)
2. **NO implementar solo STATE_RESET sin STATE_SNAPSHOT** - Ambos son críticos
3. **NO olvidar el flag `_is_rebuilding_state`** - Previene race conditions
4. **NO olvidar enviar `SEEK_COMPLETE`** - Confirma sincronización al engine
5. **NO olvidar validar end-to-end** - Tests de integración son obligatorios

---

## CHECKLIST ANTES DE HACER COMMIT

- [ ] `_local_wo_state` agregado al `__init__()`
- [ ] `_handle_state_reset()` implementado
- [ ] `_handle_state_snapshot()` implementado
- [ ] Handlers granulares (status_changed, assigned, progress_updated, completed) implementados
- [ ] `_find_row_by_wo_id()` helper implementado
- [ ] `_get_column_index()` helper implementado
- [ ] `SEEK_COMPLETE` confirmation enviada al engine
- [ ] `_process_event_batch()` en ReplayEngine emite eventos granulares
- [ ] Test 1: STATE_RESET limpia dashboard ✅
- [ ] Test 2: STATE_SNAPSHOT reconstruye estado ✅
- [ ] Test 3: Eventos granulares actualizan UI ✅
- [ ] Test 4: Operarios se mueven en layout ✅
- [ ] Test 5: Scrubber sin race conditions ✅
- [ ] Tests de integración creados
- [ ] Performance benchmarks ejecutados
- [ ] Documentación actualizada

---

## ORDEN DE IMPLEMENTACIÓN RECOMENDADO

1. **Primero:** Agregar estado local al Dashboard
2. **Segundo:** Implementar `_handle_state_reset()`
3. **Tercero:** Implementar `_handle_state_snapshot()`
4. **Cuarto:** Modificar `_process_event_batch()` para emitir eventos
5. **Quinto:** Implementar handlers granulares
6. **Sexto:** Validar con tests manuales
7. **Séptimo:** Crear tests de integración
8. **Octavo:** Benchmark de performance

---

## ARQUITECTURA OBJETIVO FINAL

```
[Event Stream] (replay_events.jsonl)
    |
    v
[ReplayEngine._process_event_batch]
    |
    +---> _emit_event(WorkOrderStatusChangedEvent)
    +---> _emit_event(WorkOrderAssignedEvent)
    +---> _emit_event(WorkOrderProgressUpdatedEvent)
    |
    v
[DashboardCommunicator.send_event]
    |
    v
[IPC Queue] (multiprocessing.Queue)
    |
    v
[WorkOrderDashboard.handle_message]
    |
    +---> _handle_state_reset() -----> Limpia _local_wo_state
    +---> _handle_state_snapshot() --> Reconstruye desde eventos
    +---> _handle_wo_status_changed() -> Actualiza UI (granular)
    +---> _handle_wo_assigned() -------> Actualiza UI (granular)
    +---> _handle_wo_progress_updated() -> Actualiza UI (granular)
    |
    v
[QTableView con datos actualizados]
```

---

## TIEMPO ESTIMADO

- Implementación del Event Consumer: **6-8 horas**
- Validación end-to-end: **2-3 horas**
- Tests de integración: **2-3 horas**
- Performance tuning: **1-2 horas**

**Total:** **12-16 horas**

---

## RESULTADO ESPERADO

Al completar esta implementación:

✅ Dashboard PyQt6 recibirá y procesará eventos correctamente
✅ Work Orders se actualizarán en tiempo real
✅ Operarios se moverán visualmente en layout
✅ Scrubber funcionará sin race conditions
✅ Latencia de actualización < 5ms (vs 67ms actual)
✅ Sistema completamente funcional con Event Sourcing

---

## CONTACTO Y SEGUIMIENTO

Si encuentras algún problema durante la implementación:

1. Verificar que `USE_EVENT_SOURCING=true` está seteado
2. Verificar logs: `[DASHBOARD]`, `[DEBUG-EVENT]`, `[EVENT-ENGINE]`
3. Verificar que imports son relativos (no `src.`)
4. Revisar que `_is_rebuilding_state` previene race conditions

---

**IMPORTANTE:** Esta es la implementación completa y final. NO omitas ningún paso. El sistema NO funcionará si falta alguno de los handlers críticos (STATE_RESET, STATE_SNAPSHOT, eventos granulares).

**¡ÉXITO EN LA IMPLEMENTACIÓN!** 🚀

