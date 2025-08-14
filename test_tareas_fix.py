#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST FIX - VERIFICAR CREACIÓN DE TAREAS CORREGIDA
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_tareas_con_config_correcta():
    """Test con configuración en formato correcto"""
    
    print("=" * 60)
    print("TEST FIX - CREACIÓN DE TAREAS CON CONFIG CORRECTA")
    print("=" * 60)
    
    try:
        # Configuración en formato correcto que espera AlmacenMejorado
        config_correcta = {
            'use_dynamic_layout': False,
            'total_tareas_picking': 50,  # NOMBRE CORRECTO
            'distribucion_tipos': {      # FORMATO CORRECTO
                'pequeno': 60,
                'mediano': 30,
                'grande': 10
            },
            'volumenes': {               # FORMATO CORRECTO
                'pequeno': 5,
                'mediano': 25,
                'grande': 80
            },
            'capacidad_carro': 150,
            'num_operarios_terrestres': 3,
            'num_montacargas': 1
        }
        
        print("1. Configuración corregida:")
        print(f"   total_tareas_picking: {config_correcta['total_tareas_picking']}")
        print(f"   distribucion_tipos: {config_correcta['distribucion_tipos']}")
        
        # Crear almacén
        from simulation.warehouse import AlmacenMejorado
        import simpy
        
        env = simpy.Environment()
        almacen = AlmacenMejorado(env, config_correcta)
        
        print("\n2. Almacén creado:")
        print(f"   total_tareas: {almacen.total_tareas}")
        print(f"   total_tareas_picking: {almacen.total_tareas_picking}")
        print(f"   bolsa_tareas_picking: {len(almacen.bolsa_tareas_picking)}")
        
        # Verificar que hay tareas
        hay_tareas = almacen.hay_tareas_pendientes()
        print(f"   hay_tareas_pendientes(): {hay_tareas}")
        
        if almacen.bolsa_tareas_picking:
            print("\n3. Ejemplo de tarea de picking:")
            tarea_ejemplo = almacen.bolsa_tareas_picking[0]
            print(f"   ID: {tarea_ejemplo.get('id', 'N/A')}")
            print(f"   Tipo: {tarea_ejemplo.get('tipo', 'N/A')}")
            print(f"   Volumen: {tarea_ejemplo.get('volumen_l', 'N/A')}")
            print(f"   Coordenadas: {tarea_ejemplo.get('coordenadas', 'N/A')}")
        
        # Test crear operarios
        print("\n4. Creando operarios...")
        from simulation.operators import crear_operarios
        
        procesos_operarios = crear_operarios(env, almacen, config_correcta)
        print(f"   Operarios creados: {len(procesos_operarios)}")
        
        # Test estado visual
        from visualization.state import inicializar_estado, estado_visual
        
        inicializar_estado(almacen, env, config_correcta)
        print(f"   Operarios en estado visual: {len(estado_visual.get('operarios', {}))}")
        
        print("\n" + "=" * 60)
        if almacen.total_tareas > 0 and len(procesos_operarios) > 0:
            print("✓ ÉXITO: TAREAS Y OPERARIOS CREADOS CORRECTAMENTE")
            print("Los operarios deberían moverse ahora en la simulación")
        else:
            print("✗ ERROR: Aún faltan tareas u operarios")
        
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_config_window_fix():
    """Test de la ventana de configuración corregida"""
    
    print("\n" + "=" * 40)
    print("TEST VENTANA CONFIGURACIÓN CORREGIDA")
    print("=" * 40)
    
    try:
        from enhanced_config_window import EnhancedConfigWindow
        
        # Crear ventana sin mostrar
        window = EnhancedConfigWindow()
        
        # Simular valores
        window.total_tareas_picking.set(100)
        window.pct_pequeno.set(60)
        window.pct_mediano.set(30)
        window.pct_grande.set(10)
        window.vol_pequeno.set(5)
        window.vol_mediano.set(25)
        window.vol_grande.set(80)
        window.capacidad_carro.set(150)
        window.num_operarios_terrestres.set(4)
        window.num_montacargas.set(2)
        
        # Simular configuración generada
        config_simulada = {
            'total_tareas_picking': window.total_tareas_picking.get(),
            'distribucion_tipos': {
                'pequeno': window.pct_pequeno.get(),
                'mediano': window.pct_mediano.get(),
                'grande': window.pct_grande.get()
            },
            'volumenes': {
                'pequeno': window.vol_pequeno.get(),
                'mediano': window.vol_mediano.get(),
                'grande': window.vol_grande.get()
            },
            'capacidad_carro': window.capacidad_carro.get(),
            'num_operarios_terrestres': window.num_operarios_terrestres.get(),
            'num_montacargas': window.num_montacargas.get()
        }
        
        print("✓ Configuración corregida:")
        print(f"   total_tareas_picking: {config_simulada['total_tareas_picking']}")
        print(f"   operarios_terrestres: {config_simulada['num_operarios_terrestres']}")
        
        # Cerrar ventana
        window.root.destroy()
        
        return config_simulada
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    # Test 1: Ventana corregida
    config = test_enhanced_config_window_fix()
    
    # Test 2: Creación de tareas
    if config:
        test_tareas_con_config_correcta()
    else:
        print("No se pudo generar configuración")