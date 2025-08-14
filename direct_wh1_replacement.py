#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REEMPLAZO DIRECTO - Forzar WH1 modificando archivos directamente
"""

import os
import sys
import json

def create_wh1_matrix():
    """Crear matriz WH1 basada en tu patrón"""
    
    matrix = []
    
    # Fila 0: Mayormente parking/depot
    row0 = [1] * 30
    matrix.append(row0)
    
    # Filas 1-2: Pasillos
    for _ in range(2):
        matrix.append([1] * 30)
    
    # Filas 3-26: Racks y picking alternados
    for y in range(3, 27):
        row = []
        for x in range(30):
            # Patrón: rack, picking, picking, rack, ...
            if x % 3 == 1:  # Racks (obstáculos)
                row.append(0)
            else:  # Picking (navegable)
                row.append(1)
        matrix.append(row)
    
    # Filas 27-28: Pasillos
    for _ in range(2):
        matrix.append([1] * 30)
    
    # Fila 29: Zona inbound
    matrix.append([1] * 30)
    
    return matrix

def replace_fallback_layouts():
    """Reemplazar layouts fallback con WH1"""
    
    print("Reemplazando layouts fallback con WH1...")
    
    wh1_matrix = create_wh1_matrix()
    
    # Calcular estadísticas
    total_tiles = 30 * 30
    walkable_tiles = sum(sum(row) for row in wh1_matrix)
    walkable_pct = (walkable_tiles / total_tiles) * 100
    
    print(f"WH1 Matrix: {walkable_tiles}/{total_tiles} ({walkable_pct:.1f}%) navegable")
    
    # 1. Reemplazar configuración de layouts personalizados
    enhanced_layouts = [
        {
            'info': {
                'name': 'Almacen_Pequeño',
                'width': 30,
                'height': 30,
                'tile_width': 32,
                'tile_height': 32,
                'description': 'WH1 personalizado (pequeño)'
            },
            'pattern': 'wh1_custom'
        },
        {
            'info': {
                'name': 'Almacen_Grande',
                'width': 30,
                'height': 30,
                'tile_width': 32,
                'tile_height': 32,
                'description': 'WH1 personalizado (grande)'
            },
            'pattern': 'wh1_custom'
        },
        {
            'info': {
                'name': 'Layout_Corredor_Central',
                'width': 30,
                'height': 30,
                'tile_width': 32,
                'tile_height': 32,
                'description': 'WH1 personalizado (corredor)'
            },
            'pattern': 'wh1_custom'
        }
    ]
    
    config_path = "layouts/layouts_personalizados.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(enhanced_layouts, f, indent=2, ensure_ascii=False)
    
    print(f"Configuración actualizada: {config_path}")
    
    # 2. Crear patch mejorado que use WH1
    patch_code = f'''
# PATCH DEFINITIVO PARA WH1
import json
import os

# Matriz WH1 hardcodeada
WH1_MATRIX = {wh1_matrix}

def _create_enhanced_fallback_layout(self, tmx_path):
    """Fallback que SIEMPRE usa WH1"""
    
    print(f"[WH1 PATCH] Interceptando: {{tmx_path}} -> Usando WH1")
    
    return {{
        'info': {{
            'name': 'WH1_FORCED',
            'path': tmx_path,
            'width': 30,
            'height': 30,
            'tile_width': 32,
            'tile_height': 32
        }},
        'navigation_matrix': WH1_MATRIX,
        'special_locations': {{
            'depot_points': [
                {{'tile_pos': (15, 0), 'pixel_pos': (480, 0)}},
                {{'tile_pos': (20, 0), 'pixel_pos': (640, 0)}}
            ],
            'inbound_points': [
                {{'tile_pos': (5, 29), 'pixel_pos': (160, 928)}},
                {{'tile_pos': (10, 29), 'pixel_pos': (320, 928)}}
            ],
            'picking_points': [
                {{'tile_pos': (x, y), 'pixel_pos': (x*32, y*32)}} 
                for y in range(3, 27) for x in range(0, 30, 3)
            ],
            'emergency_exits': []
        }},
        'tmx_data': None
    }}

def _generate_wh1_custom_matrix(self, width, height):
    """Generar matriz WH1 personalizada"""
    return WH1_MATRIX

def _generate_special_locations_wh1(self, pattern, info):
    """Generar ubicaciones especiales para WH1"""
    return {{
        'depot_points': [
            {{'tile_pos': (15, 0), 'pixel_pos': (480, 0)}},
            {{'tile_pos': (20, 0), 'pixel_pos': (640, 0)}}
        ],
        'inbound_points': [
            {{'tile_pos': (5, 29), 'pixel_pos': (160, 928)}},
            {{'tile_pos': (10, 29), 'pixel_pos': (320, 928)}}
        ],
        'picking_points': [
            {{'tile_pos': (x, y), 'pixel_pos': (x*32, y*32)}} 
            for y in range(3, 27) for x in range(0, 30, 3)
        ],
        'workstations': [],
        'emergency_exits': []
    }}

# Aplicar patch a DynamicLayoutLoader
from dynamic_layout_loader import DynamicLayoutLoader

# Guardar método original si no existe
if not hasattr(DynamicLayoutLoader, '_create_fallback_layout_original'):
    DynamicLayoutLoader._create_fallback_layout_original = DynamicLayoutLoader._create_fallback_layout

# Aplicar métodos WH1
DynamicLayoutLoader._create_enhanced_fallback_layout = _create_enhanced_fallback_layout
DynamicLayoutLoader._generate_wh1_custom_matrix = _generate_wh1_custom_matrix
DynamicLayoutLoader._generate_special_locations_wh1 = _generate_special_locations_wh1

# Reemplazar método de fallback
DynamicLayoutLoader._create_fallback_layout = _create_enhanced_fallback_layout

print("[WH1 DEFINITIVE PATCH] Parche definitivo aplicado - Todos los layouts usan WH1")
'''
    
    # Guardar patch definitivo
    patch_path = "layouts/wh1_definitive_patch.py"
    with open(patch_path, 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    print(f"Patch definitivo guardado: {patch_path}")
    
    return True

def apply_definitive_patch():
    """Aplicar patch definitivo a run_simulator.py"""
    
    # Leer run_simulator.py actual
    with open('run_simulator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar línea donde se aplican parches
    patch_line = "# Aplicar parche FORZADO para WH1"
    
    if patch_line in content and "wh1_definitive_patch" not in content:
        # Agregar patch definitivo
        new_patch = '''
# Aplicar parche DEFINITIVO para WH1
try:
    exec(open('layouts/wh1_definitive_patch.py', encoding='utf-8').read())
except FileNotFoundError:
    print("Warning: Patch definitivo WH1 no encontrado")'''
    
        content = content.replace(patch_line, patch_line + new_patch)
        
        # Guardar archivo modificado
        with open('run_simulator.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("run_simulator.py actualizado con patch definitivo")
        return True
    else:
        print("run_simulator.py ya tiene patch definitivo o no se encontró línea de patch")
        return False

def main():
    """Aplicar reemplazo definitivo"""
    
    print("="*60)
    print("REEMPLAZO DEFINITIVO DE WH1")
    print("="*60)
    
    # 1. Reemplazar layouts fallback
    if replace_fallback_layouts():
        print("EXITO: Layouts fallback reemplazados")
    else:
        print("ERROR: No se pudieron reemplazar layouts")
        return
    
    # 2. Aplicar patch al simulador
    apply_definitive_patch()
    
    print("\n" + "="*60)
    print("PATCH DEFINITIVO APLICADO")
    print("="*60)
    print("TODOS los layouts ahora usarán tu WH1:")
    print("- Dimensiones: 30x30")
    print("- Navegabilidad: ~67% (no 100%)")
    print("- Patrón: Racks y picking alternados")
    print("- Parking, depot, inbound configurados")
    print("\nEjecuta el simulador - debería mostrar WH1")
    print("="*60)

if __name__ == "__main__":
    main()