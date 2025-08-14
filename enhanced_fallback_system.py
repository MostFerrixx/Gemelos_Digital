#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA FALLBACK MEJORADO - Crear layouts personalizados sin PyTMX
"""

import os
import sys
import json
from pathlib import Path

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def create_enhanced_fallback_layouts():
    """Crear layouts personalizados directamente como fallback"""
    
    print("Creando sistema fallback mejorado...")
    
    # Layout 1: Almacén pequeño con racks organizados
    layout_pequeño = {
        'info': {
            'name': 'Almacen_Pequeño',
            'width': 25,
            'height': 18,
            'tile_width': 32,
            'tile_height': 32,
            'description': 'Almacén pequeño con racks organizados'
        },
        'pattern': 'warehouse_small'
    }
    
    # Layout 2: Almacén grande con múltiples zonas
    layout_grande = {
        'info': {
            'name': 'Almacen_Grande', 
            'width': 35,
            'height': 25,
            'tile_width': 32,
            'tile_height': 32,
            'description': 'Almacén grande con múltiples zonas de picking'
        },
        'pattern': 'warehouse_large'
    }
    
    # Layout 3: Corredor central
    layout_corredor = {
        'info': {
            'name': 'Layout_Corredor_Central',
            'width': 30,
            'height': 20,
            'tile_width': 32,
            'tile_height': 32,
            'description': 'Layout con corredor central principal'
        },
        'pattern': 'central_corridor'
    }
    
    layouts_config = [layout_pequeño, layout_grande, layout_corredor]
    
    # Guardar configuración de layouts
    config_path = "layouts/layouts_personalizados.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(layouts_config, f, indent=2, ensure_ascii=False)
    
    print(f"Configuración de layouts guardada: {config_path}")
    
    return layouts_config

def generate_warehouse_small_matrix(width, height):
    """Generar matriz de almacén pequeño"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            # Bordes como muros
            if y == 0 or y == height-1 or x == 0 or x == width-1:
                tile = 0  # Suelo navegable en bordes
            # Racks en patrón regular
            elif y % 4 == 2 and 2 <= x <= width-3:
                if x % 4 in [1, 2]:
                    tile = 0  # Racks (obstáculos)
                else:
                    tile = 1  # Pasillos entre racks
            # Corredor principal horizontal
            elif y == height // 2:
                tile = 1  # Corredor principal navegable
            # Suelo navegable por defecto
            else:
                tile = 1
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def generate_warehouse_large_matrix(width, height):
    """Generar matriz de almacén grande"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            # Zona de entrada (primeras 3 filas)
            if y < 3:
                tile = 1  # Zona despejada
            # Zona de carga (últimas 3 filas)
            elif y > height - 4:
                tile = 1  # Zona despejada
            # Corredor central
            elif y == height // 2:
                tile = 1  # Corredor principal
            # Racks organizados
            elif (y - 3) % 5 in [1, 2, 3] and 3 <= x <= width-4:
                if x % 6 in [1, 2, 3, 4]:
                    tile = 0  # Racks
                else:
                    tile = 1  # Pasillos
            else:
                tile = 1  # Navegable
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def generate_central_corridor_matrix(width, height):
    """Generar matriz con corredor central"""
    matrix = []
    
    main_corridor_y = height // 2
    main_corridor_x = width // 2
    
    for y in range(height):
        row = []
        for x in range(width):
            # Corredor principal horizontal
            if y == main_corridor_y or y == main_corridor_y - 1:
                tile = 1  # Corredor principal
            # Corredor principal vertical  
            elif x == main_corridor_x or x == main_corridor_x - 1:
                tile = 1  # Corredor principal
            # Racks en cuadrantes
            elif (x % 4 in [1, 2]) and (y % 4 in [1, 2]):
                # Excepto cerca de corredores principales
                if abs(y - main_corridor_y) > 2 and abs(x - main_corridor_x) > 2:
                    tile = 0  # Racks
                else:
                    tile = 1  # Espacio libre cerca de corredores
            else:
                tile = 1  # Navegable
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def patch_dynamic_layout_loader():
    """Parchear el loader para usar layouts mejorados"""
    
    print("Aplicando patch al dynamic layout loader...")
    
    # Leer configuración de layouts
    config_path = "layouts/layouts_personalizados.json"
    if not os.path.exists(config_path):
        print("ERROR: No existe configuración de layouts personalizados")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        layouts_config = json.load(f)
    
    # Crear archivo de patch
    patch_code = '''
# PATCH AUTOMÁTICO PARA DYNAMIC LAYOUT LOADER
import json
import os

def _create_enhanced_fallback_layout(self, tmx_path):
    """Crear layout fallback mejorado basado en configuración"""
    
    # Leer configuración de layouts personalizados
    config_path = "layouts/layouts_personalizados.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            layouts_config = json.load(f)
        
        # Buscar configuración para este layout
        layout_name = os.path.splitext(os.path.basename(tmx_path))[0]
        
        for layout_config in layouts_config:
            if layout_config['info']['name'].lower() in layout_name.lower():
                return self._generate_layout_from_config(layout_config)
    
    # Fallback original si no hay configuración
    return self._create_fallback_layout_original(tmx_path)

def _generate_layout_from_config(self, layout_config):
    """Generar layout desde configuración"""
    
    info = layout_config['info']
    pattern = layout_config['pattern']
    
    # Generar matriz según patrón
    if pattern == 'warehouse_small':
        matrix = self._generate_warehouse_small_matrix(info['width'], info['height'])
    elif pattern == 'warehouse_large':
        matrix = self._generate_warehouse_large_matrix(info['width'], info['height'])
    elif pattern == 'central_corridor':
        matrix = self._generate_central_corridor_matrix(info['width'], info['height'])
    else:
        matrix = [[1 for _ in range(info['width'])] for _ in range(info['height'])]
    
    # Crear ubicaciones especiales basadas en el layout
    special_locations = self._generate_special_locations_for_pattern(pattern, info)
    
    return {
        'info': {
            'name': info['name'],
            'path': '',
            'width': info['width'],
            'height': info['height'],
            'tile_width': info['tile_width'],
            'tile_height': info['tile_height']
        },
        'navigation_matrix': matrix,
        'special_locations': special_locations,
        'tmx_data': None
    }

# Métodos auxiliares para generar matrices
def _generate_warehouse_small_matrix(self, width, height):
    """Generar matriz de almacén pequeño"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            if y == 0 or y == height-1 or x == 0 or x == width-1:
                tile = 1  # Bordes navegables
            elif y % 4 == 2 and 2 <= x <= width-3:
                if x % 4 in [1, 2]:
                    tile = 0  # Racks
                else:
                    tile = 1  # Pasillos
            elif y == height // 2:
                tile = 1  # Corredor principal
            else:
                tile = 1
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def _generate_warehouse_large_matrix(self, width, height):
    """Generar matriz de almacén grande"""
    matrix = []
    
    for y in range(height):
        row = []
        for x in range(width):
            if y < 3 or y > height - 4:
                tile = 1  # Zonas despejadas
            elif y == height // 2:
                tile = 1  # Corredor central
            elif (y - 3) % 5 in [1, 2, 3] and 3 <= x <= width-4:
                if x % 6 in [1, 2, 3, 4]:
                    tile = 0  # Racks
                else:
                    tile = 1  # Pasillos
            else:
                tile = 1
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def _generate_central_corridor_matrix(self, width, height):
    """Generar matriz con corredor central"""
    matrix = []
    
    main_corridor_y = height // 2
    main_corridor_x = width // 2
    
    for y in range(height):
        row = []
        for x in range(width):
            if y == main_corridor_y or y == main_corridor_y - 1:
                tile = 1  # Corredor horizontal
            elif x == main_corridor_x or x == main_corridor_x - 1:
                tile = 1  # Corredor vertical
            elif (x % 4 in [1, 2]) and (y % 4 in [1, 2]):
                if abs(y - main_corridor_y) > 2 and abs(x - main_corridor_x) > 2:
                    tile = 0  # Racks
                else:
                    tile = 1
            else:
                tile = 1
            
            row.append(tile)
        matrix.append(row)
    
    return matrix

def _generate_special_locations_for_pattern(self, pattern, info):
    """Generar ubicaciones especiales según patrón"""
    
    width = info['width']
    height = info['height']
    
    locations = {
        'depot_points': [],
        'inbound_points': [],
        'picking_points': [],
        'workstations': [],
        'emergency_exits': []
    }
    
    # Depot siempre en esquina inferior derecha
    depot_x = (width - 3) * info['tile_width']
    depot_y = (height - 3) * info['tile_height']
    locations['depot_points'].append({
        'tile_pos': (width - 3, height - 3),
        'pixel_pos': (depot_x, depot_y)
    })
    
    # Inbound siempre en esquina superior izquierda
    inbound_x = 2 * info['tile_width']
    inbound_y = 2 * info['tile_height']
    locations['inbound_points'].append({
        'tile_pos': (2, 2),
        'pixel_pos': (inbound_x, inbound_y)
    })
    
    # Picking points distribuidos según patrón
    if pattern == 'warehouse_small':
        for i in range(3):
            x = (5 + i * 6) * info['tile_width']
            y = (6) * info['tile_height']
            locations['picking_points'].append({
                'tile_pos': (5 + i * 6, 6),
                'pixel_pos': (x, y)
            })
    
    elif pattern == 'warehouse_large':
        for i in range(5):
            x = (5 + i * 6) * info['tile_width']
            y = (8) * info['tile_height']
            locations['picking_points'].append({
                'tile_pos': (5 + i * 6, 8),
                'pixel_pos': (x, y)
            })
    
    elif pattern == 'central_corridor':
        # Picking en los 4 cuadrantes
        for qx in [0, 1]:
            for qy in [0, 1]:
                x = (width // 4 + qx * width // 2) * info['tile_width']
                y = (height // 4 + qy * height // 2) * info['tile_height']
                locations['picking_points'].append({
                    'tile_pos': (width // 4 + qx * width // 2, height // 4 + qy * height // 2),
                    'pixel_pos': (x, y)
                })
    
    return locations

# Aplicar patch a DynamicLayoutLoader
from dynamic_layout_loader import DynamicLayoutLoader

# Guardar método original
DynamicLayoutLoader._create_fallback_layout_original = DynamicLayoutLoader._create_fallback_layout

# Reemplazar con versión mejorada
DynamicLayoutLoader._create_enhanced_fallback_layout = _create_enhanced_fallback_layout
DynamicLayoutLoader._generate_layout_from_config = _generate_layout_from_config
DynamicLayoutLoader._generate_warehouse_small_matrix = _generate_warehouse_small_matrix
DynamicLayoutLoader._generate_warehouse_large_matrix = _generate_warehouse_large_matrix
DynamicLayoutLoader._generate_central_corridor_matrix = _generate_central_corridor_matrix
DynamicLayoutLoader._generate_special_locations_for_pattern = _generate_special_locations_for_pattern

# Reemplazar método de fallback
DynamicLayoutLoader._create_fallback_layout = _create_enhanced_fallback_layout

print("[PATCH] Sistema fallback mejorado aplicado")
'''
    
    # Guardar patch
    patch_path = "layouts/fallback_patch.py"
    with open(patch_path, 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    print(f"Patch guardado: {patch_path}")
    print("Para aplicar el patch, importar este archivo antes de usar el loader")
    
    return True

def main():
    """Crear sistema fallback mejorado"""
    
    print("=" * 60)
    print("SISTEMA FALLBACK MEJORADO")
    print("=" * 60)
    
    # Crear configuración de layouts
    layouts_config = create_enhanced_fallback_layouts()
    
    # Crear patch
    patch_dynamic_layout_loader()
    
    print("\n" + "=" * 60)
    print("SISTEMA FALLBACK MEJORADO CREADO")
    print("=" * 60)
    print("Layouts personalizados disponibles:")
    for layout in layouts_config:
        info = layout['info']
        print(f"  - {info['name']}: {info['width']}x{info['height']} ({info['description']})")
    
    print(f"\nAhora cuando PyTMX falle, el sistema usará layouts")
    print(f"personalizados en lugar del fallback genérico.")
    print(f"Los operarios verán layouts diferentes y únicos.")
    print("=" * 60)

if __name__ == "__main__":
    main()