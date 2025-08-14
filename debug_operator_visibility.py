#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG VISIBILIDAD OPERARIOS: Investigar por qué no aparecen los operarios
"""

def debug_operator_visibility():
    """Debugger la visibilidad de los operarios"""
    
    print("="*70)
    print("DEBUG: ¿POR QUÉ NO SE VEN LOS OPERARIOS?")
    print("="*70)
    
    # 1. Verificar estado visual de operarios
    print("\n1. ESTADO VISUAL DE OPERARIOS:")
    try:
        from visualization.state import estado_visual
        
        operarios = estado_visual.get("operarios", {})
        print(f"   Operarios en estado_visual: {len(operarios)}")
        
        for op_id, data in operarios.items():
            x = data.get('x', 0)
            y = data.get('y', 0)
            accion = data.get('accion', 'Unknown')
            tipo = data.get('tipo', 'unknown')
            print(f"   Operario {op_id} ({tipo}): TMX({x}, {y}) - {accion}")
            
    except Exception as e:
        print(f"   Error obteniendo estado visual: {e}")
    
    # 2. Verificar conversión TMX -> pantalla
    print("\n2. CONVERSIÓN TMX -> PANTALLA:")
    try:
        from tmx_screen_converter import tmx_screen_converter, convert_operator_coordinates
        
        # Simular dimensiones de pantalla del usuario (estimando por la imagen)
        screen_width, screen_height = 1366, 768  # Estimación basada en la imagen
        
        print(f"   Pantalla estimada: {screen_width}x{screen_height}")
        
        if operarios:
            converted = convert_operator_coordinates(operarios, screen_width, screen_height)
            
            print(f"   Operarios convertidos: {len(converted)}")
            for op_id, data in converted.items():
                tmx_x = data.get('tmx_x', 0)
                tmx_y = data.get('tmx_y', 0)
                screen_x = data.get('x', 0)
                screen_y = data.get('y', 0)
                print(f"   Operario {op_id}: TMX({tmx_x}, {tmx_y}) -> Pantalla({screen_x}, {screen_y})")
                
                # Verificar si están dentro del área visible
                if 0 <= screen_x <= screen_width and 0 <= screen_y <= screen_height:
                    print(f"     ✓ Dentro del área visible")
                else:
                    print(f"     ✗ FUERA del área visible (pantalla: 0-{screen_width} x 0-{screen_height})")
    
    except Exception as e:
        print(f"   Error en conversión: {e}")
    
    # 3. Verificar área del layout en pantalla
    print("\n3. ÁREA DEL LAYOUT EN PANTALLA:")
    try:
        from tmx_screen_converter import tmx_screen_converter
        
        if tmx_screen_converter.initialize_for_screen(screen_width, screen_height):
            bounds = tmx_screen_converter.get_layout_bounds_on_screen()
            if bounds:
                print(f"   Layout area: ({bounds['min_x']}, {bounds['min_y']}) a ({bounds['max_x']}, {bounds['max_y']})")
                print(f"   Layout size: {bounds['max_x'] - bounds['min_x']}x{bounds['max_y'] - bounds['min_y']}")
                
                # Verificar si el layout cabe en pantalla
                if bounds['max_x'] <= screen_width and bounds['max_y'] <= screen_height:
                    print(f"   ✓ Layout cabe en pantalla")
                else:
                    print(f"   ✗ Layout se sale de pantalla")
                    
    except Exception as e:
        print(f"   Error obteniendo bounds del layout: {e}")
    
    # 4. Verificar si el patch de renderizado está funcionando
    print("\n4. VERIFICAR PATCH DE RENDERIZADO:")
    try:
        import visualization.original_renderer as renderer_module
        
        # Verificar si la función fue patcheada
        func = getattr(renderer_module, 'dibujar_operarios', None)
        if func:
            func_name = func.__name__ if hasattr(func, '__name__') else 'unknown'
            print(f"   Función dibujar_operarios: {func_name}")
            
            if 'tmx' in func_name.lower() or 'corrected' in func_name.lower():
                print("   ✓ Función patcheada detectada")
            else:
                print("   ✗ Función original (NO patcheada)")
                print("   El patch de renderizado no se aplicó correctamente")
        else:
            print("   ✗ Función dibujar_operarios no encontrada")
            
    except Exception as e:
        print(f"   Error verificando patch: {e}")
    
    # 5. Proponer soluciones
    print("\n5. POSIBLES SOLUCIONES:")
    print("   A. Si operarios están fuera de pantalla:")
    print("      - Ajustar conversión de coordenadas")
    print("      - Cambiar tamaño de layout")
    print("   B. Si patch no funcionó:")
    print("      - Re-aplicar patch de renderizado")
    print("      - Verificar orden de imports")
    print("   C. Si problema de escala:")
    print("      - Ajustar factores de escala")
    print("      - Aumentar tamaño de operarios")

def test_simple_operator_rendering():
    """Test simple de renderizado de operarios"""
    
    print("\n" + "="*70)
    print("TEST SIMPLE DE RENDERIZADO")
    print("="*70)
    
    try:
        # Simular datos de operario simple
        test_operators = {
            1: {
                'x': 480,  # Centro TMX
                'y': 480,  # Centro TMX  
                'accion': 'Test',
                'tareas_completadas': 0,
                'tipo': 'terrestre'
            }
        }
        
        # Test de conversión
        from tmx_screen_converter import convert_operator_coordinates
        screen_w, screen_h = 1366, 768
        
        converted = convert_operator_coordinates(test_operators, screen_w, screen_h)
        
        print("Operario de test:")
        for op_id, data in converted.items():
            print(f"  TMX: ({data.get('tmx_x', 0)}, {data.get('tmx_y', 0)})")
            print(f"  Pantalla: ({data.get('x', 0)}, {data.get('y', 0)})")
            
        # Verificar si está en área visible
        test_op = converted[1]
        x, y = test_op['x'], test_op['y']
        
        if 0 <= x <= screen_w and 0 <= y <= screen_h:
            print(f"  ✓ Operario test VISIBLE en ({x}, {y})")
        else:
            print(f"  ✗ Operario test INVISIBLE en ({x}, {y})")
            
        return True
        
    except Exception as e:
        print(f"Error en test: {e}")
        return False

if __name__ == "__main__":
    # Activar TMX primero
    try:
        from force_tmx_activation import force_tmx_activation
        force_tmx_activation()
    except ImportError:
        print("Error: No se pudo activar TMX")
    
    # Debug principal
    debug_operator_visibility()
    
    # Test simple
    test_simple_operator_rendering()
    
    print("\n" + "="*70)
    print("ANÁLISIS COMPLETADO")
    print("="*70)