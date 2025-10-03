# -*- coding: utf-8 -*-
"""
Pathfinder Module - A* Algorithm Implementation
Digital Twin Warehouse Simulator

Implements A* pathfinding algorithm for grid-based navigation
"""

import heapq
import math
from typing import List, Tuple, Optional, Set, Dict


class Pathfinder:
    """
    A* Pathfinding Algorithm for Grid-Based Navigation

    Finds the shortest path between two points on a walkable grid using
    the A* search algorithm with octile distance heuristic.
    """

    def __init__(self, collision_matrix: List[List[bool]]):
        """
        Initialize Pathfinder with walkability matrix

        Args:
            collision_matrix: 2D matrix [y][x] where True=walkable, False=blocked

        Raises:
            ValueError: If collision_matrix is empty or invalid
        """
        if not collision_matrix or not collision_matrix[0]:
            raise ValueError("[PATHFINDER ERROR] collision_matrix cannot be empty")

        self.collision_matrix = collision_matrix
        self.height = len(collision_matrix)
        self.width = len(collision_matrix[0])

        # Movement costs
        self.COST_STRAIGHT = 1.0
        self.COST_DIAGONAL = math.sqrt(2)  # ~1.414

        print(f"[PATHFINDER] Inicializado con grid {self.width}x{self.height}")

    def is_walkable(self, x: int, y: int) -> bool:
        """
        Check if a grid cell is walkable

        Args:
            x: Grid X coordinate
            y: Grid Y coordinate

        Returns:
            True if cell is within bounds and walkable, False otherwise
        """
        # Check bounds
        if x < 0 or x >= self.width:
            return False
        if y < 0 or y >= self.height:
            return False

        # Check walkability
        return self.collision_matrix[y][x]

    def get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[Tuple[int, int], float]]:
        """
        Get walkable neighbors with movement costs

        Args:
            pos: Current position (x, y)

        Returns:
            List of tuples: ((neighbor_x, neighbor_y), cost)
        """
        x, y = pos
        neighbors = []

        # 8-directional movement: cardinals + diagonals
        # Format: (dx, dy, cost)
        directions = [
            # Cardinals (cost = 1.0)
            (0, -1, self.COST_STRAIGHT),   # North
            (1, 0, self.COST_STRAIGHT),    # East
            (0, 1, self.COST_STRAIGHT),    # South
            (-1, 0, self.COST_STRAIGHT),   # West
            # Diagonals (cost = sqrt(2))
            (1, -1, self.COST_DIAGONAL),   # NE
            (1, 1, self.COST_DIAGONAL),    # SE
            (-1, 1, self.COST_DIAGONAL),   # SW
            (-1, -1, self.COST_DIAGONAL)   # NW
        ]

        for dx, dy, cost in directions:
            nx = x + dx
            ny = y + dy

            if self.is_walkable(nx, ny):
                neighbors.append(((nx, ny), cost))

        return neighbors

    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """
        Octile distance heuristic (optimal for 8-directional movement)

        Args:
            a: Start position (x, y)
            b: Goal position (x, y)

        Returns:
            Estimated distance from a to b
        """
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])

        # Octile distance: allows diagonal movement
        # Formula: D * (dx + dy) + (D_diag - 2 * D) * min(dx, dy)
        # Where D = straight cost, D_diag = diagonal cost
        return self.COST_STRAIGHT * (dx + dy) + \
               (self.COST_DIAGONAL - 2 * self.COST_STRAIGHT) * min(dx, dy)

    def reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]],
                        current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Reconstruct path from start to goal using parent tracking

        Args:
            came_from: Dictionary mapping each node to its parent
            current: Goal position

        Returns:
            List of positions from start to goal
        """
        path = [current]

        while current in came_from:
            current = came_from[current]
            path.append(current)

        # Reverse to get start -> goal order
        path.reverse()

        return path

    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        Find shortest path from start to goal using A* algorithm

        Args:
            start: Starting position (grid_x, grid_y)
            goal: Goal position (grid_x, grid_y)

        Returns:
            List of grid positions [(x, y), ...] forming the path,
            or None if no path exists

        Edge Cases:
            - Returns None if start or goal is out of bounds
            - Returns None if start or goal is blocked
            - Returns [start] if start == goal
            - Returns None if no path exists (disconnected regions)
        """
        # Edge case: start == goal
        if start == goal:
            return [start]

        # Edge case: start or goal out of bounds or blocked
        if not self.is_walkable(start[0], start[1]):
            print(f"[PATHFINDER WARNING] Start position {start} is not walkable")
            return None

        if not self.is_walkable(goal[0], goal[1]):
            print(f"[PATHFINDER WARNING] Goal position {goal} is not walkable")
            return None

        # Initialize A* data structures
        # Open set: priority queue of (f_score, counter, position)
        open_set: List[Tuple[float, int, Tuple[int, int]]] = []
        counter = 0  # Tie-breaker for equal f_scores
        heapq.heappush(open_set, (0.0, counter, start))
        counter += 1

        # Closed set: visited nodes
        closed_set: Set[Tuple[int, int]] = set()

        # Cost from start to each node
        g_score: Dict[Tuple[int, int], float] = {start: 0.0}

        # Estimated total cost (g_score + heuristic)
        f_score: Dict[Tuple[int, int], float] = {start: self.heuristic(start, goal)}

        # Parent tracking for path reconstruction
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}

        # A* main loop
        while open_set:
            # Get node with lowest f_score
            _, _, current = heapq.heappop(open_set)

            # Skip if already visited
            if current in closed_set:
                continue

            # Goal reached!
            if current == goal:
                path = self.reconstruct_path(came_from, current)
                print(f"[PATHFINDER] Camino encontrado: {len(path)} pasos")
                return path

            # Mark as visited
            closed_set.add(current)

            # Explore neighbors
            for neighbor, move_cost in self.get_neighbors(current):
                # Skip if already visited
                if neighbor in closed_set:
                    continue

                # Calculate tentative g_score
                tentative_g_score = g_score[current] + move_cost

                # If this path to neighbor is better than previous
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    # Update scores
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, goal)

                    # Add to open set
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                    counter += 1

        # No path found
        print(f"[PATHFINDER WARNING] No se encontro camino de {start} a {goal}")
        return None

    def __repr__(self):
        return f"Pathfinder(grid={self.width}x{self.height})"
