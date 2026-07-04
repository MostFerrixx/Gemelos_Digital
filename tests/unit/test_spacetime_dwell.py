# -*- coding: utf-8 -*-
"""
MEJ-4 / TW-xx: el planner espacio-temporal respeta la PERMANENCIA (dwell) y el
fallback best-effort deja huella visible en la tabla.

Usa un pathfinder de juguete (grilla abierta) — sin SimPy, sin TMX.
"""
import math

from subsystems.simulation.reservation_table import ReservationTable
from subsystems.simulation.spacetime_planner import SpaceTimePlanner


class FakeGridPathfinder:
    """Grilla rectangular totalmente caminable."""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def is_walkable(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_neighbors(self, cell):
        x, y = cell
        out = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                out.append(((nx, ny), 1.0))
        return out

    def heuristic(self, a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + (math.sqrt(2) - 1.0) * min(dx, dy)


def _planner(width=10, height=3):
    table = ReservationTable(clearance=0.0)
    planner = SpaceTimePlanner(
        pathfinder=FakeGridPathfinder(width, height),
        reservation_table=table,
        time_per_cell=0.1, dt_wait=0.1,
        max_expansions=20000, allow_diagonal=False,
    )
    return planner, table


def test_tw01_pasillo_libre_sin_esperas():
    planner, table = _planner()
    plan = planner.plan_and_reserve((0, 1), (9, 1), t0=0.0, agent_id="A", speed=1.0)
    assert plan is not None
    assert plan[0] == ((0, 1), 0.0)
    assert plan[-1][0] == (9, 1)
    assert abs(plan[-1][1] - 0.9) < 1e-6  # 9 pasos * 0.1
    assert planner.last_waits == 0
    assert table.overlap_violations == 0


def test_tw02_dwell_bloquea_y_el_plan_rodea():
    planner, table = _planner(width=10, height=3)
    # A esta PARADO pikeando en (5,1) durante [0, 10]
    assert planner.reserve_dwell((5, 1), 0.0, 10.0, "A") is True
    plan = planner.plan_and_reserve((0, 1), (9, 1), t0=0.0, agent_id="B", speed=1.0)
    assert plan is not None
    celdas = [c for (c, _t) in plan]
    # B rodea (hay fila arriba/abajo): jamas pisa la celda del dwell antes de t=10
    for (cell, t) in plan:
        assert not (cell == (5, 1) and t <= 10.0), "el plan pisa el dwell de A"
    assert (5, 1) not in celdas  # con detour barato disponible, la evita
    assert plan[-1][1] <= 1.4    # detour de 2 celdas extra: ~1.1
    assert table.overlap_violations == 0


def test_tw03_pasillo_unico_el_plan_espera():
    planner, table = _planner(width=10, height=1)  # sin detour posible
    assert planner.reserve_dwell((5, 0), 0.0, 2.0, "A") is True
    plan = planner.plan_and_reserve((0, 0), (9, 0), t0=0.0, agent_id="B", speed=1.0)
    assert plan is not None
    assert planner.last_waits > 0  # tuvo que insertar esperas planificadas
    # La ENTRADA a (5,0) (intervalo [t_prev, t]) empieza cuando el dwell libero
    entradas = [(prev_t, t) for ((c, t), (_pc, prev_t))
                in zip(plan[1:], plan[:-1]) if c == (5, 0)]
    assert entradas, "el plan nunca cruza la celda del dwell?"
    for (t_in, _t_out) in entradas:
        assert t_in >= 2.0 - 1e-9
    assert plan[-1][1] >= 2.4  # espero ~1.6 s + 5 pasos restantes
    assert table.overlap_violations == 0


def test_tw06_dwell_largo_no_revienta_expansiones():
    """MEJ-4 salto SIPP: esperar un dwell de 60 s cuesta UN estado, no 600."""
    planner, table = _planner(width=10, height=1)
    assert planner.reserve_dwell((5, 0), 0.0, 60.0, "A") is True
    plan = planner.plan_and_reserve((0, 0), (9, 0), t0=0.0, agent_id="B", speed=1.0)
    assert plan is not None
    assert planner.last_expansions < 500  # antes: >600 esperas encadenadas + vecinos
    entradas = [(prev_t, t) for ((c, t), (_pc, prev_t))
                in zip(plan[1:], plan[:-1]) if c == (5, 0)]
    for (t_in, _t_out) in entradas:
        assert t_in >= 60.0 - 1e-9
    assert plan[-1][1] >= 60.4
    assert table.overlap_violations == 0


def test_tw04_fallback_best_effort_deja_huella():
    planner, table = _planner()
    n = planner.reserve_path_best_effort([(0, 0), (1, 0), (2, 0)],
                                         t0=0.0, dur=0.1, agent_id="A")
    assert n == 2
    # Otro agente ya NO ve libre la celda en ese intervalo
    assert table.is_free((1, 0), 0.0, 0.1, ignore_agent="B") is False
    assert table.overlap_violations == 0


def test_tw05_fallback_omite_conflictos_sin_violar_invariante():
    planner, table = _planner()
    table.reserve((1, 0), 0.0, 0.1, "C")
    n = planner.reserve_path_best_effort([(0, 0), (1, 0), (2, 0)],
                                         t0=0.0, dur=0.1, agent_id="A")
    assert n == 1  # (1,0) estaba tomada por C -> se omite; (2,0) entra
    assert table.overlap_violations == 0  # el invariante NUNCA se contamina
