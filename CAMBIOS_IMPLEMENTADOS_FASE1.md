# CAMBIOS IMPLEMENTADOS - FASE 1

**Fecha:** 2025-10-07  
**Objetivo:** Conectar replay_buffer con sistema de eventos del almacen

---

## RESUMEN DE CAMBIOS

### ✅ COMPLETADO: Conexion replay_buffer <-> registrar_evento()

**Archivos Modificados:** 2
- `src/subsystems/simulation/warehouse.py`
- `src/engines/simulation_engine.py`

**Total de Lineas Agregadas:** ~15 lineas
**Total de Lineas Modificadas:** ~5 lineas

---

## CAMBIOS DETALLADOS

### 1. `src/subsystems/simulation/warehouse.py`

#### Cambio A: Constructor - Agregar parametro replay_buffer
**Linea:** 84 (antes linea 84)
```python
# ANTES:
def __init__(self, env, configuracion, ..., visual_event_queue=None):

# DESPUES:
def __init__(self, env, configuracion, ..., visual_event_queue=None, replay_buffer=None):
```

#### Cambio B: Constructor - Guardar referencia
**Linea:** 112 (nueva linea)
```python
self.replay_buffer = replay_buffer
```

#### Cambio C: registrar_evento() - Escribir a replay_buffer
**Lineas:** 389-397 (nuevas lineas)
```python
# BUGFIX JSONL: Tambien agregar al replay_buffer para generacion de .jsonl
if self.replay_buffer:
    # Convertir formato para replay (tipo -> type)
    replay_evento = {
        'type': tipo,
        'timestamp': self.env.now,
        **datos
    }
    self.replay_buffer.add_event(replay_evento)
```

---

### 2. `src/engines/simulation_engine.py`

#### Cambio A: Pasar replay_buffer al crear AlmacenMejorado (modo normal)
**Linea:** 346 (nueva linea)
```python
self.almacen = AlmacenMejorado(
    ...
    simulador=self,
    replay_buffer=self.replay_buffer  # NUEVO
)
```

#### Cambio B: Proceso productor - Comentario explicativo
**Lineas:** 1494-1506 (modificadas)
```python
# NOTA JSONL: En proceso productor NO se pasa replay_buffer porque es un proceso
# separado. Los eventos se envian via visual_event_queue y se copian al
# replay_buffer en el proceso consumidor
almacen = AlmacenMejorado(
    ...
    visual_event_queue=visual_event_queue,
    replay_buffer=None  # No disponible en proceso hijo
)
```

#### Cambio C: Bucle consumidor - Copiar eventos a replay_buffer
**Lineas:** 644-646 (nuevas lineas)
```python
# BUGFIX JSONL: Tambien copiar al replay_buffer para .jsonl
if self.replay_buffer:
    self.replay_buffer.add_event(mensaje)
```

---

## FLUJO DE EVENTOS REPARADO

### Modo Headless (Proceso Unico)
```
[Dispatcher.notificar_completado()]
  └─> almacen.registrar_evento('work_order_update', datos)
      ├─> event_log.append(evento)           # Para analytics
      └─> replay_buffer.add_event(evento)    # Para .jsonl ✅ NUEVO
```

### Modo Visual (Productor-Consumidor)
```
[Proceso Productor SimPy]
  └─> almacen.registrar_evento('work_order_update', datos)
      └─> event_log.append(evento)           # replay_buffer=None en proceso hijo
      └─> visual_event_queue.put(evento)     # Envia a proceso consumidor

[Proceso Consumidor Visual]
  └─> visual_event_queue.get()
      ├─> event_buffer.append(mensaje)       # Para visualizacion
      └─> replay_buffer.add_event(mensaje)   # Para .jsonl ✅ NUEVO
```

---

## EVENTOS CAPTURADOS

### ✅ YA SE CAPTURAN (con esta reparacion):
- `work_order_update` - Cuando se completan WorkOrders
- Eventos de metricas del dashboard (modo visual)
- Eventos de finalizacion de simulacion

### ⏳ PENDIENTE (FASE 2 - Opcional):
- `estado_agente` - Posiciones y estados de operarios en tiempo real

---

## TESTING REQUERIDO

### Test 1: Modo Headless
```bash
python entry_points/run_live_simulation.py --headless
```

**Verificar:**
- [ ] Se crea carpeta `output/simulation_YYYYMMDD_HHMMSS/`
- [ ] Archivo `replay_YYYYMMDD_HHMMSS.jsonl` existe
- [ ] Log muestra: `[REPLAY-BUFFER] NNN eventos guardados en ...`
- [ ] Archivo tiene mas de 2 lineas

**Inspeccion:**
```bash
# Contar lineas
wc -l output/simulation_*/replay_*.jsonl

# Ver primeros eventos
head -10 output/simulation_*/replay_*.jsonl

# Contar eventos por tipo
grep -o '"type":"[^"]*"' output/simulation_*/replay_*.jsonl | sort | uniq -c
```

### Test 2: Modo Visual
```bash
python entry_points/run_live_simulation.py
```

**Verificar:** Mismos criterios que Test 1

### Test 3: Replay Viewer
```bash
python entry_points/run_replay_viewer.py output/simulation_YYYYMMDD_HHMMSS/replay_YYYYMMDD_HHMMSS.jsonl
```

**Verificar:**
- [ ] No hay errores de parsing
- [ ] Dashboard muestra progreso
- [ ] WorkOrders se actualizan

---

## PROXIMOS PASOS

### FASE 2 (Opcional): Eventos estado_agente
- Modificar `src/subsystems/simulation/operators.py`
- Capturar posiciones de agentes en tiempo real
- **Beneficio:** Replay viewer mostrara movimiento de agentes

### FASE 4: Testing Completo
- Ejecutar simulacion completa
- Validar todos los archivos generados
- Confirmar compatibilidad con replay viewer

---

## ROLLBACK (si es necesario)

```bash
git restore src/subsystems/simulation/warehouse.py
git restore src/engines/simulation_engine.py
```

---

**ESTADO:** ✅ FASE 1 COMPLETADA - Listo para testing
