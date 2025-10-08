# -*- coding: utf-8 -*-
"""
Operators Module - Agent Classes for Warehouse Simulation
Digital Twin Warehouse Simulator

Contains agent classes (GroundOperator, Forklift) and factory function
"""

import simpy
from typing import List, Dict, Any, Optional, Tuple


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
        4. Navegar a staging area
        5. Descargar
        6. Notificar completado
        7. Repetir
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
            
            # FASE 1: Capturar cambio de estado a idle
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'tipo': self.type,
                'position': self.current_position,
                'status': self.status,
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })
            
            tour = self.almacen.dispatcher.solicitar_asignacion(self)

            if tour is None:
                # No hay trabajo disponible, verificar si termino
                if self.almacen.simulacion_ha_terminado():
                    print(f"[{self.id}] Simulacion finalizada, saliendo...")
                    break
                
                # Esperar un poco antes de reintentar
                yield self.env.timeout(1.0)
                continue

            # PASO 2: Procesar tour asignado
            self.status = "working"
            work_orders = tour['work_orders']
            route_info = tour['route']

            print(f"[{self.id}] t={self.env.now:.1f} Tour asignado: "
                  f"{len(work_orders)} WOs, distancia: {tour['total_distance']:.1f}")

            # Notificar inicio del primer WO
            if work_orders:
                self.almacen.dispatcher.notificar_inicio_trabajo(self, work_orders[0])

            # PASO 3: Visitar cada ubicacion de picking
            visit_sequence = route_info['visit_sequence']
            segment_paths = route_info['segment_paths']
            segment_distances = route_info['segment_distances']

            for idx, wo in enumerate(visit_sequence):
                # Navegar a ubicacion de picking usando pathfinding paso a paso
                segment_path = segment_paths[idx] if idx < len(segment_paths) else []
                segment_distance = segment_distances[idx] if idx < len(segment_distances) else 0

                if segment_path and len(segment_path) > 1:
                    self.status = "moving"
                    
                    # FASE 1: Capturar cambio de estado a moving (navegando)
                    self.almacen.registrar_evento('estado_agente', {
                        'agent_id': self.id,
                        'tipo': self.type,
                        'position': self.current_position,
                        'status': self.status,
                        'current_task': wo.id if wo else None,
                        'cargo_volume': self.cargo_volume
                    })
                    
                    print(f"[{self.id}] t={self.env.now:.1f} Navegando a {wo.ubicacion} "
                          f"(path: {len(segment_path)} pasos)")
                    
                    # MOVIMIENTO PASO A PASO: Generar eventos intermedios
                    for step_idx, step_position in enumerate(segment_path[1:], 1):  # Skip first (current position)
                        # Actualizar posición paso a paso
                        self.current_position = step_position
                        
                        # Registrar evento intermedio de movimiento
                        self.almacen.registrar_evento('estado_agente', {
                            'agent_id': self.id,
                            'tipo': self.type,
                            'position': self.current_position,
                            'status': self.status,
                            'current_task': wo.id if wo else None,
                            'cargo_volume': self.cargo_volume
                        })
                        
                        # Avanzar tiempo por celda
                        yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                        
                        print(f"[{self.id}] t={self.env.now:.1f} Paso {step_idx}/{len(segment_path)-1}: {step_position}")
                else:
                    # Fallback: movimiento directo si no hay path
                    self.current_position = wo.ubicacion
                    self.total_distance_traveled += segment_distance

                # FASE 1: Capturar evento de posición para replay
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'tipo': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id if wo else None,
                    'cargo_volume': self.cargo_volume
                })

                # Simular picking
                self.status = "picking"
                
                # FASE 1: Capturar cambio de estado a picking
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'tipo': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id if wo else None,
                    'cargo_volume': self.cargo_volume
                })
                
                print(f"[{self.id}] t={self.env.now:.1f} Picking en {wo.ubicacion}")
                yield self.env.timeout(self.discharge_time)

                # Actualizar cargo
                self.cargo_volume += wo.calcular_volumen_restante()

            # PASO 4: Navegar a staging area para descarga usando pathfinding paso a paso
            depot_location = self.almacen.data_manager.outbound_staging_locations.get(1, (0, 0))

            # Calcular ruta de regreso usando pathfinder
            if hasattr(self.almacen, 'route_calculator') and self.almacen.route_calculator:
                try:
                    return_path = self.almacen.route_calculator.pathfinder.find_path(self.current_position, depot_location)
                    if return_path and len(return_path) > 1:
                        self.status = "moving"
                        
                        # FASE 1: Capturar cambio de estado a moving (regresando)
                        self.almacen.registrar_evento('estado_agente', {
                            'agent_id': self.id,
                            'tipo': self.type,
                            'position': self.current_position,
                            'status': self.status,
                            'current_task': None,
                            'cargo_volume': self.cargo_volume
                        })
                        
                        print(f"[{self.id}] t={self.env.now:.1f} Regresando a staging (path: {len(return_path)} pasos)")
                        
                        # MOVIMIENTO PASO A PASO: Generar eventos intermedios de regreso
                        for step_idx, step_position in enumerate(return_path[1:], 1):
                            self.current_position = step_position
                            
                            # Registrar evento intermedio de movimiento
                            self.almacen.registrar_evento('estado_agente', {
                                'agent_id': self.id,
                                'tipo': self.type,
                                'position': self.current_position,
                                'status': self.status,
                                'current_task': None,
                                'cargo_volume': self.cargo_volume
                            })
                            
                            # Avanzar tiempo por celda
                            yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                            
                            print(f"[{self.id}] t={self.env.now:.1f} Regreso paso {step_idx}/{len(return_path)-1}: {step_position}")
                        
                        self.total_distance_traveled += len(return_path) - 1
                    else:
                        # Fallback: movimiento directo si no hay path
                        final_segment_distance = segment_distances[-1] if segment_distances else 0
                        self.current_position = depot_location
                        self.total_distance_traveled += final_segment_distance
                except Exception as e:
                    print(f"[{self.id}] Error calculando ruta de regreso: {e}")
                    # Fallback: movimiento directo
                    final_segment_distance = segment_distances[-1] if segment_distances else 0
                    self.current_position = depot_location
                    self.total_distance_traveled += final_segment_distance
            else:
                # Fallback: movimiento directo si no hay route_calculator
                final_segment_distance = segment_distances[-1] if segment_distances else 0
                self.current_position = depot_location
                self.total_distance_traveled += final_segment_distance

            # PASO 5: Descargar
            self.status = "unloading"
            
            # FASE 1: Capturar cambio de estado a unloading
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'tipo': self.type,
                'position': self.current_position,
                'status': self.status,
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })
            
            print(f"[{self.id}] t={self.env.now:.1f} Descargando en staging")
            yield self.env.timeout(self.discharge_time)
            self.cargo_volume = 0
            
            # FASE 1: Capturar evento después de descarga
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'tipo': self.type,
                'position': self.current_position,
                'status': 'idle',
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })

            # PASO 6: Notificar completado
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
            
            # FASE 1: Capturar cambio de estado a idle
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'tipo': self.type,
                'position': self.current_position,
                'status': self.status,
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })
            
            tour = self.almacen.dispatcher.solicitar_asignacion(self)

            if tour is None:
                # No hay trabajo disponible, verificar si termino
                if self.almacen.simulacion_ha_terminado():
                    print(f"[{self.id}] Simulacion finalizada, saliendo...")
                    break
                
                # Esperar un poco antes de reintentar
                yield self.env.timeout(1.0)
                continue

            # PASO 2: Procesar tour asignado
            self.status = "working"
            work_orders = tour['work_orders']
            route_info = tour['route']

            print(f"[{self.id}] t={self.env.now:.1f} Tour asignado: "
                  f"{len(work_orders)} WOs, distancia: {tour['total_distance']:.1f}")

            # Notificar inicio del primer WO
            if work_orders:
                self.almacen.dispatcher.notificar_inicio_trabajo(self, work_orders[0])

            # PASO 3: Visitar cada ubicacion de picking
            visit_sequence = route_info['visit_sequence']
            segment_paths = route_info['segment_paths']
            segment_distances = route_info['segment_distances']

            for idx, wo in enumerate(visit_sequence):
                # Navegar a ubicacion de picking usando pathfinding paso a paso
                segment_path = segment_paths[idx] if idx < len(segment_paths) else []
                segment_distance = segment_distances[idx] if idx < len(segment_distances) else 0

                if segment_path and len(segment_path) > 1:
                    self.status = "moving"
                    
                    # FASE 1: Capturar cambio de estado a moving (navegando)
                    self.almacen.registrar_evento('estado_agente', {
                        'agent_id': self.id,
                        'tipo': self.type,
                        'position': self.current_position,
                        'status': self.status,
                        'current_task': wo.id if wo else None,
                        'cargo_volume': self.cargo_volume
                    })
                    
                    print(f"[{self.id}] t={self.env.now:.1f} Navegando a {wo.ubicacion} "
                          f"(path: {len(segment_path)} pasos)")
                    
                    # MOVIMIENTO PASO A PASO: Generar eventos intermedios
                    for step_idx, step_position in enumerate(segment_path[1:], 1):  # Skip first (current position)
                        # Actualizar posición paso a paso
                        self.current_position = step_position
                        
                        # Registrar evento intermedio de movimiento
                        self.almacen.registrar_evento('estado_agente', {
                            'agent_id': self.id,
                            'tipo': self.type,
                            'position': self.current_position,
                            'status': self.status,
                            'current_task': wo.id if wo else None,
                            'cargo_volume': self.cargo_volume
                        })
                        
                        # Avanzar tiempo por celda
                        yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                        
                        print(f"[{self.id}] t={self.env.now:.1f} Paso {step_idx}/{len(segment_path)-1}: {step_position}")
                else:
                    # Fallback: movimiento directo si no hay path
                    self.current_position = wo.ubicacion
                    self.total_distance_traveled += segment_distance

                # FORKLIFT SPECIFIC: Elevar horquilla
                self.status = "lifting"
                print(f"[{self.id}] t={self.env.now:.1f} Elevando horquilla")
                yield self.env.timeout(LIFT_TIME)
                self.set_lift_height(1)  # Altura elevada

                # Simular picking
                self.status = "picking"
                print(f"[{self.id}] t={self.env.now:.1f} Picking en {wo.ubicacion}")
                yield self.env.timeout(self.discharge_time)

                # FORKLIFT SPECIFIC: Bajar horquilla
                print(f"[{self.id}] t={self.env.now:.1f} Bajando horquilla")
                yield self.env.timeout(LIFT_TIME)
                self.set_lift_height(0)  # Altura baja

                # Actualizar cargo
                self.cargo_volume += wo.calcular_volumen_restante()

            # PASO 4: Navegar a staging area para descarga usando pathfinding paso a paso
            depot_location = self.almacen.data_manager.outbound_staging_locations.get(1, (0, 0))

            # Calcular ruta de regreso usando pathfinder
            if hasattr(self.almacen, 'route_calculator') and self.almacen.route_calculator:
                try:
                    return_path = self.almacen.route_calculator.pathfinder.find_path(self.current_position, depot_location)
                    if return_path and len(return_path) > 1:
                        self.status = "moving"
                        
                        # FASE 1: Capturar cambio de estado a moving (regresando)
                        self.almacen.registrar_evento('estado_agente', {
                            'agent_id': self.id,
                            'tipo': self.type,
                            'position': self.current_position,
                            'status': self.status,
                            'current_task': None,
                            'cargo_volume': self.cargo_volume
                        })
                        
                        print(f"[{self.id}] t={self.env.now:.1f} Regresando a staging (path: {len(return_path)} pasos)")
                        
                        # MOVIMIENTO PASO A PASO: Generar eventos intermedios de regreso
                        for step_idx, step_position in enumerate(return_path[1:], 1):
                            self.current_position = step_position
                            
                            # Registrar evento intermedio de movimiento
                            self.almacen.registrar_evento('estado_agente', {
                                'agent_id': self.id,
                                'tipo': self.type,
                                'position': self.current_position,
                                'status': self.status,
                                'current_task': None,
                                'cargo_volume': self.cargo_volume
                            })
                            
                            # Avanzar tiempo por celda
                            yield self.env.timeout(TIME_PER_CELL * self.default_speed)
                            
                            print(f"[{self.id}] t={self.env.now:.1f} Regreso paso {step_idx}/{len(return_path)-1}: {step_position}")
                        
                        self.total_distance_traveled += len(return_path) - 1
                    else:
                        # Fallback: movimiento directo si no hay path
                        final_segment_distance = segment_distances[-1] if segment_distances else 0
                        self.current_position = depot_location
                        self.total_distance_traveled += final_segment_distance
                except Exception as e:
                    print(f"[{self.id}] Error calculando ruta de regreso: {e}")
                    # Fallback: movimiento directo
                    final_segment_distance = segment_distances[-1] if segment_distances else 0
                    self.current_position = depot_location
                    self.total_distance_traveled += final_segment_distance
            else:
                # Fallback: movimiento directo si no hay route_calculator
                final_segment_distance = segment_distances[-1] if segment_distances else 0
                self.current_position = depot_location
                self.total_distance_traveled += final_segment_distance

            # PASO 5: Descargar
            self.status = "unloading"
            
            # FASE 1: Capturar cambio de estado a unloading
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'tipo': self.type,
                'position': self.current_position,
                'status': self.status,
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })
            
            print(f"[{self.id}] t={self.env.now:.1f} Descargando en staging")
            yield self.env.timeout(self.discharge_time)
            self.cargo_volume = 0
            
            # FASE 1: Capturar evento después de descarga
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'tipo': self.type,
                'position': self.current_position,
                'status': 'idle',
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })

            # PASO 6: Notificar completado
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
                capacity=150,  # Default capacity
                discharge_time=5,
                work_area_priorities={"Area_Ground": 1, "Area_Piso_L1": 2},
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
                capacity=1000,  # Default capacity
                discharge_time=5,
                work_area_priorities={"Area_Rack": 1},
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
