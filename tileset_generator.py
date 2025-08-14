#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GENERADOR DE TILESET MAESTRO - Crear tileset.png para Tiled
"""

import pygame
import os
import json

class TilesetGenerator:
    """Generador de tileset visual para uso en Tiled"""
    
    def __init__(self):
        pygame.init()
        
        # Configuración del tileset
        self.tile_size = 32  # Tamaño estándar para Tiled
        self.tileset_cols = 4
        self.tileset_rows = 3
        
        # Crear surface del tileset
        tileset_width = self.tileset_cols * self.tile_size
        tileset_height = self.tileset_rows * self.tile_size
        self.tileset_surface = pygame.Surface((tileset_width, tileset_height))
        self.tileset_surface.fill((255, 255, 255))  # Fondo blanco
        
        # Definir tiles con sus propiedades
        self.tiles_definition = {
            0: {
                'name': 'Floor_Walkable',
                'color': (240, 240, 240),  # Gris claro
                'properties': {'walkable': 'true', 'type': 'floor', 'speed_modifier': '1.0'},
                'description': 'Suelo navegable normal'
            },
            1: {
                'name': 'Rack_Obstacle',
                'color': (101, 67, 33),  # Marrón oscuro
                'properties': {'walkable': 'false', 'type': 'rack', 'height': '3'},
                'description': 'Rack de almacén (obstáculo)'
            },
            2: {
                'name': 'Picking_Point',
                'color': (0, 200, 0),  # Verde brillante
                'properties': {'walkable': 'true', 'type': 'picking', 'priority': 'high'},
                'description': 'Punto de picking'
            },
            3: {
                'name': 'Depot_Zone',
                'color': (0, 100, 200),  # Azul
                'properties': {'walkable': 'true', 'type': 'depot', 'capacity': '10'},
                'description': 'Zona de depot/estacionamiento'
            },
            4: {
                'name': 'Inbound_Zone',
                'color': (200, 100, 0),  # Naranja
                'properties': {'walkable': 'true', 'type': 'inbound', 'dock_count': '2'},
                'description': 'Zona de entrada/inbound'
            },
            5: {
                'name': 'Wall_Blocked',
                'color': (50, 50, 50),  # Gris oscuro
                'properties': {'walkable': 'false', 'type': 'wall', 'blocking': 'true'},
                'description': 'Muro/zona prohibida'
            },
            6: {
                'name': 'Corridor_Main',
                'color': (200, 200, 255),  # Azul claro
                'properties': {'walkable': 'true', 'type': 'corridor', 'speed_modifier': '1.2'},
                'description': 'Pasillo principal (más rápido)'
            },
            7: {
                'name': 'Workstation',
                'color': (255, 200, 100),  # Amarillo
                'properties': {'walkable': 'true', 'type': 'workstation', 'equipment': 'scanner'},
                'description': 'Estación de trabajo'
            },
            8: {
                'name': 'Emergency_Exit',
                'color': (255, 0, 0),  # Rojo
                'properties': {'walkable': 'true', 'type': 'emergency', 'exit': 'true'},
                'description': 'Salida de emergencia'
            },
            9: {
                'name': 'Loading_Dock',
                'color': (128, 0, 128),  # Púrpura
                'properties': {'walkable': 'true', 'type': 'loading', 'truck_capacity': '1'},
                'description': 'Muelle de carga'
            },
            10: {
                'name': 'Office_Area',
                'color': (255, 255, 150),  # Amarillo claro
                'properties': {'walkable': 'false', 'type': 'office', 'restricted': 'true'},
                'description': 'Área de oficinas'
            },
            11: {
                'name': 'Reserved_Future',
                'color': (180, 180, 180),  # Gris medio
                'properties': {'walkable': 'false', 'type': 'reserved', 'future_use': 'true'},
                'description': 'Reservado para uso futuro'
            }
        }
    
    def draw_tile(self, tile_id, x, y):
        """Dibujar un tile específico"""
        tile_info = self.tiles_definition[tile_id]
        
        # Calcular posición en el tileset
        tile_x = x * self.tile_size
        tile_y = y * self.tile_size
        
        # Crear rectángulo del tile
        tile_rect = pygame.Rect(tile_x, tile_y, self.tile_size, self.tile_size)
        
        # Rellenar con color base
        pygame.draw.rect(self.tileset_surface, tile_info['color'], tile_rect)
        
        # Agregar borde negro
        pygame.draw.rect(self.tileset_surface, (0, 0, 0), tile_rect, 2)
        
        # Agregar texto identificativo
        font = pygame.font.Font(None, 16)
        text = font.render(str(tile_id), True, (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.topleft = (tile_x + 2, tile_y + 2)
        self.tileset_surface.blit(text, text_rect)
        
        # Agregar indicador visual según tipo
        self._add_tile_indicator(tile_id, tile_x, tile_y)
    
    def _add_tile_indicator(self, tile_id, tile_x, tile_y):
        """Agregar indicadores visuales específicos por tipo de tile"""
        tile_info = self.tiles_definition[tile_id]
        tile_type = tile_info['properties'].get('type', '')
        
        center_x = tile_x + self.tile_size // 2
        center_y = tile_y + self.tile_size // 2
        
        if tile_type == 'picking':
            # Cruz verde para picking
            pygame.draw.line(self.tileset_surface, (0, 150, 0), 
                           (center_x - 8, center_y), (center_x + 8, center_y), 3)
            pygame.draw.line(self.tileset_surface, (0, 150, 0), 
                           (center_x, center_y - 8), (center_x, center_y + 8), 3)
        
        elif tile_type == 'depot':
            # Círculo azul para depot
            pygame.draw.circle(self.tileset_surface, (0, 150, 200), 
                             (center_x, center_y), 8, 2)
        
        elif tile_type == 'rack':
            # Líneas para simular estantes
            for i in range(3):
                y_line = tile_y + 8 + i * 6
                pygame.draw.line(self.tileset_surface, (60, 40, 20), 
                               (tile_x + 4, y_line), (tile_x + self.tile_size - 4, y_line), 2)
        
        elif tile_type == 'wall':
            # Patrón de ladrillos
            brick_height = 4
            for row in range(0, self.tile_size, brick_height * 2):
                for col in range(0, self.tile_size, 8):
                    offset = 4 if (row // (brick_height * 2)) % 2 else 0
                    pygame.draw.rect(self.tileset_surface, (30, 30, 30), 
                                   (tile_x + col + offset, tile_y + row, 6, brick_height))
        
        elif tile_type == 'corridor':
            # Flechas direccionales para indicar flujo
            arrow_points = [
                (center_x - 6, center_y - 3),
                (center_x + 6, center_y),
                (center_x - 6, center_y + 3)
            ]
            pygame.draw.polygon(self.tileset_surface, (150, 150, 200), arrow_points)
    
    def generate_tileset_image(self, output_path="tilesets/warehouse_tileset.png"):
        """Generar imagen del tileset"""
        
        print("Generando tileset maestro...")
        
        # Dibujar todos los tiles
        tile_id = 0
        for row in range(self.tileset_rows):
            for col in range(self.tileset_cols):
                if tile_id < len(self.tiles_definition):
                    self.draw_tile(tile_id, col, row)
                    tile_id += 1
        
        # Guardar imagen
        pygame.image.save(self.tileset_surface, output_path)
        print(f"Tileset guardado: {output_path}")
        
        return output_path
    
    def generate_tileset_tsx(self, image_path, output_path="tilesets/warehouse_tileset.tsx"):
        """Generar archivo .tsx de Tiled con propiedades"""
        
        print("Generando archivo TSX para Tiled...")
        
        tsx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.5" name="warehouse_tileset" tilewidth="{self.tile_size}" tileheight="{self.tile_size}" tilecount="{len(self.tiles_definition)}" columns="{self.tileset_cols}">
 <image source="{os.path.basename(image_path)}" width="{self.tileset_cols * self.tile_size}" height="{self.tileset_rows * self.tile_size}"/>
'''
        
        # Agregar propiedades para cada tile
        for tile_id, tile_info in self.tiles_definition.items():
            tsx_content += f' <tile id="{tile_id}">\n'
            tsx_content += '  <properties>\n'
            
            for prop_name, prop_value in tile_info['properties'].items():
                tsx_content += f'   <property name="{prop_name}" value="{prop_value}"/>\n'
            
            # Agregar nombre y descripción
            tsx_content += f'   <property name="name" value="{tile_info["name"]}"/>\n'
            tsx_content += f'   <property name="description" value="{tile_info["description"]}"/>\n'
            
            tsx_content += '  </properties>\n'
            tsx_content += ' </tile>\n'
        
        tsx_content += '</tileset>\n'
        
        # Guardar archivo TSX
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tsx_content)
        
        print(f"Archivo TSX guardado: {output_path}")
        
        return output_path
    
    def generate_tiles_reference(self, output_path="docs/TILES_REFERENCE.md"):
        """Generar documentación de referencia de tiles"""
        
        print("Generando documentación de tiles...")
        
        md_content = '''# 🎨 REFERENCIA DE TILES - WAREHOUSE TILESET

## Tileset Maestro para Diseño de Almacenes

Este documento describe todos los tiles disponibles en el tileset maestro para diseñar layouts de almacén.

## 📋 LISTA COMPLETA DE TILES

| ID | Nombre | Descripción | Navegable | Tipo |
|----|--------|-------------|-----------|------|
'''
        
        for tile_id, tile_info in self.tiles_definition.items():
            walkable = "✅" if tile_info['properties'].get('walkable') == 'true' else "❌"
            tile_type = tile_info['properties'].get('type', 'unknown')
            
            md_content += f"| {tile_id} | **{tile_info['name']}** | {tile_info['description']} | {walkable} | `{tile_type}` |\n"
        
        md_content += '''

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

'''
        
        # Crear directorio docs si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"Documentación guardada: {output_path}")
        
        return output_path
    
    def generate_complete_tileset(self):
        """Generar tileset completo con todos los archivos"""
        
        print("="*60)
        print("GENERADOR DE TILESET MAESTRO")
        print("="*60)
        
        # Crear directorio tilesets si no existe
        os.makedirs("tilesets", exist_ok=True)
        
        # 1. Generar imagen del tileset
        image_path = self.generate_tileset_image()
        
        # 2. Generar archivo TSX
        tsx_path = self.generate_tileset_tsx(image_path)
        
        # 3. Generar documentación
        docs_path = self.generate_tiles_reference()
        
        # 4. Generar archivo JSON con metadata
        metadata = {
            'tileset_info': {
                'name': 'warehouse_tileset',
                'tile_size': self.tile_size,
                'columns': self.tileset_cols,
                'rows': self.tileset_rows,
                'total_tiles': len(self.tiles_definition)
            },
            'tiles': self.tiles_definition
        }
        
        metadata_path = "tilesets/tileset_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"Metadata guardado: {metadata_path}")
        
        print(f"\n{'='*60}")
        print("TILESET COMPLETO GENERADO")
        print("="*60)
        print(f"📁 Imagen: {image_path}")
        print(f"📁 TSX: {tsx_path}")
        print(f"📁 Docs: {docs_path}")
        print(f"📁 Metadata: {metadata_path}")
        
        return {
            'image': image_path,
            'tsx': tsx_path,
            'docs': docs_path,
            'metadata': metadata_path
        }

def main():
    """Generar tileset completo"""
    
    generator = TilesetGenerator()
    files = generator.generate_complete_tileset()
    
    print(f"\n🎉 TILESET LISTO PARA USAR EN TILED")
    print(f"Importa el archivo: {files['tsx']}")
    print(f"Lee la documentación: {files['docs']}")
    
    return generator

if __name__ == "__main__":
    generator = main()