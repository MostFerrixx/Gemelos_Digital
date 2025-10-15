# INSTRUCCIONES TÉCNICAS DEL SISTEMA

**Proyecto:** Simulador de Gemelo Digital de Almacén  
**Versión:** V11 Complete  
**Última Actualización:** 2025-01-14
**Estado:** ✅ Sistema completamente funcional

---

## 🚀 INICIO RÁPIDO

### Ejecutar Simulación Visual:
```bash
python entry_points/run_live_simulation.py
# O: make sim-visual
```

### Ejecutar Simulación Headless (sin GUI):
```bash
python entry_points/run_live_simulation.py --headless
# O: make sim
```

### Ejecutar Test Rápido:
```bash
python test_quick_jsonl.py
# O: make test
```

### Ejecutar Configurador con Sistema de Slots:
```bash
python configurator.py
# O: make config
```

### Ver Replay de Simulación:
```bash
python entry_points/run_replay_viewer.py output/simulation_YYYYMMDD_HHMMSS/replay_events_YYYYMMDD_HHMMSS.jsonl
# O: make replay FILE=output/simulation_YYYYMMDD_HHMMSS/replay_events_YYYYMMDD_HHMMSS.jsonl
```

**NOTA:** Se ha creado un Makefile para comandos convenientes. Ejecuta `make help` para ver todas las opciones disponibles.

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
│   │       ├── dashboard_world_class.py # Dashboard World-Class
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
│       ├── replay_events_YYYYMMDD_HHMMSS.jsonl      # Archivo de replay
│       ├── raw_events_YYYYMMDD_HHMMSS.json         # Eventos sin procesar
│       └── simulation_report_YYYYMMDD_HHMMSS.xlsx   # Reporte ejecutivo
│
├── config.json                      # Configuración principal
├── config_test_quick.json           # Config para testing (3 órdenes)
└── test_quick_jsonl.py              # Script de test rápido
```

---

## 🔧 SISTEMA DE SLOTS DE CONFIGURACIÓN

### Estado Actual: 100% Funcional
El sistema de slots permite gestionar múltiples configuraciones con metadatos completos, iconos vectoriales profesionales y tema oscuro moderno.

### Funcionalidades:
- ✅ **Save:** Guarda configuraciones con metadatos completos
- ✅ **Load:** Carga configuraciones existentes
- ✅ **Use:** Aplica configuración de slots a config.json
- ✅ **Manage:** Gestiona configuraciones (eliminar, listar)
- ✅ **Default:** Carga configuración marcada como default
- ✅ **Iconos Vectoriales:** 8 iconos profesionales generados con Pillow
- ✅ **Tema Oscuro:** Sistema completo de alternancia claro/oscuro

---

## 🎨 DASHBOARD WORLD-CLASS

### Estado Actual: FASE 8 COMPLETADA AL 100%

**Archivo principal:** `src/subsystems/visualization/dashboard_world_class.py`

### Características Implementadas:
- ✅ Panel izquierdo de 440px de ancho
- ✅ Diseño moderno con gradientes y sombras
- ✅ Renderizado con Pygame nativo (sin pygame_gui)
- ✅ Tema cargado desde JSON (`data/themes/dashboard_theme.json`)
- ✅ Fuentes profesionales y jerarquía visual
- ✅ Métricas en tiempo real
- ✅ Cards con diseño profesional
- ✅ Barra de progreso con gradiente
- ✅ Lista de operarios con scroll
- ✅ Footer con controles de teclado

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
│       └─ replay_buffer.add()     │
│  - Sin GUI, máxima velocidad     │
└─────────────────────────────────┘
```

---

## 📊 SALIDAS DEL SISTEMA

### Archivos Generados:
```
output/simulation_20251008_140900/
├── replay_events_20251008_140900.jsonl              # Se genera (7.6MB)
├── raw_events_20251008_140900.json                 # Se genera (4.3MB)
├── simulacion_completada_20251008_140900.json       # Se genera (112 bytes)
├── simulation_report_20251008_140900.xlsx           # Se genera (40KB)
└── dashboard_screenshot_20251008_140900.png         # Solo en modo visual
```

### Formato de replay_events_YYYYMMDD_HHMMSS.jsonl:
```jsonl
{"type":"SIMULATION_START","timestamp":0.0,"config":{...}}
{"type":"work_order_update","timestamp":125.5,"id":"WO-0001","status":"completed",...}
{"type":"estado_agente","timestamp":126.0,"agent_id":"GroundOp-01","data":{...}}
...
{"type":"SIMULATION_END","timestamp":4919.5,"summary":{...}}
```

---

## 🧪 TESTING

### Test Rápido:
```bash
python test_quick_jsonl.py
```
**Propósito:** Verificación rápida con 3 órdenes  
**Duración:** 20-40 segundos  
**Output:** Reporte en consola + archivos en `output/`

### Test Completo:
```bash
python entry_points/run_live_simulation.py --headless
```
**Propósito:** Simulación completa de 50 órdenes  
**Duración:** 1-3 minutos  
**Output:** Archivos en `output/`

---

## 🔍 DEBUGGING

### Logs Importantes:

**Generación exitosa:**
```
[REPLAY] Generating replay file: output\simulation_YYYYMMDD_HHMMSS\replay_events_YYYYMMDD_HHMMSS.jsonl
[VOLCADO-REFACTOR] Usando ReplayBuffer con 17684 eventos
[REPLAY-EXPORT] Volcando 581 work_order_update + 17103 estado_agente de 17684 total
[REPLAY-BUFFER] 17684 eventos guardados en output\simulation_YYYYMMDD_HHMMSS\replay_events_YYYYMMDD_HHMMSS.jsonl
[REPLAY] Replay file generated successfully: 17684 events
```

**Simulación completada:**
```
[ALMACEN] Simulacion finalizada en t=4919.50
[ALMACEN] WorkOrders completadas: 581
[GroundOp-01] Simulacion finalizada, saliendo...
```

---

## 📚 DOCUMENTACIÓN ESENCIAL

- `ACTIVE_SESSION_STATE.md` - Estado actual de la sesión
- `HANDOFF.md` - Overview completo del proyecto
- `INSTRUCCIONES.md` - Este archivo

---

## 🚨 REGLAS OBLIGATORIAS

### AL INICIAR SESIÓN:
1. Leer `ACTIVE_SESSION_STATE.md`
2. Leer `HANDOFF.md`
3. Leer `INSTRUCCIONES.md`
4. Ejecutar `git status`
5. Ejecutar `git log --oneline -3`

### DURANTE LA SESIÓN:
- Sistema completamente funcional
- Documentación actualizada
- Código usa solo caracteres ASCII

### AL FINALIZAR SESIÓN:
- Sistema sigue siendo funcional
- Documentación actualizada si es necesario
- Git status verificado

---

## 📞 SOPORTE

**Para nueva sesión:**
1. Leer documentación en orden: ACTIVE_SESSION_STATE → HANDOFF → INSTRUCCIONES
2. Ejecutar `python test_quick_jsonl.py` para verificar funcionamiento
3. Usar `python entry_points/run_replay_viewer.py` para visualizar simulaciones

**Archivos críticos para uso:**
- `test_quick_jsonl.py` - Test rápido
- `entry_points/run_live_simulation.py` - Simulación completa
- `entry_points/run_replay_viewer.py` - Visualizador
- `output/simulation_*/replay_events_*.jsonl` - Archivos generados

---

**Última Actualización:** 2025-01-14  
**Estado:** ✅ Sistema completamente funcional