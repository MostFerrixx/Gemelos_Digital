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


class Dispatcher:
    """Dispatcher V2.6 - Manages work order assignment and distribution"""

    def __init__(self, env: simpy.Environment, almacen: 'AlmacenMejorado'):
        self.env = env
        self.almacen = almacen
        self.lista_maestra_work_orders: List[WorkOrder] = []
        self.work_orders_completadas_historicas: List[WorkOrder] = []
        self.work_orders_total_inicial = 0
        self.initial_work_orders_snapshot = []

    def agregar_work_order(self, work_order: WorkOrder):
        """Add a work order to the master list"""
        self.lista_maestra_work_orders.append(work_order)
        self.work_orders_total_inicial = len(self.lista_maestra_work_orders)

    def completar_work_order(self, work_order: WorkOrder):
        """Mark a work order as completed and move to history"""
        if work_order in self.lista_maestra_work_orders:
            self.lista_maestra_work_orders.remove(work_order)
        work_order.status = "completed"
        work_order.tiempo_fin = self.env.now
        self.work_orders_completadas_historicas.append(work_order)

    def dispatcher_process(self, operarios: List[Any]):
        """
        SimPy process for dispatching work orders to agents
        This is a placeholder - actual implementation would be in dispatcher.py
        """
        while True:
            # Placeholder logic - real implementation in dispatcher.py module
            yield self.env.timeout(1.0)

            if self.almacen.simulacion_ha_terminado():
                break


class AlmacenMejorado:
    """
    Improved Warehouse Class - Main simulation entity
    Manages inventory, orders, and coordinates agent activities
    """

    def __init__(self, env: simpy.Environment, configuracion: Dict[str, Any],
                 layout_manager=None, pathfinder=None, data_manager=None,
                 cost_calculator=None, simulador=None, visual_event_queue=None):
        """
        Initialize warehouse with configuration and dependencies

        Args:
            env: SimPy environment
            configuracion: Configuration dictionary from config.json
            layout_manager: LayoutManager instance for TMX map handling
            pathfinder: Pathfinder instance for A* navigation
            data_manager: DataManager instance for warehouse data
            cost_calculator: AssignmentCostCalculator for task assignment
            simulador: Reference to main simulator (optional)
            visual_event_queue: Multiprocessing queue for visual events (optional)
        """
        self.env = env
        self.configuracion = configuracion
        self.layout_manager = layout_manager
        self.pathfinder = pathfinder
        self.data_manager = data_manager
        self.cost_calculator = cost_calculator
        self.simulador = simulador
        self.visual_event_queue = visual_event_queue

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

        # Dispatcher V2.6
        self.dispatcher = Dispatcher(env, self)

        # Event log for analytics
        self.event_log: List[Dict[str, Any]] = []

        # Agent configuration
        self.num_operarios_total = configuracion.get('num_operarios_total', 3)

        # Simulation state
        self._simulation_finished = False

        print(f"[ALMACEN] AlmacenMejorado inicializado:")
        print(f"  - Total ordenes configuradas: {self.total_ordenes}")
        print(f"  - Operarios totales: {self.num_operarios_total}")
        print(f"  - Layout Manager: {'ACTIVO' if layout_manager else 'NO DISPONIBLE'}")
        print(f"  - Data Manager: {'ACTIVO' if data_manager else 'NO DISPONIBLE'}")

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

        # Generate work orders
        wo_counter = 0
        order_counter = 1

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

                # Create work order
                work_order = WorkOrder(
                    work_order_id=f"WO-{wo_counter:04d}",
                    order_id=f"ORD-{order_counter:04d}",
                    tour_id=f"TOUR-{order_counter:04d}",
                    sku=sku,
                    cantidad=random.randint(1, 5),
                    ubicacion=ubicacion,
                    work_area=work_area,
                    pick_sequence=wo_counter
                )

                self.dispatcher.agregar_work_order(work_order)

            order_counter += 1

        print(f"[ALMACEN] Generadas {len(self.dispatcher.lista_maestra_work_orders)} WorkOrders")
        print(f"[ALMACEN] Distribucion por tipo: {self.distribucion_tipos}")

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
        # Check if all work orders are completed
        if not self.dispatcher.lista_maestra_work_orders:
            # All work orders completed
            if not self._simulation_finished:
                self._simulation_finished = True
                print(f"[ALMACEN] Simulacion finalizada en t={self.env.now:.2f}")
                print(f"[ALMACEN] WorkOrders completadas: {self.workorders_completadas_count}")
                print(f"[ALMACEN] Tareas completadas: {self.tareas_completadas_count}")
            return True

        return False

    def incrementar_contador_workorders(self):
        """Increment WorkOrders completed counter"""
        self.workorders_completadas_count += 1

    def incrementar_contador_tareas(self):
        """Increment picking tasks completed counter (legacy)"""
        self.tareas_completadas_count += 1

    def registrar_evento(self, tipo: str, datos: Dict[str, Any]):
        """
        Register an event in the event log for analytics

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

    def __repr__(self):
        return (f"AlmacenMejorado(ordenes={self.total_ordenes}, "
                f"wos_completadas={self.workorders_completadas_count}, "
                f"tareas={self.tareas_completadas_count})")
