#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GENERADOR DE TILESET PERSONALIZADO - Usar texturas del usuario
"""

import os
import sys
import json
from PIL import Image
from pathlib import Path

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

class CustomTilesetGenerator:
    """Generador de tileset usando texturas personalizadas del usuario"""
    
    def __init__(self):
        self.custom_textures_folder = "custom_textures"
        self.output_folder = "layouts"
        self.tile_size = 32
        self.tiles_config = []
        
    def setup_textures_folder(self):
        """Crear carpeta para texturas personalizadas"""
        if not os.path.exists(self.custom_textures_folder):
            os.makedirs(self.custom_textures_folder)
            print(f"Carpeta creada: {self.custom_textures_folder}")
            print("Coloca aqui tus imagenes de texturas (PNG, JPG, etc.)")
        
        return self.custom_textures_folder
        
    def configure_tile_properties(self):
        """Configurar propiedades para cada tipo de tile"""
        
        print("\n" + "="*60)
        print("CONFIGURACION DE TEXTURAS PERSONALIZADAS")
        print("="*60)
        
        # Tipos de tiles que necesitamos
        tile_types = [
            {
                "type": "floor",
                "name": "Suelo navegable",
                "walkable": True,
                "description": "Suelo normal por donde pueden caminar los operarios",
                "required": True
            },
            {
                "type": "rack", 
                "name": "Racks/Estantes",
                "walkable": False,
                "description": "Racks de almacen (obstaculos)",
                "required": True
            },
            {
                "type": "corridor",
                "name": "Pasillos principales", 
                "walkable": True,
                "description": "Pasillos principales (navegacion rapida)",
                "required": False
            },
            {
                "type": "wall",
                "name": "Muros/Paredes",
                "walkable": False, 
                "description": "Muros y paredes (obstaculos)",
                "required": False
            },
            {
                "type": "depot",
                "name": "Zona depot/estacionamiento",
                "walkable": True,
                "description": "Zona donde aparecen los operarios",
                "required": True
            },
            {
                "type": "inbound", 
                "name": "Zona de entrada/recepcion",
                "walkable": True,
                "description": "Zona de entrada de mercancia",
                "required": True
            },
            {
                "type": "picking",
                "name": "Puntos de picking",
                "walkable": True,
                "description": "Ubicaciones especificas de picking",
                "required": True
            },
            {
                "type": "workstation",
                "name": "Estaciones de trabajo", 
                "walkable": True,
                "description": "Estaciones especiales de trabajo",
                "required": False
            }
        ]
        
        # Mostrar archivos disponibles
        texture_files = self.scan_texture_files()
        if not texture_files:
            print("ERROR: No se encontraron archivos de texturas")
            print(f"Coloca tus imagenes en: {self.custom_textures_folder}")
            return False
            
        print(f"\nArchivos de texturas encontrados en {self.custom_textures_folder}:")
        for i, file in enumerate(texture_files):
            print(f"  {i+1}. {file}")
            
        print(f"\nAsigna cada archivo a un tipo de tile:")
        print("(Ingresa el numero del archivo, o 0 para omitir)")
        
        # Configurar cada tipo de tile
        configured_tiles = []
        for tile_info in tile_types:
            print(f"\n--- {tile_info['name']} ---")
            print(f"Descripcion: {tile_info['description']}")
            print(f"Navegable: {'SI' if tile_info['walkable'] else 'NO'}")
            
            if tile_info['required']:
                print("(REQUERIDO)")
            
            while True:
                try:
                    choice = input(f"Archivo para '{tile_info['name']}' (1-{len(texture_files)}, 0=omitir): ")
                    choice = int(choice)
                    
                    if choice == 0:
                        if tile_info['required']:
                            print("ERROR: Este tipo de tile es requerido")
                            continue
                        else:
                            break
                    elif 1 <= choice <= len(texture_files):
                        file_path = texture_files[choice-1]
                        configured_tiles.append({
                            "id": len(configured_tiles),
                            "type": tile_info["type"],
                            "name": tile_info["name"],
                            "walkable": tile_info["walkable"],
                            "description": tile_info["description"],
                            "texture_file": file_path,
                            "texture_path": os.path.join(self.custom_textures_folder, file_path)
                        })
                        print(f"Asignado: {file_path} -> {tile_info['name']}")
                        break
                    else:
                        print("Numero invalido")
                        
                except ValueError:
                    print("Ingresa un numero valido")
        
        self.tiles_config = configured_tiles
        return len(configured_tiles) > 0
        
    def scan_texture_files(self):
        """Escanear archivos de texturas en la carpeta"""
        if not os.path.exists(self.custom_textures_folder):
            return []
            
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tga'}
        texture_files = []
        
        for file in os.listdir(self.custom_textures_folder):
            if any(file.lower().endswith(ext) for ext in valid_extensions):
                texture_files.append(file)
                
        return sorted(texture_files)
        
    def generate_custom_tileset_image(self):
        """Generar imagen de tileset usando texturas personalizadas"""
        
        if not self.tiles_config:
            print("ERROR: No hay configuracion de tiles")
            return None
            
        print(f"\nGenerando tileset con {len(self.tiles_config)} texturas...")
        
        # Calcular dimensiones del tileset
        tiles_per_row = 4
        rows_needed = (len(self.tiles_config) + tiles_per_row - 1) // tiles_per_row
        
        tileset_width = tiles_per_row * self.tile_size
        tileset_height = rows_needed * self.tile_size
        
        # Crear imagen del tileset
        tileset_image = Image.new('RGBA', (tileset_width, tileset_height), (255, 255, 255, 0))
        
        for i, tile_config in enumerate(self.tiles_config):
            try:
                # Cargar textura del usuario
                texture_path = tile_config["texture_path"]
                if not os.path.exists(texture_path):
                    print(f"WARNING: No existe {texture_path}")
                    continue
                    
                user_texture = Image.open(texture_path)
                
                # Redimensionar a 32x32 si es necesario
                if user_texture.size != (self.tile_size, self.tile_size):
                    user_texture = user_texture.resize((self.tile_size, self.tile_size), Image.Resampling.LANCZOS)
                
                # Convertir a RGBA si es necesario
                if user_texture.mode != 'RGBA':
                    user_texture = user_texture.convert('RGBA')
                
                # Calcular posicion en el tileset
                col = i % tiles_per_row
                row = i // tiles_per_row
                x = col * self.tile_size
                y = row * self.tile_size
                
                # Pegar textura en el tileset
                tileset_image.paste(user_texture, (x, y))
                
                print(f"  Tile {i}: {tile_config['name']} -> ({x}, {y})")
                
            except Exception as e:
                print(f"ERROR procesando {texture_path}: {e}")
                continue
        
        # Guardar tileset
        output_path = os.path.join(self.output_folder, "custom_warehouse_tileset.png")
        tileset_image.save(output_path)
        print(f"\nTileset guardado: {output_path}")
        
        return output_path
        
    def generate_custom_tsx_file(self, tileset_image_path):
        """Generar archivo TSX para Tiled usando texturas personalizadas"""
        
        tsx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.5" name="custom_warehouse_tileset" tilewidth="32" tileheight="32" tilecount="{}" columns="4">
 <image source="custom_warehouse_tileset.png" width="{}" height="{}"/>
'''.format(len(self.tiles_config), 4 * self.tile_size, ((len(self.tiles_config) + 3) // 4) * self.tile_size)
        
        # Agregar propiedades para cada tile
        for tile_config in self.tiles_config:
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
        tsx_path = os.path.join(self.output_folder, "custom_warehouse_tileset.tsx")
        with open(tsx_path, 'w', encoding='utf-8') as f:
            f.write(tsx_content)
            
        print(f"Archivo TSX generado: {tsx_path}")
        return tsx_path
        
    def save_tileset_mapping(self):
        """Guardar mapeo de tiles para el sistema"""
        
        mapping = {
            "tileset_name": "custom_warehouse_tileset",
            "tile_size": self.tile_size,
            "tiles": []
        }
        
        for tile_config in self.tiles_config:
            mapping["tiles"].append({
                "id": tile_config["id"],
                "type": tile_config["type"], 
                "walkable": tile_config["walkable"],
                "name": tile_config["name"],
                "description": tile_config["description"],
                "texture_file": tile_config["texture_file"]
            })
        
        mapping_path = os.path.join(self.output_folder, "custom_tileset_mapping.json")
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
            
        print(f"Mapeo guardado: {mapping_path}")
        return mapping_path
        
    def generate_complete_custom_tileset(self):
        """Generar tileset personalizado completo"""
        
        print("="*60)
        print("GENERADOR DE TILESET PERSONALIZADO")
        print("="*60)
        
        # Configurar carpeta de texturas
        textures_folder = self.setup_textures_folder()
        
        # Verificar si hay texturas
        texture_files = self.scan_texture_files()
        if not texture_files:
            print(f"\nPASO 1: Coloca tus imagenes de texturas en: {textures_folder}")
            print("PASO 2: Ejecuta este script nuevamente")
            return None
            
        # Configurar propiedades
        if not self.configure_tile_properties():
            print("ERROR: Configuracion cancelada")
            return None
            
        # Generar tileset
        tileset_path = self.generate_custom_tileset_image()
        if not tileset_path:
            print("ERROR: No se pudo generar el tileset")
            return None
            
        # Generar TSX
        tsx_path = self.generate_custom_tsx_file(tileset_path)
        
        # Guardar mapeo
        mapping_path = self.save_tileset_mapping()
        
        print("\n" + "="*60)
        print("TILESET PERSONALIZADO COMPLETADO")
        print("="*60)
        print(f"Archivos generados:")
        print(f"  - Tileset: {tileset_path}")
        print(f"  - TSX: {tsx_path}")
        print(f"  - Mapeo: {mapping_path}")
        print(f"\nAhora puedes usar estos archivos en Tiled:")
        print(f"1. Abrir Tiled")
        print(f"2. Importar tileset: {tsx_path}")
        print(f"3. Crear tu layout")
        print(f"4. Guardarlo en layouts/")
        print("="*60)
        
        return {
            "tileset": tileset_path,
            "tsx": tsx_path, 
            "mapping": mapping_path
        }

def main():
    """Generar tileset personalizado"""
    generator = CustomTilesetGenerator()
    result = generator.generate_complete_custom_tileset()
    
    if result:
        print("\nTILESET PERSONALIZADO LISTO!")
    else:
        print("\nCOLOCA TUS TEXTURAS Y EJECUTA NUEVAMENTE")

if __name__ == "__main__":
    main()