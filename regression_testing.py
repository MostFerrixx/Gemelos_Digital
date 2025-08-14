#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTING DE REGRESIÓN COMPLETO - Verificar que todo funciona después de cambios
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

class RegressionTester:
    """Suite completa de testing de regresión"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test(self, test_name, success, details="", duration=0):
        """Registrar resultado de test"""
        
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        self.total_tests += 1
        if success:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
    
    def test_imports(self):
        """Test 1: Verificar que todas las importaciones funcionan"""
        
        print("\nTest 1: Verificando importaciones...")
        test_start = time.time()
        
        try:
            # Test importaciones críticas
            from config.settings import ANCHO_PANTALLA, ALTO_PANTALLA
            from utils.ubicaciones_picking import ubicaciones_picking
            
            # Test importaciones del sistema mejorado
            from enhanced_calibrator import EnhancedCalibrator
            from pathfinding_manager import get_pathfinding_manager
            
            # Test importaciones del simulador
            from simulation.warehouse import AlmacenMejorado
            from simulation.operators import proceso_operario_traspaleta
            
            duration = time.time() - test_start
            self.log_test("imports", True, "Todas las importaciones exitosas", duration)
            print(f"   PASS - Importaciones OK ({duration*1000:.1f}ms)")
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("imports", False, f"Error: {e}", duration)
            print(f"   FAIL - Error en importaciones: {e}")
            return False
    
    def test_enhanced_calibrator(self):
        """Test 2: Verificar que el calibrador mejorado funciona"""
        
        print("\nTest 2: Verificando calibrador mejorado...")
        test_start = time.time()
        
        try:
            from enhanced_calibrator import EnhancedCalibrator
            
            # Crear calibrador
            calibrator = EnhancedCalibrator()
            
            # Test casos básicos
            test_routes = [
                ((1750, 550), (100, 50)),    # Depot a Inbound
                ((100, 50), (300, 300)),     # Inbound a picking
                ((300, 300), (800, 400)),    # Entre ubicaciones
            ]
            
            successful_routes = 0
            
            for start, end in test_routes:
                route, runs = calibrator.calculate_route_enhanced(start, end)
                if route and len(route) >= 2:
                    successful_routes += 1
            
            success_rate = successful_routes / len(test_routes) * 100
            
            if success_rate >= 80:
                duration = time.time() - test_start
                self.log_test("enhanced_calibrator", True, f"Success rate: {success_rate:.1f}%", duration)
                print(f"   PASS - Calibrador OK ({success_rate:.1f}% éxito, {duration*1000:.1f}ms)")
                return True
            else:
                duration = time.time() - test_start
                self.log_test("enhanced_calibrator", False, f"Low success rate: {success_rate:.1f}%", duration)
                print(f"   FAIL - Baja tasa de éxito: {success_rate:.1f}%")
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("enhanced_calibrator", False, f"Error: {e}", duration)
            print(f"   FAIL - Error en calibrador: {e}")
            return False
    
    def test_pathfinding_manager(self):
        """Test 3: Verificar que el manager de pathfinding funciona"""
        
        print("\nTest 3: Verificando pathfinding manager...")
        test_start = time.time()
        
        try:
            from pathfinding_manager import get_pathfinding_manager
            
            # Obtener manager
            manager = get_pathfinding_manager()
            
            # Test cambio de modo
            original_mode = manager.modo
            
            # Test modo MEJORADO
            success_mejorado = manager.establecer_modo("MEJORADO")
            if not success_mejorado:
                raise Exception("No se pudo establecer modo MEJORADO")
            
            # Test ruta con modo mejorado
            test_route = manager.calcular_ruta_con_fallback((1750, 550), (100, 50))
            if not test_route or len(test_route) < 2:
                raise Exception("Ruta inválida en modo MEJORADO")
            
            # Test modo AB_TEST
            success_ab = manager.establecer_modo("AB_TEST")
            if not success_ab:
                raise Exception("No se pudo establecer modo AB_TEST")
            
            # Test varias rutas en modo AB
            for i in range(5):
                route = manager.calcular_ruta_con_fallback((300, 300), (800, 400))
                if not route or len(route) < 2:
                    raise Exception(f"Ruta inválida en AB_TEST iteración {i}")
            
            # Obtener estadísticas
            stats = manager.obtener_estadisticas()
            if stats['llamadas_total'] == 0:
                raise Exception("No se registraron llamadas")
            
            duration = time.time() - test_start
            self.log_test("pathfinding_manager", True, f"Llamadas: {stats['llamadas_total']}", duration)
            print(f"   PASS - Manager OK ({stats['llamadas_total']} llamadas, {duration*1000:.1f}ms)")
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("pathfinding_manager", False, f"Error: {e}", duration)
            print(f"   FAIL - Error en manager: {e}")
            return False
    
    def test_operators_integration(self):
        """Test 4: Verificar integración en operators.py"""
        
        print("\nTest 4: Verificando integración operators.py...")
        test_start = time.time()
        
        try:
            # Test que se puede importar el reemplazo
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git', 'simulation'))
            
            from mover_por_ruta_mejorado import mover_por_ruta_realista
            
            # Test básico de que la función existe y es callable
            if not callable(mover_por_ruta_realista):
                raise Exception("mover_por_ruta_realista no es callable")
            
            # Verificar que operators.py importa el sistema mejorado
            with open('git/simulation/operators.py', 'r', encoding='utf-8') as f:
                operators_content = f.read()
            
            if 'from mover_por_ruta_mejorado import' in operators_content:
                integration_ok = True
            else:
                integration_ok = False
                raise Exception("operators.py no está usando el sistema mejorado")
            
            duration = time.time() - test_start
            self.log_test("operators_integration", True, "Integración correcta", duration)
            print(f"   PASS - Integración OK ({duration*1000:.1f}ms)")
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("operators_integration", False, f"Error: {e}", duration)
            print(f"   FAIL - Error en integración: {e}")
            return False
    
    def test_ubicaciones_picking(self):
        """Test 5: Verificar sistema de ubicaciones de picking"""
        
        print("\nTest 5: Verificando ubicaciones de picking...")
        test_start = time.time()
        
        try:
            from utils.ubicaciones_picking import ubicaciones_picking
            
            # Test obtener ubicaciones
            todas_ubicaciones = ubicaciones_picking.obtener_todas_ubicaciones()
            
            if not todas_ubicaciones:
                raise Exception("No se obtuvieron ubicaciones")
            
            if len(todas_ubicaciones) < 100:
                raise Exception(f"Pocas ubicaciones: {len(todas_ubicaciones)}")
            
            # Test estadísticas
            stats = ubicaciones_picking.obtener_estadisticas()
            
            if 'total_ubicaciones' not in stats:
                raise Exception("Estadísticas incompletas")
            
            # Test ubicación específica
            primera_ubicacion = todas_ubicaciones[0]
            if not isinstance(primera_ubicacion, tuple) or len(primera_ubicacion) != 2:
                raise Exception("Formato de ubicación inválido")
            
            duration = time.time() - test_start
            self.log_test("ubicaciones_picking", True, f"Ubicaciones: {len(todas_ubicaciones)}", duration)
            print(f"   PASS - Ubicaciones OK ({len(todas_ubicaciones)} ubicaciones, {duration*1000:.1f}ms)")
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("ubicaciones_picking", False, f"Error: {e}", duration)
            print(f"   FAIL - Error en ubicaciones: {e}")
            return False
    
    def test_configuracion(self):
        """Test 6: Verificar configuración del sistema"""
        
        print("\nTest 6: Verificando configuración...")
        test_start = time.time()
        
        try:
            import config.settings as settings
            
            # Test constantes críticas
            critical_settings = {
                'ANCHO_PANTALLA': settings.ANCHO_PANTALLA,
                'ALTO_PANTALLA': settings.ALTO_PANTALLA, 
                'POS_DEPOT': settings.POS_DEPOT,
                'POS_INBOUND': settings.POS_INBOUND,
                'NUM_COLUMNAS_RACKS': settings.NUM_COLUMNAS_RACKS,
                'VELOCIDAD_MOVIMIENTO': settings.VELOCIDAD_MOVIMIENTO
            }
            
            for name, value in critical_settings.items():
                if value is None:
                    raise Exception(f"{name} is None")
                if name in ['ANCHO_PANTALLA', 'ALTO_PANTALLA'] and value <= 0:
                    raise Exception(f"{name} debe ser positivo: {value}")
            
            # Test posiciones válidas
            if not isinstance(settings.POS_DEPOT, tuple) or len(settings.POS_DEPOT) != 2:
                raise Exception("POS_DEPOT formato inválido")
            
            if not isinstance(settings.POS_INBOUND, tuple) or len(settings.POS_INBOUND) != 2:
                raise Exception("POS_INBOUND formato inválido")
            
            duration = time.time() - test_start
            self.log_test("configuracion", True, "Configuración válida", duration)
            print(f"   PASS - Configuración OK ({duration*1000:.1f}ms)")
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("configuracion", False, f"Error: {e}", duration)
            print(f"   FAIL - Error en configuración: {e}")
            return False
    
    def test_performance(self):
        """Test 7: Test de rendimiento básico"""
        
        print("\nTest 7: Verificando rendimiento...")
        test_start = time.time()
        
        try:
            from pathfinding_manager import get_pathfinding_manager
            
            manager = get_pathfinding_manager()
            manager.establecer_modo("MEJORADO")
            
            # Test rendimiento con múltiples rutas
            test_routes = [
                ((1750, 550), (100, 50)),
                ((100, 50), (300, 300)),
                ((300, 300), (800, 400)),
                ((800, 400), (1200, 500)),
                ((1200, 500), (1750, 550)),
            ] * 10  # 50 rutas total
            
            performance_start = time.time()
            
            for start, end in test_routes:
                route = manager.calcular_ruta_con_fallback(start, end)
                if not route or len(route) < 2:
                    raise Exception(f"Ruta falló: {start} -> {end}")
            
            performance_duration = time.time() - performance_start
            avg_time_per_route = (performance_duration / len(test_routes)) * 1000  # ms
            
            # Criterio: menos de 50ms por ruta en promedio
            if avg_time_per_route > 50:
                raise Exception(f"Rendimiento lento: {avg_time_per_route:.1f}ms por ruta")
            
            duration = time.time() - test_start
            details = f"{len(test_routes)} rutas, {avg_time_per_route:.1f}ms/ruta"
            self.log_test("performance", True, details, duration)
            print(f"   PASS - Rendimiento OK ({details})")
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("performance", False, f"Error: {e}", duration)
            print(f"   FAIL - Error rendimiento: {e}")
            return False
    
    def run_complete_regression_test(self):
        """Ejecutar suite completa de regression testing"""
        
        print("="*60)
        print("TESTING DE REGRESIÓN COMPLETO")
        print("="*60)
        print(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.start_time = time.time()
        
        # Lista de tests
        tests = [
            ("Importaciones", self.test_imports),
            ("Calibrador Mejorado", self.test_enhanced_calibrator),
            ("Pathfinding Manager", self.test_pathfinding_manager),
            ("Integración Operators", self.test_operators_integration),
            ("Ubicaciones Picking", self.test_ubicaciones_picking),
            ("Configuración", self.test_configuracion),
            ("Rendimiento", self.test_performance),
        ]
        
        print(f"\nEjecutando {len(tests)} tests de regresión...")
        print("-" * 40)
        
        # Ejecutar tests
        for test_name, test_function in tests:
            try:
                test_function()
            except Exception as e:
                self.log_test(test_name.lower().replace(' ', '_'), False, f"Exception: {e}")
                print(f"   FAIL - Error inesperado: {e}")
        
        # Generar reporte
        self.generate_regression_report()
        
        return self.passed_tests == self.total_tests
    
    def generate_regression_report(self):
        """Generar reporte completo de regresión"""
        
        total_duration = time.time() - self.start_time
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"\n{'='*60}")
        print("REPORTE DE REGRESIÓN")
        print("="*60)
        
        print(f"Tests ejecutados: {self.total_tests}")
        print(f"Tests exitosos: {self.passed_tests}")
        print(f"Tests fallidos: {self.failed_tests}")
        print(f"Tasa de éxito: {success_rate:.1f}%")
        print(f"Tiempo total: {total_duration:.2f} segundos")
        
        if self.failed_tests > 0:
            print(f"\nTESTS FALLIDOS:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"  - {test_name}: {result['details']}")
        
        # Guardar reporte detallado
        report_data = {
            'summary': {
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'success_rate': success_rate,
                'total_duration': total_duration,
                'timestamp': datetime.now().isoformat()
            },
            'detailed_results': self.test_results
        }
        
        report_filename = f"regression_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nReporte detallado guardado: {report_filename}")
        
        # Veredicto final
        if success_rate >= 90:
            print(f"\n✅ REGRESIÓN EXITOSA - Sistema funciona correctamente")
        elif success_rate >= 70:
            print(f"\n⚠️ REGRESIÓN PARCIAL - Revisar tests fallidos")
        else:
            print(f"\n❌ REGRESIÓN FALLIDA - Sistema necesita correcciones")
        
        return success_rate

def main():
    """Ejecutar testing de regresión completo"""
    
    tester = RegressionTester()
    success = tester.run_complete_regression_test()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)