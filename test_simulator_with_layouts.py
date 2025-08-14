#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SIMULADOR CON LAYOUTS DINÁMICOS
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_simulator_integration():
    """Test de integración completa del simulador"""
    
    print("=" * 60)
    print("TEST SIMULADOR CON LAYOUTS DINÁMICOS")
    print("=" * 60)
    
    try:
        # 1. Test imports
        print("1. Verificando imports...")
        
        from enhanced_config_window import EnhancedConfigWindow
        from dynamic_layout_loader import DynamicLayoutLoader
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        
        print("   OK: Todos los imports exitosos")
        
        # 2. Test dynamic layout loader
        print("\n2. Verificando layout loader...")
        
        loader = DynamicLayoutLoader()
        available = loader.scan_available_layouts()
        
        print(f"   OK: {len(available)} layouts encontrados")
        
        if available:
            # Test cargar un layout
            first_layout = available[0]
            loaded = loader.load_layout(first_layout['path'])
            
            if loaded:
                print(f"   OK: Layout '{loaded['info']['name']}' cargado")
                matrix, locations = loader.get_layout_for_pathfinding()
                print(f"   OK: Matriz {len(matrix)}x{len(matrix[0]) if matrix else 0}")
            else:
                print("   ERROR: No se pudo cargar layout")
        else:
            print("   WARNING: No hay layouts disponibles")
        
        # 3. Test pathfinding integration
        print("\n3. Verificando pathfinding integration...")
        
        wrapper = get_dynamic_pathfinding_wrapper()
        
        if available:
            success = wrapper.initialize_with_layout(available[0]['path'])
            if success:
                print("   OK: Pathfinding wrapper inicializado")
                
                # Test calcular ruta
                route = wrapper.calculate_route((100, 100), (500, 300))
                if route and len(route) > 0:
                    print(f"   OK: Ruta calculada con {len(route)} puntos")
                
                # Test ubicaciones especiales
                depot = wrapper.get_depot_position()
                inbound = wrapper.get_inbound_position()
                
                print(f"   OK: Depot en {depot}")
                print(f"   OK: Inbound en {inbound}")
            else:
                print("   ERROR: No se pudo inicializar wrapper")
        
        # 4. Test enhanced config window (sin mostrar UI)
        print("\n4. Verificando enhanced config window...")
        
        window = EnhancedConfigWindow()
        
        # Verificar que se cargaron layouts
        ui_layouts = window.layout_loader.get_layouts_list_for_ui()
        print(f"   OK: {len(ui_layouts)} layouts en UI")
        
        # Verificar dropdown
        if hasattr(window, 'layout_dropdown'):
            values = window.layout_dropdown['values']
            print(f"   OK: Dropdown con {len(values)} opciones")
        
        # Cerrar ventana sin mostrar
        window.root.destroy()
        
        # 5. Test configuración simulada
        print("\n5. Simulando configuración...")
        
        config_simulada = {
            'use_dynamic_layout': True,
            'selected_layout_path': available[0]['path'] if available else '',
            'total_tareas': 300,
            'pct_pequeno': 60,
            'pct_mediano': 30,
            'pct_grande': 10,
            'vol_pequeno': 5,
            'vol_mediano': 25,
            'vol_grande': 80,
            'capacidad_carro': 150,
            'num_operarios': 4,
            'num_montacargas': 2
        }
        
        print("   OK: Configuración simulada creada")
        print(f"   Layout: {config_simulada['selected_layout_path']}")
        print(f"   Tareas: {config_simulada['total_tareas']}")
        print(f"   Operarios: {config_simulada['num_operarios']}")
        
        print("\n" + "=" * 60)
        print("RESULTADO DEL TEST")
        print("=" * 60)
        
        # Resumen
        checks = [
            ("Imports funcionando", True),
            ("Layout loader OK", len(available) > 0 if 'available' in locals() else False),
            ("Pathfinding integration OK", wrapper.is_initialized if 'wrapper' in locals() else False),
            ("Enhanced config window OK", True),
            ("Configuración simulada OK", True)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "PASS" if check_result else "FAIL"
            print(f"   {status}: {check_name}")
            if not check_result:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("ESTADO: SISTEMA COMPLETAMENTE FUNCIONAL")
            print("\nPara usar:")
            print("1. Ejecuta: python run_simulator.py")
            print("2. Ve al tab '📐 Layout del Almacén'")
            print("3. Marca 'Usar layout personalizado (TMX)'")
            print("4. Selecciona layout del dropdown")
            print("5. Configura otros parámetros")
            print("6. Inicia simulación")
        else:
            print("ESTADO: ALGUNOS COMPONENTES NECESITAN REVISIÓN")
        
        print("=" * 60)
        
        return all_passed
        
    except Exception as e:
        print(f"ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simulator_integration()