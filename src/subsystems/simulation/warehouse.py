# -*- coding: utf-8 -*-
"""
Warehouse Management Module - AlmacenMejorado Class
Digital Twin Warehouse Simulator
"""

import simpy
import random
from typing import Optional, List, Dict, Any


class SKU:
    """Stock Keeping Unit - Represents a product in the warehouse"""

    def __init__(self, sku_id: str, volumen: int, descripcion: str = ""):
        self.id = sku_id
        self.volumen = volumen
        self.descripcion = descripcion

    def __repr__(self):
        return f"SKU({self.id}, vol={self.volumen})"


class WorkOrder:
    """Work Order - Represents a picking task"""

    def __init__(self, work_order_id: str, order_id: str, tour_id: str,
                 sku: SKU, cantidad: int, ubicacion: tuple,
                 work_area: str, pick_sequence: int):
        self.id = work_order_id
        self.order_id = order_id
        self.tour_id = tour_id
        self.sku = sku
        self.cantidad_inicial = cantidad
        self.cantidad_restante = cantidad
        self.ubicacion = ubicacion
        self.work_area = work_area
        self.pick_sequence = pick_sequence
        self.status = "pending"
        self.assigned_agent_id = None
        self.tiempo_inicio = None
        self.tiempo_fin = None

    @property
    def sku_id(self) -> str:
        """Get SKU ID from SKU object"""
        return self.sku.id if self.sku else "N/A"
    
    @property
    def sku_name(self) -> str:
        """Get SKU name (same as ID for now)"""
        return self.sku.id if self.sku else "N/A"
    
    @property
    def cantidad_total(self) -> int:
        """Alias for cantidad_inicial"""
        return self.cantidad_inicial
    
    @property
    def volumen_restante(self) -> int:
        """Calculate remaining volume"""
        return self.cantidad_restante * self.sku.volumen if self.sku else 0
    
    @property
    def staging_id(self) -> int:
        """Get staging ID (placeholder)"""
        return 1  # Default staging
    
    @property
    def work_group(self) -> str:
        """Get work group (derived from work_area)"""
        # Map work_area to work_group
        if 'Ground' in self.work_area:
            return 'WG_A'
        elif 'Piso' in self.work_area:
            return 'WG_B'
        elif 'Rack' in self.work_area:
            return 'WG_C'
        return 'WG_A'  # Default

    def calcular_volumen_restante(self) -> int:
        """Calculate remaining volume for this work order"""
        return self.cantidad_restante * self.sku.volumen

    def to_dict(self) -> Dict[str, Any]:
        """Convert work order to dictionary for serialization"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'tour_id': self.tour_id,
            'sku_id': self.sku.id if self.sku else "N/A",
            'cantidad_inicial': self.cantidad_inicial,
            'cantidad_restante': self.cantidad_restante,
            'ubicacion': self.ubicacion,
            'work_area': self.work_area,
            'pick_sequence': self.pick_sequence,
            'status': self.status,
            'assigned_agent_id': self.assigned_agent_id,
            'tiempo_inicio': self.tiempo_inicio,
            'tiempo_fin': self.tiempo_fin,
        }

    def __repr__(self):
        return f"WO({self.id}, {self.sku.id}, {self.cantidad_restante}/{self.cantidad_inicial})"


# BUGFIX FASE 1: Dispatcher stub eliminado - usando DispatcherV11 real
# La clase Dispatcher stub (lineas 70-104) ha sido eliminada completamente
# Ahora se usa DispatcherV11 de dispatcher.py con logica completa implementada


class AlmacenMejorado:
    """
    Improved Warehouse Class - Main simulation entity
    Manages inventory, orders, and coordinates agent activities
    """

    def __init__(self, env: simpy.Environment, configuracion: Dict[str, Any],
                 layout_manager=None, pathfinder=None, data_manager=None,
                 cost_calculator=None, route_calculator=None, simulador=None,
                 visual_event_queue=None, replay_buffer=None):
        """
        Initialize warehouse with configuration and dependencies

        BUGFIX FASE 1: Agregado route_calculator para integracion con DispatcherV11
        BUGFIX JSONL: Agregado replay_buffer para generacion de archivos .jsonl

        Args:
            env: SimPy environment
            configuracion: Configuration dictionary from config.json
            layout_manager: LayoutManager instance for TMX map handling
            pathfinder: Pathfinder instance for A* navigation
            data_manager: DataManager instance for warehouse data
            cost_calculator: AssignmentCostCalculator for task assignment
            route_calculator: RouteCalculator for tour optimization
            simulador: Reference to main simulator (optional)
            visual_event_queue: Multiprocessing queue for visual events (optional)
            replay_buffer: ReplayBuffer instance for .jsonl generation (optional)
        """
        self.env = env
        self.configuracion = configuracion
        self.layout_manager = layout_manager
        self.pathfinder = pathfinder
        self.data_manager = data_manager
        self.cost_calculator = cost_calculator
        self.route_calculator = route_calculator
        self.simulador = simulador
        self.visual_event_queue = visual_event_queue
        self.replay_buffer = replay_buffer
        

        # Inventory and catalog
        self.catalogo_skus: Dict[str, SKU] = {}
        self.inventario: Dict[str, int] = {}

        # Order configuration
        self.total_ordenes = configuracion.get('total_ordenes', 300)
        self.distribucion_tipos = configuracion.get('distribucion_tipos', {
            'pequeno': {'porcentaje': 60, 'volumen': 5},
            'mediano': {'porcentaje': 30, 'volumen': 25},
            'grande': {'porcentaje': 10, 'volumen': 80}
        })

        # Counters (dual system: WorkOrders and PickingTasks)
        self.workorders_completadas_count = 0  # Main KPI counter
        self.tareas_completadas_count = 0      # Legacy picking tasks counter

        # Event log for analytics
        self.event_log: List[Dict[str, Any]] = []

        # Agent configuration
        self.num_operarios_total = configuracion.get('num_operarios_total', 3)

        # Simulation state
        self._simulation_finished = False

        # BUGFIX JSONL: Crear dispatcher DESPUÉS de completar inicialización
        # para evitar problemas de referencia con replay_buffer
        from .dispatcher import DispatcherV11
        self.dispatcher = DispatcherV11(
            env=env,
            almacen=self,
            assignment_calculator=cost_calculator,
            route_calculator=route_calculator,
            data_manager=data_manager,
            configuracion=configuracion
        )

        # BUGFIX CAPACITY VALIDATION: Extract operator capacities from configuration
        self.operator_capacities = {}  # {work_area: max_capacity}
        agent_types = configuracion.get('agent_types', [])

        for agent_config in agent_types:
            agent_type = agent_config.get('type')
            capacity = agent_config.get('capacity', 0)
            work_areas = agent_config.get('work_area_priorities', {})

            # For each work area this agent can handle, track max capacity
            for work_area in work_areas.keys():
                current_max = self.operator_capacities.get(work_area, 0)
                self.operator_capacities[work_area] = max(current_max, capacity)

        # Compute global max capacity (for fallback)
        self.max_operator_capacity = max(
            [agent.get('capacity', 0) for agent in agent_types],
            default=150  # Fallback if no agents defined
        )

        print(f"[ALMACEN] AlmacenMejorado inicializado:")
        print(f"  - Total ordenes configuradas: {self.total_ordenes}")
        print(f"  - Operarios totales: {self.num_operarios_total}")
        print(f"  - Layout Manager: {'ACTIVO' if layout_manager else 'NO DISPONIBLE'}")
        print(f"  - Data Manager: {'ACTIVO' if data_manager else 'NO DISPONIBLE'}")
        print(f"  - Capacidades por work area: {self.operator_capacities}")
        print(f"  - Capacidad maxima global: {self.max_operator_capacity}")

    def _crear_catalogo_y_stock(self):
        """Create SKU catalog and initialize inventory"""
        print("[ALMACEN] Creando catalogo de SKUs y stock inicial...")

        # Create SKUs based on distribution types
        sku_counter = 1
        for tipo, config in self.distribucion_tipos.items():
            volumen = config['volumen']
            # Create multiple SKUs per type
            for i in range(5):  # 5 SKUs per type
                sku_id = f"SKU-{tipo[:3].upper()}-{sku_counter:03d}"
                sku = SKU(sku_id, volumen, f"Producto {tipo} #{i+1}")
                self.catalogo_skus[sku_id] = sku
                self.inventario[sku_id] = 1000  # Initial stock
                sku_counter += 1

        print(f"[ALMACEN] Catalogo creado: {len(self.catalogo_skus)} SKUs")
        print(f"[ALMACEN] Inventario inicial: {sum(self.inventario.values())} unidades")

    def _validar_y_ajustar_cantidad(self, sku: SKU, cantidad_original: int,
                                     work_area: str) -> int:
        """
        Validate WorkOrder quantity against operator capacity

        BUGFIX CAPACITY VALIDATION: Ensures all WorkOrders are physically possible
        by adjusting quantity if total volume exceeds operator capacity.

        Args:
            sku: SKU object with volumen attribute
            cantidad_original: Requested quantity (1-5)
            work_area: Work area identifier

        Returns:
            Adjusted quantity (guaranteed to fit in at least one operator)
        """
        # Calculate total volume
        volumen_total = sku.volumen * cantidad_original

        # Determine max capacity for this work area
        max_capacity = self.operator_capacities.get(
            work_area,
            self.max_operator_capacity  # Fallback to global max
        )

        # Check if volume exceeds capacity
        if volumen_total > max_capacity:
            # Calculate max quantity that fits
            cantidad_ajustada = max_capacity // sku.volumen

            # Ensure at least 1 unit (minimum viable WO)
            cantidad_ajustada = max(1, cantidad_ajustada)

            # Log adjustment
            print(f"[ALMACEN WARNING] WO ajustada: SKU {sku.id} "
                  f"cantidad {cantidad_original} -> {cantidad_ajustada} "
                  f"(volumen {volumen_total} > capacidad {max_capacity})")

            return cantidad_ajustada
        else:
            return cantidad_original

    def _generar_flujo_ordenes(self):
        """Generate work orders flow based on configuration"""
        print(f"[ALMACEN] Generando {self.total_ordenes} ordenes de trabajo...")

        # Get picking points from data manager
        if not self.data_manager or not self.data_manager.puntos_de_picking_ordenados:
            print("[ALMACEN WARNING] No hay puntos de picking disponibles - usando ubicaciones dummy")
            picking_points = [(10, 10), (15, 15), (20, 20)]
            work_areas = ["Area_Ground", "Area_Rack", "Area_Piso_L1"]
        else:
            picking_points = [pp['ubicacion_grilla'] for pp in self.data_manager.puntos_de_picking_ordenados]
            work_areas = [pp.get('work_area', 'Area_Ground') for pp in self.data_manager.puntos_de_picking_ordenados]

        # Generate work orders (collect all first, then add in batch)
        wo_counter = 0
        order_counter = 1
        all_work_orders = []  # BUGFIX FASE 2: Collect all WOs for batch add
        wo_adjusted_count = 0  # BUGFIX CAPACITY VALIDATION: Track adjustments

        for order_num in range(1, self.total_ordenes + 1):
            # Determine order type based on distribution
            rand = random.random() * 100
            cumulative = 0
            tipo_seleccionado = 'pequeno'

            for tipo, config in self.distribucion_tipos.items():
                cumulative += config['porcentaje']
                if rand <= cumulative:
                    tipo_seleccionado = tipo
                    break

            # Select SKU of chosen type
            skus_tipo = [sku for sku in self.catalogo_skus.values()
                        if tipo_seleccionado[:3].upper() in sku.id]
            if not skus_tipo:
                skus_tipo = list(self.catalogo_skus.values())

            sku = random.choice(skus_tipo)

            # Generate 1-3 work orders per order
            num_wos = random.randint(1, 3)

            for wo_num in range(num_wos):
                wo_counter += 1

                # Select picking location
                pick_idx = wo_counter % len(picking_points)
                ubicacion = picking_points[pick_idx]
                work_area = work_areas[pick_idx] if pick_idx < len(work_areas) else "Area_Ground"

                # BUGFIX CAPACITY VALIDATION: Validate quantity before creating WorkOrder
                cantidad_solicitada = random.randint(1, 5)
                cantidad_valida = self._validar_y_ajustar_cantidad(
                    sku=sku,
                    cantidad_original=cantidad_solicitada,
                    work_area=work_area
                )

                # Track adjustments
                if cantidad_valida < cantidad_solicitada:
                    wo_adjusted_count += 1

                # Create work order with validated quantity
                work_order = WorkOrder(
                    work_order_id=f"WO-{wo_counter:04d}",
                    order_id=f"ORD-{order_counter:04d}",
                    tour_id=f"TOUR-{order_counter:04d}",
                    sku=sku,
                    cantidad=cantidad_valida,  # BUGFIX: Use validated quantity
                    ubicacion=ubicacion,
                    work_area=work_area,
                    pick_sequence=wo_counter
                )

                all_work_orders.append(work_order)  # BUGFIX FASE 2: Collect instead of immediate add

            order_counter += 1

        # BUGFIX FASE 2: Add all work orders in one batch (DispatcherV11 uses plural method)
        if all_work_orders:
            self.dispatcher.agregar_work_orders(all_work_orders)

        print(f"[ALMACEN] Generadas {len(self.dispatcher.lista_maestra_work_orders)} WorkOrders")
        print(f"[ALMACEN] Distribucion por tipo: {self.distribucion_tipos}")

        # BUGFIX CAPACITY VALIDATION: Report statistics
        if wo_adjusted_count > 0:
            adjustment_percentage = (wo_adjusted_count / len(all_work_orders)) * 100
            print(f"[ALMACEN] {wo_adjusted_count} WorkOrders ajustadas por capacidad "
                  f"({adjustment_percentage:.1f}%)")
        else:
            print(f"[ALMACEN] Todas las WorkOrders caben dentro de capacidad de operarios")

    def adelantar_tiempo(self, tiempo: float):
        """
        Advance simulation time (utility method for processes)

        Args:
            tiempo: Time units to advance

        Returns:
            SimPy timeout event
        """
        return self.env.timeout(tiempo)

    def simulacion_ha_terminado(self) -> bool:
        """
        Check if simulation has finished

        Returns:
            True if all work orders are completed and no agents are busy
        """
        # BUGFIX: Delegar al dispatcher que tiene la logica correcta
        # (compara completados vs total en lugar de verificar si lista esta vacia)
        terminado = self.dispatcher.simulacion_ha_terminado()
        
        if terminado and not self._simulation_finished:
            self._simulation_finished = True
            print(f"[ALMACEN] Simulacion finalizada en t={self.env.now:.2f}")
            print(f"[ALMACEN] WorkOrders completadas: {self.workorders_completadas_count}")
            print(f"[ALMACEN] Tareas completadas: {self.tareas_completadas_count}")
        
        return terminado

    def incrementar_contador_workorders(self):
        """Increment WorkOrders completed counter"""
        self.workorders_completadas_count += 1

    def incrementar_contador_tareas(self):
        """Increment picking tasks completed counter (legacy)"""
        self.tareas_completadas_count += 1

    def registrar_evento(self, tipo: str, datos: Dict[str, Any]):
        """
        Register an event in the event log for analytics and replay buffer

        BUGFIX JSONL: Ahora tambien escribe eventos al replay_buffer para
        generacion de archivos .jsonl

        Args:
            tipo: Event type (e.g., 'task_completed', 'agent_moved')
            datos: Event data dictionary
        """
        evento = {
            'timestamp': self.env.now,
            'tipo': tipo,
            **datos
        }
        self.event_log.append(evento)
        
        # BUGFIX JSONL: Tambien agregar al replay_buffer para generacion de .jsonl
        if self.replay_buffer is not None:
            # Convertir formato para replay (tipo -> type)
            replay_evento = {
                'type': tipo,
                'timestamp': self.env.now,
                **datos
            }
            self.replay_buffer.add_event(replay_evento)

    def __repr__(self):
        return (f"AlmacenMejorado(ordenes={self.total_ordenes}, "
                f"wos_completadas={self.workorders_completadas_count}, "
                f"tareas={self.tareas_completadas_count})")
