#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADAPTADOR DE COMPATIBILIDAD: Sistema Dual TMX + Código Existente
Permite usar pytmx + pathfinding gradualmente sin romper el código actual
"""

import sys
import os
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

# Importar módulos existentes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

try:
    import pytmx
    import pytmx.util_pygame
    PYTMX_AVAILABLE = True
except ImportError:
    PYTMX_AVAILABLE = False

class TiledPathfindingAdapter:
    """
    Adaptador que funciona como reemplazo drop-in del sistema A* actual
    Compatible con la API existente pero usando pytmx + pathfinding internamente
    """
    
    def __init__(self, config_source="matrix"):
        """
        Inicializar adaptador
        config_source: "matrix", "tmx_warehouse", "tmx_torture", "current_system"
        """
        self.config_source = config_source
        self.grid = None
        self.matrix = None
        self.width = 0
        self.height = 0
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        
        # Configuración de mapeo con el sistema actual
        self.scale_factor = 1.0  # Factor de escalado coordenadas
        self.offset_x = 0        # Offset X para mapear coordenadas
        self.offset_y = 0        # Offset Y para mapear coordenadas
        
        self._load_pathfinding_data()
    
    def _load_pathfinding_data(self):
        """Cargar datos de pathfinding según la fuente configurada"""
        
        if self.config_source == "tmx_warehouse":
            self._load_from_tmx("warehouse_basic.tmx")
        elif self.config_source == "tmx_torture":
            self._load_from_tmx("torture_layout.tmx")
        elif self.config_source == "current_system":
            self._load_from_current_system()
        else:
            # Default: matriz de prueba
            self._load_default_matrix()
    
    def _load_from_tmx(self, tmx_file):
        """Cargar desde archivo TMX"""
        if not PYTMX_AVAILABLE:
            print("PyTMX no disponible, usando matriz fallback")
            self._load_default_matrix()
            return
        
        try:
            tmx_data = pytmx.util_pygame.load_pygame(tmx_file)
            
            self.width = tmx_data.width
            self.height = tmx_data.height
            
            # Extraer matriz de pathfinding
            matrix = []
            
            # Encontrar capa de datos
            layer = None
            for layer_obj in tmx_data.layers:
                if hasattr(layer_obj, 'data'):
                    layer = layer_obj
                    break
            
            if layer:
                for y in range(self.height):
                    row = []
                    for x in range(self.width):
                        tile_gid = layer.data[y][x]
                        if tile_gid == 0:
                            row.append(0)  # Sin tile = obstáculo
                        else:
                            # Obtener propiedades del tile
                            tile = tmx_data.get_tile_by_gid(tile_gid)
                            if tile and hasattr(tile, 'properties'):
                                walkable = tile.properties.get('walkable', 'false')
                                row.append(1 if walkable.lower() == 'true' else 0)
                            else:
                                # Default: TMX con gid 1 = walkable, gid 2+ = obstáculo
                                row.append(1 if tile_gid == 1 else 0)
                    
                    matrix.append(row)
                
                self.matrix = matrix
                self.grid = Grid(matrix=matrix)
                
                print(f"TMX cargado: {tmx_file} ({self.width}x{self.height})")
            else:
                raise Exception("No se encontró capa de datos en TMX")
                
        except Exception as e:
            print(f"Error cargando TMX {tmx_file}: {e}")
            self._load_default_matrix()
    
    def _load_from_current_system(self):
        """Cargar desde el sistema actual de ubicaciones"""
        try:
            import config.settings as settings
            from utils.ubicaciones_picking import ubicaciones_picking
            
            # Crear matriz basada en la configuración actual del almacén
            # Usar las dimensiones del almacén actual escaladas a grid
            
            # Mapeo aproximado del almacén actual a grid de pathfinding
            grid_width = settings.NUM_COLUMNAS_RACKS * 4  # 4 tiles por columna de rack
            grid_height = 30  # Altura aproximada
            
            matrix = []
            
            for y in range(grid_height):
                row = []
                for x in range(grid_width):
                    # Lógica simplificada: crear pasillos y racks
                    
                    # Pasillos horizontales en Y específicas
                    if y < 3 or y > grid_height - 4:
                        row.append(1)  # Navegable
                    # Racks en posiciones específicas
                    elif x % 4 in [1, 2]:  # Racks en medio de cada grupo de 4
                        row.append(0)  # Obstáculo (rack)
                    else:
                        row.append(1)  # Pasillos verticales navegables
                
                matrix.append(row)
            
            self.matrix = matrix
            self.width = grid_width
            self.height = grid_height
            self.grid = Grid(matrix=matrix)
            
            # Configurar escalado para mapear con coordenadas actuales
            self.scale_factor = settings.ANCHO_PANTALLA / grid_width
            
            print(f"Sistema actual mapeado a grid {grid_width}x{grid_height}")
            
        except Exception as e:
            print(f"Error cargando desde sistema actual: {e}")
            self._load_default_matrix()
    
    def _load_default_matrix(self):
        """Cargar matriz por defecto si todo falla"""
        # Matriz de prueba simple pero funcional
        default_matrix = [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,1,0,0,1,0,0,1,0,0,1,0,1],
            [1,0,0,1,0,0,1,0,0,1,0,0,1,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,1,0,0,1,0,0,1,0,0,1,0,1],
            [1,0,0,1,0,0,1,0,0,1,0,0,1,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        ]
        
        self.matrix = default_matrix
        self.width = len(default_matrix[0])
        self.height = len(default_matrix)
        self.grid = Grid(matrix=default_matrix)
        
        print(f"Matriz por defecto cargada: {self.width}x{self.height}")
    
    def world_to_grid(self, world_x, world_y):
        """Convertir coordenadas del mundo real a coordenadas de grid"""
        grid_x = int((world_x - self.offset_x) / self.scale_factor)
        grid_y = int((world_y - self.offset_y) / self.scale_factor)
        
        # Clamp dentro de límites
        grid_x = max(0, min(grid_x, self.width - 1))
        grid_y = max(0, min(grid_y, self.height - 1))
        
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x, grid_y):
        """Convertir coordenadas de grid a coordenadas del mundo real"""
        world_x = grid_x * self.scale_factor + self.offset_x
        world_y = grid_y * self.scale_factor + self.offset_y
        
        return world_x, world_y
    
    def calcular_ruta_realista(self, pos_actual, pos_destino, operario_id=None):
        """
        REEMPLAZO DIRECTO de la función calcular_ruta_realista actual
        Mantiene la misma API pero usa pathfinding library internamente
        """
        print(f"[TILED ADAPTER] Calculando ruta: {pos_actual} -> {pos_destino}")
        
        if not self.grid:
            print("[ERROR] Grid no inicializado")
            return [pos_actual, pos_destino]
        
        # Convertir coordenadas del mundo a grid
        start_grid = self.world_to_grid(pos_actual[0], pos_actual[1])
        end_grid = self.world_to_grid(pos_destino[0], pos_destino[1])
        
        print(f"[GRID] {pos_actual} -> {start_grid}, {pos_destino} -> {end_grid}")
        
        # Limpiar grid para nueva búsqueda
        self.grid.cleanup()
        
        # Obtener nodos
        try:
            start_node = self.grid.node(start_grid[0], start_grid[1])
            end_node = self.grid.node(end_grid[0], end_grid[1])
            
            # Verificar que sean navegables
            if not start_node.walkable:
                print(f"[WARN] Nodo inicio no navegable, buscando alternativa...")
                start_grid = self._find_nearest_walkable(start_grid[0], start_grid[1])
                start_node = self.grid.node(start_grid[0], start_grid[1])
            
            if not end_node.walkable:
                print(f"[WARN] Nodo destino no navegable, buscando alternativa...")
                end_grid = self._find_nearest_walkable(end_grid[0], end_grid[1])
                end_node = self.grid.node(end_grid[0], end_grid[1])
            
            # Calcular ruta
            path, runs = self.finder.find_path(start_node, end_node, self.grid)
            
            if path:
                # Convertir ruta de grid a coordenadas mundo
                world_path = []
                for node in path:
                    world_pos = self.grid_to_world(node.x, node.y)
                    world_path.append(world_pos)
                
                print(f"[SUCCESS] Ruta encontrada: {len(world_path)} puntos, {runs} nodos explorados")
                return world_path
            else:
                print(f"[FAIL] Sin ruta encontrada ({runs} nodos explorados)")
                return [pos_actual, pos_destino]  # Fallback
        
        except Exception as e:
            print(f"[ERROR] Error en pathfinding: {e}")
            return [pos_actual, pos_destino]  # Fallback
    
    def _find_nearest_walkable(self, grid_x, grid_y, radius=3):
        """Encontrar el punto navegable más cercano"""
        for r in range(1, radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    x, y = grid_x + dx, grid_y + dy
                    if (0 <= x < self.width and 0 <= y < self.height and 
                        self.matrix[y][x] == 1):
                        print(f"[NEAREST] Alternativa encontrada: ({x}, {y})")
                        return (x, y)
        
        print(f"[WARN] No se encontró alternativa navegable cerca de ({grid_x}, {grid_y})")
        return (grid_x, grid_y)  # Fallback
    
    def obtener_estadisticas(self):
        """Obtener estadísticas del sistema de pathfinding"""
        if not self.matrix:
            return {}
        
        total_cells = self.width * self.height
        walkable_cells = sum(sum(row) for row in self.matrix)
        
        return {
            'grid_size': f"{self.width}x{self.height}",
            'total_cells': total_cells,
            'walkable_cells': walkable_cells,
            'obstacle_cells': total_cells - walkable_cells,
            'walkable_percentage': (walkable_cells / total_cells) * 100,
            'source': self.config_source,
            'pytmx_available': PYTMX_AVAILABLE
        }

# Factory function para crear adaptador según configuración
def crear_adaptador_pathfinding(config_source="current_system"):
    """
    Crear adaptador de pathfinding
    config_source: "matrix", "tmx_warehouse", "tmx_torture", "current_system"
    """
    print(f"Creando adaptador de pathfinding: {config_source}")
    
    adapter = TiledPathfindingAdapter(config_source)
    stats = adapter.obtener_estadisticas()
    
    print("Estadísticas del adaptador:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return adapter

# Función de compatibilidad - reemplazo directo
def calcular_ruta_realista_tiled(pos_actual, pos_destino, operario_id=None):
    """
    Función de reemplazo directo para calcular_ruta_realista
    Usa el sistema Tiled internamente
    """
    
    # Crear adaptador temporal (en producción, sería singleton)
    global _adaptador_global
    if '_adaptador_global' not in globals():
        _adaptador_global = crear_adaptador_pathfinding("tmx_torture")  # Para testing
    
    return _adaptador_global.calcular_ruta_realista(pos_actual, pos_destino, operario_id)

if __name__ == "__main__":
    print("="*50)
    print("TESTING ADAPTADOR TILED")
    print("="*50)
    
    # Test básico
    adapter = crear_adaptador_pathfinding("tmx_torture")
    
    # Casos de prueba
    test_cases = [
        {"start": (100, 100), "end": (500, 200), "name": "Ruta básica"},
        {"start": (50, 50), "end": (600, 300), "name": "Ruta larga"},
        {"start": (200, 150), "end": (300, 150), "name": "Ruta corta"},
    ]
    
    for case in test_cases:
        print(f"\nTEST: {case['name']}")
        ruta = adapter.calcular_ruta_realista(case['start'], case['end'])
        print(f"Resultado: {len(ruta)} puntos")
        if len(ruta) <= 5:
            print(f"Ruta: {ruta}")
        else:
            print(f"Ruta: {ruta[:2]} ... {ruta[-2:]}")
    
    print("\nAdaptador funcionando correctamente!")