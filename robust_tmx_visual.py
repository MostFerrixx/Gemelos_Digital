#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONVERTIDOR TMX VISUAL ROBUSTO - Sistema visual con manejo de errores
"""

import os
import sys

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def get_layout_visual_data():
    """Obtener datos visuales del layout actual con fallbacks robustos"""
    
    # Intentar obtener TMX real desde el wrapper global
    try:
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        
        wrapper = get_dynamic_pathfinding_wrapper()
        print(f"[VISUAL DEBUG] Wrapper: {wrapper}")
        
        if wrapper and hasattr(wrapper, 'integration'):
            integration = wrapper.integration
            print(f"[VISUAL DEBUG] Integration: {integration}")
            print(f"[VISUAL DEBUG] Has current_layout_data: {hasattr(integration, 'current_layout_data')}")
            
            if hasattr(integration, 'current_layout_data') and integration.current_layout_data:
                layout_data = integration.current_layout_data
                layout_name = layout_data.get('info', {}).get('name', 'Unknown')
                print(f"[VISUAL] Usando layout TMX: {layout_name}")
                result = convert_tmx_to_visual_optimized(layout_data)
                if result:
                    return result
                else:
                    print("[VISUAL] Error convirtiendo TMX, usando fallback")
            else:
                print("[VISUAL] No hay current_layout_data en integration")
        else:
            print("[VISUAL] No wrapper o no integration disponible")
            
    except Exception as e:
        print(f"[VISUAL] Error accediendo TMX: {e}")
        import traceback
        traceback.print_exc()
    
    # Intentar cargar directamente desde archivo WH1.tmx
    try:
        print("[VISUAL] Intentando cargar WH1.tmx directamente...")
        direct_data = load_wh1_directly()
        if direct_data:
            return direct_data
    except Exception as e:
        print(f"[VISUAL] Error carga directa: {e}")
    
    # Fallback: Layout por defecto escalado
    print("[VISUAL] Usando layout fallback optimizado")
    return get_optimized_fallback_layout()

def load_wh1_directly():
    """Cargar WH1.tmx directamente desde archivo"""
    
    try:
        from dynamic_layout_loader import DynamicLayoutLoader
        
        wh1_path = "layouts/WH1.tmx"
        if os.path.exists(wh1_path):
            loader = DynamicLayoutLoader("layouts")
            layout_data = loader.load_layout(wh1_path)
            
            if layout_data and 'navigation_matrix' in layout_data:
                print(f"[VISUAL] WH1.tmx cargado directamente desde archivo")
                return convert_tmx_to_visual_optimized(layout_data)
        
        print(f"[VISUAL] WH1.tmx no encontrado en {wh1_path}")
        return None
        
    except Exception as e:
        print(f"[VISUAL] Error cargando WH1 directamente: {e}")
        return None

def convert_tmx_to_visual_optimized(layout_data):
    """Convertir TMX a visual con escala optimizada"""
    
    try:
        navigation_matrix = layout_data.get('navigation_matrix', [])
        info = layout_data.get('info', {})
        
        if not navigation_matrix:
            return None
        
        height = len(navigation_matrix)
        width = len(navigation_matrix[0]) if navigation_matrix else 0
        
        # Escala dinámica para que quepa en pantalla
        max_screen_width = 1200
        max_screen_height = 700
        
        tile_size_x = min(20, max_screen_width // width)
        tile_size_y = min(20, max_screen_height // height)
        tile_size = min(tile_size_x, tile_size_y)
        
        # Centrar en pantalla
        total_width = width * tile_size
        total_height = height * tile_size
        offset_x = max(10, (max_screen_width - total_width) // 2)
        offset_y = max(10, (max_screen_height - total_height) // 2)
        
        visual_data = {
            'rack_positions': [],
            'picking_positions': [],
            'corridor_positions': [],
            'depot_positions': [],
            'inbound_positions': [],
            'layout_info': {
                'width': width,
                'height': height,
                'tile_size': tile_size,
                'total_width': total_width,
                'total_height': total_height
            }
        }
        
        # Convertir matriz a rectangulos
        for y in range(height):
            for x in range(width):
                pixel_x = offset_x + (x * tile_size)
                pixel_y = offset_y + (y * tile_size)
                rect = {'x': pixel_x, 'y': pixel_y, 'width': tile_size, 'height': tile_size}
                
                # Determinar navegabilidad
                is_navigable = navigation_matrix[y][x] == 1 if y < len(navigation_matrix) and x < len(navigation_matrix[y]) else False
                
                # Clasificar por posición y navegabilidad
                if y == 0:  # Primera fila
                    visual_data['depot_positions'].append(rect)
                elif y == height - 1:  # Última fila
                    visual_data['inbound_positions'].append(rect)
                elif y <= 2 or y >= height - 3:  # Pasillos principales
                    visual_data['corridor_positions'].append(rect)
                else:  # Zona central
                    if not is_navigable:
                        visual_data['rack_positions'].append(rect)
                    else:
                        visual_data['picking_positions'].append(rect)
        
        print(f"[VISUAL] Layout TMX convertido: {width}x{height}, tile_size={tile_size}")
        return visual_data
        
    except Exception as e:
        print(f"[VISUAL] Error convirtiendo TMX: {e}")
        return None

def get_optimized_fallback_layout():
    """Layout fallback optimizado para pantalla"""
    
    # Layout más pequeño para que quepa
    width, height = 40, 25
    tile_size = 15
    offset_x, offset_y = 50, 50
    
    visual_data = {
        'rack_positions': [],
        'picking_positions': [],
        'corridor_positions': [],
        'depot_positions': [],
        'inbound_positions': [],
        'layout_info': {
            'width': width,
            'height': height,
            'tile_size': tile_size,
            'total_width': width * tile_size,
            'total_height': height * tile_size
        }
    }
    
    # Patrón de almacén típico
    for y in range(height):
        for x in range(width):
            pixel_x = offset_x + (x * tile_size)
            pixel_y = offset_y + (y * tile_size)
            rect = {'x': pixel_x, 'y': pixel_y, 'width': tile_size, 'height': tile_size}
            
            if y == 0:  # Depot
                visual_data['depot_positions'].append(rect)
            elif y == height - 1:  # Inbound
                visual_data['inbound_positions'].append(rect)
            elif y in [1, 2, height-3, height-2]:  # Pasillos
                visual_data['corridor_positions'].append(rect)
            elif x % 4 == 1 or x % 4 == 2:  # Racks
                visual_data['rack_positions'].append(rect)
            else:  # Picking
                visual_data['picking_positions'].append(rect)
    
    return visual_data

def patch_renderer_robust():
    """Patch robusto del renderizador"""
    
    try:
        from visualization.original_renderer import RendererOriginal
        import pygame
        
        def render_layout_robust(self):
            """Renderizar layout con manejo robusto de errores"""
            
            try:
                # Limpiar pantalla
                self.pantalla.fill((245, 245, 245))
                
                # Obtener datos visuales (esto se ejecuta cada frame)
                visual_data = get_layout_visual_data()
                
                if not visual_data:
                    # Fallback extremo: solo texto
                    self._render_error_message("Error: No layout data available")
                    return
                
                # Renderizar layout
                self._render_layout_data(visual_data)
                
                # Renderizar información
                self._render_layout_info(visual_data)
                
            except Exception as e:
                # Fallback de emergencia
                try:
                    font = pygame.font.Font(None, 24)
                    error_text = f"Error renderizando: {str(e)[:50]}"
                    surface = font.render(error_text, True, (255, 0, 0))
                    self.pantalla.blit(surface, (10, 10))
                except:
                    pass
        
        def _render_layout_data(self, visual_data):
            """Renderizar datos del layout"""
            
            import pygame
            
            # Colores optimizados
            colors = {
                'rack': (139, 69, 19),        # Marrón - racks
                'picking': (144, 238, 144),   # Verde claro - picking
                'corridor': (200, 200, 200),  # Gris - pasillos
                'depot': (100, 149, 237),     # Azul - depot
                'inbound': (255, 182, 193)    # Rosa claro - inbound
            }
            
            # Renderizar cada tipo
            for element_type, positions in visual_data.items():
                if element_type == 'layout_info' or not isinstance(positions, list):
                    continue
                
                # Determinar color
                color = (128, 128, 128)  # Gris por defecto
                if 'rack' in element_type:
                    color = colors['rack']
                elif 'picking' in element_type:
                    color = colors['picking']
                elif 'corridor' in element_type:
                    color = colors['corridor']
                elif 'depot' in element_type:
                    color = colors['depot']
                elif 'inbound' in element_type:
                    color = colors['inbound']
                
                # Dibujar rectangulos
                for rect_data in positions:
                    try:
                        rect = pygame.Rect(rect_data['x'], rect_data['y'], 
                                         rect_data['width'], rect_data['height'])
                        pygame.draw.rect(self.pantalla, color, rect)
                        pygame.draw.rect(self.pantalla, (0, 0, 0), rect, 1)
                    except:
                        continue
        
        def _render_layout_info(self, visual_data):
            """Renderizar información del layout"""
            
            import pygame
            
            try:
                font = pygame.font.Font(None, 20)
                
                # Información del layout
                layout_info = visual_data.get('layout_info', {})
                width = layout_info.get('width', 0)
                height = layout_info.get('height', 0)
                tile_size = layout_info.get('tile_size', 0)
                
                # Determinar fuente del layout
                layout_source = "TMX"
                try:
                    from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
                    wrapper = get_dynamic_pathfinding_wrapper()
                    if wrapper and hasattr(wrapper, 'integration'):
                        integration = wrapper.integration
                        if hasattr(integration, 'current_layout_data') and integration.current_layout_data:
                            info = integration.current_layout_data.get('info', {})
                            layout_name = info.get('name', 'TMX')
                            layout_source = f"TMX: {layout_name}"
                        else:
                            layout_source = "FALLBACK"
                    else:
                        layout_source = "FALLBACK"
                except:
                    layout_source = "UNKNOWN"
                
                # Textos informativos
                texts = [
                    f"Layout: {layout_source}",
                    f"Size: {width}x{height} (tile: {tile_size}px)",
                    f"Racks: {len(visual_data.get('rack_positions', []))}",
                    f"Picking: {len(visual_data.get('picking_positions', []))}"
                ]
                
                # Renderizar textos
                for i, text in enumerate(texts):
                    try:
                        color = (255, 0, 0) if i == 0 else (0, 0, 150)
                        surface = font.render(text, True, color)
                        self.pantalla.blit(surface, (10, 10 + i * 22))
                    except:
                        continue
                        
            except Exception as e:
                pass
        
        def _render_error_message(self, message):
            """Renderizar mensaje de error"""
            
            import pygame
            
            try:
                font = pygame.font.Font(None, 36)
                surface = font.render(message, True, (255, 0, 0))
                self.pantalla.blit(surface, (100, 100))
            except:
                pass
        
        # Aplicar patches
        RendererOriginal.renderizar_frame_completo = render_layout_robust
        RendererOriginal._render_layout_data = _render_layout_data
        RendererOriginal._render_layout_info = _render_layout_info
        RendererOriginal._render_error_message = _render_error_message
        
        print("[VISUAL] Patch robusto aplicado exitosamente")
        return True
        
    except Exception as e:
        print(f"[VISUAL] Error aplicando patch: {e}")
        return False

# Auto-aplicar patch
if patch_renderer_robust():
    print("[VISUAL] Sistema visual robusto activado")
else:
    print("[VISUAL] ERROR: No se pudo activar sistema visual")

def main():
    """Test del sistema visual"""
    patch_renderer_robust()

if __name__ == "__main__":
    main()