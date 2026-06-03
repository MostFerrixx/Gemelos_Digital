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

        # Metricas agregadas del modo SOMBRA (Fase 1). Se vuelcan a un JSON al final.
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

        # open: (f, counter, cell, t). g = t - t0.
        counter = 0
        h0 = self._heuristic_time(start, goal, dur)
        open_heap: List[Tuple[float, int, Cell, float]] = [(h0, counter, start, t0)]
        counter += 1
        # mejor g conocido por estado cuantizado (cell, round(t)).
        best_g: Dict[Tuple[Cell, float], float] = {(start, round(t0, _T_QUANT)): 0.0}
        came_from: Dict[Tuple[Cell, float], Tuple[Cell, float]] = {}

        while open_heap:
            f, _, cell, t = heapq.heappop(open_heap)
            self.last_expansions += 1
            if self.last_expansions > self.max_expansions:
                self.last_capped = True
                return None

            if cell == goal:
                return self._reconstruct(came_from, cell, t, t0)

            tq = round(t, _T_QUANT)
            g_cur = t - t0
            if g_cur > best_g.get((cell, tq), float("inf")) + 1e-12:
                continue  # estado ya superado

            # --- sucesor MOVER ---
            t_next = t + dur
            for nb in self._neighbors(cell):
                if not tbl.is_free(nb, t, t_next, ignore_agent=agent_id):
                    continue
                if not tbl.can_swap(cell, nb, t, t_next, agent_id):
                    continue
                self._relax(open_heap, best_g, came_from, nb, t_next, cell, t,
                            t0, goal, dur)
                counter += 1

            # --- sucesor ESPERAR ---
            t_wait = t + self.dt_wait
            if tbl.is_free(cell, t, t_wait, ignore_agent=agent_id):
                self._relax(open_heap, best_g, came_from, cell, t_wait, cell, t,
                            t0, goal, dur)
                counter += 1

        return None  # open vacio: no alcanzable sin pisar reservas

    def _relax(self, open_heap, best_g, came_from, ncell, nt, pcell, pt,
               t0, goal, dur):
        nq = (ncell, round(nt, _T_QUANT))
        ng = nt - t0
        if ng < best_g.get(nq, float("inf")) - 1e-12:
            best_g[nq] = ng
            came_from[nq] = (pcell, round(pt, _T_QUANT))
            f = ng + self._heuristic_time(ncell, goal, dur)
            # contador implicito via id() no es determinista; usamos longitud del heap.
            heapq.heappush(open_heap, (f, len(open_heap), ncell, nt))

    def _reconstruct(self, came_from, goal_cell, goal_t, t0) -> List[PlanStep]:
        """Reconstruye [(celda, t_llegada), ...] desde start hasta goal."""
        path: List[PlanStep] = [(goal_cell, goal_t)]
        key = (goal_cell, round(goal_t, _T_QUANT))
        # came_from mapea estado-cuantizado -> estado-padre-cuantizado. Para recuperar
        # el t real reconstruimos hacia atras por el t cuantizado (coincide con el real
        # porque dur y dt_wait son fijos => t = t0 + k*paso, sin deriva).
        waits = 0
        while key in came_from:
            pcell, pt_q = came_from[key]
            path.append((pcell, pt_q))
            if pcell == path[-2][0]:
                waits += 1
            key = (pcell, pt_q)
        path.reverse()
        self.last_waits = waits
        return path

    # ------------------------------------------------------------------
    # Modo SOMBRA (Fase 1): planifica + reserva + mide, SIN ejecutar
    # ------------------------------------------------------------------
    def plan_and_reserve_shadow(self, start: Cell, goal: Cell, t0: float,
                                agent_id: str, speed: float,
                                static_steps: int = 0) -> Dict[str, Any]:
        """
        Para un tramo: libera las reservas previas del agente (re-planificacion),
        planifica una ruta espacio-temporal, la RESERVA en la tabla (vertices+aristas)
        y actualiza las metricas de sombra. NO altera el movimiento real (la ejecucion
        sigue la ruta estatica). Devuelve un resumen del tramo.

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
            return {"ok": False, "expansions": self.last_expansions,
                    "ms": plan_ms, "capped": self.last_capped}

        m["plans_found"] += 1
        m["total_plan_steps"] += len(plan)
        m["total_waits_inserted"] += self.last_waits

        # Reservar el plan: cada celda entrada ocupa [t_prev, t_cur]; el primer nodo
        # (start) se reserva como permanencia puntual [t0, t0] (la posee al planificar).
        prev_cell, prev_t = plan[0]
        self.table.reserve(prev_cell, prev_t, prev_t, agent_id)
        m["reserve_attempts"] += 1
        for (cell, t) in plan[1:]:
            m["reserve_attempts"] += 1
            ok = self.table.reserve(cell, prev_t, t, agent_id)
            if not ok:
                m["reserve_overlaps"] += 1
            if cell != prev_cell:
                self.table.reserve_move(prev_cell, cell, prev_t, t, agent_id)
            prev_cell, prev_t = cell, t

        return {"ok": True, "steps": len(plan), "waits": self.last_waits,
                "expansions": self.last_expansions, "ms": plan_ms,
                "t_start": t0, "t_end": plan[-1][1]}

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
