# PLAN DE REPARACION: Generacion de Archivos .jsonl

**Fecha:** 2025-10-07  
**Basado en:** AUDITORIA_JSONL_GENERATION.md  
**Objetivo:** Reparar sistema de generacion de archivos `.jsonl` y carpetas `output/`

---

## RESUMEN EJECUTIVO

**PROBLEMA IDENTIFICADO:**  
El `replay_buffer` NO se llena durante la simulacion porque:
1. `AlmacenMejorado.registrar_evento()` solo escribe a `event_log` (para analytics)
2. Operarios NO capturan eventos de `estado_agente`
3. No hay conexion entre `event_log` y `replay_buffer`

**SOLUCION:**  
Conectar el sistema de eventos del almacen con el `replay_buffer` del simulador

---

## FASE 1: Conectar registrar_evento() con replay_buffer

### Objetivo
Hacer que todos los eventos capturados por `registrar_evento()` tambien se agreguen al `replay_buffer`

### Archivos a Modificar

#### 1.1 `src/subsystems/simulation/warehouse.py`

**Cambio A: Agregar replay_buffer al constructor**

**Ubicacion:** Linea 81 (metodo `__init__`)

**Antes:**
```python
def __init__(self, env: simpy.Environment, configuracion: Dict[str, Any],
             layout_manager=None, pathfinder=None, data_manager=None,
             cost_calculator=None, route_calculator=None, simulador=None,
             visual_event_queue=None):
```

**Despues:**
```python
def __init__(self, env: simpy.Environment, configuracion: Dict[str, Any],
             layout_manager=None, pathfinder=None, data_manager=None,
             cost_calculator=None, route_calculator=None, simulador=None,
             visual_event_queue=None, replay_buffer=None):
```

**Cambio B: Guardar referencia al replay_buffer**

**Ubicacion:** Despues de linea 109

**Agregar:**
```python
self.replay_buffer = replay_buffer  # NEW: Replay buffer for .jsonl generation
```

**Cambio C: Modificar registrar_evento()**

**Ubicacion:** Linea 368-381

**Antes:**
```python
def registrar_evento(self, tipo: str, datos: Dict[str, Any]):
    evento = {
        'timestamp': self.env.now,
        'tipo': tipo,
        **datos
    }
    self.event_log.append(evento)
```

**Despues:**
```python
def registrar_evento(self, tipo: str, datos: Dict[str, Any]):
    evento = {
        'timestamp': self.env.now,
        'tipo': tipo,
        **datos
    }
    self.event_log.append(evento)
    
    # BUGFIX: Tambien agregar al replay_buffer para generacion de .jsonl
    if self.replay_buffer:
        # Convertir formato para replay (tipo -> type)
        replay_evento = {
            'type': tipo,
            'timestamp': self.env.now,
            **datos
        }
        self.replay_buffer.add_event(replay_evento)
```

#### 1.2 `src/engines/simulation_engine.py`

**Cambio: Pasar replay_buffer al crear AlmacenMejorado**

**Ubicacion:** Buscar donde se crea `AlmacenMejorado` (aprox linea 200-300)

**Antes:**
```python
self.almacen = AlmacenMejorado(
    env=self.env,
    configuracion=self.configuracion,
    layout_manager=self.layout_manager,
    pathfinder=self.pathfinder,
    data_manager=data_manager,
    cost_calculator=cost_calculator,
    route_calculator=route_calculator,
    simulador=self,
    visual_event_queue=self.visual_event_queue  # Si existe
)
```

**Despues:**
```python
self.almacen = AlmacenMejorado(
    env=self.env,
    configuracion=self.configuracion,
    layout_manager=self.layout_manager,
    pathfinder=self.pathfinder,
    data_manager=data_manager,
    cost_calculator=cost_calculator,
    route_calculator=route_calculator,
    simulador=self,
    visual_event_queue=self.visual_event_queue,  # Si existe
    replay_buffer=self.replay_buffer  # NEW: Pass replay buffer
)
```

**NOTA:** Buscar TODAS las llamadas a `AlmacenMejorado()` en el archivo

#### 1.3 `src/engines/simulation_engine.py` - Proceso Productor

**Cambio: Pasar replay_buffer al proceso separado**

**Ubicacion:** Funcion `_run_simulation_process_static` (linea 1419)

**PROBLEMA:** El proceso productor NO tiene acceso al replay_buffer porque es un proceso separado

**SOLUCION:** El proceso productor ya usa `visual_event_queue` para enviar eventos. Estos eventos deben copiarse al replay_buffer en el proceso consumidor.

**Ubicacion del consumidor:** Metodo `ejecutar_bucle_principal()` (linea 630-641)

**ANTES:**
```python
try:
    while True:  # Drenar la cola completamente
        try:
            mensaje = self.visual_event_queue.get_nowait()
            eventos_recibidos += 1
            
            # Asignar timestamp del productor, o tiempo actual si no tiene
            if 'timestamp' not in mensaje or mensaje['timestamp'] is None:
                mensaje['timestamp'] = self.playback_time - 0.001
            
            # Agregar evento al buffer ordenado por timestamp
            self.event_buffer.append(mensaje)
            
        except queue.Empty:
            break
```

**DESPUES:**
```python
try:
    while True:  # Drenar la cola completamente
        try:
            mensaje = self.visual_event_queue.get_nowait()
            eventos_recibidos += 1
            
            # Asignar timestamp del productor, o tiempo actual si no tiene
            if 'timestamp' not in mensaje or mensaje['timestamp'] is None:
                mensaje['timestamp'] = self.playback_time - 0.001
            
            # Agregar evento al buffer ordenado por timestamp
            self.event_buffer.append(mensaje)
            
            # BUGFIX: Tambien copiar al replay_buffer para .jsonl
            if self.replay_buffer:
                self.replay_buffer.add_event(mensaje)
            
        except queue.Empty:
            break
```

### Testing FASE 1

**Comando:**
```bash
python entry_points/run_live_simulation.py --headless
```

**Verificaciones:**
1. No hay errores de ejecucion
2. Se crea carpeta `output/simulation_YYYYMMDD_HHMMSS/`
3. Archivo `replay_YYYYMMDD_HHMMSS.jsonl` existe
4. Archivo tiene mas de 2 lineas (SIMULATION_START y SIMULATION_END)
5. Archivo contiene eventos `work_order_update`

**Log esperado:**
```
[REPLAY-BUFFER] 500+ eventos guardados en output/.../replay_....jsonl
```

---

## FASE 2: Agregar captura de eventos estado_agente

### Objetivo
Capturar posiciones y estados de operarios para visualizacion en replay

### Archivos a Modificar

#### 2.1 `src/subsystems/simulation/operators.py` - GroundOperator

**Ubicacion:** Metodo `agent_process()` (linea 165-263)

**Puntos de Captura:**

**A) Despues de actualizar posicion (linea 232)**
```python
# Actualizar posicion
self.current_position = wo.ubicacion
self.total_distance_traveled += segment_distance

# BUGFIX: Capturar evento de posicion para replay
self.almacen.registrar_evento('estado_agente', {
    'agent_id': self.id,
    'tipo': self.type,
    'x': self.current_position[0] * 32 + 16,  # Convertir a pixeles
    'y': self.current_position[1] * 32 + 16,
    'status': self.status,
    'current_task': wo.id if wo else None
})
```

**B) Despues de cambiar status (lineas 226, 236, 248, 256)**
```python
self.status = "moving"  # o "picking", "unloading"

# BUGFIX: Capturar cambio de estado
if self.current_position:
    self.almacen.registrar_evento('estado_agente', {
        'agent_id': self.id,
        'tipo': self.type,
        'x': self.current_position[0] * 32 + 16,
        'y': self.current_position[1] * 32 + 16,
        'status': self.status,
        'current_task': None
    })
```

**NOTA:** Aplicar cambios similares a clase `Forklift`

### Testing FASE 2

**Verificaciones:**
1. Archivo `.jsonl` contiene eventos `estado_agente`
2. Eventos tienen campos: `agent_id`, `tipo`, `x`, `y`, `status`
3. Eventos se generan en timestamps correctos

**Comando de inspeccion:**
```bash
grep "estado_agente" output/simulation_*/replay_*.jsonl | head -5
```

---

## FASE 3: Verificar escritura de archivo

### Objetivo
Asegurar que `volcar_replay_a_archivo()` se ejecuta correctamente

### Archivos a Verificar

#### 3.1 `src/engines/simulation_engine.py`

**Ubicacion:** Metodo `ejecutar()` lineas 1380-1385

**Verificar que existe:**
```python
# RESTORED: Generate replay file after simulation completion
if self.replay_buffer and len(self.replay_buffer) > 0:
    os.makedirs(self.session_output_dir, exist_ok=True)
    output_file = os.path.join(self.session_output_dir, f"replay_{self.session_timestamp}.jsonl")
    print(f"[REPLAY] Generating replay file: {output_file}")
    initial_snapshot = getattr(self.almacen.dispatcher, 'initial_work_orders_snapshot', []) if hasattr(self, 'almacen') and self.almacen else []
    volcar_replay_a_archivo(self.replay_buffer, output_file, self.configuracion, self.almacen, initial_snapshot)
```

**PROBLEMA POTENCIAL:** Modo headless puede no ejecutar esta seccion

**SOLUCION:** Verificar que AMBOS modos (visual y headless) llegan a este codigo

### Testing FASE 3

**Verificaciones:**
1. Log muestra: `[REPLAY] Generating replay file: output/.../replay_....jsonl`
2. Log muestra: `[REPLAY-BUFFER] NNN eventos guardados en ...`
3. Archivo existe y tiene contenido

---

## FASE 4: Testing Completo

### 4.1 Test Modo Headless

**Comando:**
```bash
python entry_points/run_live_simulation.py --headless
```

**Verificaciones:**
- [ ] Se crea carpeta `output/simulation_YYYYMMDD_HHMMSS/`
- [ ] Archivo `replay_YYYYMMDD_HHMMSS.jsonl` existe
- [ ] Archivo `simulacion_completada_YYYYMMDD_HHMMSS.json` existe
- [ ] Archivo `simulation_report_YYYYMMDD_HHMMSS.xlsx` existe
- [ ] Archivo `raw_events_YYYYMMDD_HHMMSS.json` existe

**Contenido del .jsonl:**
- [ ] Primera linea: `SIMULATION_START` con metadata
- [ ] Eventos `work_order_update` presentes
- [ ] Eventos `estado_agente` presentes (si FASE 2 implementada)
- [ ] Ultima linea: `SIMULATION_END`

### 4.2 Test Modo Visual

**Comando:**
```bash
python entry_points/run_live_simulation.py
```

**Verificaciones:** Mismas que modo headless

### 4.3 Inspeccion Manual

**Ver eventos capturados:**
```bash
# Contar lineas
wc -l output/simulation_*/replay_*.jsonl

# Ver primeras 5 lineas
head -5 output/simulation_*/replay_*.jsonl

# Ver ultimas 5 lineas
tail -5 output/simulation_*/replay_*.jsonl

# Contar eventos por tipo
grep -o '"type":"[^"]*"' output/simulation_*/replay_*.jsonl | sort | uniq -c
```

---

## FASE 5: Validacion con Replay Viewer

### Objetivo
Confirmar que el archivo generado es compatible con el replay viewer

### Comando

```bash
python entry_points/run_replay_viewer.py output/simulation_YYYYMMDD_HHMMSS/replay_YYYYMMDD_HHMMSS.jsonl
```

### Verificaciones

**Al iniciar:**
- [ ] No hay errores de parsing JSON
- [ ] Log muestra: `[REPLAY] NNN eventos cargados exitosamente`
- [ ] Dashboard muestra metricas iniciales
- [ ] Mapa TMX se renderiza correctamente

**Durante replay:**
- [ ] Agentes se mueven en el mapa
- [ ] Dashboard se actualiza con progreso
- [ ] No hay errores en consola
- [ ] WorkOrders se marcan como completadas

**Al finalizar:**
- [ ] Mensaje: `SIMULATION_END detectado`
- [ ] Replay se pausa automaticamente
- [ ] Metricas finales son correctas

---

## ROLLBACK PLAN

Si algo falla durante la implementacion:

### Revertir FASE 1
```bash
git restore src/subsystems/simulation/warehouse.py
git restore src/engines/simulation_engine.py
```

### Revertir FASE 2
```bash
git restore src/subsystems/simulation/operators.py
```

---

## CRITERIOS DE EXITO

### Minimo Viable (FASE 1)
- ✅ Archivo `.jsonl` se genera
- ✅ Contiene eventos `work_order_update`
- ✅ Replay viewer puede cargar el archivo

### Completo (FASE 1 + 2)
- ✅ Archivo `.jsonl` con eventos completos
- ✅ Eventos `estado_agente` presentes
- ✅ Replay viewer muestra agentes en movimiento
- ✅ Dashboard funciona correctamente

---

## ORDEN DE IMPLEMENTACION RECOMENDADO

1. ✅ **COMPLETADO:** Auditoria completa
2. ⏳ **SIGUIENTE:** FASE 1 - Implementar conexion replay_buffer
3. ⏳ **DESPUES:** FASE 3 - Verificar escritura archivo
4. ⏳ **DESPUES:** FASE 4 - Testing completo
5. ⏳ **OPCIONAL:** FASE 2 - Eventos estado_agente (si se necesita visualizacion)
6. ⏳ **FINAL:** FASE 5 - Validacion replay viewer

---

## NOTAS IMPORTANTES

1. **Modo Productor-Consumidor:** Requiere atencion especial porque usa procesos separados
2. **Formato de eventos:** `tipo` (event_log) vs `type` (replay) - conversión necesaria
3. **Timestamps:** Usar `self.env.now` del SimPy environment
4. **Posiciones:** Convertir grid coordinates a pixeles (x*32+16, y*32+16)

---

**LISTO PARA IMPLEMENTACION**

¿Proceder con FASE 1?

