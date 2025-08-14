#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REEMPLAZO PATHFINDING OPERATORS.PY
Drop-in replacement para mover_por_ruta_realista
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# IMPORTAR SISTEMA TMX UNIFICADO PARA BOUNDS CHECKING
from tmx_coordinate_system import tmx_coords
from universal_bounds_checker import bounds_checker

# Importar sistema mejorado
try:
    from pathfinding_manager import get_pathfinding_manager
    SISTEMA_MEJORADO_DISPONIBLE = True
except ImportError:
    SISTEMA_MEJORADO_DISPONIBLE = False
    print("ADVERTENCIA: Sistema mejorado no disponible, usando fallback")

# Importar sistema original como fallback
try:
    from utils.pathfinding import mover_por_ruta_realista as mover_original
    SISTEMA_ORIGINAL_DISPONIBLE = True
except ImportError:
    SISTEMA_ORIGINAL_DISPONIBLE = False
    mover_original = None

def mover_por_ruta_realista_nueva(env, operario_id, origen, destino, accion_texto):
    """
    FUNCIÓN DE REEMPLAZO para mover_por_ruta_realista
    Usa sistema mejorado con fallback al original
    """
    
    if SISTEMA_MEJORADO_DISPONIBLE:
        try:
            # Usar sistema mejorado
            manager = get_pathfinding_manager()
            
            # Importar dependencias necesarias
            from visualization.state import estado_visual
            from utils.strict_lane_system import sistema_carriles_estricto
            from config.settings import VELOCIDAD_MOVIMIENTO
            
            print(f"[PATHFINDING MEJORADO] Operario {operario_id}: {origen} -> {destino}")
            
            # VALIDAR COORDENADAS DE ENTRADA
            origen = bounds_checker.validate_and_clamp(origen[0], origen[1], 
                                                     f"mover_por_ruta origen", operario_id)
            destino = bounds_checker.validate_and_clamp(destino[0], destino[1], 
                                                      f"mover_por_ruta destino", operario_id)
            
            # Calcular ruta mejorada
            ruta_espacial = manager.calcular_ruta_con_fallback(origen, destino, operario_id)
            
            if not ruta_espacial or len(ruta_espacial) < 2:
                ruta_espacial = [origen, destino]
            
            # VALIDAR RUTA COMPLETA
            ruta_espacial = bounds_checker.validate_and_fix_route(ruta_espacial, 
                                                               f"mover_por_ruta ruta", operario_id)
            
            print(f"[RUTA MEJORADA] {len(ruta_espacial)} puntos (validados)")
            
            # Ejecutar movimiento
            pos_x, pos_y = origen
            
            for i, punto_destino in enumerate(ruta_espacial[1:], 1):
                x_destino, y_destino = punto_destino
                
                # VALIDAR CADA PUNTO DE LA RUTA EN TIEMPO REAL
                x_destino, y_destino = bounds_checker.validate_and_clamp(x_destino, y_destino, 
                                                                       f"mover_por_ruta punto {i}", operario_id)
                
                distancia = ((x_destino - pos_x) ** 2 + (y_destino - pos_y) ** 2) ** 0.5
                tiempo_movimiento = distancia / VELOCIDAD_MOVIMIENTO
                
                if tiempo_movimiento > 0:
                    if operario_id in estado_visual["operarios"]:
                        # VALIDAR COORDENADAS ANTES DE ACTUALIZAR ESTADO VISUAL
                        final_x, final_y = bounds_checker.validate_and_clamp(x_destino, y_destino, 
                                                                           f"estado_visual update", operario_id)
                        
                        estado_visual["operarios"][operario_id].update({
                            'accion': f'{accion_texto} (mejorado {i}/{len(ruta_espacial)-1})',
                            'x': final_x,
                            'y': final_y,
                            'direccion_x': 1 if final_x > pos_x else -1 if final_x < pos_x else 0,
                            'direccion_y': 1 if final_y > pos_y else -1 if final_y < pos_y else 0
                        })
                    
                    sistema_carriles_estricto.liberar_punto((pos_x, pos_y), operario_id)
                    sistema_carriles_estricto.ocupar_punto((x_destino, y_destino), operario_id)
                    
                    yield env.timeout(tiempo_movimiento)
                    pos_x, pos_y = x_destino, y_destino
            
            return  # Éxito con sistema mejorado
            
        except Exception as e:
            print(f"[ERROR SISTEMA MEJORADO] {e} - Usando fallback")
    
    # Fallback al sistema original
    if SISTEMA_ORIGINAL_DISPONIBLE:
        print(f"[FALLBACK ORIGINAL] Operario {operario_id}")
        yield from mover_original(env, operario_id, origen, destino, accion_texto)
    else:
        print(f"[ERROR CRÍTICO] Ningún sistema disponible")
        # Movimiento directo de emergencia
        from visualization.state import estado_visual
        from config.settings import VELOCIDAD_MOVIMIENTO
        
        # VALIDAR COORDENADAS EN MODO EMERGENCIA
        origen = bounds_checker.validate_and_clamp(origen[0], origen[1], 
                                                 f"emergencia origen", operario_id)
        destino = bounds_checker.validate_and_clamp(destino[0], destino[1], 
                                                  f"emergencia destino", operario_id)
        
        distancia = ((destino[0] - origen[0]) ** 2 + (destino[1] - origen[1]) ** 2) ** 0.5
        tiempo = distancia / VELOCIDAD_MOVIMIENTO
        
        if operario_id in estado_visual["operarios"]:
            estado_visual["operarios"][operario_id].update({
                'accion': f'{accion_texto} (emergencia)',
                'x': destino[0],
                'y': destino[1]
            })
        
        yield env.timeout(tiempo)

# Alias para compatibilidad
mover_por_ruta_realista = mover_por_ruta_realista_nueva
