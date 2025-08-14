#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO DE SELECCIÓN DE LAYOUT - Verificar qué está pasando
"""

import os
import sys

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_layout_loading():
    """Probar carga de layouts paso a paso"""
    
    print("="*70)
    print("DIAGNÓSTICO DE CARGA DE LAYOUTS")
    print("="*70)
    
    # 1. Verificar dynamic layout loader
    print("\n1. PROBANDO DYNAMIC LAYOUT LOADER:")
    try:
        from dynamic_layout_loader import DynamicLayoutLoader
        loader = DynamicLayoutLoader("layouts")
        
        # Escanear layouts disponibles
        layouts = loader.scan_available_layouts()
        print(f"   Layouts encontrados: {len(layouts)}")
        
        for layout in layouts:
            print(f"   - {layout['name']}: {layout.get('valid', 'Unknown')}")
            if layout['name'] == 'WH1':
                print(f"     WH1 encontrado: {layout}")
                
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 2. Probar carga específica de WH1
    print("\n2. PROBANDO CARGA ESPECÍFICA DE WH1:")
    try:
        wh1_path = "layouts/WH1.tmx"
        if os.path.exists(wh1_path):
            print(f"   WH1.tmx existe: {wh1_path}")
            
            # Probar con el loader
            result = loader.load_layout(wh1_path)
            if result:
                print(f"   WH1 cargado exitosamente")
                print(f"   Dimensiones: {result['info']['width']}x{result['info']['height']}")
                
                # Verificar matriz de navegación
                nav_matrix = result.get('navigation_matrix', [])
                if nav_matrix:
                    total_tiles = len(nav_matrix) * len(nav_matrix[0]) if nav_matrix else 0
                    walkable_tiles = sum(sum(row) for row in nav_matrix)
                    walkable_pct = (walkable_tiles / total_tiles) * 100 if total_tiles > 0 else 0
                    print(f"   Navegabilidad: {walkable_tiles}/{total_tiles} ({walkable_pct:.1f}%)")
                    
                    if walkable_pct == 100:
                        print("   ⚠️  WARNING: 100% navegable = usando fallback genérico")
                    else:
                        print(f"   ✅ OK: {walkable_pct:.1f}% navegable = layout personalizado")
                else:
                    print("   ❌ ERROR: No hay matriz de navegación")
            else:
                print("   ❌ ERROR: No se pudo cargar WH1")
        else:
            print(f"   ❌ ERROR: WH1.tmx no existe en {wh1_path}")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 3. Probar integración pathfinding
    print("\n3. PROBANDO INTEGRACIÓN PATHFINDING:")
    try:
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        wrapper = get_dynamic_pathfinding_wrapper()
        
        if wrapper.initialize_with_layout("layouts/WH1.tmx"):
            print("   ✅ WH1 inicializado en pathfinding wrapper")
        else:
            print("   ❌ ERROR: WH1 no se pudo inicializar en pathfinding")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 4. Verificar parches aplicados
    print("\n4. VERIFICANDO PARCHES APLICADOS:")
    try:
        # Verificar si el parche WH1 está activo
        from dynamic_layout_loader import DynamicLayoutLoader
        
        # Buscar métodos patcheados
        methods = dir(DynamicLayoutLoader)
        patched_methods = [m for m in methods if 'original' in m.lower() or 'wh1' in m.lower()]
        
        if patched_methods:
            print(f"   Métodos patcheados encontrados: {patched_methods}")
        else:
            print("   ⚠️  WARNING: No se detectaron parches aplicados")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 5. Simular selección WH1
    print("\n5. SIMULANDO SELECCIÓN DE WH1:")
    try:
        # Simular configuración como la haría el simulador
        config = {
            'use_dynamic_layout': True,
            'selected_layout_path': 'layouts/WH1.tmx'
        }
        
        print(f"   Configuración simulada: {config}")
        
        # Probar inicialización como en run_simulator.py
        wrapper = get_dynamic_pathfinding_wrapper()
        if wrapper.initialize_with_layout(config['selected_layout_path']):
            print("   ✅ WH1 se inicializaría correctamente")
            
            # Verificar si está usando layout personalizado
            # (Esto requeriría acceso interno al wrapper)
            print("   ✅ Simulación exitosa")
        else:
            print("   ❌ ERROR: WH1 fallaría en inicialización")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print(f"\n{'='*70}")
    print("RESUMEN DEL DIAGNÓSTICO:")
    print(f"{'='*70}")
    print("Si ves '100% navegable' en cualquier parte = problema detectado")
    print("Si ves '60% navegable' = WH1 funcionando correctamente")
    print("Si ves errores de pathfinding = problema de integración")
    print(f"{'='*70}")

if __name__ == "__main__":
    test_layout_loading()