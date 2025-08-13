# Simulador de Almacén - Gemelo Digital

## Sistema de Navegación Inteligente v2.0

### 🚀 Ejecución Rápida

```bash
cd "C:\Users\ferri\OneDrive\Escritorio\Gemelos Digital"
python run_simulator.py
```

### 🎮 Controles Durante la Simulación

| Tecla | Función |
|-------|---------|
| **ESPACIO** | Pausa/Reanuda |
| **R** | Reiniciar simulación |
| **M** | Mostrar métricas en consola |
| **X** | Exportar datos a JSON |
| **D** | Toggle dashboard |
| **+/-** | Aumentar/Disminuir velocidad |
| **N** | 🆕 Diagnóstico navegación |
| **C** | 🆕 Diagnóstico colisiones |
| **F1** | 🆕 Toggle modo debug |
| **ESC** | Salir |

### ✨ Nuevas Características

- **Sin colisiones**: Los operarios ya no se atraviesan
- **Esquiva inteligente**: Cambios de carril automáticos
- **Rutas adaptativas**: Recalculación dinámica
- **Movimiento realista**: Sin teleportación
- **Diagnósticos en tiempo real**

### 📁 Estructura del Proyecto

```
Gemelos Digital/
├── run_simulator.py          ← ARCHIVO PRINCIPAL
├── git/
│   ├── config/               ← Configuraciones
│   ├── simulation/           ← Lógica de simulación  
│   ├── utils/                ← Sistema navegación inteligente
│   ├── visualization/        ← Renderizado
│   ├── CLAUDE.md            ← Config para Claude
│   └── NAVEGACION_INTELIGENTE.md ← Documentación
└── README.md                ← Este archivo
```

### 🛠️ Requisitos

- Python 3.8+
- SimPy: `pip install simpy`
- Pygame: `pip install pygame`

### 📊 Monitoreo

Durante la simulación, presiona **N** para ver estadísticas como:

```
=== ESTADÍSTICAS DE NAVEGACIÓN ===
Puntos válidos totales: 2847
Conexiones totales: 8456
Puntos ocupados: 12
Operarios activos: 4

✓ No se detectó congestión

POSICIONES DE OPERARIOS:
  Operario 1 (traspaleta): (245, 180) - Picking Piso L1
  Operario 2 (traspaleta): (890, 220) - → Rack 8-A
```

---

**Versión**: 2.0 | **Fecha**: Agosto 2025