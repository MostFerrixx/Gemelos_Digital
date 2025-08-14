#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PARCHE ESPECÍFICO PARA WH1.TMX - Forzar lectura correcta
"""

import os
import sys
import json

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def parse_wh1_manually():
    """Leer WH1.tmx manualmente sin PyTMX"""
    
    wh1_path = "layouts/WH1.tmx"
    if not os.path.exists(wh1_path):
        print("ERROR: No existe WH1.tmx")
        return None
    
    print("Parseando WH1.tmx manualmente...")
    
    # Leer archivo TMX
    with open(wh1_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraer dimensiones
    if 'width="30" height="30"' in content:
        width, height = 30, 30
        print(f"Dimensiones detectadas: {width}x{height}")
    else:
        print("ERROR: No se pudieron detectar dimensiones")
        return None
    
    # Extraer datos CSV
    csv_start = content.find('<data encoding="csv">') + len('<data encoding="csv">')
    csv_end = content.find('</data>')
    csv_data = content[csv_start:csv_end].strip()
    
    # Procesar CSV
    rows = []
    for line in csv_data.split('\n'):
        if line.strip():
            row = [int(x.strip()) for x in line.split(',') if x.strip()]
            rows.append(row)
    
    print(f"Filas procesadas: {len(rows)}")
    
    # Cargar mapeo personalizado
    with open('layouts/custom_tileset_mapping.json', 'r', encoding='utf-8') as f:
        tileset_mapping = json.load(f)
    
    # Crear diccionario de tiles
    tile_map = {}
    for tile in tileset_mapping['tiles']:
        # TMX usa IDs 1-indexed, nuestro mapeo es 0-indexed
        tile_map[tile['id'] + 1] = tile
    
    print(f"Tiles mapeados: {list(tile_map.keys())}")
    
    # Convertir a matriz de navegación
    navigation_matrix = []
    for y, row in enumerate(rows):
        nav_row = []
        for x, tile_id in enumerate(row):
            if tile_id in tile_map:
                tile_info = tile_map[tile_id]
                nav_value = 1 if tile_info['walkable'] else 0
                nav_row.append(nav_value)
            else:
                # Tile desconocido, asumir navegable
                nav_row.append(1)
        navigation_matrix.append(nav_row)
    
    # Calcular estadísticas
    total_tiles = width * height
    walkable_tiles = sum(sum(row) for row in navigation_matrix)
    walkable_pct = (walkable_tiles / total_tiles) * 100
    
    print(f"Matriz generada: {walkable_tiles}/{total_tiles} navegables ({walkable_pct:.1f}%)")
    
    # Crear ubicaciones especiales basadas en los tiles
    special_locations = {
        'depot_points': [],
        'inbound_points': [],
        'picking_points': [],
        'parking_points': []
    }
    
    for y, row in enumerate(rows):
        for x, tile_id in enumerate(row):
            if tile_id in tile_map:
                tile_info = tile_map[tile_id]
                tile_type = tile_info['type']
                
                pixel_x = x * 32
                pixel_y = y * 32
                
                if tile_type == 'depot':
                    special_locations['depot_points'].append({
                        'tile_pos': (x, y),
                        'pixel_pos': (pixel_x, pixel_y)
                    })
                elif tile_type == 'inbound':
                    special_locations['inbound_points'].append({
                        'tile_pos': (x, y),
                        'pixel_pos': (pixel_x, pixel_y)
                    })
                elif tile_type == 'picking':
                    special_locations['picking_points'].append({
                        'tile_pos': (x, y),
                        'pixel_pos': (pixel_x, pixel_y)
                    })
                elif tile_type == 'parking':
                    special_locations['parking_points'].append({
                        'tile_pos': (x, y),
                        'pixel_pos': (pixel_x, pixel_y)
                    })
    
    print(f"Ubicaciones especiales:")
    for loc_type, locations in special_locations.items():
        print(f"  {loc_type}: {len(locations)} ubicaciones")
    
    return {
        'info': {
            'name': 'WH1',
            'path': wh1_path,
            'width': width,
            'height': height,
            'tile_width': 32,
            'tile_height': 32
        },
        'navigation_matrix': navigation_matrix,
        'special_locations': special_locations,
        'tmx_data': None  # Procesado manualmente
    }

def patch_dynamic_loader_for_wh1():
    """Aplicar parche específico para WH1"""
    
    try:
        from dynamic_layout_loader import DynamicLayoutLoader
        
        # Método específico para WH1
        def _load_wh1_specifically(self, tmx_path):
            """Carga específica para WH1.tmx"""
            
            if 'WH1' in tmx_path:
                print("[WH1 PATCH] Detectado WH1.tmx - usando parser manual")
                return parse_wh1_manually()
            else:
                # Usar método original para otros layouts
                return self._load_layout_original(tmx_path)
        
        # Guardar método original si no existe
        if not hasattr(DynamicLayoutLoader, '_load_layout_original'):
            DynamicLayoutLoader._load_layout_original = DynamicLayoutLoader.load_layout
        
        # Aplicar parche
        DynamicLayoutLoader.load_layout = _load_wh1_specifically
        
        print("[WH1 PATCH] Parche aplicado para WH1.tmx")
        return True
        
    except Exception as e:
        print(f"ERROR aplicando parche WH1: {e}")
        return False

# Auto-aplicar parche al importar
patch_dynamic_loader_for_wh1()
print("[WH1 PATCH] Parche WH1 aplicado automáticamente")

def main():
    """Aplicar parche WH1"""
    
    print("="*60)
    print("PARCHE ESPECÍFICO PARA WH1.TMX")
    print("="*60)
    
    # Probar parseo manual
    result = parse_wh1_manually()
    if result:
        print("\nWH1.tmx parseado exitosamente")
        
        # Aplicar parche
        if patch_dynamic_loader_for_wh1():
            print("Parche aplicado al dynamic loader")
            
            print("\nAhora ejecuta el simulador y selecciona WH1")
            print("Debería mostrar tu layout personalizado")
        else:
            print("Error aplicando parche")
    else:
        print("Error parseando WH1.tmx")
    
    print("="*60)

if __name__ == "__main__":
    main()