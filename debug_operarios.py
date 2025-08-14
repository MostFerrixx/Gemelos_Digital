#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG - DIAGNÓSTICO DE OPERARIOS EN SIMULACIÓN
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def debug_operarios_config():
    """Diagnosticar configuración de operarios"""
    
    print("=" * 60)
    print("DIAGNÓSTICO - OPERARIOS EN SIMULACIÓN")
    print("=" * 60)
    
    try:
        # 1. Verificar imports del sistema
        print("1. Verificando imports...")
        
        from simulation.operators import crear_operarios
        from config.settings import NUM_OPERARIOS, POS_DEPOT, POS_INBOUND
        from enhanced_config_window import EnhancedConfigWindow
        
        print("   OK: Imports exitosos")
        print(f"   NUM_OPERARIOS default: {NUM_OPERARIOS}")
        print(f"   POS_DEPOT default: {POS_DEPOT}")
        print(f"   POS_INBOUND default: {POS_INBOUND}")
        
        # 2. Simular configuración típica
        print("\n2. Simulando configuración típica...")
        
        config_simulada = {
            'use_dynamic_layout': True,
            'selected_layout_path': 'layouts/tutorial_completo.tmx',
            'total_tareas': 300,
            'pct_pequeno': 60,
            'pct_mediano': 30,
            'pct_grande': 10,
            'vol_pequeno': 5,
            'vol_mediano': 25,
            'vol_grande': 80,
            'capacidad_carro': 150,
            'num_operarios': 4,  # ¡CLAVE!
            'num_montacargas': 2
        }
        
        print("   Configuración simulada:")
        print(f"     - num_operarios: {config_simulada['num_operarios']}")
        print(f"     - use_dynamic_layout: {config_simulada['use_dynamic_layout']}")
        print(f"     - selected_layout_path: {config_simulada['selected_layout_path']}")
        
        # 3. Verificar sistema de pathfinding dinámico
        print("\n3. Verificando pathfinding dinámico...")
        
        from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
        
        wrapper = get_dynamic_pathfinding_wrapper()
        if config_simulada['use_dynamic_layout']:
            success = wrapper.initialize_with_layout(config_simulada['selected_layout_path'])
            if success:
                depot_pos = wrapper.get_depot_position()
                inbound_pos = wrapper.get_inbound_position()
                print(f"   OK: Layout dinámico cargado")
                print(f"   Depot dinámico: {depot_pos}")
                print(f"   Inbound dinámico: {inbound_pos}")
            else:
                print("   ERROR: No se pudo cargar layout dinámico")
        
        # 4. Verificar creación de operarios (simulado)
        print("\n4. Verificando creación de operarios...")
        
        try:
            import simpy
            env = simpy.Environment()
            
            # Simular almacén básico
            class AlmacenSimulado:
                def __init__(self, config):
                    self.config = config
                    self.total_tareas = config['total_tareas']
                    self.tareas_zona_a = list(range(150))  # Simular tareas
                    self.tareas_zona_b = list(range(150))
                    
                    # Recursos simulados
                    self.operarios_terrestres = simpy.Resource(env, capacity=config['num_operarios'])
                    self.montacargas_normal = simpy.Resource(env, capacity=config['num_montacargas'])
                    self.montacargas_altura = simpy.Resource(env, capacity=1)
            
            almacen = AlmacenSimulado(config_simulada)
            
            # Intentar crear operarios
            print(f"   Creando {config_simulada['num_operarios']} operarios...")
            
            # Verificar si la función crear_operarios existe y funciona
            procesos = crear_operarios(env, almacen, config_simulada)
            
            print(f"   OK: {len(procesos)} procesos de operarios creados")
            
            # Verificar tipos de procesos
            if procesos:
                print("   Tipos de procesos creados:")
                for i, proceso in enumerate(procesos):
                    print(f"     - Proceso {i}: {type(proceso)}")
            
        except Exception as e:
            print(f"   ERROR en creación de operarios: {e}")
            import traceback
            traceback.print_exc()
        
        # 5. Verificar estado visual
        print("\n5. Verificando sistema de visualización...")
        
        try:
            from visualization.state import inicializar_estado, estado_visual
            
            print("   OK: Sistema de visualización disponible")
            
            # Simular inicialización
            inicializar_estado(almacen, env, config_simulada)
            
            print(f"   Estado visual inicializado")
            print(f"   Operarios en estado: {len(estado_visual.get('operarios', {}))}")
            
        except Exception as e:
            print(f"   ERROR en visualización: {e}")
        
        print("\n" + "=" * 60)
        print("POSIBLES PROBLEMAS Y SOLUCIONES:")
        print("=" * 60)
        
        problemas = [
            ("num_operarios = 0", "Verificar que se pase num_operarios > 0 en config"),
            ("Layout dinámico sin depot", "Verificar que layout tenga objetos depot e inbound"),
            ("Error en crear_operarios()", "Verificar compatibilidad con config dinámico"),
            ("Estado visual no actualizado", "Verificar inicializar_estado() con config"),
            ("Pathfinding no configurado", "Verificar wrapper.initialize_with_layout()"),
        ]
        
        for problema, solucion in problemas:
            print(f"   PROBLEMA: {problema}")
            print(f"   SOLUCIÓN: {solucion}")
            print()
        
        print("=" * 60)
        print("SIGUIENTE PASO: Revisar run_simulator.py")
        print("Verificar que la configuración se pase correctamente")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR EN DIAGNÓSTICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_operarios_config()