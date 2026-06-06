# -*- coding: utf-8 -*-
"""
Warehouse Management Module - AlmacenMejorado Class
Digital Twin Warehouse Simulator
"""

import simpy
import random
from typing import Optional, List, Dict, Any
from .order_strategies import create_order_strategy, OrderGenerationStrategy


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
                 work_area: str, pick_sequence: int, staging_id: int = 1,
                 qty_requested: int = None, location_id: str = None):
        self.id = work_order_id
        self.order_id = order_id
        self.tour_id = tour_id
        self.sku = sku
        self.cantidad_inicial = cantidad
        self.cantidad_restante = cantidad
        self.ubicacion = ubicacion
        self.work_area = work_area
        self.pick_sequence = pick_sequence
        self._staging_id = staging_id  # Store staging_id as instance variable
        self.status = "released"
        self.assigned_agent_id = None
        self.tiempo_inicio = None
        self.tiempo_fin = None
        
        # ALLOCATION LAYER (V12.1): Track original request vs actual allocation
        # qty_requested: Original quantity from order file
        # qty_allocated: Actual quantity assigned (limited by stock availability)
        # is_partial: True if qty_allocated < qty_requested (stock was insufficient)
        self.qty_requested = qty_requested if qty_requested is not None else cantidad
        self.qty_allocated = cantidad
        self.is_partial = (self.qty_allocated < self.qty_requested)
        # ALLOCATION LAYER (V12.1 - Init #1): real picking location for this WO
        # (location_id from inventory; lets us trace/verify real-location picking)
        self.location_id = location_id

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
        """Get staging ID"""
        return self._staging_id
    
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
            # ALLOCATION LAYER (V12.1)
            'qty_requested': self.qty_requested,
            'qty_allocated': self.qty_allocated,
            'is_partial': self.is_partial,
            'location_id': self.location_id,
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
        
        # Outbound staging distribution
        self.outbound_staging_distribution = configuracion.get('outbound_staging_distribution', {
            '1': 100, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0
        })

        # ============================================================
        # INICIATIVA #2 - CONGESTION (Fase 0)
        # Se LEE el bloque de configuracion pero todavia NO se usa.
        # Por defecto enabled:false / mode:off => comportamiento identico al actual
        # (gate de no-regresion: .jsonl byte-identico al baseline).
        # El motor solo lee; la web/UI solo edita (Ley #3: config.json fuente de verdad).
        # ============================================================
        self.congestion_config = configuracion.get('congestion', {
            'enabled': False,
            'mode': 'off'
        })
        self.congestion_enabled = bool(self.congestion_config.get('enabled', False))
        self.congestion_mode = self.congestion_config.get('mode', 'off')
        from .congestion_manager import CongestionManager
        self.congestion_manager = CongestionManager(
            env=env,
            enabled=self.congestion_enabled,
            mode=self.congestion_mode,
            config=self.congestion_config,
        )
        print(f"[CONGESTION] {self.congestion_manager}")

        # ============================================================
        # INICIATIVA #2 - OPCION C (time-window routing) - Fase 0 (andamiaje)
        # Se crean ReservationTable + SpaceTimePlanner SOLO si timewindow esta
        # activo (enabled + mode:timewindow). Con el flag apagado quedan en None
        # => ningun codigo nuevo se ejecuta => .jsonl byte-identico al baseline.
        # El planner reusa el pathfinder estatico (Ley #6: respeta arquitectura).
        # ============================================================
        self.reservation_table = None
        self.spacetime_planner = None
        if getattr(self.congestion_manager, 'timewindow_active', False):
            tw_cfg = dict(self.congestion_config.get('timewindow', {}))
            from .reservation_table import ReservationTable
            from .spacetime_planner import SpaceTimePlanner
            self.reservation_table = ReservationTable(
                clearance=float(tw_cfg.get('clearance', 0.0))
            )
            if pathfinder is not None:
                self.spacetime_planner = SpaceTimePlanner(
                    pathfinder=pathfinder,
                    reservation_table=self.reservation_table,
                    time_per_cell=0.1,
                    dt_wait=float(tw_cfg.get('dt_wait', 0.1)),
                    max_expansions=int(tw_cfg.get('max_expansions', 20000)),
                    allow_diagonal=bool(tw_cfg.get('allow_diagonal', True)),
                )
            self.timewindow_shadow = bool(tw_cfg.get('shadow', True))
            print(f"[TIMEWINDOW] OpcionC activo (shadow={self.timewindow_shadow}). "
                  f"table={self.reservation_table}, planner={self.spacetime_planner}")

        # ============================================================
        # INICIATIVA #3 - OUTBOUND (aforo de staging + despacho) - Fase 0
        # Se LEE el bloque config["outbound"] pero NO se usa con el flag off.
        # Con enabled:false (default) => staging_zones vacio, outbound_process None
        # => ningun codigo nuevo se ejecuta => .jsonl byte-identico al baseline.
        # La logica activa (pallets persistentes, slots, camion) es Fase 1-2.
        # ============================================================
        self.outbound_config = configuracion.get('outbound', {'enabled': False})
        self.outbound_enabled = bool(self.outbound_config.get('enabled', False))
        self.staging_zones = {}       # {staging_id: StagingZone}; se puebla si enabled
        self.outbound_process = None  # se instancia en Fase 2 (camion)
        if self.outbound_enabled:
            from .outbound import StagingZone, build_zone_cells
            zones_raw = (self.data_manager.get_outbound_staging_zones()
                         if self.data_manager is not None else {})
            k = int(self.outbound_config.get('zone_capacity_default', 8))
            lm = self.layout_manager
            def _walk(x, y):
                try:
                    return bool(lm.collision_matrix[y][x])
                except Exception:
                    return False
            gw = getattr(lm, 'grid_width', 10**9)
            gh = getattr(lm, 'grid_height', 10**9)
            all_anchors = set(cells[0] for cells in zones_raw.values() if cells)
            used = set()
            self.staging_zones = {}
            for sid in sorted(zones_raw):
                cells = zones_raw[sid]
                if not cells:
                    continue
                anchor = cells[0]
                if len(cells) >= k:
                    # la hoja Excel ya define la zona completa: usarla tal cual.
                    zcells = [tuple(c) for c in cells[:k]]
                else:
                    # auto-expandir el ancla a k celdas caminables, sin solapar zonas.
                    others = (all_anchors - {anchor}) | used
                    zcells = build_zone_cells(anchor, k, _walk, exclude=others,
                                              grid_w=gw, grid_h=gh)
                self.staging_zones[sid] = StagingZone(sid, zcells)
                used.update(zcells)
            # INICIATIVA #3 / F1.2a: metricas del muelle (aforo).
            self.outbound_metrics = {
                'pallets_staged': 0,
                'pallets_shipped': 0,
                'slot_wait_events': 0,
                'slot_wait_time': 0.0,
                'max_slot_wait': 0.0,
                'peak_occupancy': {},
            }
            print(f"[OUTBOUND] Fase1 zonas (k={k}): "
                  f"{ {sid: z.capacity for sid, z in self.staging_zones.items()} }")
        else:
            print("[OUTBOUND] desactivado (enabled:false) - comportamiento actual.")

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
        print(f"[WAREHOUSE DEBUG] Configuración pasada al DispatcherV11: {configuracion}")
        print(f"[WAREHOUSE DEBUG] dispatch_strategy en config: '{configuracion.get('dispatch_strategy', 'NO ENCONTRADO')}'")
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

        # ORDER GENERATION STRATEGY: Create based on configuration
        # Supports 'stochastic' (random) and 'deterministic' (file-based) modes
        self.order_strategy: OrderGenerationStrategy = create_order_strategy(configuracion)
        order_mode = configuracion.get('order_generation_mode', 'stochastic')
        print(f"  - Order Generation Mode: {order_mode.upper()}")
        if order_mode == 'deterministic':
            policy = configuracion.get('fulfillment_policy', 'ship_partial')
            print(f"  - Fulfillment Policy: {policy}")

    def _crear_catalogo_y_stock(self):
        """
        Create SKU catalog and initialize inventory.
        
        V12 UPGRADE: Now loads from SQLite database via data_manager instead of
        generating synthetic SKUs. Falls back to legacy synthetic generation
        only if data_manager is not available.
        """
        print("[ALMACEN] Creando catalogo de SKUs y stock inicial...")
        
        # Try loading from data_manager (SQLite-backed)
        if self.data_manager and hasattr(self.data_manager, 'sku_catalog'):
            self._load_catalog_from_data_manager()
        else:
            # LEGACY FALLBACK: Generate synthetic SKUs
            print("[ALMACEN WARNING] No data_manager, using synthetic catalog")
            self._create_synthetic_catalog()
    
    def _load_catalog_from_data_manager(self):
        """
        Load SKU catalog and inventory from data_manager (SQLite).
        
        Uses real SKU codes (e.g., 'SKU029') and actual quantities from database.
        """
        print("[ALMACEN] Loading catalog from SQLite via data_manager...")
        
        # Load SKU catalog
        sku_catalog = self.data_manager.sku_catalog
        for sku_code, sku_info in sku_catalog.items():
            # Map volume from m3 to integer (multiply by 100 for internal use)
            volume_m3 = sku_info.get('volume_m3', 0.01)
            volumen_int = max(1, int(volume_m3 * 100))  # Convert to internal units
            
            # Create SKU object with real data
            sku = SKU(
                sku_id=sku_code,
                volumen=volumen_int,
                descripcion=sku_info.get('description', f'SKU {sku_code}')
            )
            self.catalogo_skus[sku_code] = sku
        
        # Load inventory from picking points
        picking_points = self.data_manager.get_picking_points()
        for punto in picking_points:
            sku_code = punto.get('sku_initial', '')
            qty = punto.get('qty_initial', 0)
            
            if sku_code:
                # Sum quantities per SKU (multiple locations may have same SKU)
                current_qty = self.inventario.get(sku_code, 0)
                self.inventario[sku_code] = current_qty + qty
        
        print(f"[ALMACEN] Catalogo SQLite cargado: {len(self.catalogo_skus)} SKUs")
        print(f"[ALMACEN] Inventario real: {sum(self.inventario.values())} unidades")
        
        # Log sample for verification
        sample_skus = list(self.catalogo_skus.keys())[:5]
        print(f"[ALMACEN] Sample SKUs: {sample_skus}")
    
    def _create_synthetic_catalog(self):
        """
        LEGACY FALLBACK: Create synthetic SKU catalog.
        
        Only used when data_manager is not available (backward compatibility).
        Generates SKUs like 'SKU-PEQ-001', 'SKU-MED-002', etc.
        """
        sku_counter = 1
        for tipo, config in self.distribucion_tipos.items():
            volumen = config['volumen']
            # Create multiple SKUs per type
            for i in range(5):  # 5 SKUs per type
                sku_id = f"SKU-{tipo[:3].upper()}-{sku_counter:03d}"
                sku = SKU(sku_id, volumen, f"Producto {tipo} #{i+1}")
                self.catalogo_skus[sku_id] = sku
                self.inventario[sku_id] = 1000  # Default stock
                sku_counter += 1

        print(f"[ALMACEN] Catalogo sintetico: {len(self.catalogo_skus)} SKUs")

    def _validar_y_ajustar_cantidad(self, sku: SKU, cantidad_original: int,
                                     work_area: str) -> List[int]:
        """
        Divide cantidad solicitada en multiples WOs si excede capacidad.

        BUGFIX WO DIVISION: Cuando una orden solicita mas volumen del que cabe
        en un operario, crea multiples WOs para completar la orden.

        Args:
            sku: SKU object with volumen attribute
            cantidad_original: Requested quantity (1-5)
            work_area: Work area identifier

        Returns:
            Lista de cantidades (una por cada WO necesaria para completar la orden)
        """
        from typing import List
        
        # Calculate total volume
        volumen_total = sku.volumen * cantidad_original

        # Determine max capacity for this work area
        max_capacity = self.operator_capacities.get(
            work_area,
            self.max_operator_capacity  # Fallback to global max
        )

        # Calculate units that fit per trip
        unidades_por_viaje = max_capacity // sku.volumen

        # Check if volume exceeds capacity
        if volumen_total <= max_capacity:
            # Fits in a single trip
            return [cantidad_original]
        else:
            # Needs multiple trips
            cantidades = []
            cantidad_restante = cantidad_original
            
            while cantidad_restante > 0:
                cantidad_viaje = min(unidades_por_viaje, cantidad_restante)
                cantidades.append(cantidad_viaje)
                cantidad_restante -= cantidad_viaje
            
            # Log division
            print(f"[ALMACEN] WO DIVIDIDA: SKU {sku.id} "
                  f"cantidad {cantidad_original} -> {len(cantidades)} WOs {cantidades} "
                  f"(volumen {volumen_total} > capacidad {max_capacity})")
            
            return cantidades

    def _obtener_pick_sequence_real(self, ubicacion: tuple, work_area: str) -> int:
        """
        Obtiene el pick_sequence real desde Warehouse_Logic.xlsx
        
        Args:
            ubicacion: (x, y) coordenadas de la ubicación
            work_area: Área de trabajo
            
        Returns:
            pick_sequence real desde Excel, o fallback si no se encuentra
        """
        if not self.data_manager or not hasattr(self.data_manager, 'puntos_de_picking_ordenados'):
            return 999  # Fallback para compatibilidad
        
        # Buscar en puntos de picking ordenados
        for punto in self.data_manager.puntos_de_picking_ordenados:
            if (punto.get('x') == ubicacion[0] and 
                punto.get('y') == ubicacion[1] and 
                punto.get('WorkArea') == work_area):
                return punto.get('pick_sequence', 999)
        
        # Si no se encuentra, usar fallback
        print(f"[WAREHOUSE WARN] No se encontró pick_sequence para {ubicacion} en {work_area}")
        return 999

    def _seleccionar_staging_id(self) -> int:
        """
        Select staging ID based on outbound_staging_distribution configuration
        
        Returns:
            int: Selected staging ID (1-7)
        """
        # Convert distribution to cumulative probabilities
        staging_ids = []
        probabilities = []
        
        for staging_id_str, percentage in self.outbound_staging_distribution.items():
            staging_id = int(staging_id_str)
            if percentage > 0:  # Only include staging areas with non-zero distribution
                staging_ids.append(staging_id)
                probabilities.append(percentage)
        
        if not staging_ids:
            return 1  # Default to staging 1 if no distribution
        
        # Select based on weighted random choice
        rand = random.random() * sum(probabilities)
        cumulative = 0
        
        for i, prob in enumerate(probabilities):
            cumulative += prob
            if rand <= cumulative:
                return staging_ids[i]
        
        # Fallback to first staging
        return staging_ids[0]

    def _generar_flujo_ordenes(self):
        """
        Generate work orders flow using configured strategy.
        
        Delegates to either StochasticOrderStrategy (random) or
        DeterministicOrderStrategy (file-based) based on configuration.
        """
        # Delegate to strategy pattern
        all_work_orders = self.order_strategy.generate_work_orders(self)
        
        # Add work orders to dispatcher
        if all_work_orders:
            self.dispatcher.agregar_work_orders(all_work_orders)
        
        print(f"[ALMACEN] Distribucion por tipo: {self.distribucion_tipos}")
        
        # Store validation result for API access (deterministic mode only)
        self._last_validation_result = self.order_strategy.get_validation_result()
    
    def get_order_validation_result(self):
        """Get validation result from last order generation (deterministic mode only)"""
        return getattr(self, '_last_validation_result', None)

    def consumir_stock_picking(self, wo, sim_now=None):
        """
        Consume real stock when an operator physically picks a WorkOrder (Fase 2).

        Delegates to data_manager.consume_stock to decrement qty_available and
        release the matching qty_reserved at the WO's real inventory location.

        NO-OP when there is no data_manager, the WO has no location_id (stochastic
        mode), or the picked quantity is not positive. ASCII-only logging (Ley 4).

        Args:
            wo: the WorkOrder being picked (uses wo.location_id and
                wo.cantidad_inicial as the picked quantity).
            sim_now: optional SimPy timestamp for inventory.last_updated.
        """
        if not self.data_manager or not hasattr(self.data_manager, 'consume_stock'):
            return
        location_id = getattr(wo, 'location_id', None)
        qty = getattr(wo, 'cantidad_inicial', 0)
        if not location_id or not qty or qty <= 0:
            return  # stochastic WO (no real location) or nothing to consume

        result = self.data_manager.consume_stock(location_id, qty, sim_now=sim_now)
        if result is not None:
            new_avail, new_reserved = result
            print(f"[STOCK] Pick {wo.id}: {qty}u de {location_id} "
                  f"({wo.sku_id}) -> avail={new_avail}, reserved={new_reserved}")

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
            if tipo == 'estado_agente':
                # FIX REPLAY VIEWER: Usar estructura compatible con replay viewer
                # Estructura: {type, timestamp, agent_id, data: {...}}
                agent_id = datos.get('agent_id', 'unknown')
                
                # Calcular coordenadas pixel desde position (grid coordinates)
                position = datos.get('position', [0, 0])
                pixel_x, pixel_y = 0, 0
                if self.layout_manager and position:
                    try:
                        pixel_x, pixel_y = self.layout_manager.grid_to_pixel(position[0], position[1])
                    except Exception as e:
                        print(f"[WARNING] Error calculating pixel coordinates from {position}: {e}")
                        pixel_x, pixel_y = position[0] * 32, position[1] * 32  # Fallback
                
                # Obtener capacidad real del operario desde configuracion
                agent_type = datos.get('agent_type', 'Unknown')
                capacidad_real = 150  # Default
                
                # Buscar capacidad en configuracion por tipo de agente
                agent_types_config = self.configuracion.get('agent_types', [])
                for agent_config in agent_types_config:
                    if agent_config.get('type') == agent_type:
                        capacidad_real = agent_config.get('capacity', 150)
                        break
                
                replay_evento = {
                    'type': tipo,
                    'timestamp': self.env.now,
                    'agent_id': agent_id,
                    'data': {
                        'x': pixel_x,  # CRITICAL: Coordenadas pixel para replay viewer
                        'y': pixel_y,  # CRITICAL: Coordenadas pixel para replay viewer
                        'tipo': datos.get('tipo', 'unknown'),
                        'position': position,
                        'status': datos.get('status', 'idle'),
                        'current_task': datos.get('current_task'),
                        'current_work_area': datos.get('current_work_area'),
                        'cargo_volume': datos.get('cargo_volume', 0),
                        # Campos adicionales para compatibilidad
                        'accion': f"Estado: {datos.get('status', 'idle')}",
                        'tareas_completadas': 0,
                        'direccion_x': 0,
                        'direccion_y': 0,
                        'type': datos.get('tipo', 'unknown'),
                        'tour_tasks_completed': 0,
                        'tour_total_tasks': 0,
                        'current_item': 'N/A',
                        'carga': datos.get('cargo_volume', 0),
                        'capacidad': capacidad_real  # Usar capacidad real desde config.json
                    }
                }
            else:
                # Para otros tipos de eventos, mantener estructura original
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
