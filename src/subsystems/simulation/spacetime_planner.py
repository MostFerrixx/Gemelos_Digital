# -*- coding: utf-8 -*-
"""
SpaceTimePlanner - Iniciativa #2 / Opcion C (Time-Window / Reservation Routing)
Digital Twin Warehouse Simulator

A* espacio-temporal (cooperative A* en tiempo continuo). Busca en el espacio
(celda, t_llegada) una ruta cuyas ocupaciones de celda NO se solapen con las
reservas existentes en una ReservationTable. Sucesores de (c, t):
  - MOVER a un vecino caminable c': llegada t' = t + dur (dur = time_per_cell*speed),
    valido si la celda c' esta libre en [t, t'] y no hay swap en la arista c->c'.
  - ESPERAR en c: llegada t' = t + dt_wait, valido si c sigue libre en [t, t'].

Heuristica: distancia geometrica octil del Pathfinder (REUSADA via
`pathfinder.heuristic`) convertida a una COTA INFERIOR de tiempo -> admisible y
consistente (nunca sobreestima el tiempo restante). A* optimo y eficiente.

Modelo de coste MVP (plan 2.4): coste PLANO por paso `time_per_cell*speed`, sin
distinguir diagonal de recto (paridad con la semantica actual). El refinamiento
sqrt(2) en diagonal es una fase posterior.

Determinismo (plan 3.6/4.10): vecinos en orden fijo (Pathfinder.get_neighbors),
tie-break del heap por contador incremental, estados cuantizados por redondeo de t.

Fase 1 (SOMBRA): `plan_and_reserve_shadow` planifica+reserva+mide pero NO ejecuta.
Fase 2 (EJECUCION): `plan_and_reserve` planifica+reserva+mide y DEVUELVE el plan
para que el operario lo siga (la ejecucion sustituye a la ruta estatica). Ambas
comparten el mismo core (`_plan_reserve_core`) => las metricas son identicas.

Ley #4: ASCII puro en prints/logs.
"""

import heapq
import math
from typing import List, Tuple, Optional, Any, Dict

Cell = Tuple[int, int]
# Un paso de plan: (celda, t_llegada).
PlanStep = Tuple[Cell, float]

# Redondeo de t para la cuantizacion de estados (evita deriva de float en el closed-set).
_T_QUANT = 6


class SpaceTimePlanner:
    """
    Planificador A* espacio-temporal sobre una ReservationTable.
    """

    def __init__(self, pathfinder: Any, reservation_table: Any,
                 time_per_cell: float = 0.1,
                 dt_wait: float = 0.1,
                 max_expansions: int = 20000,
                 allow_diagonal: bool = True):
        if pathfinder is None:
            raise ValueError("[SPACETIME-PLANNER ERROR] pathfinder cannot be None")
        if reservation_table is None:
            raise ValueError("[SPACETIME-PLANNER ERROR] reservation_table cannot be None")
        self.pathfinder = pathfinder
        self.table = reservation_table
        self.time_per_cell = float(time_per_cell)
        self.dt_wait = float(dt_wait)
        self.max_expansions = int(max_expansions)
        self.allow_diagonal = bool(allow_diagonal)

        # Stats de la ultima busqueda (para metricas en sombra).
        self.last_expansions = 0
        self.last_capped = False
        self.last_waits = 0

        # Metricas agregadas (Fase 1 sombra Y Fase 2 ejecucion comparten el mismo
        # dict; el campo `exec_segments` distingue cuantos tramos se EJECUTARON).
        self.shadow_metrics: Dict[str, Any] = {
            "segments_planned": 0,
            "plans_found": 0,
            "plans_failed": 0,
            "total_expansions": 0,
            "max_expansions_in_a_plan": 0,
            "expansion_cap_hits": 0,
            "total_plan_ms": 0.0,
            "max_plan_ms": 0.0,
            "total_waits_inserted": 0,
            "total_plan_steps": 0,
            "total_static_steps": 0,
            "reserve_attempts": 0,
            "reserve_overlaps": 0,
            # Fase 2 (ejecucion real segun plan).
            "exec_segments": 0,
            "exec_fallbacks": 0,
            # MEJ-4: permanencias (dwell) y fallback visible.
            "dwell_conflicts": 0,
            "exec_fallback_reserved_steps": 0,
        }

    # ------------------------------------------------------------------
    # Heuristica (cota inferior de tiempo, admisible) - REUSA octil del Pathfinder
    # ------------------------------------------------------------------
    def _dur(self, speed: float) -> float:
        return self.time_per_cell * float(speed)

    def _heuristic_time(self, cell: Cell, goal: Cell, dur: float) -> float:
        """
        Cota inferior del tiempo de `cell` a `goal`. Reusa la distancia octil
        geometrica del Pathfinder y la divide por el MAXIMO avance geometrico por
        paso (sqrt(2) si hay diagonales, 1 si solo cardinales), multiplicado por el
        coste temporal por paso. Como el avance octil real por paso nunca supera ese
        maximo, h <= tiempo real => admisible y consistente.
        """
        d_geo = self.pathfinder.heuristic(cell, goal)  # octil (reuso de codigo)
        max_step_geo = math.sqrt(2) if self.allow_diagonal else 1.0
        return (d_geo / max_step_geo) * dur

    def _neighbors(self, cell: Cell):
        """Vecinos caminables en orden fijo; filtra diagonales si allow_diagonal=False."""
        out = []
        for (nb, _cost) in self.pathfinder.get_neighbors(cell):
            if not self.allow_diagonal:
                dx = abs(nb[0] - cell[0]); dy = abs(nb[1] - cell[1])
                if dx != 0 and dy != 0:
                    continue
            out.append(nb)
        return out

    # ------------------------------------------------------------------
    # A* espacio-temporal
    # ------------------------------------------------------------------
    def find_path_st(self, start: Cell, goal: Cell, t0: float, agent_id: str,
                     speed: float = 1.0) -> Optional[List[PlanStep]]:
        """
        Devuelve un plan [(celda, t_llegada), ...] libre de conflicto desde `start`
        en `t0` hasta `goal`, o None si no se encontro dentro de `max_expansions`.
        Las reservas existentes del PROPIO agente se ignoran (ignore_agent=agent_id).
        """
        self.last_expansions = 0
        self.last_capped = False
        self.last_waits = 0

        if start == goal:
            return [(start, t0)]
        if not self.pathfinder.is_walkable(start[0], start[1]):
            return None
        if not self.pathfinder.is_walkable(goal[0], goal[1]):
            return None

        dur = self._dur(speed)
        tbl = self.table

        # MEJ-4 (SIPP): el estado es (celda, INTERVALO SEGURO), no (celda, t).
        # Dos llegadas a la misma celda dentro del mismo hueco libre son
        # equivalentes (desde la mas temprana se puede esperar hasta la otra):
        # solo se conserva la MAS TEMPRANA. Esto elimina la oscilacion y las
        # cadenas de espera que hacian explotar las expansiones ante dwells
        # largos (descargas de decenas de segundos).
        def _interval_id(cell, t):
            ivs = tbl.reservations.get(cell)
            if not ivs:
                return 0
            cl = tbl.clearance
            n = 0
            for (_e_in, e_out, e_agent) in ivs:
                if e_agent == agent_id:
                    continue
                if e_out + cl <= t:
                    n += 1
            return n

        # open: (f, counter, cell, t). g = t - t0.
        counter = 0
        h0 = self._heuristic_time(start, goal, dur)
        open_heap: List[Tuple[float, int, Cell, float]] = [(h0, counter, start, t0)]
        counter += 1
        # llegada mas temprana conocida por estado SIPP (cell, interval_id).
        arrival: Dict[Tuple[Cell, int], float] = {(start, _interval_id(start, t0)): t0}
        came_from: Dict[Tuple[Cell, int], Tuple[Cell, int, float]] = {}

        def _relax(ncell, nt, pkey, pt):
            nonlocal counter
            nkey = (ncell, _interval_id(ncell, nt))
            if nt < arrival.get(nkey, float("inf")) - 1e-12:
                arrival[nkey] = nt
                came_from[nkey] = (pkey[0], pkey[1], pt)
                f = (nt - t0) + self._heuristic_time(ncell, goal, dur)
                heapq.heappush(open_heap, (f, counter, ncell, nt))
                counter += 1

        while open_heap:
            f, _, cell, t = heapq.heappop(open_heap)
            self.last_expansions += 1
            if self.last_expansions > self.max_expansions:
                self.last_capped = True
                return None

            key = (cell, _interval_id(cell, t))
            if t > arrival.get(key, float("inf")) + 1e-12:
                continue  # estado dominado (llegada mas temprana ya conocida)

            if cell == goal:
                return self._reconstruct(came_from, arrival, key, t, t0, dur)

            # --- sucesor MOVER (con salida retrasada estilo SIPP ante bloqueo) ---
            # No hay sucesor generico de "esperar": si el movimiento a un vecino
            # esta bloqueado, se genera EL MISMO movimiento con salida retrasada
            # al primer instante util (earliest_free), siempre que la celda
            # actual siga libre mientras tanto. La espera queda implicita en el
            # delta de tiempos del plan (el ejecutor hace timeout largo y la
            # reserva cubre la permanencia en la celda de espera).
            t_next = t + dur
            for nb in self._neighbors(cell):
                free_ok = tbl.is_free(nb, t, t_next, ignore_agent=agent_id)
                swap_ok = tbl.can_swap(cell, nb, t, t_next, agent_id)
                if free_ok and swap_ok:
                    _relax(nb, t_next, key, t)
                    continue
                if not free_ok:
                    # vertice ocupado (dwell/transito ajeno): saltar al primer hueco
                    try:
                        t_free = tbl.earliest_free(nb, t, dur, ignore_agent=agent_id)
                    except Exception:
                        t_free = None
                else:
                    # solo conflicto de cruce (arista inversa): reintento corto,
                    # los cruces duran <= un paso (dur)
                    t_free = t + self.dt_wait
                if (t_free is not None and t_free > t
                        and tbl.is_free(cell, t, t_free, ignore_agent=agent_id)
                        and tbl.is_free(nb, t_free, t_free + dur, ignore_agent=agent_id)
                        and tbl.can_swap(cell, nb, t_free, t_free + dur, agent_id)):
                    # movimiento retrasado: esperar en `cell` hasta t_free y entrar
                    _relax(nb, t_free + dur, key, t_free)

        return None  # open vacio: no alcanzable sin pisar reservas

    def _reconstruct(self, came_from, arrival, goal_key, goal_t, t0,
                     dur) -> List[PlanStep]:
        """
        Reconstruye [(celda, t_llegada), ...] desde start hasta goal (claves SIPP).
        Las ESPERAS son implicitas: un delta entre pasos mayor que `dur` significa
        que el agente espero en la celda anterior (asi se cuentan en last_waits).
        """
        path: List[PlanStep] = [(goal_key[0], round(goal_t, _T_QUANT))]
        key = goal_key
        while key in came_from:
            pcell, p_iid, pt = came_from[key]
            path.append((pcell, round(pt, _T_QUANT)))
            key = (pcell, p_iid)
        path.reverse()
        # Anclar el primer paso a t0: si la PRIMERA salida fue retrasada, la
        # espera inicial queda dentro del primer delta (el ejecutor hara el
        # timeout largo y la reserva cubrira la permanencia en el origen).
        path[0] = (path[0][0], round(float(t0), _T_QUANT))
        waits = 0
        for i in range(1, len(path)):
            if (path[i][1] - path[i - 1][1]) > dur + 1e-9:
                waits += 1
        self.last_waits = waits
        return path

    # ------------------------------------------------------------------
    # Core compartido: planifica + reserva + mide (sombra Y ejecucion).
    # ------------------------------------------------------------------
    def _plan_reserve_core(self, start: Cell, goal: Cell, t0: float,
                           agent_id: str, speed: float,
                           static_steps: int = 0) -> Optional[List[PlanStep]]:
        """
        Para un tramo: libera las reservas previas del agente (re-planificacion),
        planifica una ruta espacio-temporal, la RESERVA en la tabla (vertices+aristas)
        y actualiza las metricas. Devuelve el PLAN [(celda, t), ...] o None.

        El `release_agent` previo evita que el agente choque con su propio plan anterior
        y mantiene la tabla acotada (~1 plan por agente activo).
        """
        import time as _time
        m = self.shadow_metrics
        m["segments_planned"] += 1
        m["total_static_steps"] += int(static_steps)

        # Re-planificacion: soltar reservas futuras propias y purgar pasado.
        self.table.release_agent(agent_id)
        self.table.purge_before(t0 - 1.0)

        t_start = _time.perf_counter()
        plan = self.find_path_st(start, goal, t0, agent_id, speed)
        plan_ms = (_time.perf_counter() - t_start) * 1000.0

        m["total_expansions"] += self.last_expansions
        m["max_expansions_in_a_plan"] = max(m["max_expansions_in_a_plan"],
                                            self.last_expansions)
        m["total_plan_ms"] += plan_ms
        m["max_plan_ms"] = max(m["max_plan_ms"], plan_ms)
        if self.last_capped:
            m["expansion_cap_hits"] += 1

        if plan is None:
            m["plans_failed"] += 1
            return None

        m["plans_found"] += 1
        m["total_plan_steps"] += len(plan)
        m["total_waits_inserted"] += self.last_waits

        # Reservar el plan: cada celda entrada ocupa [t_prev, t_cur]; el primer nodo
        # (start) se reserva como permanencia puntual [t0, t0] (la posee al planificar).
        # MEJ-4: insercion con PRE-CHEQUEO (is_free). Los bordes cuantizados (round
        # a 6 decimales) + clearance pueden voltear una comparacion de frontera que
        # el A* valido con los t sin redondear: en ese caso se OMITE el intervalo y
        # se cuenta en reserve_overlaps (metrica del planner), sin contaminar
        # table.overlap_violations, que queda reservado para bugs de construccion.
        def _reserve_or_skip(cell, t_in, t_out):
            m["reserve_attempts"] += 1
            if self.table.is_free(cell, t_in, t_out, ignore_agent=agent_id):
                self.table.reserve(cell, t_in, t_out, agent_id)
                return True
            m["reserve_overlaps"] += 1
            return False

        prev_cell, prev_t = plan[0]
        _reserve_or_skip(prev_cell, prev_t, prev_t)
        for (cell, t) in plan[1:]:
            if _reserve_or_skip(cell, prev_t, t) and cell != prev_cell:
                self.table.reserve_move(prev_cell, cell, prev_t, t, agent_id)
            prev_cell, prev_t = cell, t

        return plan

    def reserve_path_best_effort(self, path: List[Cell], t0: float, dur: float,
                                 agent_id: str) -> int:
        """
        MEJ-4 (F2): reserva BEST-EFFORT de una ruta ESTATICA (fallback sin plan).
        Cuando el A* espacio-temporal no encuentra plan, el operario recorre la
        ruta estatica igualmente (regla de oro: nunca congelar). Antes ese
        recorrido era INVISIBLE para los demas planners. Aqui se insertan los
        intervalos [t, t+dur] por celda que NO pisen reservas ajenas (los que
        pisan se omiten: is_free previo evita contaminar overlap_violations,
        cuyo invariante DEBE seguir en 0). Devuelve cuantos intervalos entraron.
        """
        if not path or len(path) < 2 or dur <= 0:
            return 0
        inserted = 0
        prev = path[0]
        t = float(t0)
        for cell in path[1:]:
            t_next = t + float(dur)
            if self.table.is_free(cell, t, t_next, ignore_agent=agent_id):
                self.table.reserve(cell, t, t_next, agent_id)
                inserted += 1
                if cell != prev:
                    self.table.reserve_move(prev, cell, t, t_next, agent_id)
            prev, t = cell, t_next
        self.shadow_metrics["exec_fallback_reserved_steps"] = (
            self.shadow_metrics.get("exec_fallback_reserved_steps", 0) + inserted)
        return inserted

    def reserve_dwell(self, cell: Cell, t_in: float, dwell: float,
                      agent_id: str) -> bool:
        """
        Fase 2: reserva la PERMANENCIA de un agente en `cell` durante [t_in, t_in+dwell]
        (picking / descarga / lifting). Sin esto, otro agente podria planificar una ruta
        que cruce la celda donde este agente esta fisicamente parado => co-ocupacion (I1).
        Modela el destino-con-permanencia del plan (3.2 / 4.6) de forma uniforme.

        MEJ-4: BEST-EFFORT con pre-chequeo. Si el intervalo pisa una reserva ajena
        (tipico: un plan COMMITTED antes de que existiera este dwell), NO se inserta
        y se cuenta en `dwell_conflicts` — sin contaminar `overlap_violations` de la
        tabla, cuyo invariante (0 por construccion del A*) debe seguir limpio.
        """
        if dwell <= 0.0:
            return True
        t_out = float(t_in) + float(dwell)
        if not self.table.is_free(cell, t_in, t_out, ignore_agent=agent_id):
            self.shadow_metrics["dwell_conflicts"] = (
                self.shadow_metrics.get("dwell_conflicts", 0) + 1)
            return False
        return self.table.reserve(cell, t_in, t_out, agent_id)

    # ------------------------------------------------------------------
    # Fase 1 (SOMBRA): planifica + reserva + mide, SIN ejecutar.
    # ------------------------------------------------------------------
    def plan_and_reserve_shadow(self, start: Cell, goal: Cell, t0: float,
                                agent_id: str, speed: float,
                                static_steps: int = 0) -> Dict[str, Any]:
        """
        Modo SOMBRA: planifica+reserva+mide pero NO altera el movimiento (la ejecucion
        sigue la ruta estatica). Devuelve un resumen del tramo (no se ejecuta).
        Comparte el core con la ejecucion => metricas identicas a Fase 1.
        """
        plan = self._plan_reserve_core(start, goal, t0, agent_id, speed, static_steps)
        if plan is None:
            return {"ok": False, "expansions": self.last_expansions,
                    "capped": self.last_capped}
        return {"ok": True, "steps": len(plan), "waits": self.last_waits,
                "expansions": self.last_expansions,
                "t_start": t0, "t_end": plan[-1][1]}

    # ------------------------------------------------------------------
    # Fase 2 (EJECUCION): planifica + reserva + mide y DEVUELVE el plan.
    # ------------------------------------------------------------------
    def plan_and_reserve(self, start: Cell, goal: Cell, t0: float,
                         agent_id: str, speed: float,
                         static_steps: int = 0,
                         goal_dwell: float = 0.0) -> Optional[List[PlanStep]]:
        """
        Modo EJECUCION (Fase 2): igual que el core, pero devuelve el PLAN para que el
        operario lo SIGA (la ejecucion sustituye a la ruta estatica). El reloj de SimPy
        avanza segun los t_llegada del plan; las esperas son pasos explicitos (celda
        repetida) ya reservados => sin espera reactiva.

        MEJ-4 (destino-con-permanencia, plan 3.2/4.6): si `goal_dwell` > 0, ademas
        del transito se reserva la PERMANENCIA en el destino [t_llegada,
        t_llegada+goal_dwell] EN EL MOMENTO DE PLANIFICAR (no al llegar). Asi los
        demas agentes ven la estadia ANTES de comprometer sus propios planes, y
        las llegadas al mismo destino (p.ej. staging) se serializan solas: el A*
        del siguiente inserta esperas hasta que el dwell libere.
        """
        plan = self._plan_reserve_core(start, goal, t0, agent_id, speed, static_steps)
        if plan is not None:
            self.shadow_metrics["exec_segments"] += 1
            if goal_dwell and goal_dwell > 0.0:
                g_cell, g_t = plan[-1]
                self.reserve_dwell(g_cell, float(g_t), float(goal_dwell), agent_id)
        return plan

    def shadow_report(self) -> Dict[str, Any]:
        """Resumen agregado para volcar a JSON (metricas de coste y validacion)."""
        m = dict(self.shadow_metrics)
        pf = m["plans_found"] or 1
        seg = m["segments_planned"] or 1
        m["avg_plan_ms"] = round(m["total_plan_ms"] / seg, 4)
        m["avg_expansions"] = round(m["total_expansions"] / seg, 2)
        m["avg_plan_steps"] = round(m["total_plan_steps"] / pf, 2)
        m["avg_waits_per_plan"] = round(m["total_waits_inserted"] / pf, 3)
        m["table_overlap_violations"] = self.table.overlap_violations
        m["table_reserve_calls"] = self.table.reserve_calls
        m["clearance"] = self.table.clearance
        m["dt_wait"] = self.dt_wait
        m["max_expansions"] = self.max_expansions
        m["allow_diagonal"] = self.allow_diagonal
        return m

    def __repr__(self):
        return (f"SpaceTimePlanner(dt_wait={self.dt_wait}, "
                f"max_expansions={self.max_expansions}, diag={self.allow_diagonal})")
