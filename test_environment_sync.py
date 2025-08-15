#!/usr/bin/env python3
"""
Test para verificar sincronización del entorno y cache
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA DE SINCRONIZACIÓN DEL ENTORNO ===")

try:
    # Importar simulador para activar verificaciones de entorno
    from run_simulator import SimuladorAlmacen
    
    print("\n1. CREANDO SIMULADOR CON PRUEBA DE HUMO...")
    
    # Crear instancia del simulador
    simulador = SimuladorAlmacen()
    
    # Configuración mínima
    configuracion_test = {
        'num_operarios_terrestres': 1,
        'num_montacargas': 1,
        'tareas_zona_a': 1,
        'tareas_zona_b': 1
    }
    
    simulador.configuracion = configuracion_test
    
    print("\n2. CREANDO SIMULACIÓN (debe mostrar mensaje de código nuevo)...")
    
    if simulador.crear_simulacion():
        print("   [OK] Simulación creada - código nuevo ejecutado")
        
        # Verificar que la matriz de colisión es la correcta
        walkable_count = (simulador.layout_manager.collision_matrix == 0).sum()
        blocked_count = (simulador.layout_manager.collision_matrix == 1).sum()
        
        print(f"   [MATRIZ] {walkable_count} caminables, {blocked_count} bloqueadas")
        
        if blocked_count > 0:
            print("   [SUCCESS] Matriz de colisión corregida funcionando")
        else:
            print("   [ERROR] Matriz aún incorrecta - posible cache obsoleto")
        
        # Verificar depot
        if simulador.layout_manager.depot_points:
            depot = simulador.layout_manager.depot_points[0]
            print(f"   [DEPOT] Encontrado en: {depot}")
        else:
            print("   [ERROR] Depot no encontrado")
        
        simulador.limpiar_recursos()
        
    else:
        print("   [ERROR] No se pudo crear la simulación")
    
    print("\n[CONCLUSIÓN]")
    print("Si viste el mensaje '*** EJECUTANDO CÓDIGO NUEVO ***', el entorno está sincronizado")
    print("Si NO viste ese mensaje, hay cache obsoleto o imports incorrectos")
    
except Exception as e:
    print(f"[ERROR] Error en prueba: {e}")
    import traceback
    traceback.print_exc()