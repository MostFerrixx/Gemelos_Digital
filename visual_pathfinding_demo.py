#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEMO VISUAL INTERACTIVO: PyTMX + Pathfinding + Pygame
¡Finalmente algo que puedes VER funcionando!
"""

import pygame
import sys
import os
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

# Agregar directorio git para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

try:
    import pytmx
    import pytmx.util_pygame
    PYTMX_AVAILABLE = True
except ImportError:
    PYTMX_AVAILABLE = False

class VisualPathfindingDemo:
    """Demo interactivo de pathfinding con visualización"""
    
    def __init__(self):
        pygame.init()
        
        # Configuración de ventana
        self.width = 1200
        self.height = 800
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("DEMO PyTMX + Pathfinding - ¡Haz clic para navegar!")
        
        # Configuración de pathfinding
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        self.grid = None
        self.current_path = []
        self.start_pos = None
        self.end_pos = None
        
        # Estado del demo
        self.tmx_data = None
        self.tile_size = 24  # Tamaño de tile en pixels
        self.current_map = "torture"  # "torture" o "warehouse"
        self.show_grid = True
        self.show_path_numbers = True
        
        # Colores
        self.colors = {
            'walkable': (144, 238, 144),    # Verde claro
            'obstacle': (139, 69, 19),      # Marrón
            'start': (255, 0, 0),           # Rojo
            'end': (0, 0, 255),            # Azul  
            'path': (255, 255, 0),          # Amarillo
            'explored': (255, 200, 200),    # Rosa claro
            'grid': (200, 200, 200),        # Gris claro
            'text': (0, 0, 0),             # Negro
            'background': (245, 245, 245)   # Gris muy claro
        }
        
        # Fuentes
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_large = pygame.font.Font(None, 36)
        
        # Cargar mapas
        self.load_maps()
        
        # Clock para FPS
        self.clock = pygame.time.Clock()
    
    def load_maps(self):
        """Cargar mapas TMX y datos de pathfinding"""
        print("Cargando mapas...")
        
        # Cargar mapa de tortura (más pequeño para empezar)
        self.load_torture_map()
        
        print("Mapas cargados exitosamente")
    
    def load_torture_map(self):
        """Cargar el mapa de tortura"""
        try:
            if PYTMX_AVAILABLE:
                # Intentar cargar con pytmx
                try:
                    self.tmx_data = pytmx.util_pygame.load_pygame('torture_layout.tmx')
                    print("TMX cargado con pytmx")
                    self.load_from_tmx()
                    return
                except Exception as e:
                    print(f"Error cargando TMX: {e}")
            
            # Fallback: cargar directamente la matriz
            self.load_torture_matrix_directly()
            
        except Exception as e:
            print(f"Error cargando mapa de tortura: {e}")
            self.create_simple_test_grid()
    
    def load_from_tmx(self):
        """Cargar datos desde TMX"""
        if not self.tmx_data:
            return
        
        width = self.tmx_data.width
        height = self.tmx_data.height
        
        # Crear matriz para pathfinding
        matrix = []
        
        # Obtener capa principal
        layer = None
        for layer_obj in self.tmx_data.layers:
            if hasattr(layer_obj, 'data'):
                layer = layer_obj
                break
        
        if layer:
            for y in range(height):
                row = []
                for x in range(width):
                    tile_gid = layer.data[y][x]
                    if tile_gid == 0:
                        row.append(0)  # Sin tile = obstáculo
                    else:
                        # Obtener propiedades del tile
                        tile = self.tmx_data.get_tile_by_gid(tile_gid)
                        if tile and hasattr(tile, 'properties'):
                            walkable = tile.properties.get('walkable', 'false')
                            row.append(1 if walkable.lower() == 'true' else 0)
                        else:
                            row.append(1 if tile_gid == 1 else 0)  # Default: tile 1 = walkable
                
                matrix.append(row)
        
        self.setup_pathfinding_grid(matrix)
    
    def load_torture_matrix_directly(self):
        """Cargar matriz de tortura directamente (fallback)"""
        torture_matrix = [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [0,1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,1,0],
            [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
            [0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0],
            [1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,1],
            [0,1,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0],
            [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
            [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        ]
        
        self.setup_pathfinding_grid(torture_matrix)
        print("Matriz de tortura cargada directamente")
    
    def create_simple_test_grid(self):
        """Crear grilla simple de prueba si todo falla"""
        simple_matrix = [
            [1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,1,0,0,0,0,1],
            [1,0,1,0,1,0,1,1,0,1],
            [1,0,1,0,0,0,1,0,0,1],
            [1,0,1,1,1,0,1,0,1,1],
            [1,0,0,0,0,0,0,0,0,1],
            [1,1,1,1,1,1,1,1,1,1]
        ]
        
        self.setup_pathfinding_grid(simple_matrix)
        print("Grilla simple de prueba creada")
    
    def setup_pathfinding_grid(self, matrix):
        """Configurar grid de pathfinding"""
        self.matrix = matrix
        self.grid_width = len(matrix[0]) if matrix else 0
        self.grid_height = len(matrix) if matrix else 0
        self.grid = Grid(matrix=matrix)
        
        # Ajustar tamaño de tile según dimensiones
        self.tile_size = min(
            (self.width - 200) // self.grid_width,
            (self.height - 100) // self.grid_height
        )
        self.tile_size = max(12, min(32, self.tile_size))
        
        print(f"Grid configurado: {self.grid_width}x{self.grid_height}, tile_size: {self.tile_size}")
    
    def screen_to_grid(self, screen_x, screen_y):
        """Convertir coordenadas de pantalla a grid"""
        offset_x = 50
        offset_y = 80
        
        grid_x = (screen_x - offset_x) // self.tile_size
        grid_y = (screen_y - offset_y) // self.tile_size
        
        if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
            return grid_x, grid_y
        return None
    
    def grid_to_screen(self, grid_x, grid_y):
        """Convertir coordenadas de grid a pantalla"""
        offset_x = 50
        offset_y = 80
        
        screen_x = offset_x + grid_x * self.tile_size
        screen_y = offset_y + grid_y * self.tile_size
        
        return screen_x, screen_y
    
    def calculate_path(self):
        """Calcular ruta entre start y end"""
        if not self.grid or not self.start_pos or not self.end_pos:
            return
        
        # Limpiar grid
        self.grid.cleanup()
        
        # Obtener nodos
        start_node = self.grid.node(self.start_pos[0], self.start_pos[1])
        end_node = self.grid.node(self.end_pos[0], self.end_pos[1])
        
        # Calcular ruta
        path, runs = self.finder.find_path(start_node, end_node, self.grid)
        
        self.current_path = [(node.x, node.y) for node in path]
        
        print(f"Ruta calculada: {len(self.current_path)} puntos, {runs} nodos explorados")
    
    def handle_click(self, pos):
        """Manejar clic del mouse"""
        grid_pos = self.screen_to_grid(pos[0], pos[1])
        
        if not grid_pos:
            return
        
        grid_x, grid_y = grid_pos
        
        # Verificar que la posición sea navegable
        if self.matrix[grid_y][grid_x] == 0:  # Obstáculo
            print(f"Posición ({grid_x}, {grid_y}) no navegable - ignorando clic")
            return
        
        # Establecer start o end
        if not self.start_pos:
            self.start_pos = grid_pos
            print(f"Punto de inicio: {self.start_pos}")
        elif not self.end_pos:
            self.end_pos = grid_pos
            print(f"Punto de destino: {self.end_pos}")
            self.calculate_path()
        else:
            # Reset - nuevo inicio
            self.start_pos = grid_pos
            self.end_pos = None
            self.current_path = []
            print(f"Nuevo punto de inicio: {self.start_pos}")
    
    def render(self):
        """Renderizar toda la escena"""
        self.screen.fill(self.colors['background'])
        
        # Título
        title_text = self.font_large.render("DEMO: PyTMX + Pathfinding Interactivo", True, self.colors['text'])
        self.screen.blit(title_text, (10, 10))
        
        # Instrucciones
        instructions = [
            "Clic 1: Establecer INICIO (rojo)",
            "Clic 2: Establecer DESTINO (azul) - calcula ruta",
            "Clic 3+: Nuevo inicio",
            f"Grid: {self.grid_width}x{self.grid_height} - {len(self.current_path)} puntos en ruta"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.font_small.render(instruction, True, self.colors['text'])
            self.screen.blit(text, (10, 45 + i * 20))
        
        if not self.grid:
            error_text = self.font.render("Error: No se pudo cargar el grid", True, (255, 0, 0))
            self.screen.blit(error_text, (10, 200))
            return
        
        # Renderizar grid
        self.render_grid()
        
        # Renderizar ruta
        if self.current_path:
            self.render_path()
        
        # Renderizar start/end
        if self.start_pos:
            self.render_point(self.start_pos, self.colors['start'], "S")
        
        if self.end_pos:
            self.render_point(self.end_pos, self.colors['end'], "E")
    
    def render_grid(self):
        """Renderizar la grilla del pathfinding"""
        offset_x = 50
        offset_y = 80
        
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                screen_x = offset_x + x * self.tile_size
                screen_y = offset_y + y * self.tile_size
                
                # Color según tipo de tile
                if self.matrix[y][x] == 1:
                    color = self.colors['walkable']
                else:
                    color = self.colors['obstacle']
                
                # Dibujar tile
                pygame.draw.rect(self.screen, color, 
                               (screen_x, screen_y, self.tile_size, self.tile_size))
                
                # Dibujar borde si se muestra grid
                if self.show_grid:
                    pygame.draw.rect(self.screen, self.colors['grid'],
                                   (screen_x, screen_y, self.tile_size, self.tile_size), 1)
    
    def render_path(self):
        """Renderizar la ruta calculada"""
        if len(self.current_path) < 2:
            return
        
        # Líneas de la ruta
        screen_points = []
        for grid_x, grid_y in self.current_path:
            screen_x, screen_y = self.grid_to_screen(grid_x, grid_y)
            center_x = screen_x + self.tile_size // 2
            center_y = screen_y + self.tile_size // 2
            screen_points.append((center_x, center_y))
        
        # Dibujar línea de ruta
        if len(screen_points) > 1:
            pygame.draw.lines(self.screen, self.colors['path'], False, screen_points, 3)
        
        # Números en la ruta
        if self.show_path_numbers:
            for i, (grid_x, grid_y) in enumerate(self.current_path[1:-1], 1):  # Saltar start y end
                screen_x, screen_y = self.grid_to_screen(grid_x, grid_y)
                center_x = screen_x + self.tile_size // 2
                center_y = screen_y + self.tile_size // 2
                
                # Círculo amarillo para el número
                pygame.draw.circle(self.screen, self.colors['path'], (center_x, center_y), 8)
                pygame.draw.circle(self.screen, self.colors['text'], (center_x, center_y), 8, 1)
                
                # Número
                if i < 100:  # Evitar números muy grandes
                    text = self.font_small.render(str(i), True, self.colors['text'])
                    text_rect = text.get_rect(center=(center_x, center_y))
                    self.screen.blit(text, text_rect)
    
    def render_point(self, grid_pos, color, label):
        """Renderizar punto especial (start/end)"""
        grid_x, grid_y = grid_pos
        screen_x, screen_y = self.grid_to_screen(grid_x, grid_y)
        center_x = screen_x + self.tile_size // 2
        center_y = screen_y + self.tile_size // 2
        
        # Círculo grande
        pygame.draw.circle(self.screen, color, (center_x, center_y), self.tile_size // 3)
        pygame.draw.circle(self.screen, self.colors['text'], (center_x, center_y), self.tile_size // 3, 2)
        
        # Etiqueta
        text = self.font.render(label, True, (255, 255, 255))
        text_rect = text.get_rect(center=(center_x, center_y))
        self.screen.blit(text, text_rect)
    
    def run(self):
        """Ejecutar el demo"""
        print("="*60)
        print("DEMO VISUAL INTERACTIVO INICIADO")
        print("="*60)
        print("- Haz clic para establecer inicio y destino")
        print("- Ver pathfinding en acción!")
        print("- ESC para salir")
        print("="*60)
        
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # Reset
                        self.start_pos = None
                        self.end_pos = None
                        self.current_path = []
                        print("Reset - selecciona nuevos puntos")
                    elif event.key == pygame.K_g:
                        # Toggle grid
                        self.show_grid = not self.show_grid
                    elif event.key == pygame.K_n:
                        # Toggle números de ruta
                        self.show_path_numbers = not self.show_path_numbers
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Clic izquierdo
                        self.handle_click(event.pos)
            
            self.render()
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        print("Demo finalizado")

def main():
    """Ejecutar demo"""
    print("Iniciando demo visual de pathfinding...")
    
    try:
        demo = VisualPathfindingDemo()
        demo.run()
    except Exception as e:
        print(f"Error en demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()