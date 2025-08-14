#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONVERTIDOR TMX VISUAL SIMPLE - Sin caracteres problemáticos
"""

import os
import sys

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def get_current_tmx_visual_data():
    """Obtener datos visuales del TMX actual"""
    
    try:
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        
        wrapper = get_dynamic_pathfinding_wrapper()
        if wrapper and hasattr(wrapper, 'integration') and wrapper.integration.current_layout_data:
            layout_data = wrapper.integration.current_layout_data
            return convert_tmx_to_visual_data(layout_data)
    except:
        pass
    
    return None

def convert_tmx_to_visual_data(layout_data):
    """Convertir datos TMX a formato visual optimizado"""
    
    if not layout_data or 'navigation_matrix' not in layout_data:
        return None
    
    navigation_matrix = layout_data['navigation_matrix']
    info = layout_data.get('info', {})
    
    width = info.get('width', len(navigation_matrix[0]) if navigation_matrix else 30)
    height = info.get('height', len(navigation_matrix))
    tile_size = min(20, max(10, 800 // max(width, height)))  # Escala dinámica
    
    visual_data = {
        'rack_positions': [],
        'picking_positions': [],
        'corridor_positions': [],
        'depot_positions': [],
        'inbound_positions': []
    }
    
    # Offset para centrar
    offset_x = 50
    offset_y = 50
    
    for y in range(height):
        for x in range(width):
            pixel_x = offset_x + (x * tile_size)
            pixel_y = offset_y + (y * tile_size)
            rect = {'x': pixel_x, 'y': pixel_y, 'width': tile_size, 'height': tile_size}
            
            # Determinar tipo basado en navegabilidad y posición
            is_navigable = navigation_matrix[y][x] == 1 if y < len(navigation_matrix) and x < len(navigation_matrix[y]) else False
            
            # Clasificar según patrón
            if y == 0:  # Primera fila - depot
                visual_data['depot_positions'].append(rect)
            elif y == height - 1:  # Última fila - inbound
                visual_data['inbound_positions'].append(rect)
            elif y <= 2 or y >= height - 3:  # Pasillos horizontales
                visual_data['corridor_positions'].append(rect)
            else:  # Zona central
                if not is_navigable:  # No navegable = rack
                    visual_data['rack_positions'].append(rect)
                else:  # Navegable = picking
                    visual_data['picking_positions'].append(rect)
    
    return visual_data

def get_wh1_visual_data():
    """Obtener datos visuales de WH1 directamente (fallback)"""
    
    visual_data = {
        'rack_positions': [],
        'picking_positions': [],
        'corridor_positions': [],
        'depot_positions': [],
        'inbound_positions': []
    }
    
    tile_size = 20  # Reducido para que quepa mejor
    offset_x = 50
    offset_y = 50
    
    # Generar posiciones basadas en patrón WH1 (30x30)
    for y in range(30):
        for x in range(30):
            pixel_x = offset_x + (x * tile_size)
            pixel_y = offset_y + (y * tile_size)
            rect = {'x': pixel_x, 'y': pixel_y, 'width': tile_size, 'height': tile_size}
            
            # Clasificar según patrón WH1
            if y == 0:  # Primera fila - depot/parking
                visual_data['depot_positions'].append(rect)
            elif y == 29:  # Última fila - inbound
                visual_data['inbound_positions'].append(rect)
            elif y in [1, 2, 27, 28]:  # Pasillos
                visual_data['corridor_positions'].append(rect)
            elif 3 <= y <= 26:  # Zona racks/picking
                if x % 3 == 1:  # Racks
                    visual_data['rack_positions'].append(rect)
                else:  # Picking
                    visual_data['picking_positions'].append(rect)
    
    return visual_data

def patch_renderer_simple():
    """Patch simple del renderizador"""
    
    try:
        from visualization.original_renderer import RendererOriginal
        import pygame
        
        def render_tmx_layout(self):
            """Renderizar layout TMX real"""
            
            # Fondo
            self.pantalla.fill((240, 240, 240))
            
            # Obtener datos del layout TMX actual
            visual_data = get_current_tmx_visual_data()
            
            if not visual_data:
                # Fallback a WH1 si no hay TMX
                visual_data = get_wh1_visual_data()
            
            # Colores
            colors = {
                'rack': (139, 69, 19),        # Marrón
                'picking': (144, 238, 144),   # Verde
                'corridor': (200, 200, 200),  # Gris
                'depot': (173, 216, 230),     # Azul
                'inbound': (255, 192, 203)    # Rosa
            }
            
            # Dibujar cada tipo
            for element_type, positions in visual_data.items():
                if not positions:
                    continue
                    
                # Color según tipo
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
                else:
                    color = (255, 255, 255)
                
                # Dibujar rectángulos
                for rect_data in positions:
                    rect = pygame.Rect(rect_data['x'], rect_data['y'], rect_data['width'], rect_data['height'])
                    pygame.draw.rect(self.pantalla, color, rect)
                    pygame.draw.rect(self.pantalla, (0, 0, 0), rect, 1)
            
            # Etiqueta del layout
            try:
                font = pygame.font.Font(None, 24)
                
                # Determinar nombre del layout
                layout_name = "LAYOUT TMX DESCONOCIDO"
                try:
                    from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
                    wrapper = get_dynamic_pathfinding_wrapper()
                    if wrapper and hasattr(wrapper, 'integration') and wrapper.integration.current_layout_data:
                        info = wrapper.integration.current_layout_data.get('info', {})
                        layout_name = f"LAYOUT: {info.get('name', 'TMX')}"
                    elif visual_data == get_wh1_visual_data():
                        layout_name = "LAYOUT: WH1 (FALLBACK)"
                except:
                    pass
                
                text = font.render(layout_name, True, (255, 0, 0))
                self.pantalla.blit(text, (10, 10))
                
                # Info adicional
                total_tiles = sum(len(positions) for positions in visual_data.values() if isinstance(positions, list))
                info_text = f"Tiles: {total_tiles}"
                info_surface = font.render(info_text, True, (0, 0, 255))
                self.pantalla.blit(info_surface, (10, 35))
                
            except:
                pass
        
        # Aplicar patch
        RendererOriginal.renderizar_frame_completo = render_tmx_layout
        print("PATCH VISUAL WH1 APLICADO")
        return True
        
    except Exception as e:
        print(f"ERROR PATCH: {e}")
        return False

# Auto-aplicar
if patch_renderer_simple():
    print("SISTEMA VISUAL WH1 ACTIVO")
else:
    print("ERROR ACTIVANDO VISUAL WH1")