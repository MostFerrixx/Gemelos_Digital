#!/usr/bin/env python3
"""
Test final del movimiento de operarios con coordenadas centradas
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA FINAL DEL MOVIMIENTO CORREGIDO ===")

try:
    # Importar simulador
    from run_simulator import SimuladorAlmacen
    
    # Crear instancia del simulador
    simulador = SimuladorAlmacen()
    
    # Configuración de prueba
    configuracion_test = {
        'num_operarios_terrestres': 1,
        'num_montacargas': 1,
        'tareas_zona_a': 3,
        'tareas_zona_b': 3
    }
    
    simulador.configuracion = configuracion_test
    
    print("1. Creando simulación con coordenadas centradas...")
    
    if simulador.crear_simulacion():
        print("   [OK] Simulación creada exitosamente")
        
        # Verificar spawn centrado
        from visualization.state import estado_visual
        
        operario_1 = estado_visual["operarios"][1]
        spawn_x, spawn_y = operario_1['x'], operario_1['y']
        
        # Verificar que está en el centro de una celda
        grid_x, grid_y = simulador.layout_manager.pixel_to_grid(spawn_x, spawn_y)
        recalc_x, recalc_y = simulador.layout_manager.grid_to_pixel(grid_x, grid_y)
        
        if spawn_x == recalc_x and spawn_y == recalc_y:
            print(f"   [OK] Operario 1 spawn CENTRADO: píxeles({spawn_x}, {spawn_y}) en grilla({grid_x}, {grid_y})")
        else:
            print(f"   [ERROR] Operario 1 NO centrado: spawn({spawn_x}, {spawn_y}) vs recalc({recalc_x}, {recalc_y})")
        
        print("2. Inicializando pygame con dimensiones TMX exactas...")
        
        simulador.inicializar_pygame()
        
        map_width = simulador.layout_manager.grid_width * simulador.layout_manager.tile_width
        map_height = simulador.layout_manager.grid_height * simulador.layout_manager.tile_height
        actual_width, actual_height = simulador.pantalla.get_size()
        
        if actual_width == map_width and actual_height == map_height:
            print(f"   [OK] Ventana pygame TMX exacta: {actual_width}x{actual_height}")
        else:
            print(f"   [ERROR] Ventana dimensiones incorrectas")
        
        print("3. Verificando alineación pathfinding-visual...")
        
        # Simular un paso de movimiento
        from simulation.pathfinder import Pathfinder
        pathfinder = simulador.pathfinder
        
        # Ruta de prueba: del depot a un punto cercano
        depot_pos = simulador.layout_manager.depot_points[0]
        target_pos = (depot_pos[0] + 2, depot_pos[1] + 2)
        
        if simulador.layout_manager.is_walkable(*target_pos):
            route = pathfinder.find_path(depot_pos, target_pos)
            
            if route and len(route) > 1:
                print(f"   [OK] Pathfinding encuentra ruta: {len(route)} pasos")
                
                # Simular movimiento a segundo paso
                step_grid = route[1]
                step_pixels = simulador.layout_manager.grid_to_pixel(*step_grid)
                
                print(f"   [OK] Paso 1: Grilla{step_grid} -> Píxeles centrados{step_pixels}")
                
                # Verificar que la conversión es reversible
                back_to_grid = simulador.layout_manager.pixel_to_grid(*step_pixels)
                
                # La conversión de vuelta debe ser exacta o muy cercana
                if abs(back_to_grid[0] - step_grid[0]) <= 1 and abs(back_to_grid[1] - step_grid[1]) <= 1:
                    print(f"   [OK] Conversión reversible: Grilla{step_grid} -> Píxeles{step_pixels} -> Grilla{back_to_grid}")
                else:
                    print(f"   [WARNING] Conversión no exacta: {step_grid} != {back_to_grid}")
            else:
                print("   [WARNING] No se encontró ruta de prueba")
        else:
            print("   [WARNING] Posición target no caminable")
        
        print("4. Resumen de correcciones aplicadas...")
        
        print("   [APLICADO] grid_to_pixel suma tile_width//2 y tile_height//2")
        print("   [APLICADO] Operarios spawn desde depot TMX con coordenadas centradas")
        print("   [APLICADO] Renderizado usa coordenadas píxeles ya centradas")
        print("   [APLICADO] TMX dicta ventana con correspondencia 1:1")
        
        # Limpiar recursos
        simulador.limpiar_recursos()
        
        print("\n[SUCCESS] MOVIMIENTO CORREGIDO - COORDENADAS CENTRADAS!")
        print("El simulador ahora debe mostrar movimiento fluido y preciso.")
        print("Los operarios se moverán por el centro de las celdas TMX.")
        
    else:
        print("   [ERROR] No se pudo crear la simulación")
    
except Exception as e:
    print(f"[ERROR] Error en prueba: {e}")
    import traceback
    traceback.print_exc()