#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALIBRADOR DE COORDENADAS - Mapeo perfecto mundo real ↔ grid pathfinding
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

import pygame
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

# Importar configuración actual
from config.settings import *
from utils.ubicaciones_picking import ubicaciones_picking

class CoordinateCalibrator:
    """Calibrador para mapeo perfecto entre coordenadas del mundo y grid pathfinding"""
    
    def __init__(self):
        # Configuración del mundo actual
        self.world_width = ANCHO_PANTALLA
        self.world_height = ALTO_PANTALLA
        
        # Análisis del layout actual
        self.analyze_current_layout()
        
        # Crear grid de pathfinding optimizado
        self.create_optimized_grid()
        
        # Setup pathfinding
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
    
    def analyze_current_layout(self):
        """Analizar el layout actual para crear mapeo perfecto"""
        print("ANALIZANDO LAYOUT ACTUAL:")
        print("="*50)
        
        # Dimensiones del mundo
        print(f"Mundo: {self.world_width}x{self.world_height} pixels")
        
        # Análisis de racks
        print(f"Racks: {NUM_COLUMNAS_RACKS} columnas")
        print(f"Rack width: {ANCHO_RACK} pixels")
        print(f"Espacio entre racks: {ESPACIO_ENTRE_RACKS_DOBLES} pixels")
        print(f"Rack start X: {RACK_START_X}")
        
        # Análisis de pasillos
        pasillo_height = Y_PASILLO_INFERIOR - Y_PASILLO_SUPERIOR
        print(f"Pasillos Y: {Y_PASILLO_SUPERIOR} - {Y_PASILLO_INFERIOR} ({pasillo_height} pixels)")
        print(f"Ancho pasillo vertical: {ANCHO_PASILLO_VERTICAL} pixels")
        
        # Análisis de ubicaciones de picking
        stats = ubicaciones_picking.obtener_estadisticas()
        print(f"Ubicaciones picking: {stats['total_ubicaciones']}")
        
        # Calcular dimensiones óptimas del grid
        self.calculate_optimal_grid_size()
    
    def calculate_optimal_grid_size(self):
        """Calcular tamaño óptimo del grid para mapeo perfecto"""
        
        # Estrategia: 1 tile del grid = 1 zona de movimiento mínima
        # Basado en ANCHO_PASILLO_VERTICAL como unidad mínima
        
        tile_size = ANCHO_PASILLO_VERTICAL  # 30 pixels por tile
        
        self.grid_width = self.world_width // tile_size
        self.grid_height = self.world_height // tile_size
        
        self.tile_size = tile_size
        
        print(f"\nGRID OPTIMIZADO:")
        print(f"Tiles: {self.grid_width}x{self.grid_height}")
        print(f"Tile size: {self.tile_size} pixels")
        print(f"Cobertura: {self.grid_width * self.tile_size}x{self.grid_height * self.tile_size} pixels")
        
        # Calcular offsets para centrar
        self.offset_x = (self.world_width - self.grid_width * self.tile_size) // 2
        self.offset_y = (self.world_height - self.grid_height * self.tile_size) // 2
        
        print(f"Offsets: ({self.offset_x}, {self.offset_y})")
    
    def create_optimized_grid(self):
        """Crear grid de pathfinding que mapea perfectamente el almacén actual"""
        
        print(f"\nCREANDO GRID OPTIMIZADO...")
        
        matrix = []
        
        for grid_y in range(self.grid_height):
            row = []
            for grid_x in range(self.grid_width):
                # Convertir coordenadas de grid a mundo
                world_x, world_y = self.grid_to_world(grid_x, grid_y)
                
                # Determinar si esta posición es navegable
                walkable = self.is_position_walkable(world_x, world_y)
                row.append(1 if walkable else 0)
            
            matrix.append(row)
        
        self.matrix = matrix
        self.grid = Grid(matrix=matrix)
        
        # Estadísticas
        total_cells = self.grid_width * self.grid_height
        walkable_cells = sum(sum(row) for row in matrix)
        
        print(f"Grid creado: {total_cells} cells, {walkable_cells} navegables ({walkable_cells/total_cells*100:.1f}%)")
    
    def is_position_walkable(self, world_x, world_y):
        """Determinar si una posición del mundo es navegable"""
        
        # Fuera de límites = no navegable
        if world_x < 0 or world_x >= self.world_width or world_y < 0 or world_y >= self.world_height:
            return False
        
        # Zonas especiales navegables
        # Depot
        depot_x, depot_y = POS_DEPOT
        if abs(world_x - depot_x) < 100 and abs(world_y - depot_y) < 50:
            return True
        
        # Inbound
        inbound_x, inbound_y = POS_INBOUND
        if abs(world_x - inbound_x) < 100 and abs(world_y - inbound_y) < 50:
            return True
        
        # Pasillos horizontales
        if Y_PASILLO_SUPERIOR <= world_y <= Y_PASILLO_SUPERIOR + 30:
            return True  # Pasillo H1
        if Y_PASILLO_INFERIOR - 30 <= world_y <= Y_PASILLO_INFERIOR:
            return True  # Pasillo H2
        
        # Área principal de trabajo (entre pasillos)
        if Y_PASILLO_SUPERIOR + 30 < world_y < Y_PASILLO_INFERIOR - 30:
            # Verificar si está en un pasillo vertical
            for col in range(NUM_COLUMNAS_RACKS - 1):
                rack_x_end = RACK_START_X + col * (ANCHO_RACK * 2 + ESPACIO_ENTRE_RACKS_DOBLES + ANCHO_PASILLO_VERTICAL)
                pasillo_x_start = rack_x_end + ANCHO_RACK * 2 + ESPACIO_ENTRE_RACKS_DOBLES
                pasillo_x_end = pasillo_x_start + ANCHO_PASILLO_VERTICAL
                
                if pasillo_x_start <= world_x <= pasillo_x_end:
                    return True  # En pasillo vertical
            
            # Verificar si está en zona de picking (cerca de racks pero no dentro)
            rack_area = False
            for col in range(NUM_COLUMNAS_RACKS):
                rack_x = RACK_START_X + col * (ANCHO_RACK * 2 + ESPACIO_ENTRE_RACKS_DOBLES + ANCHO_PASILLO_VERTICAL)
                
                # Rack izquierdo
                if rack_x <= world_x <= rack_x + ANCHO_RACK:
                    rack_area = True
                    break
                
                # Rack derecho  
                rack_der_x = rack_x + ANCHO_RACK + ESPACIO_ENTRE_RACKS_DOBLES
                if rack_der_x <= world_x <= rack_der_x + ANCHO_RACK:
                    rack_area = True
                    break
            
            # Si está en área de rack, no navegable (excepto zonas de picking específicas)
            if rack_area:
                return False
            
            # Resto del área principal = navegable
            return True
        
        # Por defecto = no navegable
        return False
    
    def world_to_grid(self, world_x, world_y):
        """Convertir coordenadas del mundo a grid"""
        grid_x = int((world_x - self.offset_x) // self.tile_size)
        grid_y = int((world_y - self.offset_y) // self.tile_size)
        
        # Clamp dentro de límites
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x, grid_y):
        """Convertir coordenadas de grid a mundo"""
        world_x = grid_x * self.tile_size + self.offset_x + self.tile_size // 2
        world_y = grid_y * self.tile_size + self.offset_y + self.tile_size // 2
        
        return world_x, world_y
    
    def test_pathfinding_with_real_coordinates(self):
        """Probar pathfinding con coordenadas reales del simulador"""
        
        print(f"\n{'='*60}")
        print("TESTING PATHFINDING CON COORDENADAS REALES")
        print("="*60)
        
        # Casos de prueba con coordenadas típicas del simulador
        test_cases = [
            {
                "name": "Depot a Inbound",
                "start": POS_DEPOT,
                "end": POS_INBOUND
            },
            {
                "name": "Inbound a zona de racks",
                "start": POS_INBOUND,
                "end": (500, 300)
            },
            {
                "name": "Navegación entre racks",
                "start": (300, 350),
                "end": (800, 350)
            },
            {
                "name": "Ruta larga diagonal",
                "start": (200, 200),
                "end": (1500, 500)
            },
            {
                "name": "Ubicación de picking real",
                "start": POS_DEPOT,
                "end": (ubicaciones_picking.obtener_todas_ubicaciones()[0])
            }
        ]
        
        successful_routes = 0
        
        for i, case in enumerate(test_cases, 1):
            print(f"\nCaso {i}: {case['name']}")
            print(f"  Mundo: {case['start']} -> {case['end']}")
            
            # Convertir a grid
            start_grid = self.world_to_grid(case['start'][0], case['start'][1])
            end_grid = self.world_to_grid(case['end'][0], case['end'][1])
            
            print(f"  Grid: {start_grid} -> {end_grid}")
            
            # Verificar navegabilidad
            start_walkable = self.matrix[start_grid[1]][start_grid[0]]
            end_walkable = self.matrix[end_grid[1]][end_grid[0]]
            
            print(f"  Navegable: start={bool(start_walkable)}, end={bool(end_walkable)}")
            
            if not start_walkable or not end_walkable:
                print("  [SKIP] Puntos no navegables")
                continue
            
            # Calcular ruta
            self.grid.cleanup()
            start_node = self.grid.node(start_grid[0], start_grid[1])
            end_node = self.grid.node(end_grid[0], end_grid[1])
            
            path, runs = self.finder.find_path(start_node, end_node, self.grid)
            
            if path:
                successful_routes += 1
                
                # Convertir ruta de vuelta a coordenadas mundo
                world_path = []
                for node in path:
                    world_pos = self.grid_to_world(node.x, node.y)
                    world_path.append(world_pos)
                
                print(f"  [SUCCESS] Ruta: {len(world_path)} puntos, {runs} nodos explorados")
                
                # Mostrar algunos puntos de la ruta
                if len(world_path) > 6:
                    print(f"  Ruta: {world_path[0]} -> ... -> {world_path[-1]}")
                else:
                    print(f"  Ruta completa: {world_path}")
                
                # Análisis de la ruta
                total_distance = self.calculate_route_distance(world_path)
                print(f"  Distancia total: {total_distance:.1f} pixels")
                
            else:
                print(f"  [FAIL] Sin ruta ({runs} nodos explorados)")
        
        print(f"\n{'='*60}")
        print(f"RESUMEN: {successful_routes}/{len(test_cases)} rutas exitosas")
        print(f"Tasa de éxito: {successful_routes/len(test_cases)*100:.1f}%")
        
        if successful_routes >= len(test_cases) * 0.8:  # 80% éxito
            print("✅ CALIBRACIÓN EXITOSA - Grid optimizado funcionando")
            return True
        else:
            print("⚠️ CALIBRACIÓN NECESITA AJUSTES")
            return False
    
    def calculate_route_distance(self, world_path):
        """Calcular distancia total de una ruta en coordenadas mundo"""
        if len(world_path) < 2:
            return 0
        
        total_distance = 0
        for i in range(1, len(world_path)):
            x1, y1 = world_path[i-1]
            x2, y2 = world_path[i]
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            total_distance += distance
        
        return total_distance
    
    def visualize_grid(self, output_file="grid_visualization.txt"):
        """Crear visualización ASCII del grid calibrado"""
        
        print(f"\nCreando visualización del grid: {output_file}")
        
        with open(output_file, 'w') as f:
            f.write("GRID CALIBRADO - ALMACÉN DIGITAL TWIN\n")
            f.write("="*50 + "\n")
            f.write(f"Dimensiones: {self.grid_width}x{self.grid_height}\n")
            f.write(f"Tile size: {self.tile_size} pixels\n")
            f.write("Leyenda: . = navegable, # = obstáculo\n")
            f.write("\n")
            
            # Números de columna
            f.write("   ")
            for x in range(min(self.grid_width, 100)):  # Limitar para legibilidad
                f.write(str(x % 10))
            f.write("\n")
            
            # Filas del grid
            for y in range(min(self.grid_height, 50)):  # Limitar para legibilidad
                f.write(f"{y:2d} ")
                for x in range(min(self.grid_width, 100)):
                    if self.matrix[y][x] == 1:
                        f.write(".")
                    else:
                        f.write("#")
                f.write(f" {y}\n")
        
        print(f"Visualización guardada en {output_file}")

def main():
    """Ejecutar calibración completa"""
    print("="*70)
    print("CALIBRADOR DE COORDENADAS - INTEGRACIÓN COMPLETA")
    print("="*70)
    
    calibrator = CoordinateCalibrator()
    
    # Probar pathfinding con coordenadas reales
    success = calibrator.test_pathfinding_with_real_coordinates()
    
    # Crear visualización
    calibrator.visualize_grid()
    
    if success:
        print("\n🎉 CALIBRACIÓN COMPLETADA EXITOSAMENTE")
        print("✅ Grid optimizado listo para integración")
        print("✅ Mapeo mundo ↔ grid funcionando perfectamente")
    else:
        print("\n⚠️ CALIBRACIÓN NECESITA AJUSTES")
        print("🔧 Revisar lógica de navegabilidad")
    
    return calibrator

if __name__ == "__main__":
    calibrator = main()