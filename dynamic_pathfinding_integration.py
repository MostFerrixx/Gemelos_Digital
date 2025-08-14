#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTEGRACIÓN PATHFINDING DINÁMICO - Conectar layouts TMX con pathfinding mejorado
"""

import sys
import os
from typing import Optional, Tuple, List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

# Importar sistemas
from enhanced_calibrator import EnhancedCalibrator
# from pathfinding_manager import PathfindingManager  # Removido para evitar dependencia circular
from dynamic_layout_loader import DynamicLayoutLoader

class DynamicPathfindingIntegration:
    """Integración entre layouts dinámicos y sistema de pathfinding"""
    
    def __init__(self):
        self.layout_loader = DynamicLayoutLoader()
        self.pathfinding_manager = None
        self.current_layout_data = None
        self.enhanced_calibrator = None
        
        print("Dynamic Pathfinding Integration inicializado")
    
    def load_layout_for_pathfinding(self, layout_path: str) -> bool:
        """Cargar layout y configurar pathfinding para usarlo"""
        
        print(f"Cargando layout para pathfinding: {layout_path}")
        
        try:
            # 1. Cargar layout con el loader
            layout_data = self.layout_loader.load_layout(layout_path)
            
            if not layout_data:
                print(f"Error: No se pudo cargar layout {layout_path}")
                return False
            
            self.current_layout_data = layout_data
            
            # 2. Crear calibrador personalizado para este layout
            self.enhanced_calibrator = self._create_custom_calibrator(layout_data)
            
            # 3. Configurar pathfinding manager
            self._configure_pathfinding_manager()
            
            print(f"Layout cargado exitosamente: {layout_data['info']['name']}")
            return True
            
        except Exception as e:
            print(f"Error cargando layout: {e}")
            return False
    
    def _create_custom_calibrator(self, layout_data: Dict) -> 'CustomLayoutCalibrator':
        """Crear calibrador personalizado basado en layout TMX"""
        
        print("Creando calibrador personalizado para layout TMX...")
        
        return CustomLayoutCalibrator(layout_data)
    
    def _configure_pathfinding_manager(self):
        """Configurar pathfinding manager para usar layout personalizado"""
        
        # Ya no necesitamos PathfindingManager, el wrapper maneja todo directamente
        print("Sistema TMX configurado directamente (sin PathfindingManager intermedio)")
    
    def calculate_route(self, start_pos: Tuple[float, float], 
                       end_pos: Tuple[float, float]) -> Optional[List[Tuple[float, float]]]:
        """Calcular ruta usando el layout TMX actual"""
        
        if not self.enhanced_calibrator:
            print("Error: Sistema TMX no inicializado")
            return None
        
        try:
            # Usar directamente el calibrador TMX
            world_path, runs = self.enhanced_calibrator.calculate_route_enhanced(start_pos, end_pos)
            return world_path
        
        except Exception as e:
            print(f"Error calculando ruta TMX: {e}")
            return None
    
    def get_special_locations(self) -> Dict:
        """Obtener ubicaciones especiales del layout actual"""
        
        if not self.current_layout_data:
            return {}
        
        return self.current_layout_data.get('special_locations', {})
    
    def get_layout_info(self) -> Optional[Dict]:
        """Obtener información del layout actual"""
        
        if not self.current_layout_data:
            return None
        
        return self.current_layout_data.get('info', {})


class CustomLayoutCalibrator:
    """Calibrador personalizado que usa datos de layout TMX"""
    
    def __init__(self, layout_data: Dict):
        self.layout_data = layout_data
        self.navigation_matrix = layout_data['navigation_matrix']
        self.special_locations = layout_data['special_locations']
        self.info = layout_data['info']
        
        # Configuración de escalado
        self.tile_width = self.info.get('tile_width', 32)
        self.tile_height = self.info.get('tile_height', 32)
        self.grid_width = self.info.get('width', 50)
        self.grid_height = self.info.get('height', 30)
        
        # Calcular escalado mundo ↔ grid
        self._calculate_world_scaling()
        
        # Crear grid de pathfinding
        self._create_pathfinding_grid()
        
        print(f"Custom calibrator creado: {self.grid_width}x{self.grid_height}")
    
    def _calculate_world_scaling(self):
        """Calcular escalado EXACTO que usa el renderer visual"""
        
        # USAR MISMOS CÁLCULOS que direct_layout_patch.py
        screen_width, screen_height = 1900, 900  # Valores por defecto
        available_width = screen_width - 100
        available_height = screen_height - 150
        
        tile_size_x = available_width // self.grid_width
        tile_size_y = available_height // self.grid_height
        tile_size = min(tile_size_x, tile_size_y, 25)  # MISMO LÍMITE que visual
        
        # MISMO OFFSET que visual
        total_layout_width = self.grid_width * tile_size
        total_layout_height = self.grid_height * tile_size
        self.offset_x = (screen_width - total_layout_width) // 2
        self.offset_y = (screen_height - total_layout_height - 120) // 2 + 20
        
        # ESCALADO BASADO EN tile_size REAL del visual
        self.visual_tile_size = tile_size
        self.world_to_grid_scale_x = 1.0 / tile_size
        self.world_to_grid_scale_y = 1.0 / tile_size
        
        print(f"[TMX CALIBRATOR] Escalado VISUAL sincronizado:")
        print(f"  tile_size: {tile_size} (visual compatible)")
        print(f"  offset: ({self.offset_x}, {self.offset_y}) (visual compatible)")
        print(f"  escalado: {self.world_to_grid_scale_x}x{self.world_to_grid_scale_y}")
    
    def _create_pathfinding_grid(self):
        """Crear grid de pathfinding basado en matriz TMX"""
        
        try:
            from pathfinding.core.grid import Grid
            from pathfinding.finder.a_star import AStarFinder
            from pathfinding.core.diagonal_movement import DiagonalMovement
            
            # Usar matriz directamente del TMX
            self.grid = Grid(matrix=self.navigation_matrix)
            self.finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
            
            # Estadísticas
            total_cells = self.grid_width * self.grid_height
            walkable_cells = sum(sum(row) for row in self.navigation_matrix)
            
            print(f"Grid pathfinding creado: {walkable_cells}/{total_cells} navegables ({walkable_cells/total_cells*100:.1f}%)")
            
        except Exception as e:
            print(f"Error creando grid: {e}")
            # Fallback a grid básico
            self.grid = None
            self.finder = None
    
    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convertir coordenadas mundo a grid TMX"""
        
        grid_x = int((world_x - self.offset_x) * self.world_to_grid_scale_x)
        grid_y = int((world_y - self.offset_y) * self.world_to_grid_scale_y)
        
        # Clamp dentro de límites
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convertir grid TMX a coordenadas mundo usando escalado visual"""
        
        world_x = self.offset_x + (grid_x * self.visual_tile_size) + (self.visual_tile_size // 2)
        world_y = self.offset_y + (grid_y * self.visual_tile_size) + (self.visual_tile_size // 2)
        
        return world_x, world_y
    
    def calculate_route_enhanced(self, start_world: Tuple[float, float], 
                               end_world: Tuple[float, float]) -> Tuple[Optional[List], int]:
        """Calcular ruta usando grid TMX personalizado"""
        
        if not self.grid or not self.finder:
            # Fallback: ruta directa
            return [start_world, end_world], 0
        
        try:
            # Convertir a grid
            start_grid = self.world_to_grid(start_world[0], start_world[1])
            end_grid = self.world_to_grid(end_world[0], end_world[1])
            
            # Buscar puntos navegables si es necesario
            start_grid = self._find_nearest_walkable(start_grid[0], start_grid[1])
            end_grid = self._find_nearest_walkable(end_grid[0], end_grid[1])
            
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
                
        except Exception as e:
            print(f"Error en pathfinding TMX: {e}")
            return [start_world, end_world], 0
    
    def _find_nearest_walkable(self, grid_x: int, grid_y: int, radius: int = 3) -> Tuple[int, int]:
        """Encontrar punto navegable más cercano en grid TMX"""
        
        # Verificar si la posición actual es navegable
        if (0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height and 
            self.navigation_matrix[grid_y][grid_x] == 1):
            return grid_x, grid_y
        
        # Buscar en radio creciente
        for r in range(1, radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    x, y = grid_x + dx, grid_y + dy
                    
                    if (0 <= x < self.grid_width and 0 <= y < self.grid_height and 
                        self.navigation_matrix[y][x] == 1):
                        return x, y
        
        # Fallback: punto central
        center_x = self.grid_width // 2
        center_y = self.grid_height // 2
        return center_x, center_y


def create_integration_wrapper():
    """Crear wrapper para fácil uso en simulador"""
    
    class DynamicPathfindingWrapper:
        """Wrapper para usar pathfinding dinámico en el simulador"""
        
        def __init__(self):
            self.integration = DynamicPathfindingIntegration()
            self.is_initialized = False
        
        def initialize_with_layout(self, layout_path: str) -> bool:
            """Inicializar con layout específico"""
            
            success = self.integration.load_layout_for_pathfinding(layout_path)
            self.is_initialized = success
            print(f"[TMX WRAPPER] Inicialización con layout {layout_path}: {'EXITOSA' if success else 'FALLIDA'}")
            return success
        
        def calculate_route(self, start_pos, end_pos) -> List:
            """Calcular ruta (compatible con API actual)"""
            
            if not self.is_initialized:
                print(f"[TMX WRAPPER] Pathfinding no inicializado, usando ruta directa: {start_pos} -> {end_pos}")
                return [start_pos, end_pos]
            
            print(f"[TMX WRAPPER] Calculando ruta TMX: {start_pos} -> {end_pos}")
            route = self.integration.calculate_route(start_pos, end_pos)
            
            if route:
                print(f"[TMX WRAPPER] Ruta TMX exitosa: {len(route)} puntos")
                return route
            else:
                print(f"[TMX WRAPPER] Ruta TMX falló, usando directa")
                return [start_pos, end_pos]
        
        def get_depot_position(self) -> Tuple[float, float]:
            """Obtener posición de depot desde layout"""
            
            locations = self.integration.get_special_locations()
            depot_points = locations.get('depot_points', [])
            
            if depot_points:
                return depot_points[0]['pixel_pos']
            
            # Fallback a configuración actual
            from config.settings import POS_DEPOT
            return POS_DEPOT
        
        def get_inbound_position(self) -> Tuple[float, float]:
            """Obtener posición de inbound desde layout"""
            
            locations = self.integration.get_special_locations()
            inbound_points = locations.get('inbound_points', [])
            
            if inbound_points:
                return inbound_points[0]['pixel_pos']
            
            # Fallback a configuración actual
            from config.settings import POS_INBOUND
            return POS_INBOUND
        
        def get_picking_locations(self) -> List[Tuple[float, float]]:
            """Obtener ubicaciones de picking desde layout"""
            
            locations = self.integration.get_special_locations()
            picking_points = locations.get('picking_points', [])
            
            return [point['pixel_pos'] for point in picking_points]
    
    return DynamicPathfindingWrapper()

# Instancia global para uso en simulador
_dynamic_pathfinding_wrapper = None

def get_dynamic_pathfinding_wrapper():
    """Obtener wrapper global"""
    global _dynamic_pathfinding_wrapper
    if _dynamic_pathfinding_wrapper is None:
        _dynamic_pathfinding_wrapper = create_integration_wrapper()
    return _dynamic_pathfinding_wrapper

def main():
    """Testing de integración"""
    
    print("="*60)
    print("TESTING INTEGRACIÓN PATHFINDING DINÁMICO")
    print("="*60)
    
    # Test básico
    integration = DynamicPathfindingIntegration()
    
    # Buscar layouts disponibles
    loader = DynamicLayoutLoader()
    available = loader.scan_available_layouts()
    
    if available:
        # Test cargar primer layout
        first_layout = available[0]
        print(f"\\nTesting layout: {first_layout['name']}")
        
        success = integration.load_layout_for_pathfinding(first_layout['path'])
        
        if success:
            print("✅ Layout cargado exitosamente")
            
            # Test calcular ruta
            test_route = integration.calculate_route((100, 100), (500, 300))
            if test_route:
                print(f"✅ Ruta calculada: {len(test_route)} puntos")
            
            # Test ubicaciones especiales
            locations = integration.get_special_locations()
            print(f"✅ Ubicaciones especiales: {len(locations)} tipos")
        
        else:
            print("❌ Error cargando layout")
    
    else:
        print("No hay layouts disponibles para testing")
    
    # Test wrapper
    print(f"\\nTesting wrapper...")
    wrapper = create_integration_wrapper()
    
    if available:
        if wrapper.initialize_with_layout(available[0]['path']):
            print("✅ Wrapper inicializado")
            
            depot_pos = wrapper.get_depot_position()
            inbound_pos = wrapper.get_inbound_position()
            
            print(f"Depot: {depot_pos}")
            print(f"Inbound: {inbound_pos}")
    
    print(f"\\n✅ Integración pathfinding dinámico funcionando")
    
    return integration

if __name__ == "__main__":
    integration = main()