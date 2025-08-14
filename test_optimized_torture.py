#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MATRIZ DE TORTURA OPTIMIZADA - Casos extremos pero navegables
"""

def create_optimized_torture_matrix():
    """Crear matriz de tortura que SÍ tenga soluciones válidas pero difíciles"""
    
    # Matriz 25x15 con casos extremos NAVEGABLES
    torture_matrix = [
        # 0 = navegable, 1 = obstáculo
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 0 - Ruta libre superior
        [1,1,1,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1],  # 1 - Pasillos estrechos
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 2 - Conexión horizontal
        [1,0,1,1,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,0,1],  # 3 - Obstáculos zigzag
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],  # 4 - Pasillo serpentina
        [1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1],  # 5 - Intersecciones T
        [0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0],  # 6 - Ruta con obstáculos puntuales
        [1,0,1,1,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,1,0,1,1,1],  # 7 - Laberinto parcial
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],  # 8 - Corredor largo
        [1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1],  # 9 - Callejón con salida
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 10 - Ruta libre inferior
        [1,1,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1], # 11 - Últimos obstáculos
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]   # 12 - Destino libre
    ]
    
    return torture_matrix

def test_optimized_torture():
    """Probar pathfinding con la matriz optimizada"""
    try:
        from pathfinding.core.grid import Grid
        from pathfinding.finder.a_star import AStarFinder
        from pathfinding.core.diagonal_movement import DiagonalMovement
        
        print("PROBANDO MATRIZ DE TORTURA OPTIMIZADA...")
        torture_matrix = create_optimized_torture_matrix()
        grid = Grid(matrix=torture_matrix)
        
        # Casos de prueba que SÍ deberían tener solución
        test_cases = [
            {"name": "Ruta simple horizontal", "start": (0, 0), "end": (24, 0)},
            {"name": "Navegacion vertical con obstaculos", "start": (0, 0), "end": (0, 12)},
            {"name": "Ruta serpenteante larga", "start": (1, 4), "end": (23, 8)},
            {"name": "Evitar laberinto", "start": (8, 1), "end": (14, 7)},
            {"name": "Intersecciones multiples", "start": (3, 3), "end": (19, 9)},
            {"name": "Pasillo estrecho extremo", "start": (8, 1), "end": (14, 1)},
            {"name": "Ruta diagonal compleja", "start": (1, 1), "end": (23, 11)}
        ]
        
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        
        successful_cases = 0
        total_cases = len(test_cases)
        
        for i, case in enumerate(test_cases, 1):
            print(f"\nCaso {i}: {case['name']}")
            
            start = grid.node(case['start'][0], case['start'][1])
            end = grid.node(case['end'][0], case['end'][1])
            
            # Reiniciar grid para cada test
            grid.cleanup()
            
            path, runs = finder.find_path(start, end, grid)
            
            if path:
                successful_cases += 1
                route = [(node.x, node.y) for node in path]
                print(f"   [EXITO] Ruta: {len(path)} pasos, {runs} nodos explorados")
                print(f"   Desde {route[0]} hasta {route[-1]}")
                
                # Analizar complejidad de la ruta
                if runs > 50:
                    print("   [ANALISIS] Ruta compleja - algoritmo trabajó duro")
                elif len(path) > 30:
                    print("   [ANALISIS] Ruta larga - buenos obstáculos")
                else:
                    print("   [ANALISIS] Ruta eficiente encontrada")
            else:
                print(f"   [FALLO] Sin solución ({runs} nodos explorados)")
        
        print(f"\n{'='*50}")
        print(f"RESUMEN MATRIZ TORTURA OPTIMIZADA:")
        print(f"Casos exitosos: {successful_cases}/{total_cases}")
        print(f"Tasa de éxito: {(successful_cases/total_cases)*100:.1f}%")
        
        if successful_cases >= 5:  # Al menos 5/7 casos exitosos
            print("[MATRIZ VALIDA] Lista para usar en Tiled!")
            return True
        else:
            print("[MATRIZ MUY AGRESIVA] Necesita más ajustes")
            return False
        
    except Exception as e:
        print(f"[ERROR] Error en prueba optimizada: {e}")
        import traceback
        traceback.print_exc()
        return False

def visualize_matrix():
    """Crear visualización ASCII de la matriz"""
    matrix = create_optimized_torture_matrix()
    
    print("\nVISUALIZACION DE MATRIZ DE TORTURA:")
    print("  " + "".join([str(i%10) for i in range(25)]))
    
    for i, row in enumerate(matrix):
        visual_row = ""
        for cell in row:
            if cell == 0:
                visual_row += "."  # Navegable
            else:
                visual_row += "#"  # Obstáculo
        print(f"{i:2d}{visual_row}")
    
    print("\nLEYENDA:")
    print("  . = Navegable")
    print("  # = Obstáculo")
    print("  Dimensiones: 25x13")

if __name__ == "__main__":
    visualize_matrix()
    test_optimized_torture()