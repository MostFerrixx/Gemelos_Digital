# HANDOFF - Digital Twin Warehouse Simulator

**Proyecto:** Simulador de Gemelo Digital de Almacen  
**Rama:** `main`  
**Estado:** ✅ Sistema completamente funcional (Headless + Replay)  
**Ultima Actualizacion:** 2025-10-27

---

## 📋 RESUMEN EJECUTIVO

Sistema de simulacion de almacen completamente funcional con **Generador de Eventos Headless**, **Sistema de Slots de Configuracion**, **Replay Viewer** y **Analytics Engine** implementados al 100%.

**CAMBIO ARQUITECTONICO IMPORTANTE (2025-10-27):**
- ✅ Eliminada simulacion en tiempo real (live simulation)
- ✅ Arquitectura simplificada: Generacion headless → Visualizacion replay
- ✅ Sistema mas eficiente, sin overhead de renderizado en tiempo real

### ✅ FUNCIONALIDADES COMPLETADAS

- **Simulación:** Ejecuta y completa correctamente
- **Dashboard World-Class:** Implementado (Fases 1-8 completadas)
- **Sistema de Slots:** 100% funcional con modernización UI
- **Replay Scrubber:** Operarios móviles tras retroceder
- **Dashboard PyQt6:** Comunicación inter-proceso en tiempo real
- **Solución Holística:** Estado autoritativo con navegación temporal
- **Cálculos de Tiempo:** Corregidos y validados en Excel
- **Generación de Archivos:** .jsonl, .xlsx, .json funcionando
- **Nomenclatura de Estados:** Actualizada (completed → staged, pending → released)

### ⚠️ CAMBIO IMPORTANTE: NOMENCLATURA DE ESTADOS WO

**Estados de Work Orders actualizados:**
- `pending` → `released` (estado inicial de WO)
- `completed` → `staged` (estado final de WO, preparado para despacho)

Todos los archivos del sistema han sido actualizados para reflejar esta nueva nomenclatura.

### ❌ PROBLEMA PENDIENTE

**Estrategias de Despacho:** Los operarios no respetan `pick_sequence` desde la WO 1. Problema sistémico independiente de la estrategia elegida.

---

## 🚀 COMANDOS PRINCIPALES

### Generar Eventos (Headless):
```bash
python entry_points/run_generate_replay.py
```

### Visualizar Replay:
```bash
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

### Configurador:
```bash
python configurator.py
```

**NOTA:** La simulacion en tiempo real ha sido eliminada.  
Flujo actual: `EventGenerator` (headless) → Archivo `.jsonl` → `ReplayViewer`

---

## 📁 ESTRUCTURA DEL PROYECTO

```
src/
├── engines/
│   ├── event_generator.py           # Motor headless de eventos
│   ├── analytics_engine.py          # Motor de analisis
│   └── replay_engine.py             # Motor de replay
├── subsystems/
│   ├── simulation/
│   │   ├── warehouse.py             # Almacen
│   │   ├── dispatcher.py            # Despachador
│   │   └── operators.py             # Operarios
│   └── visualization/
│       ├── dashboard_world_class.py # Dashboard World-Class
│       ├── renderer.py              # Renderizado
│       └── state.py                 # Estado visual
└── shared/
    └── buffer.py                    # ReplayBuffer

Archivos principales:
├── configurator.py                  # Sistema de slots
├── config.json                      # Configuración principal
└── output/                          # Resultados
    └── simulation_YYYYMMDD_HHMMSS/
        ├── replay_events_*.jsonl    # Archivo de replay
        ├── raw_events_*.json       # Eventos sin procesar
        └── simulation_report_*.xlsx  # Reporte ejecutivo
```

---

## 🔄 CAMBIO ARQUITECTONICO: ELIMINACION DE LIVE SIMULATION (2025-10-27)

### Archivos Eliminados:
- ❌ `entry_points/run_live_simulation.py` - Entry point de simulacion en tiempo real
- ❌ `src/engines/simulation_engine.py` - Motor de simulacion con rendering
- ❌ `src/communication/simulation_data_provider.py` - Proveedor de datos para dashboard en tiempo real

### Archivos Creados:
- ✅ `src/engines/event_generator.py` - Motor headless puro de generacion de eventos
- ✅ `entry_points/run_generate_replay.py` - Entry point headless para generar .jsonl

### Archivos Modificados:
- ✅ `Makefile` - Comandos actualizados (sim → genera replay)
- ✅ `run.bat` - Scripts actualizados para Windows
- ✅ `src/communication/__init__.py` - Eliminadas referencias a simulation_data_provider

### Razon del Cambio:
La simulacion en tiempo real introducia complejidad innecesaria con multiproceso, Pygame en tiempo real y comunicacion IPC compleja. La nueva arquitectura simplificada:
1. **Genera eventos:** EventGenerator ejecuta simulacion SimPy pura (headless)
2. **Exporta .jsonl:** Todos los eventos capturados en archivo de replay
3. **Visualiza:** ReplayViewer reproduce eventos con Pygame
4. **Analytics:** Reportes Excel/JSON/heatmap generados automaticamente

**Ventajas:**
- 🚀 Mayor velocidad (sin overhead de rendering)
- 🧹 Codigo mas simple (sin multiproceso)
- 🔍 Mejor debugging (eventos persistidos)
- 📊 Analytics completos (siempre generados)

---

## 🔧 CONFIGURACION

### config.json (Default):
- 30 órdenes
- 2 operarios terrestres
- 2 montacargas
- Estrategia: "Ejecución de Plan (Filtro por Prioridad)"
- Tour Type: "Tour Simple (Un Destino)"

---

## 📊 SALIDAS DEL SISTEMA

### Archivos Generados:
```
output/simulation_YYYYMMDD_HHMMSS/
├── replay_events_*.jsonl              # 7.6MB - Eventos de replay
├── raw_events_*.json                 # 4.3MB - Eventos sin procesar
├── simulation_report_*.xlsx           # 40KB - Reporte ejecutivo
└── simulacion_completada_*.json       # 112 bytes - Resumen
```

---

## 🧪 USO DEL SISTEMA

### Ejecutar Simulación:
```bash
python entry_points/run_live_simulation.py --headless
```
**Duración:** 1-3 minutos  
**Output:** Archivos en `output/`

### Ver Replay:
```bash
python entry_points/run_replay_viewer.py output/simulation_*/replay_events_*.jsonl
```

---

## 📚 DOCUMENTACIÓN

- `ACTIVE_SESSION_STATE.md` - Estado actual de la sesión
- `HANDOFF.md` - Este archivo
- `INSTRUCCIONES.md` - Instrucciones técnicas

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
2. Ejecutar `python entry_points/run_live_simulation.py --headless` para iniciar simulación
3. Usar `python entry_points/run_replay_viewer.py` para visualizar simulaciones

**Archivos críticos:**
- `entry_points/run_live_simulation.py` - Simulación completa
- `entry_points/run_replay_viewer.py` - Visualizador
- `configurator.py` - Sistema de slots
- `config.json` - Configuración principal

---

**Última Actualización:** 2025-01-14  
**Estado:** ✅ Sistema completamente funcional