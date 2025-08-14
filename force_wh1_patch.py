#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PARCHE FORZADO PARA WH1 - Reemplazar fallback genérico completamente
"""

import os
import sys
import json

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def force_wh1_as_default():
    """Forzar WH1 como el layout por defecto para CUALQUIER selección"""
    
    print("[FORCE WH1] Aplicando parche forzado...")
    
    # Datos de WH1 parseados manualmente
    wh1_data = parse_wh1_manual()
    
    if not wh1_data:
        print("[FORCE WH1] ERROR: No se pudo parsear WH1")
        return False
    
    try:
        from dynamic_layout_loader import DynamicLayoutLoader
        
        # REEMPLAZAR COMPLETAMENTE el método _create_fallback_layout
        def _create_fallback_layout_wh1(self, tmx_path):
            """Fallback que SIEMPRE retorna WH1, sin importar qué layout se seleccione"""
            
            print(f"[FORCE WH1] Interceptado: {tmx_path} -> Forzando WH1")
            
            return {
                'info': {
                    'name': 'WH1_FORZADO',
                    'path': tmx_path,  # Mantener path original
                    'width': 30,
                    'height': 30,
                    'tile_width': 32,
                    'tile_height': 32
                },
                'navigation_matrix': wh1_data['navigation_matrix'],
                'special_locations': wh1_data['special_locations'],
                'tmx_data': None
            }
        
        # REEMPLAZAR COMPLETAMENTE el método load_layout
        def load_layout_wh1_forced(self, tmx_path):
            """Cargar layout que SIEMPRE retorna WH1"""
            
            print(f"[FORCE WH1] Carga interceptada: {tmx_path}")
            
            # Siempre retornar WH1, sin importar qué TMX se pida
            return _create_fallback_layout_wh1(self, tmx_path)
        
        # Aplicar parches
        DynamicLayoutLoader._create_fallback_layout = _create_fallback_layout_wh1
        DynamicLayoutLoader.load_layout = load_layout_wh1_forced
        
        print("[FORCE WH1] Parche forzado aplicado - TODOS los layouts serán WH1")
        return True
        
    except Exception as e:
        print(f"[FORCE WH1] ERROR: {e}")
        return False

def parse_wh1_manual():
    """Parsear WH1.tmx manualmente (copia del método anterior)"""
    
    wh1_path = "layouts/WH1.tmx"
    if not os.path.exists(wh1_path):
        return None
    
    # Leer archivo TMX
    with open(wh1_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
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
    
    # Cargar mapeo personalizado
    with open('layouts/custom_tileset_mapping.json', 'r', encoding='utf-8') as f:
        tileset_mapping = json.load(f)
    
    # Crear diccionario de tiles
    tile_map = {}
    for tile in tileset_mapping['tiles']:
        tile_map[tile['id'] + 1] = tile  # TMX usa IDs 1-indexed
    
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
                nav_row.append(1)  # Navegable por defecto
        navigation_matrix.append(nav_row)
    
    # Crear ubicaciones especiales
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
    
    return {
        'navigation_matrix': navigation_matrix,
        'special_locations': special_locations
    }

# Auto-aplicar parche al importar
force_wh1_as_default()
print("[FORCE WH1] Sistema interceptado - WH1 será usado SIEMPRE")