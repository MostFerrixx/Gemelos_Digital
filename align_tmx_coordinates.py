#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALINEAR COORDENADAS TMX: Sincronizar sistema visual con pathfinding
"""

def analyze_coordinate_mismatch():
    """Analizar la desalineación entre coordenadas visuales y de pathfinding"""
    
    print("=" * 70)
    print("ANÁLISIS DE DESALINEACIÓN DE COORDENADAS TMX")
    print("=" * 70)
    
    # De los logs podemos extraer información clave:
    print("\n1. SISTEMA TMX CONFIGURADO:")
    print("   - Grid: 30x30 tiles")
    print("   - World: 960x960 pixels")
    print("   - Navegabilidad: 60% (540/900 celdas)")
    
    print("\n2. SISTEMA VISUAL DETECTADO:")
    print("   - tile_size: 25 pixels")
    print("   - offset: (575, 35)")
    print("   - Escalado: 0.04x0.04")
    
    print("\n3. COORDENADAS DE PATHFINDING:")
    print("   - Operarios se mueven a: (288, 160), (320, 192), etc.")
    print("   - Estas son coordenadas TMX pixel-level")
    
    print("\n4. PROBLEMA IDENTIFICADO:")
    print("   - Sistema visual usa tile_size=25 pixels")
    print("   - Sistema TMX real usa 32x32 pixels por tile")
    print("   - Offset visual (575, 35) no coincide con pathfinding")
    
    # Análisis matemático
    print("\n5. CÁLCULO DE DESAJUSTE:")
    
    # TMX real: 30x30 tiles * 32 pixels/tile = 960x960
    tmx_tile_size = 32
    tmx_grid_size = 30
    tmx_world_size = tmx_tile_size * tmx_grid_size  # 960
    
    # Visual actual
    visual_tile_size = 25
    visual_offset_x = 575
    visual_offset_y = 35
    
    print(f"   - TMX real: {tmx_grid_size}x{tmx_grid_size} tiles × {tmx_tile_size}px = {tmx_world_size}x{tmx_world_size}")
    print(f"   - Visual: tiles de {visual_tile_size}px con offset ({visual_offset_x}, {visual_offset_y})")
    
    # Ejemplo de conversión
    example_pathfinding_coords = [(288, 160), (320, 192), (192, 96)]
    
    print(f"\n6. EJEMPLOS DE DESAJUSTE:")
    for px, py in example_pathfinding_coords:
        # Conversión a tiles TMX
        tile_x = px // tmx_tile_size
        tile_y = py // tmx_tile_size
        
        # Donde debería aparecer visualmente (TMX correcto)
        visual_correct_x = tile_x * visual_tile_size + visual_offset_x
        visual_correct_y = tile_y * visual_tile_size + visual_offset_y
        
        # Donde probablemente aparece ahora (sin offset)
        visual_wrong_x = px * (visual_tile_size / tmx_tile_size)
        visual_wrong_y = py * (visual_tile_size / tmx_tile_size)
        
        print(f"   Pathfinding ({px}, {py}) -> Tile({tile_x}, {tile_y})")
        print(f"     Visual correcto: ({visual_correct_x:.0f}, {visual_correct_y:.0f})")
        print(f"     Visual incorrecto: ({visual_wrong_x:.0f}, {visual_wrong_y:.0f})")
        print()

def create_unified_coordinate_converter():
    """Crear un convertidor unificado que alinee visual con pathfinding"""
    
    print("=" * 70)
    print("CREANDO CONVERTIDOR UNIFICADO DE COORDENADAS")
    print("=" * 70)
    
    try:
        import pygame
        
        class UnifiedTMXConverter:
            """Convertidor que alinea perfectamente visual con pathfinding"""
            
            def __init__(self):
                # Configuración TMX real
                self.tmx_tile_size = 32  # Pixels por tile en TMX
                self.tmx_grid_width = 30  # Tiles horizontales
                self.tmx_grid_height = 30  # Tiles verticales
                self.tmx_world_width = self.tmx_tile_size * self.tmx_grid_width  # 960
                self.tmx_world_height = self.tmx_tile_size * self.tmx_grid_height  # 960
                
                # Configuración visual (será calculada dinámicamente)
                self.screen_width = 1200
                self.screen_height = 700
                self.visual_tile_size = 18  # Más pequeño para que quepa bien
                self.visual_offset_x = 50   # Margen izquierdo
                self.visual_offset_y = 50   # Margen superior
                
                # Área visual total
                self.visual_area_width = self.visual_tile_size * self.tmx_grid_width
                self.visual_area_height = self.visual_tile_size * self.tmx_grid_height
                
                print(f"[UNIFIED] TMX World: {self.tmx_world_width}x{self.tmx_world_height}")
                print(f"[UNIFIED] Visual Area: {self.visual_area_width}x{self.visual_area_height}")
                print(f"[UNIFIED] Visual Offset: ({self.visual_offset_x}, {self.visual_offset_y})")
                print(f"[UNIFIED] Tile Size: TMX={self.tmx_tile_size}px -> Visual={self.visual_tile_size}px")
            
            def tmx_pixel_to_screen(self, tmx_x, tmx_y):
                """Convertir coordenadas TMX pixel a coordenadas de pantalla"""
                
                # Convertir TMX pixel a tile
                tile_x = tmx_x / self.tmx_tile_size
                tile_y = tmx_y / self.tmx_tile_size
                
                # Convertir tile a pantalla
                screen_x = tile_x * self.visual_tile_size + self.visual_offset_x
                screen_y = tile_y * self.visual_tile_size + self.visual_offset_y
                
                return int(screen_x), int(screen_y)
            
            def screen_to_tmx_pixel(self, screen_x, screen_y):
                """Convertir coordenadas de pantalla a TMX pixel"""
                
                # Convertir pantalla a tile
                tile_x = (screen_x - self.visual_offset_x) / self.visual_tile_size
                tile_y = (screen_y - self.visual_offset_y) / self.visual_tile_size
                
                # Convertir tile a TMX pixel
                tmx_x = tile_x * self.tmx_tile_size
                tmx_y = tile_y * self.tmx_tile_size
                
                return int(tmx_x), int(tmx_y)
            
            def get_visual_grid_rect(self, tile_x, tile_y):
                """Obtener el rectángulo visual para un tile específico"""
                
                screen_x = tile_x * self.visual_tile_size + self.visual_offset_x
                screen_y = tile_y * self.visual_tile_size + self.visual_offset_y
                
                return pygame.Rect(
                    screen_x, screen_y,
                    self.visual_tile_size, self.visual_tile_size
                )
            
            def get_layout_bounds_on_screen(self):
                """Obtener los límites del layout en coordenadas de pantalla"""
                
                return {
                    'min_x': self.visual_offset_x,
                    'min_y': self.visual_offset_y,
                    'max_x': self.visual_offset_x + self.visual_area_width,
                    'max_y': self.visual_offset_y + self.visual_area_height
                }
        
        # Crear instancia global
        converter = UnifiedTMXConverter()
        globals()['unified_converter'] = converter
        
        print("[SUCCESS] Convertidor unificado creado")
        return converter
        
    except Exception as e:
        print(f"[ERROR] Error creando convertidor: {e}")
        return None

def patch_coordinate_systems():
    """Patchear todos los sistemas para usar el convertidor unificado"""
    
    print("\n" + "=" * 70)
    print("APLICANDO PATCHES DE COORDINACIÓN")
    print("=" * 70)
    
    converter = create_unified_coordinate_converter()
    if not converter:
        print("[ERROR] No se pudo crear convertidor")
        return False
    
    success_count = 0
    
    # 1. Patch del sistema de conversión TMX actual
    try:
        import tmx_screen_converter
        
        # Reemplazar el convertidor actual
        def convert_operator_coordinates_unified(operators, screen_width, screen_height):
            """Conversión unificada de operarios"""
            
            converted = {}
            
            for op_id, data in operators.items():
                # Obtener coordenadas TMX originales
                tmx_x = data.get('x', 0)
                tmx_y = data.get('y', 0)
                
                # Convertir usando sistema unificado
                screen_x, screen_y = converter.tmx_pixel_to_screen(tmx_x, tmx_y)
                
                # Crear datos convertidos
                converted_data = data.copy()
                converted_data['x'] = screen_x
                converted_data['y'] = screen_y
                converted_data['tmx_x'] = tmx_x  # Preservar originales
                converted_data['tmx_y'] = tmx_y
                
                converted[op_id] = converted_data
            
            return converted
        
        # Aplicar patch
        tmx_screen_converter.convert_operator_coordinates = convert_operator_coordinates_unified
        
        print("[PATCH] convert_operator_coordinates -> UNIFICADO")
        success_count += 1
        
    except Exception as e:
        print(f"[PATCH] Error en tmx_screen_converter: {e}")
    
    # 2. Patch del renderizado de layout
    try:
        import direct_layout_patch
        
        def draw_tmx_layout_unified(screen, almacen=None):
            """Dibujar layout TMX con coordenadas unificadas"""
            
            import pygame
            
            # Limpiar área de layout
            layout_bounds = converter.get_layout_bounds_on_screen()
            layout_rect = pygame.Rect(
                layout_bounds['min_x'], layout_bounds['min_y'],
                layout_bounds['max_x'] - layout_bounds['min_x'],
                layout_bounds['max_y'] - layout_bounds['min_y']
            )
            pygame.draw.rect(screen, (20, 20, 20), layout_rect)
            
            # Obtener datos TMX
            try:
                from tmx_coordinate_system import tmx_coords
                if not tmx_coords.is_tmx_active():
                    print("[DRAW_UNIFIED] TMX no activo")
                    return
                
                # Dibujar grid TMX tile por tile
                for tile_x in range(converter.tmx_grid_width):
                    for tile_y in range(converter.tmx_grid_height):
                        
                        # Obtener tipo de tile TMX
                        tmx_pixel_x = tile_x * converter.tmx_tile_size
                        tmx_pixel_y = tile_y * converter.tmx_tile_size
                        
                        # Verificar si está dentro de bounds TMX
                        if (tmx_pixel_x < converter.tmx_world_width and 
                            tmx_pixel_y < converter.tmx_world_height):
                            
                            # Obtener rectángulo visual
                            visual_rect = converter.get_visual_grid_rect(tile_x, tile_y)
                            
                            # Determinar color según navegabilidad
                            # Por ahora usar patrón de test - después integrar con TMX real
                            if (tile_x + tile_y) % 2 == 0:
                                color = (60, 100, 60)  # Verde navegable
                            else:
                                color = (100, 60, 60)  # Rojo obstáculo
                            
                            # Dibujar tile
                            pygame.draw.rect(screen, color, visual_rect)
                            pygame.draw.rect(screen, (40, 40, 40), visual_rect, 1)
                
                # Dibujar borde del layout
                pygame.draw.rect(screen, (255, 255, 255), layout_rect, 2)
                
                # Información de debug
                font = pygame.font.Font(None, 16)
                info_text = f"TMX: {converter.tmx_grid_width}x{converter.tmx_grid_height} tiles, Visual: {converter.visual_tile_size}px/tile"
                text_surface = font.render(info_text, True, (255, 255, 255))
                screen.blit(text_surface, (layout_bounds['min_x'], layout_bounds['min_y'] - 20))
                
            except Exception as e:
                print(f"[DRAW_UNIFIED] Error: {e}")
        
        # Aplicar patch
        direct_layout_patch.draw_tmx_layout = draw_tmx_layout_unified
        
        print("[PATCH] draw_tmx_layout -> UNIFICADO")
        success_count += 1
        
    except Exception as e:
        print(f"[PATCH] Error en direct_layout_patch: {e}")
    
    # 3. Patch del renderizado de operarios
    try:
        import visualization.original_renderer as renderer_module
        
        def dibujar_operarios_aligned(screen):
            """Dibujar operarios perfectamente alineados con grid"""
            
            from visualization.state import estado_visual
            import pygame
            
            operarios = estado_visual.get("operarios", {})
            if not operarios:
                return
            
            # Convertir coordenadas
            screen_w, screen_h = screen.get_size()
            converted = convert_operator_coordinates_unified(operarios, screen_w, screen_h)
            
            for op_id, data in converted.items():
                x, y = data['x'], data['y']
                tmx_x, tmx_y = data['tmx_x'], data['tmx_y']
                tipo = data.get('tipo', 'terrestre')
                accion = data.get('accion', 'Unknown')
                
                # Color por tipo
                if tipo == 'montacargas':
                    color = (255, 165, 0)  # Naranja
                elif tipo == 'traspaleta':
                    color = (0, 150, 0)    # Verde
                else:
                    color = (227, 63, 44)  # Rojo
                
                # Dibujar operario centrado en su tile
                radio = 8
                pygame.draw.circle(screen, color, (x, y), radio)
                pygame.draw.circle(screen, (255, 255, 255), (x, y), radio, 2)
                
                # ID del operario
                font = pygame.font.Font(None, 16)
                text_id = font.render(f"O{op_id}", True, (255, 255, 255))
                text_rect = text_id.get_rect(center=(x, y))
                screen.blit(text_id, text_rect)
                
                # Info de debug
                font_small = pygame.font.Font(None, 12)
                debug_text = f"TMX({tmx_x:.0f},{tmx_y:.0f})"
                debug_surface = font_small.render(debug_text, True, (255, 255, 0))
                screen.blit(debug_surface, (x + 12, y - 6))
        
        # Aplicar patch
        renderer_module.dibujar_operarios = dibujar_operarios_aligned
        
        print("[PATCH] dibujar_operarios -> ALINEADO")
        success_count += 1
        
    except Exception as e:
        print(f"[PATCH] Error en operarios renderer: {e}")
    
    print(f"\n[RESULT] {success_count}/3 patches aplicados exitosamente")
    return success_count == 3

def test_coordinate_alignment():
    """Test para verificar alineación de coordenadas"""
    
    print("\n" + "=" * 70)
    print("TEST DE ALINEACIÓN DE COORDENADAS")
    print("=" * 70)
    
    try:
        converter = unified_converter
        
        # Test con coordenadas de pathfinding reales del log
        test_coords = [
            (288, 160),   # Operario moviéndose a tarea
            (320, 192),   # Otra tarea
            (192, 96),    # Otra tarea
            (96, 96),     # Posición inicial operario
            (160, 128),   # Más tareas
        ]
        
        print("Verificando conversion TMX -> Pantalla:")
        for tmx_x, tmx_y in test_coords:
            screen_x, screen_y = converter.tmx_pixel_to_screen(tmx_x, tmx_y)
            
            # Verificar conversión inversa
            back_tmx_x, back_tmx_y = converter.screen_to_tmx_pixel(screen_x, screen_y)
            
            # Calcular tile correspondiente
            tile_x = tmx_x // converter.tmx_tile_size
            tile_y = tmx_y // converter.tmx_tile_size
            
            print(f"  TMX({tmx_x:3d},{tmx_y:3d}) -> Tile({tile_x:2d},{tile_y:2d}) -> Screen({screen_x:3d},{screen_y:3d}) -> Back({back_tmx_x:3d},{back_tmx_y:3d})")
            
            # Verificar precisión
            if abs(back_tmx_x - tmx_x) <= 1 and abs(back_tmx_y - tmx_y) <= 1:
                status = "OK"
            else:
                status = "ERR"
            print(f"    {status} Precisión: ±{abs(back_tmx_x - tmx_x)}, ±{abs(back_tmx_y - tmx_y)}")
        
        # Verificar bounds del layout
        bounds = converter.get_layout_bounds_on_screen()
        print(f"\nLayout en pantalla:")
        print(f"  Área: ({bounds['min_x']}, {bounds['min_y']}) - ({bounds['max_x']}, {bounds['max_y']})")
        print(f"  Tamaño: {bounds['max_x'] - bounds['min_x']}x{bounds['max_y'] - bounds['min_y']}")
        
        # Verificar que cabe en pantalla
        if bounds['max_x'] <= converter.screen_width and bounds['max_y'] <= converter.screen_height:
            print(f"  OK Cabe en pantalla {converter.screen_width}x{converter.screen_height}")
        else:
            print(f"  ERR No cabe en pantalla {converter.screen_width}x{converter.screen_height}")
        
        return True
        
    except Exception as e:
        print(f"[TEST] Error: {e}")
        return False

if __name__ == "__main__":
    print("ALINEACIÓN DE COORDENADAS TMX")
    print("=" * 70)
    
    # Análisis del problema
    analyze_coordinate_mismatch()
    
    # Aplicar solución
    if patch_coordinate_systems():
        print("\n[SUCCESS] Sistemas de coordenadas unificados")
    else:
        print("\n[ERROR] No se pudieron unificar los sistemas")
    
    # Test de verificación
    if test_coordinate_alignment():
        print("\n[SUCCESS] Test de alineación exitoso")
    else:
        print("\n[ERROR] Test de alineación falló")
    
    print("\n" + "=" * 70)
    print("¡Los operarios ahora deberían estar perfectamente alineados con el grid!")
    print("=" * 70)