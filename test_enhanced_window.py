#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST RÁPIDO - VENTANA DE CONFIGURACIÓN MEJORADA
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from enhanced_config_window import EnhancedConfigWindow

def test_enhanced_window():
    """Test básico de la ventana mejorada"""
    
    print("=" * 50)
    print("TEST - VENTANA DE CONFIGURACIÓN MEJORADA")
    print("=" * 50)
    
    print("1. Verificando imports...")
    try:
        window = EnhancedConfigWindow()
        print("   ✓ EnhancedConfigWindow creada")
    except Exception as e:
        print(f"   ✗ Error creando ventana: {e}")
        return False
    
    print("2. Verificando carga de layouts...")
    try:
        # Verificar que los layouts se cargan
        if hasattr(window, 'available_layouts'):
            print(f"   ✓ Layouts disponibles: {len(window.available_layouts)}")
        else:
            print("   ✗ No se encontró lista de layouts")
    except Exception as e:
        print(f"   ✗ Error verificando layouts: {e}")
    
    print("3. Verificando UI...")
    try:
        # Verificar que los widgets se crearon
        if hasattr(window, 'layout_dropdown'):
            values = window.layout_dropdown['values']
            print(f"   ✓ Dropdown creado con {len(values)} opciones")
            
            if values:
                print(f"   ✓ Primera opción: {values[0]}")
            else:
                print("   ! Dropdown vacío (normal si no hay TMX válidos)")
        else:
            print("   ✗ Dropdown no encontrado")
    except Exception as e:
        print(f"   ✗ Error verificando UI: {e}")
    
    print("\n" + "=" * 50)
    print("TEST COMPLETADO")
    print("Si no hay errores ✗, la ventana debería mostrar el dropdown")
    print("=" * 50)
    
    # Cerrar ventana sin mostrar
    window.root.destroy()
    
    return True

if __name__ == "__main__":
    test_enhanced_window()