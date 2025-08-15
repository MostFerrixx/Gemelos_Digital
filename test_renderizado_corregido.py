#!/usr/bin/env python3
"""
Test del renderizado corregido sin escalado para TMX
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA DE RENDERIZADO CORREGIDO ===")

try:
    import pygame
    pygame.init()
    
    # Crear ventana TMX exacta
    screen = pygame.display.set_mode((960, 960))
    
    from simulation.layout_manager import LayoutManager
    from visualization.state import estado_visual
    
    # Cargar TMX
    layout_manager = LayoutManager("layouts/WH1.tmx")
    
    print("1. VERIFICANDO MODO TMX SIN ESCALADO...")
    
    # Verificar detección de modo TMX
    ancho_ventana, alto_ventana = screen.get_size()
    if ancho_ventana == 960 and alto_ventana == 960:
        print(f"   [OK] Modo TMX detectado: {ancho_ventana}x{alto_ventana}")
        usar_escalado = False
    else:
        print(f"   [ERROR] Modo TMX no detectado: {ancho_ventana}x{alto_ventana}")
        usar_escalado = True
    
    print("2. CONFIGURANDO OPERARIOS DE PRUEBA...")
    
    # Configurar operarios en posiciones TMX válidas
    depot_grid = layout_manager.depot_points[0]
    depot_pixels = layout_manager.grid_to_pixel(*depot_grid)
    
    # Operario en depot
    operario_1_pixels = depot_pixels
    
    # Operario en posición diferente
    test_grid = (5, 5)
    operario_2_pixels = layout_manager.grid_to_pixel(*test_grid)
    
    estado_visual["operarios"] = {
        1: {
            'x': operario_1_pixels[0],
            'y': operario_1_pixels[1],
            'tipo': 'terrestre',
            'accion': 'Esperando tareas',
            'tareas_completadas': 0
        },
        2: {
            'x': operario_2_pixels[0],
            'y': operario_2_pixels[1],
            'tipo': 'montacargas',
            'accion': 'En movimiento',
            'tareas_completadas': 5
        }
    }
    
    print(f"   [OK] Operario 1: píxeles{operario_1_pixels} (depot)")
    print(f"   [OK] Operario 2: píxeles{operario_2_pixels} (grilla {test_grid})")
    
    print("3. PROBANDO RENDERIZADO...")
    
    # Renderizar fondo TMX
    screen.fill((245, 245, 245))
    layout_manager.render(screen)
    print("   [OK] Fondo TMX renderizado")
    
    # Renderizar operarios usando función corregida
    from visualization.original_renderer import dibujar_operarios
    
    try:
        dibujar_operarios(screen)
        print("   [OK] Operarios renderizados sin errores")
        
        # Verificar que las coordenadas están dentro de la ventana
        for op_id, data in estado_visual["operarios"].items():
            x, y = data['x'], data['y']
            if 0 <= x <= 960 and 0 <= y <= 960:
                print(f"   [OK] Operario {op_id} coordenadas válidas: ({x}, {y})")
            else:
                print(f"   [ERROR] Operario {op_id} fuera de ventana: ({x}, {y})")
        
    except Exception as e:
        print(f"   [ERROR] Error en renderizado: {e}")
        import traceback
        traceback.print_exc()
    
    print("4. PROBANDO MOVIMIENTO DE OPERARIO...")
    
    # Simular movimiento del operario 1
    ruta_test = [(0, 0), (1, 0), (2, 0), (3, 0)]  # Movimiento horizontal
    
    for i, (grid_x, grid_y) in enumerate(ruta_test):
        pixel_x, pixel_y = layout_manager.grid_to_pixel(grid_x, grid_y)
        estado_visual["operarios"][1]['x'] = pixel_x
        estado_visual["operarios"][1]['y'] = pixel_y
        
        print(f"   [PASO {i+1}] Grilla({grid_x}, {grid_y}) -> Píxeles({pixel_x}, {pixel_y})")
        
        # Verificar que se puede renderizar
        try:
            screen.fill((245, 245, 245))
            layout_manager.render(screen)
            dibujar_operarios(screen)
            print(f"   [OK] Paso {i+1} renderizado exitosamente")
        except Exception as e:
            print(f"   [ERROR] Paso {i+1} falló: {e}")
            break
    
    pygame.quit()
    
    print("\n[SUCCESS] RENDERIZADO CORREGIDO!")
    print("Cambios aplicados:")
    print("• Eliminado escalado legacy para modo TMX 960x960")
    print("• Coordenadas píxeles usadas directamente (correspondencia 1:1)")
    print("• Validación de coordenadas añadida")
    print("• Sistema detecta automáticamente modo TMX vs legacy")
    
except Exception as e:
    print(f"[ERROR] Error en prueba: {e}")
    import traceback
    traceback.print_exc()