# -*- coding: utf-8 -*-
"""
QA H-27 (BK-25 F0): el que espera ocupa UNA celda.

El planificador reservaba la celda de origen hasta la SALIDA de la celda
siguiente: si el plan esperaba ahi, el agente ocupaba dos celdas durante toda
la espera y se rechazaban planes validos (92-95% de los rechazos en corridas
canonicas). Hallado en la consulta de diseno (docs/PROPUESTA_DISENO_...).
"""
from subsystems.simulation.reservation_table import ReservationTable
from subsystems.simulation.spacetime_planner import SpaceTimePlanner


class Pasillo:
    """Grilla 10x3 libre, vecinos cardinales."""
    def is_walkable(self, x, y):
        return 0 <= x < 10 and 0 <= y < 3

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, c):
        return [((c[0] + dx, c[1] + dy), 1) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if self.is_walkable(c[0] + dx, c[1] + dy)]


def _nuevo():
    tabla = ReservationTable(0.05)
    return tabla, SpaceTimePlanner(Pasillo(), tabla, 0.1, 0.1, 20000, False)


def _reservas(tabla, celda, agente):
    return [(round(a, 3), round(b, 3)) for (a, b, w) in tabla.reservations.get(celda, []) if w == agente]


def test_h27_el_que_espera_no_bloquea_la_celda_de_atras():
    tabla, pl = _nuevo()
    pl.plan_and_reserve((0, 0), (3, 0), 0.0, 'Z', 1.0, goal_dwell=60.0)   # Z descarga 60 s en (3,0)
    tabla.reserve((1, 0), 5.0, 5.1, 'X')                                # X cruza (1,0) en t=5
    plan = pl.plan_and_reserve((1, 0), (3, 0), 0.5, 'Y', 1.0, goal_dwell=5.0)
    assert plan is not None                                            # antes: None (rechazado)
    assert pl.shadow_metrics['plans_rejected_unreservable'] == 0
    assert _reservas(tabla, (1, 0), 'Y') == [(0.5, 0.6)]              # solo el paso de salida


def test_h27_durante_una_espera_el_agente_tiene_una_sola_celda():
    tabla, pl = _nuevo()
    pl.plan_and_reserve((0, 0), (3, 0), 0.0, 'Z', 1.0, goal_dwell=60.0)
    pl.plan_and_reserve((1, 0), (3, 0), 0.5, 'Y', 1.0, goal_dwell=5.0)
    for t in (5.0, 20.0, 50.0):                                        # en plena espera
        celdas = {c for c, ivs in tabla.reservations.items()
                  for (a, b, w) in ivs if w == 'Y' and a <= t <= b}
        assert len(celdas) == 1, (t, celdas)


def test_h27_espera_inicial_explicita_en_el_origen():
    """Si la primera salida se retrasa, el plan espera EN el origen (celda repetida)."""
    tabla, pl = _nuevo()
    tabla.reserve((1, 0), 0.0, 10.0, 'X')     # la unica salida util esta ocupada 10 s
    tabla.reserve((0, 1), 0.0, 10.0, 'X2')
    plan = pl.plan_and_reserve((0, 0), (2, 0), 0.0, 'Y', 1.0)
    assert plan is not None
    assert plan[0][0] == (0, 0) and plan[1][0] == (0, 0)             # espera explicita
    assert plan[1][1] >= 10.0
    assert not any(a < 10.0 for (a, b) in _reservas(tabla, (1, 0), 'Y'))
