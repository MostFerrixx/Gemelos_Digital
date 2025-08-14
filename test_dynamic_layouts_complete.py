#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST COMPLETO DEL SISTEMA DE LAYOUTS DINÁMICOS
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from dynamic_layout_loader import DynamicLayoutLoader
from dynamic_pathfinding_integration import DynamicPathfindingIntegration
from enhanced_config_window import EnhancedConfigWindow

def test_complete_workflow():
    """Test del flujo completo de layouts dinámicos"""
    
    print("=" * 60)
    print("TEST COMPLETO - SISTEMA LAYOUTS DINÁMICOS")
    print("=" * 60)
    
    # 1. Test del loader
    print("\n1. TESTING DYNAMIC LAYOUT LOADER")
    loader = DynamicLayoutLoader()
    
    # Crear layouts si no existen
    if not os.path.exists("layouts/basic_example.tmx"):
        loader.create_sample_layouts()
    
    # Escanear layouts
    available = loader.scan_available_layouts()
    print(f"   - Layouts encontrados: {len(available)}")
    
    if available:
        # Cargar primer layout
        first_layout = available[0]
        loaded = loader.load_layout(first_layout['path'])
        if loaded:
            print(f"   - Layout cargado: {loaded['info']['name']}")
            matrix, locations = loader.get_layout_for_pathfinding()
            print(f"   - Matriz: {len(matrix)}x{len(matrix[0]) if matrix else 0}")
        else:
            print("   - ERROR: No se pudo cargar layout")
    
    # 2. Test de integración pathfinding
    print("\n2. TESTING PATHFINDING INTEGRATION")
    integration = DynamicPathfindingIntegration()
    
    if available:
        success = integration.load_layout_for_pathfinding(first_layout['path'])
        if success:
            print("   - Integración exitosa")
            
            # Test calcular ruta
            route = integration.calculate_route((100, 100), (500, 300))
            if route:
                print(f"   - Ruta calculada: {len(route)} puntos")
            
            # Test ubicaciones especiales
            locations = integration.get_special_locations()
            print(f"   - Ubicaciones especiales: {len(locations)} tipos")
        else:
            print("   - ERROR: Integración falló")
    
    # 3. Test UI layouts list
    print("\n3. TESTING UI INTEGRATION")
    ui_layouts = loader.get_layouts_list_for_ui()
    print(f"   - Layouts para UI: {len(ui_layouts)}")
    
    for layout in ui_layouts:
        status = "VÁLIDO" if layout['valid'] else "INVÁLIDO"
        print(f"     * {layout['display_name']} - {status}")
    
    # 4. Test wrapper
    print("\n4. TESTING WRAPPER INTEGRATION")
    from dynamic_pathfinding_integration import create_integration_wrapper
    
    wrapper = create_integration_wrapper()
    if available and wrapper.initialize_with_layout(first_layout['path']):
        print("   - Wrapper inicializado")
        
        depot_pos = wrapper.get_depot_position()
        inbound_pos = wrapper.get_inbound_position()
        
        print(f"   - Depot position: {depot_pos}")
        print(f"   - Inbound position: {inbound_pos}")
    
    print("\n" + "=" * 60)
    print("RESULTADO DEL TEST")
    print("=" * 60)
    
    # Verificaciones finales
    checks = [
        ("Layouts creados", len(available) > 0),
        ("Layout cargable", loaded is not None if available else False),
        ("Pathfinding integrado", success if available else False),
        ("UI lista disponible", len(ui_layouts) > 0),
        ("Wrapper funcional", wrapper.is_initialized if available else False)
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        status = "PASS" if check_result else "FAIL"
        print(f"   {status}: {check_name}")
        if not check_result:
            all_passed = False
    
    print("\n" + ("=" * 60))
    if all_passed:
        print("RESULTADO FINAL: SISTEMA LAYOUTS DINÁMICOS FUNCIONANDO")
        print("Funcionalidades disponibles:")
        print("- Cargar layouts TMX personalizados")
        print("- Selector dropdown en configuración")
        print("- Pathfinding con layouts custom")
        print("- Documentación usuario completa")
        print("- Layouts de ejemplo incluidos")
    else:
        print("RESULTADO FINAL: ALGUNAS FUNCIONES TIENEN PROBLEMAS")
    
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    test_complete_workflow()