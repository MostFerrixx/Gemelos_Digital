#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARREGLO COMPLETO RENDERIZADO OPERARIOS: Solución definitiva para mostrar operarios
"""

def create_enhanced_operator_renderer():
    """Crear función de renderizado mejorada que funcione definitivamente"""
    
    def dibujar_operarios_enhanced(screen):
        """Función de renderizado mejorada que SIEMPRE muestra operarios"""
        
        try:
            import pygame
            from visualization.state import estado_visual
            from tmx_screen_converter import convert_operator_coordinates
            
            # Obtener dimensiones de pantalla
            screen_width, screen_height = screen.get_size()
            
            # Obtener operarios del estado visual
            operarios = estado_visual.get("operarios", {})
            
            if not operarios:
                # DEBUG: Mostrar mensaje si no hay operarios
                font = pygame.font.Font(None, 24)
                text = font.render("NO HAY OPERARIOS EN ESTADO VISUAL", True, (255, 0, 0))
                screen.blit(text, (10, screen_height - 30))
                return
            
            # DEBUG: Mostrar cuántos operarios hay
            font_debug = pygame.font.Font(None, 20)
            debug_text = font_debug.render(f"Operarios: {len(operarios)}", True, (0, 255, 0))
            screen.blit(debug_text, (10, screen_height - 60))
            
            # Convertir coordenadas TMX a pantalla
            try:
                operarios_convertidos = convert_operator_coordinates(operarios, screen_width, screen_height)
            except Exception as e:
                # Fallback: usar coordenadas originales pero escaladas
                print(f"[RENDER] Error conversión TMX: {e}")
                operarios_convertidos = {}
                factor_x = screen_width / 1920
                factor_y = screen_height / 1080
                
                for op_id, data in operarios.items():
                    converted_data = data.copy()
                    converted_data['x'] = int(data.get('x', 0) * factor_x)
                    converted_data['y'] = int(data.get('y', 0) * factor_y)
                    operarios_convertidos[op_id] = converted_data
            
            # Dibujar cada operario
            for op_id, data in operarios_convertidos.items():
                x = int(data.get('x', 0))
                y = int(data.get('y', 0))
                tipo = data.get('tipo', 'unknown')
                accion = data.get('accion', 'Unknown')
                tareas = data.get('tareas_completadas', 0)
                
                # DEBUG: Mostrar coordenadas TMX originales si existen
                if 'tmx_x' in data and 'tmx_y' in data:
                    tmx_pos = f"TMX:({data['tmx_x']:.0f},{data['tmx_y']:.0f})"
                else:
                    tmx_pos = f"Legacy:({data.get('x',0):.0f},{data.get('y',0):.0f})"
                
                # Determinar color por tipo
                if tipo == 'montacargas':
                    color_operario = (255, 165, 0)  # Naranja
                    color_borde = (200, 100, 0)
                elif tipo == 'traspaleta':
                    color_operario = (0, 150, 0)    # Verde
                    color_borde = (0, 100, 0)
                else:  # terrestre
                    color_operario = (227, 63, 44)  # Rojo
                    color_borde = (150, 0, 0)
                
                # Dibujar operario (círculo más grande para que sea visible)
                radio = 12  # Radio fijo más grande
                pygame.draw.circle(screen, color_operario, (x, y), radio)
                pygame.draw.circle(screen, color_borde, (x, y), radio, 2)
                
                # ID del operario (texto más grande)
                font = pygame.font.Font(None, 18)
                texto_id = font.render(f"O{op_id}", True, (255, 255, 255))
                text_rect = texto_id.get_rect(center=(x, y))
                screen.blit(texto_id, text_rect)
                
                # Información del operario (con fondo)
                font_info = pygame.font.Font(None, 14)
                info_lines = [
                    f"O{op_id} ({tipo})",
                    accion[:20] + "..." if len(accion) > 20 else accion,
                    f"Tareas: {tareas}",
                    tmx_pos
                ]
                
                # Calcular posición del texto
                text_x = x + 15
                text_y = y - 30
                
                # Dibujar fondo del texto
                max_width = max(font_info.size(line)[0] for line in info_lines)
                bg_rect = pygame.Rect(text_x - 2, text_y - 2, max_width + 4, len(info_lines) * 16 + 4)
                bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
                bg_surface.set_alpha(200)
                bg_surface.fill((0, 0, 0))
                screen.blit(bg_surface, bg_rect)
                
                # Dibujar líneas de información
                for i, line in enumerate(info_lines):
                    color = (255, 255, 255) if i < 2 else (200, 200, 200)
                    texto = font_info.render(line, True, color)
                    screen.blit(texto, (text_x, text_y + i * 16))
                
                # DEBUG: Dibujar coordenadas de pantalla
                coord_text = font_info.render(f"Screen:({x},{y})", True, (255, 255, 0))
                screen.blit(coord_text, (text_x, text_y + len(info_lines) * 16))
            
            # Mostrar información de área de layout
            try:
                from tmx_screen_converter import tmx_screen_converter
                if tmx_screen_converter.is_initialized():
                    bounds = tmx_screen_converter.get_layout_bounds_on_screen()
                    if bounds:
                        # Dibujar borde del área de layout
                        layout_rect = pygame.Rect(
                            bounds['min_x'], bounds['min_y'],
                            bounds['max_x'] - bounds['min_x'],
                            bounds['max_y'] - bounds['min_y']
                        )
                        pygame.draw.rect(screen, (255, 0, 255), layout_rect, 2)
                        
                        # Mostrar info del área
                        area_text = font_debug.render(
                            f"Layout area: {bounds['min_x']},{bounds['min_y']} - {bounds['max_x']}x{bounds['max_y']}", 
                            True, (255, 0, 255)
                        )
                        screen.blit(area_text, (10, screen_height - 90))
            except Exception as e:
                pass
            
        except Exception as e:
            # Emergency fallback: mostrar error en pantalla
            try:
                import pygame
                font = pygame.font.Font(None, 24)
                error_text = font.render(f"ERROR RENDERIZADO: {str(e)[:50]}", True, (255, 0, 0))
                screen.blit(error_text, (10, 10))
            except:
                pass
            print(f"[RENDER] Error crítico: {e}")
    
    return dibujar_operarios_enhanced

def force_patch_operator_rendering():
    """Forzar el patch de renderizado con múltiples estrategias"""
    
    print("[FIX_RENDER] Aplicando patch de renderizado mejorado...")
    
    try:
        # Estrategia 1: Patch directo del módulo
        import visualization.original_renderer as renderer_module
        
        enhanced_renderer = create_enhanced_operator_renderer()
        
        # Guardar función original como respaldo
        if hasattr(renderer_module, 'dibujar_operarios'):
            renderer_module._original_dibujar_operarios = renderer_module.dibujar_operarios
        
        # Aplicar nuevo renderizador
        renderer_module.dibujar_operarios = enhanced_renderer
        
        print("[FIX_RENDER] OK Patch aplicado a visualization.original_renderer")
        
        # Estrategia 2: Patch del método en la clase RendererOriginal
        from visualization.original_renderer import RendererOriginal
        
        def renderizar_frame_completo_fixed(self):
            """Renderizado completo con operarios mejorados"""
            
            from visualization.state import estado_visual
            
            almacen = estado_visual.get("almacen")
            
            # Dibujar layout (ya funciona)
            try:
                from direct_layout_patch import draw_tmx_layout
                draw_tmx_layout(self.pantalla, almacen)
            except Exception as e:
                # Fallback a función original
                from visualization.original_renderer import dibujar_almacen
                dibujar_almacen(self.pantalla, almacen)
            
            # Dibujar operarios con función mejorada
            enhanced_renderer(self.pantalla)
            
            # Dibujar panel de información
            try:
                from visualization.original_renderer import dibujar_panel_informacion
                dibujar_panel_informacion(self.pantalla)
            except Exception as e:
                print(f"[FIX_RENDER] Error panel info: {e}")
        
        # Aplicar patch a la clase
        RendererOriginal.renderizar_frame_completo = renderizar_frame_completo_fixed
        
        print("[FIX_RENDER] OK Patch aplicado a RendererOriginal.renderizar_frame_completo")
        
        return True
        
    except Exception as e:
        print(f"[FIX_RENDER] Error aplicando patch: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_screen_dimensions():
    """Arreglar las dimensiones de pantalla para que quepa todo el contenido"""
    
    print("[FIX_SCREEN] Arreglando dimensiones de pantalla...")
    
    try:
        # Modificar las configuraciones de pantalla en settings
        import config.settings as settings
        
        # Ajustar para pantallas más pequeñas
        if hasattr(settings, 'ANCHO_PANTALLA'):
            settings.ANCHO_PANTALLA = min(settings.ANCHO_PANTALLA, 1200)
        if hasattr(settings, 'ALTO_PANTALLA'):
            settings.ALTO_PANTALLA = min(settings.ALTO_PANTALLA, 700)
        
        print(f"[FIX_SCREEN] Dimensiones ajustadas: {getattr(settings, 'ANCHO_PANTALLA', 'N/A')}x{getattr(settings, 'ALTO_PANTALLA', 'N/A')}")
        
        # También intentar modificar la inicialización de pygame
        def patch_pygame_init():
            import pygame
            original_set_mode = pygame.display.set_mode
            
            def set_mode_adjusted(size, flags=0, depth=0, display=0):
                # Ajustar tamaño si es muy grande
                adjusted_size = (
                    min(size[0], 1200),
                    min(size[1], 700)
                )
                print(f"[FIX_SCREEN] Ajustando ventana: {size} -> {adjusted_size}")
                return original_set_mode(adjusted_size, flags | pygame.RESIZABLE, depth, display)
            
            pygame.display.set_mode = set_mode_adjusted
        
        patch_pygame_init()
        
        return True
        
    except Exception as e:
        print(f"[FIX_SCREEN] Error: {e}")
        return False

if __name__ == "__main__":
    print("ARREGLO COMPLETO DE RENDERIZADO DE OPERARIOS")
    print("="*60)
    
    # Activar TMX
    try:
        from force_tmx_activation import force_tmx_activation
        force_tmx_activation()
    except ImportError:
        print("Error: No se pudo activar TMX")
    
    # Arreglar renderizado
    if force_patch_operator_rendering():
        print("[OK] Patch de renderizado aplicado exitosamente")
    else:
        print("[ERROR] No se pudo aplicar patch de renderizado")
    
    # Arreglar dimensiones
    if fix_screen_dimensions():
        print("[OK] Dimensiones de pantalla ajustadas")
    else:
        print("[ERROR] No se pudieron ajustar dimensiones")
    
    print("\n[INFO] Ahora ejecuta el simulador - los operarios deberían ser visibles")