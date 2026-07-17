# -*- coding: utf-8 -*-
"""
Order Generation Strategies Module
Digital Twin Warehouse Simulator

Implements Strategy Pattern for dual-mode order generation:
- StochasticOrderStrategy: Random generation based on distribution parameters
- DeterministicOrderStrategy: Load orders from JSON/CSV file with fulfillment policies

Author: Digital Twin Warehouse Team
Version: V12 - Deterministic Mode Feature
"""

import json
import csv
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


def _coerce_int(value):
    """INIT-4: convierte a int de forma defensiva. Malformado/None -> None."""
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value):
    """INIT-4: convierte a float de forma defensiva. Malformado/None -> None."""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def skus_por_clase(catalogo_values, clase):
    """
    AUD8-2 (auditoria INIT-8): SKUs cuya CLASE DE MANEJO (SKU.clase, hoja
    SkuCatalog / INIT-8 F1) coincide con la clave de distribucion_tipos.
    Devuelve [] si ninguna coincide: el caller decide el fallback (todos los
    SKUs + WARN). Reemplaza al filtro historico por substring del id, que
    nunca matcheaba ('PEQ' in 'SKU001') y dejaba la mezcla uniforme.
    """
    return [s for s in catalogo_values
            if getattr(s, 'clase', 'GENERAL') == clase]


@dataclass
class OrderItem:
    """Represents a single item within an order"""
    sku_id: str
    quantity: int
    work_area: Optional[str] = None


@dataclass
class ParsedOrder:
    """Represents a parsed order with its items"""
    order_id: str
    items: List[OrderItem] = field(default_factory=list)
    staging_id: Optional[int] = None
    # INIT-4 (C2): prioridad de pedido (menor = mas urgente) y SLA opcional.
    # Default None -> el WorkOrder usa su default historico (99) -> no-regresion.
    priority: Optional[int] = None
    due_time: Optional[float] = None
    # INIT-4 (C3): ola/wave a la que pertenece el pedido (None = sin ola).
    wave: Optional[int] = None
    # INIT-6 Opcion B: destino de negocio (tienda/zona de reparto). Se resuelve
    # a staging_id via destino_staging_map (almacen._resolver_staging_id).
    # None -> sin efecto, se usa staging_id explicito o el fallback aleatorio.
    destino: Optional[str] = None


@dataclass
class ExclusionRecord:
    """Records why an order or item was excluded"""
    order_id: str
    reason: str
    item_sku: Optional[str] = None
    action: str = "excluded"  # "excluded", "modified", "discarded"


@dataclass 
class ValidationResult:
    """Result of order file validation and processing"""
    valid_orders: List[ParsedOrder] = field(default_factory=list)
    exclusions: List[ExclusionRecord] = field(default_factory=list)
    total_orders_input: int = 0
    total_items_input: int = 0
    total_orders_output: int = 0
    total_items_output: int = 0
    skus_found: set = field(default_factory=set)
    skus_missing: set = field(default_factory=set)
    # ALLOCATION LAYER (V12.1): Track stock-based allocation results
    unfilled_demand: List[Dict[str, Any]] = field(default_factory=list)
    allocation_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'summary': {
                'total_orders_input': self.total_orders_input,
                'total_items_input': self.total_items_input,
                'total_orders_output': self.total_orders_output,
                'total_items_output': self.total_items_output,
                'skus_found': len(self.skus_found),
                'skus_missing': list(self.skus_missing),
                'allocation': self.allocation_summary
            },
            'exclusions': [
                {
                    'order_id': e.order_id,
                    'reason': e.reason,
                    'item_sku': e.item_sku,
                    'action': e.action
                }
                for e in self.exclusions
            ],
            'unfilled_demand': self.unfilled_demand
        }


class OrderGenerationStrategy(ABC):
    """
    Abstract base class for order generation strategies.
    
    Implements Strategy Pattern to allow switching between
    stochastic (random) and deterministic (file-based) order generation.
    """
    
    @abstractmethod
    def generate_work_orders(self, almacen: 'AlmacenMejorado') -> List['WorkOrder']:
        """
        Generate work orders for the simulation.
        
        Args:
            almacen: AlmacenMejorado instance with catalog and configuration
            
        Returns:
            List of WorkOrder objects ready for dispatch
        """
        pass
    
    @abstractmethod
    def get_validation_result(self) -> Optional[ValidationResult]:
        """Return validation result (for deterministic strategy only)"""
        pass


class StochasticOrderStrategy(OrderGenerationStrategy):
    """
    Stochastic order generation strategy.
    
    Generates random work orders based on configuration parameters:
    - total_ordenes: Total number of orders to generate
    - distribucion_tipos: Distribution percentages for order types
    - outbound_staging_distribution: Staging area distribution
    """
    
    def __init__(self):
        self.validation_result = None
    
    def generate_work_orders(self, almacen: 'AlmacenMejorado') -> List['WorkOrder']:
        """
        Generate random work orders based on configuration.
        
        This method contains the original logic from AlmacenMejorado._generar_flujo_ordenes()
        """
        import random
        from .warehouse import WorkOrder
        
        # Get picking points from data manager
        if not almacen.data_manager or not almacen.data_manager.puntos_de_picking_ordenados:
            print("[STOCHASTIC] WARNING: No hay puntos de picking disponibles - usando ubicaciones dummy")
            picking_points = [(10, 10), (15, 15), (20, 20)]
            work_areas = ["Area_Ground", "Area_High", "Area_Special"]
            points_by_sku: Dict[str, List[Dict[str, Any]]] = {}
        else:
            # Mix picking points randomly to ensure fair distribution across areas
            mixed_points = almacen.data_manager.puntos_de_picking_ordenados.copy()
            random.shuffle(mixed_points)

            picking_points = [pp['ubicacion_grilla'] for pp in mixed_points]
            work_areas = [pp.get('WorkArea', 'Area_Ground') for pp in mixed_points]

            # INIT-1: indice SKU -> puntos reales donde ese SKU efectivamente
            # esta (sku_initial), para que la WO no vaya a una ubicacion al
            # azar desconectada del SKU que dice transportar.
            points_by_sku = {}
            for pp in almacen.data_manager.puntos_de_picking_ordenados:
                sku_code = pp.get('sku_initial')
                if sku_code:
                    points_by_sku.setdefault(sku_code, []).append(pp)

        # Generate work orders
        wo_counter = 0
        order_counter = 1
        all_work_orders = []
        wo_adjusted_count = 0
        sku_sin_ubicacion_count = 0
        _tipos_sin_skus_avisados = set()  # AUD8-2: WARN una vez por tipo

        for order_num in range(1, almacen.total_ordenes + 1):
            # Determine order type based on distribution
            rand = random.random() * 100
            cumulative = 0
            tipo_seleccionado = 'pequeno'

            for tipo, config in almacen.distribucion_tipos.items():
                cumulative += config['porcentaje']
                if rand <= cumulative:
                    tipo_seleccionado = tipo
                    break

            # AUD8-2 (auditoria INIT-8): seleccionar SKU por CLASE DE MANEJO
            # real (SKU.clase, hoja SkuCatalog). El filtro historico
            # (`tipo[:3].upper() in sku.id`) buscaba 'PEQ'/'MED'/'GRA' dentro
            # de 'SKU001'... => NUNCA matcheaba y la mezcla era uniforme
            # (distribucion_tipos era letra muerta). Ahora las claves de
            # distribucion_tipos son clases de manejo y la mezcla es
            # CONTROLABLE de verdad.
            skus_tipo = skus_por_clase(almacen.catalogo_skus.values(),
                                       tipo_seleccionado)
            if not skus_tipo:
                if tipo_seleccionado not in _tipos_sin_skus_avisados:
                    _tipos_sin_skus_avisados.add(tipo_seleccionado)
                    print(f"[STOCHASTIC][WARN] distribucion_tipos: la clase "
                          f"'{tipo_seleccionado}' no tiene SKUs en el catalogo; "
                          f"fallback a TODOS (mezcla uniforme en ese tipo).")
                skus_tipo = list(almacen.catalogo_skus.values())

            sku = random.choice(skus_tipo)

            # Generate 1-3 work orders per order
            num_wos = random.randint(1, 3)

            for wo_num in range(num_wos):
                # INIT-1: elegir una ubicacion REAL donde el SKU seleccionado
                # efectivamente esta (sku_initial), en vez de un round-robin
                # ciego sobre todos los puntos de picking.
                sku_points = points_by_sku.get(sku.id)
                if sku_points:
                    punto = random.choice(sku_points)
                    ubicacion = punto['ubicacion_grilla']
                    work_area = punto.get('WorkArea', 'Area_Ground')
                    pick_sequence_real = punto.get('pick_sequence')
                else:
                    # Fallback (SKU sin punto de picking conocido, no deberia
                    # pasar en un catalogo real): round-robin como antes + WARN.
                    sku_sin_ubicacion_count += 1
                    pick_idx = order_counter % len(picking_points)
                    ubicacion = picking_points[pick_idx]
                    work_area = work_areas[pick_idx] if pick_idx < len(work_areas) else "Area_Ground"
                    pick_sequence_real = None

                # Validate and potentially divide quantity
                cantidad_solicitada = random.randint(1, 5)
                cantidades = almacen._validar_y_ajustar_cantidad(
                    sku=sku,
                    cantidad_original=cantidad_solicitada,
                    work_area=work_area
                )

                # Track adjustments
                if len(cantidades) > 1:
                    wo_adjusted_count += 1

                # Select staging ID based on distribution
                staging_id = almacen._seleccionar_staging_id()
                
                # Create work orders
                for cantidad in cantidades:
                    wo_counter += 1
                    work_order = WorkOrder(
                        work_order_id=f"WO-{wo_counter:04d}",
                        order_id=f"ORD-{order_counter:04d}",
                        tour_id=f"TOUR-{order_counter:04d}",
                        sku=sku,
                        cantidad=cantidad,
                        ubicacion=ubicacion,
                        work_area=work_area,
                        pick_sequence=(pick_sequence_real if pick_sequence_real is not None
                                       else almacen._obtener_pick_sequence_real(ubicacion, work_area)),
                        staging_id=staging_id
                    )
                    all_work_orders.append(work_order)

            order_counter += 1

        print(f"[STOCHASTIC] Generadas {len(all_work_orders)} WorkOrders")
        print(f"[STOCHASTIC] Distribucion por tipo: {almacen.distribucion_tipos}")

        if wo_adjusted_count > 0:
            print(f"[STOCHASTIC] {wo_adjusted_count} WorkOrders ajustadas por capacidad")

        if sku_sin_ubicacion_count > 0:
            print(f"[STOCHASTIC][WARN] {sku_sin_ubicacion_count} WorkOrders sin punto de "
                  f"picking real para su SKU -- se uso ubicacion de fallback (round-robin).")

        return all_work_orders
    
    def get_validation_result(self) -> Optional[ValidationResult]:
        return None


class DeterministicOrderStrategy(OrderGenerationStrategy):
    """
    Deterministic order generation strategy.
    
    Loads orders from a JSON or CSV file and applies fulfillment policies:
    - ship_partial: Process valid items, exclude invalid ones
    - fill_or_kill: Discard entire order if any item is invalid
    """
    
    POLICY_SHIP_PARTIAL = "ship_partial"
    POLICY_FILL_OR_KILL = "fill_or_kill"
    
    def __init__(self, file_path: str, fulfillment_policy: str = "ship_partial"):
        """
        Initialize deterministic strategy with file path and policy.
        
        Args:
            file_path: Path to JSON or CSV file containing orders
            fulfillment_policy: "ship_partial" or "fill_or_kill"
        """
        self.file_path = file_path
        self.fulfillment_policy = fulfillment_policy
        self.parsed_orders: List[ParsedOrder] = []
        self.validation_result: Optional[ValidationResult] = None
        
        # Load and parse file on initialization
        if file_path:
            self._load_file()
    
    def _load_file(self):
        """Load and parse order file (JSON or CSV)"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Order file not found: {self.file_path}")
        
        _, ext = os.path.splitext(self.file_path.lower())
        
        if ext == '.json':
            self._parse_json()
        elif ext == '.csv':
            self._parse_csv()
        else:
            raise ValueError(f"Unsupported file format: {ext}. Use .json or .csv")
    
    def _parse_json(self):
        """Parse JSON order file"""
        print(f"[DETERMINISTIC] Parsing JSON file: {self.file_path}")
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        orders_data = data.get('orders', data) if isinstance(data, dict) else data
        
        if not isinstance(orders_data, list):
            raise ValueError("JSON must contain 'orders' array or be an array of orders")
        
        for order_data in orders_data:
            order = ParsedOrder(
                order_id=str(order_data.get('order_id', '')),
                staging_id=order_data.get('staging_id'),
                # INIT-4: campos opcionales por pedido. Coercion defensiva:
                # valores malformados -> None (sin crash, cae al default historico).
                priority=_coerce_int(order_data.get('priority')),
                due_time=_coerce_float(order_data.get('due_time')),
                wave=_coerce_int(order_data.get('wave')),
                # INIT-6 Opcion B: destino de negocio (opcional).
                destino=(str(order_data['destino']) if order_data.get('destino') else None),
            )

            items = order_data.get('items', [])
            for item_data in items:
                item = OrderItem(
                    sku_id=str(item_data.get('sku_id', '')),
                    quantity=int(item_data.get('quantity', 1)),
                    work_area=item_data.get('work_area')
                )
                order.items.append(item)
            
            if order.order_id and order.items:
                self.parsed_orders.append(order)
        
        print(f"[DETERMINISTIC] Parsed {len(self.parsed_orders)} orders from JSON")
    
    def _parse_csv(self):
        """
        Parse CSV order file with intelligent grouping.
        
        CSV format: order_id,sku_id,quantity,work_area,staging_id,destino
        Rows with same order_id are grouped into a single order.
        """
        print(f"[DETERMINISTIC] Parsing CSV file: {self.file_path}")

        orders_dict: Dict[str, ParsedOrder] = {}

        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                order_id = str(row.get('order_id', '')).strip()
                if not order_id:
                    continue

                # Create or get existing order
                if order_id not in orders_dict:
                    staging_id = row.get('staging_id')
                    destino = (row.get('destino') or '').strip()
                    orders_dict[order_id] = ParsedOrder(
                        order_id=order_id,
                        staging_id=int(staging_id) if staging_id and staging_id.strip() else None,
                        # INIT-4: campos opcionales tomados de la primera fila del pedido.
                        priority=_coerce_int(row.get('priority')),
                        due_time=_coerce_float(row.get('due_time')),
                        wave=_coerce_int(row.get('wave')),
                        # INIT-6 Opcion B: destino de negocio (opcional).
                        destino=(destino or None),
                    )
                
                # Add item to order
                sku_id = str(row.get('sku_id', '')).strip()
                quantity_str = row.get('quantity', '1')
                
                try:
                    quantity = int(quantity_str) if quantity_str else 1
                except ValueError:
                    quantity = 1
                
                if sku_id:
                    item = OrderItem(
                        sku_id=sku_id,
                        quantity=quantity,
                        work_area=row.get('work_area', '').strip() or None
                    )
                    orders_dict[order_id].items.append(item)
        
        self.parsed_orders = list(orders_dict.values())
        print(f"[DETERMINISTIC] Parsed {len(self.parsed_orders)} orders from CSV "
              f"(grouped from {sum(len(o.items) for o in self.parsed_orders)} rows)")
    
    def generate_work_orders(self, almacen: 'AlmacenMejorado') -> List['WorkOrder']:
        """
        Generate work orders from loaded file data with fulfillment policy.
        
        ALLOCATION LAYER (V12.1): Now checks stock availability before creating
        WorkOrders. Uses FCFS (First-Come, First-Served) algorithm.
        
        Validates orders against catalog and applies configured policy.
        """
        import random
        from .warehouse import WorkOrder
        
        # Initialize validation result
        self.validation_result = ValidationResult(
            total_orders_input=len(self.parsed_orders),
            total_items_input=sum(len(o.items) for o in self.parsed_orders)
        )
        
        all_work_orders = []
        wo_counter = 0
        
        # =====================================================================
        # ALLOCATION LAYER (V12.1 - Init #1): per-LOCATION inventory ledger
        # Instead of aggregating stock by SKU and picking a RANDOM location, we
        # now allocate each item to the REAL locations that physically hold the
        # SKU, consuming qty_free and reserving the committed quantity.
        # =====================================================================
        inventory_ledger = {}        # {sku_code: [loc dicts with mutable qty_free]}
        initial_free_by_sku = {}     # {sku_code: total qty_free at snapshot} (reporting)

        if almacen.data_manager and hasattr(almacen.data_manager, 'get_inventory_by_location'):
            # Fase 2: restore qty_available from baseline and clear reservations so
            # each run starts from full stock (reproducible; in-sim consumption does
            # not accumulate across runs). Must run BEFORE reading the ledger.
            if hasattr(almacen.data_manager, 'restore_inventory_baseline'):
                almacen.data_manager.restore_inventory_baseline()
            inventory_ledger = almacen.data_manager.get_inventory_by_location()
            initial_free_by_sku = {
                sku: sum(loc['qty_free'] for loc in locs)
                for sku, locs in inventory_ledger.items()
            }
            total_skus = len(inventory_ledger)
            total_locs = sum(len(v) for v in inventory_ledger.values())
            print(f"[ALLOCATION] Per-location ledger loaded: {total_skus} SKUs, {total_locs} locations")
        else:
            print("[ALLOCATION] WARNING: No data_manager - allocation disabled")

        # Track allocation statistics
        total_qty_requested = 0
        total_qty_allocated = 0
        backorder_items_count = 0

        # Reservations to commit to inventory.qty_reserved {location_id: qty}
        reservations = {}
        
        for order in self.parsed_orders:
            # Validate and filter items based on policy
            valid_items, order_exclusions = self._validate_order(
                order, almacen.catalogo_skus, almacen
            )
            
            self.validation_result.exclusions.extend(order_exclusions)
            
            # Apply fulfillment policy
            if self.fulfillment_policy == self.POLICY_FILL_OR_KILL:
                # If any item was excluded, discard entire order
                if order_exclusions:
                    self.validation_result.exclusions.append(ExclusionRecord(
                        order_id=order.order_id,
                        reason=f"Order discarded (fill_or_kill policy) - {len(order_exclusions)} items invalid",
                        action="discarded"
                    ))
                    continue
            else:  # ship_partial
                # Skip if no valid items remain
                if not valid_items:
                    self.validation_result.exclusions.append(ExclusionRecord(
                        order_id=order.order_id,
                        reason="Order empty after filtering invalid items",
                        action="discarded"
                    ))
                    continue
            
            # Generate work orders for valid items WITH ALLOCATION CHECK
            for item in valid_items:
                sku = almacen.catalogo_skus[item.sku_id]
                self.validation_result.skus_found.add(item.sku_id)
                
                # =====================================================================
                # ALLOCATION LAYER (V12.1 - Init #1): allocate to REAL locations
                # Walk the SKU's locations (FCFS by pick_sequence), consuming
                # qty_free and reserving the taken quantity per location.
                # =====================================================================
                requested_qty = item.quantity
                total_qty_requested += requested_qty

                sku_locations = inventory_ledger.get(item.sku_id, [])
                allocations, qty_to_allocate = self._allocate_across_locations(
                    sku_locations, requested_qty, item.work_area
                )
                total_qty_allocated += qty_to_allocate

                # Track unfilled demand (backorders)
                if qty_to_allocate < requested_qty:
                    unfilled_qty = requested_qty - qty_to_allocate
                    backorder_items_count += 1

                    self.validation_result.unfilled_demand.append({
                        'order_id': order.order_id,
                        'sku_id': item.sku_id,
                        'qty_requested': requested_qty,
                        'qty_allocated': qty_to_allocate,
                        'qty_unfilled': unfilled_qty,
                        'stock_at_time': initial_free_by_sku.get(item.sku_id, 0),
                        'reason': f"Insufficient physical stock (free: {initial_free_by_sku.get(item.sku_id, 0)})"
                    })

                # Skip if no stock to allocate at any location
                if qty_to_allocate <= 0:
                    continue

                # Determine staging ID (once per item). INIT-6 Opcion B:
                # staging_id explicito > destino resuelto via destino_staging_map
                # > fallback aleatorio de siempre (ver _resolver_staging_id).
                staging_id = almacen._resolver_staging_id(order)

                # Create WorkOrders per allocated location (REAL coords / area /
                # pick_sequence), each split further by operator capacity.
                for loc, qty_chunk in allocations:
                    location_id = loc['location_id']
                    work_area = loc['work_area']           # REAL area of the location
                    ubicacion = (loc['x'], loc['y'])       # REAL grid coords
                    pick_sequence = loc['pick_sequence']   # REAL sequence

                    # Reserve the taken quantity for this physical location
                    reservations[location_id] = reservations.get(location_id, 0) + qty_chunk

                    # Capacity split (may yield several WOs for this chunk)
                    cantidades = almacen._validar_y_ajustar_cantidad(
                        sku=sku,
                        cantidad_original=qty_chunk,
                        work_area=work_area
                    )

                    for cantidad in cantidades:
                        wo_counter += 1
                        work_order = WorkOrder(
                            work_order_id=f"WO-{wo_counter:04d}",
                            order_id=order.order_id,
                            tour_id=f"TOUR-{order.order_id}",
                            sku=sku,
                            cantidad=cantidad,
                            ubicacion=ubicacion,
                            work_area=work_area,
                            pick_sequence=pick_sequence,
                            staging_id=staging_id,
                            qty_requested=requested_qty,   # Original request for tracking
                            location_id=location_id,       # REAL inventory location
                            # INIT-4: prioridad/SLA/ola del pedido (None -> default historico)
                            priority=order.priority,
                            due_time=order.due_time,
                        )
                        # INIT-4 (C3): propagar la ola del pedido a la WO (elegibilidad).
                        work_order.wave_id = order.wave
                        all_work_orders.append(work_order)

                self.validation_result.total_items_output += 1
            
            self.validation_result.total_orders_output += 1
        
        # =====================================================================
        # ALLOCATION LAYER: Generate summary and console output
        # =====================================================================
        unfilled_total_qty = total_qty_requested - total_qty_allocated
        
        self.validation_result.allocation_summary = {
            'total_qty_requested': total_qty_requested,
            'total_qty_allocated': total_qty_allocated,
            'total_qty_unfilled': unfilled_total_qty,
            'backorder_items_count': backorder_items_count,
            'allocation_rate': round((total_qty_allocated / total_qty_requested * 100), 1) if total_qty_requested > 0 else 100.0,
            'locations_reserved': len([q for q in reservations.values() if q > 0]),
            'total_units_reserved': sum(reservations.values()),
        }

        # Store reservations so they can be committed to the DB (see P5)
        self._pending_reservations = reservations
        
        # Print clear allocation summary to console
        print("\n" + "=" * 70)
        print("[ALLOCATION] STOCK ALLOCATION SUMMARY")
        print("=" * 70)
        print(f"  Orders processed: {self.validation_result.total_orders_output}")
        print(f"  Total qty requested: {total_qty_requested}")
        print(f"  Total qty allocated: {total_qty_allocated}")
        
        if backorder_items_count > 0:
            print(f"  [!] BACKORDERS DETECTED: {backorder_items_count} items ({unfilled_total_qty} units not allocated)")
            print(f"  Allocation rate: {self.validation_result.allocation_summary['allocation_rate']}%")
            
            # Show first few backorder details
            for i, backorder in enumerate(self.validation_result.unfilled_demand[:5]):
                print(f"      - {backorder['order_id']}: SKU {backorder['sku_id']} "
                      f"(req: {backorder['qty_requested']}, got: {backorder['qty_allocated']}, "
                      f"unfilled: {backorder['qty_unfilled']})")
            
            if len(self.validation_result.unfilled_demand) > 5:
                print(f"      ... and {len(self.validation_result.unfilled_demand) - 5} more")
        else:
            print("  [OK] All requested quantities fully allocated!")
        
        print("=" * 70 + "\n")
        
        # Log exclusion report
        self._log_exclusion_report()
        
        print(f"[DETERMINISTIC] Generated {len(all_work_orders)} WorkOrders "
              f"from {self.validation_result.total_orders_output} valid orders")

        # =====================================================================
        # ALLOCATION LAYER (V12.1 - Init #1): commit reservations to the DB
        # Idempotent: commit_reservations resets qty_reserved to 0 first, then
        # writes the absolute reserved qty per location for THIS run.
        # =====================================================================
        if almacen.data_manager and hasattr(almacen.data_manager, 'commit_reservations'):
            committed = almacen.data_manager.commit_reservations(reservations)
            if committed:
                print(f"[ALLOCATION] Reserved {sum(reservations.values())} units "
                      f"across {len([q for q in reservations.values() if q > 0])} locations "
                      f"(qty_reserved persisted).")
            else:
                print("[ALLOCATION] WARNING: failed to persist reservations to DB")
        else:
            print("[ALLOCATION] No data_manager - reservations NOT persisted")

        return all_work_orders
    
    def _validate_order(self, order: ParsedOrder, catalogo: Dict[str, 'SKU'],
                        almacen: 'AlmacenMejorado') -> Tuple[List[OrderItem], List[ExclusionRecord]]:
        """
        Validate order items against catalog.
        
        Returns:
            Tuple of (valid_items, exclusion_records)
        """
        valid_items = []
        exclusions = []
        
        for item in order.items:
            # Check if SKU exists in catalog
            if item.sku_id not in catalogo:
                self.validation_result.skus_missing.add(item.sku_id)
                exclusions.append(ExclusionRecord(
                    order_id=order.order_id,
                    item_sku=item.sku_id,
                    reason=f"SKU '{item.sku_id}' not found in catalog",
                    action="excluded"
                ))
                continue
            
            # Validate quantity
            if item.quantity <= 0:
                exclusions.append(ExclusionRecord(
                    order_id=order.order_id,
                    item_sku=item.sku_id,
                    reason=f"Invalid quantity: {item.quantity}",
                    action="excluded"
                ))
                continue
            
            valid_items.append(item)
        
        return valid_items, exclusions

    def _allocate_across_locations(self, sku_locations: List[Dict[str, Any]],
                                   requested: int,
                                   preferred_area: Optional[str] = None
                                   ) -> Tuple[List[Tuple[Dict[str, Any], int]], int]:
        """
        Allocate `requested` units across the REAL locations holding a SKU (Init #1).

        FCFS by pick_sequence (sku_locations already comes ordered ASC). Mutates
        each location's 'qty_free' in place so subsequent items/orders see the
        decremented availability (no two orders fight over the same stock).

        If `preferred_area` is given, locations in that work_area are tried FIRST;
        if they cannot satisfy the demand, the remaining locations are used as a
        fallback (the WO's real area is always the chosen location's area).

        Args:
            sku_locations: list of mutable location dicts (with 'qty_free').
            requested: units requested for this item.
            preferred_area: optional work_area preference filter.

        Returns:
            (allocations, total_taken) where allocations is a list of
            (location_dict, qty_taken) tuples.
        """
        allocations: List[Tuple[Dict[str, Any], int]] = []
        remaining = requested

        if preferred_area:
            preferred = [l for l in sku_locations if l['work_area'] == preferred_area]
            fallback = [l for l in sku_locations if l['work_area'] != preferred_area]
            ordered = preferred + fallback
        else:
            ordered = sku_locations

        for loc in ordered:
            if remaining <= 0:
                break
            free = loc.get('qty_free', 0)
            if free <= 0:
                continue
            take = min(remaining, free)
            loc['qty_free'] = free - take
            allocations.append((loc, take))
            remaining -= take

        return allocations, requested - remaining

    def _build_picking_points_index(self, almacen: 'AlmacenMejorado') -> Dict[str, List[tuple]]:
        """Build index of picking points by work area"""
        index = {}
        
        if almacen.data_manager and almacen.data_manager.puntos_de_picking_ordenados:
            for pp in almacen.data_manager.puntos_de_picking_ordenados:
                work_area = pp.get('WorkArea', 'Area_Ground')
                if work_area not in index:
                    index[work_area] = []
                index[work_area].append(pp['ubicacion_grilla'])
        
        return index
    
    def _get_default_work_area(self, sku: 'SKU', almacen: 'AlmacenMejorado') -> str:
        """Determine default work area based on SKU type"""
        # Use volume-based heuristic
        if sku.volumen <= 10:
            return "Area_Ground"
        elif sku.volumen <= 50:
            return "Area_High"
        else:
            return "Area_Special"
    
    def _get_location_for_area(self, work_area: str, 
                                picking_points_by_area: Dict[str, List[tuple]],
                                almacen: 'AlmacenMejorado') -> tuple:
        """Get a picking location for the given work area"""
        import random
        
        if work_area in picking_points_by_area and picking_points_by_area[work_area]:
            return random.choice(picking_points_by_area[work_area])
        
        # Fallback to any available location
        all_points = [p for points in picking_points_by_area.values() for p in points]
        if all_points:
            return random.choice(all_points)
        
        # Ultimate fallback
        return (10, 10)
    
    def _log_exclusion_report(self):
        """Print exclusion report to console"""
        result = self.validation_result
        
        print("\n" + "=" * 60)
        print("DETERMINISTIC ORDER LOAD - EXCLUSION REPORT")
        print("=" * 60)
        print(f"Policy: {self.fulfillment_policy}")
        print(f"Input:  {result.total_orders_input} orders, {result.total_items_input} items")
        print(f"Output: {result.total_orders_output} orders, {result.total_items_output} items")
        
        if result.skus_missing:
            print(f"\nMissing SKUs ({len(result.skus_missing)}): {list(result.skus_missing)}")
        
        if result.exclusions:
            print(f"\nExclusions ({len(result.exclusions)}):")
            for exc in result.exclusions[:10]:  # Show first 10
                if exc.item_sku:
                    print(f"  - [{exc.action.upper()}] Order {exc.order_id}, SKU {exc.item_sku}: {exc.reason}")
                else:
                    print(f"  - [{exc.action.upper()}] Order {exc.order_id}: {exc.reason}")
            
            if len(result.exclusions) > 10:
                print(f"  ... and {len(result.exclusions) - 10} more")
        else:
            print("\nNo exclusions - all orders processed successfully!")
        
        print("=" * 60 + "\n")
    
    def get_validation_result(self) -> Optional[ValidationResult]:
        return self.validation_result


def create_order_strategy(configuracion: Dict[str, Any]) -> OrderGenerationStrategy:
    """
    Factory function to create appropriate order generation strategy.
    
    Args:
        configuracion: Configuration dictionary with order generation settings
        
    Returns:
        OrderGenerationStrategy instance (Stochastic or Deterministic)
    """
    mode = configuracion.get('order_generation_mode', 'stochastic')
    
    if mode == 'deterministic':
        file_path = configuracion.get('order_file_path')
        policy = configuracion.get('fulfillment_policy', 'ship_partial')
        
        if not file_path:
            print("[WARNING] Deterministic mode selected but no file path provided. "
                  "Falling back to stochastic mode.")
            return StochasticOrderStrategy()
        
        return DeterministicOrderStrategy(file_path=file_path, fulfillment_policy=policy)
    
    return StochasticOrderStrategy()
