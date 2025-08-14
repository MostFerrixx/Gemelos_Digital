#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SIMPLE - TAREAS CON CONFIGURACIÓN CORRECTA
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def main():
    """Test simple de tareas con configuración correcta"""
    
    print("=" * 50)
    print("TEST SIMPLE - TAREAS")
    print("=" * 50)
    
    try:
        # Configuración CORRECTA para AlmacenMejorado
        config = {
            'total_tareas_picking': 50,  # NOMBRE CORRECTO
            'distribucion_tipos': {      # ESTRUCTURA CORRECTA COMPLETA
                'pequeno': {
                    'porcentaje': 60,
                    'volumen': 5
                },
                'mediano': {
                    'porcentaje': 30,
                    'volumen': 25
                },
                'grande': {
                    'porcentaje': 10,
                    'volumen': 80
                }
            },
            'capacidad_carro': 150,
            'num_operarios_terrestres': 3,
            'num_montacargas': 1
        }
        
        print("1. Config correcta creada")
        print(f"   total_tareas_picking: {config['total_tareas_picking']}")
        
        # Crear almacén
        from simulation.warehouse import AlmacenMejorado
        import simpy
        
        env = simpy.Environment()
        almacen = AlmacenMejorado(env, config)
        
        print("2. Almacen creado")
        print(f"   total_tareas: {almacen.total_tareas}")
        print(f"   bolsa_tareas_picking: {len(almacen.bolsa_tareas_picking)}")
        
        # Verificar estado
        hay_tareas = almacen.hay_tareas_pendientes()
        print(f"3. hay_tareas_pendientes: {hay_tareas}")
        
        if hay_tareas and len(almacen.bolsa_tareas_picking) > 0:
            print("EXITO: Las tareas se crearon correctamente")
            
            # Mostrar ejemplo de tarea
            tarea = almacen.bolsa_tareas_picking[0]
            print(f"   Ejemplo tarea: ID={tarea.get('id')}, vol={tarea.get('volumen_l')}")
        else:
            print("ERROR: No se crearon tareas")
            
        print("=" * 50)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()