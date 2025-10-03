# -*- coding: utf-8 -*-
"""
Dispatcher Module - Orchestrates WorkOrder Assignment to Operators
Digital Twin Warehouse Simulator

Manages:
- Master WorkOrder queue (pending, assigned, completed)
- Operator availability monitoring
- Assignment decisions using AssignmentCostCalculator
- Tour creation with RouteCalculator
- Dispatch strategies (FIFO, Global Optimization, Proximity)

Author: Digital Twin Warehouse Team
Version: V11 - Migration Phase 3
"""

import simpy
from typing import List, Dict, Optional, Any, Tuple
import math


class DispatcherV11:
    """
    Dispatcher V11 - Central orchestrator for WorkOrder assignment

    The Dispatcher acts as the "brain" of the warehouse operation, managing:
    1. WorkOrder lifecycle (pending -> assigned -> in_progress -> completed)
    2. Operator availability tracking
    3. Intelligent task assignment using cost calculation
    4. Tour optimization for multi-stop routes
    5. Strategy-based dispatch (FIFO, Global Optimization, Proximity)

    Integration:
    - Uses AssignmentCostCalculator for cost-based assignment decisions
    - Uses RouteCalculator for optimal multi-stop tour planning
    - Interfaces with GroundOperator/Forklift for task execution
    - Receives WorkOrders from AlmacenMejorado
    """

    def __init__(self,
                 env: simpy.Environment,
                 almacen: Any,
                 assignment_calculator: Any,
                 route_calculator: Any,
                 data_manager: Any,
                 configuracion: Dict[str, Any]):
        """
        Initialize Dispatcher with dependencies

        Args:
            env: SimPy Environment for simulation time
            almacen: AlmacenMejorado instance (warehouse)
            assignment_calculator: AssignmentCostCalculator for cost evaluation
            route_calculator: RouteCalculator for tour optimization
            data_manager: DataManager for layout/picking data
            configuracion: Configuration dict from config.json
        """
        self.env = env
        self.almacen = almacen
        self.assignment_calculator = assignment_calculator
        self.route_calculator = route_calculator
        self.data_manager = data_manager
        self.configuracion = configuracion

        # WorkOrder State Management
        self.lista_maestra_work_orders: List[Any] = []          # All WOs (source of truth)
        self.work_orders_pendientes: List[Any] = []              # PENDING state
        self.work_orders_asignados: Dict[str, List[Any]] = {}    # {operator_id: [WO1, WO2...]}
        self.work_orders_en_progreso: Dict[str, Any] = {}        # {operator_id: current_WO}
        self.work_orders_completados: List[Any] = []             # COMPLETED state

        # Operator Tracking
        self.operadores_disponibles: List[Any] = []              # Idle operators
        self.operadores_activos: Dict[str, Any] = {}             # {operator_id: assigned_tour}

        # Dispatch Strategy (from config.json)
        self.estrategia = configuracion.get('dispatch_strategy', 'Optimizacion Global')

        # Statistics
        self.total_asignaciones = 0
        self.total_tours_creados = 0

        # Configuration parameters
        self.max_wos_por_tour = configuracion.get('max_wos_por_tour', 20)
        self.radio_cercania = configuracion.get('radio_cercania', 100)  # Grid cells

        print(f"[DISPATCHER] Inicializado con estrategia: '{self.estrategia}'")
        print(f"[DISPATCHER] Max WOs por tour: {self.max_wos_por_tour}, "
              f"Radio cercania: {self.radio_cercania}")

    def agregar_work_orders(self, work_orders: List[Any]) -> None:
        """
        Add new WorkOrders to master list and pending queue

        Args:
            work_orders: List[WorkOrder] - New orders from warehouse generation
        """
        if not work_orders:
            return

        for wo in work_orders:
            self.lista_maestra_work_orders.append(wo)
            self.work_orders_pendientes.append(wo)
            wo.status = "pending"

        print(f"[DISPATCHER] {self.env.now:.2f} - Agregados {len(work_orders)} WorkOrders. "
              f"Total pendientes: {len(self.work_orders_pendientes)}")

    def registrar_operador_disponible(self, operator: Any) -> None:
        """
        Register operator as available for work assignment

        Args:
            operator: GroundOperator or Forklift instance
        """
        if operator not in self.operadores_disponibles:
            self.operadores_disponibles.append(operator)
            print(f"[DISPATCHER] {self.env.now:.2f} - Operador {operator.type}_{operator.id} "
                  f"registrado como disponible (pos: {operator.current_position})")

    def solicitar_asignacion(self, operator: Any) -> Optional[Dict[str, Any]]:
        """
        Main assignment logic - called by Operator when idle

        This is the core dispatch method that:
        1. Checks if work is available
        2. Selects candidate WorkOrders based on strategy
        3. Calculates assignment costs
        4. Builds optimal tour
        5. Updates state and returns tour to operator

        Args:
            operator: GroundOperator or Forklift instance requesting work

        Returns:
            tour: Dictionary with:
                {
                    'work_orders': [WO1, WO2, ...],
                    'route': RouteCalculator result dict,
                    'total_distance': float,
                    'total_volume': float,
                    'num_stops': int
                }
                or None if no work available
        """
        # Step 1: Check if work is available
        if not self.work_orders_pendientes:
            print(f"[DISPATCHER] {self.env.now:.2f} - No hay WorkOrders pendientes para "
                  f"{operator.type}_{operator.id}")
            return None

        print(f"[DISPATCHER] {self.env.now:.2f} - Operador {operator.type}_{operator.id} "
              f"solicita asignacion (pos: {operator.current_position})")

        # Step 2: Select candidate WorkOrders based on strategy
        candidatos = self._seleccionar_work_orders_candidatos(operator)

        if not candidatos:
            print(f"[DISPATCHER] No hay candidatos viables para {operator.type}_{operator.id}")
            return None

        print(f"[DISPATCHER] Estrategia '{self.estrategia}' selecciono {len(candidatos)} candidatos")

        # Step 3: Calculate assignment costs and select best batch
        selected_work_orders = self._seleccionar_mejor_batch(operator, candidatos)

        if not selected_work_orders:
            print(f"[DISPATCHER] No se pudo seleccionar batch para {operator.type}_{operator.id}")
            return None

        # Step 4: Build optimal tour
        tour = self._construir_tour(operator, selected_work_orders)

        if tour is None or not tour.get('success', False):
            print(f"[DISPATCHER ERROR] Fallo al construir tour para {operator.type}_{operator.id}")
            return None

        # Step 5: Update state - mark as assigned
        self._marcar_asignados(operator, selected_work_orders)

        # Step 6: Build return tour structure
        tour_result = {
            'work_orders': selected_work_orders,
            'route': tour,
            'total_distance': tour['total_distance'],
            'total_volume': sum(wo.calcular_volumen_restante() for wo in selected_work_orders),
            'num_stops': len(selected_work_orders)
        }

        self.total_asignaciones += 1
        self.total_tours_creados += 1

        print(f"[DISPATCHER] Tour asignado a {operator.type}_{operator.id}: "
              f"{tour_result['num_stops']} WOs, "
              f"distancia: {tour_result['total_distance']:.1f}, "
              f"volumen: {tour_result['total_volume']}")

        return tour_result

    def _seleccionar_work_orders_candidatos(self, operator: Any) -> List[Any]:
        """
        Strategy-specific WorkOrder candidate selection

        Args:
            operator: Operator requesting work

        Returns:
            List[WorkOrder] - Candidate WOs for evaluation
        """
        if self.estrategia == "FIFO Estricto":
            return self._estrategia_fifo(operator)
        elif self.estrategia == "Optimizacion Global":
            return self._estrategia_optimizacion_global(operator)
        elif self.estrategia == "Cercania":
            return self._estrategia_cercania(operator)
        else:
            # Default to FIFO if unknown strategy
            print(f"[DISPATCHER WARN] Estrategia desconocida '{self.estrategia}', usando FIFO")
            return self._estrategia_fifo(operator)

    def _estrategia_fifo(self, operator: Any) -> List[Any]:
        """
        FIFO Strategy - Take first N WorkOrders that fit operator capacity

        Args:
            operator: Operator instance

        Returns:
            List[WorkOrder] - First N WOs that fit capacity
        """
        # Filter by work area compatibility
        candidatos = [wo for wo in self.work_orders_pendientes
                     if operator.can_handle_work_area(wo.work_area)]

        # Take up to max_wos_por_tour or until capacity filled
        selected = []
        volume_acumulado = 0

        for wo in candidatos[:self.max_wos_por_tour]:
            wo_volume = wo.calcular_volumen_restante()
            if volume_acumulado + wo_volume <= operator.capacity:
                selected.append(wo)
                volume_acumulado += wo_volume
            else:
                break  # Capacity full

        return selected

    def _estrategia_optimizacion_global(self, operator: Any) -> List[Any]:
        """
        Global Optimization Strategy - Evaluate ALL pending WorkOrders

        Uses AssignmentCostCalculator to evaluate all WOs and select
        the best batch based on total cost.

        Args:
            operator: Operator instance

        Returns:
            List[WorkOrder] - Best WOs based on cost calculation
        """
        # Filter by work area compatibility
        candidatos = [wo for wo in self.work_orders_pendientes
                     if operator.can_handle_work_area(wo.work_area)]

        if not candidatos:
            return []

        # Return all candidates - cost calculation happens in _seleccionar_mejor_batch
        # Limit to max_wos_por_tour for performance
        return candidatos[:self.max_wos_por_tour * 3]  # Evaluate more options

    def _estrategia_cercania(self, operator: Any) -> List[Any]:
        """
        Proximity Strategy - Filter WorkOrders within radius, then optimize

        Args:
            operator: Operator instance

        Returns:
            List[WorkOrder] - WOs within proximity radius
        """
        if operator.current_position is None:
            # Fallback to FIFO if no position known
            return self._estrategia_fifo(operator)

        # Filter by work area compatibility AND proximity
        candidatos = []
        op_x, op_y = operator.current_position

        for wo in self.work_orders_pendientes:
            if not operator.can_handle_work_area(wo.work_area):
                continue

            wo_x, wo_y = wo.ubicacion
            distance = math.sqrt((wo_x - op_x)**2 + (wo_y - op_y)**2)

            if distance <= self.radio_cercania:
                candidatos.append(wo)

        # Limit to max_wos_por_tour
        return candidatos[:self.max_wos_por_tour * 2]

    def _seleccionar_mejor_batch(self, operator: Any, candidatos: List[Any]) -> List[Any]:
        """
        Select best batch of WorkOrders from candidates using cost calculation

        Args:
            operator: Operator instance
            candidatos: List of candidate WorkOrders

        Returns:
            List[WorkOrder] - Best batch that fits capacity
        """
        if not candidatos:
            return []

        # Get operator's current position (or depot if none)
        current_pos = operator.current_position
        if current_pos is None:
            # Use first outbound staging location as default
            staging_locs = self.data_manager.get_outbound_staging_locations()
            current_pos = staging_locs.get(1, (0, 0))

        # Calculate costs for all candidates
        costos = []
        for wo in candidatos:
            cost_result = self.assignment_calculator.calculate_cost(
                operator, wo, current_pos
            )
            costos.append((wo, cost_result))

        # Sort by total cost (lower is better)
        costos.sort(key=lambda x: x[1].total_cost)

        # Select best WOs that fit capacity
        selected = []
        volume_acumulado = 0

        for wo, cost_result in costos:
            wo_volume = wo.calcular_volumen_restante()
            if volume_acumulado + wo_volume <= operator.capacity:
                selected.append(wo)
                volume_acumulado += wo_volume

                if len(selected) >= self.max_wos_por_tour:
                    break  # Max tour size reached

        return selected

    def _construir_tour(self, operator: Any, work_orders: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Build optimal tour using RouteCalculator

        Args:
            operator: Operator instance
            work_orders: List of WorkOrders to visit

        Returns:
            RouteCalculator result dict or None if failed
        """
        if not work_orders:
            return None

        # Get start position (operator's current position or depot)
        start_pos = operator.current_position
        if start_pos is None:
            # Use depot as start
            staging_locs = self.data_manager.get_outbound_staging_locations()
            start_pos = staging_locs.get(1, (0, 0))

        # Calculate optimal route
        try:
            route_result = self.route_calculator.calculate_route(
                start_position=start_pos,
                work_orders=work_orders,
                return_to_start=True  # Return to staging area after picks
            )

            if route_result and route_result.get('success', False):
                return route_result
            else:
                print(f"[DISPATCHER ERROR] RouteCalculator fallo: {route_result.get('errors', [])}")
                return None

        except Exception as e:
            print(f"[DISPATCHER ERROR] Excepcion al calcular ruta: {e}")
            return None

    def _marcar_asignados(self, operator: Any, work_orders: List[Any]) -> None:
        """
        Move WorkOrders from pending to assigned state

        Args:
            operator: Operator instance
            work_orders: List of WorkOrders being assigned
        """
        operator_id = f"{operator.type}_{operator.id}"

        for wo in work_orders:
            # Remove from pending
            if wo in self.work_orders_pendientes:
                self.work_orders_pendientes.remove(wo)

            # Add to assigned
            if operator_id not in self.work_orders_asignados:
                self.work_orders_asignados[operator_id] = []
            self.work_orders_asignados[operator_id].append(wo)

            # Update WorkOrder state
            wo.status = "assigned"
            wo.assigned_agent_id = operator_id
            wo.tiempo_inicio = self.env.now

        # Update operator tracking
        if operator in self.operadores_disponibles:
            self.operadores_disponibles.remove(operator)

        self.operadores_activos[operator_id] = {
            'operator': operator,
            'work_orders': work_orders,
            'tiempo_asignacion': self.env.now
        }

    def notificar_inicio_trabajo(self, operator: Any, work_order: Any) -> None:
        """
        Callback when operator starts working on a WorkOrder

        Args:
            operator: Operator instance
            work_order: WorkOrder being started
        """
        operator_id = f"{operator.type}_{operator.id}"

        # Move to in_progress
        work_order.status = "in_progress"
        self.work_orders_en_progreso[operator_id] = work_order

        print(f"[DISPATCHER] {self.env.now:.2f} - {operator_id} inicio WO {work_order.id}")

    def notificar_completado(self, operator: Any, work_orders_completados: List[Any]) -> None:
        """
        Callback when operator finishes tour

        Args:
            operator: Operator instance
            work_orders_completados: List[WorkOrder] that were completed
        """
        operator_id = f"{operator.type}_{operator.id}"

        # Move WorkOrders from assigned to completed
        for wo in work_orders_completados:
            # Remove from assigned
            if operator_id in self.work_orders_asignados:
                if wo in self.work_orders_asignados[operator_id]:
                    self.work_orders_asignados[operator_id].remove(wo)

            # Remove from in_progress
            if operator_id in self.work_orders_en_progreso:
                if self.work_orders_en_progreso[operator_id] == wo:
                    del self.work_orders_en_progreso[operator_id]

            # Add to completed
            self.work_orders_completados.append(wo)

            # Update WorkOrder state
            wo.status = "completed"
            wo.tiempo_fin = self.env.now

        # Operator back to available
        if operator_id in self.operadores_activos:
            del self.operadores_activos[operator_id]

        if operator not in self.operadores_disponibles:
            self.operadores_disponibles.append(operator)

        tiempo_total = self.env.now - work_orders_completados[0].tiempo_inicio if work_orders_completados else 0

        print(f"[DISPATCHER] {self.env.now:.2f} - {operator_id} completo {len(work_orders_completados)} WOs "
              f"en {tiempo_total:.2f}s simulados. "
              f"Total completados: {len(self.work_orders_completados)}/{len(self.lista_maestra_work_orders)}")

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Return current dispatcher statistics

        Returns:
            Dictionary with current state metrics:
            {
                'pendientes': int,
                'asignados': int,
                'en_progreso': int,
                'completados': int,
                'total': int,
                'operadores_disponibles': int,
                'operadores_activos': int,
                'total_asignaciones': int,
                'total_tours': int,
                'porcentaje_completado': float
            }
        """
        total_asignados = sum(len(wos) for wos in self.work_orders_asignados.values())

        stats = {
            'pendientes': len(self.work_orders_pendientes),
            'asignados': total_asignados,
            'en_progreso': len(self.work_orders_en_progreso),
            'completados': len(self.work_orders_completados),
            'total': len(self.lista_maestra_work_orders),
            'operadores_disponibles': len(self.operadores_disponibles),
            'operadores_activos': len(self.operadores_activos),
            'total_asignaciones': self.total_asignaciones,
            'total_tours': self.total_tours_creados,
            'porcentaje_completado': (len(self.work_orders_completados) / len(self.lista_maestra_work_orders) * 100)
                                     if self.lista_maestra_work_orders else 0.0
        }

        return stats

    def imprimir_resumen(self) -> None:
        """Print current dispatcher state summary"""
        stats = self.obtener_estadisticas()

        print("\n" + "="*70)
        print(f"RESUMEN DISPATCHER - Tiempo Simulado: {self.env.now:.2f}s")
        print("="*70)
        print(f"WorkOrders:")
        print(f"  Pendientes:    {stats['pendientes']:4d}")
        print(f"  Asignados:     {stats['asignados']:4d}")
        print(f"  En Progreso:   {stats['en_progreso']:4d}")
        print(f"  Completados:   {stats['completados']:4d}")
        print(f"  Total:         {stats['total']:4d}")
        print(f"  % Completado:  {stats['porcentaje_completado']:5.1f}%")
        print(f"\nOperadores:")
        print(f"  Disponibles:   {stats['operadores_disponibles']:4d}")
        print(f"  Activos:       {stats['operadores_activos']:4d}")
        print(f"\nMetricas:")
        print(f"  Asignaciones:  {stats['total_asignaciones']:4d}")
        print(f"  Tours:         {stats['total_tours']:4d}")
        print("="*70 + "\n")

    def simulacion_ha_terminado(self) -> bool:
        """
        Check if all WorkOrders have been completed

        Returns:
            True if all WOs are completed, False otherwise
        """
        if not self.lista_maestra_work_orders:
            return False

        return len(self.work_orders_completados) >= len(self.lista_maestra_work_orders)


# Export main class
__all__ = ['DispatcherV11']
