# TUTORIAL LAYOUT - EXPLICACIÓN DE TILES

Este layout tutorial muestra cómo usar cada tile del warehouse_tileset:

## MAPA VISUAL DEL LAYOUT (25x18):

```
Azul Claro = Pasillo perimetral rápido (ID 6)
Naranja   = Zona entrada/inbound (ID 4)  
Rojo      = Salida emergencia (ID 8)
Amarillo  = Estación trabajo (ID 7)
Verde     = Racks con picking (ID 2)
Gris      = Suelo navegable (ID 0)
Marrón C. = Muelle carga (ID 9)
Azul      = Zona depot (ID 3)
Amar. C.  = Oficinas (ID 10)
Blanco    = Reservado futuro (ID 11)
```

## DISEÑO DEL LAYOUT:

### ZONA SUPERIOR (Entrada):
- **Perimetro Azul Claro**: Pasillos rápidos (+20% velocidad)
- **Esquina Sup. Izq. Naranja**: Zona entrada/inbound  
- **Esquina Sup. Der. Rojo**: Salida de emergencia
- **Tile Amarillo**: Estación de trabajo con scanner

### ZONAS DE PICKING (4 secciones horizontales):
- **Tiles Verde**: Racks con puntos de picking
- **Tiles Gris**: Pasillos navegables entre racks
- **Patrón**: 3 tiles picking + 1 pasillo, repetido
- **4 Secciones**: Distribuidas verticalmente

### PASILLO PRINCIPAL CENTRAL (Fila 8):
- **Línea Amarilla horizontal**: Corredor principal
- **Velocidad aumentada**: 20% más rápido que suelo normal
- **Atraviesa**: Todo el almacén de izquierda a derecha

### ZONA INFERIOR (Salida):
- **Esquina Inf. Izq. Marrón Claro**: Muelle de carga
- **Esquina Inf. Der. Azul**: Zona depot/estacionamiento

### ÁREAS ESPECIALES (Lado derecho):
- **Tiles Amarillo Claro**: Área de oficinas (no navegable)
- **Tiles Blanco**: Zonas reservadas para expansión

## TILES UTILIZADOS Y SUS FUNCIONES:

| **Tile** | **ID** | **Navegable** | **Función** | **Ubicación en Layout** |
|----------|--------|---------------|-------------|-------------------------|
| Gris Claro | 0 | ✅ Sí | Suelo básico | Pasillos entre racks |
| Marrón | 1 | ❌ No | Racks | NO usado (sustituido por verde) |
| Verde | 2 | ✅ Sí | Picking | Secciones de racks principales |
| Azul | 3 | ✅ Sí | Depot | Zona estacionamiento (inf. der.) |
| Naranja | 4 | ✅ Sí | Inbound | Zona entrada (sup. izq.) |
| Gris Oscuro | 5 | ❌ No | Muro | NO usado |
| Azul Claro | 6 | ✅ Sí | Pasillo rápido | Perímetro del layout |
| Amarillo | 7 | ✅ Sí | Workstation | Pasillo central + estación |
| Rojo | 8 | ✅ Sí | Emergencia | Salida emergencia (sup. der.) |
| Marrón Claro | 9 | ✅ Sí | Muelle carga | Zona carga (inf. izq.) |
| Amarillo Claro | 10 | ❌ No | Oficinas | Área administrativa (derecha) |
| Blanco | 11 | ❌ No | Reservado | Expansión futura (derecha) |

## OBJETOS ESPECIALES COLOCADOS:

1. **Main_Depot** (Azul): Estacionamiento principal - 8 operarios
2. **Inbound_Main** (Naranja): Entrada principal - 2 muelles  
3. **Loading_Dock_1** (Marrón Claro): Muelle de carga
4. **Emergency_Exit_1** (Rojo): Salida de emergencia
5. **Workstation_Scanner** (Amarillo): Estación de escaneo
6. **Picking_Zone_A1, A2, B1** (Verde): Zonas picking diferentes prioridades
7. **Office_Area_1** (Amarillo Claro): Área administrativa 
8. **Main_Corridor** (Amarillo): Pasillo central rápido
9. **Future_Expansion** (Blanco): Zona reservada

## FLUJO DE OPERARIOS:

1. **Entrada**: Por zona naranja (inbound)
2. **Picking**: En zonas verdes (4 secciones disponibles)
3. **Movimiento rápido**: Por perímetro azul claro y pasillo central amarillo
4. **Estacionamiento**: En zona azul (depot)
5. **Carga**: En zona marrón claro (loading dock)
6. **Emergencia**: Salida roja disponible

## CARACTERÍSTICAS ESPECIALES:

- **Velocidad optimizada**: Pasillos azul claro y amarillo dan +20% velocidad
- **Múltiples zonas picking**: 4 secciones independientes
- **Flujo eficiente**: Entrada → Picking → Depot → Carga
- **Seguridad**: Salida de emergencia y oficinas separadas
- **Escalabilidad**: Zonas blancas reservadas para expansión

¡Este layout demuestra todas las texturas del tileset en un diseño funcional!