#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH RENDERIZADO OPERARIOS: Corregir posiciones visuales usando conversión TMX
"""

def patch_operator_rendering():
    """Patchear la función dibujar_operarios para usar conversión TMX correcta"""
    
    try:
        import visualization.original_renderer as renderer_module
        from tmx_screen_converter import convert_operator_coordinates
        
        # Guardar función original
        original_dibujar_operarios = renderer_module.dibujar_operarios
        
        def dibujar_operarios_tmx_corrected(screen):
            """Función corregida que convierte coordenadas TMX a pantalla"""
            
            from visualization.state import estado_visual
            import pygame
            from config.colors import COLOR_TRASPALETA, COLOR_MONTACARGAS, COLOR_OPERARIO
            
            font = pygame.font.Font(None, 16)
            font_small = pygame.font.Font(None, 14)
            
            # Obtener dimensiones actuales de pantalla
            ancho_ventana, alto_ventana = screen.get_size()
            
            # NUEVO: Convertir coordenadas TMX a pantalla
            operarios_convertidos = convert_operator_coordinates(
                estado_visual.get("operarios", {}), 
                ancho_ventana, 
                alto_ventana
            )
            
            # Factor de escala para elementos gráficos
            factor_x = ancho_ventana / 1920  # Pantalla de referencia
            factor_y = alto_ventana / 1080
            factor_escala = min(factor_x, factor_y)
            
            for op_id, data in operarios_convertidos.items():
                # USAR COORDENADAS CONVERTIDAS (ya no son TMX brutos)
                x, y = int(data['x']), int(data['y'])
                
                # Determinar color según tipo de operario
                tipo_operario = data.get('tipo', 'general')
                if tipo_operario == 'traspaleta':
                    color_operario = COLOR_TRASPALETA  # Verde
                    color_borde = (0, 100, 0)
                elif tipo_operario == 'montacargas':
                    color_operario = COLOR_MONTACARGAS  # Naranja
                    color_borde = (200, 100, 0)
                else:  # terrestre u otros
                    color_operario = COLOR_OPERARIO  # Rojo
                    color_borde = (150, 0, 0)
                
                # Cambiar a color de espera si es necesario
                if 'Esperando' in data['accion'] or 'colisión' in data['accion']:
                    color_operario = tuple(min(255, c + 50) for c in color_operario)  # Aclarar color
                
                # Dibujar operario
                radio_operario = max(8, int(15 * factor_escala))
                pygame.draw.circle(screen, color_operario, (x, y), radio_operario)
                pygame.draw.circle(screen, color_borde, (x, y), radio_operario, max(1, int(2 * factor_escala)))
                
                # ID del operario
                texto_id = font.render(f"O{op_id}", True, (255, 255, 255))
                offset_id = max(5, int(10 * factor_escala))
                screen.blit(texto_id, (x - offset_id, y - int(8 * factor_escala)))
                
                # Acción del operario
                accion = data['accion']
                texto_accion = font_small.render(accion, True, (255, 255, 255))
                ancho_texto = texto_accion.get_width()
                alto_texto = max(14, int(18 * factor_escala))
                superficie_texto = pygame.Surface((ancho_texto + 6, alto_texto))
                superficie_texto.set_alpha(180)
                superficie_texto.fill((0, 0, 0))
                offset_x = max(15, int(20 * factor_escala))
                offset_y = max(10, int(15 * factor_escala))
                screen.blit(superficie_texto, (x + offset_x, y - offset_y))
                screen.blit(texto_accion, (x + offset_x + 3, y - int(12 * factor_escala)))
                
                # Tareas completadas
                texto_tareas = font_small.render(f"Tareas: {data['tareas_completadas']}", True, (100, 0, 0))
                screen.blit(texto_tareas, (x + offset_x, y + int(5 * factor_escala)))
                
                # DEBUG: Mostrar coordenadas TMX originales (temporal)
                if 'tmx_x' in data and 'tmx_y' in data:
                    texto_debug = font_small.render(f"TMX: ({data['tmx_x']:.0f},{data['tmx_y']:.0f})", True, (255, 255, 0))
                    screen.blit(texto_debug, (x + offset_x, y + int(25 * factor_escala)))
        
        # Aplicar patch
        renderer_module.dibujar_operarios = dibujar_operarios_tmx_corrected
        
        print("[PATCH_OPERATORS] dibujar_operarios() patcheado con conversión TMX")
        return True
        
    except Exception as e:
        print(f"[PATCH_OPERATORS] Error aplicando patch: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_coordinate_conversion():
    """Test de conversión de coordenadas"""
    
    print("\n" + "="*60)
    print("TEST CONVERSIÓN COORDENADAS TMX -> PANTALLA")
    print("="*60)
    
    try:
        # Activar TMX
        from force_tmx_activation import force_tmx_activation
        force_tmx_activation()
        
        # Test del convertidor
        from tmx_screen_converter import TMXScreenConverter
        converter = TMXScreenConverter()
        
        # Simular diferentes tamaños de pantalla
        screen_sizes = [
            (1920, 1080),  # Full HD
            (1366, 768),   # HD común
            (1280, 720),   # HD básico
        ]
        
        test_tmx_coords = [
            (0, 0),        # Esquina TMX
            (959, 959),    # Otra esquina TMX  
            (320, 128),    # Coord típica operario
            (837, 297),    # Otra coord típica
            (480, 480),    # Centro TMX
        ]
        
        for screen_w, screen_h in screen_sizes:
            print(f"\nPantalla: {screen_w}x{screen_h}")
            converter.initialize_for_screen(screen_w, screen_h)
            
            for tmx_x, tmx_y in test_tmx_coords:
                screen_x, screen_y = converter.convert_tmx_to_screen(tmx_x, tmx_y)
                print(f"  TMX ({tmx_x:3d},{tmx_y:3d}) -> Pantalla ({screen_x:4d},{screen_y:4d})")
            
            # Mostrar área de layout
            bounds = converter.get_layout_bounds_on_screen()
            if bounds:
                w = bounds['max_x'] - bounds['min_x']
                h = bounds['max_y'] - bounds['min_y']
                print(f"  Layout en pantalla: ({bounds['min_x']},{bounds['min_y']}) - {w}x{h}")
        
        return True
        
    except Exception as e:
        print(f"Error en test: {e}")
        return False

if __name__ == "__main__":
    print("PATCH RENDERIZADO DE OPERARIOS")
    print("="*60)
    
    # Test de conversión
    if test_coordinate_conversion():
        print("\n[OK] Test de conversión exitoso")
    else:
        print("\n[ERROR] Test de conversión falló")
    
    # Aplicar patch
    if patch_operator_rendering():
        print("[OK] Patch de renderizado aplicado")
        print("\nAhora los operarios deberían aparecer dentro del layout visual")
    else:
        print("[ERROR] No se pudo aplicar el patch")