#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANÁLISIS SIMPLE DE CASOS FALLIDOS (SIN UNICODE)
"""

def simple_analysis():
    # Matriz exacta
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
    
    print("RESUMEN DE CASOS FALLIDOS")
    print("="*40)
    
    # Caso 4: (1,2) -> (23,6)
    print("\nCASO 4 FALLO: Obstaculos zigzag")
    print("Start: (1,2) -> End: (23,6)")
    print(f"Start navegable: {torture_matrix[2][1] == 1}")
    print(f"End navegable: {torture_matrix[6][23] == 1}")
    print("PROBLEMA: Ambos puntos son navegables, pero NO HAY RUTA ENTRE ELLOS")
    print("CAUSA: Los obstaculos zigzag crean 'islas' separadas")
    
    # Caso 7: (1,7) -> (23,7)  
    print("\nCASO 7 FALLO: Laberinto parcial")
    print("Start: (1,7) -> End: (23,7)")
    print(f"Start navegable: {torture_matrix[7][1] == 1}")
    print(f"End navegable: {torture_matrix[7][23] == 1}")
    print("PROBLEMA: El destino (23,7) es un OBSTACULO (valor 0)")
    print("CAUSA: Error en seleccion de coordenadas")
    
    print("\n" + "="*40)
    print("CONCLUSION:")
    print("- Caso 4: Matriz demasiado agresiva, crea islas")  
    print("- Caso 7: Destino en obstaculo (error humano)")
    print("- Ambos casos son NORMALES en testing extremo")
    print("- 71.4% exito es EXCELENTE para 'tortura'")

if __name__ == "__main__":
    simple_analysis()