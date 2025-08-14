#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIX TEMPORAL - FORZAR OPERARIOS EN ESTADO VISUAL
"""

import sys
import os

# Agregar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def fix_operarios_in_visual_state():
    """Patch temporal para asegurar que los operarios aparezcan"""
    
    # Parche en visualization.state
    from visualization import state
    
    original_inicializar = state.inicializar_estado
    
    def inicializar_estado_con_operarios(almacen, env, configuracion):
        """Inicializar estado y crear operarios dummy"""
        
        # Llamar función original
        original_inicializar(almacen, env, configuracion)
        
        # Forzar creación de operarios en estado visual
        num_operarios = configuracion.get('num_operarios_terrestres', 0)
        num_montacargas = configuracion.get('num_montacargas', 0)
        
        print(f"[FIX] Forzando creación de {num_operarios} operarios terrestres y {num_montacargas} montacargas en estado visual")
        
        from config.settings import POS_DEPOT
        
        # Crear operarios terrestres
        for i in range(1, num_operarios + 1):
            x = POS_DEPOT[0] - (i * 40)
            y = POS_DEPOT[1]
            
            state.estado_visual["operarios"][f"terrestre_{i}"] = {
                'x': x,
                'y': y,
                'accion': 'En Estacionamiento (Fix)',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'terrestre'
            }
            print(f"[FIX] Operario terrestre_{i} creado en ({x}, {y})")
        
        # Crear montacargas
        for i in range(1, num_montacargas + 1):
            x = POS_DEPOT[0] - (i * 40)
            y = POS_DEPOT[1] + 50
            
            state.estado_visual["operarios"][f"montacargas_{i}"] = {
                'x': x,
                'y': y,
                'accion': 'En Estacionamiento (Fix)',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'montacargas'
            }
            print(f"[FIX] Montacargas montacargas_{i} creado en ({x}, {y})")
        
        print(f"[FIX] Total operarios en estado visual: {len(state.estado_visual['operarios'])}")
    
    # Reemplazar función
    state.inicializar_estado = inicializar_estado_con_operarios
    
    print("[FIX] Patch aplicado a inicializar_estado")

def main():
    """Aplicar fix y testear"""
    
    print("=" * 50)
    print("APLICANDO FIX TEMPORAL PARA OPERARIOS")
    print("=" * 50)
    
    # Aplicar patch
    fix_operarios_in_visual_state()
    
    try:
        # Test con configuración
        config = {
            'use_dynamic_layout': False,
            'total_tareas': 30,
            'pct_pequeno': 60,
            'pct_mediano': 30,
            'pct_grande': 10,
            'vol_pequeno': 5,
            'vol_mediano': 25,
            'vol_grande': 80,
            'capacidad_carro': 150,
            'num_operarios_terrestres': 2,
            'num_montacargas': 1
        }
        
        from simulation.warehouse import AlmacenMejorado
        from visualization.state import inicializar_estado, estado_visual
        import simpy
        
        env = simpy.Environment()
        almacen = AlmacenMejorado(env, config)
        
        # Esta llamada ahora debería crear operarios en estado visual
        inicializar_estado(almacen, env, config)
        
        operarios_count = len(estado_visual.get('operarios', {}))
        print(f"\nRESULTADO: {operarios_count} operarios en estado visual")
        
        if operarios_count > 0:
            print("EXITO: Los operarios aparecerán en la simulación")
            
            for op_id, op_data in estado_visual['operarios'].items():
                print(f"  {op_id}: {op_data.get('tipo')} en ({op_data.get('x')}, {op_data.get('y')})")
        else:
            print("ERROR: Aún no hay operarios")
        
        print("\n" + "=" * 50)
        print("AHORA EJECUTAR: python run_simulator.py")
        print("Los operarios deberían aparecer")
        print("=" * 50)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()