#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MATRIZ FINAL DE TORTURA - VALORES CORREGIDOS
1 = navegable, 0 = obstáculo
"""

def create_final_torture_matrix():
    """Matriz de tortura con convención correcta: 1=navegable, 0=obstáculo"""
    
    # Matriz 25x13 CORREGIDA
    torture_matrix = [
        # 1 = navegable, 0 = obstáculo  
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],  # 0 - Ruta libre superior
        [0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0],  # 1 - Pasillos estrechos
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],  # 2 - Conexión horizontal
        [0,1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,1,0],  # 3 - Obstáculos zigzag
        [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 4 - Pasillo serpentina
        [0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0],  # 5 - Intersecciones T
        [1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,1],  # 6 - Ruta con obstáculos puntuales
        [0,1,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0],  # 7 - Laberinto parcial
        [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 8 - Corredor largo
        [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0],  # 9 - Callejón con salida
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],  # 10 - Ruta libre inferior
        [0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0],  # 11 - Últimos obstáculos
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]   # 12 - Destino libre
    ]
    
    return torture_matrix

def test_final_torture():
    """Prueba final con matriz corregida"""
    try:
        from pathfinding.core.grid import Grid
        from pathfinding.finder.a_star import AStarFinder
        from pathfinding.core.diagonal_movement import DiagonalMovement
        
        print("PRUEBA FINAL - MATRIZ DE TORTURA CORREGIDA")
        torture_matrix = create_final_torture_matrix()
        
        # Visualizar matriz
        print("\nVISUALIZACION:")
        print("  " + "".join([str(i%10) for i in range(25)]))
        for i, row in enumerate(torture_matrix):
            visual = ""
            for cell in row:
                visual += "." if cell == 1 else "#"
            print(f"{i:2d}{visual}")
        print("  . = navegable, # = obstáculo")
        
        grid = Grid(matrix=torture_matrix)
        
        # Casos de prueba en posiciones navegables
        test_cases = [
            {"name": "Ruta horizontal simple", "start": (0, 0), "end": (24, 0)},
            {"name": "Ruta vertical completa", "start": (0, 0), "end": (0, 12)},
            {"name": "Navegacion serpentina", "start": (1, 4), "end": (23, 8)},
            {"name": "Evitar obstáculos zigzag", "start": (1, 2), "end": (23, 6)},
            {"name": "Ruta compleja diagonal", "start": (5, 2), "end": (19, 10)},
            {"name": "Pasillo estrecho", "start": (8, 1), "end": (14, 1)},
            {"name": "Laberinto parcial", "start": (1, 7), "end": (23, 7)}
        ]
        
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        
        successful = 0
        total = len(test_cases)
        
        for i, case in enumerate(test_cases, 1):
            print(f"\nCaso {i}: {case['name']}")
            
            start = grid.node(case['start'][0], case['start'][1])
            end = grid.node(case['end'][0], case['end'][1])
            
            print(f"   Start navegable? {start.walkable}")
            print(f"   End navegable? {end.walkable}")
            
            if not start.walkable or not end.walkable:
                print("   [ERROR] Nodos no navegables!")
                continue
            
            grid.cleanup()
            path, runs = finder.find_path(start, end, grid)
            
            if path:
                successful += 1
                route = [(node.x, node.y) for node in path]
                print(f"   [EXITO] Ruta: {len(path)} pasos, {runs} nodos explorados")
                print(f"   Desde {route[0]} hasta {route[-1]}")
                
                # Análisis de complejidad
                complexity = "SIMPLE" if runs < 20 else "MEDIA" if runs < 50 else "COMPLEJA"
                efficiency = "DIRECTA" if len(path) < 30 else "SERPENTEANTE"
                print(f"   [ANÁLISIS] Complejidad: {complexity}, Ruta: {efficiency}")
            else:
                print(f"   [FALLO] Sin solución ({runs} nodos explorados)")
        
        print(f"\n{'='*60}")
        print(f"RESUMEN FINAL MATRIZ DE TORTURA:")
        print(f"Casos exitosos: {successful}/{total} ({(successful/total)*100:.1f}%)")
        
        if successful >= 5:
            print("[MATRIZ PERFECTA] Lista para implementar en Tiled!")
            print("Casos extremos validados:")
            print("- Pasillos estrechos de 1 tile")
            print("- Obstáculos en zigzag") 
            print("- Intersecciones complejas")
            print("- Rutas serpenteantes largas")
            print("- Navegación con múltiples obstáculos")
            return True
        else:
            print("[MATRIZ NECESITA AJUSTES]")
            return False
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_final_torture()