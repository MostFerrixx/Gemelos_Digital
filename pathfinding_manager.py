#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANAGER DE PATHFINDING - Sistema de transición segura
Permite cambiar entre sistema actual y mejorado con rollback automático
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

# Importar sistemas
try:
    from utils.pathfinding import calcular_ruta_realista as sistema_actual
    SISTEMA_ACTUAL_DISPONIBLE = True
except ImportError:
    SISTEMA_ACTUAL_DISPONIBLE = False
    sistema_actual = None

try:
    from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper
    SISTEMA_MEJORADO_DISPONIBLE = True
except ImportError:
    SISTEMA_MEJORADO_DISPONIBLE = False
    get_dynamic_pathfinding_wrapper = None

class PathfindingManager:
    """Manager que controla qué sistema de pathfinding usar"""
    
    def __init__(self):
        self.modo = "MEJORADO"  # "ACTUAL", "MEJORADO", "AB_TEST" - Cambio a MEJORADO para usar TMX
        self.sistema_mejorado = None
        self.estadisticas = {
            "llamadas_total": 0,
            "llamadas_actual": 0,
            "llamadas_mejorado": 0,
            "errores_actual": 0,
            "errores_mejorado": 0,
            "tiempo_actual": 0.0,
            "tiempo_mejorado": 0.0,
            "inicio_sesion": datetime.now().isoformat()
        }
        
        # Configuración A/B testing
        self.porcentaje_mejorado = 50  # % de llamadas que usan sistema mejorado
        self.auto_rollback = True
        self.umbral_error = 10  # % de errores antes de rollback automático
        
        print("PathfindingManager inicializado")
        print(f"Sistema actual disponible: {SISTEMA_ACTUAL_DISPONIBLE}")
        print(f"Sistema mejorado disponible: {SISTEMA_MEJORADO_DISPONIBLE}")
    
    def inicializar_sistema_mejorado(self):
        """Inicializar sistema TMX wrapper lazy loading"""
        if self.sistema_mejorado is None and SISTEMA_MEJORADO_DISPONIBLE:
            print("Inicializando sistema TMX wrapper...")
            self.sistema_mejorado = get_dynamic_pathfinding_wrapper()
            print("Sistema TMX wrapper listo")
        return self.sistema_mejorado is not None
    
    def establecer_modo(self, nuevo_modo):
        """Cambiar modo de operación"""
        modos_validos = ["ACTUAL", "MEJORADO", "AB_TEST"]
        if nuevo_modo not in modos_validos:
            raise ValueError(f"Modo debe ser uno de: {modos_validos}")
        
        modo_anterior = self.modo
        self.modo = nuevo_modo
        
        if nuevo_modo == "MEJORADO" or nuevo_modo == "AB_TEST":
            if not self.inicializar_sistema_mejorado():
                print("ERROR: No se pudo inicializar sistema mejorado, volviendo a ACTUAL")
                self.modo = "ACTUAL"
                return False
        
        print(f"Modo cambiado: {modo_anterior} -> {self.modo}")
        return True
    
    def _usar_sistema_mejorado_decision(self):
        """Decidir si usar sistema mejorado en modo AB_TEST"""
        if self.modo == "ACTUAL":
            return False
        elif self.modo == "MEJORADO":
            return True
        elif self.modo == "AB_TEST":
            # Usar estadísticas para decidir
            return (self.estadisticas["llamadas_total"] % 100) < self.porcentaje_mejorado
        
        return False
    
    def _calcular_ruta_actual(self, pos_actual, pos_destino, operario_id):
        """Calcular ruta con sistema actual"""
        if not SISTEMA_ACTUAL_DISPONIBLE:
            raise Exception("Sistema actual no disponible")
        
        start_time = time.time()
        try:
            resultado = sistema_actual(pos_actual, pos_destino, operario_id)
            elapsed = time.time() - start_time
            
            self.estadisticas["llamadas_actual"] += 1
            self.estadisticas["tiempo_actual"] += elapsed
            
            return resultado, elapsed, None
        except Exception as e:
            elapsed = time.time() - start_time
            self.estadisticas["errores_actual"] += 1
            self.estadisticas["tiempo_actual"] += elapsed
            return None, elapsed, str(e)
    
    def _calcular_ruta_mejorado(self, pos_actual, pos_destino, operario_id):
        """Calcular ruta con sistema TMX"""
        if not self.inicializar_sistema_mejorado():
            raise Exception("Sistema TMX no disponible")
        
        start_time = time.time()
        try:
            # Usar el wrapper TMX para calcular ruta
            ruta = self.sistema_mejorado.calculate_route(pos_actual, pos_destino)
            elapsed = time.time() - start_time
            
            self.estadisticas["llamadas_mejorado"] += 1
            self.estadisticas["tiempo_mejorado"] += elapsed
            
            return ruta, elapsed, None
        except Exception as e:
            elapsed = time.time() - start_time
            self.estadisticas["errores_mejorado"] += 1
            self.estadisticas["tiempo_mejorado"] += elapsed
            return None, elapsed, str(e)
    
    def calcular_ruta_con_fallback(self, pos_actual, pos_destino, operario_id=None):
        """Función principal con fallback automático"""
        self.estadisticas["llamadas_total"] += 1
        
        usar_mejorado = self._usar_sistema_mejorado_decision()
        
        # Verificar si necesitamos rollback automático
        if self._necesita_rollback_automatico():
            print("🚨 ROLLBACK AUTOMÁTICO ACTIVADO - Cambiando a sistema ACTUAL")
            self.modo = "ACTUAL"
            usar_mejorado = False
        
        if usar_mejorado:
            # Intentar sistema mejorado primero
            resultado, tiempo, error = self._calcular_ruta_mejorado(pos_actual, pos_destino, operario_id)
            
            if resultado is not None:
                print(f"[MEJORADO OK] Ruta: {len(resultado)} puntos ({tiempo*1000:.1f}ms)")
                return resultado
            else:
                print(f"[MEJORADO FAIL] {error} - Usando fallback")
                # Fallback al sistema actual
                if SISTEMA_ACTUAL_DISPONIBLE:
                    resultado, tiempo, error = self._calcular_ruta_actual(pos_actual, pos_destino, operario_id)
                    if resultado is not None:
                        print(f"[FALLBACK OK] Ruta: {len(resultado)} puntos ({tiempo*1000:.1f}ms)")
                        return resultado
        else:
            # Usar sistema actual
            if SISTEMA_ACTUAL_DISPONIBLE:
                resultado, tiempo, error = self._calcular_ruta_actual(pos_actual, pos_destino, operario_id)
                if resultado is not None:
                    print(f"[ACTUAL OK] Ruta: {len(resultado)} puntos ({tiempo*1000:.1f}ms)")
                    return resultado
                else:
                    print(f"[ACTUAL FAIL] {error}")
        
        # Si todo falla, ruta directa
        print(f"[EMERGENCY FALLBACK] Ruta directa")
        return [pos_actual, pos_destino]
    
    def _necesita_rollback_automatico(self):
        """Verificar si necesitamos rollback automático"""
        if not self.auto_rollback or self.modo == "ACTUAL":
            return False
        
        if self.estadisticas["llamadas_mejorado"] < 10:
            return False  # Muy pocas muestras
        
        tasa_error_mejorado = (self.estadisticas["errores_mejorado"] / 
                               max(1, self.estadisticas["llamadas_mejorado"])) * 100
        
        return tasa_error_mejorado > self.umbral_error
    
    def obtener_estadisticas(self):
        """Obtener estadísticas detalladas"""
        stats = self.estadisticas.copy()
        
        # Calcular métricas derivadas
        if stats["llamadas_actual"] > 0:
            stats["tiempo_promedio_actual"] = stats["tiempo_actual"] / stats["llamadas_actual"]
            stats["tasa_error_actual"] = (stats["errores_actual"] / stats["llamadas_actual"]) * 100
        else:
            stats["tiempo_promedio_actual"] = 0
            stats["tasa_error_actual"] = 0
        
        if stats["llamadas_mejorado"] > 0:
            stats["tiempo_promedio_mejorado"] = stats["tiempo_mejorado"] / stats["llamadas_mejorado"]
            stats["tasa_error_mejorado"] = (stats["errores_mejorado"] / stats["llamadas_mejorado"]) * 100
        else:
            stats["tiempo_promedio_mejorado"] = 0
            stats["tasa_error_mejorado"] = 0
        
        stats["modo_actual"] = self.modo
        stats["auto_rollback_activo"] = self.auto_rollback
        
        return stats
    
    def exportar_estadisticas(self, archivo=None):
        """Exportar estadísticas a archivo JSON"""
        if archivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo = f"pathfinding_stats_{timestamp}.json"
        
        stats = self.obtener_estadisticas()
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"Estadísticas exportadas: {archivo}")
        return archivo
    
    def mostrar_reporte(self):
        """Mostrar reporte de estadísticas"""
        stats = self.obtener_estadisticas()
        
        print(f"\n{'='*50}")
        print("REPORTE PATHFINDING MANAGER")
        print("="*50)
        print(f"Modo actual: {stats['modo_actual']}")
        print(f"Llamadas totales: {stats['llamadas_total']}")
        print(f"Auto-rollback: {'Activo' if stats['auto_rollback_activo'] else 'Inactivo'}")
        
        print(f"\nSISTEMA ACTUAL:")
        print(f"  Llamadas: {stats['llamadas_actual']}")
        print(f"  Errores: {stats['errores_actual']} ({stats['tasa_error_actual']:.1f}%)")
        print(f"  Tiempo promedio: {stats['tiempo_promedio_actual']*1000:.1f}ms")
        
        print(f"\nSISTEMA MEJORADO:")
        print(f"  Llamadas: {stats['llamadas_mejorado']}")
        print(f"  Errores: {stats['errores_mejorado']} ({stats['tasa_error_mejorado']:.1f}%)")
        print(f"  Tiempo promedio: {stats['tiempo_promedio_mejorado']*1000:.1f}ms")
        
        if stats['llamadas_actual'] > 0 and stats['llamadas_mejorado'] > 0:
            mejora_tiempo = ((stats['tiempo_promedio_actual'] - stats['tiempo_promedio_mejorado']) / 
                            stats['tiempo_promedio_actual']) * 100
            print(f"\nMEJORA RENDIMIENTO: {mejora_tiempo:+.1f}%")

# Instancia global del manager
_pathfinding_manager = None

def get_pathfinding_manager():
    """Obtener instancia global del manager"""
    global _pathfinding_manager
    if _pathfinding_manager is None:
        _pathfinding_manager = PathfindingManager()
    return _pathfinding_manager

def calcular_ruta_managed(pos_actual, pos_destino, operario_id=None):
    """Función pública que usa el manager"""
    manager = get_pathfinding_manager()
    return manager.calcular_ruta_con_fallback(pos_actual, pos_destino, operario_id)

def cambiar_modo_pathfinding(modo):
    """Cambiar modo de pathfinding"""
    manager = get_pathfinding_manager()
    return manager.establecer_modo(modo)

def obtener_estadisticas_pathfinding():
    """Obtener estadísticas del pathfinding"""
    manager = get_pathfinding_manager()
    return manager.obtener_estadisticas()

def mostrar_reporte_pathfinding():
    """Mostrar reporte de pathfinding"""
    manager = get_pathfinding_manager()
    manager.mostrar_reporte()

if __name__ == "__main__":
    print("="*60)
    print("TESTING PATHFINDING MANAGER")
    print("="*60)
    
    manager = PathfindingManager()
    
    # Casos de prueba
    test_cases = [
        ((1750, 550), (100, 50), "Depot a Inbound"),
        ((100, 50), (300, 300), "Inbound a picking"),
        ((300, 300), (800, 400), "Entre ubicaciones"),
    ]
    
    # Test en modo AB_TEST
    print("\nTesting modo AB_TEST...")
    manager.establecer_modo("AB_TEST")
    
    for i, (start, end, nombre) in enumerate(test_cases):
        print(f"\nTest {i+1}: {nombre}")
        resultado = manager.calcular_ruta_con_fallback(start, end)
        print(f"Resultado: {len(resultado)} puntos")
    
    # Mostrar estadísticas
    manager.mostrar_reporte()
    
    print("\nManager funcionando correctamente!")