#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG - DIAGNÓSTICO DE CREACIÓN DE TAREAS
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def debug_tareas_creation():
    """Diagnosticar por qué no se crean tareas"""
    
    print("=" * 60)
    print("DIAGNÓSTICO - CREACIÓN DE TAREAS")
    print("=" * 60)
    
    try:
        # 1. Verificar configuración típica
        config = {
            'use_dynamic_layout': False,
            'total_tareas': 100,  # Debe generar tareas
            'pct_pequeno': 60,
            'pct_mediano': 30,
            'pct_grande': 10,
            'vol_pequeno': 5,
            'vol_mediano': 25,
            'vol_grande': 80,
            'capacidad_carro': 150,
            'num_operarios_terrestres': 3,
            'num_montacargas': 1
        }
        
        print("1. Configuración de test:")
        print(f"   total_tareas: {config['total_tareas']}")
        print(f"   operarios: {config['num_operarios_terrestres']}")
        
        # 2. Crear almacén y verificar tareas
        from simulation.warehouse import AlmacenMejorado
        import simpy
        
        env = simpy.Environment()
        almacen = AlmacenMejorado(env, config)
        
        print("\n2. Almacén creado:")
        print(f"   total_tareas: {almacen.total_tareas}")
        print(f"   tareas_zona_a: {len(almacen.tareas_zona_a)}")
        print(f"   tareas_zona_b: {len(almacen.tareas_zona_b)}")
        
        # 3. Verificar contenido de las tareas
        if almacen.tareas_zona_a:
            print("\n3. Ejemplo tarea Zona A:")
            tarea_ejemplo = almacen.tareas_zona_a[0]
            print(f"   ID: {tarea_ejemplo.get('id', 'N/A')}")
            print(f"   Tipo: {tarea_ejemplo.get('tipo', 'N/A')}")
            print(f"   Nivel: {tarea_ejemplo.get('nivel_h', 'N/A')}")
            print(f"   Coordenadas: {tarea_ejemplo.get('coordenadas', 'N/A')}")
            print(f"   Volumen: {tarea_ejemplo.get('volumen_l', 'N/A')}")
        else:
            print("\n3. ERROR: No hay tareas en Zona A")
        
        if almacen.tareas_zona_b:
            print("\n4. Ejemplo tarea Zona B:")
            tarea_ejemplo = almacen.tareas_zona_b[0]
            print(f"   ID: {tarea_ejemplo.get('id', 'N/A')}")
            print(f"   Tipo: {tarea_ejemplo.get('tipo', 'N/A')}")
            print(f"   Nivel: {tarea_ejemplo.get('nivel_h', 'N/A')}")
            print(f"   Coordenadas: {tarea_ejemplo.get('coordenadas', 'N/A')}")
            print(f"   Volumen: {tarea_ejemplo.get('volumen_l', 'N/A')}")
        else:
            print("\n4. ERROR: No hay tareas en Zona B")
        
        # 5. Verificar método hay_tareas_pendientes
        hay_pendientes = almacen.hay_tareas_pendientes()
        print(f"\n5. hay_tareas_pendientes(): {hay_pendientes}")
        
        # 6. Verificar distribución esperada
        total_esperado = config['total_tareas']
        zona_a_esperado = int(total_esperado * 0.5)  # Supongamos 50-50
        zona_b_esperado = total_esperado - zona_a_esperado
        
        print(f"\n6. Distribución esperada vs real:")
        print(f"   Total esperado: {total_esperado}, Real: {almacen.total_tareas}")
        print(f"   Zona A esperado: ~{zona_a_esperado}, Real: {len(almacen.tareas_zona_a)}")
        print(f"   Zona B esperado: ~{zona_b_esperado}, Real: {len(almacen.tareas_zona_b)}")
        
        # 7. Verificar si es problema de configuración de layout dinámico
        print(f"\n7. Configuración layout:")
        print(f"   use_dynamic_layout: {config['use_dynamic_layout']}")
        
        if config['use_dynamic_layout']:
            print("   Verificando ubicaciones dinámicas...")
            from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
            wrapper = get_dynamic_pathfinding_wrapper()
            locations = wrapper.get_picking_locations()
            print(f"   Ubicaciones picking dinámicas: {len(locations)}")
        
        print("\n" + "=" * 60)
        print("POSIBLES PROBLEMAS:")
        print("=" * 60)
        
        if almacen.total_tareas == 0:
            print("PROBLEMA 1: total_tareas = 0")
            print("  - Verificar que config['total_tareas'] > 0")
            print("  - Verificar AlmacenMejorado.__init__()")
            
        if len(almacen.tareas_zona_a) == 0 and len(almacen.tareas_zona_b) == 0:
            print("PROBLEMA 2: No se generan tareas en ninguna zona")
            print("  - Verificar generador de tareas")
            print("  - Verificar ubicaciones de picking")
            
        if not hay_pendientes:
            print("PROBLEMA 3: hay_tareas_pendientes() = False")
            print("  - Operarios no buscarán tareas")
            print("  - Verificar lógica del método")
        
        print("\nRECOMENDACIONES:")
        print("1. Verificar AlmacenMejorado.__init__() recibe config correctamente")
        print("2. Verificar generación de tareas usa config['total_tareas']")
        print("3. Verificar ubicaciones de picking están disponibles")
        print("4. Verificar que hay_tareas_pendientes() detecta las tareas")
        
        print("=" * 60)
        
        return almacen
        
    except Exception as e:
        print(f"ERROR EN DIAGNÓSTICO: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    almacen = debug_tareas_creation()