#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG: Verificar qué coordenadas de picking tiene el TMX
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def debug_tmx_picking():
    """Debug de coordenadas de picking TMX vs hardcoded"""
    
    print("=" * 60)
    print("DEBUG TMX PICKING COORDINATES")
    print("=" * 60)
    
    # Importar sistemas
    from dynamic_layout_loader import DynamicLayoutLoader
    from utils.ubicaciones_picking import ubicaciones_picking
    from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
    
    # 1. Verificar ubicaciones hardcoded actuales
    ubicaciones_hardcoded = ubicaciones_picking.obtener_todas_ubicaciones()
    print(f"\n1. UBICACIONES HARDCODED:")
    print(f"   Total: {len(ubicaciones_hardcoded)}")
    if ubicaciones_hardcoded:
        print(f"   Primera: {ubicaciones_hardcoded[0]}")
        print(f"   Última: {ubicaciones_hardcoded[-1]}")
    
    # 2. Cargar TMX WH1 y verificar picking points
    print(f"\n2. VERIFICANDO TMX WH1:")
    tmx_path = "layouts/WH1.tmx"
    
    if os.path.exists(tmx_path):
        loader = DynamicLayoutLoader("layouts")
        layout_data = loader.load_layout(tmx_path)
        
        if layout_data and 'special_locations' in layout_data:
            picking_points = layout_data['special_locations'].get('picking_points', [])
            print(f"   Picking points en TMX: {len(picking_points)}")
            
            if picking_points:
                print(f"   Primeros 5 picking points TMX:")
                for i, point in enumerate(picking_points[:5]):
                    print(f"     {i+1}. {point}")
            else:
                print("   ¡ERROR! No hay picking points definidos en TMX")
                print("   El TMX debe tener objetos tipo 'picking' en capas de objetos")
    else:
        print(f"   ERROR: {tmx_path} no existe")
    
    # 3. Verificar integration actual
    print(f"\n3. VERIFICANDO INTEGRATION:")
    try:
        wrapper = get_dynamic_pathfinding_wrapper()
        if wrapper and hasattr(wrapper, 'integration'):
            integration = wrapper.integration
            if hasattr(integration, 'current_layout_data') and integration.current_layout_data:
                data = integration.current_layout_data
                special_locs = data.get('special_locations', {})
                picking_points = special_locs.get('picking_points', [])
                print(f"   Integration tiene {len(picking_points)} picking points cargados")
                
                if picking_points:
                    print(f"   Primer picking point: {picking_points[0]}")
            else:
                print("   Integration no tiene layout cargado")
        else:
            print("   Integration no disponible")
    except Exception as e:
        print(f"   Error verificando integration: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    debug_tmx_picking()