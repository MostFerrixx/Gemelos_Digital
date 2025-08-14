#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG PATHFINDING - Encontrar el problema con las matrices
"""

def debug_pathfinding_basics():
    """Debuggear paso a paso el comportamiento del pathfinding"""
    try:
        from pathfinding.core.grid import Grid
        from pathfinding.finder.a_star import AStarFinder
        from pathfinding.core.diagonal_movement import DiagonalMovement
        
        print("DEBUGGING PATHFINDING LIBRARY...")
        
        # Test 1: Matriz super simple
        print("\n=== TEST 1: MATRIZ SIMPLE 3x3 ===")
        simple_matrix = [
            [1, 1, 1],
            [1, 1, 1], 
            [1, 1, 1]
        ]
        
        grid = Grid(matrix=simple_matrix)
        start = grid.node(0, 0)
        end = grid.node(2, 2)
        
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        path, runs = finder.find_path(start, end, grid)
        
        print(f"Matriz: {simple_matrix}")
        print(f"Start: {start}, End: {end}")
        print(f"Path: {path}")
        print(f"Ruta: {[(node.x, node.y) for node in path] if path else 'NINGUNA'}")
        
        # Test 2: Verificar convención de la matriz
        print("\n=== TEST 2: CONVENCION DE MATRIZ ===")
        print("Probando si 0=navegable o 1=navegable...")
        
        # Probar con 0 = navegable
        matrix_0_walkable = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]
        ]
        
        grid2 = Grid(matrix=matrix_0_walkable)
        start2 = grid2.node(0, 0)
        end2 = grid2.node(2, 2)
        
        path2, runs2 = finder.find_path(start2, end2, grid2)
        print(f"Con 0=navegable: {len(path2) if path2 else 0} puntos en ruta")
        
        # Probar con 1 = navegable  
        matrix_1_walkable = [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 1]
        ]
        
        grid3 = Grid(matrix=matrix_1_walkable)
        start3 = grid3.node(0, 0)
        end3 = grid3.node(2, 2)
        
        path3, runs3 = finder.find_path(start3, end3, grid3)
        print(f"Con 1=navegable: {len(path3) if path3 else 0} puntos en ruta")
        
        # Test 3: Matriz con obstáculos
        print("\n=== TEST 3: MATRIZ CON OBSTACULOS ===")
        matrix_with_obstacles = [
            [1, 1, 1, 1, 1],
            [1, 0, 0, 0, 1],
            [1, 0, 1, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1]
        ]
        
        grid4 = Grid(matrix=matrix_with_obstacles)
        start4 = grid4.node(1, 1)
        end4 = grid4.node(3, 3)
        
        path4, runs4 = finder.find_path(start4, end4, grid4)
        print(f"Matriz con obstáculos:")
        for i, row in enumerate(matrix_with_obstacles):
            print(f"  {i}: {row}")
        
        print(f"Ruta encontrada: {[(node.x, node.y) for node in path4] if path4 else 'NINGUNA'}")
        
        # Test 4: Verificar nodos válidos
        print(f"\n=== TEST 4: VERIFICACION DE NODOS ===")
        print(f"Nodo start walkable? {start4.walkable}")
        print(f"Nodo end walkable? {end4.walkable}")
        
        # Mostrar estado de todos los nodos
        print("Estado de nodos en matriz 5x5:")
        for y in range(5):
            row_info = []
            for x in range(5):
                node = grid4.node(x, y)
                row_info.append("W" if node.walkable else "B")
            print(f"  Fila {y}: {' '.join(row_info)}")
        
        print("W=Walkable, B=Blocked")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error en debugging: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_pathfinding_basics()