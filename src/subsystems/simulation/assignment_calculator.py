# -*- coding: utf-8 -*-
"""
Assignment Cost Calculator Module
Digital Twin Warehouse Simulator

Calculates assignment costs for WorkOrder -> Operator matching.
Used by Dispatcher to make intelligent task allocation decisions.

Author: Digital Twin Warehouse Team
Version: V11 - Migration Phase 3
"""

from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass, field


@dataclass
class CostResult:
    """
    Result of assignment cost calculation

    Represents the total cost and breakdown of assigning a WorkOrder to an Operator.
    Lower total_cost indicates a better match.

    Attributes:
        total_cost: Final weighted cost (lower is better)
        priority_score: Work area priority (1 = best, 999 = incompatible)
        priority_penalty: Penalty for low priority (0 or large value)
        distance_cost: Estimated travel distance cost
        breakdown: Dict with detailed cost components for debugging
    """
    total_cost: float
    priority_score: int
    priority_penalty: float
    distance_cost: float
    breakdown: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return (f"CostResult(total={self.total_cost:.0f}, "
                f"priority={self.priority_score}, "
                f"penalty={self.priority_penalty:.0f}, "
                f"distance={self.distance_cost:.1f})")


class AssignmentCostCalculator:
    """
    Calculator for WorkOrder -> Operator assignment costs

    Uses multi-factor cost function to determine optimal task assignments:
    - Work Area Priority: Agent's affinity for specific work areas
    - Distance: Travel distance from current position to WorkOrder location
    - Capacity: Agent's remaining capacity vs WorkOrder volume (future)

    Cost Formula:
        total_cost = priority_penalty + (distance * distance_weight)

    Where:
        - priority_penalty = 0 if agent has priority for work_area
        - priority_penalty = LARGE_NUMBER if agent incompatible with work_area
        - distance = Estimated travel distance (via pathfinding or heuristic)

    The calculator integrates with:
    - DataManager: For agent configuration and work area definitions
    - RouteCalculator: For accurate distance estimation via pathfinding
    - Operators: To query work_area_priorities
    - WorkOrders: To get work_area and location requirements
    """

    # Cost parameters (tunable for different optimization strategies)
    PRIORITY_PENALTY_INCOMPATIBLE = 98_000_000  # Agent cannot handle work_area
    PRIORITY_PENALTY_LOW = 50_000               # Agent has low priority for work_area
    DISTANCE_WEIGHT = 100                       # Cost per grid cell of travel
    PRIORITY_THRESHOLD_GOOD = 10                # Priority <= this is considered good

    def __init__(self, data_manager, route_calculator=None):
        """
        Initialize assignment cost calculator

        Args:
            data_manager: DataManager instance with agent configuration
            route_calculator: Optional RouteCalculator for precise distance calculation

        Configuration Loaded:
            - agent_types with work_area_priorities
            - Work area definitions
        """
        self.data_manager = data_manager
        self.route_calculator = route_calculator

        # Load agent configuration from data_manager
        self.agent_config = []
        self._load_agent_configuration()

        print("[COST-CALC] Calculador de costos inicializado con configuracion WorkArea.")

    def calculate_cost(self, operator, work_order, current_position: Optional[Tuple[int, int]] = None) -> CostResult:
        """
        Calculate assignment cost for operator -> work_order pairing

        Args:
            operator: BaseOperator instance (GroundOperator or Forklift)
            work_order: WorkOrder instance to be assigned
            current_position: Optional (x, y) tuple of operator's current position
                            If None, uses operator.posicion_grilla

        Returns:
            CostResult with total_cost and detailed breakdown

        Cost Components:
            1. Priority Score: operator.get_priority_for_work_area(work_order.work_area)
            2. Priority Penalty: Based on priority_score (0, LOW, or INCOMPATIBLE)
            3. Distance Cost: Estimated travel distance to WorkOrder location
            4. Total Cost: priority_penalty + (distance * distance_weight)

        Example:
            >>> cost = calculator.calculate_cost(ground_op, work_order_1)
            >>> if cost.total_cost < 1000:
            ...     print("Good assignment!")
        """
        work_area = work_order.work_area

        # Component 1: Work Area Priority
        # Lower number = higher priority (1 is best)
        priority_score = operator.get_priority_for_work_area(work_area)

        # Component 2: Priority Penalty
        if priority_score == 999:
            # Agent is incompatible with this work area
            priority_penalty = self.PRIORITY_PENALTY_INCOMPATIBLE
        elif priority_score > self.PRIORITY_THRESHOLD_GOOD:
            # Agent has low priority for this work area
            priority_penalty = self.PRIORITY_PENALTY_LOW
        else:
            # Agent has good priority for this work area (1-10)
            priority_penalty = 0.0

        # Component 3: Distance Cost
        # Use operator's current position or default to posicion_grilla
        start_pos = current_position
        if start_pos is None:
            if hasattr(operator, 'posicion_grilla'):
                start_pos = operator.posicion_grilla
            else:
                # Fallback: use (0, 0) if no position available
                start_pos = (0, 0)

        distance = self._calculate_distance(start_pos, work_order.ubicacion)
        distance_cost = distance * self.DISTANCE_WEIGHT

        # Component 4: Total Cost
        total_cost = priority_penalty + distance_cost

        # Build detailed breakdown for debugging
        breakdown = {
            'agent_id': operator.id,
            'agent_type': type(operator).__name__,
            'work_order_id': work_order.id,
            'work_area': work_area,
            'priority_score': priority_score,
            'priority_penalty': priority_penalty,
            'distance': distance,
            'distance_cost': distance_cost,
            'start_position': start_pos,
            'target_position': work_order.ubicacion,
        }

        # Log calculation (format matches production logs)
        print(f"[COST-CALC] {operator.tipo}_{operator.id} -> {work_area}: "
              f"priority={priority_score}, penalty={int(priority_penalty)}, "
              f"distance={int(distance)}, total={int(total_cost)}")

        return CostResult(
            total_cost=total_cost,
            priority_score=priority_score,
            priority_penalty=priority_penalty,
            distance_cost=distance_cost,
            breakdown=breakdown
        )

    def calculate_costs_for_candidates(self, operator, work_orders: List,
                                      current_position: Optional[Tuple[int, int]] = None) -> List[CostResult]:
        """
        Calculate costs for multiple work orders (batch mode)

        Evaluates all candidate WorkOrders for a single operator,
        useful for finding the best match among many options.

        Args:
            operator: BaseOperator instance
            work_orders: List of WorkOrder instances to evaluate
            current_position: Optional current position of operator

        Returns:
            List of CostResult, sorted by total_cost (ascending = better first)

        Usage:
            >>> results = calculator.calculate_costs_for_candidates(op, pending_wos)
            >>> best_match = results[0]  # Lowest cost
        """
        results = []

        for wo in work_orders:
            cost_result = self.calculate_cost(operator, wo, current_position)
            results.append(cost_result)

        # Sort by total_cost (ascending = better assignments first)
        results.sort(key=lambda r: r.total_cost)

        return results

    def find_best_assignment(self, operators: List, work_orders: List) -> Optional[Tuple]:
        """
        Find globally optimal assignment across all operators and WorkOrders

        Uses greedy approach to find the best (operator, work_order) pairing
        based on minimum total_cost.

        Args:
            operators: List of available BaseOperator instances
            work_orders: List of pending WorkOrder instances

        Returns:
            Tuple (best_operator, best_work_order, cost_result) or None if no valid match

        Algorithm:
            1. For each available operator, calculate cost to each WorkOrder
            2. Find global minimum cost across all pairings
            3. Return (operator, WorkOrder, cost) triple

        Note:
            This is a greedy approach, not an optimal assignment problem solution.
            For optimal global assignment, consider Hungarian algorithm (future).

        Example:
            >>> match = calculator.find_best_assignment(idle_ops, pending_wos)
            >>> if match:
            ...     operator, wo, cost = match
            ...     assign_work_order(operator, wo)
        """
        best_cost = float('inf')
        best_match = None

        for operator in operators:
            # Skip operators that are not available for new assignments
            if not self._is_operator_available(operator):
                continue

            for wo in work_orders:
                # Skip work orders that are already assigned
                if hasattr(wo, 'status') and wo.status != 'pending':
                    continue

                cost_result = self.calculate_cost(operator, wo)

                if cost_result.total_cost < best_cost:
                    best_cost = cost_result.total_cost
                    best_match = (operator, wo, cost_result)

        return best_match

    def _calculate_distance(self, from_pos: Tuple[int, int],
                          to_pos: Tuple[int, int]) -> float:
        """
        Calculate estimated travel distance between two grid positions

        Uses multiple strategies with fallbacks:
        1. RouteCalculator with pathfinding (most accurate)
        2. Manhattan distance (good for grid-based movement)
        3. Euclidean distance (fallback)

        Args:
            from_pos: Starting (x, y) grid position
            to_pos: Destination (x, y) grid position

        Returns:
            Estimated distance as float (in grid cells)
        """
        # Strategy 1: Use RouteCalculator with pathfinding if available
        if self.route_calculator and hasattr(self.route_calculator, 'pathfinder'):
            try:
                path = self.route_calculator.pathfinder.find_path(from_pos, to_pos)
                if path:
                    return float(len(path))  # Path length in grid cells
            except Exception:
                # Pathfinding failed, fall through to heuristics
                pass

        # Strategy 2: Manhattan distance (good for grid-based movement)
        # Assumes 4-directional or 8-directional movement
        dx = abs(to_pos[0] - from_pos[0])
        dy = abs(to_pos[1] - from_pos[1])
        manhattan = dx + dy

        return float(manhattan)

    def _is_operator_available(self, operator) -> bool:
        """
        Check if operator is available for new assignment

        Args:
            operator: BaseOperator instance

        Returns:
            True if operator can accept new work, False otherwise

        Availability Checks:
            - Not currently executing a tour
            - In idle state
            - Not in error state

        Note:
            This is a basic check. Advanced availability logic
            (e.g., checking capacity, maintenance) can be added here.
        """
        # Check if operator has active tour
        if hasattr(operator, 'tour_actual') and operator.tour_actual:
            return False

        # Check if operator is in idle state
        if hasattr(operator, 'estado'):
            if operator.estado not in ['idle', 'disponible', 'waiting']:
                return False

        # Operator is available
        return True

    def _load_agent_configuration(self):
        """
        Load agent configuration from DataManager

        Extracts:
            - agent_types list with work_area_priorities
            - Configuration for debugging and validation

        Stored in self.agent_config for reference
        """
        if not self.data_manager:
            print("[COST-CALC WARNING] No DataManager provided - using defaults")
            self.agent_config = []
            return

        # Try to get configuration from data_manager
        if hasattr(self.data_manager, 'configuracion'):
            config = self.data_manager.configuracion
            self.agent_config = config.get('agent_types', [])

            # Debug: show loaded configuration
            if self.agent_config:
                num_agents = len(self.agent_config)
                print(f"[COST-CALC] Configuration loaded for {num_agents} agent type(s)")
        else:
            print("[COST-CALC WARNING] DataManager has no configuration - using defaults")
            self.agent_config = []

    def get_cost_parameters(self) -> Dict[str, float]:
        """
        Get current cost calculation parameters

        Returns:
            Dict with tunable cost parameters

        Useful for:
            - Parameter tuning and optimization
            - Debugging cost calculations
            - Exporting configuration
        """
        return {
            'PRIORITY_PENALTY_INCOMPATIBLE': self.PRIORITY_PENALTY_INCOMPATIBLE,
            'PRIORITY_PENALTY_LOW': self.PRIORITY_PENALTY_LOW,
            'DISTANCE_WEIGHT': self.DISTANCE_WEIGHT,
            'PRIORITY_THRESHOLD_GOOD': self.PRIORITY_THRESHOLD_GOOD,
        }

    def set_cost_parameters(self, **params):
        """
        Update cost calculation parameters

        Args:
            **params: Keyword arguments for parameter updates

        Example:
            >>> calculator.set_cost_parameters(
            ...     DISTANCE_WEIGHT=150,
            ...     PRIORITY_PENALTY_LOW=75000
            ... )

        Useful for:
            - Runtime parameter tuning
            - A/B testing different strategies
            - Adapting to different warehouse configurations
        """
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
                print(f"[COST-CALC] Updated {key} = {value}")
            else:
                print(f"[COST-CALC WARNING] Unknown parameter: {key}")

    def __repr__(self):
        route_calc_status = "ACTIVE" if self.route_calculator else "DISABLED"
        return (f"AssignmentCostCalculator("
                f"agents={len(self.agent_config)}, "
                f"route_calc={route_calc_status})")
