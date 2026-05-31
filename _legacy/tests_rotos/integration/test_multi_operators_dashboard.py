#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script para probar Dashboard World-Class con múltiples operarios.
Este script genera una simulación con 8 operarios (5 terrestres + 3 montacargas)
para probar la funcionalidad de scroll en la lista de operarios.
"""

import os
import sys
import json
import shutil
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("=" * 60)
    print("TEST MULTI-OPERATORS - DASHBOARD WORLD-CLASS")
    print("=" * 60)
    
    # 1. Backup config original
    if os.path.exists('config.json'):
        shutil.copy('config.json', 'config.json.backup')
        print("[TEST] Config original respaldado")
    
    # 2. Usar config de múltiples operarios
    shutil.copy('config_test_multi_operators.json', 'config.json')
    print("[TEST] Config de múltiples operarios aplicado")
    
    try:
        # 3. Ejecutar simulación
        print("\n[TEST] Ejecutando simulación con múltiples operarios...")
        print("Operarios: 5 terrestres + 3 montacargas = 8 total")
        print("Órdenes: 20")
        
        # Importar y ejecutar simulación
        from engines.simulation_engine import SimulationEngine
        
        engine = SimulationEngine()
        result = engine.run(headless=True)
        
        if result:
            print("\n[TEST] Simulación completada exitosamente")
            
            # 4. Buscar archivo JSONL generado
            output_dir = None
            for item in os.listdir('output'):
                if item.startswith('simulation_'):
                    output_dir = os.path.join('output', item)
                    break
            
            if output_dir:
                jsonl_files = [f for f in os.listdir(output_dir) if f.endswith('.jsonl')]
                if jsonl_files:
                    jsonl_file = os.path.join(output_dir, jsonl_files[0])
                    print(f"[TEST] Archivo JSONL encontrado: {jsonl_file}")
                    
                    # 5. Ejecutar replay viewer
                    print("\n[TEST] Ejecutando replay viewer para probar scroll...")
                    print("Presiona 'O' para activar el dashboard")
                    print("Usa la rueda del mouse sobre la lista de operarios para probar scroll")
                    
                    import subprocess
                    subprocess.run([
                        sys.executable, 
                        'entry_points/run_replay_viewer.py', 
                        jsonl_file
                    ])
                else:
                    print("[TEST ERROR] No se encontró archivo JSONL")
            else:
                print("[TEST ERROR] No se encontró directorio de output")
        else:
            print("[TEST ERROR] Simulación falló")
            
    except Exception as e:
        print(f"[TEST ERROR] Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 6. Restaurar config original
        if os.path.exists('config.json.backup'):
            shutil.copy('config.json.backup', 'config.json')
            os.remove('config.json.backup')
            print("\n[TEST] Config original restaurado")
        
        # Limpiar archivo temporal
        if os.path.exists('config_test_multi_operators.json'):
            os.remove('config_test_multi_operators.json')
            print("[TEST] Archivo temporal limpiado")

if __name__ == "__main__":
    main()
