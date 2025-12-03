# -*- coding: utf-8 -*-
"""
Operators Module - Agent Classes for Warehouse Simulation
Digital Twin Warehouse Simulator

Contains agent classes (GroundOperator, Forklift) and factory function
"""

import simpy
from typing import List, Dict, Any, Optional, Tuple


def determinar_staging_destino(work_orders: List[Any], data_manager: Any) -> Tuple[int, Tuple[int, int]]:
    """
    Determina el staging correcto basado en las WorkOrders del tour
    
    Args:
        work_orders: Lista de WorkOrders del tour
        data_manager: DataManager para obtener ubicaciones de staging
        
    Returns:
        Tuple[int, Tuple[int, int]]: (staging_id, ubicacion)
    """
    if not work_orders:
        # Default to staging 1 if no work orders
        staging_locs = data_manager.get_outbound_staging_locations()
        return 1, staging_locs.get(1, (3, 29))
    
    # Get staging_id from first work order (all should be same in Tour Simple)
    staging_id = work_orders[0].staging_id
    
    # Get staging location from data_manager
    staging_locs = data_manager.get_outbound_staging_locations()
    ubicacion = staging_locs.get(staging_id, (3, 29))  # Default to staging 1 location
    
    return staging_id, ubicacion


class BaseOperator:
    """
    Base class for warehouse operators
    Common functionality for all agent types
    """

    def __init__(self, agent_id: str, agent_type: str, env: simpy.Environment,
                 almacen: Any, configuracion: Dict[str, Any],
                 capacity: int, discharge_time: int,
                 work_area_priorities: Dict[str, int],
                 pathfinder: Any = None, layout_manager: Any = None,
                 simulador: Any = None):
        """
        Initialize base operator

        Args:
            agent_id: Unique agent identifier
            agent_type: Agent type string ('GroundOperator' or 'Forklift')
            env: SimPy environment
            almacen: Warehouse instance
            configuracion: Configuration dictionary
            capacity: Cargo capacity in volume units
            discharge_time: Time to discharge per task
            work_area_priorities: Dict mapping work_area -> priority
            pathfinder: Pathfinder instance for navigation
            layout_manager: LayoutManager for TMX maps
            simulador: Main simulator reference
        """
        self.id = agent_id
        self.type = agent_type
        self.env = env
        self.almacen = almacen
        self.configuracion = configuracion
        self.capacity = capacity
        self.discharge_time = discharge_time
        self.work_area_priorities = work_area_priorities
        self.pathfinder = pathfinder
        self.layout_manager = layout_manager
        self.simulador = simulador

        # Agent state
        self.current_position = None  # (grid_x, grid_y)
        self.current_task = None
        self.status = "idle"  # idle, moving, working
        self.cargo_volume = 0
        self.tasks_completed = 0

        # Performance metrics
        self.total_distance_traveled = 0
        self.total_work_time = 0
        self.idle_time = 0

        print(f"[AGENT] {self.id} ({self.type}) inicializado - Capacidad: {self.capacity}")

    def get_priority_for_work_area(self, work_area: str) -> int:
        """
        Get priority for a specific work area

        Args:
            work_area: Work area identifier

        Returns:
            Priority level (lower is higher priority), 999 if not in priorities
        """
        return self.work_area_priorities.get(work_area, 999)

    def can_handle_work_area(self, work_area: str) -> bool:
        """
        Check if this agent can handle tasks in the given work area

        Args:
            work_area: Work area identifier

        Returns:
            True if agent has priority for this work area
        """
        return work_area in self.work_area_priorities

    def has_capacity_for(self, volume: int) -> bool:
        """
        Check if agent has capacity for additional volume

        Args:
            volume: Volume to add

        Returns:
            True if volume fits in remaining capacity
        """
        return (self.cargo_volume + volume) <= self.capacity

    def add_cargo(self, volume: int):
        """Add cargo volume to agent"""
        self.cargo_volume += volume

    def clear_cargo(self):
        """Clear all cargo"""
        self.cargo_volume = 0

    def move_to(self, target_position: Tuple[int, int]):
        """
        Move agent to target position (simplified - actual pathfinding in subclasses)

        Args:
            target_position: (grid_x, grid_y) target coordinates
        """
        # This is a placeholder - actual movement would use pathfinder
        # and yield env.timeout() for travel time
        self.current_position = target_position

    def update_status(self, new_status: str):
        """Update agent status"""
        self.status = new_status

    def _agrupar_wos_por_staging(self, work_orders: List[Any]) -> Dict[int, List[Any]]:
        """
        Agrupa WorkOrders por staging_id para descarga multiple
        
        Args:
            work_orders: Lista de WorkOrders del tour
            
        Returns:
            Dict[staging_id: int, wos: List[WorkOrder]]
        """
        from collections import defaultdict
        staging_groups = defaultdict(list)
        
        for wo in work_orders:
            staging_id = wo.staging_id
            staging_groups[staging_id].append(wo)
        
        return dict(staging_groups)

    def _ordenar_stagings_por_distancia(self, staging_groups: Dict[int, List[Any]], 
                                         start_position: Tuple[int, int]) -> List[Tuple[int, List[Any]]]:
        """
        Ordena stagings por distancia desde posicion actual para minimizar desplazamientos
        
        Args:
            staging_groups: Dict[staging_id -> List[WorkOrder]]
            start_position: Posicion actual del operador (x, y)
            
        Returns:
            List[(staging_id, wos)] ordenada por distancia
        """
        staging_locs = self.almacen.data_manager.get_outbound_staging_locations()
        
        # Calcular distancia a cada staging
        staging_distances = []
        for staging_id, wos in staging_groups.items():
            staging_pos = staging_locs.get(staging_id, (3, 29))
            distance = abs(staging_pos[0] - start_position[0]) + abs(staging_pos[1] - start_position[1])
            staging_distances.append((distance, staging_id, wos))
        
        # Ordenar por distancia (mas cercano primero)
        staging_distances.sort(key=lambda x: x[0])
        
        # Retornar sin la distancia
        return [(staging_id, wos) for _, staging_id, wos in staging_distances]

    def _get_current_work_area(self) -> Optional[str]:
        """
        Obtiene el work_area de la WorkOrder actual si existe.
        
        Returns:
            str: Work area de la WO actual o None si no hay WO activa
        """
        if not self.current_task:
            return None
            
        # Buscar la WorkOrder en el dispatcher
        if hasattr(self.almacen, 'dispatcher') and self.almacen.dispatcher:
            operator_id = f"{self.type}_{self.id}"
            current_wo = self.almacen.dispatcher.work_orders_en_progreso.get(operator_id)
            if current_wo and hasattr(current_wo, 'work_area'):
                return current_wo.work_area
        
        return None

    def __repr__(self):
        return f"{self.type}({self.id}, cargo={self.cargo_volume}/{self.capacity}, status={self.status})"


class GroundOperator(BaseOperator):
    """
    Ground Operator - Handles ground-level picking tasks
    Uses pallet jacks for lighter cargo
    """

    def __init__(self, agent_id: str, env: simpy.Environment, almacen: Any,
                 configuracion: Dict[str, Any], capacity: int, discharge_time: int,
                 work_area_priorities: Dict[str, int],
                 pathfinder: Any = None, layout_manager: Any = None,
                 simulador: Any = None):
        """
        Initialize Ground Operator

        Args:
            Same as BaseOperator
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="GroundOperator",
            env=env,
            almacen=almacen,
            configuracion=configuracion,
            capacity=capacity,
            discharge_time=discharge_time,
            work_area_priorities=work_area_priorities,
            pathfinder=pathfinder,
            layout_manager=layout_manager,
            simulador=simulador
        )

        # Ground operator specific attributes
        self.default_speed = 1.0  # Speed multiplier
        self.preferred_areas = ["Area_Ground", "Area_Piso_L1"]

    def agent_process(self):
        """
        BUGFIX FASE 2: SimPy process real para GroundOperator
        Implementa ciclo pull-based de trabajo

        Flujo:
        1. Solicitar tour del dispatcher
        2. Navegar a ubicaciones de picking
        3. Simular picking en cada ubicacion
        4. Agrupar por staging y descargar multiple (MULTI-STAGING SUPPORT)
        5. Notificar completado
        6. Repetir
        """
        # Configuracion de simulacion
        TIME_PER_CELL = 0.1  # Segundos por celda de grid (ajustable)

        # Inicializar posicion en depot
        staging_locs = self.almacen.data_manager.get_outbound_staging_locations()
        depot_location = staging_locs.get(1, (3, 29))  # Staging 1 como depot default
        self.current_position = depot_location

        print(f"[{self.id}] Proceso iniciado en depot {depot_location}")

        while True:
            # PASO 1: Solicitar asignacion de tour
            self.status = "idle"
            
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'agent_type': self.type,
                'position': self.current_position,
                'status': self.status,
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })
            
            tour = self.almacen.dispatcher.solicitar_asignacion(self)

            if tour is None:
                if self.almacen.simulacion_ha_terminado():
                    print(f"[{self.id}] Simulacion finalizada, saliendo...")
                    break
                
                yield self.env.timeout(5.0)
                continue

            tour_start_time = self.env.now

            # PASO 2: Procesar tour asignado
            self.status = "working"
            work_orders = tour['work_orders']
            route_info = tour['route']

            print(f"[{self.id}] t={self.env.now:.1f} Tour asignado: "
                  f"{len(work_orders)} WOs, distancia: {tour['total_distance']:.1f}")

            if work_orders:
                self.almacen.dispatcher.notificar_inicio_trabajo(self, work_orders[0])

            # PASO 3: Visitar cada ubicacion de picking
            visit_sequence = route_info['visit_sequence']
            segment_paths = route_info['segment_paths']
            segment_distances = route_info['segment_distances']

            for idx, wo in enumerate(visit_sequence):
                segment_path = segment_paths[idx] if idx < len(segment_paths) else []
                segment_distance = segment_distances[idx] if idx < len(segment_distances) else 0

                if segment_path and len(segment_path) > 1:
                    self.status = "moving"
                    
                    self.almacen.registrar_evento('estado_agente', {
                        'agent_id': self.id,
                        'agent_type': self.type,
                        'position': self.current_position,
                        'status': self.status,
                        'current_task': wo.id if wo else None,
                        'current_work_area': wo.work_area if wo else None,
                        'cargo_volume': self.cargo_volume
                    })
                    
                    print(f"[{self.id}] t={self.env.now:.1f} Navegando a {wo.ubicacion} "
                          f"(path: {len(segment_path)} pasos)")
                    
                    for step_idx, step_position in enumerate(segment_path[1:], 1):
                        self.current_position = step_position
                        
                        self.almacen.registrar_evento('estado_agente', {
                            'agent_id': self.id,
                            'agent_type': self.type,
                            'position': self.current_position,
                            'status': self.status,
                            'current_task': wo.id if wo else None,
                            'current_work_area': wo.work_area if wo else None,
                            'cargo_volume': self.cargo_volume
                        })
                        
                        if wo:
                            progress = round(((wo.cantidad_total - wo.cantidad_restante) / wo.cantidad_total) * 100, 2) if wo.cantidad_total > 0 else 0
                            self.almacen.registrar_evento('work_order_update', {
                                'id': wo.id,
                                'order_id': wo.order_id,
                                'tour_id': getattr(wo, 'tour_id', None),
                                'sku_id': wo.sku_id,
                                'product': wo.sku_name,
                                'status': 'in_progress',
                                'assigned_agent_id': wo.assigned_agent_id,
                                'priority': getattr(wo, 'priority', 99),
                                'items': getattr(wo, 'items', 1),
                                'total_qty': wo.cantidad_total,
                                'volume': getattr(wo, 'volume', wo.volumen_restante),
                                'location': wo.ubicacion,
                                'staging': wo.staging_id,
                                'work_group': wo.work_group,
                                'work_area': wo.work_area,
                                'executions': getattr(wo, 'picking_executions', 0),
                                'start_time': wo.tiempo_inicio,
                                'progress': progress,
                                'tiempo_fin': getattr(wo, 'tiempo_fin', None)
                            })
                        
                        yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                        
                        print(f"[{self.id}] t={self.env.now:.1f} Paso {step_idx}/{len(segment_path)-1}: {step_position}")
                else:
                    self.current_position = wo.ubicacion
                    self.total_distance_traveled += segment_distance

                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id if wo else None,
                    'current_work_area': wo.work_area if wo else None,
                    'cargo_volume': self.cargo_volume
                })

                self.status = "picking"
                
                # Registrar evento con estado de picking
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id if wo else None,
                    'current_work_area': wo.work_area if wo else None,
                    'cargo_volume': self.cargo_volume
                })
                
                picking_duration = self.discharge_time
                yield self.env.timeout(picking_duration)

                self.almacen.registrar_evento('operation_completed', {
                    'agent_id': self.id,
                    'data': {
                        'duration': picking_duration,
                        'work_order_id': wo.id
                    }
                })
                self.almacen.registrar_evento('task_completed', {
                    'agent_id': self.id,
                    'task_id': wo.id,
                    'data': {
                        'task_ubicacion': wo.ubicacion,
                        'tiempo_picking': picking_duration
                    }
                })
                
                # ACTUALIZAR CARGO_VOLUME ANTES de poner cantidad_restante = 0
                if wo:
                    # Sumar el volumen ANTES de modificar cantidad_restante
                    self.cargo_volume += wo.calcular_volumen_restante()
                    wo.status = 'picked'
                    wo.cantidad_restante = 0
                    progress = round(((wo.cantidad_total - wo.cantidad_restante) / wo.cantidad_total) * 100, 2) if wo.cantidad_total > 0 else 0
                    self.almacen.registrar_evento('work_order_update', {
                        'id': wo.id,
                        'order_id': wo.order_id,
                        'tour_id': getattr(wo, 'tour_id', None),
                        'sku_id': wo.sku_id,
                        'product': wo.sku_name,
                        'status': 'picked',
                        'assigned_agent_id': wo.assigned_agent_id,
                        'priority': getattr(wo, 'priority', 99),
                        'items': getattr(wo, 'items', 1),
                        'total_qty': wo.cantidad_total,
                        'volume': getattr(wo, 'volume', wo.volumen_restante),
                        'location': wo.ubicacion,
                        'staging': wo.staging_id,
                        'work_group': wo.work_group,
                        'work_area': wo.work_area,
                        'executions': getattr(wo, 'picking_executions', 0) + 1,
                        'start_time': wo.tiempo_inicio,
                        'progress': progress,
                        'tiempo_fin': getattr(wo, 'tiempo_fin', None)
                    })

            # PASO 4: Agrupar WOs por staging y descargar en cada uno
            print(f"[{self.id}] Agrupando WOs por staging para descarga multiple")
            staging_groups = self._agrupar_wos_por_staging(work_orders)
            print(f"[{self.id}] Tour requiere visitar {len(staging_groups)} stagings: {list(staging_groups.keys())}")

            # Ordenar stagings por distancia desde posicion actual
            ordered_stagings = self._ordenar_stagings_por_distancia(staging_groups, self.current_position)
            staging_locs = self.almacen.data_manager.get_outbound_staging_locations()

            # Visitar cada staging en orden
            for idx, (staging_id, staging_wos) in enumerate(ordered_stagings, 1):
                staging_location = staging_locs.get(staging_id, (3, 29))
                # IMPORTANTE: Usar cantidad_inicial * sku.volumen porque cantidad_restante ya es 0 despues del picking
                volumen_staging = sum(wo.cantidad_inicial * wo.sku.volumen for wo in staging_wos)
                
                print(f"[{self.id}] [{idx}/{len(ordered_stagings)}] Navegando a staging {staging_id} "
                      f"en {staging_location} para descargar {len(staging_wos)} WOs ({volumen_staging}L)")
                
                # Navegar al staging
                if hasattr(self.almacen, 'route_calculator') and self.almacen.route_calculator:
                    try:
                        return_path = self.almacen.route_calculator.pathfinder.find_path(
                            self.current_position, staging_location
                        )
                        
                        if return_path and len(return_path) > 1:
                            self.status = "moving"
                            
                            self.almacen.registrar_evento('estado_agente', {
                                'agent_id': self.id,
                                'agent_type': self.type,
                                'position': self.current_position,
                                'status': self.status,
                                'current_task': None,
                                'cargo_volume': self.cargo_volume
                            })
                            
                            print(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                                  f"(path: {len(return_path)} pasos)")
                            
                            for step_idx, step_position in enumerate(return_path[1:], 1):
                                self.current_position = step_position
                                
                                self.almacen.registrar_evento('estado_agente', {
                                    'agent_id': self.id,
                                    'agent_type': self.type,
                                    'position': self.current_position,
                                    'status': self.status,
                                    'current_task': None,
                                    'cargo_volume': self.cargo_volume
                                })
                                
                                yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                                
                                if step_idx % 5 == 0:
                                    print(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                                          f"paso {step_idx}/{len(return_path)-1}")
                            
                            self.total_distance_traveled += len(return_path) - 1
                        else:
                            self.current_position = staging_location
                    except Exception as e:
                        print(f"[{self.id}] ERROR en pathfinding a staging {staging_id}: {e}")
                        self.current_position = staging_location
                
                # DESCARGAR en este staging
                self.status = "unloading"
                
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': None,
                    'cargo_volume': self.cargo_volume
                })
                
                print(f"[{self.id}] t={self.env.now:.1f} Descargando en staging {staging_id}")
                discharge_duration = self.discharge_time * len(staging_wos)
                yield self.env.timeout(discharge_duration)
                
                # Actualizar cargo_volume PARCIALMENTE (solo lo descargado)
                self.cargo_volume -= volumen_staging
                print(f"[{self.id}] t={self.env.now:.1f} Descargados {volumen_staging}L en staging {staging_id}, "
                      f"cargo restante: {self.cargo_volume}L")
                
                # Registrar evento de descarga parcial
                self.almacen.registrar_evento('partial_discharge', {
                    'agent_id': self.id,
                    'staging_id': staging_id,
                    'wos_descargadas': [wo.id for wo in staging_wos],
                    'volumen_descargado': volumen_staging,
                    'cargo_restante': self.cargo_volume,
                    'timestamp': self.env.now
                })

            # PASO 5: Limpiar cargo final (por seguridad)
            self.cargo_volume = 0
            print(f"[{self.id}] t={self.env.now:.1f} Descarga completa en todos los stagings")
            
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'agent_type': self.type,
                'position': self.current_position,
                'status': 'idle',
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })

            # PASO 6: Notificar completado
            tour_duration = self.env.now - tour_start_time
            self.almacen.registrar_evento('trip_completed', {
                'agent_id': self.id,
                'data': {
                    'duration': tour_duration,
                    'num_work_orders': len(work_orders)
                }
            })
            self.almacen.dispatcher.notificar_completado(self, work_orders)
            self.tasks_completed += len(work_orders)

            print(f"[{self.id}] t={self.env.now:.1f} Tour completado, "
                  f"total completadas: {self.tasks_completed}")


class Forklift(BaseOperator):
    """
    Forklift Operator - Handles heavy rack-level picking tasks
    Higher capacity, can access elevated storage
    """

    def __init__(self, agent_id: str, env: simpy.Environment, almacen: Any,
                 configuracion: Dict[str, Any], capacity: int, discharge_time: int,
                 work_area_priorities: Dict[str, int],
                 pathfinder: Any = None, layout_manager: Any = None,
                 simulador: Any = None):
        """
        Initialize Forklift

        Args:
            Same as BaseOperator
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="Forklift",
            env=env,
            almacen=almacen,
            configuracion=configuracion,
            capacity=capacity,
            discharge_time=discharge_time,
            work_area_priorities=work_area_priorities,
            pathfinder=pathfinder,
            layout_manager=layout_manager,
            simulador=simulador
        )

        # Forklift specific attributes
        self.default_speed = 0.8  # Slightly slower than ground operators
        self.preferred_areas = ["Area_Rack"]
        self.lift_height = 0  # Current lift height

    def set_lift_height(self, height: int):
        """Set forklift lift height"""
        self.lift_height = height

    def agent_process(self):
        """
        BUGFIX FASE 2: SimPy process real para Forklift
        Implementa ciclo pull-based con mecanica de elevacion

        Diferencias vs GroundOperator:
        - Tiempo de elevacion/bajada de horquilla
        - Velocidad mas lenta (default_speed = 0.8)
        - Descarga multiple en stagings (MULTI-STAGING SUPPORT)
        """
        # Configuracion de simulacion
        TIME_PER_CELL = 0.1  # Segundos por celda de grid
        LIFT_TIME = 2.0      # Segundos para elevar/bajar horquilla

        # Inicializar posicion en depot
        staging_locs = self.almacen.data_manager.get_outbound_staging_locations()
        depot_location = staging_locs.get(1, (3, 29))  # Staging 1 como depot default
        self.current_position = depot_location

        print(f"[{self.id}] Proceso iniciado en depot {depot_location}")

        while True:
            # PASO 1: Solicitar asignacion de tour
            self.status = "idle"
            
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'agent_type': self.type,
                'position': self.current_position,
                'status': self.status,
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })
            
            tour = self.almacen.dispatcher.solicitar_asignacion(self)

            if tour is None:
                if self.almacen.simulacion_ha_terminado():
                    print(f"[{self.id}] Simulacion finalizada, saliendo...")
                    break
                
                yield self.env.timeout(5.0)
                continue

            tour_start_time = self.env.now

            # PASO 2: Procesar tour asignado
            self.status = "working"
            work_orders = tour['work_orders']
            route_info = tour['route']

            print(f"[{self.id}] t={self.env.now:.1f} Tour asignado: "
                  f"{len(work_orders)} WOs, distancia: {tour['total_distance']:.1f}")

            if work_orders:
                self.almacen.dispatcher.notificar_inicio_trabajo(self, work_orders[0])

            # PASO 3: Visitar cada ubicacion de picking
            visit_sequence = route_info['visit_sequence']
            segment_paths = route_info['segment_paths']
            segment_distances = route_info['segment_distances']

            for idx, wo in enumerate(visit_sequence):
                segment_path = segment_paths[idx] if idx < len(segment_paths) else []
                segment_distance = segment_distances[idx] if idx < len(segment_distances) else 0

                if segment_path and len(segment_path) > 1:
                    self.status = "moving"
                    
                    self.almacen.registrar_evento('estado_agente', {
                        'agent_id': self.id,
                        'agent_type': self.type,
                        'position': self.current_position,
                        'status': self.status,
                        'current_task': wo.id if wo else None,
                        'current_work_area': wo.work_area if wo else None,
                        'cargo_volume': self.cargo_volume
                    })
                    
                    print(f"[{self.id}] t={self.env.now:.1f} Navegando a {wo.ubicacion} "
                          f"(path: {len(segment_path)} pasos)")
                    
                    for step_idx, step_position in enumerate(segment_path[1:], 1):
                        self.current_position = step_position
                        
                        self.almacen.registrar_evento('estado_agente', {
                            'agent_id': self.id,
                            'agent_type': self.type,
                            'position': self.current_position,
                            'status': self.status,
                            'current_task': wo.id if wo else None,
                            'current_work_area': wo.work_area if wo else None,
                            'cargo_volume': self.cargo_volume
                        })

                        if wo:
                            progress = round(((wo.cantidad_total - wo.cantidad_restante) / wo.cantidad_total) * 100, 2) if wo.cantidad_total > 0 else 0
                            self.almacen.registrar_evento('work_order_update', {
                                'id': wo.id,
                                'order_id': wo.order_id,
                                'tour_id': getattr(wo, 'tour_id', None),
                                'sku_id': wo.sku_id,
                                'product': wo.sku_name,
                                'status': 'in_progress',
                                'assigned_agent_id': wo.assigned_agent_id,
                                'priority': getattr(wo, 'priority', 99),
                                'items': getattr(wo, 'items', 1),
                                'total_qty': wo.cantidad_total,
                                'volume': getattr(wo, 'volume', wo.volumen_restante),
                                'location': wo.ubicacion,
                                'staging': wo.staging_id,
                                'work_group': wo.work_group,
                                'work_area': wo.work_area,
                                'executions': getattr(wo, 'picking_executions', 0),
                                'start_time': wo.tiempo_inicio,
                                'progress': progress,
                                'tiempo_fin': getattr(wo, 'tiempo_fin', None)
                            })
                        
                        yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                        
                        print(f"[{self.id}] t={self.env.now:.1f} Paso {step_idx}/{len(segment_path)-1}: {step_position}")
                else:
                    self.current_position = wo.ubicacion
                    self.total_distance_traveled += segment_distance

                self.status = "lifting"
                print(f"[{self.id}] t={self.env.now:.1f} Elevando horquilla")
                
                # Registrar evento con estado de lifting
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id if wo else None,
                    'current_work_area': wo.work_area if wo else None,
                    'cargo_volume': self.cargo_volume
                })
                
                yield self.env.timeout(LIFT_TIME)
                self.set_lift_height(1)

                self.status = "picking"
                print(f"[{self.id}] t={self.env.now:.1f} Picking en {wo.ubicacion}")
                
                # Registrar evento con estado de picking
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id if wo else None,
                    'current_work_area': wo.work_area if wo else None,
                    'cargo_volume': self.cargo_volume
                })
                
                picking_duration = self.discharge_time
                yield self.env.timeout(picking_duration)

                print(f"[{self.id}] t={self.env.now:.1f} Bajando horquilla")
                yield self.env.timeout(LIFT_TIME)
                self.set_lift_height(0)

                total_operation_duration = LIFT_TIME + picking_duration + LIFT_TIME
                self.almacen.registrar_evento('operation_completed', {
                    'agent_id': self.id,
                    'data': {
                        'duration': total_operation_duration,
                        'work_order_id': wo.id
                    }
                })
                self.almacen.registrar_evento('task_completed', {
                    'agent_id': self.id,
                    'task_id': wo.id,
                    'data': {
                        'task_ubicacion': wo.ubicacion,
                        'tiempo_picking': total_operation_duration
                    }
                })

                # ACTUALIZAR CARGO_VOLUME ANTES de poner cantidad_restante = 0
                if wo:
                    # Sumar el volumen ANTES de modificar cantidad_restante
                    self.cargo_volume += wo.calcular_volumen_restante()
                    wo.cantidad_restante = 0
                    if hasattr(wo, 'picking_executions'):
                        wo.picking_executions += 1
                    else:
                        wo.picking_executions = 1

                if wo:
                    wo.status = 'picked'
                    progress = round(((wo.cantidad_total - wo.cantidad_restante) / wo.cantidad_total) * 100, 2) if wo.cantidad_total > 0 else 0
                    self.almacen.registrar_evento('work_order_update', {
                        'id': wo.id,
                        'order_id': wo.order_id,
                        'tour_id': getattr(wo, 'tour_id', None),
                        'sku_id': wo.sku_id,
                        'product': wo.sku_name,
                        'status': 'picked',
                        'assigned_agent_id': wo.assigned_agent_id,
                        'priority': getattr(wo, 'priority', 99),
                        'items': getattr(wo, 'items', 1),
                        'total_qty': wo.cantidad_total,
                        'volume': getattr(wo, 'volume', wo.volumen_restante),
                        'location': wo.ubicacion,
                        'staging': wo.staging_id,
                        'work_group': wo.work_group,
                        'work_area': wo.work_area,
                        'executions': getattr(wo, 'picking_executions', 0) + 1,
                        'start_time': wo.tiempo_inicio,
                        'progress': progress,
                        'tiempo_fin': getattr(wo, 'tiempo_fin', None)
                    })

            # PASO 4: Agrupar WOs por staging y descargar en cada uno
            print(f"[{self.id}] Agrupando WOs por staging para descarga multiple")
            staging_groups = self._agrupar_wos_por_staging(work_orders)
            print(f"[{self.id}] Tour requiere visitar {len(staging_groups)} stagings: {list(staging_groups.keys())}")

            # Ordenar stagings por distancia desde posicion actual
            ordered_stagings = self._ordenar_stagings_por_distancia(staging_groups, self.current_position)
            staging_locs = self.almacen.data_manager.get_outbound_staging_locations()

            # Visitar cada staging en orden
            for idx, (staging_id, staging_wos) in enumerate(ordered_stagings, 1):
                staging_location = staging_locs.get(staging_id, (3, 29))
                # IMPORTANTE: Usar cantidad_inicial * sku.volumen porque cantidad_restante ya es 0 despues del picking
                volumen_staging = sum(wo.cantidad_inicial * wo.sku.volumen for wo in staging_wos)
                
                print(f"[{self.id}] [{idx}/{len(ordered_stagings)}] Navegando a staging {staging_id} "
                      f"en {staging_location} para descargar {len(staging_wos)} WOs ({volumen_staging}L)")
                
                # Navegar al staging
                if hasattr(self.almacen, 'route_calculator') and self.almacen.route_calculator:
                    try:
                        return_path = self.almacen.route_calculator.pathfinder.find_path(
                            self.current_position, staging_location
                        )
                        
                        if return_path and len(return_path) > 1:
                            self.status = "moving"
                            
                            self.almacen.registrar_evento('estado_agente', {
                                'agent_id': self.id,
                                'agent_type': self.type,
                                'position': self.current_position,
                                'status': self.status,
                                'current_task': None,
                                'cargo_volume': self.cargo_volume
                            })
                            
                            print(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                                  f"(path: {len(return_path)} pasos)")
                            
                            for step_idx, step_position in enumerate(return_path[1:], 1):
                                self.current_position = step_position
                                
                                self.almacen.registrar_evento('estado_agente', {
                                    'agent_id': self.id,
                                    'agent_type': self.type,
                                    'position': self.current_position,
                                    'status': self.status,
                                    'current_task': None,
                                    'cargo_volume': self.cargo_volume
                                })
                                
                                yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                                
                                if step_idx % 5 == 0:
                                    print(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                                          f"paso {step_idx}/{len(return_path)-1}")
                            
                            self.total_distance_traveled += len(return_path) - 1
                        else:
                            self.current_position = staging_location
                    except Exception as e:
                        print(f"[{self.id}] ERROR en pathfinding a staging {staging_id}: {e}")
                        self.current_position = staging_location
                
                # DESCARGAR en este staging
                self.status = "unloading"
                
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': None,
                    'cargo_volume': self.cargo_volume
                })
                
                print(f"[{self.id}] t={self.env.now:.1f} Descargando en staging {staging_id}")
                discharge_duration = self.discharge_time * len(staging_wos)
                yield self.env.timeout(discharge_duration)
                
                # Actualizar cargo_volume PARCIALMENTE (solo lo descargado)
                self.cargo_volume -= volumen_staging
                print(f"[{self.id}] t={self.env.now:.1f} Descargados {volumen_staging}L en staging {staging_id}, "
                      f"cargo restante: {self.cargo_volume}L")
                
                # Registrar evento de descarga parcial
                self.almacen.registrar_evento('partial_discharge', {
                    'agent_id': self.id,
                    'staging_id': staging_id,
                    'wos_descargadas': [wo.id for wo in staging_wos],
                    'volumen_descargado': volumen_staging,
                    'cargo_restante': self.cargo_volume,
                    'timestamp': self.env.now
                })

            # PASO 5: Limpiar cargo final (por seguridad)
            self.cargo_volume = 0
            print(f"[{self.id}] t={self.env.now:.1f} Descarga completa en todos los stagings")
            
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'agent_type': self.type,
                'position': self.current_position,
                'status': 'idle',
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })

            # PASO 6: Notificar completado
            tour_duration = self.env.now - tour_start_time
            self.almacen.registrar_evento('trip_completed', {
                'agent_id': self.id,
                'data': {
                    'duration': tour_duration,
                    'num_work_orders': len(work_orders)
                }
            })
            self.almacen.dispatcher.notificar_completado(self, work_orders)
            self.tasks_completed += len(work_orders)

            print(f"[{self.id}] t={self.env.now:.1f} Tour completado, "
                  f"total completadas: {self.tasks_completed}")



def crear_operarios(env: simpy.Environment, almacen: Any,
                    configuracion: Dict[str, Any],
                    simulador: Any = None, pathfinder: Any = None,
                    layout_manager: Any = None) -> Tuple[List[Any], List[BaseOperator]]:
    """
    Factory function to create warehouse operators based on configuration

    Args:
        env: SimPy environment
        almacen: Warehouse instance
        configuracion: Configuration dictionary
        simulador: Main simulator reference (optional)
        pathfinder: Pathfinder instance (optional)
        layout_manager: LayoutManager instance (optional)

    Returns:
        Tuple of (procesos_operarios, operarios)
        - procesos_operarios: List of SimPy processes
        - operarios: List of operator instances
    """
    print("[OPERATORS] Creando operarios desde configuracion...")

    operarios: List[BaseOperator] = []
    procesos_operarios: List[Any] = []

    # Get agent configuration from agent_types array
    agent_types_config = configuracion.get('agent_types', [])

    if not agent_types_config:
        # Fallback: Create default agents from legacy config
        print("[OPERATORS] No agent_types encontrado, usando configuracion legacy...")

        num_terrestres = configuracion.get('num_operarios_terrestres', 2)
        num_montacargas = configuracion.get('num_montacargas', 1)

        # Create ground operators
        for i in range(num_terrestres):
            agent_id = f"GroundOp-{i+1:02d}"
            operator = GroundOperator(
                agent_id=agent_id,
                env=env,
                almacen=almacen,
                configuracion=configuracion,
                capacity=150,
                discharge_time=5,
                work_area_priorities={"Area_Ground": 1, "Area_High": 2, "Area_Special": 3},
                pathfinder=pathfinder,
                layout_manager=layout_manager,
                simulador=simulador
            )
            operarios.append(operator)
            proceso = env.process(operator.agent_process())
            procesos_operarios.append(proceso)

        # Create forklifts
        for i in range(num_montacargas):
            agent_id = f"Forklift-{i+1:02d}"
            forklift = Forklift(
                agent_id=agent_id,
                env=env,
                almacen=almacen,
                configuracion=configuracion,
                capacity=1000,
                discharge_time=5,
                work_area_priorities={"Area_High": 1, "Area_Special": 2},
                pathfinder=pathfinder,
                layout_manager=layout_manager,
                simulador=simulador
            )
            operarios.append(forklift)
            proceso = env.process(forklift.agent_process())
            procesos_operarios.append(proceso)

    else:
        # Create agents from agent_types configuration
        print(f"[OPERATORS] Creando {len(agent_types_config)} agentes desde agent_types...")

        for idx, agent_config in enumerate(agent_types_config):
            agent_type = agent_config.get('type', 'GroundOperator')
            capacity = agent_config.get('capacity', 150)
            discharge_time = agent_config.get('discharge_time', 5)
            work_area_priorities = agent_config.get('work_area_priorities', {})

            # Generate unique ID
            if agent_type == "GroundOperator":
                # Count existing ground operators
                ground_count = sum(1 for op in operarios if op.type == "GroundOperator")
                agent_id = f"GroundOp-{ground_count+1:02d}"

                operator = GroundOperator(
                    agent_id=agent_id,
                    env=env,
                    almacen=almacen,
                    configuracion=configuracion,
                    capacity=capacity,
                    discharge_time=discharge_time,
                    work_area_priorities=work_area_priorities,
                    pathfinder=pathfinder,
                    layout_manager=layout_manager,
                    simulador=simulador
                )
                operarios.append(operator)
                proceso = env.process(operator.agent_process())
                procesos_operarios.append(proceso)

            elif agent_type == "Forklift":
                # Count existing forklifts
                forklift_count = sum(1 for op in operarios if op.type == "Forklift")
                agent_id = f"Forklift-{forklift_count+1:02d}"

                forklift = Forklift(
                    agent_id=agent_id,
                    env=env,
                    almacen=almacen,
                    configuracion=configuracion,
                    capacity=capacity,
                    discharge_time=discharge_time,
                    work_area_priorities=work_area_priorities,
                    pathfinder=pathfinder,
                    layout_manager=layout_manager,
                    simulador=simulador
                )
                operarios.append(forklift)
                proceso = env.process(forklift.agent_process())
                procesos_operarios.append(proceso)

            else:
                print(f"[OPERATORS WARNING] Tipo de agente desconocido: {agent_type}")

    print(f"[OPERATORS] Creados {len(operarios)} operarios:")
    for operario in operarios:
        print(f"  - {operario.id} ({operario.type}) - Capacidad: {operario.capacity}")

    return procesos_operarios, operarios