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
        else:
            # Mix picking points randomly to ensure fair distribution across areas
            mixed_points = almacen.data_manager.puntos_de_picking_ordenados.copy()
            random.shuffle(mixed_points)
            
            picking_points = [pp['ubicacion_grilla'] for pp in mixed_points]
            work_areas = [pp.get('WorkArea', 'Area_Ground') for pp in mixed_points]

        # Generate work orders
        wo_counter = 0
        order_counter = 1
        all_work_orders = []
        wo_adjusted_count = 0

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

            # Select SKU of chosen type
            skus_tipo = [sku for sku in almacen.catalogo_skus.values()
                        if tipo_seleccionado[:3].upper() in sku.id]
            if not skus_tipo:
                skus_tipo = list(almacen.catalogo_skus.values())

            sku = random.choice(skus_tipo)

            # Generate 1-3 work orders per order
            num_wos = random.randint(1, 3)

            for wo_num in range(num_wos):
                # Select picking location
                pick_idx = order_counter % len(picking_points)
                ubicacion = picking_points[pick_idx]
                work_area = work_areas[pick_idx] if pick_idx < len(work_areas) else "Area_Ground"

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
                        pick_sequence=almacen._obtener_pick_sequence_real(ubicacion, work_area),
                        staging_id=staging_id
                    )
                    all_work_orders.append(work_order)

            order_counter += 1

        print(f"[STOCHASTIC] Generadas {len(all_work_orders)} WorkOrders")
        print(f"[STOCHASTIC] Distribucion por tipo: {almacen.distribucion_tipos}")

        if wo_adjusted_count > 0:
            print(f"[STOCHASTIC] {wo_adjusted_count} WorkOrders ajustadas por capacidad")

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
                staging_id=order_data.get('staging_id')
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
        
        CSV format: order_id,sku_id,quantity,work_area,staging_id
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
                    orders_dict[order_id] = ParsedOrder(
                        order_id=order_id,
                        staging_id=int(staging_id) if staging_id and staging_id.strip() else None
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
        # ALLOCATION LAYER: Load stock snapshot from SQLite
        # =====================================================================
        available_stock = {}
        initial_stock_snapshot = {}
        
        if almacen.data_manager:
            available_stock = almacen.data_manager.get_all_available_stock()
            initial_stock_snapshot = available_stock.copy()  # Keep original for reporting
            print(f"[ALLOCATION] Stock snapshot loaded: {len(available_stock)} SKUs")
        else:
            print("[ALLOCATION] WARNING: No data_manager - allocation disabled")
        
        # Track allocation statistics
        total_qty_requested = 0
        total_qty_allocated = 0
        backorder_items_count = 0
        
        # Get picking points for location assignment
        picking_points_by_area = self._build_picking_points_index(almacen)
        
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
                # ALLOCATION LAYER: Check and decrement stock (FCFS)
                # =====================================================================
                requested_qty = item.quantity
                total_qty_requested += requested_qty
                
                current_stock = available_stock.get(item.sku_id, 0)
                qty_to_allocate = min(requested_qty, current_stock)
                
                # Decrement virtual stock
                if qty_to_allocate > 0:
                    available_stock[item.sku_id] = current_stock - qty_to_allocate
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
                        'stock_at_time': initial_stock_snapshot.get(item.sku_id, 0),
                        'reason': f"Insufficient stock (available: {current_stock})"
                    })
                
                # Skip if no stock to allocate
                if qty_to_allocate <= 0:
                    continue
                
                # Determine work area (from item, catalog, or default)
                work_area = item.work_area or self._get_default_work_area(sku, almacen)
                
                # Get location for this work area
                ubicacion = self._get_location_for_area(work_area, picking_points_by_area, almacen)
                
                # Validate and adjust quantity for capacity (may split into multiple WOs)
                cantidades = almacen._validar_y_ajustar_cantidad(
                    sku=sku,
                    cantidad_original=qty_to_allocate,
                    work_area=work_area
                )
                
                # Determine staging ID
                staging_id = order.staging_id or almacen._seleccionar_staging_id()
                
                # Create work orders with allocation metadata
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
                        pick_sequence=almacen._obtener_pick_sequence_real(ubicacion, work_area),
                        staging_id=staging_id,
                        qty_requested=requested_qty  # Original request for tracking
                    )
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
            'allocation_rate': round((total_qty_allocated / total_qty_requested * 100), 1) if total_qty_requested > 0 else 100.0
        }
        
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
