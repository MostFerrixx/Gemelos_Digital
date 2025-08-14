#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIVERSAL BOUNDS CHECKER - Validación exhaustiva de coordenadas
Garantiza que NINGÚN operario se salga del layout TMX
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from tmx_coordinate_system import tmx_coords

class UniversalBoundsChecker:
    """Checker universal que valida TODAS las coordenadas del sistema"""
    
    def __init__(self):
        self.violations_count = 0
        self.last_violations = []
        self.debug_enabled = True
        
        print("[BOUNDS_CHECKER] Universal Bounds Checker inicializado")
    
    def validate_position(self, x, y, context="Unknown", operario_id=None):
        """Validar posición con contexto completo"""
        
        # Verificar si está dentro de bounds
        is_valid = tmx_coords.is_point_valid(x, y)
        
        if not is_valid:
            self.violations_count += 1
            violation = {
                'position': (x, y),
                'context': context,
                'operario_id': operario_id,
                'bounds': tmx_coords.get_bounds()
            }
            self.last_violations.append(violation)
            
            if self.debug_enabled:
                print(f"[BOUNDS_VIOLATION] {context}")
                print(f"  Operario: {operario_id}")
                print(f"  Posición: ({x}, {y})")
                print(f"  Bounds válidos: {tmx_coords.get_bounds()}")
                
                # Si TMX está activo, mostrar info adicional
                if tmx_coords.is_tmx_active():
                    grid_pos = tmx_coords.pixel_to_grid(x, y)
                    print(f"  Grid equivalente: {grid_pos}")
                    if grid_pos:
                        walkable = tmx_coords.is_grid_cell_walkable(grid_pos[0], grid_pos[1])
                        print(f"  Celda navegable: {walkable}")
            
            return False
        
        return True
    
    def validate_and_clamp(self, x, y, context="Unknown", operario_id=None):
        """Validar posición y corregir si es necesario"""
        
        original_pos = (x, y)
        clamped_pos = tmx_coords.clamp_point(x, y)
        
        if original_pos != clamped_pos:
            if self.debug_enabled:
                print(f"[BOUNDS_CLAMP] {context}")
                print(f"  Operario: {operario_id}")
                print(f"  Posición original: {original_pos}")
                print(f"  Posición corregida: {clamped_pos}")
            
            self.violations_count += 1
        
        return clamped_pos
    
    def validate_route(self, route, context="Route", operario_id=None):
        """Validar una ruta completa"""
        
        if not route:
            return True
        
        invalid_points = []
        
        for i, (x, y) in enumerate(route):
            if not tmx_coords.is_point_valid(x, y):
                invalid_points.append((i, x, y))
        
        if invalid_points:
            if self.debug_enabled:
                print(f"[BOUNDS_ROUTE_VIOLATION] {context}")
                print(f"  Operario: {operario_id}")
                print(f"  Puntos inválidos: {len(invalid_points)}/{len(route)}")
                for i, x, y in invalid_points[:3]:  # Solo mostrar primeros 3
                    print(f"    Punto {i}: ({x}, {y})")
                if len(invalid_points) > 3:
                    print(f"    ... y {len(invalid_points) - 3} más")
            
            self.violations_count += len(invalid_points)
            return False
        
        return True
    
    def validate_and_fix_route(self, route, context="Route", operario_id=None):
        """Validar ruta y corregir puntos problemáticos"""
        
        if not route:
            return route
        
        fixed_route = []
        fixes_made = 0
        
        for i, (x, y) in enumerate(route):
            original_pos = (x, y)
            fixed_pos = tmx_coords.clamp_point(x, y)
            
            if original_pos != fixed_pos:
                fixes_made += 1
                if self.debug_enabled and fixes_made <= 3:  # Solo mostrar primeros 3 fixes
                    print(f"[BOUNDS_ROUTE_FIX] {context} punto {i}: {original_pos} -> {fixed_pos}")
            
            fixed_route.append(fixed_pos)
        
        if fixes_made > 0:
            if self.debug_enabled:
                print(f"[BOUNDS_ROUTE_FIX] {context} - Operario {operario_id}: {fixes_made} puntos corregidos")
            self.violations_count += fixes_made
        
        return fixed_route
    
    def check_operator_movement(self, operario_id, current_pos, target_pos, context="Movement"):
        """Validación específica para movimiento de operarios"""
        
        current_valid = self.validate_position(current_pos[0], current_pos[1], 
                                             f"{context} - Posición actual", operario_id)
        target_valid = self.validate_position(target_pos[0], target_pos[1], 
                                            f"{context} - Posición objetivo", operario_id)
        
        # Verificar navegabilidad si TMX está activo
        if tmx_coords.is_tmx_active():
            current_walkable = tmx_coords.is_pixel_walkable(current_pos[0], current_pos[1])
            target_walkable = tmx_coords.is_pixel_walkable(target_pos[0], target_pos[1])
            
            if not current_walkable or not target_walkable:
                if self.debug_enabled:
                    print(f"[BOUNDS_WALKABLE] {context} - Operario {operario_id}")
                    print(f"  Actual navegable: {current_walkable}")
                    print(f"  Objetivo navegable: {target_walkable}")
                
                return False
        
        return current_valid and target_valid
    
    def get_safe_alternative_position(self, x, y, operario_id=None):
        """Obtener posición alternativa segura cerca de una posición problemática"""
        
        # Intentar clamp primero
        clamped = tmx_coords.clamp_point(x, y)
        if tmx_coords.is_point_valid(clamped[0], clamped[1]):
            # Verificar navegabilidad
            if not tmx_coords.is_tmx_active() or tmx_coords.is_pixel_walkable(clamped[0], clamped[1]):
                return clamped
        
        # Si clamp no funciona, buscar posición inicial segura
        safe_start = tmx_coords.get_safe_starting_position(operario_id)
        
        if self.debug_enabled:
            print(f"[BOUNDS_SAFE_ALT] Operario {operario_id}: ({x},{y}) -> {safe_start}")
        
        return safe_start
    
    def install_global_hooks(self):
        """Instalar hooks globales para interceptar movimientos"""
        
        print("[BOUNDS_CHECKER] Hooks de validación disponibles")
        print("[BOUNDS_CHECKER] Nota: mover_por_ruta_mejorado.py ya incluye validación integrada")
        
        # NO parchear - las validaciones ya están integradas en mover_por_ruta_mejorado.py
        # self._patch_movement_functions()
    
    def _patch_movement_functions(self):
        """Parchear funciones de movimiento para validación automática"""
        
        try:
            # Parchear mover_por_ruta_realista si existe
            from mover_por_ruta_mejorado import mover_por_ruta_realista
            original_mover = mover_por_ruta_realista
            
            def validated_mover_por_ruta_realista(env, operario_id, origen, destino, accion_texto):
                # Validar entrada
                origen = self.validate_and_clamp(origen[0], origen[1], 
                                               "mover_por_ruta_realista - origen", operario_id)
                destino = self.validate_and_clamp(destino[0], destino[1], 
                                                "mover_por_ruta_realista - destino", operario_id)
                
                # Llamar función original
                try:
                    yield from original_mover(env, operario_id, origen, destino, accion_texto)
                except Exception as e:
                    print(f"[BOUNDS_HOOK] Error en mover_por_ruta_realista: {e}")
                    # Fallback: movimiento directo
                    from visualization.state import estado_visual
                    from config.settings import VELOCIDAD_MOVIMIENTO
                    
                    distancia = ((destino[0] - origen[0]) ** 2 + (destino[1] - origen[1]) ** 2) ** 0.5
                    tiempo = max(0.1, distancia / VELOCIDAD_MOVIMIENTO)
                    
                    if operario_id in estado_visual["operarios"]:
                        # Validar destino final antes de actualizar estado visual
                        destino_final = self.validate_and_clamp(destino[0], destino[1], 
                                                              "fallback destino", operario_id)
                        estado_visual["operarios"][operario_id].update({
                            'accion': f'{accion_texto} (bounds fallback)',
                            'x': destino_final[0],
                            'y': destino_final[1]
                        })
                    
                    yield env.timeout(tiempo)
            
            # Reemplazar función
            import mover_por_ruta_mejorado
            mover_por_ruta_mejorado.mover_por_ruta_realista = validated_mover_por_ruta_realista
            
            print("[BOUNDS_CHECKER] Hook instalado en mover_por_ruta_realista")
            
        except ImportError:
            print("[BOUNDS_CHECKER] Warning: No se pudo instalar hook en mover_por_ruta_realista")
    
    def get_stats(self):
        """Obtener estadísticas de violaciones"""
        return {
            'total_violations': self.violations_count,
            'recent_violations': len(self.last_violations),
            'tmx_active': tmx_coords.is_tmx_active(),
            'current_bounds': tmx_coords.get_bounds()
        }
    
    def reset_stats(self):
        """Resetear estadísticas"""
        self.violations_count = 0
        self.last_violations = []
    
    def enable_debug(self, enabled=True):
        """Habilitar/deshabilitar debug output"""
        self.debug_enabled = enabled

# Instancia global del checker
bounds_checker = UniversalBoundsChecker()

# Funciones de utilidad global
def validate_operator_position(x, y, context="Position", operario_id=None):
    """Validar posición de operario"""
    return bounds_checker.validate_position(x, y, context, operario_id)

def safe_clamp_position(x, y, context="Clamp", operario_id=None):
    """Clamp seguro de posición"""
    return bounds_checker.validate_and_clamp(x, y, context, operario_id)

def validate_movement(operario_id, current_pos, target_pos):
    """Validar movimiento de operario"""
    return bounds_checker.check_operator_movement(operario_id, current_pos, target_pos)

def install_bounds_checking():
    """Instalar sistema de bounds checking global"""
    bounds_checker.install_global_hooks()
    return bounds_checker