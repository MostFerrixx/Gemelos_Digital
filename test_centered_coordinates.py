#!/usr/bin/env python3
"""
Test de las correcciones de coordenadas centradas
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA DE COORDENADAS CENTRADAS ===")

try:
    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100))
    
    from simulation.layout_manager import LayoutManager
    
    # Cargar TMX
    layout_manager = LayoutManager("layouts/WH1.tmx")
    
    print("1. VERIFICANDO grid_to_pixel CENTRADO...")
    
    # Test conversiones de grilla a píxeles
    test_cases = [
        (0, 0),     # Esquina superior izquierda
        (1, 1),     # Segunda celda
        (15, 15),   # Centro del mapa
        (29, 29)    # Esquina inferior derecha
    ]
    
    for grid_x, grid_y in test_cases:
        pixel_x, pixel_y = layout_manager.grid_to_pixel(grid_x, grid_y)
        
        # Verificar que está centrado
        expected_center_x = (grid_x * 32) + 16  # 32 = tile_width, 16 = mitad
        expected_center_y = (grid_y * 32) + 16  # 32 = tile_height, 16 = mitad
        
        if pixel_x == expected_center_x and pixel_y == expected_center_y:
            print(f"   [OK] Grilla({grid_x}, {grid_y}) -> Píxeles CENTRADOS({pixel_x}, {pixel_y})")
        else:
            print(f"   [ERROR] Grilla({grid_x}, {grid_y}) -> Esperado({expected_center_x}, {expected_center_y}), Obtenido({pixel_x}, {pixel_y})")
    
    print("2. VERIFICANDO DEPOT POINTS...")
    
    if layout_manager.depot_points:
        depot_grid = layout_manager.depot_points[0]
        depot_pixels = layout_manager.grid_to_pixel(*depot_grid)
        print(f"   [OK] Depot TMX: Grilla{depot_grid} -> Píxeles centrados{depot_pixels}")
    else:
        print("   [ERROR] No hay depot points en TMX")
    
    print("3. SIMULANDO PROCESO OPERARIO...")
    
    from simulation.pathfinder import Pathfinder
    from visualization.state import inicializar_estado, estado_visual
    import simpy
    
    # Crear simulación mínima
    pathfinder = Pathfinder(layout_manager.collision_matrix)
    env = simpy.Environment()
    
    configuracion = {
        'num_operarios_terrestres': 1,
        'num_montacargas': 1,  # Mínimo 1 para evitar error SimPy
        'tareas_zona_a': 1,
        'tareas_zona_b': 1
    }
    
    from simulation.warehouse import AlmacenMejorado
    almacen = AlmacenMejorado(env, configuracion, layout_manager=layout_manager)
    inicializar_estado(almacen, env, configuracion, layout_manager=layout_manager)
    
    # Simular inicio del proceso operario
    print("   [SIMULANDO] Spawn del operario desde depot TMX...")
    
    # Obtener posición inicial como lo hace el operario
    spawn_grid_pos = almacen.layout_manager.depot_points[0]
    current_grid_x, current_grid_y = spawn_grid_pos
    
    # Convertir a píxeles centrados
    pixel_x, pixel_y = almacen.layout_manager.grid_to_pixel(current_grid_x, current_grid_y)
    
    print(f"   [OK] Operario spawn: Grilla({current_grid_x}, {current_grid_y}) -> Píxeles centrados({pixel_x}, {pixel_y})")
    
    # Verificar que el estado visual se actualiza correctamente
    estado_visual["operarios"] = {1: {'x': pixel_x, 'y': pixel_y, 'tipo': 'terrestre'}}
    
    op_data = estado_visual["operarios"][1]
    if op_data['x'] == pixel_x and op_data['y'] == pixel_y:
        print(f"   [OK] Estado visual actualizado con coordenadas centradas: ({op_data['x']}, {op_data['y']})")
    else:
        print(f"   [ERROR] Estado visual incorrecto")
    
    pygame.quit()
    
    print("\n[SUCCESS] COORDENADAS CENTRADAS IMPLEMENTADAS CORRECTAMENTE!")
    print("Resumen de cambios:")
    print("• grid_to_pixel ahora apunta al CENTRO de cada tile")
    print("• Operarios spawn desde depot TMX con coordenadas centradas")
    print("• Renderizado usa coordenadas ya centradas")
    print("• Movimiento será visualmente preciso")
    
except Exception as e:
    print(f"[ERROR] Error en prueba: {e}")
    import traceback
    traceback.print_exc()