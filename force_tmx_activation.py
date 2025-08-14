#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FORZAR ACTIVACIÓN TMX - Asegurar que WH1 se activa siempre
"""

def force_tmx_activation():
    """Forzar activación del sistema TMX con WH1"""
    
    print("[FORCE_TMX] Forzando activación del sistema TMX...")
    
    try:
        from dynamic_layout_loader import DynamicLayoutLoader
        from tmx_coordinate_system import initialize_tmx_system, tmx_coords
        
        # Cargar WH1 directamente
        loader = DynamicLayoutLoader("layouts")
        layout_data = loader.load_layout("layouts/WH1.tmx")
        
        if layout_data:
            # Activar TMX
            success = initialize_tmx_system(layout_data)
            
            if success and tmx_coords.is_tmx_active():
                bounds = tmx_coords.get_bounds()
                nav_matrix = tmx_coords.get_navigation_matrix()
                
                if nav_matrix:
                    total_cells = len(nav_matrix) * len(nav_matrix[0])
                    walkable_cells = sum(sum(row) for row in nav_matrix)
                    navegabilidad = (walkable_cells / total_cells) * 100
                    
                    print(f"[FORCE_TMX] SUCCESS: TMX activado")
                    print(f"[FORCE_TMX] Layout: {tmx_coords.current_layout_data['info']['name']}")
                    print(f"[FORCE_TMX] Bounds: {bounds['max_x']}x{bounds['max_y']}")
                    print(f"[FORCE_TMX] Navegabilidad: {navegabilidad:.1f}%")
                    
                    return True
                else:
                    print("[FORCE_TMX] ERROR: Sin matriz de navegación")
            else:
                print("[FORCE_TMX] ERROR: No se pudo activar TMX")
        else:
            print("[FORCE_TMX] ERROR: No se pudo cargar WH1")
        
        return False
        
    except Exception as e:
        print(f"[FORCE_TMX] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def patch_direct_layout_to_use_tmx():
    """Parchear direct_layout_patch para usar el sistema TMX unificado"""
    
    print("[FORCE_TMX] Parcheando sistema visual...")
    
    try:
        import direct_layout_patch
        
        # Reemplazar get_tmx_layout_data
        def get_tmx_layout_data_from_unified():
            """Obtener datos TMX desde el sistema unificado"""
            from tmx_coordinate_system import tmx_coords
            
            if tmx_coords.is_tmx_active():
                return tmx_coords.current_layout_data
            else:
                print("[PATCH_TMX] Sistema TMX unificado no activo")
                return None
        
        # Aplicar parche
        direct_layout_patch.get_tmx_layout_data = get_tmx_layout_data_from_unified
        
        print("[FORCE_TMX] Sistema visual parcheado para usar TMX unificado")
        return True
        
    except Exception as e:
        print(f"[FORCE_TMX] Error parcheando sistema visual: {e}")
        return False

def debug_activation_status():
    """Debug del estado de activación"""
    
    print("\n[DEBUG] Estado sistemas después de forzar activación:")
    
    # TMX Unificado
    from tmx_coordinate_system import tmx_coords
    print(f"[DEBUG] TMX Unificado activo: {tmx_coords.is_tmx_active()}")
    
    if tmx_coords.is_tmx_active():
        bounds = tmx_coords.get_bounds()
        print(f"[DEBUG] TMX Bounds: {bounds['max_x']}x{bounds['max_y']}")
        
        nav_matrix = tmx_coords.get_navigation_matrix()
        if nav_matrix:
            total_cells = len(nav_matrix) * len(nav_matrix[0])
            walkable_cells = sum(sum(row) for row in nav_matrix)
            navegabilidad = (walkable_cells / total_cells) * 100
            print(f"[DEBUG] TMX Navegabilidad: {navegabilidad:.1f}%")
    
    # Sistema Visual
    try:
        from direct_layout_patch import get_tmx_layout_data
        visual_data = get_tmx_layout_data()
        
        if visual_data:
            nav_matrix_visual = visual_data.get('navigation_matrix', [])
            if nav_matrix_visual:
                total_cells_visual = len(nav_matrix_visual) * len(nav_matrix_visual[0])
                walkable_cells_visual = sum(sum(row) for row in nav_matrix_visual)
                navegabilidad_visual = (walkable_cells_visual / total_cells_visual) * 100
                print(f"[DEBUG] Visual Layout: {visual_data['info']['name']}")
                print(f"[DEBUG] Visual Navegabilidad: {navegabilidad_visual:.1f}%")
            else:
                print("[DEBUG] Visual: Sin matriz de navegación")
        else:
            print("[DEBUG] Visual: Sin datos")
    except Exception as e:
        print(f"[DEBUG] Error obteniendo datos visuales: {e}")

# Auto-activar al importar este módulo
if __name__ == "__main__":
    # Activar TMX
    tmx_success = force_tmx_activation()
    
    # Parchear sistema visual
    visual_success = patch_direct_layout_to_use_tmx()
    
    # Debug estado
    debug_activation_status()
    
    if tmx_success and visual_success:
        print("\n[FORCE_TMX] ÉXITO: Sistemas TMX lógico y visual sincronizados")
    else:
        print("\n[FORCE_TMX] ERROR: No se pudieron sincronizar los sistemas")
else:
    # Auto-activar al importar
    print("[FORCE_TMX] Auto-activando TMX...")
    force_tmx_activation()
    patch_direct_layout_to_use_tmx()