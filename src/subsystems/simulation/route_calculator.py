# -*- coding: utf-8 -*-
"""
Route Calculator Module - Multi-Stop Tour Optimization
Digital Twin Warehouse Simulator

Calculates optimal routes for visiting multiple picking locations
"""

import math
from typing import List, Tuple, Optional, Dict, Any


class RouteCalculator:
    """
    Route Calculator for Multi-Stop Tour Optimization

    Calculates optimal routes for warehouse operators visiting multiple
    picking locations. Uses A* pathfinding and respects pick_sequence ordering.
    """

    def __init__(self, pathfinder: Any):
        """
        Initialize RouteCalculator with pathfinder

        Args:
            pathfinder: Pathfinder instance for A* pathfinding

        Raises:
            ValueError: If pathfinder is None
        """
        if pathfinder is None:
            raise ValueError("[ROUTE-CALCULATOR ERROR] pathfinder cannot be None")

        self.pathfinder = pathfinder
        print(f"[ROUTE-CALCULATOR] Inicializado con pathfinder {self.pathfinder}")

    def calculate_route(self,
                       start_position: Tuple[int, int],
                       work_orders: List[Any],
                       return_to_start: bool = True,
                       preserve_first: bool = False) -> Optional[Dict[str, Any]]:
        """
        Calculate optimal route visiting all work order locations

        Args:
            start_position: Starting position (grid coordinates) - typically depot
            work_orders: List of WorkOrder objects to visit
            return_to_start: Whether to return to start position after last pick

        Returns:
            Dictionary with route information:
            {
                'success': bool,
                'total_distance': float,
                'num_stops': int,
                'visit_sequence': List[WorkOrder],
                'full_path': List[Tuple[int,int]],
                'segment_paths': List[List[Tuple]],
                'segment_distances': List[float],
                'errors': List[str]
            }
            Returns None if route cannot be calculated
        """
        errors = []

        # Edge case: empty work orders list
        if not work_orders:
            return {
                'success': True,
                'total_distance': 0.0,
                'num_stops': 0,
                'visit_sequence': [],
                'full_path': [start_position],
                'segment_paths': [],
                'segment_distances': [],
                'errors': []
            }

        # Validate start position
        if not self.pathfinder.is_walkable(start_position[0], start_position[1]):
            errors.append(f"Start position {start_position} is not walkable")
            return {
                'success': False,
                'total_distance': 0.0,
                'num_stops': 0,
                'visit_sequence': [],
                'full_path': [],
                'segment_paths': [],
                'segment_distances': [],
                'errors': errors
            }

        # Validate work order positions
        if not self.validate_work_order_positions(work_orders):
            errors.append("One or more work order positions are invalid")
            # Continue anyway - validation already logged warnings

        # Order work orders by pick_sequence (default strategy)
        ordered_work_orders = self.order_work_orders_by_sequence(work_orders, preserve_first)

        # Calculate route segments
        segment_paths = []
        segment_distances = []
        full_path = []
        current_position = start_position

        # Add start position to full path
        full_path.append(start_position)

        # Calculate path for each work order
        for wo in ordered_work_orders:
            goal_position = wo.ubicacion

            # Find path from current position to work order location
            path = self.pathfinder.find_path(current_position, goal_position)

            if path is None:
                # No path found
                errors.append(f"No path found from {current_position} to {goal_position} (WO {wo.id})")
                return {
                    'success': False,
                    'total_distance': 0.0,
                    'num_stops': len(segment_paths),
                    'visit_sequence': ordered_work_orders[:len(segment_paths)],
                    'full_path': full_path,
                    'segment_paths': segment_paths,
                    'segment_distances': segment_distances,
                    'errors': errors
                }

            # Calculate distance of this segment
            distance = self.calculate_path_distance(path)

            # Store segment information
            segment_paths.append(path)
            segment_distances.append(distance)

            # Append to full path (skip first point to avoid duplication)
            if len(path) > 1:
                full_path.extend(path[1:])
            else:
                full_path.extend(path)

            # Update current position
            current_position = goal_position

        # Return to start if requested
        if return_to_start and current_position != start_position:
            return_path = self.pathfinder.find_path(current_position, start_position)

            if return_path is None:
                errors.append(f"No return path from {current_position} to {start_position}")
            else:
                return_distance = self.calculate_path_distance(return_path)
                segment_paths.append(return_path)
                segment_distances.append(return_distance)

                # Append return path to full path
                if len(return_path) > 1:
                    full_path.extend(return_path[1:])

        # Calculate total distance
        total_distance = sum(segment_distances)

        # Build result
        result = {
            'success': True,
            'total_distance': total_distance,
            'num_stops': len(ordered_work_orders),
            'visit_sequence': ordered_work_orders,
            'full_path': full_path,
            'segment_paths': segment_paths,
            'segment_distances': segment_distances,
            'errors': errors
        }

        print(f"[ROUTE-CALCULATOR] Ruta calculada: {len(ordered_work_orders)} paradas, "
              f"distancia total: {total_distance:.2f}")

        return result

    def order_work_orders_by_sequence(self, work_orders: List[Any], preserve_first: bool = False) -> List[Any]:
        """
        Order work orders by their pick_sequence attribute

        Args:
            work_orders: List of WorkOrder objects
            preserve_first: If True, keep the first WorkOrder at the beginning

        Returns:
            Sorted list of WorkOrders by pick_sequence (ascending)

        Notes:
            - pick_sequence comes from Warehouse_Logic.xlsx
            - This represents the optimal picking order determined by warehouse design
            - Lower sequence = pick first
            - If preserve_first=True, the first WorkOrder stays first regardless of pick_sequence
        """
        if not work_orders:
            return work_orders
            
        if preserve_first:
            # Don't reorder at all - keep the order provided by dispatcher
            ordered = work_orders
            print(f"[ROUTE-CALCULATOR] Ordenados {len(ordered)} WorkOrders por orden del dispatcher (sin reordenar)")
        else:
            # Sort by pick_sequence attribute
            ordered = sorted(work_orders, key=lambda wo: wo.pick_sequence)
            print(f"[ROUTE-CALCULATOR] Ordenados {len(ordered)} WorkOrders por pick_sequence")

        return ordered

    def calculate_path_distance(self, path: List[Tuple[int, int]]) -> float:
        """
        Calculate total distance of a path

        Args:
            path: List of grid positions [(x,y), ...]

        Returns:
            Total distance (sum of euclidean distances between consecutive points)

        Notes:
            - Accounts for diagonal movement (cost = sqrt(2))
            - Matches Pathfinder's distance metric
        """
        if not path or len(path) < 2:
            return 0.0

        total_distance = 0.0

        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]

            # Calculate euclidean distance
            dx = x2 - x1
            dy = y2 - y1
            distance = math.sqrt(dx * dx + dy * dy)

            total_distance += distance

        return total_distance

    def validate_work_order_positions(self, work_orders: List[Any]) -> bool:
        """
        Validate that all work order positions are reachable

        Args:
            work_orders: List of WorkOrder objects

        Returns:
            True if all positions are valid and walkable, False otherwise

        Notes:
            - Checks using pathfinder.is_walkable()
            - Prevents errors during route calculation
            - Logs warnings for invalid positions
        """
        all_valid = True

        for wo in work_orders:
            ubicacion = wo.ubicacion
            x, y = ubicacion

            if not self.pathfinder.is_walkable(x, y):
                print(f"[ROUTE-CALCULATOR WARNING] WorkOrder {wo.id} ubicacion {ubicacion} "
                      f"is not walkable")
                all_valid = False

        return all_valid

    def get_total_volume(self, work_orders: List[Any]) -> int:
        """
        Calculate total volume of work orders

        Args:
            work_orders: List of WorkOrder objects

        Returns:
            Total volume (sum of all work order volumes)

        Notes:
            - Uses WorkOrder.calcular_volumen_restante() method
            - Useful for validating capacity constraints
        """
        total_volume = sum(wo.calcular_volumen_restante() for wo in work_orders)
        return total_volume

    def calculate_greedy_nearest_neighbor(self,
                                         start_position: Tuple[int, int],
                                         work_orders: List[Any]) -> List[Any]:
        """
        Calculate visiting order using greedy nearest-neighbor heuristic

        Args:
            start_position: Starting position (grid)
            work_orders: List of WorkOrder objects

        Returns:
            Reordered list of WorkOrders (closest-first strategy)

        Notes:
            - Alternative to pick_sequence ordering
            - May be used if config.dispatch_strategy == "Cercania"
            - Greedy TSP approximation (not optimal but fast)
        """
        if not work_orders:
            return []

        sequence = []
        remaining = work_orders.copy()
        current_position = start_position

        while remaining:
            # Find nearest work order
            nearest_wo = min(
                remaining,
                key=lambda wo: self._euclidean_distance(current_position, wo.ubicacion)
            )

            # Add to sequence
            sequence.append(nearest_wo)
            remaining.remove(nearest_wo)

            # Update current position
            current_position = nearest_wo.ubicacion

        print(f"[ROUTE-CALCULATOR] Nearest-neighbor ordenamiento: {len(sequence)} WOs")

        return sequence

    def _euclidean_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """
        Calculate euclidean distance between two positions

        Args:
            pos1: First position (x, y)
            pos2: Second position (x, y)

        Returns:
            Euclidean distance
        """
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        return math.sqrt(dx * dx + dy * dy)

    def __repr__(self):
        return f"RouteCalculator(pathfinder={self.pathfinder})"
