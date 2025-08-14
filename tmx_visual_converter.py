#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONVERTIDOR TMX → VISUAL - Conectar datos TMX con renderizado visual
"""

import os
import sys
import json

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

class TMXVisualConverter:
    """Convierte datos TMX a formato visual para el renderizador"""
    
    def __init__(self):
        self.current_tmx_layout = None
        self.visual_data = None
        
    def load_current_tmx_layout(self):
        """Obtener el layout TMX que está siendo usado actualmente"""
        
        try:
            from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
            wrapper = get_dynamic_pathfinding_wrapper()
            
            # Obtener el layout actualmente cargado
            if hasattr(wrapper, 'current_layout_data') and wrapper.current_layout_data:
                self.current_tmx_layout = wrapper.current_layout_data
                print(f"[TMX→VISUAL] Layout TMX encontrado: {wrapper.current_layout_data.get('info', {}).get('name', 'Unknown')}")
                return True
            else:
                # Intentar cargar directamente si no está en wrapper
                print("[TMX→VISUAL] Intentando cargar layout TMX directamente...")
                return self._load_tmx_directly()
                
        except Exception as e:
            print(f"[TMX→VISUAL] Error obteniendo layout: {e}")
            return self._load_tmx_directly()
    
    def _load_tmx_directly(self):
        """Cargar TMX directamente desde el archivo"""
        
        try:
            from dynamic_layout_loader import DynamicLayoutLoader
            
            # Buscar archivo WH1.tmx
            wh1_path = "layouts/WH1.tmx"
            if os.path.exists(wh1_path):
                loader = DynamicLayoutLoader("layouts")
                layout_data = loader.load_layout(wh1_path)
                
                if layout_data:
                    self.current_tmx_layout = layout_data
                    print(f"[TMX→VISUAL] WH1.tmx cargado directamente")
                    return True
            
            print(f"[TMX→VISUAL] No se pudo cargar TMX directamente")
            return False
            
        except Exception as e:
            print(f"[TMX→VISUAL] Error carga directa: {e}")
            return False
    
    def convert_tmx_to_visual_coordinates(self):
        """Convertir datos TMX a coordenadas visuales"""
        
        if not self.current_tmx_layout:
            return None
            
        # Obtener matriz de navegación del TMX
        navigation_matrix = self.current_tmx_layout.get('navigation_matrix', [])
        if not navigation_matrix:
            return None
            
        info = self.current_tmx_layout.get('info', {})
        width = info.get('width', 30)
        height = info.get('height', 30)
        tile_width = info.get('tile_width', 32)
        tile_height = info.get('tile_height', 32)
        
        print(f"[TMX→VISUAL] Convirtiendo layout {width}x{height}")
        
        # Configuración visual
        visual_data = {
            'rack_positions': [],
            'corridor_positions': [],
            'picking_positions': [],
            'depot_positions': [],
            'inbound_positions': [],
            'floor_positions': [],
            'layout_bounds': {
                'width': width * tile_width,
                'height': height * tile_height,
                'tile_width': tile_width,
                'tile_height': tile_height
            }
        }
        
        # Convertir cada tile a coordenadas visuales
        for y in range(len(navigation_matrix)):
            for x in range(len(navigation_matrix[y])):
                
                # Coordenadas de píxeles
                pixel_x = x * tile_width
                pixel_y = y * tile_height
                rect = {
                    'x': pixel_x,
                    'y': pixel_y,
                    'width': tile_width,
                    'height': tile_height
                }
                
                # Determinar tipo de tile basado en posición y navegabilidad
                is_navigable = navigation_matrix[y][x] == 1
                
                # Clasificar según patrón de tu WH1
                if y == 0:  # Primera fila - parking/depot
                    if x < width // 2:
                        visual_data['depot_positions'].append(rect)  # Parking/depot
                    else:
                        visual_data['depot_positions'].append(rect)  # Depot
                elif y == height - 1:  # Última fila - inbound
                    visual_data['inbound_positions'].append(rect)
                elif y in [1, 2, height-3, height-2]:  # Pasillos principales
                    visual_data['corridor_positions'].append(rect)
                elif 3 <= y <= height-4:  # Zona de racks/picking
                    if not is_navigable:  # Tile no navegable = rack
                        visual_data['rack_positions'].append(rect)
                    else:  # Tile navegable = picking point
                        visual_data['picking_positions'].append(rect)
                else:
                    if is_navigable:
                        visual_data['floor_positions'].append(rect)
                    else:
                        visual_data['rack_positions'].append(rect)
        
        self.visual_data = visual_data
        
        # Estadísticas
        total_racks = len(visual_data['rack_positions'])
        total_picking = len(visual_data['picking_positions'])
        total_corridors = len(visual_data['corridor_positions'])
        
        print(f"[TMX→VISUAL] Convertido: {total_racks} racks, {total_picking} picking, {total_corridors} pasillos")
        
        return visual_data
    
    def get_visual_data(self):
        """Obtener datos visuales del layout TMX actual"""
        
        if not self.load_current_tmx_layout():
            return None
            
        return self.convert_tmx_to_visual_coordinates()

# Instancia global del convertidor
tmx_visual_converter = TMXVisualConverter()

def get_tmx_visual_data():
    """Función helper para obtener datos visuales del TMX"""
    return tmx_visual_converter.get_visual_data()

def patch_renderer_with_tmx_data():
    """Parchear el renderizador para usar datos TMX"""
    
    try:
        from visualization.original_renderer import RendererOriginal
        
        # Método original de renderizado
        original_render_frame = getattr(RendererOriginal, 'renderizar_frame_completo', None)
        
        def renderizar_frame_completo_tmx(self):
            """Renderizar usando datos TMX convertidos"""
            
            # Limpiar pantalla
            self.pantalla.fill((240, 240, 240))  # Fondo gris claro
            
            # Obtener datos visuales del TMX
            visual_data = get_tmx_visual_data()
            
            if visual_data:
                print("[TMX→VISUAL] Renderizando layout desde TMX")
                self._render_tmx_layout(visual_data)
            else:
                print("[TMX→VISUAL] Sin datos TMX, usando renderizado original")
                if original_render_frame:
                    original_render_frame(self)
                    
        def _render_tmx_layout(self, visual_data):
            """Renderizar layout basado en datos TMX"""
            
            import pygame
            
            # Colores para cada tipo de elemento
            colors = {
                'rack': (139, 69, 19),        # Marrón - racks
                'picking': (144, 238, 144),   # Verde claro - picking
                'corridor': (200, 200, 200),  # Gris - pasillos
                'depot': (173, 216, 230),     # Azul claro - depot
                'inbound': (255, 192, 203),   # Rosa - inbound
                'floor': (245, 245, 245)     # Gris muy claro - suelo
            }
            
            # Dibujar cada tipo de elemento
            for element_type, positions in visual_data.items():
                if element_type == 'layout_bounds':
                    continue
                    
                # Determinar color
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
                    color = colors['floor']
                
                # Dibujar cada rectángulo
                for rect_data in positions:
                    rect = pygame.Rect(
                        rect_data['x'], 
                        rect_data['y'], 
                        rect_data['width'], 
                        rect_data['height']
                    )
                    pygame.draw.rect(self.pantalla, color, rect)
                    pygame.draw.rect(self.pantalla, (0, 0, 0), rect, 1)  # Borde negro
            
            # Dibujar etiqueta indicando que usa TMX
            self._draw_tmx_label(visual_data)
            
        def _draw_tmx_label(self, visual_data):
            """Dibujar etiqueta indicando uso de TMX"""
            
            import pygame
            
            try:
                font = pygame.font.Font(None, 36)
            except:
                font = pygame.font.SysFont('Arial', 24)
            
            bounds = visual_data.get('layout_bounds', {})
            layout_name = f"WH1 TMX LAYOUT ({bounds.get('width', 0)}x{bounds.get('height', 0)})"
            
            text_surface = font.render(layout_name, True, (255, 0, 0))  # Rojo
            self.pantalla.blit(text_surface, (10, 10))
            
            # Estadísticas
            stats_text = f"Racks: {len(visual_data.get('rack_positions', []))} | Picking: {len(visual_data.get('picking_positions', []))}"
            stats_surface = font.render(stats_text, True, (0, 0, 255))  # Azul
            self.pantalla.blit(stats_surface, (10, 50))
        
        # Aplicar parches
        RendererOriginal.renderizar_frame_completo = renderizar_frame_completo_tmx
        RendererOriginal._render_tmx_layout = _render_tmx_layout
        RendererOriginal._draw_tmx_label = _draw_tmx_label
        
        print("[TMX→VISUAL] Renderer patcheado para usar datos TMX")
        return True
        
    except Exception as e:
        print(f"[TMX→VISUAL] Error patcheando renderer: {e}")
        return False

# Auto-aplicar patch al importar
if patch_renderer_with_tmx_data():
    print("[TMX→VISUAL] Sistema de renderizado conectado con TMX")
else:
    print("[TMX→VISUAL] WARNING: No se pudo conectar renderizado con TMX")