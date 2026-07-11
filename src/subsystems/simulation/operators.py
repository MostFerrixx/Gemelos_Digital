# -*- coding: utf-8 -*-
"""
Operators Module - Agent Classes for Warehouse Simulation
Digital Twin Warehouse Simulator

Contains agent classes (GroundOperator, Forklift) and factory function
"""

import simpy

import logging

logger = logging.getLogger(__name__)
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

        # Iniciativa #2 / Fase 2: indice de spawn (0-based) asignado por crear_operarios.
        # Se usa para el arranque escalonado (stagger temporal) y la dispersion espacial
        # (anden de salida distinto por agente). Default 0 => agente "ancla" en el depot.
        self.spawn_index = 0

        # Performance metrics
        self.total_distance_traveled = 0
        self.total_work_time = 0
        self.idle_time = 0

        # --- Bloque tiempos (C1: config-ificacion neutra) ---
        # Lee los parametros de tiempo del bloque "tiempos" de config.json.
        # Todos los defaults son exactamente los valores que antes estaban
        # hardcodeados, por lo que configs sin el bloque "tiempos" producen
        # comportamiento IDENTICO (cero cambio observable).
        _tiempos = configuracion.get("tiempos", {}) if configuracion else {}
        self.time_per_cell = float(_tiempos.get("time_per_cell", 0.1))
        self.speed_factor_ground = float(_tiempos.get("speed_factor_ground", 1.0))
        self.speed_factor_forklift = float(_tiempos.get("speed_factor_forklift", 0.8))
        _pick = _tiempos.get("tiempo_picking_por_linea", None)
        self.picking_time = float(_pick) if _pick is not None else None
        self.lift_time = float(_tiempos.get("tiempo_horquilla", 2.0))

        # INIT-4 (C1): modelo de tiempo de pick que escala con cantidad/volumen.
        # Bloque OPCIONAL config["tiempos"]["pick_time_model"]. Defaults NEUTROS:
        # con base=None y por_unidad=0 y por_volumen=0, _compute_pick_time()
        # devuelve EXACTAMENTE el valor historico (picking_time o discharge_time),
        # garantizando byte-identico con configs que NO traen el bloque.
        _ptm = _tiempos.get("pick_time_model", {})
        if not isinstance(_ptm, dict):
            _ptm = {}
        _ptm_base = _ptm.get("base", None)
        self.pick_time_base = float(_ptm_base) if _ptm_base is not None else None
        self.pick_time_por_unidad = float(_ptm.get("por_unidad", 0.0) or 0.0)
        self.pick_time_por_volumen = float(_ptm.get("por_volumen", 0.0) or 0.0)
        self.pick_time_minimo = float(_ptm.get("minimo", 0.0) or 0.0)

        logger.info(f"[AGENT] {self.id} ({self.type}) inicializado - Capacidad: {self.capacity}")

    def _compute_pick_time(self, wo) -> float:
        """
        INIT-4 (C1): tiempo de pick, opcionalmente escalado por cantidad/volumen.

        Rama de COMPATIBILIDAD (neutra): si no hay 'base' y los factores son 0,
        devuelve EXACTAMENTE el valor historico (picking_time o discharge_time).
        Esto garantiza el gate byte-identico con configs sin pick_time_model.

        Rama ESCALADA: base + por_unidad*cantidad + por_volumen*volumen, acotado
        por 'minimo'. 'base' en None reutiliza el tiempo historico como base.
        El volumen se calcula sobre cantidad_inicial (estable, independiente del
        estado de picking).
        """
        historico = self.picking_time if self.picking_time is not None else self.discharge_time
        # Compat exacta: sin parametros activos -> comportamiento de hoy.
        if (self.pick_time_base is None
                and self.pick_time_por_unidad == 0.0
                and self.pick_time_por_volumen == 0.0):
            return historico
        base = self.pick_time_base if self.pick_time_base is not None else historico
        cantidad = wo.cantidad_inicial if wo else 0
        volumen = (wo.cantidad_inicial * wo.sku.volumen) if (wo and wo.sku) else 0
        t = base + self.pick_time_por_unidad * cantidad + self.pick_time_por_volumen * volumen
        return max(t, self.pick_time_minimo)

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

    # ------------------------------------------------------------------
    # Iniciativa #2 / Fase 2: arranque escalonado + dispersion espacial
    # (mata F1 = spawn-stacking). TODO gated por congestion.enabled +
    # congestion.staggered_start. Con la capa apagada estos helpers son
    # no-ops y el comportamiento es byte-identico al original.
    # ------------------------------------------------------------------
    def _f2_config(self) -> Dict[str, Any]:
        return getattr(self.almacen, 'congestion_config', {}) or {}

    def _f2_active(self) -> bool:
        """True si el arranque escalonado/dispersion debe aplicarse."""
        if not bool(getattr(self.almacen, 'congestion_enabled', False)):
            return False
        return bool(self._f2_config().get('staggered_start', False))

    def _compute_departure_lanes(self, depot, k):
        """
        BFS cardinal DETERMINISTA desde `depot`. Devuelve hasta `k` celdas caminables
        ordenadas por capa de distancia y, dentro de la capa, por (x,y). candidates[0]
        es siempre el propio depot. Como el orden BFS no depende de k, el agente con
        spawn_index=i recibe SIEMPRE la misma celda candidates[i] (anden distinto por
        agente, determinista, conectado al depot). No muta collision_matrix.
        """
        from collections import deque
        pf = self.pathfinder
        if pf is None:
            return [depot]
        seen = {depot}
        order = [depot]
        q = deque([depot])
        while q and len(order) < k:
            cx, cy = q.popleft()
            # vecinos cardinales en orden lexicografico fijo (determinismo, I5)
            nbrs = sorted([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
            for nx, ny in nbrs:
                if (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                if pf.is_walkable(nx, ny):
                    order.append((nx, ny))
                    q.append((nx, ny))
        return order

    def _spawn_lane(self, depot):
        """
        Dispersion espacial: devuelve el anden de salida de ESTE agente. Si la capa F2
        no esta activa, no hay pathfinder, o es el agente ancla (index 0), devuelve el
        depot intacto (comportamiento original). Si no hay suficientes celdas libres,
        cae al depot (el agente esperara su turno; nunca se congela: regla de oro 4.4).
        """
        if not self._f2_active() or self.spawn_index <= 0 or self.pathfinder is None:
            return depot
        candidates = self._compute_departure_lanes(depot, self.spawn_index + 1)
        if self.spawn_index < len(candidates):
            return candidates[self.spawn_index]
        return depot

    def _spawn_stagger(self):
        """
        Stagger temporal: el agente i espera `spawn_offset * i` antes de su primer
        movimiento, para desincronizar el embudo de salida del depot. Generador SimPy
        (usar con `yield from`). No-op si F2 inactiva o index 0.
        """
        if self._f2_active() and self.spawn_index > 0:
            offset = float(self._f2_config().get('spawn_offset', 0.3))
            if offset > 0:
                yield self.env.timeout(offset * self.spawn_index)

    def _set_pos(self, new_cell):
        """
        Choke point unico para cambiar la posicion del agente (Iniciativa #2).

        Notifica a la capa de ocupacion (CongestionManager) el movimiento celda->celda
        ANTES de actualizar current_position. Si la capa esta inactiva (enabled:false o
        mode:off) NO hace nada salvo el seteo => comportamiento byte-identico al original.

        En Fase 1 (instrument) la capa solo OBSERVA (cuenta co-ocupaciones); no bloquea ni
        emite eventos al replay, asi que el .jsonl no cambia respecto al baseline.
        """
        cm = getattr(self.almacen, 'congestion_manager', None)
        if cm is not None and cm.active:
            cm.move(self.id, self.current_position, new_cell)
        self.current_position = new_cell

    def _claim_spawn(self, cell):
        """
        Fase 3 (cell mode): reservar la celda de spawn para sostener el invariante
        'el agente posee su current_position' (asi el metrico I1 lee 0). No-op si la
        exclusion no esta activa. La dispersion F2 garantiza celdas de spawn distintas.
        """
        cm = getattr(self.almacen, 'congestion_manager', None)
        if cm is not None and getattr(cm, 'cell_exclusion', False):
            cm.claim(self.id, cell)

    def _jump_to(self, dest):
        """
        Fase 3 (cell mode): teletransporte I1-safe que sustituye los `_set_pos` directos
        de los fallbacks (CB19). Suelta la celda actual, salta a `dest` y la reserva, de
        modo que la exclusion se respeta aunque el tramo no se recorra celda a celda
        (caso degenerado: find_path None/corto). Sin exclusion activa equivale a _set_pos.
        """
        cm = getattr(self.almacen, 'congestion_manager', None)
        if cm is not None and getattr(cm, 'cell_exclusion', False):
            prev = self.current_position
            self._set_pos(dest)
            cm.claim(self.id, dest)
            if prev is not None and prev != dest:
                cm.release(self.id, prev)
        else:
            self._set_pos(dest)

    def _timewindow_shadow_plan(self, segment_path, speed, time_per_cell):
        """
        OPCION C (time-window) - modo SOMBRA. Planifica una ruta espacio-temporal
        libre de conflicto para `segment_path` contra la ReservationTable global y la
        RESERVA, registrando metricas (longitud, esperas, expansiones, ms, solapes).
        NO altera el movimiento real (la ejecucion sigue siendo la estatica). Asi se
        mide el coste del planner sobre el layout real sin riesgo de regresion.

        Fase 1: planificacion+reserva real en sombra, delegada al SpaceTimePlanner.
        Es PURO (sin yield / sin env.timeout / sin emision de eventos) => no avanza el
        reloj de SimPy ni toca el replay => .jsonl byte-identico al baseline.
        """
        planner = getattr(self.almacen, 'spacetime_planner', None)
        if planner is None or not segment_path or len(segment_path) < 2:
            return
        try:
            start = segment_path[0]
            goal = segment_path[-1]
            t0 = float(self.env.now)
            planner.plan_and_reserve_shadow(
                start=start, goal=goal, t0=t0, agent_id=self.id,
                speed=speed, static_steps=len(segment_path),
            )
        except Exception as e:
            # El modo sombra JAMAS debe romper la simulacion real (es un observador).
            logger.warning(f"[TIMEWINDOW][SHADOW][WARN] plan fallo para {self.id}: {e}")

    def _tw_exec_active(self) -> bool:
        """MEJ-4: True si el ruteo timewindow esta en EJECUCION (Fase 2, no sombra)."""
        cm = getattr(self.almacen, 'congestion_manager', None)
        return (cm is not None and getattr(cm, 'timewindow_active', False)
                and not bool(getattr(self.almacen, 'timewindow_shadow', True)))

    def _pick_dwell_estimate(self, wo) -> float:
        """
        MEJ-4: duracion estimada de la PERMANENCIA en el punto de picking.
        Base: tiempo de pick (puro, sin RNG). Forklift lo redefine sumando los
        dos movimientos de horquilla. Se usa para el destino-con-permanencia.
        """
        try:
            return float(self._compute_pick_time(wo))
        except Exception:
            return 0.0

    def _tw_reserve_dwell(self, duration):
        """
        MEJ-4 (F1): reservar la PERMANENCIA del agente en su celda actual en la
        ReservationTable, para que los planes de OTROS agentes no atraviesen a un
        operario parado (picking / descarga / lifting). Antes de esto, el planner
        solo modelaba el transito: la estadia era invisible y producia
        co-ocupaciones reales (28 en la corrida canonica, hotspot en staging).

        Sin yields (no toca el reloj de SimPy). No-op si timewindow esta inactivo,
        no hay planner, o la duracion no es positiva. Las reservas propias se
        liberan solas al planificar el siguiente tramo (release_agent) o por purga.
        """
        if not duration or duration <= 0:
            return
        cm = getattr(self.almacen, 'congestion_manager', None)
        planner = getattr(self.almacen, 'spacetime_planner', None)
        if planner is None or cm is None or not getattr(cm, 'timewindow_active', False):
            return
        pos = self.current_position
        if pos is None:
            return
        try:
            planner.reserve_dwell(tuple(pos), float(self.env.now),
                                  float(duration), self.id)
        except Exception as e:
            logger.warning(f"[TIMEWINDOW][DWELL][WARN] {self.id}: reserva de "
                           f"permanencia fallo: {e}")

    def _timewindow_execute_plan(self, segment_path, speed, on_before, on_after,
                                 time_per_cell, goal_dwell=0.0):
        """
        OPCION C (time-window) - Fase 2: EJECUCION segun el plan espacio-temporal.
        Planifica+reserva la ruta libre de conflicto y la SIGUE celda a celda,
        avanzando el reloj de SimPy con env.timeout exacto entre llegadas. Las esperas
        planificadas son pasos con celda REPETIDA (env.timeout en la celda segura): NO
        hay espera reactiva ni adquisicion por cerrojo (la F3 queda jubilada en este
        modo). Emite los mismos eventos que el lazo estatico (on_before tras mover,
        on_after tras el timeout) => el viewer ve el movimiento ordenado.

        Generador SimPy. Devuelve (via StopIteration value) True si EJECUTO el plan,
        False si no habia plan: el llamador cae entonces a la ruta estatica (fallback
        de seguridad 4.2, instrumentado en exec_fallbacks). Nunca congela ni aborta.
        """
        planner = getattr(self.almacen, 'spacetime_planner', None)
        if planner is None or not segment_path or len(segment_path) < 2:
            return False
        start = segment_path[0]
        goal = segment_path[-1]
        t0 = float(self.env.now)
        try:
            plan = planner.plan_and_reserve(
                start, goal, t0, self.id, speed, static_steps=len(segment_path),
                goal_dwell=float(goal_dwell or 0.0))
        except Exception as e:
            logger.warning(f"[TIMEWINDOW][EXEC][WARN] plan fallo para {self.id}: {e}")
            return False
        if not plan or len(plan) < 2:
            try:
                planner.shadow_metrics["exec_fallbacks"] += 1
            except Exception:
                pass
            # MEJ-4 (F2): fallback VISIBLE. La ruta estatica que va a recorrer el
            # llamador se reserva best-effort en la tabla, para que los demas
            # planners puedan esquivar al agente degradado (antes era invisible).
            try:
                dur = float(time_per_cell) * float(speed)
                reservados = planner.reserve_path_best_effort(
                    segment_path, t0, dur, self.id)
                logger.warning(
                    f"[TIMEWINDOW][EXEC][WARN] {self.id}: sin plan para tramo de "
                    f"{len(segment_path)} pasos en t={t0:.1f}; fallback ESTATICO "
                    f"con reserva best-effort ({reservados} intervalos)")
            except Exception:
                pass
            return False

        prev_t = float(plan[0][1])  # = t0; plan[0] == start == posicion actual
        for step_idx, (cell, t) in enumerate(plan[1:], 1):
            dt = float(t) - prev_t
            if dt < 0.0:
                dt = 0.0
            self._set_pos(cell)  # mover (o re-entrar si es espera: cell == actual)
            if on_before is not None:
                on_before(step_idx, cell)
            if dt > 0.0:
                yield self.env.timeout(dt)
            if on_after is not None:
                on_after(step_idx, cell)
            prev_t = float(t)
        return True

    def _recorrer_tramo(self, segment_path, speed, on_before=None, on_after=None,
                        time_per_cell: float = 0.1, goal_dwell: float = 0.0):
        """
        Helper compartido (Ground + Forklift) que recorre un tramo celda a celda.

        Extraido en Iniciativa #2 / Fase 0 para tener UN solo lazo de movimiento donde
        insertar despues la logica de congestion (sin duplicarla en dos agent_process).

        Comportamiento F0 (SIN congestion): identico al lazo original. Por cada celda de
        `segment_path[1:]`:
          1. actualiza self.current_position
          2. ejecuta on_before(step_idx, step_position) si se paso (emite eventos)
          3. yield env.timeout(time_per_cell * speed)
          4. ejecuta on_after(step_idx, step_position) si se paso (prints)

        Args:
            segment_path: lista de celdas [(x,y), ...]; se recorre desde el indice 1.
            speed: multiplicador de velocidad del agente (Ground 1.0, Forklift 0.8).
            on_before: callable(step_idx, step_position) -> None, ejecutado ANTES del timeout.
            on_after: callable(step_idx, step_position) -> None, ejecutado DESPUES del timeout.
            time_per_cell: segundos base por celda (default 0.1).

        Es un generador SimPy: usar con `yield from self._recorrer_tramo(...)`.

        Fase 3 (mode:cell): si la capa de exclusion esta activa, cada paso es ATOMICO:
        se adquiere la celda siguiente ANTES de soltar la actual (anti-F10) y, si esta
        ocupada, se ESPERA (yield release_event | timeout W) y se REINTENTA. Nunca se
        congela ni aborta (regla de oro 4.4). Si la exclusion NO esta activa, el lazo es
        identico al de las fases previas (byte-identico con flag off).
        """
        cm = getattr(self.almacen, 'congestion_manager', None)
        cell_mode = cm is not None and getattr(cm, 'cell_exclusion', False)

        if not cell_mode:
            # --- Rama F0/F1/F2: comportamiento original (sin exclusion) ---
            # OPCION C (timewindow) - injerto gateado: en modo SOMBRA se PLANIFICA y
            # se RESERVA la ruta espacio-temporal y se MIDE el coste, pero la EJECUCION
            # sigue siendo la estatica de abajo (NO se altera el movimiento; el .jsonl
            # no cambia). Fase 0: stub no-op. Fase 1: planificacion real en sombra.
            if cm is not None and getattr(cm, 'timewindow_active', False):
                shadow = bool(getattr(self.almacen, 'timewindow_shadow', True))
                if shadow:
                    # Fase 1: planifica+reserva en SOMBRA; ejecuta estatico abajo.
                    self._timewindow_shadow_plan(segment_path, speed, time_per_cell)
                else:
                    # Fase 2: EJECUTA el plan espacio-temporal (sin espera reactiva).
                    # Si hay plan, recorre y retorna; si no, cae al estatico (fallback).
                    # MEJ-4: goal_dwell = permanencia esperada en el destino, que se
                    # reserva EN el plan (destino-con-permanencia, 3.2/4.6).
                    executed = yield from self._timewindow_execute_plan(
                        segment_path, speed, on_before, on_after, time_per_cell,
                        goal_dwell=goal_dwell)
                    if executed:
                        return
            for step_idx, step_position in enumerate(segment_path[1:], 1):
                self._set_pos(step_position)
                if on_before is not None:
                    on_before(step_idx, step_position)
                yield self.env.timeout(time_per_cell * speed)
                if on_after is not None:
                    on_after(step_idx, step_position)
            return

        # --- Rama F3: paso atomico con exclusion por celda ---
        cfg = self._f2_config()
        W = float(cfg.get('wait_timeout', 0.5))
        hard_cap = float(cfg.get('wait_hard_cap', 30.0))
        for step_idx, step_position in enumerate(segment_path[1:], 1):
            nxt = step_position
            cur = self.current_position
            if nxt == cur:
                # mismo sitio: no hay contencion, solo emitir eventos/timeout.
                if on_before is not None:
                    on_before(step_idx, nxt)
                yield self.env.timeout(time_per_cell * speed)
                if on_after is not None:
                    on_after(step_idx, nxt)
                continue

            # Adquirir la celda SIGUIENTE antes de soltar la ACTUAL (anti-F10).
            # Si esta ocupada: ESPERAR y REINTENTAR. Nunca congelar (regla de oro).
            waited = 0.0
            entered_wait = False
            while not cm.try_acquire(self.id, nxt):
                if not entered_wait:
                    cm.note_wait_episode()
                    entered_wait = True
                rel = cm.release_event(nxt)
                t0 = self.env.now
                yield rel | self.env.timeout(W)
                dt = self.env.now - t0
                waited += dt
                if dt >= W:
                    cm.note_wait_timeout()
                if waited >= hard_cap:
                    # Cota blanda: registrar incidente y SEGUIR esperando en ciclos
                    # acotados. Jamas crash ni abort (I3). La cesion formal es Fase 5.
                    cm.note_hardcap(self.id, nxt)
                    waited = 0.0

            # Celda siguiente adquirida: mover (metrico + posicion) y soltar la anterior.
            self._set_pos(nxt)
            if on_before is not None:
                on_before(step_idx, nxt)
            yield self.env.timeout(time_per_cell * speed)
            if on_after is not None:
                on_after(step_idx, nxt)
            cm.release(self.id, cur)

    def __repr__(self):
        return f"{self.type}({self.id}, cargo={self.cargo_volume}/{self.capacity}, status={self.status})"

    # ====================================================================
    # INICIATIVA #3 / Fase 1.2a - AFORO DE STAGING (mecanica, sin planner aun)
    # Gateado por almacen.outbound_enabled. Con outbound off => no-op =>
    # comportamiento byte-identico al baseline. La reserva de la celda del pallet
    # en la ReservationTable (acople con el planner) es F1.2b.
    # ====================================================================
    def _outbound_wait_slot(self, staging_id, wo):
        """
        Backpressure: cede el reloj (yield) hasta que haya una posicion LIBRE en la
        zona de aforo del staging, la reserva atomicamente (assign provisional) y la
        devuelve. No-op (None) si outbound off o no hay zona. Generador: usar
        `slot = yield from self._outbound_wait_slot(staging_id, wo)`.
        """
        if not getattr(self.almacen, 'outbound_enabled', False):
            return None
        zone = getattr(self.almacen, 'staging_zones', {}).get(staging_id)
        if zone is None:
            return None
        dt = float(self.almacen.outbound_config.get('slot_poll_dt', 0.1))
        waited = 0.0
        slot = zone.free_slot()
        while slot is None:
            yield self.env.timeout(dt)
            waited += dt
            slot = zone.free_slot()
        slot.assign("PENDING:" + str(self.id))  # reserva atomica (sin yield aqui)
        m = getattr(self.almacen, 'outbound_metrics', None)
        if m is not None and waited > 0:
            m['slot_wait_events'] += 1
            m['slot_wait_time'] += waited
            if waited > m['max_slot_wait']:
                m['max_slot_wait'] = waited
        return slot

    def _outbound_place_pallet(self, slot, wo, staging_id):
        """
        Convierte el WO depositado en un Pallet persistente que ocupa `slot`, y
        arranca el SCAFFOLD de release (SOLO Fase 1: proxy del camion, se reemplaza
        por OutboundProcess en Fase 2). No-op si slot None / outbound off.
        """
        if slot is None or not getattr(self.almacen, 'outbound_enabled', False):
            return
        from .outbound import Pallet
        pid = "PALLET:" + str(wo.id)
        vol = wo.cantidad_inicial * wo.sku.volumen if wo.sku else 0
        pallet = Pallet(pid, wo.id, getattr(wo, 'order_id', ''), staging_id,
                        slot.cell, float(self.env.now), vol)
        slot.assign(pid)
        # F1.2b: reservar la celda del pallet como OBSTACULO en la ReservationTable
        # (de ahora hasta que el camion/scaffold lo retire) para que el planner de la
        # Opcion C enrute a los demas agentes ESQUIVANDOLO. No-op si no hay tabla
        # (modo != timewindow). La celda-ancla nunca llega aqui (es SERVICE).
        rt = getattr(self.almacen, 'reservation_table', None)
        if rt is not None:
            try:
                # MINI-FIX reservas (post F1.3): ignorar las reservas del PROPIO
                # gruero que coloca el pallet (su permanencia/dwell en la celda
                # es el pasado inmediato, no un conflicto real). Sin esto, la
                # reserva del pallet fallaba (~180 solapes) y el pallet quedaba
                # INVISIBLE para el ruteo de los demas agentes.
                ok = rt.reserve(slot.cell, float(self.env.now),
                                float(self.env.now) + 1e9, pid,
                                ignore_agents={self.id})
                m_fix = getattr(self.almacen, 'outbound_metrics', None)
                if m_fix is not None:
                    key = 'pallet_reserve_ok' if ok else 'pallet_reserve_fail'
                    m_fix[key] = m_fix.get(key, 0) + 1
            except Exception:
                pass
        m = getattr(self.almacen, 'outbound_metrics', None)
        zone = getattr(self.almacen, 'staging_zones', {}).get(staging_id)
        if m is not None:
            m['pallets_staged'] += 1
            if zone is not None:
                occ = zone.occupancy()
                if occ > m['peak_occupancy'].get(staging_id, 0):
                    m['peak_occupancy'][staging_id] = occ
        # F2.a: registrar pallet en la cola FIFO del camion.
        # La lista se mantiene ordenada por (t_staged, id) para FIFO determinista
        # incluso si dos pallets llegan en el mismo tick de simulacion.
        _staged_list = getattr(self.almacen, 'staged_pallets', None)
        if _staged_list is not None:
            _staged_list.append(pallet)
            _staged_list.sort(key=lambda p: (p.t_staged, p.id))
        # F2.a: scaffold SOLO si policy=='scaffold' (Fase 1 proxy).
        # Con policy='interval', OutboundProcess.run() gestiona el release.
        _policy = self.almacen.outbound_config.get('dispatch_policy', 'scaffold')
        if _policy == 'scaffold':
            dwell = float(self.almacen.outbound_config.get('dwell_scaffold', 10.0))
            self.env.process(self._outbound_scaffold_release(slot, pallet, dwell))

    def _outbound_scaffold_release(self, slot, pallet, dwell):
        """SCAFFOLD Fase 1 (proxy del camion): libera la posicion tras `dwell` seg."""
        yield self.env.timeout(dwell)
        slot.release()
        # F1.2b: liberar la reserva-obstaculo de la celda del pallet (la celda vuelve
        # a estar disponible para el ruteo).
        rt = getattr(self.almacen, 'reservation_table', None)
        if rt is not None:
            try:
                rt.release_agent("PALLET:" + str(pallet.wo_id))
            except Exception:
                pass
        pallet.status = "shipped"
        pallet.t_shipped = float(self.env.now)
        m = getattr(self.almacen, 'outbound_metrics', None)
        if m is not None:
            m['pallets_shipped'] += 1

    def _outbound_nav_to(self, cell):
        """Navega el agente a una celda concreta usando el movimiento normal (en
        timewindow, ruteo que esquiva pallets reservados). Generador. No-op si ya esta."""
        if cell is None or tuple(cell) == tuple(self.current_position):
            return
        rc = getattr(self.almacen, 'route_calculator', None)
        path = None
        if rc is not None and getattr(rc, 'pathfinder', None) is not None:
            try:
                path = rc.pathfinder.find_path(self.current_position, tuple(cell))
            except Exception:
                path = None
        if path and len(path) > 1:
            self.status = "moving"
            # C1: time_per_cell leido de config (self.time_per_cell); default 0.1
            yield from self._recorrer_tramo(
                path, self.default_speed, on_before=None, on_after=None,
                time_per_cell=self.time_per_cell)
        else:
            self._jump_to(tuple(cell))

    def _outbound_discharge_lanes(self, staging_id, staging_wos):
        """
        F1.3 - DESCARGA REALISTA POR CARRILES. Modelo pedido por el Director:
        - Cada staging tiene 2 columnas = 2 carriles; como mucho UN gruero por columna.
        - Si las 2 columnas estan ocupadas por un gruero, los demas ESPERAN FUERA hasta
          que uno salga; entonces entra el siguiente.
        - Los pallets se dejan de ATRAS hacia ADELANTE (celda libre mas al fondo).
        Generador SimPy. Solo se usa con outbound habilitado (gate en el agent_process).
        """
        zone = getattr(self.almacen, 'staging_zones', {}).get(staging_id)
        if zone is None:
            # fallback de seguridad: descarga simple sin aforo
            for wo in staging_wos:
                yield self.env.timeout(self.discharge_time)
                self.cargo_volume -= wo.cantidad_inicial * wo.sku.volumen
                self.almacen.dispatcher.notificar_completado_individual(self, wo)
            return

        dt = float(self.almacen.outbound_config.get('slot_poll_dt', 0.1))
        # 1) ESPERAR FUERA hasta conseguir un carril (columna) libre.
        waited = 0.0
        lane = zone.acquire_lane(self.id)
        while lane is None:
            self.status = "waiting"
            yield self.env.timeout(dt)
            waited += dt
            lane = zone.acquire_lane(self.id)
        if waited > 0:
            mm = getattr(self.almacen, 'outbound_metrics', None)
            if mm is not None:
                mm['slot_wait_events'] += 1
                mm['slot_wait_time'] += waited
                if waited > mm['max_slot_wait']:
                    mm['max_slot_wait'] = waited

        # 2) F2.d: con staging bloqueado para A*, navegar primero al PASILLO de
        # entrada (celda walkable justo delante del carril) via A* normal.
        # El movimiento intra-carril (slot a slot) usara _jump_to (ver abajo).
        _front_col = zone.columns.get(lane, [])
        if _front_col:
            _fc = _front_col[-1].cell   # celda delantera del carril (y menor)
            _entry = (_fc[0], _fc[1] - 1)  # pasillo justo delante (caminable)
            if _entry[1] >= 0:
                yield from self._outbound_nav_to(_entry)

        # 2) Entrar y descargar de ATRAS hacia ADELANTE (un gruero solo en esta columna).
        for wo in staging_wos:
            slot = zone.deepest_empty_cell(lane)
            if slot is None:
                # F2.b: columna llena => esperar dentro del carril (el agente ya
                # esta fisicamente dentro) hasta que el camion/scaffold libere
                # una celda. Sin time-cap: el slot SIEMPRE se libera (scaffold
                # tras dwell_scaffold s; camion tras truck_interval s).
                _lane_wait = 0.0
                self.status = "waiting"
                while slot is None:
                    yield self.env.timeout(dt)
                    _lane_wait += dt
                    slot = zone.deepest_empty_cell(lane)
                _mm = getattr(self.almacen, 'outbound_metrics', None)
                if _mm is not None:
                    _mm['lane_full_wait_events'] = (
                        _mm.get('lane_full_wait_events', 0) + 1)
                    _mm['lane_full_wait_time'] = (
                        _mm.get('lane_full_wait_time', 0.0) + _lane_wait)
            # F2.d: staging bloqueado para A* => saltar directamente al slot.
            # El agente ya esta en el pasillo de entrada (paso anterior).
            # Distancia intra-carril <= zone_capacity/n_columnas celdas: aceptable.
            self._jump_to(slot.cell)
            # F1.3: reservar la celda AL LLEGAR (la mantiene ocupada durante la descarga
            # para que nadie enrute a traves del gruero que descarga). place_pallet luego
            # consolida (Pallet + metricas + scaffold); la reserva duplicada del mismo id
            # es inofensiva (is_free ignora el propio id; release elimina todas).
            slot.assign("PALLET:" + str(wo.id))
            _rt = getattr(self.almacen, 'reservation_table', None)
            if _rt is not None:
                try:
                    # retener la celda con el id del PROPIO agente SOLO durante la
                    # descarga (asi nadie enruta a traves; no choca con la reserva de
                    # movimiento del agente, que comparte id). El pallet (obstaculo
                    # persistente) lo reserva place_pallet despues, ya sin solape.
                    _rt.reserve(slot.cell, float(self.env.now),
                                float(self.env.now) + float(self.discharge_time), self.id)
                except Exception:
                    pass
            self.status = "unloading"
            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id, 'agent_type': self.type,
                'position': self.current_position, 'status': self.status,
                'current_task': wo.id, 'cargo_volume': self.cargo_volume,
            })
            yield self.env.timeout(self.discharge_time)
            self.cargo_volume -= wo.cantidad_inicial * wo.sku.volumen
            self.almacen.dispatcher.notificar_completado_individual(self, wo)
            # crear el Pallet persistente + reservar la celda (obstaculo) + scaffold.
            self._outbound_place_pallet(slot, wo, staging_id)

        # 3) SALIR del staging ANTES de liberar el carril (columna sin gruero al soltar).
        front = zone.columns.get(lane, [])
        if front:
            fcell = front[-1].cell  # celda de FRENTE de la columna (y menor)
            exit_cell = (fcell[0], fcell[1] - 1)  # pasillo justo delante
            yield from self._outbound_nav_to(exit_cell)
        zone.release_lane(lane)

    def _do_picking_at(self, wo):
        """
        Hook de picking en la ubicacion de la WorkOrder.
        GroundOperator: timeout simple. Forklift: lift + pick + lower.
        Generador SimPy; usar con `yield from self._do_picking_at(wo)`.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} debe implementar _do_picking_at")
        yield  # hace que Python trate esto como generador

    def agent_process(self):
        """
        Ciclo pull-based compartido (GroundOperator + Forklift).
        El picking especifico de cada tipo se delega a _do_picking_at().
        """
        # Configuracion de simulacion
        # C1: TIME_PER_CELL leido de config; default 0.1 (escala actual)
        TIME_PER_CELL = self.time_per_cell

        # Inicializar posicion en depot
        staging_locs = self.almacen.data_manager.get_outbound_staging_locations()
        depot_location = staging_locs.get(1, (3, 29))  # Staging 1 como depot default
        # Iniciativa #2 / Fase 2: dispersion espacial (anden distinto por agente).
        spawn_cell = self._spawn_lane(depot_location)
        self._set_pos(spawn_cell)
        # Fase 3 (cell mode): reservar la celda de spawn (invariante de exclusion).
        self._claim_spawn(spawn_cell)

        logger.info(f"[{self.id}] Proceso iniciado en depot {spawn_cell}")

        # Iniciativa #2 / Fase 2: arranque escalonado (stagger temporal).
        yield from self._spawn_stagger()

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
                    logger.info(f"[{self.id}] Simulacion finalizada, saliendo...")
                    break

                yield self.env.timeout(0.5)  # V12: Reduced for fast termination detection
                continue

            # INIT-7 F2: tour de putaway (muelle -> ubicacion), flujo propio.
            if tour.get('tour_type') == 'putaway':
                try:
                    yield from self._execute_putaway_tour(tour)
                except Exception as e:
                    self._abort_tour(tour, e)
                continue

            # MEJ-ROBUSTEZ (auditoria 2026-07-10): tour envuelto -- si algo
            # revienta a mitad de tour, la WO se marca fallida, el agente
            # sobrevive y la corrida termina con degradacion por WO en vez
            # de perderse entera (la excepcion propagaba a env.run()).
            try:
                yield from self._execute_pick_tour(tour, TIME_PER_CELL)
            except Exception as e:
                self._abort_tour(tour, e)

    def _execute_pick_tour(self, tour, TIME_PER_CELL):
        """
        Cuerpo del tour de picks, extraido VERBATIM de agent_process
        (MEJ-ROBUSTEZ, auditoria 2026-07-10) para poder envolverlo en
        try/except: antes una excepcion a mitad de tour reventaba la
        corrida ENTERA via env.run() (se perdia todo el trabajo).
        La extraccion la valida el gate byte-identico.
        """
        tour_start_time = self.env.now

        # PASO 2: Procesar tour asignado
        self.status = "working"
        work_orders = tour['work_orders']
        route_info = tour['route']

        logger.info(f"[{self.id}] t={self.env.now:.1f} Tour asignado: "
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

                logger.debug(f"[{self.id}] t={self.env.now:.1f} Navegando a {wo.ubicacion} "
                      f"(path: {len(segment_path)} pasos)")

                def _on_before(step_idx, step_position):
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
                            'qty_requested': wo.cantidad_inicial,
                            'qty_picked': wo.cantidad_inicial - wo.cantidad_restante,
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

                def _on_after(step_idx, step_position):
                    logger.debug(f"[{self.id}] t={self.env.now:.1f} Paso {step_idx}/{len(segment_path)-1}: {step_position}")

                yield from self._recorrer_tramo(
                    segment_path, self.default_speed,
                    on_before=_on_before, on_after=_on_after,
                    time_per_cell=TIME_PER_CELL,
                    goal_dwell=self._pick_dwell_estimate(wo)
                )
            else:
                self._jump_to(wo.ubicacion)
                self.total_distance_traveled += segment_distance

            yield from self._do_picking_at(wo)
        # PASO 4: Agrupar WOs por staging y descargar en cada uno
        logger.debug(f"[{self.id}] Agrupando WOs por staging para descarga multiple")
        staging_groups = self._agrupar_wos_por_staging(work_orders)
        logger.debug(f"[{self.id}] Tour requiere visitar {len(staging_groups)} stagings: {list(staging_groups.keys())}")

        # Ordenar stagings por distancia desde posicion actual
        ordered_stagings = self._ordenar_stagings_por_distancia(staging_groups, self.current_position)
        staging_locs = self.almacen.data_manager.get_outbound_staging_locations()

        # Visitar cada staging en orden
        for idx, (staging_id, staging_wos) in enumerate(ordered_stagings, 1):
            if getattr(self.almacen, 'outbound_enabled', False):
                # F1.3: descarga realista por carriles (2 por staging, espera fuera,
                # llenado de atras hacia adelante). Reemplaza la descarga clasica.
                yield from self._outbound_discharge_lanes(staging_id, staging_wos)
                continue
            staging_location = staging_locs.get(staging_id, (3, 29))
            # IMPORTANTE: Usar cantidad_inicial * sku.volumen porque cantidad_restante ya es 0 despues del picking
            volumen_staging = sum(wo.cantidad_inicial * wo.sku.volumen for wo in staging_wos)

            logger.debug(f"[{self.id}] [{idx}/{len(ordered_stagings)}] Navegando a staging {staging_id} "
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

                        logger.debug(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                              f"(path: {len(return_path)} pasos)")

                        def _on_before(step_idx, step_position):
                            self.almacen.registrar_evento('estado_agente', {
                                'agent_id': self.id,
                                'agent_type': self.type,
                                'position': self.current_position,
                                'status': self.status,
                                'current_task': None,
                                'cargo_volume': self.cargo_volume
                            })

                        def _on_after(step_idx, step_position):
                            if step_idx % 5 == 0:
                                logger.debug(f"[{self.id}] t={self.env.now:.1f} Navegando a staging {staging_id} "
                                      f"paso {step_idx}/{len(return_path)-1}")

                        yield from self._recorrer_tramo(
                            return_path, self.default_speed,
                            on_before=_on_before, on_after=_on_after,
                            time_per_cell=TIME_PER_CELL,
                            goal_dwell=float(self.discharge_time) * len(staging_wos)
                        )

                        self.total_distance_traveled += len(return_path) - 1
                    else:
                        self._jump_to(staging_location)
                        # F2.d fix: staging no-walkable para A*; regresar al
                        # pasillo (y-1) antes de quedar idle para que el
                        # dispatcher pueda rutar desde una celda transitable.
                        _exit_cell = (staging_location[0], staging_location[1] - 1)
                        if _exit_cell[1] >= 0:
                            self._jump_to(_exit_cell)
                except Exception as e:
                    logger.error(f"[{self.id}] ERROR en pathfinding a staging {staging_id}: {e}")
                    self._jump_to(staging_location)
                    # F2.d fix: staging no-walkable para A*; regresar al
                    # pasillo (y-1) antes de quedar idle para que el
                    # dispatcher pueda rutar desde una celda transitable.
                    _exit_cell = (staging_location[0], staging_location[1] - 1)
                    if _exit_cell[1] >= 0:
                        self._jump_to(_exit_cell)

            # DESCARGAR GRANULAR en este staging (V12: Progreso visible por WO)
            self.status = "unloading"

            self.almacen.registrar_evento('estado_agente', {
                'agent_id': self.id,
                'agent_type': self.type,
                'position': self.current_position,
                'status': self.status,
                'current_task': None,
                'cargo_volume': self.cargo_volume
            })

            logger.debug(f"[{self.id}] t={self.env.now:.1f} Iniciando descarga granular en staging {staging_id} "
                  f"({len(staging_wos)} WOs)")

            # V12 GRANULAR DISCHARGE: Descargar cada WO individualmente
            for wo_idx, wo in enumerate(staging_wos, 1):
                # Calcular volumen de esta WO especifica
                wo_volume = wo.cantidad_inicial * wo.sku.volumen

                # INICIATIVA #3 / F1.2a: backpressure - esperar una posicion
                # libre de la zona de aforo antes de depositar (no-op si off).
                _ob_slot = yield from self._outbound_wait_slot(staging_id, wo)

                # MEJ-4 (F1): reservar la permanencia de la descarga (era la
                # fuga principal: hotspot staging con 4 agentes superpuestos).
                self._tw_reserve_dwell(self.discharge_time)
                # Timeout individual por WO
                yield self.env.timeout(self.discharge_time)

                # Actualizar cargo parcialmente
                self.cargo_volume -= wo_volume

                # Registrar evento de estado actualizado
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id,
                    'cargo_volume': self.cargo_volume
                })

                # Notificar completion individual - esto emite work_order_update con status='staged'
                self.almacen.dispatcher.notificar_completado_individual(self, wo)

                # INICIATIVA #3 / F1.2a: el WO depositado se vuelve un Pallet
                # persistente que ocupa la posicion de aforo (no-op si off).
                self._outbound_place_pallet(_ob_slot, wo, staging_id)

                logger.debug(f"[{self.id}] t={self.env.now:.1f} [{wo_idx}/{len(staging_wos)}] "
                      f"WO {wo.id} staged (-{wo_volume}L, cargo: {self.cargo_volume}L)")

            # MEJ-4 (F3b): con timewindow en EJECUCION, salir del staging al
            # pasillo antes de quedar idle o seguir al proximo staging.
            # Un agente estacionado en la celda de descarga es invisible para
            # la tabla (estadia sin fin conocido) y producia co-ocupaciones
            # con el siguiente que llegaba a descargar. El punto de
            # estacionamiento se DISPERSA por agente (reusa _spawn_lane, BFS
            # determinista) para que los idle no se apilen en la misma celda.
            if self._tw_exec_active():
                _exit_cell = (staging_location[0], staging_location[1] - 1)
                if _exit_cell[1] >= 0:
                    try:
                        _park = tuple(self._spawn_lane(_exit_cell))
                    except Exception:
                        _park = _exit_cell
                    if tuple(self.current_position) != _park:
                        yield from self._outbound_nav_to(_park)

        # PASO 5: Limpiar cargo final (por seguridad)
        self.cargo_volume = 0
        logger.debug(f"[{self.id}] t={self.env.now:.1f} Descarga completa en todos los stagings")

        self.almacen.registrar_evento('estado_agente', {
            'agent_id': self.id,
            'agent_type': self.type,
            'position': self.current_position,
            'status': 'idle',
            'current_task': None,
            'cargo_volume': self.cargo_volume
        })

        # PASO 6: Finalizar tour (ya no usamos notificar_completado batch)
        tour_duration = self.env.now - tour_start_time
        self.almacen.registrar_evento('trip_completed', {
            'agent_id': self.id,
            'data': {
                'duration': tour_duration,
                'num_work_orders': len(work_orders)
            }
        })

        # V12: Usar finalizar_tour en lugar de notificar_completado batch
        self.almacen.dispatcher.finalizar_tour(self)
        self.tasks_completed += len(work_orders)

        logger.info(f"[{self.id}] t={self.env.now:.1f} Tour completado, "
              f"total completadas: {self.tasks_completed}")

    def _abort_tour(self, tour, exc):
        """
        MEJ-ROBUSTEZ (auditoria 2026-07-10): limpieza tras una excepcion a
        mitad de tour (pick o putaway). Sin esto, la excepcion propagaba a
        env.run() y REVENTABA la corrida entera (sin .jsonl, sin Excel).

        Marca fallidas las WOs no completadas del tour (via
        dispatcher.notificar_wo_fallida: cuentan como cerradas => la
        terminacion cierra), resetea la carga y devuelve al agente al ciclo
        idle. Nota: si un pallet inbound ya habia salido del buffer, queda
        perdido con su WO fallida (no bloquea nada; visible en el deficit
        de pallets_stored).
        """
        import traceback
        logger.error(f"[{self.id}] t={self.env.now:.1f} TOUR ABORTADO por "
                     f"excepcion: {exc}")
        logger.error(traceback.format_exc())

        wos = (tour or {}).get('work_orders', []) or []
        fallidas = []
        for wo in wos:
            if getattr(wo, 'status', '') not in ('staged', 'failed'):
                try:
                    self.almacen.dispatcher.notificar_wo_fallida(self, wo)
                    fallidas.append(wo.id)
                except Exception as e2:
                    logger.error(f"[{self.id}] ERROR marcando WO fallida "
                                 f"{getattr(wo, 'id', '?')}: {e2}")

        self.cargo_volume = 0
        self.status = "idle"
        try:
            self.almacen.registrar_evento('agent_tour_crashed', {
                'agent_id': self.id,
                'agent_type': self.type,
                'position': self.current_position,
                'failed_work_orders': fallidas,
                'error': str(exc)[:300],
            })
        except Exception:
            pass
        try:
            self.almacen.dispatcher.finalizar_tour(self)
        except Exception as e3:
            logger.error(f"[{self.id}] ERROR en finalizar_tour tras abort: {e3}")

    # ------------------------------------------------------------------
    # INIT-7 F2: tour de putaway (inverso del pick)
    # ------------------------------------------------------------------

    def _putaway_nav(self, destino, wo, goal_dwell: float = 0.0):
        """Navega al destino con el mismo primitivo del pick (_recorrer_tramo:
        congestion timewindow incluida). Fallback _jump_to si no hay path."""
        destino = tuple(destino)
        if tuple(self.current_position) == destino:
            return
        path = None
        if hasattr(self.almacen, 'route_calculator') and self.almacen.route_calculator:
            try:
                path = self.almacen.route_calculator.pathfinder.find_path(
                    self.current_position, destino)
            except Exception as e:
                logger.error(f"[{self.id}] ERROR pathfinding putaway a {destino}: {e}")
        if path and len(path) > 1:
            self.status = "moving"

            def _on_before(step_idx, step_position):
                self.almacen.registrar_evento('estado_agente', {
                    'agent_id': self.id,
                    'agent_type': self.type,
                    'position': self.current_position,
                    'status': self.status,
                    'current_task': wo.id,
                    'current_work_area': wo.work_area,
                    'cargo_volume': self.cargo_volume
                })

            yield from self._recorrer_tramo(
                path, self.default_speed, on_before=_on_before,
                time_per_cell=self.time_per_cell, goal_dwell=goal_dwell)
            self.total_distance_traveled += len(path) - 1
        else:
            self._jump_to(destino)

    def _execute_putaway_tour(self, tour):
        """
        INIT-7 F2: ciclo de UN putaway (1 pallet por viaje):
        ir al muelle -> cargar el pallet -> ir a la ubicacion destino ->
        depositar -> stock += (registrar_stock_putaway) -> WO completada.
        """
        wo = tour['work_orders'][0]
        tour_start_time = self.env.now
        # F4: distancia recorrida SOLO en este putaway (muelle + destino),
        # para el KPI de distancia de guardado por estrategia de slotting.
        dist_before = self.total_distance_traveled
        load_time = float(getattr(self.almacen, 'inbound_config', {})
                          .get('putaway_load_time', 10.0))

        self.status = "working"
        self.almacen.dispatcher.notificar_inicio_trabajo(self, wo)
        logger.info(f"[{self.id}] t={self.env.now:.1f} Putaway asignado: {wo.id} "
              f"muelle {getattr(wo, 'dock_id', '?')} -> {wo.target_location}")

        # 1. Ir al muelle y cargar el pallet.
        yield from self._putaway_nav(wo.ubicacion, wo, goal_dwell=load_time)
        self.status = "picking"
        self.almacen.registrar_evento('estado_agente', {
            'agent_id': self.id, 'agent_type': self.type,
            'position': self.current_position, 'status': self.status,
            'current_task': wo.id, 'current_work_area': wo.work_area,
            'cargo_volume': self.cargo_volume
        })
        self._tw_reserve_dwell(load_time)
        yield self.env.timeout(load_time)

        pallet = None
        if hasattr(self.almacen, 'tomar_pallet_inbound'):
            pallet = self.almacen.tomar_pallet_inbound(
                getattr(wo, 'pallet_id', None))
        self.cargo_volume += wo.cantidad_inicial * wo.sku.volumen
        self.almacen.registrar_evento('inbound_putaway_started', {
            'pallet_id': getattr(wo, 'pallet_id', None),
            'work_order_id': wo.id,
            'agent_id': self.id,
            'dock_id': getattr(wo, 'dock_id', None),
            'sku_id': wo.sku_id,
            'quantity': wo.cantidad_inicial,
        })

        # 2. Ir a la ubicacion destino y depositar.
        yield from self._putaway_nav(wo.target_location, wo,
                                     goal_dwell=float(self.discharge_time))
        self.status = "unloading"
        self.almacen.registrar_evento('estado_agente', {
            'agent_id': self.id, 'agent_type': self.type,
            'position': self.current_position, 'status': self.status,
            'current_task': wo.id, 'current_work_area': wo.work_area,
            'cargo_volume': self.cargo_volume
        })
        self._tw_reserve_dwell(float(self.discharge_time))
        yield self.env.timeout(float(self.discharge_time))

        self.cargo_volume = max(0, self.cargo_volume
                                - wo.cantidad_inicial * wo.sku.volumen)
        wo.cantidad_restante = 0
        # Stock += en la ubicacion real + dock-to-stock + distancia + evento.
        putaway_distance = self.total_distance_traveled - dist_before
        self.almacen.registrar_stock_putaway(wo, pallet,
                                             distance=putaway_distance)
        # Contabilidad estandar (misma que un pick: contadores + terminacion).
        self.almacen.dispatcher.notificar_completado_individual(self, wo)

        self.almacen.registrar_evento('trip_completed', {
            'agent_id': self.id,
            'data': {
                'duration': self.env.now - tour_start_time,
                'num_work_orders': 1
            }
        })
        self.almacen.dispatcher.finalizar_tour(self)
        self.tasks_completed += 1
        logger.info(f"[{self.id}] t={self.env.now:.1f} Putaway completado: {wo.id} "
              f"({wo.cantidad_inicial}u {wo.sku_id} en {wo.location_id})")


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
        # C1: default_speed leido de config (speed_factor_ground); default 1.0
        self.default_speed = self.speed_factor_ground
        self.preferred_areas = ["Area_Ground", "Area_Piso_L1"]

    def _do_picking_at(self, wo):
        """Secuencia de picking Ground: status -> timeout -> cargo."""
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

        # INIT-4 C1: tiempo de pick (escala con cantidad/volumen si esta activo;
        # neutro -> picking_time o discharge_time, igual que antes).
        picking_duration = self._compute_pick_time(wo)
        # MEJ-4 (F1): la permanencia del picking se reserva en la tabla.
        self._tw_reserve_dwell(picking_duration)
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
            # Fase 2: consume real stock at the picked location
            self.almacen.consumir_stock_picking(wo, self.env.now)
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
                'qty_requested': wo.cantidad_inicial,
                'qty_picked': wo.cantidad_inicial - wo.cantidad_restante,
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
        # C1: default_speed leido de config (speed_factor_forklift); default 0.8.
        # NOTA: default_speed es multiplicador de TIEMPO (0.8 => 20% mas rapido
        # que Ground, no mas lento). El comentario anterior era incorrecto.
        self.default_speed = self.speed_factor_forklift
        self.preferred_areas = ["Area_Rack"]
        self.lift_height = 0  # Current lift height

    def set_lift_height(self, height: int):
        """Set forklift lift height"""
        self.lift_height = height

    def _pick_dwell_estimate(self, wo) -> float:
        """MEJ-4: la permanencia del Forklift incluye subir y bajar la horquilla."""
        base = super()._pick_dwell_estimate(wo)
        return base + 2.0 * float(self.lift_time)

    def _do_picking_at(self, wo):
        """Secuencia de picking Forklift: lift + timeout + lower."""
        LIFT_TIME = self.lift_time
        # MEJ-4 (F1): reservar la permanencia COMPLETA (lift + pick + lower) de
        # una vez. _compute_pick_time es puro (sin RNG): calcularlo aqui no
        # altera el comportamiento.
        _pick_est = self._compute_pick_time(wo)
        self._tw_reserve_dwell(LIFT_TIME + _pick_est + LIFT_TIME)
        self.status = "lifting"
        logger.debug(f"[{self.id}] t={self.env.now:.1f} Elevando horquilla")

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
        logger.debug(f"[{self.id}] t={self.env.now:.1f} Picking en {wo.ubicacion}")

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

        # INIT-4 C1: tiempo de pick (escala con cantidad/volumen si esta activo;
        # neutro -> picking_time o discharge_time, igual que antes).
        picking_duration = self._compute_pick_time(wo)
        yield self.env.timeout(picking_duration)

        logger.debug(f"[{self.id}] t={self.env.now:.1f} Bajando horquilla")
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
            # Fase 2: consume real stock at the picked location
            self.almacen.consumir_stock_picking(wo, self.env.now)
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
                'qty_requested': wo.cantidad_inicial,
                'qty_picked': wo.cantidad_inicial - wo.cantidad_restante,
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
    logger.info("[OPERATORS] Creando operarios desde configuracion...")

    operarios: List[BaseOperator] = []
    procesos_operarios: List[Any] = []

    # Get agent configuration from agent_types array
    agent_types_config = configuracion.get('agent_types', [])

    if not agent_types_config:
        # Fallback: Create default agents from legacy config
        logger.info("[OPERATORS] No agent_types encontrado, usando configuracion legacy...")

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
            operator.spawn_index = len(operarios) - 1  # Iniciativa #2 / Fase 2
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
            forklift.spawn_index = len(operarios) - 1  # Iniciativa #2 / Fase 2
            proceso = env.process(forklift.agent_process())
            procesos_operarios.append(proceso)

    else:
        # Create agents from agent_types configuration
        logger.info(f"[OPERATORS] Creando {len(agent_types_config)} agentes desde agent_types...")

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
                operator.spawn_index = len(operarios) - 1  # Iniciativa #2 / Fase 2
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
                forklift.spawn_index = len(operarios) - 1  # Iniciativa #2 / Fase 2
                proceso = env.process(forklift.agent_process())
                procesos_operarios.append(proceso)

            else:
                logger.warning(f"[OPERATORS WARNING] Tipo de agente desconocido: {agent_type}")

    logger.info(f"[OPERATORS] Creados {len(operarios)} operarios:")
    for operario in operarios:
        logger.info(f"  - {operario.id} ({operario.type}) - Capacidad: {operario.capacity}")

    return procesos_operarios, operarios

# Iniciativa #2 / Fase 1: instrumentacion de congestion via CongestionManager.
