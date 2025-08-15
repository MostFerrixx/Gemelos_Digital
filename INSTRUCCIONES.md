# Simulador de Almacén - Gemelo Digital v1.0-stable

## Instalación y Configuración

### Requisitos Previos
- Python 3.8+
- pygame
- simpy
- pytmx
- numpy

### Instalación Rápida

1. **Clonar el repositorio:**
```bash
git clone [URL_DEL_REPOSITORIO]
cd gemelos-digital-warehouse
```

2. **Instalar dependencias:**
```bash
pip install pygame simpy pytmx numpy
```

3. **Verificar instalación:**
```bash
python test_environment_sync.py
```
Debe mostrar el mensaje "*** EJECUTANDO CÓDIGO NUEVO ***"

4. **Ejecutar simulador:**
```bash
python run_simulator.py
```

## Arquitectura TMX Unificada

### Características Principales
- **Sistema TMX obligatorio:** Sin fallback a sistema legacy
- **Correspondencia 1:1:** Píxel TMX = píxel pantalla (sin escalado)
- **Coordenadas centradas:** Los operarios se posicionan en el centro de los tiles
- **Matriz de colisión corregida:** Lee propiedades walkable='true'/'false' del TMX
- **Navegación funcional:** Los operarios no atraviesan racks ni van a (0,0)

### Archivos Principales

#### Core del Sistema
- `run_simulator.py` - Ejecutor principal con verificación de entorno
- `git/simulation/layout_manager.py` - Gestión TMX y matriz de colisión
- `git/simulation/pathfinder.py` - Sistema de pathfinding A*
- `git/visualization/original_renderer.py` - Renderizado sin escalado

#### Layout TMX
- `layouts/WH1.tmx` - Layout de almacén principal (30x30, 32x32px tiles)
- `layouts/custom_warehouse_tileset.tsx` - Tileset personalizado

### Controles del Simulador
- **ESPACIO:** Pausa/Reanuda
- **R:** Reiniciar simulación  
- **M:** Mostrar métricas en consola
- **X:** Exportar datos a JSON
- **D:** Toggle dashboard
- **+/-:** Aumentar/disminuir velocidad
- **ESC:** Salir

### Pruebas Disponibles

#### Verificación de Entorno
```bash
python test_environment_sync.py
```
Verifica que se ejecute el código corregido.

#### Pruebas TMX
```bash
python test_tmx_corrections.py
```
Valida matriz de colisión, depot y pathfinding.

#### Pruebas de Renderizado
```bash
python test_renderizado_corregido.py
```
Verifica el renderizado sin escalado.

## Resolución de Problemas

### Cache Obsoleto
Si encuentras comportamiento antiguo:
```bash
# Limpiar cache Python
find . -name "*.pyc" -delete
find . -name "__pycache__" -exec rm -rf {} +

# O en Windows:
del /s *.pyc
for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"
```

### Errores Comunes

**Error: "cannot convert without pygame.display initialized"**
- Solución: pygame.init() se llama automáticamente en crear_simulacion()

**Error: "center argument must be a pair of numbers"**  
- Solución: Escalado legacy eliminado, usa correspondencia 1:1

**Operarios en (0,0) o atravesando racks**
- Solución: Matriz de colisión y depot corregidos en v1.0

### Configuración de Ventana
La ventana se dimensiona automáticamente según el TMX:
- WH1.tmx: 30x30 tiles × 32x32px = 960x960px
- Sin escalado, correspondencia directa 1:1

## Changelog v1.0-stable

### Nuevas Características
✅ Sistema TMX unificado obligatorio  
✅ Coordenadas centradas en tiles  
✅ Matriz de colisión lee propiedades TMX  
✅ Validación estricta de depot  
✅ Renderizado sin escalado  
✅ Navegación funcional sin atravesar obstáculos  

### Eliminado
❌ Sistema legacy de layout  
❌ Fallback a coordenadas predefinidas  
❌ Escalado automático de ventana  
❌ Detección de modo visual  

### Archivos de Diagnóstico Removidos
Se eliminaron ~80 archivos de prueba y diagnóstico de versiones anteriores para mantener el repositorio limpio.

## Estructura del Proyecto
```
gemelos-digital-warehouse/
├── run_simulator.py              # Ejecutor principal
├── layouts/
│   ├── WH1.tmx                   # Layout principal
│   └── custom_warehouse_tileset.tsx
├── git/
│   ├── simulation/
│   │   ├── layout_manager.py     # Gestión TMX
│   │   ├── pathfinder.py         # Pathfinding A*
│   │   ├── warehouse.py          # Lógica de almacén
│   │   └── operators.py          # Operarios
│   ├── visualization/
│   │   ├── original_renderer.py  # Renderizado
│   │   └── state.py              # Estado visual
│   └── config/
│       ├── settings.py           # Configuración
│       └── colors.py             # Colores
├── test_*.py                     # Pruebas de verificación
└── INSTRUCCIONES.md              # Este archivo
```

---
**Versión:** v1.0-stable  
**Fecha:** 2024  
**Estado:** Producción estable