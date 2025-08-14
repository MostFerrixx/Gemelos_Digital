#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALIBRADOR MEJORADO - Mapeo realista del almacén actual
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

# Importar configuración actual
from config.settings import *
from utils.ubicaciones_picking import ubicaciones_picking

class ImprovedCalibrator:
    """Calibrador mejorado con lógica de navegabilidad más realista"""
    
    def __init__(self):
        # Configuración optimizada
        self.tile_size = 20  # Tiles más pequeños para mayor precisión
        self.grid_width = ANCHO_PANTALLA // self.tile_size
        self.grid_height = ALTO_PANTALLA // self.tile_size
        
        print(f"CALIBRADOR MEJORADO")
        print(f"Grid: {self.grid_width}x{self.grid_height} (tile_size: {self.tile_size}px)")
        
        # Crear grid simplificado pero efectivo
        self.create_realistic_grid()
        
        # Setup pathfinding
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
    
    def create_realistic_grid(self):
        """Crear grid con lógica simplificada pero efectiva"""
        
        print("Creando grid realista...")
        
        matrix = []
        
        for grid_y in range(self.grid_height):
            row = []
            for grid_x in range(self.grid_width):
                # Convertir a coordenadas mundo
                world_x = grid_x * self.tile_size
                world_y = grid_y * self.tile_size
                
                # LÓGICA SIMPLIFICADA: Mayoría navegable, obstáculos específicos
                walkable = True
                
                # Bordes no navegables
                if grid_x == 0 or grid_x >= self.grid_width - 1 or grid_y == 0 or grid_y >= self.grid_height - 1:
                    walkable = False
                
                # Racks como obstáculos (posiciones aproximadas)
                elif self.is_in_rack_area(world_x, world_y):
                    walkable = False
                
                row.append(1 if walkable else 0)
            
            matrix.append(row)
        
        self.matrix = matrix
        self.grid = Grid(matrix=matrix)
        
        # Estadísticas
        total_cells = self.grid_width * self.grid_height
        walkable_cells = sum(sum(row) for row in matrix)
        
        print(f"Grid creado: {total_cells} cells, {walkable_cells} navegables ({walkable_cells/total_cells*100:.1f}%)")
    
    def is_in_rack_area(self, world_x, world_y):
        """Determinar si una posición está en área de rack (obstáculo)"""
        
        # Solo obstáculos en la zona central donde están los racks
        if not (Y_PASILLO_SUPERIOR + 50 < world_y < Y_PASILLO_INFERIOR - 50):
            return False
        
        # Crear obstáculos cada cierta distancia (simulando racks)
        rack_spacing = 80  # Distancia entre racks en el grid
        rack_width = 30    # Ancho del obstáculo
        
        start_x = RACK_START_X
        
        for i in range(NUM_COLUMNAS_RACKS // 2):  # Menos racks para más navegabilidad
            rack_x = start_x + i * rack_spacing
            
            if rack_x <= world_x <= rack_x + rack_width:
                return True
        
        return False
    
    def world_to_grid(self, world_x, world_y):
        """Convertir coordenadas mundo a grid"""
        grid_x = int(world_x // self.tile_size)
        grid_y = int(world_y // self.tile_size)
        
        # Clamp
        grid_x = max(1, min(grid_x, self.grid_width - 2))
        grid_y = max(1, min(grid_y, self.grid_height - 2))
        
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x, grid_y):
        """Convertir grid a coordenadas mundo"""
        world_x = grid_x * self.tile_size + self.tile_size // 2
        world_y = grid_y * self.tile_size + self.tile_size // 2
        
        return world_x, world_y
    
    def find_nearest_walkable(self, grid_x, grid_y, radius=5):
        """Encontrar punto navegable más cercano"""
        
        for r in range(1, radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    x, y = grid_x + dx, grid_y + dy
                    
                    if (0 < x < self.grid_width - 1 and 0 < y < self.grid_height - 1 and 
                        self.matrix[y][x] == 1):
                        return x, y
        
        # Fallback: punto seguro en área central
        safe_x = self.grid_width // 2
        safe_y = self.grid_height // 2
        return safe_x, safe_y
    
    def calculate_route_enhanced(self, start_world, end_world):
        """Calcular ruta con manejo robusto de casos edge"""
        
        # Convertir a grid
        start_grid = self.world_to_grid(start_world[0], start_world[1])
        end_grid = self.world_to_grid(end_world[0], end_world[1])
        
        # Buscar puntos navegables si es necesario
        if self.matrix[start_grid[1]][start_grid[0]] == 0:
            start_grid = self.find_nearest_walkable(start_grid[0], start_grid[1])
            print(f"  Start ajustado a: {start_grid}")
        
        if self.matrix[end_grid[1]][end_grid[0]] == 0:
            end_grid = self.find_nearest_walkable(end_grid[0], end_grid[1])
            print(f"  End ajustado a: {end_grid}")
        
        # Limpiar y calcular
        self.grid.cleanup()
        
        start_node = self.grid.node(start_grid[0], start_grid[1])
        end_node = self.grid.node(end_grid[0], end_grid[1])
        
        path, runs = self.finder.find_path(start_node, end_node, self.grid)
        
        if path:
            # Convertir a coordenadas mundo
            world_path = []
            for node in path:
                world_pos = self.grid_to_world(node.x, node.y)
                world_path.append(world_pos)
            
            return world_path, runs
        else:
            return None, runs
    
    def test_realistic_pathfinding(self):
        """Test con casos realistas del simulador"""
        
        print(f"\n{'='*60}")
        print("TEST PATHFINDING MEJORADO")
        print("="*60)
        
        test_cases = [
            {
                "name": "Depot a Inbound",
                "start": POS_DEPOT,
                "end": POS_INBOUND
            },
            {
                "name": "Centro a esquina",
                "start": (ANCHO_PANTALLA//2, ALTO_PANTALLA//2),
                "end": (300, 200)
            },
            {
                "name": "Ruta corta horizontal",
                "start": (200, 300),
                "end": (600, 300)
            },
            {
                "name": "Ruta larga",
                "start": (150, 150),
                "end": (1500, 700)
            },
            {
                "name": "Ubicacion picking",
                "start": POS_DEPOT,
                "end": (ubicaciones_picking.obtener_todas_ubicaciones()[10])
            }
        ]
        
        successful = 0
        
        for i, case in enumerate(test_cases, 1):
            print(f"\nCaso {i}: {case['name']}")
            print(f"  Mundo: {case['start']} -> {case['end']}")
            
            try:
                world_path, runs = self.calculate_route_enhanced(case['start'], case['end'])
                
                if world_path:
                    successful += 1
                    distance = self.calculate_distance(world_path)
                    print(f"  [SUCCESS] {len(world_path)} puntos, {runs} nodos, {distance:.1f}px")
                    
                    if len(world_path) > 4:
                        print(f"    Ruta: {world_path[0]} -> ... -> {world_path[-1]}")
                    else:
                        print(f"    Ruta: {world_path}")
                else:
                    print(f"  [FAIL] Sin ruta ({runs} nodos explorados)")
                    
            except Exception as e:
                print(f"  [ERROR] {e}")
        
        success_rate = successful / len(test_cases) * 100
        
        print(f"\n{'='*60}")
        print(f"RESUMEN: {successful}/{len(test_cases)} exitosos ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("EXCELENTE - Grid calibrado correctamente")
            return True
        elif success_rate >= 60:
            print("BUENO - Grid funcional con ajustes menores")
            return True
        else:
            print("NECESITA MEJORAS - Grid requiere ajustes")
            return False
    
    def calculate_distance(self, world_path):
        """Calcular distancia total de ruta"""
        if len(world_path) < 2:
            return 0
        
        total = 0
        for i in range(1, len(world_path)):
            x1, y1 = world_path[i-1]
            x2, y2 = world_path[i]
            total += ((x2-x1)**2 + (y2-y1)**2)**0.5
        
        return total
    
    def create_replacement_function(self):
        """Crear función de reemplazo lista para usar"""
        
        replacement_code = f'''
def calcular_ruta_realista_mejorada(pos_actual, pos_destino, operario_id=None):
    """
    REEMPLAZO DIRECTO - Función mejorada usando pathfinding library
    Drop-in replacement para la función actual
    """
    global _calibrator_global
    if '_calibrator_global' not in globals():
        from improved_calibrator import ImprovedCalibrator
        _calibrator_global = ImprovedCalibrator()
    
    try:
        world_path, runs = _calibrator_global.calculate_route_enhanced(pos_actual, pos_destino)
        
        if world_path:
            print(f"[NEW PATHFINDING] Ruta: {{len(world_path)}} puntos, {{runs}} nodos")
            return world_path
        else:
            print(f"[FALLBACK] Sin ruta nueva, usando fallback")
            return [pos_actual, pos_destino]
    
    except Exception as e:
        print(f"[ERROR NEW PATHFINDING] {{e}}, usando fallback")
        return [pos_actual, pos_destino]
'''
        
        with open('pathfinding_replacement.py', 'w') as f:
            f.write(replacement_code)
        
        print(f"Función de reemplazo creada: pathfinding_replacement.py")

def main():
    """Ejecutar calibración mejorada"""
    print("="*70)
    print("CALIBRADOR MEJORADO - VERSION REALISTA")
    print("="*70)
    
    calibrator = ImprovedCalibrator()
    
    success = calibrator.test_realistic_pathfinding()
    
    if success:
        print("\nCALIBRACION EXITOSA!")
        print("Creando función de reemplazo...")
        calibrator.create_replacement_function()
        print("Listo para integración!")
    else:
        print("\nCALIBRACION NECESITA AJUSTES")
    
    return calibrator

if __name__ == "__main__":
    calibrator = main()