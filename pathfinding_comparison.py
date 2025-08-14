#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPARACIÓN DIRECTA: Sistema Actual vs Sistema Mejorado
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from config.settings import *
from utils.ubicaciones_picking import ubicaciones_picking
from enhanced_calibrator import EnhancedCalibrator

# Importar sistema actual
try:
    from utils.pathfinding import calcular_ruta_realista
    CURRENT_SYSTEM_AVAILABLE = True
except ImportError as e:
    CURRENT_SYSTEM_AVAILABLE = False
    print(f"Sistema actual no disponible: {e}")

class PathfindingComparator:
    """Comparar directamente sistema actual vs mejorado"""
    
    def __init__(self):
        print("COMPARADOR DE SISTEMAS DE PATHFINDING")
        print("="*50)
        
        # Sistema mejorado
        print("Inicializando sistema mejorado...")
        self.enhanced_system = EnhancedCalibrator()
        
        # Verificar disponibilidad del sistema actual
        self.current_available = CURRENT_SYSTEM_AVAILABLE
        print(f"Sistema actual disponible: {self.current_available}")
    
    def calculate_current_route(self, start, end):
        """Calcular ruta con sistema actual"""
        if not self.current_available:
            return None, 0, "Sistema no disponible"
        
        try:
            ruta = calcular_ruta_realista(start, end, operario_id=1)
            if ruta:
                distance = self.calculate_route_distance(ruta)
                return ruta, len(ruta), f"SUCCESS: {distance:.1f}px"
            else:
                return None, 0, "FAIL: Sin ruta"
        except Exception as e:
            return None, 0, f"ERROR: {e}"
    
    def calculate_enhanced_route(self, start, end):
        """Calcular ruta con sistema mejorado"""
        try:
            ruta, runs = self.enhanced_system.calculate_route_enhanced(start, end)
            if ruta:
                distance = self.calculate_route_distance(ruta)
                return ruta, runs, f"SUCCESS: {distance:.1f}px, {runs} nodos"
            else:
                return None, runs, f"FAIL: Sin ruta, {runs} nodos explorados"
        except Exception as e:
            return None, 0, f"ERROR: {e}"
    
    def calculate_route_distance(self, route):
        """Calcular distancia total de una ruta"""
        if not route or len(route) < 2:
            return 0
        
        total = 0
        for i in range(1, len(route)):
            x1, y1 = route[i-1]
            x2, y2 = route[i]
            total += ((x2-x1)**2 + (y2-y1)**2)**0.5
        
        return total
    
    def run_comprehensive_comparison(self):
        """Comparación exhaustiva entre sistemas"""
        
        print(f"\n{'='*60}")
        print("COMPARACIÓN EXHAUSTIVA DE SISTEMAS")
        print("="*60)
        
        # Obtener ubicaciones reales
        ubicaciones_reales = ubicaciones_picking.obtener_todas_ubicaciones()
        
        # Casos de prueba comprehensivos
        test_cases = [
            {
                "name": "Depot a Inbound (principales)",
                "start": POS_DEPOT,
                "end": POS_INBOUND,
                "category": "Principal"
            },
            {
                "name": "Inbound a primer picking",
                "start": POS_INBOUND,
                "end": ubicaciones_reales[0] if ubicaciones_reales else (300, 300),
                "category": "Picking"
            },
            {
                "name": "Entre pickings cercanos",
                "start": ubicaciones_reales[0] if ubicaciones_reales else (300, 300),
                "end": ubicaciones_reales[1] if len(ubicaciones_reales) > 1 else (320, 320),
                "category": "Picking"
            },
            {
                "name": "Picking lejano mismo rack",
                "start": ubicaciones_reales[0] if ubicaciones_reales else (300, 300),
                "end": ubicaciones_reales[5] if len(ubicaciones_reales) > 5 else (300, 400),
                "category": "Picking"
            },
            {
                "name": "Entre racks diferentes",
                "start": ubicaciones_reales[0] if ubicaciones_reales else (300, 300),
                "end": ubicaciones_reales[50] if len(ubicaciones_reales) > 50 else (800, 350),
                "category": "Picking"
            },
            {
                "name": "Picking a Depot",
                "start": ubicaciones_reales[10] if len(ubicaciones_reales) > 10 else (500, 350),
                "end": POS_DEPOT,
                "category": "Principal"
            },
            {
                "name": "Ruta diagonal larga",
                "start": (200, 200),
                "end": (1600, 600),
                "category": "Diagonal"
            },
            {
                "name": "Navegación horizontal",
                "start": (300, Y_PASILLO_SUPERIOR + 20),
                "end": (1200, Y_PASILLO_SUPERIOR + 20),
                "category": "Horizontal"
            },
            {
                "name": "Navegación vertical",
                "start": (500, Y_PASILLO_SUPERIOR + 50),
                "end": (500, Y_PASILLO_INFERIOR - 50),
                "category": "Vertical"
            },
            {
                "name": "Extremo a extremo",
                "start": (100, 100),
                "end": (1800, 800),
                "category": "Extremo"
            }
        ]
        
        # Resultados por categoría
        results_by_category = {}
        current_successful = 0
        enhanced_successful = 0
        total_cases = len(test_cases)
        
        for i, case in enumerate(test_cases, 1):
            print(f"\nCaso {i}: {case['name']} [{case['category']}]")
            print(f"  Coordenadas: {case['start']} -> {case['end']}")
            
            # Sistema actual
            if self.current_available:
                current_route, current_nodes, current_msg = self.calculate_current_route(case['start'], case['end'])
                current_success = current_route is not None
                if current_success:
                    current_successful += 1
                print(f"  [ACTUAL] {current_msg}")
            else:
                current_route, current_nodes, current_msg = None, 0, "No disponible"
                current_success = False
                print(f"  [ACTUAL] {current_msg}")
            
            # Sistema mejorado
            enhanced_route, enhanced_nodes, enhanced_msg = self.calculate_enhanced_route(case['start'], case['end'])
            enhanced_success = enhanced_route is not None
            if enhanced_success:
                enhanced_successful += 1
            print(f"  [MEJORADO] {enhanced_msg}")
            
            # Comparación si ambos exitosos
            if current_success and enhanced_success:
                current_dist = self.calculate_route_distance(current_route)
                enhanced_dist = self.calculate_route_distance(enhanced_route)
                
                dist_diff = abs(current_dist - enhanced_dist)
                dist_improvement = ((current_dist - enhanced_dist) / current_dist * 100) if current_dist > 0 else 0
                nodes_comparison = f"{current_nodes} vs {enhanced_nodes} nodos"
                
                print(f"  [COMPARE] Distancia: {current_dist:.1f}px -> {enhanced_dist:.1f}px ({dist_improvement:+.1f}%)")
                print(f"  [COMPARE] Complejidad: {nodes_comparison}")
            
            # Agrupar por categoría
            if case['category'] not in results_by_category:
                results_by_category[case['category']] = {
                    'current_success': 0,
                    'enhanced_success': 0,
                    'total': 0
                }
            
            results_by_category[case['category']]['total'] += 1
            if current_success:
                results_by_category[case['category']]['current_success'] += 1
            if enhanced_success:
                results_by_category[case['category']]['enhanced_success'] += 1
        
        # Resumen general
        print(f"\n{'='*60}")
        print("RESUMEN GENERAL")
        print("="*60)
        
        if self.current_available:
            current_rate = current_successful / total_cases * 100
            print(f"Sistema ACTUAL: {current_successful}/{total_cases} exitosos ({current_rate:.1f}%)")
        else:
            print(f"Sistema ACTUAL: No disponible para comparación")
        
        enhanced_rate = enhanced_successful / total_cases * 100
        print(f"Sistema MEJORADO: {enhanced_successful}/{total_cases} exitosos ({enhanced_rate:.1f}%)")
        
        # Resumen por categorías
        print(f"\nRESUMEN POR CATEGORÍAS:")
        for category, stats in results_by_category.items():
            total = stats['total']
            current = stats['current_success']
            enhanced = stats['enhanced_success']
            
            if self.current_available:
                current_pct = current / total * 100 if total > 0 else 0
                enhanced_pct = enhanced / total * 100 if total > 0 else 0
                print(f"  {category:12}: Actual {current_pct:5.1f}% | Mejorado {enhanced_pct:5.1f}%")
            else:
                enhanced_pct = enhanced / total * 100 if total > 0 else 0
                print(f"  {category:12}: Mejorado {enhanced_pct:5.1f}%")
        
        # Veredicto final
        print(f"\n{'='*60}")
        print("VEREDICTO FINAL")
        print("="*60)
        
        if enhanced_rate >= 90:
            print("EXCELENTE - Sistema mejorado funciona superiormente")
            if self.current_available and enhanced_rate > current_rate:
                improvement = enhanced_rate - current_rate
                print(f"MEJORA SIGNIFICATIVA: +{improvement:.1f}% vs sistema actual")
            return True
        elif enhanced_rate >= 70:
            print("BUENO - Sistema mejorado es funcional")
            return True
        else:
            print("NECESITA MEJORAS - Revisar calibración")
            return False

def main():
    """Ejecutar comparación completa"""
    print("="*70)
    print("COMPARADOR DE PATHFINDING - ACTUAL vs MEJORADO")
    print("="*70)
    
    comparator = PathfindingComparator()
    
    success = comparator.run_comprehensive_comparison()
    
    if success:
        print(f"\nSISTEMA MEJORADO VALIDADO!")
        print("Listo para reemplazar sistema actual")
    else:
        print(f"\nSISTEMA MEJORADO NECESITA AJUSTES")
    
    return comparator

if __name__ == "__main__":
    comparator = main()