#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SIMPLE - OPERARIOS SIN EMOJIS
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def main():
    """Test simple de operarios"""
    
    print("=" * 50)
    print("TEST SIMPLE - OPERARIOS")
    print("=" * 50)
    
    try:
        # Configuración correcta
        config = {
            'use_dynamic_layout': False,  # Usar layout por defecto
            'total_tareas': 50,
            'pct_pequeno': 60,
            'pct_mediano': 30,
            'pct_grande': 10,
            'vol_pequeno': 5,
            'vol_mediano': 25,
            'vol_grande': 80,
            'capacidad_carro': 150,
            'num_operarios_terrestres': 3,  # CLAVE
            'num_montacargas': 1
        }
        
        print("1. Configuracion creada")
        print(f"   num_operarios_terrestres: {config['num_operarios_terrestres']}")
        
        # Importar y crear
        from simulation.operators import crear_operarios
        from simulation.warehouse import AlmacenMejorado
        import simpy
        
        env = simpy.Environment()
        almacen = AlmacenMejorado(env, config)
        
        print("2. Almacen creado")
        
        # Crear operarios
        procesos = crear_operarios(env, almacen, config)
        
        print(f"3. Operarios creados: {len(procesos)} procesos")
        
        # Verificar estado
        from visualization.state import inicializar_estado, estado_visual
        inicializar_estado(almacen, env, config)
        
        operarios_en_estado = len(estado_visual.get('operarios', {}))
        print(f"4. Operarios en estado visual: {operarios_en_estado}")
        
        if operarios_en_estado > 0:
            print("EXITO: Los operarios se crearon correctamente")
            
            for op_id, op_data in estado_visual['operarios'].items():
                print(f"   Operario {op_id}: {op_data.get('tipo')} en ({op_data.get('x')}, {op_data.get('y')})")
        else:
            print("ERROR: No hay operarios en el estado visual")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()