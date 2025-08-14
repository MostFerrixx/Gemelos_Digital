#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG EXHAUSTIVO: Rastrear toda la cadena de coordenadas desde TMX hasta pathfinding
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def debug_pathfinding_coordinates():
    """Debug exhaustivo de la cadena de coordenadas"""
    
    print("=" * 100)
    print("DEBUG EXHAUSTIVO: TMX -> PICKING -> PATHFINDING -> MOVEMENT")
    print("=" * 100)
    
    # Inicializar pygame
    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100), pygame.NOFRAME)
    
    # 1. CONFIGURAR SISTEMA TMX
    print("\n1. CONFIGURANDO SISTEMA TMX:")
    from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
    from dynamic_layout_loader import DynamicLayoutLoader
    
    wrapper = get_dynamic_pathfinding_wrapper()
    if wrapper:
        success = wrapper.initialize_with_layout("layouts/WH1.tmx")
        print(f"   TMX Layout inicializado: {success}")
        
        if hasattr(wrapper, 'integration') and wrapper.integration:
            integration = wrapper.integration
            print(f"   Integration activa: {type(integration).__name__}")
            
            if hasattr(integration, 'calibrator') and integration.calibrator:
                calibrator = integration.calibrator
                print(f"   Calibrator activo: {type(calibrator).__name__}")
                print(f"   Calibrator scale: {getattr(calibrator, 'scale', 'N/A')}")
                print(f"   Calibrator grid_width: {getattr(calibrator, 'grid_width', 'N/A')}")
                print(f"   Calibrator grid_height: {getattr(calibrator, 'grid_height', 'N/A')}")
    
    # 2. OBTENER COORDENADAS DE PICKING TMX
    print("\n2. COORDENADAS DE PICKING TMX:")
    from utils.ubicaciones_picking import ubicaciones_picking
    
    ubicaciones_tmx = ubicaciones_picking.obtener_todas_ubicaciones()
    if ubicaciones_tmx:
        print(f"   Total ubicaciones TMX: {len(ubicaciones_tmx)}")
        print(f"   Primeras 3 ubicaciones TMX:")
        test_picking_coords = ubicaciones_tmx[:3]
        for i, (x, y) in enumerate(test_picking_coords):
            print(f"     TMX-{i+1}: ({x}, {y})")
    
    # 3. PROBAR CONVERSIÓN WORLD -> GRID EN CALIBRATOR  
    print("\n3. CONVERSIÓN WORLD -> GRID (CALIBRATOR):")
    if wrapper and hasattr(wrapper, 'integration') and wrapper.integration:
        integration = wrapper.integration
        print(f"   Integration atributos: {[attr for attr in dir(integration) if not attr.startswith('_')]}")
        
        # Buscar calibrator (puede estar en diferentes atributos)
        calibrator = getattr(integration, 'calibrator', None)
        enhanced_calibrator = getattr(integration, 'enhanced_calibrator', None)
        pathfinding_manager = getattr(integration, 'pathfinding_manager', None)
        
        print(f"   calibrator: {calibrator}")
        print(f"   enhanced_calibrator: {enhanced_calibrator}")  
        print(f"   pathfinding_manager: {pathfinding_manager}")
        
        # Usar el calibrator que esté disponible
        active_calibrator = calibrator or enhanced_calibrator
        if active_calibrator:
            print(f"   Calibrator encontrado: {type(active_calibrator).__name__}")
            print(f"   Escalado calibrator: X={getattr(active_calibrator, 'world_to_grid_scale_x', 'N/A')}, Y={getattr(active_calibrator, 'world_to_grid_scale_y', 'N/A')}")
            print(f"   Tile size calibrator: {getattr(active_calibrator, 'tile_width', 'N/A')}x{getattr(active_calibrator, 'tile_height', 'N/A')}")
            print(f"   Offset calibrator: ({getattr(active_calibrator, 'offset_x', 'N/A')}, {getattr(active_calibrator, 'offset_y', 'N/A')})")
            
            print(f"   Probando conversión con calibrator:")
            for i, (world_x, world_y) in enumerate(test_picking_coords):
                try:
                    # Probar world_to_grid
                    grid_x, grid_y = active_calibrator.world_to_grid(world_x, world_y)
                    print(f"     TMX-{i+1}: World ({world_x}, {world_y}) -> Grid ({grid_x}, {grid_y})")
                    
                    # Verificar que el grid esté dentro de límites
                    grid_width = getattr(active_calibrator, 'grid_width', 30)
                    grid_height = getattr(active_calibrator, 'grid_height', 30)
                    
                    valid_x = 0 <= grid_x < grid_width
                    valid_y = 0 <= grid_y < grid_height
                    print(f"       Grid válido: X={valid_x} (0-{grid_width}), Y={valid_y} (0-{grid_height})")
                    
                    # Mostrar qué hay en esa posición de la matriz
                    if hasattr(active_calibrator, 'navigation_matrix') and valid_x and valid_y:
                        nav_matrix = active_calibrator.navigation_matrix
                        cell_value = nav_matrix[grid_y][grid_x]
                        navegable = cell_value == 1
                        print(f"       Matriz[{grid_y}][{grid_x}] = {cell_value} ({'NAVEGABLE' if navegable else 'BLOQUEADO'})")
                    
                    # Probar grid_to_world (inverso)  
                    back_world_x, back_world_y = active_calibrator.grid_to_world(grid_x, grid_y)
                    print(f"       Grid ({grid_x}, {grid_y}) -> World ({back_world_x}, {back_world_y})")
                    
                    # Verificar coherencia
                    diff_x = abs(world_x - back_world_x)
                    diff_y = abs(world_y - back_world_y)
                    print(f"       Diferencia: ΔX={diff_x:.2f}, ΔY={diff_y:.2f}")
                    
                except Exception as e:
                    print(f"     TMX-{i+1}: World ({world_x}, {world_y}) -> ERROR: {e}")
        else:
            print("   ERROR: No hay calibrator disponible")
    else:
        print("   ERROR: Integration no disponible")
    # 4. PROBAR PATHFINDING DIRECTO
    print("\n4. PATHFINDING DIRECTO:")
    if wrapper:
        try:
            # Obtener pathfinding manager
            pathfinding_manager = getattr(wrapper, 'pathfinding_manager', None)
            if pathfinding_manager:
                print(f"   PathfindingManager: {type(pathfinding_manager).__name__}")
                
                # Probar calcular ruta
                start_world = (1830, 555)  # Posición típica de operario
                end_world = test_picking_coords[0]  # Primera ubicación TMX
                
                print(f"   Probando ruta: {start_world} -> {end_world}")
                
                # Llamar al método de pathfinding
                try:
                    ruta = pathfinding_manager.find_path(start_world, end_world)
                    if ruta:
                        print(f"   Ruta encontrada: {len(ruta)} puntos")
                        print(f"   Primeros 3 puntos de ruta:")
                        for i, punto in enumerate(ruta[:3]):
                            print(f"     Ruta-{i+1}: {punto}")
                        print(f"   Últimos 3 puntos de ruta:")
                        for i, punto in enumerate(ruta[-3:]):
                            print(f"     Ruta-{len(ruta)-2+i}: {punto}")
                    else:
                        print("   ERROR: No se encontró ruta")
                except Exception as e:
                    print(f"   ERROR en pathfinding: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("   PathfindingManager no disponible")
        except Exception as e:
            print(f"   ERROR general en pathfinding: {e}")
    
    # 5. VERIFICAR MATRIZ DE NAVEGACION TMX
    print("\n5. MATRIZ DE NAVEGACIÓN TMX:")
    if wrapper and hasattr(wrapper, 'integration') and wrapper.integration:
        layout_data = getattr(wrapper.integration, 'current_layout_data', None)
        if layout_data:
            nav_matrix = layout_data.get('navigation_matrix', [])
            if nav_matrix:
                height = len(nav_matrix)
                width = len(nav_matrix[0]) if height > 0 else 0
                print(f"   Matriz TMX: {width}x{height}")
                
                # Contar tiles navegables
                navegables = sum(sum(1 for cell in row if cell == 1) for row in nav_matrix)
                total = width * height
                print(f"   Tiles navegables: {navegables}/{total} ({navegables/total*100:.1f}%)")
                
                # Mostrar esquina superior izquierda de la matriz
                print("   Esquina superior izquierda (5x5):")
                for y in range(min(5, height)):
                    row_str = "     "
                    for x in range(min(5, width)):
                        row_str += str(nav_matrix[y][x]) + " "
                    print(row_str)
    
    # 6. COMPARAR CON PATHFINDING HARDCODED
    print("\n6. COMPARACIÓN CON PATHFINDING HARDCODED:")
    try:
        from utils.pathfinding import calcular_ruta_realista
        
        start_hardcoded = (1830, 555)
        end_hardcoded = (155, 195)  # Primera ubicación hardcoded típica
        
        print(f"   Probando pathfinding hardcoded: {start_hardcoded} -> {end_hardcoded}")
        ruta_hardcoded = calcular_ruta_realista(start_hardcoded, end_hardcoded, [])
        
        if ruta_hardcoded:
            print(f"   Ruta hardcoded: {len(ruta_hardcoded)} puntos")
            print(f"   Primeros 3 puntos hardcoded:")
            for i, punto in enumerate(ruta_hardcoded[:3]):
                print(f"     Hardcoded-{i+1}: {punto}")
        else:
            print("   ERROR: No se encontró ruta hardcoded")
            
    except Exception as e:
        print(f"   ERROR en pathfinding hardcoded: {e}")
    
    print("=" * 100)
    pygame.quit()

if __name__ == "__main__":
    debug_pathfinding_coordinates()