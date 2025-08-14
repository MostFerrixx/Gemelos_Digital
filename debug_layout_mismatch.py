#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG: Diagnosticar discrepancia entre layout lógico y visual
"""

def debug_layout_systems():
    """Diagnosticar qué layout está usando cada sistema"""
    
    print("="*70)
    print("DEBUG: DISCREPANCIA LAYOUT LÓGICO vs VISUAL")
    print("="*70)
    
    try:
        # 1. Sistema TMX Unificado (para lógica de operarios)
        print("\n1. SISTEMA TMX UNIFICADO (LÓGICA OPERARIOS):")
        from tmx_coordinate_system import tmx_coords
        
        if tmx_coords.is_tmx_active():
            bounds = tmx_coords.get_bounds()
            nav_matrix = tmx_coords.get_navigation_matrix()
            
            if nav_matrix:
                total_cells = len(nav_matrix) * len(nav_matrix[0])
                walkable_cells = sum(sum(row) for row in nav_matrix)
                navegabilidad = (walkable_cells / total_cells) * 100
                
                print(f"[TMX_UNIFICADO] ACTIVO")
                print(f"[TMX_UNIFICADO] Layout: {tmx_coords.current_layout_data['info']['name']}")
                print(f"[TMX_UNIFICADO] Bounds: {bounds['max_x']}x{bounds['max_y']}")
                print(f"[TMX_UNIFICADO] Grid: {bounds['grid_width']}x{bounds['grid_height']}")
                print(f"[TMX_UNIFICADO] Navegabilidad: {navegabilidad:.1f}%")
            else:
                print("[TMX_UNIFICADO] ERROR: Sin matriz de navegación")
        else:
            print("[TMX_UNIFICADO] NO ACTIVO")
            
        # 2. Sistema Visual (direct_layout_patch)
        print("\n2. SISTEMA VISUAL (direct_layout_patch):")
        from direct_layout_patch import get_tmx_layout_data
        
        visual_data = get_tmx_layout_data()
        
        if visual_data:
            nav_matrix_visual = visual_data.get('navigation_matrix', [])
            info_visual = visual_data.get('info', {})
            
            if nav_matrix_visual:
                total_cells_visual = len(nav_matrix_visual) * len(nav_matrix_visual[0])
                walkable_cells_visual = sum(sum(row) for row in nav_matrix_visual)
                navegabilidad_visual = (walkable_cells_visual / total_cells_visual) * 100
                
                print(f"[VISUAL] Layout: {info_visual.get('name', 'Unknown')}")
                print(f"[VISUAL] Dimensiones: {info_visual.get('width', '?')}x{info_visual.get('height', '?')}")
                print(f"[VISUAL] Navegabilidad: {navegabilidad_visual:.1f}%")
            else:
                print("[VISUAL] ERROR: Sin matriz de navegación")
        else:
            print("[VISUAL] ERROR: No se pudo obtener datos")
            
        # 3. Dynamic Layout Loader original
        print("\n3. DYNAMIC LAYOUT LOADER ORIGINAL:")
        from dynamic_layout_loader import DynamicLayoutLoader
        
        loader = DynamicLayoutLoader("layouts")
        loader_data = loader.load_layout("layouts/WH1.tmx")
        
        if loader_data:
            nav_matrix_loader = loader_data.get('navigation_matrix', [])
            info_loader = loader_data.get('info', {})
            
            if nav_matrix_loader:
                total_cells_loader = len(nav_matrix_loader) * len(nav_matrix_loader[0])
                walkable_cells_loader = sum(sum(row) for row in nav_matrix_loader)
                navegabilidad_loader = (walkable_cells_loader / total_cells_loader) * 100
                
                print(f"[LOADER] Layout: {info_loader.get('name', 'Unknown')}")
                print(f"[LOADER] Dimensiones: {info_loader.get('width', '?')}x{info_loader.get('height', '?')}")
                print(f"[LOADER] Navegabilidad: {navegabilidad_loader:.1f}%")
            else:
                print("[LOADER] ERROR: Sin matriz de navegación")
        else:
            print("[LOADER] ERROR: No se pudo cargar")
            
        # 4. Dynamic Pathfinding Integration
        print("\n4. DYNAMIC PATHFINDING INTEGRATION:")
        try:
            from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
            
            wrapper = get_dynamic_pathfinding_wrapper()
            if wrapper and hasattr(wrapper, 'integration'):
                integration = wrapper.integration
                if hasattr(integration, 'current_layout_data') and integration.current_layout_data:
                    integration_data = integration.current_layout_data
                    nav_matrix_int = integration_data.get('navigation_matrix', [])
                    info_int = integration_data.get('info', {})
                    
                    if nav_matrix_int:
                        total_cells_int = len(nav_matrix_int) * len(nav_matrix_int[0])
                        walkable_cells_int = sum(sum(row) for row in nav_matrix_int)
                        navegabilidad_int = (walkable_cells_int / total_cells_int) * 100
                        
                        print(f"[INTEGRATION] Layout: {info_int.get('name', 'Unknown')}")
                        print(f"[INTEGRATION] Dimensiones: {info_int.get('width', '?')}x{info_int.get('height', '?')}")
                        print(f"[INTEGRATION] Navegabilidad: {navegabilidad_int:.1f}%")
                    else:
                        print("[INTEGRATION] Sin matriz de navegación")
                else:
                    print("[INTEGRATION] Sin datos de layout")
            else:
                print("[INTEGRATION] Wrapper no disponible")
        except Exception as e:
            print(f"[INTEGRATION] Error: {e}")
        
        # 5. ANÁLISIS COMPARATIVO
        print("\n" + "="*70)
        print("ANÁLISIS COMPARATIVO:")
        print("="*70)
        
        print("\nSI TODOS LOS SISTEMAS MUESTRAN:")
        print("- Navegabilidad ~60%: CORRECTO (WH1 real)")
        print("- Navegabilidad 100%: PROBLEMA (fallback genérico)")
        print("- Dimensiones 30x30: CORRECTO")
        print("- Dimensiones 50x30: PROBLEMA (fallback)")
        
        print("\nSI HAY DISCREPANCIAS:")
        print("- TMX_UNIFICADO vs VISUAL diferentes → Causa los saltos")
        print("- LOADER vs INTEGRATION diferentes → Causa inconsistencia")
        
        return True
        
    except Exception as e:
        print(f"Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_layout_systems()