# 🎨 REFERENCIA DE TILES - WAREHOUSE TILESET

## Tileset Maestro para Diseño de Almacenes

Este documento describe todos los tiles disponibles en el tileset maestro para diseñar layouts de almacén.

## 📋 LISTA COMPLETA DE TILES

| ID | Nombre | Descripción | Navegable | Tipo |
|----|--------|-------------|-----------|------|
| 0 | **Floor_Walkable** | Suelo navegable normal | ✅ | `floor` |
| 1 | **Rack_Obstacle** | Rack de almacén (obstáculo) | ❌ | `rack` |
| 2 | **Picking_Point** | Punto de picking | ✅ | `picking` |
| 3 | **Depot_Zone** | Zona de depot/estacionamiento | ✅ | `depot` |
| 4 | **Inbound_Zone** | Zona de entrada/inbound | ✅ | `inbound` |
| 5 | **Wall_Blocked** | Muro/zona prohibida | ❌ | `wall` |
| 6 | **Corridor_Main** | Pasillo principal (más rápido) | ✅ | `corridor` |
| 7 | **Workstation** | Estación de trabajo | ✅ | `workstation` |
| 8 | **Emergency_Exit** | Salida de emergencia | ✅ | `emergency` |
| 9 | **Loading_Dock** | Muelle de carga | ✅ | `loading` |
| 10 | **Office_Area** | Área de oficinas | ❌ | `office` |
| 11 | **Reserved_Future** | Reservado para uso futuro | ❌ | `reserved` |


## 🎯 TILES PRINCIPALES PARA ALMACÉN

### 🚶 TILES NAVEGABLES
- **ID 0 - Floor_Walkable**: Suelo básico por donde pueden moverse los operarios
- **ID 2 - Picking_Point**: Puntos específicos donde se realizan tareas de picking
- **ID 3 - Depot_Zone**: Zona de estacionamiento y descanso de operarios
- **ID 4 - Inbound_Zone**: Zona de recepción de mercancías
- **ID 6 - Corridor_Main**: Pasillos principales (movimiento más rápido)

### 🚫 TILES OBSTÁCULOS
- **ID 1 - Rack_Obstacle**: Racks de almacén (no navegables)
- **ID 5 - Wall_Blocked**: Muros y paredes
- **ID 10 - Office_Area**: Áreas de oficina (acceso restringido)

### 🔧 TILES ESPECIALES
- **ID 7 - Workstation**: Estaciones de trabajo con equipamiento
- **ID 9 - Loading_Dock**: Muelles de carga para camiones
- **ID 8 - Emergency_Exit**: Salidas de emergencia

## 📏 ESPECIFICACIONES TÉCNICAS

- **Tamaño de tile**: 32x32 pixels
- **Formato**: PNG con transparencia
- **Grid**: 4 columnas × 3 filas
- **Total tiles**: 12 tiles únicos

## 🎨 CÓDIGO DE COLORES

Cada tile tiene un color distintivo para facilitar su identificación:

- 🟫 **Marrón**: Racks y obstáculos sólidos
- 🟢 **Verde**: Puntos de picking y áreas de trabajo
- 🔵 **Azul**: Zonas de depot y corredores
- 🟠 **Naranja**: Zonas de inbound/entrada
- ⚫ **Gris oscuro**: Muros y áreas bloqueadas
- 🟡 **Amarillo**: Estaciones de trabajo
- 🔴 **Rojo**: Emergencias
- 🟣 **Púrpura**: Muelles de carga

## 💡 CONSEJOS DE USO

1. **Usa Floor_Walkable (ID 0)** como base para toda el área navegable
2. **Coloca Picking_Points (ID 2)** como objetos, no como tiles de fondo
3. **Los Corridors (ID 6)** mejoran la velocidad de movimiento
4. **Siempre deja rutas alternativas** entre zonas importantes
5. **Usa Depot_Zone (ID 3)** cerca de la entrada principal

