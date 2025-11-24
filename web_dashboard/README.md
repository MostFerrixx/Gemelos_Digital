# Web Dashboard - Digital Twin Warehouse

Dashboard web para visualizar work orders en tiempo real durante el replay de simulaciones.

## Características

- ✅ Tabla con 18 columnas de datos de work orders
- ✅ Coloración por estado (Released/Assigned/In Progress/Staged)
- ✅ Sorting interactivo (click en headers)
- ✅ Time scrubber para navegar en el replay
- ✅ Controles de playback (Play/Pause/Reset)
- ✅ Métricas en tiempo real
- ✅ Tema oscuro profesional
- ✅ Diseño responsive

## Inicio Rápido

```bash
# Desde el directorio raíz del proyecto
cd "c:\Users\ferri\OneDrive\Escritorio\Gemelos Digital"

# Ejecutar el servidor
python web_dashboard/server.py
```

El dashboard estará disponible en: **http://localhost:8001**

## Comparación con PyQt6

Este dashboard replica la funcionalidad del dashboard PyQt6 (`src/subsystems/visualization/work_order_dashboard.py`) con las siguientes equivalencias:

| PyQt6 | Web |
|-------|-----|
| QTableView | HTML Table |
| QAbstractTableModel | JavaScript Map |
| QSlider | HTML range input |
| IPC Queue | REST API |
| Port N/A | Port 8001 |

## Estructura de Archivos

```
web_dashboard/
├── index.html    # Estructura HTML del dashboard
├── style.css     # Estilos (colores PyQt6, tema oscuro)
├── app.js        # Lógica JavaScript (tabla, sorting, scrubbing)
└── server.py     # Servidor FastAPI con endpoints REST
```

## Endpoints API

- `GET /` - Dashboard web (index.html)
- `GET /api/state?t={timestamp}` - Estado de work orders en tiempo t
- `GET /api/metrics?t={timestamp}` - Métricas agregadas
- `GET /api/info` - Información del replay

## Uso

1. **Navegar en el tiempo**: Arrastra el slider de tiempo
2. **Ordenar datos**: Click en cualquier header de columna
3. **Reproducir**: Click en "Play" para replay automático
4. **Ajustar velocidad**: Usa el selector de velocidad (0.5x - 10x)

## Datos de Replay

El dashboard carga datos desde:
```
output/simulation_20251120_224852/replay_20251120_224852.jsonl
```

Para usar un archivo de replay diferente, modifica la variable `REPLAY_FILE` en `server.py`.

## Diferencias con web_prototype

- **web_prototype** (puerto 8000): Visualización de mapa 2D con agentes
- **web_dashboard** (puerto 8001): Tabla de work orders con análisis

Ambos pueden ejecutarse simultáneamente.

## Requisitos

- Python 3.8+
- FastAPI
- Uvicorn

Instalados via `requirements.txt` del proyecto principal.

---

**Nota**: Este dashboard es la versión web del dashboard PyQt6 de replay. Para el dashboard en vivo durante simulaciones, ver el plan de implementación para agregar soporte WebSocket.
