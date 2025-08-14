# INSTRUCCIONES PARA LAYOUTS PERSONALIZADOS

## Tileset personalizado configurado: custom_warehouse_tileset

### Tiles disponibles:

**ID 0**: Suelo navegable 🚶
  - Tipo: floor
  - Navegable: Sí
  - Descripción: Suelo normal por donde pueden caminar los operarios
  - Textura: floor.png

**ID 1**: Racks/Estantes 🚫
  - Tipo: rack
  - Navegable: No
  - Descripción: Racks de almacén (obstáculos)
  - Textura: rack.png

**ID 2**: Puntos de picking 🚶
  - Tipo: picking
  - Navegable: Sí
  - Descripción: Ubicaciones de picking frente a racks
  - Textura: PickLocation.png

**ID 3**: Zona estacionamiento/inicio 🚶
  - Tipo: parking
  - Navegable: Sí
  - Descripción: Zona donde aparecen los operarios al inicio
  - Textura: ParckingLot.png

**ID 4**: Zona depot/depósito 🚶
  - Tipo: depot
  - Navegable: Sí
  - Descripción: Zona donde se depositan los productos pickeados
  - Textura: OutboundStage.png

**ID 5**: Zona entrada/recepción 🚶
  - Tipo: inbound
  - Navegable: Sí
  - Descripción: Zona de entrada de mercancía
  - Textura: InboundStage.png


### Cómo crear tu layout en Tiled:

1. **Abrir Tiled**
2. **Nuevo mapa**: File > New Map
   - Orientación: Orthogonal
   - Tile size: 32x32
   - Map size: El tamaño que prefieras
3. **Importar tileset**: Map > Add External Tileset
   - Seleccionar: `layouts/custom_warehouse_tileset.tsx`
4. **Pintar tu layout**:
   - Usar tiles navegables para pasillos
   - Usar tiles obstáculo para racks/paredes
   - Usar tiles especiales para depot, inbound, picking
5. **Guardar**: File > Save As... en carpeta `layouts/`

### Ejemplo de uso de tiles:

- **Pasillos principales**: Usar tiles tipo 'corridor' o 'floor'
- **Racks de almacén**: Usar tiles tipo 'rack' 
- **Paredes**: Usar tiles tipo 'wall'
- **Zona depot**: Usar tiles tipo 'depot'
- **Zona entrada**: Usar tiles tipo 'inbound'

### Objetos especiales (opcional):

Crear una **Object Layer** y agregar:
- 1 objeto "depot" en la zona de depot
- 1 objeto "inbound" en la zona de entrada  
- Varios objetos "picking" en puntos de interés

¡Tu layout personalizado estará listo para usar en el simulador!
