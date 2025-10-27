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
        print(f"[DISPATCHER DEBUG] Configuración recibida: {configuracion}")
        print(f"[DISPATCHER DEBUG] dispatch_strategy en config: '{configuracion.get('dispatch_strategy', 'NO ENCONTRADO')}'")
        self.estrategia = configuracion.get('dispatch_strategy', 'Optimizacion Global')
        print(f"[DISPATCHER DEBUG] Estrategia asignada: '{self.estrategia}'")
        
        # Tour Type (from config.json)
        self.tour_type = configuracion.get('tour_type', 'Tour Mixto (Multi-Destino)')
        print(f"[DISPATCHER DEBUG] Tour type: '{self.tour_type}'")

        # Statistics
        self.total_asignaciones = 0
        self.total_tours_creados = 0
        
        # FASE 2: Contador inicial de WorkOrders para metadata
        self.work_orders_total_inicial = 0

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
            wo.status = "released"

        # FASE 2: Configurar contador inicial de WorkOrders para metadata
        if not hasattr(self, 'work_orders_total_inicial') or self.work_orders_total_inicial == 0:
            self.work_orders_total_inicial = len(self.lista_maestra_work_orders)
            # print(f"[DISPATCHER] Total WorkOrders iniciales configurado: {self.work_orders_total_inicial}")

        # print(f"[DISPATCHER] {self.env.now:.2f} - Agregados {len(work_orders)} WorkOrders. "
        #       f"Total pendientes: {len(self.work_orders_pendientes)}")

    def registrar_operador_disponible(self, operator: Any) -> None:
        """
        Register operator as available for work assignment

        Args:
            operator: GroundOperator or Forklift instance
        """
        if operator not in self.operadores_disponibles:
            self.operadores_disponibles.append(operator)
        # print(f"[DISPATCHER] {self.env.now:.2f} - Operador {operator.type}_{operator.id} "
        #       f"registrado como disponible (pos: {operator.current_position})")

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
            # BUGFIX: Solo log cada 10 segundos para evitar spam
            if not hasattr(self, '_last_no_work_log'):
                self._last_no_work_log = {}
            
            operator_key = f"{operator.type}_{operator.id}"
            last_log_time = self._last_no_work_log.get(operator_key, 0)
            
            if self.env.now - last_log_time >= 10.0:
                print(f"[DISPATCHER] {self.env.now:.2f} - No hay WorkOrders pendientes para "
                      f"{operator.type}_{operator.id}")
                self._last_no_work_log[operator_key] = self.env.now
            
            return None

        # BUGFIX: Evitar spam de logs - solo log cada 5 segundos
        if not hasattr(self, '_last_request_log'):
            self._last_request_log = {}
        
        operator_key = f"{operator.type}_{operator.id}"
        last_log_time = self._last_request_log.get(operator_key, 0)
        
        if self.env.now - last_log_time >= 5.0:
            print(f"[DISPATCHER] {self.env.now:.2f} - Operador {operator.type}_{operator.id} "
                  f"solicita asignacion (pos: {operator.current_position})")
            self._last_request_log[operator_key] = self.env.now

        # Step 2: Select candidate WorkOrders based on strategy
        candidatos = self._seleccionar_work_orders_candidatos(operator)

        if not candidatos:
            # BUGFIX: Evitar loop infinito - solo log cada 10 segundos
            if not hasattr(self, '_last_no_candidates_log'):
                self._last_no_candidates_log = {}
            
            operator_key = f"{operator.type}_{operator.id}"
            last_log_time = self._last_no_candidates_log.get(operator_key, 0)
            
            if self.env.now - last_log_time >= 10.0:
                print(f"[DISPATCHER] No hay candidatos viables para {operator.type}_{operator.id}")
                self._last_no_candidates_log[operator_key] = self.env.now
            
            return None

        print(f"[DISPATCHER] Estrategia '{self.estrategia}' selecciono {len(candidatos)} candidatos")

        # Step 3: Select best batch based on strategy
        if self.estrategia in ("Optimizacion Global", "Ejecucion de Plan (Filtro por Prioridad)"):
            # Para estas estrategias, los candidatos YA representan el tour correcto
            # - Optimizacion Global: primera WO por costo, resto por pick_sequence
            # - Ejecucion de Plan: todo por pick_sequence desde la primera WO
            selected_work_orders = candidatos
            print(f"[DISPATCHER] {self.estrategia}: usando tour construido por la estrategia ({len(selected_work_orders)} WOs)")
        else:
            # Para otras estrategias, usar selección por costo
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
        elif self.estrategia == "Ejecucion de Plan (Filtro por Prioridad)" or self.estrategia == "Ejecución de Plan (Filtro por Prioridad)":
            return self._estrategia_ejecucion_plan(operator)
        elif self.estrategia == "Cercania":
            return self._estrategia_cercania(operator)
        else:
            # Default to Optimizacion Global if unknown strategy
            print(f"[DISPATCHER WARN] Estrategia desconocida '{self.estrategia}', usando Optimizacion Global")
            return self._estrategia_optimizacion_global(operator)

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
        Optimización Global CORRECTA:
        1. Considerar TODAS las WOs compatibles con el operador (todas las áreas compatibles)
        2. Usar AssignmentCostCalculator solo para la PRIMERA WO (minimizar desplazamiento desde posicion actual)
        3. Para el resto del tour, seguir pick_sequence del Excel (solo del mismo área que la primera WO)
        """
        # Paso 1: Filtrar por compatibilidad de área de trabajo
        candidatos_compatibles = [wo for wo in self.work_orders_pendientes
                                 if operator.can_handle_work_area(wo.work_area)]
        
        if not candidatos_compatibles:
            return []
        
        # Paso 2: FILTRAR al área de MAYOR PRIORIDAD del operario (respeto estricto de WA)
        candidatos_area_prioridad = self._filtrar_por_area_prioridad(operator, candidatos_compatibles)
        if not candidatos_area_prioridad:
            return []

        # Paso 3: Usar AssignmentCostCalculator para encontrar la MEJOR primera WO dentro del área prioritaria
        print(f"[DISPATCHER DEBUG] [Optimización Global] Evaluando mejor primera WO (area prioritaria) entre {len(candidatos_area_prioridad)} candidatos")
        best_first_wo = self._encontrar_mejor_primera_wo(operator, candidatos_area_prioridad)
        if not best_first_wo:
            print(f"[DISPATCHER DEBUG] No se encontró mejor primera WO")
            return []
        
        print(f"[DISPATCHER] [Optimización Global] Primera WO por costo: {best_first_wo.id} (seq={best_first_wo.pick_sequence}, area={best_first_wo.work_area})")
        
        # Paso 4: Construir tour siguiendo pick_sequence desde la primera WO
        # Preferir misma área, pero permitir cambio de área si se agota la secuencia
        tour_wos = self._construir_tour_por_secuencia(operator, best_first_wo, candidatos_compatibles)
        
        # Si es Tour Simple, filtrar por staging location
        if self.tour_type == "Tour Simple (Un Destino)":
            tour_wos = self._filtrar_por_staging_unico(operator, tour_wos)
        
        return tour_wos

    def _estrategia_ejecucion_plan(self, operator: Any) -> List[Any]:
        """
        Ejecución de Plan (Filtro por Prioridad):
        ÚNICA DIFERENCIA respecto a Optimización Global:
        - NO usa AssignmentCostCalculator para la primera WO
        - Selecciona la WO con el pick_sequence más pequeño del área con mayor prioridad
        - El resto del tour se construye igual que Optimización Global (doble barrido con todas las áreas)
        """
        # Paso 1: Filtrar por compatibilidad de área de trabajo
        candidatos_compatibles = [wo for wo in self.work_orders_pendientes
                                 if operator.can_handle_work_area(wo.work_area)]
        
        if not candidatos_compatibles:
            return []
        
        # Paso 2: Filtrar solo WOs del área de trabajo con MAYOR prioridad
        candidatos_area_prioridad = self._filtrar_por_area_prioridad(operator, candidatos_compatibles)
        
        if not candidatos_area_prioridad:
            return []
        
        # Paso 3: Seleccionar la primera WO con el pick_sequence más pequeño (SIN AssignmentCostCalculator)
        print(f"[DISPATCHER DEBUG] Ejecucion de Plan: Buscando WO con menor pick_sequence entre {len(candidatos_area_prioridad)} candidatos")
        primera_wo = min(candidatos_area_prioridad, key=lambda wo: wo.pick_sequence)
        
        print(f"[DISPATCHER DEBUG] Ejecucion de Plan: Primera WO seleccionada: {primera_wo.id} con pick_sequence={primera_wo.pick_sequence}")
        
        # Paso 4: Construir tour siguiendo pick_sequence desde la primera WO (igual que Optimización Global)
        # IMPORTANTE: Pasar candidatos_compatibles (todas las áreas) para que el doble barrido
        # pueda agregar WOs de otras áreas si es necesario
        tour_wos = self._construir_tour_por_secuencia(operator, primera_wo, candidatos_compatibles)
        
        # Si es Tour Simple, filtrar por staging location
        if self.tour_type == "Tour Simple (Un Destino)":
            tour_wos = self._filtrar_por_staging_unico(operator, tour_wos)
        
        return tour_wos

    def _filtrar_por_area_prioridad(self, operator: Any, candidatos: List[Any]) -> List[Any]:
        """
        Filtra WorkOrders del área de trabajo con MAYOR prioridad para el operador
        
        Args:
            operator: Operador para evaluar prioridades
            candidatos: Lista de WorkOrders compatibles
            
        Returns:
            List[WorkOrder] - WOs del área con mayor prioridad
        """
        if not candidatos:
            return []
        
        # Obtener prioridades de todas las áreas de trabajo presentes
        area_priorities = {}
        for wo in candidatos:
            work_area = wo.work_area
            if work_area not in area_priorities:
                priority = operator.get_priority_for_work_area(work_area)
                area_priorities[work_area] = priority
        
        # Encontrar la menor prioridad (mejor) entre las áreas disponibles
        best_priority = min(area_priorities.values())
        
        # Filtrar WOs del área con mejor prioridad
        best_area_wos = [wo for wo in candidatos 
                        if area_priorities[wo.work_area] == best_priority]
        
        print(f"[DISPATCHER] Área con mejor prioridad: {best_priority}, "
              f"WOs encontradas: {len(best_area_wos)}")
        
        return best_area_wos

    def _filtrar_por_staging_unico(self, operator: Any, work_orders: List[Any]) -> List[Any]:
        """
        Filtra WOs para que todas sean de una sola ubicación de staging
        
        Args:
            operator: Operator instance
            work_orders: List of WorkOrders to filter
            
        Returns:
            List of WorkOrders with consistent staging_id
        """
        if not work_orders:
            return []
        
        # Group by staging_id
        staging_groups = {}
        for wo in work_orders:
            staging_id = wo.staging_id
            if staging_id not in staging_groups:
                staging_groups[staging_id] = []
            staging_groups[staging_id].append(wo)
        
        # Select the group with most WOs that fit in capacity
        best_group = []
        best_volume = 0
        
        for staging_id, group_wos in staging_groups.items():
            group_volume = sum(wo.calcular_volumen_restante() for wo in group_wos)
            
            if (group_volume <= operator.capacity and 
                group_volume > best_volume):
                best_group = group_wos
                best_volume = group_volume
        
        # Limit to max_wos_por_tour
        if len(best_group) > self.max_wos_por_tour:
            best_group = best_group[:self.max_wos_por_tour]
        
        if best_group:
            staging_id = best_group[0].staging_id
            print(f"[DISPATCHER DEBUG] Tour Simple: Seleccionado grupo de {len(best_group)} WOs para staging {staging_id}")
        
        return best_group

    def _encontrar_mejor_primera_wo(self, operator: Any, candidatos: List[Any]) -> Optional[Any]:
        """
        Encuentra la mejor primera WO usando AssignmentCostCalculator
        
        Args:
            operator: Operador para evaluar costos
            candidatos: Lista de WorkOrders del área con mejor prioridad
            
        Returns:
            WorkOrder - Mejor primera WO o None si no hay candidatos válidos
        """
        if not candidatos:
            return None
        
        # Calcular costos para todas las candidatas
        costos = []
        current_pos = operator.current_position
        if current_pos is None:
            # Usar posición del depot si el operador no tiene posición actual
            staging_locs = self.data_manager.get_outbound_staging_locations()
            current_pos = staging_locs.get(1, (3, 29))  # Staging 1 como depot default
        
        print(f"[DISPATCHER DEBUG] Calculando costos desde posición: {current_pos}")
        for wo in candidatos:
            cost_result = self.assignment_calculator.calculate_cost(operator, wo, current_pos)
            costos.append((wo, cost_result))
        
        # Ordenar por costo total (menor es mejor)
        costos.sort(key=lambda x: x[1].total_cost)
        
        # Retornar la mejor WO que quepa en capacidad
        for wo, cost_result in costos:
            wo_volume = wo.calcular_volumen_restante()
            if wo_volume <= operator.capacity:
                print(f"[DISPATCHER] Mejor primera WO: {wo.id} "
                      f"(costo: {cost_result.total_cost:.0f}, volumen: {wo_volume})")
                return wo
        
        # Si ninguna WO cabe sola, retornar la mejor (será marcada como oversized)
        if costos:
            best_wo = costos[0][0]
            print(f"[DISPATCHER] WARNING: Mejor WO {best_wo.id} excede capacidad "
                  f"({best_wo.calcular_volumen_restante()} > {operator.capacity})")
            return best_wo
        
        return None

    def _construir_tour_por_secuencia(self, operator: Any, primera_wo: Any, candidatos: List[Any]) -> List[Any]:
        """
        Construye tour siguiendo pick_sequence con DOBLE BARRIDO por área.
        
        LÓGICA DE DOBLE BARRIDO:
        
        1. BARRIDO PRINCIPAL (Progresivo):
           - Punto de inicio: min_seq (último pick_sequence agregado o 1 si primera área)
           - Condición: wo.pick_sequence >= min_seq
           - Objetivo: Mantener ruta progresiva y secuencial
           - Orden: Ascendente por pick_sequence
        
        2. BARRIDO SECUNDARIO (Circular / Llenado de Huecos):
           - Activación: Solo si queda capacidad después de Barrido 1
           - Punto de inicio: pick_sequence = 1
           - Condición: wo.pick_sequence < min_seq
           - Objetivo: Maximizar utilización con retrocesos mínimos
           - Orden: Ascendente por pick_sequence
        
        CAMBIO DE ÁREA:
        - Al agotar un área, pasar a siguiente por prioridad
        - Continuar desde último pick_sequence agregado
        
        RESTRICCIÓN DE STAGING:
        - Tour Mixto (Multi-Destino): Sin restricción de staging_id
        - Tour Simple (Un Destino): Con restricción de staging_id
        
        Args:
            operator: Instancia de GroundOperator o Forklift
            primera_wo: Primera WorkOrder del tour
            candidatos: Lista de WorkOrders candidatas
        
        Returns:
            List[WorkOrder]: Lista ordenada de WOs para el tour
        """
        if not primera_wo or not candidatos:
            return []
        
        # ==================== INICIALIZACIÓN ====================
        tour_wos = []
        volume_acumulado = 0
        primera_volume = primera_wo.calcular_volumen_restante()
        
        # Validar que primera WO quepa
        if primera_volume <= operator.capacity:
            tour_wos.append(primera_wo)
            volume_acumulado += primera_volume
        else:
            print(f"[DISPATCHER ERROR] Primera WO {primera_wo.id} excede capacidad")
            return []
        
        # ==================== PREPARAR ÁREAS ====================
        # Obtener áreas compatibles con el operador
        areas_presentes = {}
        for wo in candidatos:
            pr = operator.get_priority_for_work_area(wo.work_area)
            if pr != 999:  # 999 = incompatible
                areas_presentes[wo.work_area] = pr
        
        # Ordenar áreas: primera área primero, luego resto por prioridad
        otras_areas = [a for a in areas_presentes.keys() if a != primera_wo.work_area]
        otras_areas.sort(key=lambda a: areas_presentes[a])
        ordered_areas = [primera_wo.work_area] + otras_areas
        
        # ==================== RASTREO DE ESTADO ====================
        ultimo_seq_agregado = primera_wo.pick_sequence  # Para cambio de área
        usadas = {primera_wo}  # Set de WOs ya agregadas
        
        # ==================== LOGGING INICIAL ====================
        print(f"[DISPATCHER] ===== INICIO CONSTRUCCION TOUR =====")
        print(f"[DISPATCHER] Primera WO: {primera_wo.id} (seq={primera_wo.pick_sequence}, area={primera_wo.work_area})")
        print(f"[DISPATCHER] Capacidad disponible: {operator.capacity}L")
        print(f"[DISPATCHER] Áreas a procesar: {ordered_areas}")
        print(f"[DISPATCHER] Tour type: {self.tour_type}")
        
        # ==================== PROCESAR CADA ÁREA ====================
        for area in ordered_areas:
            # Verificar límites globales
            if len(tour_wos) >= self.max_wos_por_tour:
                print(f"[DISPATCHER] Límite max_wos_por_tour alcanzado: {self.max_wos_por_tour}")
                break
            
            if volume_acumulado >= operator.capacity:
                print(f"[DISPATCHER] Capacidad llena: {volume_acumulado}/{operator.capacity}L")
                break
            
            # Obtener WOs disponibles del área actual
            area_wos = [wo for wo in candidatos 
                        if wo.work_area == area and wo not in usadas]
            
            # RESTRICCIÓN DE STAGING para Tour Simple
            if self.tour_type == "Tour Simple (Un Destino)":
                area_wos = [wo for wo in area_wos 
                            if wo.staging_id == primera_wo.staging_id]
            
            if not area_wos:
                print(f"[DISPATCHER] [{area}] No hay WOs disponibles")
                continue
            
            # Ordenar por pick_sequence
            area_wos_sorted = sorted(area_wos, key=lambda wo: wo.pick_sequence)
            
            # Determinar secuencia mínima para esta área
            # IMPORTANTE: Usar ultimo_seq_agregado para TODAS las áreas (incluida la primera)
            # Esto asegura que el doble barrido comience desde donde quedó la primera WO
            # seleccionada (ya sea por costo en Optimización Global o por seq en Ejecución de Plan)
            min_seq = ultimo_seq_agregado
            
            print(f"\n[DISPATCHER] ===== PROCESANDO ÁREA: {area} =====")
            print(f"[DISPATCHER] [{area}] WOs disponibles: {len(area_wos_sorted)}")
            print(f"[DISPATCHER] [{area}] Capacidad restante: {operator.capacity - volume_acumulado}L")
            print(f"[DISPATCHER] [{area}] Min sequence: {min_seq}")
            
            # ==================== BARRIDO 1: PRINCIPAL (PROGRESIVO) ====================
            print(f"[DISPATCHER] [{area}] --- BARRIDO PRINCIPAL (seq >= {min_seq}) ---")
            
            wos_agregadas_barrido1 = 0
            volumen_barrido1 = 0
            
            for wo in area_wos_sorted:
                # Verificar límites
                if len(tour_wos) >= self.max_wos_por_tour:
                    break
                
                if volume_acumulado >= operator.capacity:
                    break
                
                # CONDICIÓN BARRIDO 1: pick_sequence >= min_seq
                if wo.pick_sequence < min_seq:
                    continue  # Omitir para Barrido 2
                
                wo_volume = wo.calcular_volumen_restante()
                
                # Intentar agregar si cabe
                if volume_acumulado + wo_volume <= operator.capacity:
                    tour_wos.append(wo)
                    usadas.add(wo)
                    volume_acumulado += wo_volume
                    volumen_barrido1 += wo_volume
                    ultimo_seq_agregado = wo.pick_sequence  # ACTUALIZAR
                    wos_agregadas_barrido1 += 1
                    
                    print(f"[DISPATCHER] [{area}]   + WO {wo.id} agregada "
                          f"(seq={wo.pick_sequence}, vol={wo_volume}L, "
                          f"acum={volume_acumulado}L)")
                else:
                    # No cabe - seguir probando siguientes (pueden ser mas pequenas)
                    print(f"[DISPATCHER] [{area}]   x WO {wo.id} no cabe "
                          f"(seq={wo.pick_sequence}, vol={wo_volume}L, "
                          f"falta={wo_volume - (operator.capacity - volume_acumulado)}L)")
            
            print(f"[DISPATCHER] [{area}] Barrido Principal completado: "
                  f"{wos_agregadas_barrido1} WOs, {volumen_barrido1}L")
            
            # ==================== BARRIDO 2: SECUNDARIO (CIRCULAR / LLENADO) ====================
            # Solo ejecutar si queda capacidad
            capacidad_restante = operator.capacity - volume_acumulado
            
            if capacidad_restante > 0 and len(tour_wos) < self.max_wos_por_tour:
                print(f"[DISPATCHER] [{area}] --- BARRIDO SECUNDARIO (seq < {min_seq}) ---")
                print(f"[DISPATCHER] [{area}] Capacidad restante: {capacidad_restante}L")
                
                wos_agregadas_barrido2 = 0
                volumen_barrido2 = 0
                
                for wo in area_wos_sorted:
                    # Verificar límites
                    if len(tour_wos) >= self.max_wos_por_tour:
                        break
                    
                    if volume_acumulado >= operator.capacity:
                        break
                    
                    # CONDICIÓN BARRIDO 2: pick_sequence < min_seq (llenado de huecos)
                    if wo.pick_sequence >= min_seq:
                        continue  # Ya evaluada en Barrido 1
                    
                    # Ya fue agregada
                    if wo in usadas:
                        continue
                    
                    wo_volume = wo.calcular_volumen_restante()
                    
                    # Intentar agregar si cabe
                    if volume_acumulado + wo_volume <= operator.capacity:
                        tour_wos.append(wo)
                        usadas.add(wo)
                        volume_acumulado += wo_volume
                        volumen_barrido2 += wo_volume
                        wos_agregadas_barrido2 += 1
                        
                        print(f"[DISPATCHER] [{area}]   < WO {wo.id} agregada (RETROCESO) "
                              f"(seq={wo.pick_sequence}, vol={wo_volume}L, "
                              f"acum={volume_acumulado}L)")
                    else:
                        print(f"[DISPATCHER] [{area}]   x WO {wo.id} no cabe "
                              f"(seq={wo.pick_sequence}, vol={wo_volume}L)")
                
                print(f"[DISPATCHER] [{area}] Barrido Secundario completado: "
                      f"{wos_agregadas_barrido2} WOs, {volumen_barrido2}L")
            else:
                print(f"[DISPATCHER] [{area}] Barrido Secundario OMITIDO "
                      f"(capacidad restante: {capacidad_restante}L)")
            
            # Resumen del área
            total_wos_area = wos_agregadas_barrido1 + (wos_agregadas_barrido2 if capacidad_restante > 0 else 0)
            total_vol_area = volumen_barrido1 + (volumen_barrido2 if capacidad_restante > 0 else 0)
            print(f"[DISPATCHER] [{area}] ÁREA COMPLETADA: "
                  f"{total_wos_area} WOs totales, {total_vol_area}L totales")
        
        # ==================== RESUMEN FINAL ====================
        utilizacion = (volume_acumulado / operator.capacity) * 100 if operator.capacity > 0 else 0
        areas_usadas = set(wo.work_area for wo in tour_wos)
        stagings_usados = set(wo.staging_id for wo in tour_wos)
        
        print(f"\n[DISPATCHER] ===== TOUR FINAL =====")
        print(f"[DISPATCHER] Total WOs: {len(tour_wos)}")
        print(f"[DISPATCHER] Volumen: {volume_acumulado}/{operator.capacity}L")
        print(f"[DISPATCHER] Utilización: {utilizacion:.1f}%")
        print(f"[DISPATCHER] Áreas: {areas_usadas}")
        print(f"[DISPATCHER] Stagings: {stagings_usados}")
        print(f"[DISPATCHER] Secuencias: [{', '.join(str(wo.pick_sequence) for wo in tour_wos)}]")
        
        return tour_wos

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
            current_pos = staging_locs.get(1, (3, 29))  # Staging 1 como depot default

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
        skipped_oversized = []  # Track WOs that are too big even alone

        for wo, cost_result in costos:
            wo_volume = wo.calcular_volumen_restante()

            # Check if this WO would fit
            if volume_acumulado + wo_volume <= operator.capacity:
                selected.append(wo)
                volume_acumulado += wo_volume

                if len(selected) >= self.max_wos_por_tour:
                    break  # Max tour size reached
            elif len(selected) == 0 and wo_volume > operator.capacity:
                # This WO is too big even by itself - skip it
                skipped_oversized.append(wo)
                print(f"[DISPATCHER] WARNING: WO {wo.id} volume ({wo_volume}) exceeds "
                      f"{operator.type}_{operator.id} capacity ({operator.capacity}) - SKIPPING")

        # If we couldn't select any WOs, mark oversized ones as completed to avoid infinite loop
        if not selected and skipped_oversized:
            print(f"[DISPATCHER] ERROR: {len(skipped_oversized)} WorkOrders too large for any operator!")
            print(f"[DISPATCHER] Marking oversized WorkOrders as staged to avoid deadlock...")
            for wo in skipped_oversized:
                wo.status = "staged"
                wo.cantidad_restante = 0
                self.work_orders_completados.append(wo)
                # Remove from pending
                if wo in self.work_orders_pendientes:
                    self.work_orders_pendientes.remove(wo)

        return selected

    def _construir_tour(self, operator: Any, work_orders: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Build optimal tour using RouteCalculator with tour_type support

        Args:
            operator: Operator instance
            work_orders: List of WorkOrders to visit

        Returns:
            RouteCalculator result dict or None if failed
        """
        if not work_orders:
            return None

        # Check if Tour Simple and validate staging consistency
        if self.tour_type == "Tour Simple (Un Destino)":
            work_orders = self._validar_tour_simple(work_orders)
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
            # Preserve first WorkOrder for "Optimización Global" strategy
            preserve_first = (self.estrategia == "Optimizacion Global")
            route_result = self.route_calculator.calculate_route(
                start_position=start_pos,
                work_orders=work_orders,
                return_to_start=True,  # Return to staging area after picks
                preserve_first=preserve_first
            )

            if route_result and route_result.get('success', False):
                return route_result
            else:
                print(f"[DISPATCHER ERROR] RouteCalculator fallo: {route_result.get('errors', [])}")
                return None

        except Exception as e:
            print(f"[DISPATCHER ERROR] Excepcion al calcular ruta: {e}")
            return None

    def _validar_tour_simple(self, work_orders: List[Any]) -> List[Any]:
        """
        Validate Tour Simple: All WorkOrders must have the same staging_id
        
        Args:
            work_orders: List of WorkOrders to validate
            
        Returns:
            List of WorkOrders with consistent staging_id, or empty list if invalid
        """
        if not work_orders:
            return []
        
        # Check staging consistency
        staging_ids = set(wo.staging_id for wo in work_orders)
        
        if len(staging_ids) > 1:
            print(f"[DISPATCHER ERROR] Tour Simple requiere WOs de una sola ubicación de staging")
            print(f"[DISPATCHER ERROR] Encontradas ubicaciones: {staging_ids}")
            print(f"[DISPATCHER ERROR] WOs: {[wo.id for wo in work_orders]}")
            return []
        
        print(f"[DISPATCHER DEBUG] Tour Simple validado: {len(work_orders)} WOs para staging {list(staging_ids)[0]}")
        return work_orders

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

            progress = round(((wo.cantidad_total - wo.cantidad_restante) / wo.cantidad_total) * 100, 2) if wo.cantidad_total > 0 else 0
            self.almacen.registrar_evento('work_order_update', {
                'id': wo.id,
                'order_id': wo.order_id,
                'tour_id': getattr(wo, 'tour_id', None),
                'sku_id': wo.sku_id,
                'product': wo.sku_name,
                'status': 'assigned',
                'assigned_agent_id': wo.assigned_agent_id,
                'priority': getattr(wo, 'priority', 99),
                'items': getattr(wo, 'items', 1),
                'total_qty': wo.cantidad_total,
                'volume': getattr(wo, 'volume', wo.volumen_restante),
                'location': wo.ubicacion,
                'pick_sequence': getattr(wo, 'pick_sequence', None),
                'staging': wo.staging_id,
                'work_group': wo.work_group,
                'work_area': wo.work_area,
                'executions': getattr(wo, 'picking_executions', 0),
                'start_time': wo.tiempo_inicio,
                'progress': progress,
                'tiempo_fin': getattr(wo, 'tiempo_fin', None)
            })

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

        progress = round(((work_order.cantidad_total - work_order.cantidad_restante) / work_order.cantidad_total) * 100, 2) if work_order.cantidad_total > 0 else 0
        self.almacen.registrar_evento('work_order_update', {
            'id': work_order.id,
            'order_id': work_order.order_id,
            'tour_id': getattr(work_order, 'tour_id', None),
            'sku_id': work_order.sku_id,
            'product': work_order.sku_name,
            'status': 'in_progress',
            'assigned_agent_id': work_order.assigned_agent_id,
            'priority': getattr(work_order, 'priority', 99),
            'items': getattr(work_order, 'items', 1),
            'total_qty': work_order.cantidad_total,
            'volume': getattr(work_order, 'volume', work_order.volumen_restante),
            'location': work_order.ubicacion,
                'pick_sequence': getattr(work_order, 'pick_sequence', None),
            'staging': work_order.staging_id,
            'work_group': work_order.work_group,
            'work_area': work_order.work_area,
            'executions': getattr(work_order, 'picking_executions', 0),
            'start_time': work_order.tiempo_inicio,
            'progress': progress,
            'tiempo_fin': getattr(work_order, 'tiempo_fin', None)
        })

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
            wo.status = "staged"
            wo.tiempo_fin = self.env.now
            
            # BUGFIX FASE4: Emitir evento work_order_update para registrar completado
            # Esto permite que el replay tenga datos completos de progreso
            self.almacen.registrar_evento('work_order_update', {
                'id': wo.id,
                'order_id': wo.order_id,
                'tour_id': getattr(wo, 'tour_id', None),
                'sku_id': wo.sku_id,
                'product': wo.sku_name,
                'status': 'staged',
                'assigned_agent_id': wo.assigned_agent_id,
                'priority': getattr(wo, 'priority', 99),
                'items': getattr(wo, 'items', 1),
                'total_qty': wo.cantidad_total,
                'volume': getattr(wo, 'volume', wo.volumen_restante),
                'location': wo.ubicacion,
                'pick_sequence': getattr(wo, 'pick_sequence', None),
                'staging': wo.staging_id,
                'work_group': wo.work_group,
                'work_area': wo.work_area,
                'executions': getattr(wo, 'picking_executions', 0),
                'start_time': getattr(wo, 'tiempo_inicio', None),
                'progress': 100,
                'tiempo_fin': wo.tiempo_fin
            })

            # NEW: Log work_order_completed for analytics and increment counter
            self.almacen.registrar_evento('work_order_completed', {
                'agent_id': operator_id,
                'work_order_id': wo.id,
                'data': {
                    'duration': wo.tiempo_fin - wo.tiempo_inicio if wo.tiempo_inicio else 0
                }
            })
            self.almacen.incrementar_contador_workorders()

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

    def dispatcher_process(self, operarios: List[Any]):
        """
        BUGFIX FASE 1: SimPy process para coordinar asignacion de trabajo

        Este proceso implementa un modelo pull-based donde:
        - Los operarios solicitan trabajo activamente (no push desde dispatcher)
        - El dispatcher responde con tours optimizados
        - Este proceso solo monitorea estado y loggea progreso

        Args:
            operarios: Lista de operarios (GroundOperator, Forklift)

        Yields:
            timeout events para permitir ejecucion de otros procesos
        """
        print("[DISPATCHER-PROCESS] Iniciando proceso de coordinacion...")
        print(f"[DISPATCHER-PROCESS] Operarios registrados: {len(operarios)}")

        # Registrar todos los operarios como disponibles al inicio
        for operario in operarios:
            self.registrar_operador_disponible(operario)
            print(f"[DISPATCHER-PROCESS] Operario {operario.id} registrado como disponible")

        # Contadores para logging periodico
        ultimo_reporte = 0
        intervalo_reporte = 10.0  # Reportar cada 10 segundos simulados

        while True:
            # Yield pequeno para permitir que otros procesos se ejecuten
            yield self.env.timeout(0.1)

            # Verificar si termino la simulacion
            if self.simulacion_ha_terminado():
                print(f"[DISPATCHER-PROCESS] Simulacion finalizada en t={self.env.now:.2f}")
                print(f"[DISPATCHER-PROCESS] WorkOrders completadas: {len(self.work_orders_completados)}/{len(self.lista_maestra_work_orders)}")
                break

            # Logging periodico del estado (cada intervalo_reporte segundos)
            if self.env.now >= ultimo_reporte + intervalo_reporte:
                ultimo_reporte = self.env.now
                stats = self.obtener_estadisticas()

                print(f"[DISPATCHER] t={self.env.now:.1f}s | "
                      f"Pending: {stats['pendientes']} | "
                      f"Assigned: {stats['asignados']} | "
                      f"InProgress: {stats['en_progreso']} | "
                      f"Completed: {stats['completados']}")

                # Logging de operarios disponibles vs activos
                print(f"[DISPATCHER]   Operarios disponibles: {len(self.operadores_disponibles)} | "
                      f"Activos: {len(self.operadores_activos)}")


# Export main class
__all__ = ['DispatcherV11']
