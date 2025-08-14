#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PARCHE VISUAL - Cambiar la visualización gráfica para mostrar WH1
"""

import os
import sys

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def patch_visual_renderer():
    """Parchear el renderizador visual para mostrar WH1"""
    
    print("Aplicando parche visual para WH1...")
    
    try:
        from visualization.original_renderer import RendererOriginal
        
        # Método original de dibujar almacén
        original_draw_warehouse = getattr(RendererOriginal, '_dibujar_almacen', None)
        
        def _dibujar_almacen_wh1(self):
            """Dibujar almacén usando patrón WH1"""
            
            print("[VISUAL WH1] Renderizando layout WH1 personalizado")
            
            import pygame
            
            # Colores para WH1
            COLOR_SUELO = (200, 200, 200)      # Gris claro - suelo
            COLOR_RACK = (139, 69, 19)         # Marrón - racks
            COLOR_PICKING = (144, 238, 144)    # Verde claro - picking
            COLOR_PARKING = (173, 216, 230)    # Azul claro - parking
            COLOR_DEPOT = (255, 165, 0)        # Naranja - depot
            COLOR_INBOUND = (255, 192, 203)    # Rosa - inbound
            
            # Matriz WH1 (30x30)
            wh1_matrix = self._get_wh1_matrix()
            
            # Tamaño de cada celda en píxeles
            cell_width = 32
            cell_height = 32
            
            # Offset para centrar el layout
            offset_x = 50
            offset_y = 50
            
            # Dibujar cada celda según el patrón WH1
            for y in range(30):
                for x in range(30):
                    rect_x = offset_x + (x * cell_width)
                    rect_y = offset_y + (y * cell_height)
                    rect = pygame.Rect(rect_x, rect_y, cell_width, cell_height)
                    
                    # Determinar color según posición y patrón WH1
                    if y == 0:  # Fila superior - parking/depot
                        if x < 15:
                            color = COLOR_PARKING
                        else:
                            color = COLOR_DEPOT
                    elif y == 29:  # Fila inferior - inbound
                        color = COLOR_INBOUND
                    elif y in [1, 2, 27, 28]:  # Pasillos
                        color = COLOR_SUELO
                    elif 3 <= y <= 26:  # Zona de racks/picking
                        if x % 3 == 1:  # Racks
                            color = COLOR_RACK
                        else:  # Picking
                            color = COLOR_PICKING
                    else:
                        color = COLOR_SUELO
                    
                    # Dibujar celda
                    pygame.draw.rect(self.pantalla, color, rect)
                    pygame.draw.rect(self.pantalla, (0, 0, 0), rect, 1)  # Borde negro
            
            # Dibujar etiquetas
            self._dibujar_etiquetas_wh1(offset_x, offset_y, cell_width, cell_height)
        
        def _get_wh1_matrix(self):
            """Obtener matriz WH1"""
            # Esta es la matriz que ya está funcionando en navegación
            matrix = []
            for y in range(30):
                row = []
                for x in range(30):
                    if y == 0 or y == 29 or y in [1, 2, 27, 28]:
                        row.append(1)  # Navegable
                    elif 3 <= y <= 26:
                        if x % 3 == 1:
                            row.append(0)  # Racks
                        else:
                            row.append(1)  # Picking
                    else:
                        row.append(1)
                row.append(row)
            return matrix
        
        def _dibujar_etiquetas_wh1(self, offset_x, offset_y, cell_width, cell_height):
            """Dibujar etiquetas del layout WH1"""
            
            import pygame
            
            # Fuente para etiquetas
            try:
                font = pygame.font.Font(None, 24)
            except:
                font = pygame.font.SysFont('Arial', 16)
            
            # Etiquetas principales
            etiquetas = [
                ("PARKING", (offset_x + 100, offset_y - 20), (0, 0, 255)),
                ("DEPOT", (offset_x + 500, offset_y - 20), (255, 165, 0)),
                ("RACKS", (offset_x + 300, offset_y + 400), (139, 69, 19)),
                ("PICKING", (offset_x + 200, offset_y + 400), (0, 128, 0)),
                ("INBOUND", (offset_x + 300, offset_y + 950), (255, 20, 147)),
                ("WH1 LAYOUT", (offset_x + 300, offset_y + 1000), (0, 0, 0))
            ]
            
            for texto, pos, color in etiquetas:
                superficie = font.render(texto, True, color)
                self.pantalla.blit(superficie, pos)
        
        # Aplicar patch
        RendererOriginal._dibujar_almacen = _dibujar_almacen_wh1
        RendererOriginal._get_wh1_matrix = _get_wh1_matrix
        RendererOriginal._dibujar_etiquetas_wh1 = _dibujar_etiquetas_wh1
        
        print("[VISUAL WH1] Patch visual aplicado - Renderer modificado")
        return True
        
    except Exception as e:
        print(f"[VISUAL WH1] ERROR: {e}")
        return False

def patch_warehouse_background():
    """Parchear el fondo del almacén para mostrar WH1"""
    
    try:
        from visualization.original_renderer import RendererOriginal
        
        original_render_frame = getattr(RendererOriginal, 'renderizar_frame_completo', None)
        
        def renderizar_frame_completo_wh1(self):
            """Frame completo con fondo WH1"""
            
            # Limpiar pantalla con color de fondo
            self.pantalla.fill((240, 240, 240))  # Gris muy claro
            
            # Dibujar layout WH1 como fondo
            self._dibujar_almacen()
            
            # Continuar con renderizado normal de operarios, etc.
            if hasattr(self, '_renderizar_operarios'):
                self._renderizar_operarios()
            if hasattr(self, '_renderizar_tareas'):
                self._renderizar_tareas()
            if hasattr(self, '_renderizar_rutas'):
                self._renderizar_rutas()
        
        # Aplicar patch al frame completo
        RendererOriginal.renderizar_frame_completo = renderizar_frame_completo_wh1
        
        print("[VISUAL WH1] Patch de frame completo aplicado")
        return True
        
    except Exception as e:
        print(f"[VISUAL WH1] ERROR en frame: {e}")
        return False

def apply_visual_patches():
    """Aplicar todos los parches visuales"""
    
    print("="*60)
    print("APLICANDO PARCHES VISUALES PARA WH1")
    print("="*60)
    
    success = True
    
    # 1. Patch del renderer
    if patch_visual_renderer():
        print("EXITO: Renderer visual patcheado")
    else:
        print("ERROR: No se pudo patchear renderer")
        success = False
    
    # 2. Patch del fondo
    if patch_warehouse_background():
        print("EXITO: Fondo del almacén patcheado")
    else:
        print("ERROR: No se pudo patchear fondo")
        success = False
    
    if success:
        print("\nTODOS LOS PARCHES VISUALES APLICADOS")
        print("Ahora el simulador debería MOSTRAR tu layout WH1")
    else:
        print("\nERROR: Algunos parches visuales fallaron")
    
    print("="*60)
    return success

# Auto-aplicar parches al importar
if apply_visual_patches():
    print("[VISUAL WH1] Sistema visual interceptado - WH1 será visible")
else:
    print("[VISUAL WH1] WARNING: Parches visuales no aplicados completamente")

def main():
    """Aplicar parches visuales"""
    apply_visual_patches()

if __name__ == "__main__":
    main()