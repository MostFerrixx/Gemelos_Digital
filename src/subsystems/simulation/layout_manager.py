# -*- coding: utf-8 -*-
"""
Layout Manager Module - TMX Map Handler
Digital Twin Warehouse Simulator

Handles loading and parsing of Tiled TMX map files for warehouse layout
"""

import pygame
import pytmx
import random
from typing import Tuple, List, Optional, Dict, Any


class LayoutManager:
    """
    Layout Manager for TMX (Tiled) Map Files
    Provides grid/pixel conversion, collision detection, and picking point extraction
    """

    def __init__(self, tmx_file_path: str):
        """
        Initialize Layout Manager with TMX file

        Args:
            tmx_file_path: Path to TMX map file

        Raises:
            FileNotFoundError: If TMX file doesn't exist
            RuntimeError: If TMX file is invalid
        """
        print(f"[LAYOUT-MANAGER] Cargando archivo TMX: {tmx_file_path}")

        try:
            # Load TMX file using pytmx with pygame loader
            # BUGFIX 2025-10-04: Usar load_pygame() para cargar imagenes de tiles
            self.tmx_data = pytmx.load_pygame(tmx_file_path)
            print(f"[LAYOUT-MANAGER] TMX cargado exitosamente (con imagenes Pygame)")

        except FileNotFoundError:
            raise FileNotFoundError(f"[LAYOUT-MANAGER ERROR] Archivo TMX no encontrado: {tmx_file_path}")
        except Exception as e:
            raise RuntimeError(f"[LAYOUT-MANAGER ERROR] Error cargando TMX: {e}")

        # Map dimensions (in grid cells)
        self.grid_width = self.tmx_data.width
        self.grid_height = self.tmx_data.height

        # Tile dimensions (in pixels)
        self.tile_width = self.tmx_data.tilewidth
        self.tile_height = self.tmx_data.tileheight

        # Total map size in pixels
        self.pixel_width = self.grid_width * self.tile_width
        self.pixel_height = self.grid_height * self.tile_height

        print(f"[LAYOUT-MANAGER] Dimensiones del mapa:")
        print(f"  - Grid: {self.grid_width}x{self.grid_height} celdas")
        print(f"  - Tile: {self.tile_width}x{self.tile_height} pixeles")
        print(f"  - Total: {self.pixel_width}x{self.pixel_height} pixeles")

        # Initialize collision matrix and picking points
        self.collision_matrix = self._build_collision_matrix()
        self.picking_points = self._extract_picking_points()

        print(f"[LAYOUT-MANAGER] Puntos de picking encontrados: {len(self.picking_points)}")

    def _build_collision_matrix(self) -> List[List[bool]]:
        """
        Build collision matrix from TMX tile properties
        True = walkable, False = blocked

        Returns:
            2D list of booleans [y][x] representing walkability
        """
        print("[LAYOUT-MANAGER] Construyendo matriz de colisiones...")

        # Initialize matrix (all walkable by default)
        matrix = [[True for _ in range(self.grid_width)]
                  for _ in range(self.grid_height)]

        # Iterate through all layers
        for layer_idx, layer in enumerate(self.tmx_data.visible_layers):
            # Only process tile layers (skip ObjectGroup and other layer types)
            if not hasattr(layer, 'data'):
                continue

            for y in range(self.grid_height):
                for x in range(self.grid_width):
                    try:
                        # Get tile at position (use layer index, not layer.id)
                        tile = self.tmx_data.get_tile_properties(x, y, layer_idx)
                    except (AttributeError, IndexError, KeyError):
                        # Skip if layer doesn't have tile data
                        continue

                    if tile:
                        # Check walkable property
                        walkable = tile.get('walkable', 'true')

                        # Handle both string and boolean values
                        if isinstance(walkable, str):
                            is_walkable = walkable.lower() == 'true'
                        else:
                            is_walkable = bool(walkable)

                        # If any layer marks it as non-walkable, it's blocked
                        if not is_walkable:
                            matrix[y][x] = False

        # Count walkable cells
        walkable_count = sum(sum(row) for row in matrix)
        total_cells = self.grid_width * self.grid_height
        blocked_count = total_cells - walkable_count

        print(f"[LAYOUT-MANAGER] Matriz de colisiones:")
        print(f"  - Celdas caminables: {walkable_count}/{total_cells}")
        print(f"  - Celdas bloqueadas: {blocked_count}/{total_cells}")

        return matrix

    def _extract_picking_points(self) -> List[Dict[str, Any]]:
        """
        Extract picking points from TMX map
        Looks for tiles with type='picking_location'

        Returns:
            List of picking point dictionaries
        """
        picking_points = []

        # Iterate through all layers
        for layer_idx, layer in enumerate(self.tmx_data.visible_layers):
            # Only process tile layers (skip ObjectGroup and other layer types)
            if not hasattr(layer, 'data'):
                continue

            for y in range(self.grid_height):
                for x in range(self.grid_width):
                    try:
                        # Get tile properties (use layer index, not layer.id)
                        tile = self.tmx_data.get_tile_properties(x, y, layer_idx)
                    except (AttributeError, IndexError, KeyError):
                        # Skip if layer doesn't have tile data
                        continue

                    if tile:
                        tile_type = tile.get('type', '')

                        # Check if it's a picking location
                        if tile_type == 'picking_location':
                            picking_point = {
                                'grid_position': (x, y),
                                'pixel_position': self.grid_to_pixel(x, y),
                                'type': tile_type,
                                'name': tile.get('name', f'Pick-{len(picking_points)+1}')
                            }
                            picking_points.append(picking_point)

        return picking_points

    def grid_to_pixel(self, grid_x: int, grid_y: int) -> Tuple[int, int]:
        """
        Convert grid coordinates to pixel coordinates (centered on tile)

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            Tuple (pixel_x, pixel_y) at tile center
        """
        # Calculate pixel position at tile center
        pixel_x = (grid_x * self.tile_width) + (self.tile_width // 2)
        pixel_y = (grid_y * self.tile_height) + (self.tile_height // 2)

        return (pixel_x, pixel_y)

    def pixel_to_grid(self, pixel_x: int, pixel_y: int) -> Tuple[int, int]:
        """
        Convert pixel coordinates to grid coordinates

        Args:
            pixel_x: Pixel X coordinate
            pixel_y: Pixel Y coordinate

        Returns:
            Tuple (grid_x, grid_y)
        """
        grid_x = pixel_x // self.tile_width
        grid_y = pixel_y // self.tile_height

        # Clamp to map boundaries
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))

        return (grid_x, grid_y)

    def is_walkable(self, grid_x: int, grid_y: int) -> bool:
        """
        Check if a grid cell is walkable

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            True if walkable, False otherwise
        """
        # Check bounds
        if grid_x < 0 or grid_x >= self.grid_width:
            return False
        if grid_y < 0 or grid_y >= self.grid_height:
            return False

        # Check collision matrix
        return self.collision_matrix[grid_y][grid_x]

    def get_random_walkable_point(self) -> Optional[Tuple[int, int]]:
        """
        Get a random walkable grid position

        Returns:
            Tuple (grid_x, grid_y) or None if no walkable positions exist
        """
        # Collect all walkable positions
        walkable_positions = []

        for y in range(self.grid_height):
            for x in range(self.grid_width):
                if self.collision_matrix[y][x]:
                    walkable_positions.append((x, y))

        # Return random position if any exist
        if walkable_positions:
            return random.choice(walkable_positions)

        return None

    def get_neighbors(self, grid_x: int, grid_y: int,
                     include_diagonals: bool = True) -> List[Tuple[int, int]]:
        """
        Get walkable neighbors of a grid cell

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            include_diagonals: Whether to include diagonal neighbors

        Returns:
            List of walkable neighbor positions (grid_x, grid_y)
        """
        neighbors = []

        # Define neighbor offsets
        # Cardinal directions (N, E, S, W)
        cardinal_offsets = [
            (0, -1),   # North
            (1, 0),    # East
            (0, 1),    # South
            (-1, 0)    # West
        ]

        # Diagonal directions (NE, SE, SW, NW)
        diagonal_offsets = [
            (1, -1),   # NE
            (1, 1),    # SE
            (-1, 1),   # SW
            (-1, -1)   # NW
        ]

        # Choose offsets based on include_diagonals
        offsets = cardinal_offsets + (diagonal_offsets if include_diagonals else [])

        # Check each neighbor
        for dx, dy in offsets:
            nx = grid_x + dx
            ny = grid_y + dy

            # Check if neighbor is walkable
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))

        return neighbors

    def render(self, surface: pygame.Surface):
        """
        Render TMX map to pygame surface (1:1 pixel correspondence)

        Args:
            surface: Pygame surface to render to
        """
        # Render all visible tile layers
        for layer_idx, layer in enumerate(self.tmx_data.visible_layers):
            if hasattr(layer, 'data'):
                for y in range(self.grid_height):
                    for x in range(self.grid_width):
                        # Get tile image
                        tile_image = self.tmx_data.get_tile_image(x, y, layer_idx)

                        if tile_image:
                            # Calculate pixel position (top-left corner)
                            pixel_x = x * self.tile_width
                            pixel_y = y * self.tile_height

                            # Blit tile to surface
                            surface.blit(tile_image, (pixel_x, pixel_y))

    def get_tile_type(self, grid_x: int, grid_y: int) -> Optional[str]:
        """
        Get tile type at grid position

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            Tile type string or None
        """
        # Check bounds
        if not (0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height):
            return None

        # Check all layers for tile properties
        for layer_idx, layer in enumerate(self.tmx_data.visible_layers):
            if hasattr(layer, 'data'):
                tile = self.tmx_data.get_tile_properties(grid_x, grid_y, layer_idx)
                if tile:
                    return tile.get('type', None)

        return None

    def __repr__(self):
        return (f"LayoutManager(grid={self.grid_width}x{self.grid_height}, "
                f"tile={self.tile_width}x{self.tile_height}, "
                f"picking_points={len(self.picking_points)})")
