#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST DE TMX ARREGLADO - Probar si las reparaciones funcionan
"""

import os
import sys

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_pygame_display_fix():
    """Probar si pygame.display arregla el problema TMX"""
    
    print("="*60)
    print("TEST DE REPARACIONES TMX")
    print("="*60)
    
    # 1. Inicializar pygame.display ANTES de cargar TMX
    print("\n1. INICIALIZANDO PYGAME.DISPLAY...")
    import pygame
    
    if not pygame.get_init():
        pygame.init()
        print("   pygame.init() ejecutado")
    
    if not pygame.display.get_init():
        # Crear display oculto solo para TMX
        pygame.display.set_mode((1, 1), pygame.HIDDEN)
        print("   pygame.display inicializado (oculto)")
    
    # 2. Probar carga directa de WH1.tmx
    print("\n2. PROBANDO CARGA DIRECTA DE WH1.TMX...")
    
    try:
        import pytmx
        import pytmx.util_pygame
        
        wh1_path = "layouts/WH1.tmx"
        if os.path.exists(wh1_path):
            print(f"   Cargando: {wh1_path}")
            
            # Esta línea debería funcionar ahora
            tmx_data = pytmx.util_pygame.load_pygame(wh1_path)
            
            print(f"   EXITO: TMX cargado directamente!")
            print(f"   Dimensiones: {tmx_data.width}x{tmx_data.height}")
            print(f"   Tile size: {tmx_data.tilewidth}x{tmx_data.tileheight}")
            print(f"   Capas: {len(list(tmx_data.layers))}")
            
            # 3. Probar extracción de datos
            print("\n3. EXTRAYENDO DATOS DEL TMX...")
            
            # Buscar capa principal
            main_layer = None
            for layer in tmx_data.visible_layers:
                if hasattr(layer, 'data'):
                    main_layer = layer
                    break
            
            if main_layer:
                print(f"   Capa principal encontrada: {getattr(main_layer, 'name', 'Sin nombre')}")
                
                # Contar tiles navegables usando API corregida
                walkable_count = 0
                total_count = 0
                
                for y in range(tmx_data.height):
                    for x in range(tmx_data.width):
                        if y < len(main_layer.data) and x < len(main_layer.data[y]):
                            tile_gid = main_layer.data[y][x]
                            total_count += 1
                            
                            if tile_gid == 0:
                                walkable_count += 1  # Tile vacío
                            else:
                                # Usar API corregida
                                try:
                                    tile_properties = tmx_data.get_tile_properties_by_gid(tile_gid)
                                    if tile_properties:
                                        walkable_prop = tile_properties.get('walkable', 'true')
                                        if walkable_prop.lower() == 'true':
                                            walkable_count += 1
                                    else:
                                        walkable_count += 1  # Default navegable
                                except:
                                    walkable_count += 1  # Fallback navegable
                
                walkable_pct = (walkable_count / total_count) * 100 if total_count > 0 else 0
                print(f"   Tiles navegables: {walkable_count}/{total_count} ({walkable_pct:.1f}%)")
                
                if walkable_pct < 95:
                    print("   ✅ EXITO: Layout real detectado (no es 100% navegable)")
                else:
                    print("   ⚠️  WARNING: Parece layout genérico (muy alta navegabilidad)")
                    
            else:
                print("   ❌ ERROR: No se encontró capa principal")
                
            return True
            
        else:
            print(f"   ❌ ERROR: {wh1_path} no existe")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_enhanced_config_window():
    """Probar si enhanced_config_window funciona con las reparaciones"""
    
    print("\n4. PROBANDO ENHANCED CONFIG WINDOW...")
    
    try:
        from enhanced_config_window import EnhancedConfigWindow
        
        # Crear instancia (esto debería inicializar pygame.display internamente)
        config_window = EnhancedConfigWindow()
        
        # Acceder al layout loader
        if hasattr(config_window, 'layout_loader'):
            loader = config_window.layout_loader
            
            # Intentar escanear layouts (esto debería funcionar ahora)
            layouts = loader.scan_available_layouts()
            
            print(f"   Layouts escaneados: {len(layouts)}")
            
            # Buscar WH1 específicamente
            wh1_layout = None
            for layout in layouts:
                if layout['name'] == 'WH1':
                    wh1_layout = layout
                    break
            
            if wh1_layout:
                print(f"   WH1 encontrado: {wh1_layout['valid']}")
                
                if wh1_layout['valid']:
                    print("   ✅ EXITO: WH1 marcado como válido")
                    
                    # Intentar cargar WH1 directamente
                    wh1_data = loader.load_layout(wh1_layout['path'])
                    if wh1_data:
                        matrix = wh1_data.get('navigation_matrix', [])
                        if matrix:
                            total = len(matrix) * len(matrix[0])
                            walkable = sum(sum(row) for row in matrix)
                            pct = (walkable / total) * 100
                            print(f"   WH1 navegabilidad: {walkable}/{total} ({pct:.1f}%)")
                            
                            if pct < 95:
                                print("   ✅ EXITO TOTAL: WH1 cargado correctamente")
                                return True
                            else:
                                print("   ❌ ERROR: Sigue usando fallback")
                        else:
                            print("   ❌ ERROR: No hay matriz de navegación")
                    else:
                        print("   ❌ ERROR: No se pudo cargar WH1")
                else:
                    print(f"   ❌ ERROR: WH1 inválido - {wh1_layout.get('error', 'Sin error específico')}")
            else:
                print("   ❌ ERROR: WH1 no encontrado en layouts")
                
        else:
            print("   ❌ ERROR: Config window no tiene layout_loader")
            
        return False
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    """Test completo de reparaciones"""
    
    # Test 1: Carga directa TMX con pygame.display
    success1 = test_pygame_display_fix()
    
    # Test 2: Enhanced config window
    success2 = test_enhanced_config_window()
    
    print(f"\n{'='*60}")
    print("RESULTADOS DEL TEST:")
    print(f"{'='*60}")
    print(f"Carga directa TMX: {'✅ EXITO' if success1 else '❌ FALLÓ'}")
    print(f"Enhanced config: {'✅ EXITO' if success2 else '❌ FALLÓ'}")
    
    if success1 and success2:
        print("\n🎉 REPARACIONES EXITOSAS - TMX debería funcionar en simulador")
    elif success1:
        print("\n⚠️  PARCIAL - TMX funciona directamente pero hay problema en config")
    else:
        print("\n❌ REPARACIONES FALLARON - Revisar problemas")
        
    print(f"{'='*60}")

if __name__ == "__main__":
    main()