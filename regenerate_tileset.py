#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REGENERAR TILESET CON MAPEO CORRECTO
"""

import os
import json
from PIL import Image

def regenerate_custom_tileset():
    """Regenerar tileset con mapeo correcto"""
    
    # Cargar mapeo corregido
    with open('layouts/custom_tileset_mapping.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    tiles_config = mapping['tiles']
    
    print(f"Regenerando tileset con {len(tiles_config)} tiles...")
    
    # Configuración
    tile_size = 32
    tiles_per_row = 4
    rows_needed = (len(tiles_config) + tiles_per_row - 1) // tiles_per_row
    
    tileset_width = tiles_per_row * tile_size
    tileset_height = rows_needed * tile_size
    
    # Crear imagen del tileset
    tileset_image = Image.new('RGBA', (tileset_width, tileset_height), (255, 255, 255, 0))
    
    for i, tile_config in enumerate(tiles_config):
        try:
            # Cargar textura
            texture_path = os.path.join('custom_textures', tile_config["texture_file"])
            user_texture = Image.open(texture_path)
            
            # Redimensionar a 32x32
            if user_texture.size != (tile_size, tile_size):
                user_texture = user_texture.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
            
            # Convertir a RGBA
            if user_texture.mode != 'RGBA':
                user_texture = user_texture.convert('RGBA')
            
            # Calcular posición
            col = i % tiles_per_row
            row = i // tiles_per_row
            x = col * tile_size
            y = row * tile_size
            
            # Pegar en tileset
            tileset_image.paste(user_texture, (x, y))
            
            print(f"  ID {i}: {tile_config['name']} ({tile_config['texture_file']}) -> ({x}, {y})")
            
        except Exception as e:
            print(f"ERROR procesando {tile_config['texture_file']}: {e}")
            continue
    
    # Guardar tileset
    output_path = "layouts/custom_warehouse_tileset.png"
    tileset_image.save(output_path)
    print(f"\nTileset regenerado: {output_path}")
    
    # Regenerar TSX
    tsx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.5" name="custom_warehouse_tileset" tilewidth="32" tileheight="32" tilecount="{len(tiles_config)}" columns="{tiles_per_row}">
 <image source="custom_warehouse_tileset.png" width="{tileset_width}" height="{tileset_height}"/>
'''
    
    # Agregar propiedades para cada tile
    for tile_config in tiles_config:
        tile_id = tile_config["id"]
        tsx_content += f' <tile id="{tile_id}">\n'
        tsx_content += '  <properties>\n'
        tsx_content += f'   <property name="walkable" value="{str(tile_config["walkable"]).lower()}"/>\n'
        tsx_content += f'   <property name="type" value="{tile_config["type"]}"/>\n'
        tsx_content += f'   <property name="name" value="{tile_config["name"]}"/>\n'
        tsx_content += f'   <property name="description" value="{tile_config["description"]}"/>\n'
        tsx_content += f'   <property name="custom_texture" value="{tile_config["texture_file"]}"/>\n'
        tsx_content += '  </properties>\n'
        tsx_content += ' </tile>\n'
        
    tsx_content += '</tileset>\n'
    
    # Guardar archivo TSX
    tsx_path = "layouts/custom_warehouse_tileset.tsx"
    with open(tsx_path, 'w', encoding='utf-8') as f:
        f.write(tsx_content)
        
    print(f"Archivo TSX regenerado: {tsx_path}")
    
    # Mostrar mapeo corregido
    print(f"\n{'='*60}")
    print("MAPEO CORREGIDO:")
    print(f"{'='*60}")
    for tile in tiles_config:
        nav_icon = "SI" if tile['walkable'] else "NO"
        print(f"ID {tile['id']}: {tile['name']} ({tile['texture_file']}) - Navegable: {nav_icon}")
    
    print(f"\n{'='*60}")
    print("CONCEPTOS CORREGIDOS:")
    print(f"{'='*60}")
    print("ParckingLot.png = ESTACIONAMIENTO (donde INICIAN los operarios)")
    print("OutboundStage.png = DEPOT (donde DEPOSITAN los productos pickeados)")
    print("InboundStage.png = ENTRADA (donde llega mercancia)")
    print("PickLocation.png = PICKING (donde se paran frente a racks)")
    print("rack.png = RACKS (obstaculos fisicos)")
    print("floor.png = SUELO (navegable)")
    print(f"{'='*60}")

if __name__ == "__main__":
    regenerate_custom_tileset()