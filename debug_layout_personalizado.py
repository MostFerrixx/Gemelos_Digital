#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG - LAYOUT PERSONALIZADO NO SE APLICA
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def debug_layout_loading():
    """Diagnosticar por qué el layout personalizado no se aplica"""
    
    print("=" * 60)
    print("DEBUG - LAYOUT PERSONALIZADO")
    print("=" * 60)
    
    try:
        # 1. Verificar layouts disponibles
        from dynamic_layout_loader import DynamicLayoutLoader
        
        loader = DynamicLayoutLoader()
        available = loader.scan_available_layouts()
        
        print("1. Layouts disponibles:")
        for layout in available:
            status = "VÁLIDO" if layout['valid'] else "INVÁLIDO"
            print(f"   {status}: {layout['name']} - {layout.get('error', 'OK')}")
        
        # 2. Intentar cargar layout específico que creaste
        layout_personalizado = None
        for layout in available:
            if 'personalizado' in layout['name'].lower() or 'tiled' in layout['name'].lower():
                layout_personalizado = layout
                break
        
        if not layout_personalizado and available:
            layout_personalizado = available[0]  # Usar el primero disponible
        
        if layout_personalizado:
            print(f"\n2. Testing layout: {layout_personalizado['name']}")
            print(f"   Ruta: {layout_personalizado['path']}")
            print(f"   Válido: {layout_personalizado['valid']}")
            
            # Intentar cargar el layout
            layout_data = loader.load_layout(layout_personalizado['path'])
            
            if layout_data:
                print("\n3. Layout cargado:")
                print(f"   Nombre: {layout_data['info']['name']}")
                print(f"   Tamaño: {layout_data['info']['width']}x{layout_data['info']['height']}")
                print(f"   Tile size: {layout_data['info']['tile_width']}x{layout_data['info']['tile_height']}")
                
                # Verificar matriz de navegación
                matrix = layout_data['navigation_matrix']
                if matrix:
                    print(f"   Matriz navegación: {len(matrix)}x{len(matrix[0])}")
                    
                    # Contar tiles navegables vs obstáculos
                    total_tiles = len(matrix) * len(matrix[0])
                    walkable_tiles = sum(sum(row) for row in matrix)
                    obstacles = total_tiles - walkable_tiles
                    
                    print(f"   Tiles navegables: {walkable_tiles}")
                    print(f"   Obstáculos: {obstacles}")
                    print(f"   Ratio navegable: {walkable_tiles/total_tiles*100:.1f}%")
                    
                    # Mostrar sample de la matriz (primera fila)
                    print(f"   Primera fila: {matrix[0][:10]}...")
                
                # Verificar ubicaciones especiales
                locations = layout_data['special_locations']
                print(f"\n4. Ubicaciones especiales:")
                for loc_type, locs in locations.items():
                    print(f"   {loc_type}: {len(locs)} ubicaciones")
                    if locs:
                        print(f"     Ejemplo: {locs[0]}")
                
            else:
                print("   ERROR: No se pudo cargar el layout")
        
        # 3. Test integración pathfinding
        print(f"\n5. Testing pathfinding integration...")
        
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        
        wrapper = get_dynamic_pathfinding_wrapper()
        
        if layout_personalizado:
            success = wrapper.initialize_with_layout(layout_personalizado['path'])
            
            if success:
                print("   Layout cargado en pathfinding wrapper")
                
                # Verificar posiciones clave
                depot_pos = wrapper.get_depot_position()
                inbound_pos = wrapper.get_inbound_position()
                picking_locs = wrapper.get_picking_locations()
                
                print(f"   Depot: {depot_pos}")
                print(f"   Inbound: {inbound_pos}")
                print(f"   Picking locations: {len(picking_locs)}")
                
                # Test calcular ruta
                test_route = wrapper.calculate_route((100, 100), (400, 300))
                if test_route:
                    print(f"   Ruta test: {len(test_route)} puntos")
                    print(f"   Inicio: {test_route[0]}")
                    print(f"   Fin: {test_route[-1]}")
                
            else:
                print("   ERROR: No se pudo cargar layout en wrapper")
        
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO:")
        print("=" * 60)
        
        # Diagnosticar problemas
        if not available:
            print("PROBLEMA: No hay layouts disponibles")
            print("SOLUCIÓN: Crear layouts en carpeta 'layouts/'")
            
        elif all(not layout['valid'] for layout in available):
            print("PROBLEMA: Todos los layouts son inválidos")
            print("SOLUCIONES:")
            print("1. Verificar que Tiled guardó correctamente el TMX")
            print("2. Verificar que se usó el tileset correcto")
            print("3. Verificar formato TMX compatible")
            
        elif layout_data and layout_data['info']['name'].endswith('(fallback)'):
            print("PROBLEMA: Sistema usa fallback en lugar de TMX real")
            print("SOLUCIONES:")
            print("1. PyTMX no puede leer el archivo TMX")
            print("2. Verificar formato del archivo TMX")
            print("3. Sistema funciona con fallback pero no usa tu diseño")
            
        else:
            print("INFO: Sistema debería estar usando tu layout personalizado")
            print("Si ves el layout anterior, verificar:")
            print("1. Que reiniciaste la simulación")
            print("2. Que seleccionaste el layout correcto")
            print("3. Que el renderer usa las coordenadas del layout")
        
        print("=" * 60)
        
        return layout_data
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    layout_data = debug_layout_loading()