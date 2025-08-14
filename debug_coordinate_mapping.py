#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG: Verificar el mapping de coordenadas entre diferentes sistemas
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def debug_coordinate_mapping():
    """Debug completo del mapping de coordenadas"""
    
    print("=" * 80)
    print("DEBUG COORDINATE MAPPING - TMX vs VISUAL vs NAVIGATION")
    print("=" * 80)
    
    # Inicializar pygame para evitar errores
    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100), pygame.NOFRAME)
    
    # 1. TMX Layout Data
    print("\n1. TMX LAYOUT DATA:")
    from dynamic_layout_loader import DynamicLayoutLoader
    from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
    
    loader = DynamicLayoutLoader("layouts")
    layout_data = loader.load_layout("layouts/WH1.tmx")
    
    if layout_data:
        info = layout_data['info']
        navigation_matrix = layout_data.get('navigation_matrix', [])
        
        print(f"   TMX Info: {info['width']}x{info['height']} @ {info['tile_width']}x{info['tile_height']}px")
        print(f"   Matriz navegación: {len(navigation_matrix)}x{len(navigation_matrix[0]) if navigation_matrix else 0}")
        
        # Dimensiones en píxeles del TMX
        tmx_pixel_width = info['width'] * info['tile_width']
        tmx_pixel_height = info['height'] * info['tile_height']
        print(f"   Dimensiones TMX en píxeles: {tmx_pixel_width}x{tmx_pixel_height}")
    
    # 2. Visual Renderer - ¿Cómo se escala el TMX?
    print("\n2. VISUAL RENDERER SCALING:")
    from direct_layout_patch import get_tmx_layout_data
    
    tmx_data = get_tmx_layout_data()
    if tmx_data:
        nav_matrix = tmx_data.get('navigation_matrix', [])
        width = len(nav_matrix[0]) if nav_matrix else 0
        height = len(nav_matrix)
        print(f"   Renderer ve: {width}x{height}")
        
        # Simular escalado del renderer (de direct_layout_patch.py)
        screen_width, screen_height = 1900, 900  # Valores por defecto
        available_width = screen_width - 100
        available_height = screen_height - 150
        tile_size_x = available_width // width
        tile_size_y = available_height // height
        tile_size = min(tile_size_x, tile_size_y, 25)
        
        print(f"   Tile size calculado para visual: {tile_size}px")
        
        # Cálculo de offset del renderer
        total_layout_width = width * tile_size
        total_layout_height = height * tile_size
        offset_x = (screen_width - total_layout_width) // 2
        offset_y = (screen_height - total_layout_height - 120) // 2 + 20
        
        print(f"   Visual offset: ({offset_x}, {offset_y})")
        print(f"   Visual layout size: {total_layout_width}x{total_layout_height}")
        
        # Ejemplo de conversión tile -> píxel visual
        print(f"   Tile (0,0) -> Visual píxel: ({offset_x}, {offset_y})")
        print(f"   Tile (1,1) -> Visual píxel: ({offset_x + tile_size}, {offset_y + tile_size})")
    
    # 3. Picking Locations - ¿Qué coordenadas genera?
    print("\n3. PICKING LOCATIONS TMX:")
    from utils.ubicaciones_picking import ubicaciones_picking
    
    # Forzar que se cargue TMX primero
    wrapper = get_dynamic_pathfinding_wrapper()
    if wrapper:
        wrapper.initialize_with_layout("layouts/WH1.tmx")
    
    ubicaciones_tmx = ubicaciones_picking.obtener_todas_ubicaciones()
    
    if ubicaciones_tmx:
        print(f"   Total ubicaciones TMX: {len(ubicaciones_tmx)}")
        print(f"   Primeras 5 ubicaciones:")
        for i, (x, y) in enumerate(ubicaciones_tmx[:5]):
            print(f"     {i+1}. ({x}, {y})")
        print(f"   Últimas 5 ubicaciones:")
        for i, (x, y) in enumerate(ubicaciones_tmx[-5:]):
            print(f"     {len(ubicaciones_tmx)-4+i}. ({x}, {y})")
        
        # Rango de coordenadas
        xs = [x for x, y in ubicaciones_tmx]
        ys = [x for x, y in ubicaciones_tmx]
        print(f"   Rango X: {min(xs)} - {max(xs)}")
        print(f"   Rango Y: {min(ys)} - {max(ys)}")
    
    # 4. Hardcoded vs TMX comparison
    print("\n4. HARDCODED vs TMX COMPARISON:")
    from utils.ubicaciones_picking import UbicacionesPicking
    
    # Obtener hardcoded temporalmente
    temp_picker = UbicacionesPicking()
    hardcoded_locs = [ub['coordenadas'] for ub in temp_picker.ubicaciones_cache]
    
    print(f"   Hardcoded total: {len(hardcoded_locs)}")
    if hardcoded_locs:
        xs_h = [x for x, y in hardcoded_locs]
        ys_h = [y for x, y in hardcoded_locs]
        print(f"   Hardcoded rango X: {min(xs_h)} - {max(xs_h)}")
        print(f"   Hardcoded rango Y: {min(ys_h)} - {max(ys_h)}")
        print(f"   Hardcoded primera: {hardcoded_locs[0]}")
        print(f"   Hardcoded última: {hardcoded_locs[-1]}")
    
    # 5. Pathfinding coordinates
    print("\n5. PATHFINDING NAVIGATION:")
    if wrapper and hasattr(wrapper, 'integration'):
        integration = wrapper.integration
        if hasattr(integration, 'calibrator') and integration.calibrator:
            calibrator = integration.calibrator
            print(f"   Calibrator activo: {type(calibrator).__name__}")
            
            # Test conversión world -> grid
            test_coords = [(100, 100), (500, 300), (800, 600)]
            for world_x, world_y in test_coords:
                try:
                    grid_x, grid_y = calibrator.world_to_grid(world_x, world_y)
                    print(f"   World ({world_x}, {world_y}) -> Grid ({grid_x}, {grid_y})")
                except Exception as e:
                    print(f"   World ({world_x}, {world_y}) -> Error: {e}")
    
    print("=" * 80)
    pygame.quit()

if __name__ == "__main__":
    debug_coordinate_mapping()