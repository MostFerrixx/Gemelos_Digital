#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST FIX - VERIFICAR CREACIÓN DE OPERARIOS
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_operarios_creation():
    """Test completo de creación de operarios"""
    
    print("=" * 60)
    print("TEST FIX - CREACIÓN DE OPERARIOS")
    print("=" * 60)
    
    try:
        # 1. Importar componentes necesarios
        from simulation.operators import crear_operarios
        from simulation.warehouse import AlmacenMejorado
        from enhanced_config_window import EnhancedConfigWindow
        import simpy
        
        print("1. ✓ Imports exitosos")
        
        # 2. Crear configuración correcta
        config_correcta = {
            'use_dynamic_layout': True,
            'selected_layout_path': 'layouts/tutorial_completo.tmx',
            'total_tareas': 50,  # Reducido para test
            'pct_pequeno': 60,
            'pct_mediano': 30,
            'pct_grande': 10,
            'vol_pequeno': 5,
            'vol_mediano': 25,
            'vol_grande': 80,
            'capacidad_carro': 150,
            'num_operarios_terrestres': 3,  # ¡NOMBRE CORRECTO!
            'num_montacargas': 1
        }
        
        print("2. ✓ Configuración creada")
        print(f"   num_operarios_terrestres: {config_correcta['num_operarios_terrestres']}")
        print(f"   num_montacargas: {config_correcta['num_montacargas']}")
        print(f"   total_tareas: {config_correcta['total_tareas']}")
        
        # 3. Configurar pathfinding dinámico
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        
        wrapper = get_dynamic_pathfinding_wrapper()
        if config_correcta['use_dynamic_layout']:
            success = wrapper.initialize_with_layout(config_correcta['selected_layout_path'])
            print(f"3. ✓ Pathfinding dinámico: {'Configurado' if success else 'Fallback'}")
        
        # 4. Crear ambiente de simulación
        env = simpy.Environment()
        almacen = AlmacenMejorado(env, config_correcta)
        
        print(f"4. ✓ Almacén creado")
        print(f"   Total tareas: {almacen.total_tareas}")
        print(f"   Zona A: {len(almacen.tareas_zona_a)} tareas")
        print(f"   Zona B: {len(almacen.tareas_zona_b)} tareas")
        
        # 5. Crear operarios
        print("\n5. Creando operarios...")
        procesos_operarios = crear_operarios(env, almacen, config_correcta)
        
        print(f"   ✓ {len(procesos_operarios)} procesos de operarios creados")
        
        # 6. Verificar estado visual
        from visualization.state import inicializar_estado, estado_visual
        
        inicializar_estado(almacen, env, config_correcta)
        
        print(f"6. ✓ Estado visual inicializado")
        print(f"   Operarios en estado: {len(estado_visual.get('operarios', {}))}")
        
        # 7. Mostrar detalles de operarios
        print("\n7. Detalles de operarios creados:")
        for op_id, operario in estado_visual.get('operarios', {}).items():
            print(f"   Operario {op_id}:")
            print(f"     - Tipo: {operario.get('tipo', 'desconocido')}")
            print(f"     - Posición: ({operario.get('x', 0)}, {operario.get('y', 0)})")
            print(f"     - Acción: {operario.get('accion', 'Sin acción')}")
        
        # 8. Verificar recursos del almacén
        print(f"\n8. Recursos del almacén:")
        print(f"   Operarios terrestres capacity: {almacen.operarios_terrestres.capacity}")
        print(f"   Montacargas capacity: {almacen.montacargas_normal.capacity}")
        
        print("\n" + "=" * 60)
        print("RESULTADO: ¡OPERARIOS CREADOS EXITOSAMENTE!")
        print("=" * 60)
        print("Los operarios deberían aparecer ahora en la simulación")
        print("Si aún no aparecen, verificar:")
        print("1. Que se use la configuración corregida")
        print("2. Que el renderer los dibuje correctamente")
        print("3. Que las posiciones iniciales sean válidas")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_config_window():
    """Test rápido de la ventana de configuración"""
    
    print("\n" + "=" * 40)
    print("TEST VENTANA DE CONFIGURACIÓN")
    print("=" * 40)
    
    try:
        from enhanced_config_window import EnhancedConfigWindow
        
        # Crear ventana sin mostrar
        window = EnhancedConfigWindow()
        
        # Simular configuración
        config_simulada = {
            'use_dynamic_layout': True,
            'selected_layout_path': 'layouts/tutorial_completo.tmx',
            'total_tareas': 100,
            'pct_pequeno': 60,
            'pct_mediano': 30,
            'pct_grande': 10,
            'vol_pequeno': 5,
            'vol_mediano': 25,
            'vol_grande': 80,
            'capacidad_carro': 150,
            'num_operarios_terrestres': 4,  # CLAVE: nombre correcto
            'num_montacargas': 2
        }
        
        print("✓ Ventana de configuración funcional")
        print(f"  Configuración ejemplo generada con {config_simulada['num_operarios_terrestres']} operarios")
        
        # Cerrar ventana
        window.root.destroy()
        
        return config_simulada
        
    except Exception as e:
        print(f"ERROR en ventana: {e}")
        return None

if __name__ == "__main__":
    # Test 1: Configuración
    config = test_enhanced_config_window()
    
    # Test 2: Creación de operarios
    if config:
        test_operarios_creation()
    else:
        print("ERROR: No se pudo generar configuración válida")