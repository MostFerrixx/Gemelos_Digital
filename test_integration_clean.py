#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUEBA DE INTEGRACIÓN LIMPIA: PyTMX + Pygame + Pathfinding
FASE 1: Layout de Tortura - Testing de casos extremos (SIN UNICODE)
"""

import pygame
import sys
import os

# Agregar el directorio git al path para importar módulos existentes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

def test_pytmx_import():
    """Test 1: Verificar que pytmx se importa correctamente"""
    try:
        import pytmx
        print("[OK] PyTMX importado correctamente")
        print(f"   Version: {pytmx.__version__ if hasattr(pytmx, '__version__') else 'N/A'}")
        return True
    except ImportError as e:
        print(f"[ERROR] Error importando PyTMX: {e}")
        return False

def test_pathfinding_import():
    """Test 2: Verificar que pathfinding se importa correctamente"""
    try:
        import pathfinding
        from pathfinding.core.grid import Grid
        from pathfinding.finder.a_star import AStarFinder
        print("[OK] Pathfinding library importada correctamente")
        return True
    except ImportError as e:
        print(f"[ERROR] Error importando pathfinding: {e}")
        return False

def test_pygame_integration():
    """Test 3: Verificar integración básica con pygame"""
    try:
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("PyTMX Integration Test")
        print("[OK] Pygame inicializado correctamente")
        pygame.quit()
        return True
    except Exception as e:
        print(f"[ERROR] Error con pygame: {e}")
        return False

def test_simple_pathfinding():
    """Test 4: Prueba básica de pathfinding con matriz simple"""
    try:
        from pathfinding.core.grid import Grid
        from pathfinding.finder.a_star import AStarFinder
        from pathfinding.core.diagonal_movement import DiagonalMovement
        
        # Crear una grilla simple de prueba
        matrix = [
            [1, 1, 1, 1, 1],
            [1, 0, 0, 0, 1],
            [1, 1, 1, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1]
        ]
        
        grid = Grid(matrix=matrix)
        start = grid.node(1, 1)
        end = grid.node(3, 3)
        
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        path, runs = finder.find_path(start, end, grid)
        
        print(f"[OK] Pathfinding basico funcionando")
        print(f"   Ruta encontrada: {len(path)} puntos")
        print(f"   Nodos explorados: {runs}")
        print(f"   Ruta: {[(node.x, node.y) for node in path]}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error en pathfinding basico: {e}")
        return False

def create_torture_matrix():
    """Test 5: Crear matriz de 'tortura' para casos extremos"""
    print("CREANDO LAYOUT DE TORTURA:")
    
    # Matriz 20x15 con casos extremos
    torture_matrix = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],  # Borde superior
        [1,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1],  # Pasillos estrechos
        [1,0,1,0,1,0,1,1,1,1,1,1,1,0,1,0,1,1,0,1],  # Obstáculos zigzag
        [1,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,1],  # Intersección T
        [1,0,1,1,1,1,1,0,1,1,1,0,1,1,1,1,1,0,1,1],  # Laberinto parcial
        [1,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,1],  # Pasillo largo serpenteante
        [1,1,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,0,1],  # Callejones sin salida
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],  # Intersección +
        [1,0,1,1,1,0,1,1,1,1,1,1,1,0,1,1,1,1,0,1],  # Más obstáculos
        [1,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,1],  # Rutas alternativas
        [1,0,1,0,1,1,1,1,1,1,1,0,1,1,1,1,0,1,0,1],  # Complejidad máxima
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],  # Última ruta libre
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]   # Borde inferior
    ]
    
    print(f"   Matriz: {len(torture_matrix[0])}x{len(torture_matrix)}")
    print("   Casos incluidos:")
    print("   - Pasillos de 1 tile ancho")
    print("   - Intersecciones T y +")
    print("   - Callejones sin salida")
    print("   - Obstaculos en zigzag")
    print("   - Rutas serpenteantes")
    
    return torture_matrix

def test_torture_pathfinding():
    """Test 6: Probar pathfinding en condiciones extremas"""
    try:
        from pathfinding.core.grid import Grid
        from pathfinding.finder.a_star import AStarFinder
        from pathfinding.core.diagonal_movement import DiagonalMovement
        
        torture_matrix = create_torture_matrix()
        grid = Grid(matrix=torture_matrix)
        
        # Casos de prueba extremos
        test_cases = [
            {"name": "Ruta larga serpenteante", "start": (1, 1), "end": (18, 11)},
            {"name": "Navegacion por pasillo estrecho", "start": (1, 1), "end": (1, 7)},
            {"name": "Evitar callejon sin salida", "start": (7, 6), "end": (13, 6)},
            {"name": "Interseccion compleja", "start": (5, 5), "end": (15, 7)},
            {"name": "Caso imposible", "start": (1, 1), "end": (17, 2)}  # Puede no tener solución
        ]
        
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        
        for i, case in enumerate(test_cases, 1):
            print(f"\nCaso {i}: {case['name']}")
            
            start = grid.node(case['start'][0], case['start'][1])
            end = grid.node(case['end'][0], case['end'][1])
            
            # Reiniciar grid para cada test
            grid.cleanup()
            
            path, runs = finder.find_path(start, end, grid)
            
            if path:
                print(f"   [OK] Ruta encontrada: {len(path)} pasos, {runs} nodos explorados")
                # Mostrar primeros y últimos puntos
                route = [(node.x, node.y) for node in path]
                print(f"   Inicio: {route[0]} -> Fin: {route[-1]}")
                if len(route) > 6:
                    print(f"   Ruta: {route[:3]} ... {route[-3:]}")
                else:
                    print(f"   Ruta: {route}")
            else:
                print(f"   [FALLO] Sin solucion ({runs} nodos explorados)")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error en pathfinding de tortura: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todas las pruebas de integración"""
    print("="*60)
    print("PRUEBAS DE INTEGRACION - FASE 1: LAYOUT DE TORTURA")
    print("="*60)
    
    tests = [
        test_pytmx_import,
        test_pathfinding_import,
        test_pygame_integration,
        test_simple_pathfinding,
        test_torture_pathfinding
    ]
    
    passed = 0
    total = len(tests)
    
    for i, test in enumerate(tests, 1):
        print(f"\n--- Test {i}/{total}: {test.__name__} ---")
        if test():
            passed += 1
        print("---")
    
    print(f"\n{'='*60}")
    print(f"RESULTADOS: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("[EXITO] TODAS LAS PRUEBAS PASARON!")
        print("Listo para integracion con Tiled")
    else:
        print(f"[ALERTA] {total-passed} pruebas fallaron")
        print("Revisar dependencias antes de continuar")
    
    print("="*60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)