#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH DIRECTO DEL LAYOUT - Interceptar dibujar_almacen() directamente
"""

import os
import sys

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def get_tmx_layout_data():
    """Obtener datos del layout TMX actual"""
    
    try:
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        
        wrapper = get_dynamic_pathfinding_wrapper()
        if wrapper and hasattr(wrapper, 'integration'):
            integration = wrapper.integration
            if hasattr(integration, 'current_layout_data') and integration.current_layout_data:
                return integration.current_layout_data
                
        # Fallback: cargar directamente
        from dynamic_layout_loader import DynamicLayoutLoader
        wh1_path = "layouts/WH1.tmx"
        if os.path.exists(wh1_path):
            loader = DynamicLayoutLoader("layouts")
            return loader.load_layout(wh1_path)
            
    except Exception as e:
        print(f"[PATCH] Error obteniendo TMX: {e}")
    
    return None

def draw_tmx_layout(screen, almacen):
    """Dibujar layout basado en datos TMX"""
    
    import pygame
    
    # Debug: Only print once to avoid spam
    if not hasattr(draw_tmx_layout, '_debug_printed'):
        print("=" * 60)
        print("SUCCESS: TMX Layout Renderer is Working!")
        print("Layout System: TMX files now control visual display")
        print("=" * 60)
        draw_tmx_layout._debug_printed = True
    
    # Obtener datos TMX
    tmx_data = get_tmx_layout_data()
    
    if not tmx_data:
        print("[PATCH] No hay datos TMX, usando layout fallback")
        draw_fallback_layout(screen)
        return
        
    # Extraer información del TMX
    navigation_matrix = tmx_data.get('navigation_matrix', [])
    info = tmx_data.get('info', {})
    
    if not navigation_matrix:
        print("[PATCH] Matriz de navegación vacía")
        draw_fallback_layout(screen)
        return
        
    layout_name = info.get('name', 'TMX')
    width = len(navigation_matrix[0]) if navigation_matrix else 30
    height = len(navigation_matrix)
    
    print(f"[PATCH] Dibujando layout TMX: {layout_name} ({width}x{height})")
    
    # Limpiar pantalla
    screen.fill((245, 245, 245))
    
    # Calcular escala para que quepa en pantalla
    screen_width, screen_height = screen.get_size()
    
    # Dejar espacio para dashboard (120px abajo)
    available_width = screen_width - 100
    available_height = screen_height - 150
    
    tile_size_x = available_width // width
    tile_size_y = available_height // height
    tile_size = min(tile_size_x, tile_size_y, 25)  # Máximo 25px por tile
    
    # Centrar el layout
    total_layout_width = width * tile_size
    total_layout_height = height * tile_size
    offset_x = (screen_width - total_layout_width) // 2
    offset_y = (screen_height - total_layout_height - 120) // 2 + 20  # 20px desde arriba
    
    # Colores
    colors = {
        'navigable': (200, 255, 200),     # Verde claro - navegable
        'blocked': (139, 69, 19),         # Marrón - bloqueado (racks)
        'depot': (100, 149, 237),         # Azul - depot
        'inbound': (255, 182, 193),       # Rosa - inbound
        'corridor': (220, 220, 220)       # Gris claro - pasillos
    }
    
    # Dibujar cada tile
    for y in range(height):
        for x in range(width):
            pixel_x = offset_x + (x * tile_size)
            pixel_y = offset_y + (y * tile_size)
            
            # Determinar navegabilidad
            is_navigable = navigation_matrix[y][x] == 1 if y < len(navigation_matrix) and x < len(navigation_matrix[y]) else False
            
            # Determinar color según posición y navegabilidad
            if y == 0:  # Primera fila - depot
                color = colors['depot']
            elif y == height - 1:  # Última fila - inbound
                color = colors['inbound']
            elif y <= 2 or y >= height - 3:  # Pasillos principales
                color = colors['corridor']
            else:  # Zona central
                if is_navigable:
                    color = colors['navigable']  # Picking areas
                else:
                    color = colors['blocked']    # Racks
            
            # Dibujar tile
            rect = pygame.Rect(pixel_x, pixel_y, tile_size, tile_size)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 1)  # Borde negro
    
    # Dibujar información del layout
    draw_layout_info(screen, layout_name, width, height, tile_size, offset_x, offset_y)

def draw_layout_info(screen, layout_name, width, height, tile_size, offset_x, offset_y):
    """Dibujar información del layout"""
    
    import pygame
    
    try:
        font = pygame.font.Font(None, 24)
        
        # Título principal
        title_text = f"LAYOUT TMX: {layout_name}"
        title_surface = font.render(title_text, True, (255, 0, 0))
        screen.blit(title_surface, (10, 10))
        
        # Información técnica
        info_font = pygame.font.Font(None, 18)
        info_texts = [
            f"Dimension: {width}x{height}",
            f"Tile size: {tile_size}px",
            f"Posicion: ({offset_x}, {offset_y})"
        ]
        
        for i, text in enumerate(info_texts):
            info_surface = info_font.render(text, True, (0, 0, 150))
            screen.blit(info_surface, (10, 35 + i * 20))
            
        # Leyenda de colores
        legend_font = pygame.font.Font(None, 16)
        legend_y = 110
        legends = [
            ("Depot", (100, 149, 237)),
            ("Inbound", (255, 182, 193)),
            ("Racks", (139, 69, 19)),
            ("Picking", (200, 255, 200)),
            ("Pasillos", (220, 220, 220))
        ]
        
        for i, (label, color) in enumerate(legends):
            # Rectángulo de color
            color_rect = pygame.Rect(10, legend_y + i * 18, 15, 15)
            pygame.draw.rect(screen, color, color_rect)
            pygame.draw.rect(screen, (0, 0, 0), color_rect, 1)
            
            # Etiqueta
            label_surface = legend_font.render(label, True, (0, 0, 0))
            screen.blit(label_surface, (30, legend_y + i * 18))
            
    except Exception as e:
        print(f"[PATCH] Error dibujando info: {e}")

def draw_fallback_layout(screen):
    """Layout fallback simple"""
    
    import pygame
    
    screen.fill((245, 245, 245))
    
    try:
        font = pygame.font.Font(None, 36)
        text = font.render("LAYOUT TMX NO DISPONIBLE - USANDO FALLBACK", True, (255, 0, 0))
        screen.blit(text, (100, 100))
        
        # Dibujar un patrón simple
        screen_width, screen_height = screen.get_size()
        
        for y in range(0, screen_height - 150, 30):
            for x in range(0, screen_width, 60):
                if (x // 60 + y // 30) % 2 == 0:
                    color = (200, 200, 200)
                else:
                    color = (150, 150, 150)
                
                rect = pygame.Rect(x, y, 30, 30)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
                
    except Exception as e:
        print(f"[PATCH] Error en fallback: {e}")

def patch_dibujar_almacen():
    """Patchear la función dibujar_almacen directamente"""
    
    try:
        from visualization.original_renderer import dibujar_almacen
        import visualization.original_renderer as renderer_module
        
        # Guardar la función original (por si acaso)
        original_dibujar_almacen = dibujar_almacen
        
        # Reemplazar con nuestra función
        renderer_module.dibujar_almacen = draw_tmx_layout
        
        print("[PATCH] dibujar_almacen() patcheado exitosamente")
        return True
        
    except Exception as e:
        print(f"[PATCH] Error patcheando dibujar_almacen: {e}")
        return False

def patch_renderer_class():
    """Patchear también la clase RendererOriginal por si acaso"""
    
    try:
        from visualization.original_renderer import RendererOriginal
        
        # Patchear el método renderizar_frame_completo para usar nuestro dibujar_almacen
        original_renderizar = getattr(RendererOriginal, 'renderizar_frame_completo', None)
        
        def renderizar_frame_completo_patched(self):
            """Frame completo usando layout TMX"""
            
            from visualization.state import estado_visual
            
            almacen = estado_visual.get("almacen")
            
            # Usar nuestra función de dibujo TMX
            draw_tmx_layout(self.pantalla, almacen)
            
            # Continuar con operarios y panel
            try:
                from visualization.original_renderer import dibujar_operarios, dibujar_panel_informacion
                dibujar_operarios(self.pantalla)
                dibujar_panel_informacion(self.pantalla)
            except Exception as e:
                print(f"[PATCH] Error dibujando operarios/panel: {e}")
        
        # Aplicar patch
        RendererOriginal.renderizar_frame_completo = renderizar_frame_completo_patched
        
        print("[PATCH] RendererOriginal.renderizar_frame_completo() patcheado")
        return True
        
    except Exception as e:
        print(f"[PATCH] Error patcheando RendererOriginal: {e}")
        return False

def apply_all_patches():
    """Aplicar todos los patches necesarios"""
    
    print("=" * 60)
    print("APLICANDO PATCH DIRECTO DEL LAYOUT TMX")
    print("=" * 60)
    
    success_count = 0
    
    # Patch 1: dibujar_almacen function
    if patch_dibujar_almacen():
        print("[OK] Funcion dibujar_almacen patcheada")
        success_count += 1
    else:
        print("[ERROR] Error patcheando dibujar_almacen")
    
    # Patch 2: RendererOriginal class
    if patch_renderer_class():
        print("[OK] Clase RendererOriginal patcheada")
        success_count += 1
    else:
        print("[ERROR] Error patcheando RendererOriginal")
    
    if success_count == 2:
        print("\n[EXITO] TODOS LOS PATCHES APLICADOS EXITOSAMENTE")
        print("El simulador ahora deberia mostrar el layout TMX real")
    else:
        print(f"\n[WARNING] Solo {success_count}/2 patches aplicados")
    
    print("=" * 60)
    
    return success_count == 2

# Auto-aplicar patches al importar
if apply_all_patches():
    print("[PATCH] Sistema de layout TMX directo activado")
else:
    print("[PATCH] WARNING: No todos los patches se aplicaron correctamente")

def main():
    """Test del patch"""
    apply_all_patches()

if __name__ == "__main__":
    main()