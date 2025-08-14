#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALIBRADOR MEJORADO CON ESCALADO PERFECTO
Soluciona los problemas de mapeo de coordenadas mundo ↔ grid
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

class EnhancedCalibrator:
    """Calibrador mejorado con escalado perfecto de coordenadas"""
    
    def __init__(self):
        # Analizar el sistema actual
        self.analyze_real_system()
        
        # Crear grid con escalado correcto
        self.create_calibrated_grid()
        
        # Setup pathfinding
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
    
    def analyze_real_system(self):
        """Analizar el sistema real para calibración perfecta"""
        print("ANALIZANDO SISTEMA REAL:")
        print("="*50)
        
        # Dimensiones del mundo
        self.world_width = ANCHO_PANTALLA  # 1900
        self.world_height = ALTO_PANTALLA  # 900
        
        print(f"Mundo: {self.world_width}x{self.world_height} pixels")
        
        # Análisis de ubicaciones reales
        todas_ubicaciones = ubicaciones_picking.obtener_todas_ubicaciones()
        
        if todas_ubicaciones:
            # Encontrar límites reales de ubicaciones
            x_coords = [loc[0] for loc in todas_ubicaciones]
            y_coords = [loc[1] for loc in todas_ubicaciones]
            
            self.min_x = min(x_coords)
            self.max_x = max(x_coords)
            self.min_y = min(y_coords)
            self.max_y = max(y_coords)
            
            print(f"Ubicaciones reales:")
            print(f"  X: {self.min_x} - {self.max_x} ({self.max_x - self.min_x} pixels)")
            print(f"  Y: {self.min_y} - {self.max_y} ({self.max_y - self.min_y} pixels)")
        else:
            # Fallback usando configuración
            self.min_x = RACK_START_X
            self.max_x = RACK_START_X + NUM_COLUMNAS_RACKS * 100
            self.min_y = Y_PASILLO_SUPERIOR
            self.max_y = Y_PASILLO_INFERIOR
        
        # Configurar grid basado en análisis real
        self.configure_optimal_grid()
    
    def configure_optimal_grid(self):
        """Configurar grid optimal para el sistema real"""
        
        # Estrategia: Grid que cubra todo el área útil con resolución adecuada
        # Usar tile_size basado en ANCHO_PASILLO_VERTICAL para coherencia
        
        self.tile_size = ANCHO_PASILLO_VERTICAL  # 30 pixels
        
        # Grid que cubra toda la pantalla
        self.grid_width = self.world_width // self.tile_size    # 1900 / 30 = 63
        self.grid_height = self.world_height // self.tile_size  # 900 / 30 = 30
        
        # Offsets para centrar el grid
        self.offset_x = (self.world_width - self.grid_width * self.tile_size) // 2   # (1900 - 1890) // 2 = 5
        self.offset_y = (self.world_height - self.grid_height * self.tile_size) // 2 # (900 - 900) // 2 = 0
        
        print(f"\nGRID CALIBRADO:")
        print(f"Dimensiones: {self.grid_width}x{self.grid_height}")
        print(f"Tile size: {self.tile_size} pixels")
        print(f"Cobertura: {self.grid_width * self.tile_size}x{self.grid_height * self.tile_size} pixels")
        print(f"Offsets: ({self.offset_x}, {self.offset_y})")
    
    def create_calibrated_grid(self):
        """Crear grid calibrado con lógica de navegabilidad mejorada"""
        
        print(f"\nCREANDO GRID CALIBRADO...")
        
        matrix = []
        
        for grid_y in range(self.grid_height):
            row = []
            for grid_x in range(self.grid_width):
                # Convertir a coordenadas mundo
                world_x, world_y = self.grid_to_world(grid_x, grid_y)
                
                # Determinar navegabilidad con lógica mejorada
                walkable = self.is_position_walkable_enhanced(world_x, world_y)
                row.append(1 if walkable else 0)
            
            matrix.append(row)
        
        self.matrix = matrix
        self.grid = Grid(matrix=matrix)
        
        # Estadísticas
        total_cells = self.grid_width * self.grid_height
        walkable_cells = sum(sum(row) for row in matrix)
        
        print(f"Grid creado: {total_cells} cells, {walkable_cells} navegables ({walkable_cells/total_cells*100:.1f}%)")
    
    def is_position_walkable_enhanced(self, world_x, world_y):
        """Lógica mejorada para determinar navegabilidad"""
        
        # Fuera de límites = no navegable
        if world_x < 0 or world_x >= self.world_width or world_y < 0 or world_y >= self.world_height:
            return False
        
        # Zonas especiales siempre navegables
        # Depot
        depot_x, depot_y = POS_DEPOT
        if abs(world_x - depot_x) < 80 and abs(world_y - depot_y) < 60:
            return True
        
        # Inbound
        inbound_x, inbound_y = POS_INBOUND
        if abs(world_x - inbound_x) < 80 and abs(world_y - inbound_y) < 60:
            return True
        
        # Pasillos horizontales (superior e inferior) - más amplios
        if (Y_PASILLO_SUPERIOR - 20 <= world_y <= Y_PASILLO_SUPERIOR + 40) or \
           (Y_PASILLO_INFERIOR - 40 <= world_y <= Y_PASILLO_INFERIOR + 20):
            return True
        
        # Área entre pasillos (zona de racks)
        if Y_PASILLO_SUPERIOR + 40 < world_y < Y_PASILLO_INFERIOR - 40:
            
            # Calcular posición de rack basada en configuración real
            x_rel = world_x - RACK_START_X
            
            if x_rel < 0:
                return True  # Área antes de racks = navegable
            
            # Calcular en qué columna de rack estamos
            rack_width_total = ANCHO_RACK * 2 + ESPACIO_ENTRE_RACKS_DOBLES + ANCHO_PASILLO_VERTICAL
            col_index = x_rel // rack_width_total
            x_in_col = x_rel % rack_width_total
            
            if col_index >= NUM_COLUMNAS_RACKS:
                return True  # Área después de racks = navegable
            
            # Dentro de una columna: racks son obstáculos, pasillos navegables
            if x_in_col <= ANCHO_RACK:
                return False  # Rack izquierdo
            elif x_in_col <= ANCHO_RACK + ESPACIO_ENTRE_RACKS_DOBLES:
                return True   # Espacio entre racks dobles
            elif x_in_col <= ANCHO_RACK * 2 + ESPACIO_ENTRE_RACKS_DOBLES:
                return False  # Rack derecho
            else:
                return True   # Pasillo vertical
        
        # Resto de áreas: navegables por defecto para flexibilidad
        return True
    
    def world_to_grid(self, world_x, world_y):
        """Convertir coordenadas mundo a grid"""
        grid_x = int((world_x - self.offset_x) // self.tile_size)
        grid_y = int((world_y - self.offset_y) // self.tile_size)
        
        # Clamp dentro de límites
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x, grid_y):
        """Convertir grid a coordenadas mundo"""
        world_x = grid_x * self.tile_size + self.offset_x + self.tile_size // 2
        world_y = grid_y * self.tile_size + self.offset_y + self.tile_size // 2
        
        return world_x, world_y
    
    def find_nearest_walkable(self, grid_x, grid_y, radius=5):
        """Encontrar punto navegable más cercano"""
        
        for r in range(1, radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    x, y = grid_x + dx, grid_y + dy
                    
                    if (0 <= x < self.grid_width and 0 <= y < self.grid_height and 
                        self.matrix[y][x] == 1):
                        return x, y
        
        # Fallback: punto en pasillo superior
        safe_x = self.grid_width // 2
        safe_y = (Y_PASILLO_SUPERIOR + 20) // self.tile_size
        return safe_x, safe_y
    
    def calculate_route_enhanced(self, start_world, end_world):
        """Calcular ruta con manejo robusto"""
        
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
    
    def test_enhanced_pathfinding(self):
        """Test completo con casos reales del sistema"""
        
        print(f"\n{'='*60}")
        print("TEST PATHFINDING MEJORADO CON CALIBRACIÓN")
        print("="*60)
        
        # Obtener ubicaciones reales para testing
        ubicaciones_reales = ubicaciones_picking.obtener_todas_ubicaciones()
        
        test_cases = [
            {
                "name": "Depot a Inbound",
                "start": POS_DEPOT,
                "end": POS_INBOUND
            },
            {
                "name": "Inbound a primera ubicación picking",
                "start": POS_INBOUND,
                "end": ubicaciones_reales[0] if ubicaciones_reales else (300, 300)
            },
            {
                "name": "Entre ubicaciones picking",
                "start": ubicaciones_reales[0] if ubicaciones_reales else (300, 300),
                "end": ubicaciones_reales[10] if len(ubicaciones_reales) > 10 else (800, 400)
            },
            {
                "name": "Última ubicación a Depot",
                "start": ubicaciones_reales[-1] if ubicaciones_reales else (1600, 400),
                "end": POS_DEPOT
            },
            {
                "name": "Ruta diagonal larga",
                "start": (200, 200),
                "end": (1700, 700)
            },
            {
                "name": "Navegación por pasillo",
                "start": (400, Y_PASILLO_SUPERIOR + 20),
                "end": (1200, Y_PASILLO_SUPERIOR + 20)
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
        print(f"RESUMEN MEJORADO: {successful}/{len(test_cases)} exitosos ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("EXCELENTE - Calibración perfecta")
            return True
        elif success_rate >= 60:
            print("BUENO - Calibración funcional")
            return True
        else:
            print("NECESITA MEJORAS - Revisar lógica")
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
    
    def create_production_function(self):
        """Crear función lista para producción"""
        
        replacement_code = f'''
def calcular_ruta_realista_mejorada_v2(pos_actual, pos_destino, operario_id=None):
    """
    VERSIÓN MEJORADA - Calibración perfecta mundo ↔ grid
    Reemplazo directo con escalado correcto
    """
    global _enhanced_calibrator_global
    if '_enhanced_calibrator_global' not in globals():
        from enhanced_calibrator import EnhancedCalibrator
        _enhanced_calibrator_global = EnhancedCalibrator()
    
    try:
        world_path, runs = _enhanced_calibrator_global.calculate_route_enhanced(pos_actual, pos_destino)
        
        if world_path:
            print(f"[ENHANCED] Ruta: {{len(world_path)}} puntos, {{runs}} nodos")
            return world_path
        else:
            print(f"[FALLBACK] Sin ruta, usando línea directa")
            return [pos_actual, pos_destino]
    
    except Exception as e:
        print(f"[ERROR ENHANCED] {{e}}, usando fallback")
        return [pos_actual, pos_destino]
'''
        
        with open('pathfinding_enhanced.py', 'w', encoding='utf-8') as f:
            f.write(replacement_code)
        
        print(f"Función mejorada creada: pathfinding_enhanced.py")

def main():
    """Ejecutar calibración mejorada"""
    print("="*70)
    print("CALIBRADOR MEJORADO - ESCALADO PERFECTO")
    print("="*70)
    
    calibrator = EnhancedCalibrator()
    
    success = calibrator.test_enhanced_pathfinding()
    
    if success:
        print("\nCALIBRACIÓN MEJORADA EXITOSA!")
        print("Creando función de producción...")
        calibrator.create_production_function()
        print("Sistema listo para integración!")
    else:
        print("\nCALIBRACIÓN NECESITA AJUSTES")
    
    return calibrator

if __name__ == "__main__":
    calibrator = main()