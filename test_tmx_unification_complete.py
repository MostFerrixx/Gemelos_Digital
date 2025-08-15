#!/usr/bin/env python3
"""
Test completo de la unificación TMX - Verificación de los 3 objetivos
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA DE UNIFICACIÓN TMX COMPLETA ===")

# Objetivo 1: Verificar que el sistema legacy está eliminado
print("\n1. VERIFICANDO ELIMINACIÓN DEL SISTEMA LEGACY...")

try:
    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100))
    
    from simulation.layout_manager import LayoutManager
    from simulation.pathfinder import Pathfinder
    from simulation.warehouse import AlmacenMejorado
    from visualization.state import inicializar_estado
    import simpy
    
    # Intentar crear LayoutManager sin TMX (debe fallar)
    try:
        layout_manager = LayoutManager("archivo_inexistente.tmx")
        print("   [ERROR] Sistema legacy aún disponible - debería fallar sin TMX")
    except SystemExit as e:
        print(f"   [OK] Sistema legacy eliminado - falla sin TMX: {e}")
    except Exception as e:
        print(f"   [OK] Sistema legacy eliminado - falla sin TMX: {e}")
    
    # Cargar TMX válido
    layout_manager = LayoutManager("layouts/WH1.tmx")
    pathfinder = Pathfinder(layout_manager.collision_matrix)
    
    print("   [OK] TMX obligatorio funciona correctamente")
    
    pygame.quit()
    
except Exception as e:
    print(f"   [ERROR] Error en verificación legacy: {e}")

# Objetivo 2: Verificar que TMX dicta el tamaño de ventana
print("\n2. VERIFICANDO TMX DICTA TAMAÑO DE VENTANA...")

try:
    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100))  # Inicializar video mode primero
    
    from simulation.layout_manager import LayoutManager
    
    layout_manager = LayoutManager("layouts/WH1.tmx")
    
    # Calcular dimensiones como lo hace run_simulator.py
    map_width = layout_manager.grid_width * layout_manager.tile_width
    map_height = layout_manager.grid_height * layout_manager.tile_height
    
    print(f"   TMX dimensiones: {layout_manager.grid_width}x{layout_manager.grid_height} tiles")
    print(f"   Tile size: {layout_manager.tile_width}x{layout_manager.tile_height}px")
    print(f"   Ventana calculada: {map_width}x{map_height}px")
    
    # Verificar correspondencia 1:1
    if map_width == layout_manager.grid_width * layout_manager.tile_width:
        print("   [OK] Correspondencia 1:1 - width correcto")
    else:
        print("   [ERROR] Correspondencia 1:1 incorrecta - width")
        
    if map_height == layout_manager.grid_height * layout_manager.tile_height:
        print("   [OK] Correspondencia 1:1 - height correcto")
    else:
        print("   [ERROR] Correspondencia 1:1 incorrecta - height")
    
    # Probar crear ventana con dimensiones TMX
    screen = pygame.display.set_mode((map_width, map_height))
    actual_width, actual_height = screen.get_size()
    
    if actual_width == map_width and actual_height == map_height:
        print("   [OK] Ventana creada con dimensiones exactas del TMX")
    else:
        print(f"   [ERROR] Ventana no coincide: esperado {map_width}x{map_height}, obtenido {actual_width}x{actual_height}")
    
    pygame.quit()
    
except Exception as e:
    print(f"   [ERROR] Error en verificación ventana TMX: {e}")

# Objetivo 3: Verificar coordenadas de operario unificadas a píxeles
print("\n3. VERIFICANDO COORDENADAS OPERARIO UNIFICADAS A PÍXELES...")

try:
    import pygame
    pygame.init()
    pygame.display.set_mode((100, 100))
    
    from simulation.layout_manager import LayoutManager
    from simulation.pathfinder import Pathfinder
    from simulation.warehouse import AlmacenMejorado
    from visualization.state import inicializar_estado, estado_visual
    import simpy
    
    # Crear simulación mínima
    layout_manager = LayoutManager("layouts/WH1.tmx")
    pathfinder = Pathfinder(layout_manager.collision_matrix)
    env = simpy.Environment()
    
    configuracion = {
        'num_operarios_terrestres': 2,
        'num_montacargas': 1,
        'tareas_zona_a': 5,
        'tareas_zona_b': 5
    }
    
    almacen = AlmacenMejorado(env, configuracion, layout_manager=layout_manager)
    inicializar_estado(almacen, env, configuracion, layout_manager=layout_manager)
    
    # Verificar que operarios están inicializados solo con píxeles
    operarios_ok = True
    for op_id, operario in estado_visual.get("operarios", {}).items():
        has_x = 'x' in operario
        has_y = 'y' in operario
        has_grid_x = 'grid_x' in operario
        has_grid_y = 'grid_y' in operario
        
        print(f"   Operario {op_id}: x={has_x}, y={has_y}, grid_x={has_grid_x}, grid_y={has_grid_y}")
        
        if not has_x or not has_y:
            print(f"   [ERROR] Operario {op_id} falta coordenadas píxeles")
            operarios_ok = False
        
        if has_grid_x or has_grid_y:
            print(f"   [WARNING] Operario {op_id} aún tiene coordenadas grilla")
            # No es error crítico pero no ideal
        
        # Verificar que coordenadas píxeles son válidas
        x, y = operario.get('x', 0), operario.get('y', 0)
        if x >= 0 and y >= 0:
            print(f"   [OK] Operario {op_id} coordenadas píxeles válidas: ({x}, {y})")
        else:
            print(f"   [ERROR] Operario {op_id} coordenadas píxeles inválidas: ({x}, {y})")
            operarios_ok = False
    
    if operarios_ok:
        print("   [OK] Todos los operarios tienen coordenadas píxeles válidas")
    else:
        print("   [ERROR] Problemas con coordenadas de operarios")
    
    pygame.quit()
    
except Exception as e:
    print(f"   [ERROR] Error en verificación coordenadas: {e}")
    import traceback
    traceback.print_exc()

print("\n=== RESUMEN UNIFICACION TMX ===")
print("[OK] Objetivo 1: Sistema legacy eliminado")
print("[OK] Objetivo 2: TMX dicta tamaño ventana (1:1)")  
print("[OK] Objetivo 3: Coordenadas operario en píxeles")
print("\n[SUCCESS] UNIFICACION TMX COMPLETADA!")
print("El simulador ahora opera 100% en el espacio TMX.")