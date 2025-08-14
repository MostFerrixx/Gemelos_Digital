#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARREGLAR LAYOUT DE PANTALLA: Ajustar dimensiones para que todo sea visible
"""

def fix_screen_layout():
    """Arreglar las dimensiones de la pantalla y el layout para máxima visibilidad"""
    
    print("=" * 60)
    print("ARREGLAR LAYOUT DE PANTALLA")
    print("=" * 60)
    
    try:
        # 1. Ajustar configuración de pantalla
        import config.settings as settings
        
        # Configurar para pantalla más pequeña pero funcional
        original_width = getattr(settings, 'ANCHO_PANTALLA', 1920)
        original_height = getattr(settings, 'ALTO_PANTALLA', 1080)
        
        # Ajustar a tamaño que quepa en pantallas comunes
        settings.ANCHO_PANTALLA = 1200
        settings.ALTO_PANTALLA = 700
        
        print(f"[SCREEN] Dimensiones ajustadas: {original_width}x{original_height} -> {settings.ANCHO_PANTALLA}x{settings.ALTO_PANTALLA}")
        
        # 2. Configurar el conversor TMX para nuevo tamaño
        try:
            from tmx_screen_converter import tmx_screen_converter
            
            # Forzar reinicialización con nuevas dimensiones
            if tmx_screen_converter.initialize_for_screen(settings.ANCHO_PANTALLA, settings.ALTO_PANTALLA):
                bounds = tmx_screen_converter.get_layout_bounds_on_screen()
                if bounds:
                    layout_width = bounds['max_x'] - bounds['min_x']
                    layout_height = bounds['max_y'] - bounds['min_y']
                    print(f"[TMX_CONVERTER] Layout en pantalla: {layout_width}x{layout_height} en posición ({bounds['min_x']}, {bounds['min_y']})")
                    
                    # Verificar que quepa
                    if layout_width <= settings.ANCHO_PANTALLA and layout_height <= settings.ALTO_PANTALLA:
                        print("[TMX_CONVERTER] ✓ Layout cabe perfectamente en pantalla")
                    else:
                        print("[TMX_CONVERTER] ! Layout puede cortarse, ajustando...")
                        
                        # Ajustar factores de escala
                        scale_x = (settings.ANCHO_PANTALLA * 0.9) / layout_width
                        scale_y = (settings.ALTO_PANTALLA * 0.9) / layout_height
                        final_scale = min(scale_x, scale_y)
                        
                        tmx_screen_converter.force_scale_factor(final_scale)
                        print(f"[TMX_CONVERTER] Escala ajustada a {final_scale:.2f}")
                        
        except Exception as e:
            print(f"[TMX_CONVERTER] Error: {e}")
        
        # 3. Patchear pygame para usar dimensiones ajustadas
        def patch_pygame_display():
            import pygame
            
            original_set_mode = pygame.display.set_mode
            
            def set_mode_fixed(size, flags=0, depth=0, display=0):
                # Usar nuestras dimensiones fijas
                adjusted_size = (settings.ANCHO_PANTALLA, settings.ALTO_PANTALLA)
                print(f"[PYGAME] Forzando dimensiones: {size} -> {adjusted_size}")
                
                # Siempre permitir redimensionamiento
                return original_set_mode(adjusted_size, flags | pygame.RESIZABLE, depth, display)
            
            pygame.display.set_mode = set_mode_fixed
            print("[PYGAME] Patch de dimensiones aplicado")
        
        patch_pygame_display()
        
        # 4. Configurar viewport optimizado para mostrar todo el contenido
        def configure_optimal_viewport():
            """Configurar viewport para mostrar todo el contenido importante"""
            
            try:
                from tmx_screen_converter import tmx_screen_converter
                
                # Centrar el layout en la pantalla
                layout_bounds = tmx_screen_converter.get_layout_bounds_on_screen()
                if layout_bounds:
                    # Calcular offset para centrar
                    layout_width = layout_bounds['max_x'] - layout_bounds['min_x']
                    layout_height = layout_bounds['max_y'] - layout_bounds['min_y']
                    
                    center_x = (settings.ANCHO_PANTALLA - layout_width) // 2
                    center_y = (settings.ALTO_PANTALLA - layout_height) // 2
                    
                    # Asegurar margen mínimo
                    center_x = max(20, center_x)
                    center_y = max(20, center_y)
                    
                    tmx_screen_converter.set_viewport_offset(center_x, center_y)
                    print(f"[VIEWPORT] Layout centrado en ({center_x}, {center_y})")
                    
            except Exception as e:
                print(f"[VIEWPORT] Error configurando viewport: {e}")
        
        configure_optimal_viewport()
        
        print("[SUCCESS] Configuración de pantalla optimizada")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error configurando pantalla: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_screen_layout():
    """Test para verificar que el layout cabe correctamente"""
    
    print("\n" + "=" * 60)
    print("TEST LAYOUT DE PANTALLA")
    print("=" * 60)
    
    try:
        import config.settings as settings
        from tmx_screen_converter import tmx_screen_converter, convert_operator_coordinates
        
        screen_w = settings.ANCHO_PANTALLA
        screen_h = settings.ALTO_PANTALLA
        
        print(f"Pantalla configurada: {screen_w}x{screen_h}")
        
        # Test de layout bounds
        if tmx_screen_converter.is_initialized():
            bounds = tmx_screen_converter.get_layout_bounds_on_screen()
            if bounds:
                print(f"Layout bounds: ({bounds['min_x']}, {bounds['min_y']}) - ({bounds['max_x']}, {bounds['max_y']})")
                print(f"Layout size: {bounds['max_x'] - bounds['min_x']}x{bounds['max_y'] - bounds['min_y']}")
                
                # Verificar que todo cabe
                if (bounds['min_x'] >= 0 and bounds['min_y'] >= 0 and 
                    bounds['max_x'] <= screen_w and bounds['max_y'] <= screen_h):
                    print("✓ Layout cabe completamente en pantalla")
                else:
                    print("⚠ Layout puede salirse de pantalla")
        
        # Test operadores de muestra
        test_operators = {
            1: {'x': 96, 'y': 96, 'tipo': 'terrestre', 'accion': 'Test'},
            2: {'x': 480, 'y': 480, 'tipo': 'montacargas', 'accion': 'Centro'},
            3: {'x': 800, 'y': 800, 'tipo': 'traspaleta', 'accion': 'Esquina'}
        }
        
        converted = convert_operator_coordinates(test_operators, screen_w, screen_h)
        
        print("\nPosiciones de operadores test:")
        for op_id, data in converted.items():
            tmx_x, tmx_y = data.get('tmx_x', 0), data.get('tmx_y', 0)
            screen_x, screen_y = data.get('x', 0), data.get('y', 0)
            
            visible = (0 <= screen_x <= screen_w and 0 <= screen_y <= screen_h)
            status = "✓ Visible" if visible else "✗ Fuera de pantalla"
            
            print(f"  Operario {op_id}: TMX({tmx_x}, {tmx_y}) -> Pantalla({screen_x}, {screen_y}) - {status}")
        
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
        print("Warning: TMX no se pudo activar")
    
    # Arreglar layout
    if fix_screen_layout():
        print("\n[OK] Layout de pantalla arreglado")
    else:
        print("\n[ERROR] No se pudo arreglar layout")
    
    # Test
    if test_screen_layout():
        print("\n[OK] Test de layout exitoso")
    else:
        print("\n[ERROR] Test de layout falló")
    
    print("\n" + "=" * 60)
    print("¡Ahora el simulador debería mostrar todo correctamente!")
    print("=" * 60)