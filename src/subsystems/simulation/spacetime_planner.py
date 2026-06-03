# -*- coding: utf-8 -*-
"""
SpaceTimePlanner - Iniciativa #2 / Opcion C (Time-Window / Reservation Routing)
Digital Twin Warehouse Simulator

A* espacio-temporal (cooperative A* en tiempo continuo). Busca en el espacio
(celda, t_llegada) una ruta cuyas ocupaciones de celda NO se solapen con las
reservas existentes en una ReservationTable. Sucesores: MOVER a un vecino
caminable (consume dur=time_per_cell*speed) o ESPERAR en la celda (consume dt_wait).
Heuristica: distancia octil del Pathfinder (admisible/consistente) REUSADA.

ESTADO: ESQUELETO (Fase 0). Las firmas existen; la logica se implementa en Fase 1.
Reusa `Pathfinder` (is_walkable / get_neighbors / heuristic) y la `ReservationTable`.

Ley #4: ASCII puro en prints/logs.
"""

from typing import List, Tuple, Optional, Any

Cell = Tuple[int, int]
# Un paso de plan: (celda, t_llegada).
PlanStep = Tuple[Cell, float]


class SpaceTimePlanner:
    """
    Planificador A* espacio-temporal sobre una ReservationTable.

    Fase 0: esqueleto. Fase 1: implementacion de `find_path_st` + metricas de coste.
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

    def find_path_st(self, start: Cell, goal: Cell, t0: float, agent_id: str,
                     speed: float = 1.0) -> Optional[List[PlanStep]]:
        """
        Devuelve un plan [(celda, t_llegada), ...] libre de conflicto desde `start`
        en `t0` hasta `goal`, o None si no hay (dentro de max_expansions). Fase 1.
        """
        raise NotImplementedError("SpaceTimePlanner.find_path_st: Fase 1")

    def __repr__(self):
        return (f"SpaceTimePlanner(dt_wait={self.dt_wait}, "
                f"max_expansions={self.max_expansions}, diag={self.allow_diagonal})")
