#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MONITOR EN TIEMPO REAL - Detectar cuándo operarios se salen del layout
"""

import time
import threading
from typing import Dict, List, Tuple

class RealtimeBoundsMonitor:
    """Monitor que detecta violaciones de bounds en tiempo real"""
    
    def __init__(self):
        self.monitoring = False
        self.violations_log = []
        self.last_positions = {}
        self.bounds = None
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Iniciar monitoreo en tiempo real"""
        
        try:
            from tmx_coordinate_system import tmx_coords
            
            if not tmx_coords.is_tmx_active():
                print("[MONITOR] ERROR: Sistema TMX no activo")
                return False
            
            self.bounds = tmx_coords.get_bounds()
            print(f"[MONITOR] Iniciando monitoreo con bounds: {self.bounds['max_x']}x{self.bounds['max_y']}")
            
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[MONITOR] Error iniciando: {e}")
            return False
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Loop principal de monitoreo"""
        
        print("[MONITOR] Iniciando loop de monitoreo...")
        
        while self.monitoring:
            try:
                # Obtener posiciones actuales de operarios
                from visualization.state import estado_visual
                
                if "operarios" in estado_visual:
                    for operario_id, operario_data in estado_visual["operarios"].items():
                        x = operario_data.get('x', 0)
                        y = operario_data.get('y', 0)
                        accion = operario_data.get('accion', 'Unknown')
                        
                        # Verificar bounds
                        self._check_operator_bounds(operario_id, x, y, accion)
                
                time.sleep(0.1)  # Check cada 100ms
                
            except Exception as e:
                print(f"[MONITOR] Error en loop: {e}")
                time.sleep(0.5)
    
    def _check_operator_bounds(self, operario_id: str, x: float, y: float, accion: str):
        """Verificar si un operario está dentro de bounds"""
        
        if not self.bounds:
            return
        
        # Verificar si está fuera de bounds
        out_of_bounds = (
            x < self.bounds['min_x'] or x > self.bounds['max_x'] or
            y < self.bounds['min_y'] or y > self.bounds['max_y']
        )
        
        if out_of_bounds:
            # Detectar tipo de violación
            violation_type = []
            if x < self.bounds['min_x']:
                violation_type.append("LEFT")
            if x > self.bounds['max_x']:
                violation_type.append("RIGHT")  
            if y < self.bounds['min_y']:
                violation_type.append("TOP")
            if y > self.bounds['max_y']:
                violation_type.append("BOTTOM")
            
            violation = {
                'timestamp': time.time(),
                'operario_id': operario_id,
                'position': (x, y),
                'accion': accion,
                'violation_type': '+'.join(violation_type),
                'bounds': self.bounds
            }
            
            # Solo reportar si es una nueva violación
            last_pos = self.last_positions.get(operario_id)
            if not last_pos or (abs(last_pos[0] - x) > 5 or abs(last_pos[1] - y) > 5):
                self.violations_log.append(violation)
                self._report_violation(violation)
        
        # Actualizar última posición conocida
        self.last_positions[operario_id] = (x, y)
    
    def _report_violation(self, violation: Dict):
        """Reportar violación detectada"""
        
        print("=" * 80)
        print(f"[BOUNDS_VIOLATION] OPERARIO FUERA DEL LAYOUT DETECTADO")
        print("=" * 80)
        print(f"Operario ID: {violation['operario_id']}")
        print(f"Posición: ({violation['position'][0]:.1f}, {violation['position'][1]:.1f})")
        print(f"Acción: {violation['accion']}")
        print(f"Tipo violación: {violation['violation_type']}")
        print(f"Bounds válidos: 0-{violation['bounds']['max_x']} x 0-{violation['bounds']['max_y']}")
        
        # Calcular qué tan fuera está
        x, y = violation['position']
        bounds = violation['bounds']
        
        distance_out = 0
        if x < bounds['min_x']:
            distance_out = bounds['min_x'] - x
        elif x > bounds['max_x']:
            distance_out = x - bounds['max_x']
        
        if y < bounds['min_y']:
            distance_out = max(distance_out, bounds['min_y'] - y)
        elif y > bounds['max_y']:
            distance_out = max(distance_out, y - bounds['max_y'])
        
        print(f"Distancia fuera del layout: {distance_out:.1f} pixels")
        print("=" * 80)
        
        # Intentar corregir en tiempo real
        self._attempt_realtime_correction(violation)
    
    def _attempt_realtime_correction(self, violation: Dict):
        """Intentar corregir la posición en tiempo real"""
        
        try:
            from tmx_coordinate_system import tmx_coords
            from visualization.state import estado_visual
            
            operario_id = violation['operario_id']
            x, y = violation['position']
            
            # Clamp position
            corrected_pos = tmx_coords.clamp_point(x, y)
            
            # Intentar actualizar estado visual
            if operario_id in estado_visual["operarios"]:
                old_pos = (
                    estado_visual["operarios"][operario_id]['x'],
                    estado_visual["operarios"][operario_id]['y']
                )
                
                estado_visual["operarios"][operario_id]['x'] = corrected_pos[0]
                estado_visual["operarios"][operario_id]['y'] = corrected_pos[1]
                
                print(f"[MONITOR_CORRECTION] Operario {operario_id} corregido: {old_pos} -> {corrected_pos}")
            
        except Exception as e:
            print(f"[MONITOR_CORRECTION] Error: {e}")
    
    def get_violations_summary(self) -> Dict:
        """Obtener resumen de violaciones detectadas"""
        
        if not self.violations_log:
            return {"total_violations": 0, "message": "No violations detected"}
        
        # Agrupar por operario
        by_operator = {}
        violation_types = {}
        
        for violation in self.violations_log:
            op_id = violation['operario_id']
            v_type = violation['violation_type']
            
            if op_id not in by_operator:
                by_operator[op_id] = 0
            by_operator[op_id] += 1
            
            if v_type not in violation_types:
                violation_types[v_type] = 0
            violation_types[v_type] += 1
        
        return {
            "total_violations": len(self.violations_log),
            "by_operator": by_operator,
            "violation_types": violation_types,
            "first_violation": self.violations_log[0] if self.violations_log else None,
            "last_violation": self.violations_log[-1] if self.violations_log else None
        }

# Instancia global
bounds_monitor = RealtimeBoundsMonitor()

def start_realtime_monitoring():
    """Iniciar monitoreo en tiempo real"""
    return bounds_monitor.start_monitoring()

def stop_realtime_monitoring():
    """Detener monitoreo"""
    bounds_monitor.stop_monitoring()

def get_violations_report():
    """Obtener reporte de violaciones"""
    return bounds_monitor.get_violations_summary()

if __name__ == "__main__":
    print("Monitor de bounds en tiempo real")
    print("Este script debe ejecutarse mientras el simulador está corriendo")
    
    # Activar TMX primero
    try:
        import force_tmx_activation
        print("TMX activado para monitoreo")
    except ImportError:
        print("Error: No se pudo activar TMX")
    
    # Iniciar monitoreo
    if start_realtime_monitoring():
        print("Monitoreo iniciado. Presiona Ctrl+C para detener...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDeteniendo monitoreo...")
            stop_realtime_monitoring()
            
            # Mostrar reporte
            report = get_violations_report()
            print("\nREPORTE DE VIOLACIONES:")
            print(f"Total: {report['total_violations']}")
            if report['total_violations'] > 0:
                print(f"Por operario: {report['by_operator']}")
                print(f"Tipos: {report['violation_types']}")
    else:
        print("No se pudo iniciar el monitoreo")