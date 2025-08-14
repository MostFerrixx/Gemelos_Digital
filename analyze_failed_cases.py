#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANÁLISIS DETALLADO DE CASOS FALLIDOS
"""

def analyze_failed_cases():
    """Analizar específicamente por qué fallaron los casos"""
    
    # Matriz exacta del test anterior
    torture_matrix = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],  # 0
        [0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0],  # 1
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],  # 2
        [0,1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,1,0],  # 3
        [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 4
        [0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0],  # 5
        [1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,1],  # 6
        [0,1,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0],  # 7
        [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 8
        [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0],  # 9
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],  # 10
        [0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0],  # 11
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]   # 12
    ]
    
    print("ANÁLISIS DE CASOS FALLIDOS")
    print("="*50)
    
    # Caso 4 fallido: (1,2) → (23,6)
    print("\nCASO 4 FALLIDO: 'Evitar obstáculos zigzag'")
    print("Start: (1,2) -> End: (23,6)")
    
    start_pos = (1, 2)
    end_pos = (23, 6)
    
    print(f"\nStart (1,2): valor = {torture_matrix[2][1]} ({'navegable' if torture_matrix[2][1] == 1 else 'bloqueado'})")
    print(f"End (23,6): valor = {torture_matrix[6][23]} ({'navegable' if torture_matrix[6][23] == 1 else 'bloqueado'})")
    
    # Analizar el área alrededor del destino
    print("\nÁrea alrededor del destino (23,6):")
    for y in range(max(0, 6-2), min(len(torture_matrix), 6+3)):
        for x in range(max(0, 23-2), min(len(torture_matrix[0]), 23+3)):
            valor = torture_matrix[y][x]
            symbol = "." if valor == 1 else "#"
            if x == 23 and y == 6:
                symbol = "E"  # End
            print(f"{symbol}", end="")
        print(f"  <- fila {y}")
    
    # Caso 7 fallido: (1,7) → (23,7)
    print(f"\n\nCASO 7 FALLIDO: 'Laberinto parcial'")
    print("Start: (1,7) -> End: (23,7)")
    
    start_pos_7 = (1, 7)
    end_pos_7 = (23, 7)
    
    print(f"\nStart (1,7): valor = {torture_matrix[7][1]} ({'navegable' if torture_matrix[7][1] == 1 else 'bloqueado'})")
    print(f"End (23,7): valor = {torture_matrix[7][23]} ({'navegable' if torture_matrix[7][23] == 1 else 'bloqueado'})")
    
    print("\nÁrea alrededor del destino (23,7):")
    for y in range(max(0, 7-2), min(len(torture_matrix), 7+3)):
        for x in range(max(0, 23-2), min(len(torture_matrix[0]), 23+3)):
            valor = torture_matrix[y][x]
            symbol = "." if valor == 1 else "#"
            if x == 23 and y == 7:
                symbol = "E"  # End
            elif x == 1 and y == 7:
                symbol = "S"  # Start (solo para caso 7)
            print(f"{symbol}", end="")
        print(f"  <- fila {y}")
    
    # Buscar rutas alternativas válidas
    print(f"\n\nPROPUESTAS DE CORRECCIÓN:")
    print("="*30)
    
    # Para caso 4
    print("Caso 4 - Alternativas válidas:")
    for y in range(len(torture_matrix)):
        for x in range(len(torture_matrix[0])):
            if torture_matrix[y][x] == 1 and x >= 20:  # Cerca del destino original
                print(f"  Alternativa: (1,2) → ({x},{y})")
                break
        if x >= 20 and torture_matrix[y][x] == 1:
            break
    
    # Para caso 7
    print("Caso 7 - Alternativas válidas:")
    for x in range(20, 25):  # Buscar en área destino
        for y in range(5, 10):
            if x < len(torture_matrix[0]) and y < len(torture_matrix) and torture_matrix[y][x] == 1:
                print(f"  Alternativa: (1,7) → ({x},{y})")
                break
        else:
            continue
        break
    
    return True

def create_corrected_test():
    """Crear test con casos corregidos"""
    print(f"\n\nTEST CORREGIDO PROPUESTO:")
    print("="*40)
    
    corrected_cases = [
        {"name": "Ruta horizontal simple", "start": (0, 0), "end": (24, 0)},
        {"name": "Ruta vertical completa", "start": (0, 0), "end": (5, 12)}, # Corregido
        {"name": "Navegacion serpentina", "start": (1, 4), "end": (23, 8)},
        {"name": "Evitar obstaculos zigzag CORREGIDO", "start": (1, 2), "end": (24, 10)}, # Corregido
        {"name": "Ruta compleja diagonal", "start": (5, 2), "end": (19, 10)},
        {"name": "Pasillo estrecho", "start": (8, 1), "end": (14, 1)},
        {"name": "Laberinto parcial CORREGIDO", "start": (1, 8), "end": (23, 8)}  # Corregido
    ]
    
    for i, case in enumerate(corrected_cases, 1):
        print(f"{i}. {case['name']}: {case['start']} → {case['end']}")
    
    print("\nESTOS CASOS DEBERÍAN TENER 100% DE ÉXITO")

if __name__ == "__main__":
    analyze_failed_cases()
    create_corrected_test()