# INSTRUCCIONES TÉCNICAS DEL SISTEMA

**Proyecto:** Simulador de Gemelo Digital de Almacén  
**Versión:** V11 Complete  
**Última Actualización:** 2025-10-08

---

## 🚀 INICIO RÁPIDO

### Ejecutar Simulación Visual:
```bash
python entry_points/run_live_simulation.py
```

### Ejecutar Simulación Headless (sin GUI):
```bash
python entry_points/run_live_simulation.py --headless
```

### Ejecutar Test Rápido (debugging):
```bash
python test_quick_jsonl.py
```

### Ver Replay de Simulación:
```bash
python entry_points/run_replay_viewer.py output/simulation_YYYYMMDD_HHMMSS/replay_YYYYMMDD_HHMMSS.jsonl
```

---

## 📁 ESTRUCTURA DEL PROYECTO

```
Gemelos Digital/
├── entry_points/
│   ├── run_live_simulation.py       # Punto de entrada principal
│   └── run_replay_viewer.py         # Visualizador de replay
│
├── src/
│   ├── engines/
│   │   ├── simulation_engine.py     # Motor principal de simulación
│   │   ├── analytics_engine.py      # Motor de análisis y reportes
│   │   └── replay_engine.py         # Motor de replay
│   │
│   ├── subsystems/
│   │   ├── simulation/
│   │   │   ├── warehouse.py         # Almacén (entidad principal)
│   │   │   ├── dispatcher.py        # Despachador de tareas
│   │   │   └── operators.py         # Operarios y montacargas
│   │   │
│   │   └── visualization/
│   │       ├── dashboard.py         # Dashboard pygame_gui
│   │       ├── renderer.py          # Renderizado de agentes
│   │       └── state.py             # Estado de visualización
│   │
│   ├── core/
│   │   ├── config_manager.py        # Gestor de configuración
│   │   ├── replay_utils.py          # Utilidades para .jsonl
│   │   └── pathfinder.py            # Algoritmo A* para rutas
│   │
│   └── shared/
│       └── buffer.py                # ReplayBuffer para eventos
│
├── data/
│   ├── layouts/
│   │   ├── WH1.tmx                  # Mapa del almacén (Tiled)
│   │   └── Warehouse_Logic.xlsx    # Plan maestro de picking
│   │
│   └── themes/
│       └── dashboard_theme.json     # Tema del dashboard
│
├── output/                          # Resultados de simulaciones
│   └── simulation_YYYYMMDD_HHMMSS/
│       ├── replay_YYYYMMDD_HHMMSS.jsonl      # Archivo de replay
│       ├── raw_events_YYYYMMDD_HHMMSS.json   # Eventos sin procesar
│       └── metricas_YYYYMMDD_HHMMSS.xlsx     # Reporte ejecutivo
│
├── config.json                      # Configuración principal
├── config_test_quick.json           # Config para testing (3 órdenes)
└── test_quick_jsonl.py              # Script de test rápido
```

---

## ⚙️ CONFIGURACIÓN

### config.json - Parámetros principales:

```json
{
  "total_ordenes": 50,                    // Número de órdenes a simular
  "num_operarios_terrestres": 2,          // Operarios a pie
  "num_montacargas": 1,                   // Montacargas
  "capacidad_carro": 150,                 // Capacidad de carga (unidades vol.)
  "capacidad_montacargas": 1000,          // Capacidad de montacargas
  "tiempo_descarga_por_tarea": 5,         // Tiempo de descarga (segundos sim.)
  
  "dispatch_strategy": "Optimizacion Global",  // Estrategia de asignación
  "tour_type": "Tour Mixto (Multi-Destino)",   // Tipo de tour
  
  "layout_file": "data/layouts/WH1.tmx",         // Mapa TMX
  "sequence_file": "data/layouts/Warehouse_Logic.xlsx",  // Plan maestro
  
  "distribucion_tipos": {
    "pequeno": { "porcentaje": 70, "volumen": 5 },
    "mediano": { "porcentaje": 25, "volumen": 15 },
    "grande":  { "porcentaje": 5,  "volumen": 30 }
  },
  
  "assignment_rules": {
    "GroundOperator": { /* ... */ },
    "Forklift": { /* ... */ }
  }
}
```

### Estrategias de Despacho:
- `"FIFO"` - First In First Out
- `"Proximidad"` - Asignar tareas más cercanas
- `"Optimizacion Global"` - Optimización por costo/distancia
- `"Ejecucion de Plan (Filtro por Prioridad)"` - Seguir plan maestro

### Tipos de Tour:
- `"Tour Simple (Un Solo Destino)"` - Una tarea por tour
- `"Tour Mixto (Multi-Destino)"` - Múltiples tareas por tour

---

## 🔧 ARQUITECTURA TÉCNICA

### Modo Visual (Multiproceso):
```
┌─────────────────────────────────┐
│  PROCESO PRODUCTOR (SimPy)      │
│  - SimulationEngine              │
│  - AlmacenMejorado               │
│  - Dispatcher                    │
│  - Operadores                    │
│  - Genera eventos de simulación │
└────────────┬────────────────────┘
             │ visual_event_queue
             ↓
┌─────────────────────────────────┐
│  PROCESO CONSUMIDOR (Pygame)    │
│  - Lee eventos de la cola        │
│  - Actualiza estado_visual       │
│  - Renderiza dashboard           │
│  - Copia eventos a replay_buffer │
└─────────────────────────────────┘
```

### Modo Headless (Proceso único):
```
┌─────────────────────────────────┐
│  SimulationEngine (headless)    │
│  - AlmacenMejorado               │
│    └─ registrar_evento()         │
│       ├─ event_log.append()      │
│       └─ replay_buffer.add()     │  ← PROBLEMA ACTUAL
│  - Sin GUI, máxima velocidad     │
└─────────────────────────────────┘
```

### Flujo de Eventos:
```
1. Operario completa WorkOrder
   ↓
2. Dispatcher.notificar_completado()
   ↓
3. AlmacenMejorado.registrar_evento('work_order_update', {...})
   ↓
4. event_log.append(evento)         ✅ Funciona
   ↓
5. replay_buffer.add_event(evento)  ❌ Problema (buffer=None)
   ↓
6. volcar_replay_a_archivo()        ❌ Buffer vacío
```

---

## 🐛 BUGS CONOCIDOS Y WORKAROUNDS

### 🔴 CRÍTICO: replay_buffer vacío

**Síntoma:**
```
[REPLAY DEBUG] replay_buffer len: 0
[REPLAY WARNING] No replay data to save (buffer empty or missing)
```

**Causa:**
`AlmacenMejorado.replay_buffer` es `None` cuando se llama `registrar_evento()`.

**Estado:** Debugging activo, logs habilitados en:
- `src/subsystems/simulation/warehouse.py:152-153` (init)
- `src/subsystems/simulation/warehouse.py:444-449` (registrar_evento)
- `src/engines/simulation_engine.py:1393-1395` (finally)

**Workaround:** Ninguno. Sistema funciona pero no genera `.jsonl`.

**Fix estimado:** 30-60 minutos.

---

### 🟡 MEDIO: Error en analytics

**Síntoma:**
```
Error exportando metricas JSON: exportar_metricas() takes 1 positional argument but 2 were given
Error en pipeline de analiticas: 'event_type'
```

**Impacto:** No se generan archivos JSON/XLSX de métricas.

**Workaround:** Analytics falla pero simulación continúa normalmente.

**Fix sugerido:**
- `src/engines/analytics_engine.py`: Revisar firma de `exportar_metricas()`
- Cambiar `evento['event_type']` a `evento.get('type') or evento.get('event_type', 'unknown')`

---

## 📊 SALIDAS DEL SISTEMA

### Archivos Generados (Esperados):

```
output/simulation_20251008_193000/
├── replay_20251008_193000.jsonl              ❌ No se genera (bug)
├── raw_events_20251008_193000.json           ✅ Se genera
├── simulacion_completada_20251008_193000.json  ❌ No se genera (analytics)
├── metricas_20251008_193000.xlsx             ❌ No se genera (analytics)
└── dashboard_screenshot_20251008_193000.png  ⚠️ Solo en modo visual
```

### Formato de replay_YYYYMMDD_HHMMSS.jsonl:

```jsonl
{"type":"SIMULATION_START","timestamp":0.0,"config":{...}}
{"type":"work_order_update","timestamp":125.5,"id":"WO-0001","status":"completed",...}
{"type":"work_order_update","timestamp":142.3,"id":"WO-0002","status":"completed",...}
...
{"type":"SIMULATION_END","timestamp":4907.0,"summary":{...}}
```

**Cada línea:** Un evento en formato JSON  
**Tipos de eventos:**
- `SIMULATION_START` - Inicio de simulación
- `work_order_update` - Actualización de WorkOrder
- `agent_state` - Estado de operario (FASE 2, pendiente)
- `SIMULATION_END` - Fin de simulación

---

## 🧪 TESTING

### Test Rápido:
```bash
python test_quick_jsonl.py
```

**Propósito:** Debugging rápido con 3 órdenes  
**Duración:** 20-40 segundos  
**Output:** Reporte en consola + archivos en `output/`

### Test Completo:
```bash
python entry_points/run_live_simulation.py --headless
```

**Propósito:** Simulación completa de 50 órdenes  
**Duración:** 1-3 minutos  
**Output:** Archivos en `output/`

### Verificación de Archivos:
```powershell
# Listar archivos generados
Get-ChildItem output/simulation_*/ | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-ChildItem

# Inspeccionar .jsonl
Get-Content output/simulation_*/replay_*.jsonl | Select-Object -First 5

# Contar líneas
(Get-Content output/simulation_*/replay_*.jsonl).Count
```

---

## 🔍 DEBUGGING

### Logs Importantes:

**Inicialización:**
```
[ALMACEN DEBUG] __init__ replay_buffer: ReplayBuffer(events=0)
```

**Durante Ejecución:**
```
[REPLAY DEBUG] Evento agregado al buffer: work_order_update, total: 1
[REPLAY ERROR] replay_buffer is None at registrar_evento!
```

**Al Finalizar:**
```
[REPLAY DEBUG] replay_buffer len: 609
[REPLAY] Generating replay file: output/simulation_YYYYMMDD_HHMMSS/replay_YYYYMMDD_HHMMSS.jsonl
[REPLAY] Replay file generated successfully: 609 events
```

### Variables de Entorno:

```bash
# Modo headless sin ventanas
export SDL_VIDEODRIVER=dummy

# Debug de pygame
export PYGAME_DEBUG=1
```

---

## 📚 DOCUMENTACIÓN ADICIONAL

- `ACTIVE_SESSION_STATE.md` - Estado actual del debugging
- `HANDOFF.md` - Overview completo del proyecto
- `AUDITORIA_JSONL_GENERATION.md` - Diagnóstico inicial
- `PLAN_REPARACION_JSONL.md` - Plan de reparación
- `PROBLEMA_BUCLE_INFINITO.md` - Análisis bucle infinito (RESUELTO)
- `ANALISIS_PROBLEMA_REAL.md` - Problema buffer vacío (EN PROGRESO)
- `INSTRUCCIONES_TESTING_FINAL.md` - Guía de testing

---

## 🚨 REGLAS OBLIGATORIAS

### AL INICIAR SESIÓN:
1. Leer `ACTIVE_SESSION_STATE.md`
2. Leer `HANDOFF.md`
3. Ejecutar `git status`
4. Ejecutar `git log --oneline -3`

### DURANTE LA SESIÓN:
- Actualizar `ACTIVE_SESSION_STATE.md` al completar fases
- Documentar problemas encontrados
- No commitear con logs de debug activos
- Verificar que código usa solo caracteres ASCII

### AL FINALIZAR SESIÓN:
- Actualizar `ACTIVE_SESSION_STATE.md`
- Actualizar `HANDOFF.md`
- Actualizar `INSTRUCCIONES.md` si cambió algo técnico
- Ejecutar checklist de validación

---

## 📞 SOPORTE

**Para nueva sesión de debugging:**
1. Leer documentación en orden: ACTIVE_SESSION_STATE → HANDOFF → INSTRUCCIONES
2. Ejecutar `python test_quick_jsonl.py`
3. Analizar logs de `[REPLAY ERROR]` y `[REPLAY DEBUG]`
4. Revisar stacktrace para identificar flujo
5. Implementar fix
6. Validar con test completo

**Archivos críticos para modificar:**
- `src/subsystems/simulation/warehouse.py` (registrar_evento)
- `src/engines/simulation_engine.py` (finally block)
- `src/shared/buffer.py` (ReplayBuffer)

---

**Última Actualización:** 2025-10-08 19:40 UTC  
**Autor:** AI Assistant (Claude Sonnet 4.5)  
**Estado:** Sistema funcional con 1 bug en resolución
