#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTO-CONFIGURADOR DE TEXTURAS - Basado en nombres de archivos
"""

import os
import json
from PIL import Image

def auto_detect_texture_mapping():
    """Auto-detectar texturas basándose en nombres de archivos"""
    
    custom_folder = "custom_textures"
    if not os.path.exists(custom_folder):
        print(f"ERROR: No existe carpeta {custom_folder}")
        return None
    
    # Obtener archivos de texturas
    texture_files = []
    valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tga'}
    
    for file in os.listdir(custom_folder):
        if any(file.lower().endswith(ext) for ext in valid_extensions):
            texture_files.append(file)
    
    if not texture_files:
        print("ERROR: No se encontraron archivos de texturas")
        return None
    
    print(f"Texturas encontradas: {texture_files}")
    
    # Mapeo automático basado en nombres
    auto_mapping = {
        "floor": {
            "keywords": ["floor", "piso", "suelo", "ground"],
            "type": "floor",
            "name": "Suelo navegable",
            "walkable": True,
            "description": "Suelo normal navegable"
        },
        "rack": {
            "keywords": ["rack", "estante", "shelf"],
            "type": "rack", 
            "name": "Racks/Estantes",
            "walkable": False,
            "description": "Racks de almacén (obstáculos)"
        },
        "picking": {
            "keywords": ["pick", "picking", "location"],
            "type": "picking",
            "name": "Puntos de picking", 
            "walkable": True,
            "description": "Ubicaciones de picking frente a racks"
        },
        "parking": {
            "keywords": ["parking", "estacion", "station", "parck"],
            "type": "parking",
            "name": "Zona estacionamiento/inicio",
            "walkable": True, 
            "description": "Zona donde aparecen los operarios al inicio"
        },
        "depot": {
            "keywords": ["depot", "outbound", "despacho", "salida"],
            "type": "depot",
            "name": "Zona depot/depósito",
            "walkable": True, 
            "description": "Zona donde se depositan los productos pickeados"
        },
        "inbound": {
            "keywords": ["inbound", "entrada", "recepcion", "stage"],
            "type": "inbound",
            "name": "Zona entrada/recepción",
            "walkable": True,
            "description": "Zona de entrada de mercancía"
        },
    }
    
    # Detectar automáticamente
    detected_tiles = []
    used_files = set()
    
    for tile_key, tile_info in auto_mapping.items():
        matched_file = None
        
        # Buscar archivo que coincida con keywords
        for file in texture_files:
            if file in used_files:
                continue
                
            file_lower = file.lower()
            for keyword in tile_info["keywords"]:
                if keyword in file_lower:
                    matched_file = file
                    break
            
            if matched_file:
                break
        
        if matched_file:
            detected_tiles.append({
                "id": len(detected_tiles),
                "type": tile_info["type"],
                "name": tile_info["name"],
                "walkable": tile_info["walkable"],
                "description": tile_info["description"],
                "texture_file": matched_file,
                "texture_path": os.path.join(custom_folder, matched_file)
            })
            used_files.add(matched_file)
            print(f"✅ {tile_info['name']}: {matched_file}")
    
    return detected_tiles

def generate_auto_tileset(tiles_config):
    """Generar tileset automáticamente"""
    
    print(f"\nGenerando tileset con {len(tiles_config)} texturas...")
    
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
            texture_path = tile_config["texture_path"]
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
            
            print(f"  Tile {i}: {tile_config['name']} -> ({x}, {y})")
            
        except Exception as e:
            print(f"ERROR procesando {texture_path}: {e}")
            continue
    
    # Guardar tileset
    output_path = "layouts/custom_warehouse_tileset.png"
    tileset_image.save(output_path)
    print(f"\nTileset guardado: {output_path}")
    
    return output_path

def generate_auto_tsx(tiles_config):
    """Generar archivo TSX automáticamente"""
    
    tile_size = 32
    tiles_per_row = 4
    rows_needed = (len(tiles_config) + tiles_per_row - 1) // tiles_per_row
    
    tsx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.5" name="custom_warehouse_tileset" tilewidth="32" tileheight="32" tilecount="{len(tiles_config)}" columns="{tiles_per_row}">
 <image source="custom_warehouse_tileset.png" width="{tiles_per_row * tile_size}" height="{rows_needed * tile_size}"/>
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
        
    print(f"Archivo TSX generado: {tsx_path}")
    return tsx_path

def save_auto_mapping(tiles_config):
    """Guardar mapeo automático"""
    
    mapping = {
        "tileset_name": "custom_warehouse_tileset",
        "tile_size": 32,
        "auto_generated": True,
        "tiles": []
    }
    
    for tile_config in tiles_config:
        mapping["tiles"].append({
            "id": tile_config["id"],
            "type": tile_config["type"], 
            "walkable": tile_config["walkable"],
            "name": tile_config["name"],
            "description": tile_config["description"],
            "texture_file": tile_config["texture_file"]
        })
    
    mapping_path = "layouts/custom_tileset_mapping.json"
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        
    print(f"Mapeo guardado: {mapping_path}")
    return mapping_path

def main():
    """Auto-configurar texturas personalizadas"""
    
    print("="*60)
    print("AUTO-CONFIGURADOR DE TEXTURAS PERSONALIZADAS")
    print("="*60)
    
    # Detectar texturas automáticamente
    tiles_config = auto_detect_texture_mapping()
    
    if not tiles_config:
        print("ERROR: No se pudieron detectar texturas")
        return
    
    print(f"\nDetección automática completada:")
    print(f"Se configuraron {len(tiles_config)} tipos de tiles")
    
    # Generar tileset
    tileset_path = generate_auto_tileset(tiles_config)
    
    # Generar TSX
    tsx_path = generate_auto_tsx(tiles_config)
    
    # Guardar mapeo
    mapping_path = save_auto_mapping(tiles_config)
    
    print("\n" + "="*60)
    print("CONFIGURACIÓN AUTOMÁTICA COMPLETADA")
    print("="*60)
    
    print("Archivos generados:")
    print(f"  - Tileset: {tileset_path}")
    print(f"  - TSX: {tsx_path}")
    print(f"  - Mapeo: {mapping_path}")
    
    print("\nTexturas configuradas:")
    for tile in tiles_config:
        nav_icon = "✅" if tile['walkable'] else "❌"
        print(f"  {nav_icon} {tile['name']}: {tile['texture_file']}")
    
    print("\nAhora puedes:")
    print("1. Ejecutar: python custom_layout_integration.py")
    print("2. Crear layouts en Tiled usando custom_warehouse_tileset.tsx")
    print("3. Usar tus layouts en el simulador")

if __name__ == "__main__":
    main()