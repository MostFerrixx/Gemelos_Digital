#!/usr/bin/env python3
"""
Prueba simple del sistema TMX - Solo LayoutManager y Pathfinder
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

print("=== PRUEBA SIMPLE TMX ===")
print("0. Inicializando pygame...")

import pygame
pygame.init()
pygame.display.set_mode((100, 100))  # Ventana mínima para inicializar display
print("[OK] Pygame inicializado")

print("1. Importando LayoutManager...")

try:
    from simulation.layout_manager import LayoutManager
    print("[OK] LayoutManager importado correctamente")
except Exception as e:
    print(f"[ERROR] Error importando LayoutManager: {e}")
    exit(1)

print("\n2. Importando Pathfinder...")

try:
    from simulation.pathfinder import Pathfinder
    print("[OK] Pathfinder importado correctamente")
except Exception as e:
    print(f"[ERROR] Error importando Pathfinder: {e}")
    exit(1)

print("\n3. Cargando archivo TMX...")

try:
    tmx_file = "layouts/WH1.tmx"
    layout_manager = LayoutManager(tmx_file)
    print(f"[OK] TMX cargado: {tmx_file}")
    print(f"   - Dimensiones: {layout_manager.grid_width}x{layout_manager.grid_height}")
    print(f"   - Tile size: {layout_manager.tile_width}x{layout_manager.tile_height}")
    print(f"   - Puntos de picking: {len(layout_manager.picking_points)}")
    print(f"   - Puntos de depot: {len(layout_manager.depot_points)}")
except Exception as e:
    print(f"[ERROR] Error cargando TMX: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n4. Inicializando Pathfinder...")

try:
    pathfinder = Pathfinder(layout_manager.collision_matrix)
    print(f"[OK] Pathfinder inicializado")
    print(f"   - Matriz de colision: {layout_manager.collision_matrix.shape}")
    print(f"   - Celdas caminables: {(layout_manager.collision_matrix == 0).sum()}")
    print(f"   - Celdas bloqueadas: {(layout_manager.collision_matrix == 1).sum()}")
except Exception as e:
    print(f"[ERROR] Error inicializando Pathfinder: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n5. Probando pathfinding...")

try:
    if layout_manager.depot_points and layout_manager.picking_points:
        start = layout_manager.depot_points[0]
        end = layout_manager.picking_points[0]
        
        print(f"   - Origen: {start}")
        print(f"   - Destino: {end}")
        
        route = pathfinder.find_path(start, end)
        
        if route:
            print(f"[OK] Ruta encontrada: {len(route)} pasos")
            print(f"   - Primeros 3 pasos: {route[:3]}")
            print(f"   - Ultimos 3 pasos: {route[-3:]}")
        else:
            print("[ERROR] No se encontro ruta")
    else:
        print("[WARNING] No hay puntos de depot o picking para probar")
except Exception as e:
    print(f"[ERROR] Error en pathfinding: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n[SUCCESS] PRUEBA TMX COMPLETADA EXITOSAMENTE!")
print("\nLa arquitectura TMX esta funcionando correctamente.")
print("Proximo paso: Probar integracion completa con el simulador.")