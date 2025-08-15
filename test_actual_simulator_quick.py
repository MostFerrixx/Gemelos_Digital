#!/usr/bin/env python3
"""
Test rápido del simulador actual para verificar TMX unification funciona
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA RÁPIDA DEL SIMULADOR ACTUAL ===")

try:
    # Importar simulador
    from run_simulator import SimuladorAlmacen
    
    # Crear instancia del simulador
    simulador = SimuladorAlmacen()
    
    # Configuración de prueba
    configuracion_test = {
        'num_operarios_terrestres': 2,
        'num_montacargas': 1,
        'tareas_zona_a': 5,
        'tareas_zona_b': 5
    }
    
    simulador.configuracion = configuracion_test
    
    print("1. Creando simulación con TMX obligatorio...")
    
    # Intentar crear simulación (debe funcionar con TMX)
    if simulador.crear_simulacion():
        print("   [OK] Simulación creada exitosamente con TMX")
        
        # Verificar que LayoutManager está cargado
        if simulador.layout_manager:
            print(f"   [OK] LayoutManager cargado: {simulador.layout_manager.grid_width}x{simulador.layout_manager.grid_height}")
        else:
            print("   [ERROR] LayoutManager no cargado")
        
        # Verificar que Pathfinder está cargado
        if simulador.pathfinder:
            print("   [OK] Pathfinder inicializado")
        else:
            print("   [ERROR] Pathfinder no inicializado")
        
        # Verificar inicialización de pygame con dimensiones TMX
        print("2. Verificando inicialización pygame con dimensiones TMX...")
        
        try:
            simulador.inicializar_pygame()
            
            # Verificar dimensiones de la ventana
            map_width = simulador.layout_manager.grid_width * simulador.layout_manager.tile_width
            map_height = simulador.layout_manager.grid_height * simulador.layout_manager.tile_height
            
            actual_width, actual_height = simulador.pantalla.get_size()
            
            if actual_width == map_width and actual_height == map_height:
                print(f"   [OK] Ventana pygame con dimensiones TMX exactas: {actual_width}x{actual_height}")
            else:
                print(f"   [ERROR] Ventana dimensiones incorrectas: esperado {map_width}x{map_height}, obtenido {actual_width}x{actual_height}")
            
            # Verificar que estado visual tiene operarios con coordenadas píxeles
            from visualization.state import estado_visual
            
            print("3. Verificando operarios en estado visual...")
            
            total_operarios = len(estado_visual.get("operarios", {}))
            if total_operarios > 0:
                print(f"   [OK] {total_operarios} operarios inicializados")
                
                # Verificar primer operario
                primer_op_id = list(estado_visual["operarios"].keys())[0]
                primer_op = estado_visual["operarios"][primer_op_id]
                
                if 'x' in primer_op and 'y' in primer_op:
                    print(f"   [OK] Operario {primer_op_id} tiene coordenadas píxeles: ({primer_op['x']}, {primer_op['y']})")
                else:
                    print(f"   [ERROR] Operario {primer_op_id} no tiene coordenadas píxeles")
                
                if 'grid_x' in primer_op or 'grid_y' in primer_op:
                    print(f"   [WARNING] Operario {primer_op_id} aún tiene coordenadas grilla")
                else:
                    print(f"   [OK] Operario {primer_op_id} sin coordenadas grilla duplicadas")
            else:
                print("   [ERROR] No hay operarios inicializados")
            
            print("\n[SUCCESS] PRUEBA RÁPIDA COMPLETADA!")
            print("El simulador TMX unificado funciona correctamente.")
            
        except Exception as e:
            print(f"   [ERROR] Error en inicialización pygame: {e}")
        finally:
            # Limpiar recursos
            simulador.limpiar_recursos()
            
    else:
        print("   [ERROR] No se pudo crear la simulación")
    
except Exception as e:
    print(f"[ERROR] Error en prueba: {e}")
    import traceback
    traceback.print_exc()