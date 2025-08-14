#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALIZAR DISCREPANCIA VISUAL: Por qué el usuario ve saltos cuando las coordenadas son correctas
"""

def analyze_coordinate_systems():
    """Analizar la discrepancia entre coordenadas lógicas y visuales"""
    
    print("="*80)
    print("ANÁLISIS: COORDENADAS LÓGICAS vs VISUALES")
    print("="*80)
    
    # 1. Coordenadas que ve el sistema lógico (TMX)
    print("\n1. SISTEMA LÓGICO TMX:")
    from tmx_coordinate_system import tmx_coords
    
    if tmx_coords.is_tmx_active():
        bounds = tmx_coords.get_bounds()
        print(f"   Bounds TMX: 0-{bounds['max_x']} x 0-{bounds['max_y']} (960x960 píxeles)")
        print(f"   Grid: {bounds['grid_width']}x{bounds['grid_height']} (30x30 tiles)")
        print(f"   Tile size: {bounds['tile_width']}x{bounds['tile_height']} (32x32 píxeles)")
        
        # Ejemplos de coordenadas que usa el sistema
        test_coords = [(320, 128), (837, 297), (612, 172), (959, 450)]
        print(f"   Coordenadas típicas del sistema: {test_coords}")
        
        # Estas son todas válidas para TMX
        for coord in test_coords:
            clamped = tmx_coords.clamp_point(coord[0], coord[1])
            print(f"   {coord} -> {clamped} {'OK Valida' if coord == clamped else 'X Clampada'}")
    
    # 2. Coordenadas del sistema visual
    print("\n2. SISTEMA VISUAL (direct_layout_patch):")
    try:
        from direct_layout_patch import get_tmx_layout_data
        visual_data = get_tmx_layout_data()
        
        if visual_data:
            info = visual_data.get('info', {})
            nav_matrix = visual_data.get('navigation_matrix', [])
            
            print(f"   Layout visual: {info.get('name', 'Unknown')}")
            print(f"   Dimensiones matriz: {len(nav_matrix[0]) if nav_matrix else 0}x{len(nav_matrix) if nav_matrix else 0}")
            
            # El sistema visual usa la misma matriz TMX, PERO...
            # La renderización puede usar diferentes escalas y offsets
            
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Sistema de renderizado
    print("\n3. SISTEMA DE RENDERIZADO:")
    
    # Simular lo que hace direct_layout_patch.py en draw_tmx_layout()
    # (usando dimensiones típicas de pantalla)
    screen_width, screen_height = 1920, 1080  # Típica
    available_width = screen_width - 100
    available_height = screen_height - 150
    
    width, height = 30, 30  # TMX grid
    tile_size_x = available_width // width
    tile_size_y = available_height // height
    tile_size = min(tile_size_x, tile_size_y, 25)  # Máximo 25px
    
    total_layout_width = width * tile_size
    total_layout_height = height * tile_size
    offset_x = (screen_width - total_layout_width) // 2
    offset_y = (screen_height - total_layout_height - 120) // 2 + 20
    
    print(f"   Pantalla: {screen_width}x{screen_height}")
    print(f"   Tile size calculado: {tile_size}px")
    print(f"   Layout visual total: {total_layout_width}x{total_layout_height}")
    print(f"   Offset visual: ({offset_x}, {offset_y})")
    print(f"   Área visual del layout: ({offset_x}, {offset_y}) a ({offset_x + total_layout_width}, {offset_y + total_layout_height})")
    
    # 4. EL PROBLEMA: Conversión coordenadas lógicas -> visuales
    print("\n4. CONVERSIÓN LÓGICA -> VISUAL:")
    print("   ¡AQUÍ ESTÁ EL PROBLEMA!")
    
    # Las coordenadas TMX (320, 128) deben convertirse a posición en pantalla
    # PERO el sistema de operarios usa coordenadas TMX directamente para dibujar
    
    ejemplo_tmx_x, ejemplo_tmx_y = 320, 128
    
    # En TMX: coordenadas van de 0-959 (960 píxeles)
    # En visual: debe mapearse al área de renderizado
    
    # Conversión correcta sería:
    visual_x = offset_x + (ejemplo_tmx_x * total_layout_width / 960)
    visual_y = offset_y + (ejemplo_tmx_y * total_layout_height / 960)
    
    print(f"   Coord TMX: ({ejemplo_tmx_x}, {ejemplo_tmx_y})")
    print(f"   Coord Visual correcta: ({visual_x:.1f}, {visual_y:.1f})")
    print(f"   Pero operarios usan coordenadas TMX DIRECTAMENTE para dibujar")
    
    # 5. Por qué se ven saltos
    print("\n5. POR QUÉ SE VEN SALTOS:")
    print("   X Operarios usan coordenadas TMX (0-959) para posicion visual")
    print("   X Layout se dibuja en area escalada y centrada")
    print("   X NO hay conversion TMX -> coordenadas de pantalla")
    print("   X Operario en (837, 297) aparece en pixel 837 de pantalla")
    print("   X Pero layout visible solo va hasta ~750 pixels")
    print("   => OPERARIO SE VE FUERA DEL LAYOUT VISUAL")
    
    # 6. Solución
    print("\n6. SOLUCIÓN NECESARIA:")
    print("   OK Implementar conversion TMX -> coordenadas de pantalla")
    print("   OK En visualization/original_renderer.py")
    print("   OK Funcion: convertir_coordenadas_tmx_a_pantalla()")
    print("   OK Usar en dibujar_operarios() antes de renderizar")
    
    return {
        'tmx_bounds': bounds if tmx_coords.is_tmx_active() else None,
        'visual_area': (offset_x, offset_y, offset_x + total_layout_width, offset_y + total_layout_height),
        'tile_size': tile_size,
        'screen_size': (screen_width, screen_height)
    }

if __name__ == "__main__":
    try:
        # Activar TMX primero
        from force_tmx_activation import force_tmx_activation
        force_tmx_activation()
        
        # Hacer análisis
        result = analyze_coordinate_systems()
        
        print("\n" + "="*80)
        print("CONCLUSIÓN:")
        print("="*80)
        print("Las coordenadas LÓGICAS están correctas (operarios dentro de 0-959)")
        print("El problema es VISUAL: no se convierten coordenadas TMX a pantalla")
        print("Usuario ve saltos porque operarios se dibujan en píxeles TMX brutos")
        print("="*80)
        
    except Exception as e:
        print(f"Error en análisis: {e}")
        import traceback
        traceback.print_exc()