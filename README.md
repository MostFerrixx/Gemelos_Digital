# 🏭 Gemelo Digital - Simulador de Almacen

**Version:** 11.0 Complete  
**Estado:** ✅ Produccion  
**Arquitectura:** Headless + Replay  
**Fecha:** Octubre 2025

---

## 🚀 Inicio Rapido

### 1. Servidor Web (Click-and-Run) 🆕
```bash
# Windows - Modo Produccion
start_server.bat         # Iniciar servidor en segundo plano
stop_server.bat          # Detener servidor
restart_server.bat       # Reiniciar servidor
status_server.bat        # Ver estado del servidor

# Modo Desarrollo (con terminal)
python web_prototype/server.py

# Python Manager (Avanzado)
python server_manager.py start --browser  # Iniciar y abrir navegador
python server_manager.py status           # Ver estado
python server_manager.py logs --follow    # Ver logs en tiempo real
```
**URL:** `http://localhost:8000/web_configurator/`

### Características Web 🆕
- **Reinicio Remoto**: Botón "↻ Restart Server" en la interfaz web.
- **Auto-reload**: El servidor se reinicia automáticamente al guardar cambios en el código.
- **Health Check**: Verificación automática de disponibilidad.

### 2. Generar Simulacion (Headless)
```bash
python entry_points/run_generate_replay.py
```
**Genera:** Archivo `.jsonl` + Reportes Excel + Analytics + Heatmap

### 3. Visualizar Replay
```bash
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```
**Muestra:** Visualizacion interactiva con Pygame

### 4. Configurar Simulacion
```bash
python configurator.py
```
**Permite:** Ajustar parametros (operarios, ordenes, estrategias)


---

## 📁 Estructura del Proyecto

```
Gemelos Digital/
├── entry_points/
│   ├── run_generate_replay.py    # Generador headless
│   └── run_replay_viewer.py      # Visualizador de replay
│
├── src/
│   ├── engines/
│   │   ├── event_generator.py    # Motor headless de eventos
│   │   ├── analytics_engine.py   # Motor de analytics
│   │   └── replay_engine.py      # Motor de replay
│   │
│   ├── subsystems/
│   │   ├── simulation/           # Logica de simulacion
│   │   └── visualization/        # Renderizado y UI
│   │
│   ├── core/                     # Configuracion y utilidades
│   ├── analytics/                # Exportacion de reportes
│   └── communication/            # IPC y comunicacion
│
├── data/
│   ├── layouts/                  # Mapas TMX (Tiled)
│   └── themes/                   # Temas de UI
│
├── output/                       # Resultados de simulaciones
│   └── simulation_YYYYMMDD_HHMMSS/
│       ├── replay_*.jsonl        # Eventos de replay
│       ├── simulation_report_*.xlsx
│       └── warehouse_heatmap_*.png
│
└── config.json                   # Configuracion principal
```

---

## 🔧 Configuracion

### Archivo config.json
```json
{
  "numero_ordenes": 30,
  "ground_operators": 2,
  "forklifts": 2,
  "dispatch_strategy": "Ejecucion de Plan (Filtro por Prioridad)",
  "tour_type": "Tour Simple (Un Destino)"
}
```

### Configurador Visual
El configurador incluye:
- ✅ Sistema de slots (multiples configuraciones)
- ✅ Interfaz moderna con tema oscuro
- ✅ Iconos vectoriales profesionales
- ✅ Validacion de parametros
- ✅ Importar/Exportar configuraciones

---

## 📊 Salidas del Sistema

Cada simulacion genera:
1. **`replay_*.jsonl`** - Eventos para replay (2 MB)
2. **`simulation_report_*.xlsx`** - Reporte ejecutivo (43 KB)
3. **`simulation_report_*.json`** - Datos analytics (350 KB)
4. **`raw_events_*.json`** - Eventos sin procesar (1.6 MB)
5. **`warehouse_heatmap_*.png`** - Mapa de calor (2.5 KB)
6. **`simulacion_completada_*.json`** - Metadatos (112 bytes)

---

## 🏗️ Arquitectura

### Flujo de Ejecucion
```
┌─────────────────────────────────┐
│   EventGenerator (Headless)     │
│   • SimPy puro                  │
│   • Captura eventos             │
│   • Genera analytics            │
└───────────┬─────────────────────┘
            │
            ▼
┌─────────────────────────────────┐
│   Archivos de Salida            │
│   • .jsonl (replay)             │
│   • .xlsx (reportes)            │
│   • .png (heatmap)              │
└───────────┬─────────────────────┘
            │
            ▼
┌─────────────────────────────────┐
│   ReplayViewer                  │
│   • Lee .jsonl                  │
│   • Renderiza con Pygame        │
│   • Navegacion temporal         │
└─────────────────────────────────┘
```

### Ventajas de la Arquitectura
- 🚀 **Velocidad:** Sin overhead de rendering en tiempo real
- 🧹 **Simplicidad:** Sin multiproceso complejo
- 🔍 **Debugging:** Eventos persistidos para analisis
- 📊 **Analytics:** Siempre generados automaticamente

---

## 📚 Documentacion

### Archivos Principales
- **`INSTRUCCIONES.md`** - Documentacion tecnica completa
- **`HANDOFF.md`** - Estado del proyecto y changelog
- **`ACTIVE_SESSION_STATE.md`** - Estado de sesion actual

### Documentacion Archivada
- **`archived/`** - Documentacion historica y auditorias

---

## 🛠️ Requisitos

### Python
```bash
pip install -r requirements.txt
```

### Dependencias Principales
- `simpy` - Simulacion de eventos discretos
- `pygame` - Renderizado y visualizacion
- `openpyxl` - Generacion de reportes Excel
- `pytmx` - Lectura de mapas Tiled

---

## 🎯 Caracteristicas

### Simulacion
- ✅ Motor SimPy de eventos discretos
- ✅ Estrategias de despacho configurables
- ✅ Operarios terrestres y montacargas
- ✅ Pathfinding con A*
- ✅ Gestion de WorkOrders

### Analytics
- ✅ Reportes Excel con KPIs
- ✅ Heatmaps de actividad
- ✅ Metricas de rendimiento
- ✅ Exportacion JSON

### Visualizacion
- ✅ Replay interactivo
- ✅ Dashboard world-class
- ✅ Navegacion temporal
- ✅ Controles de reproduccion

---

## 🔄 Changelog

### v11.0 Complete (Octubre 2025)
- ✅ **BREAKING CHANGE:** Eliminada simulacion en tiempo real
- ✅ Nueva arquitectura: Headless + Replay
- ✅ EventGenerator optimizado
- ✅ Sistema de documentacion mejorado
- ✅ Limpieza de codigo y archivos

### v10.x (2025)
- ✅ Sistema de slots de configuracion
- ✅ Dashboard PyQt6 en tiempo real
- ✅ Replay scrubber con navegacion temporal
- ✅ Correccion de calculos de tiempo

---

## 📧 Contacto

**Proyecto:** Gemelo Digital de Almacen  
**Repository:** https://github.com/MostFerrixx/Gemelos_Digital  
**Fecha:** Octubre 2025

---

## 📜 Licencia

Este proyecto es de uso interno y academico.

---

**¡Listo para simular tu almacen! 🚀**

