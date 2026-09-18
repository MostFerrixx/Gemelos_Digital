# -*- coding: utf-8 -*-
"""
BK-15 (QA H-05): la capa anti-colision debe proteger al que esta QUIETO.

Antes, dos agentes podian ocupar la misma celda a la vez (el motor lo contaba:
23 veces por corrida canonica, 373 con pocos SKUs). Causas corregidas:
  C1 la estadia en una ubicacion cubria solo la primera tarea;
  C2 la permanencia no incluia el paso de salida (y el origen se liberaba al
     instante de salir);
  C3 el A* verificaba solo la llegada al destino, no toda la estadia;
  y las reservas que no se podian hacer se omitian EN SILENCIO (el agente
  ejecutaba igual). Mas una tolerancia numerica en los bordes.
"""
from subsystems.simulation.reservation_table import ReservationTable
from subsystems.simulation.spacetime_planner import SpaceTimePlanner


class Pasillo:
    """Grilla 10x3 sin obstaculos, vecinos cardinales."""

    def is_walkable(self, x, y):
        return 0 <= x < 10 and 0 <= y < 3

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, c):
        return [((c[0] + dx, c[1] + dy), 1)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if self.is_walkable(c[0] + dx, c[1] + dy)]


def _planner(clearance=0.05):
    tabla = ReservationTable(clearance)
    return SpaceTimePlanner(Pasillo(), tabla, 0.1, 0.1, 20000, False), tabla


def _ocupa(tabla, celda, t):
    """Agentes con reserva en `celda` en el instante t."""
    return {w for (a, b, w) in tabla.reservations.get(celda, []) if a <= t <= b}


def test_ac01_el_destino_queda_libre_toda_la_estadia():
    """C3: B no llega al destino mientras A se queda ahi, aunque A llegue antes."""
    pl, tabla = _planner()
    pl.plan_and_reserve((0, 0), (5, 0), 0.0, 'A', 1.0, goal_dwell=30.0)
    plan_b = pl.plan_and_reserve((9, 0), (5, 0), 0.0, 'B', 1.0, goal_dwell=5.0)
    llegada_b = plan_b[-1][1]
    assert llegada_b >= 0.5 + 30.0 + 0.1  # despues de la estadia + salida de A


def test_ac02_la_estadia_incluye_el_paso_de_salida():
    """C2: la reserva de la permanencia dura dwell + un paso."""
    pl, tabla = _planner()
    plan = pl.plan_and_reserve((0, 0), (3, 0), 0.0, 'A', 1.0, goal_dwell=10.0)
    llegada = plan[-1][1]
    fin = max(b for (a, b, w) in tabla.reservations[(3, 0)] if w == 'A')
    assert abs(fin - (llegada + 10.0 + 0.1)) < 1e-9


def test_ac03_el_origen_sigue_ocupado_hasta_llegar_al_vecino():
    """C2: mientras se mueve de (0,0) a (1,0), ocupa las dos celdas."""
    pl, tabla = _planner()
    pl.plan_and_reserve((0, 0), (2, 0), 0.0, 'A', 1.0)
    assert 'A' in _ocupa(tabla, (0, 0), 0.09)
    assert 'A' in _ocupa(tabla, (1, 0), 0.05)


def test_ac04_bordes_que_se_tocan_no_son_conflicto():
    """Tolerancia numerica: un intervalo que empieza exactamente donde termina
    otro (+ margen) no choca aunque la aritmetica difiera en 1e-13."""
    tabla = ReservationTable(0.05)
    tabla.reserve((3, 3), 447.56, 447.56 + 0.1, 'A')
    assert tabla.is_free((3, 3), 447.71 - 1e-13, 448.0, ignore_agent='B')
    assert not tabla.is_free((3, 3), 447.60, 448.0, ignore_agent='B')


def test_ac05_un_plan_que_no_se_puede_reservar_entero_se_descarta():
    """Antes el tramo sin reserva se omitia y el agente lo recorria igual."""
    pl, tabla = _planner()
    original = tabla.is_free
    llamadas = {'n': 0}

    def is_free_que_falla_al_reservar(cell, t_in, t_out, ignore_agent=None, ignore_agents=None):
        # El A* ve todo libre; al RESERVAR la segunda celda aparece ocupada.
        import inspect
        if inspect.stack()[1].function == '_reserve_or_skip' and cell == (1, 0):
            llamadas['n'] += 1
            return False
        return original(cell, t_in, t_out, ignore_agent, ignore_agents)

    tabla.is_free = is_free_que_falla_al_reservar
    plan = pl.plan_and_reserve((0, 0), (3, 0), 0.0, 'A', 1.0)
    assert plan is None
    assert llamadas['n'] >= 1
    assert pl.shadow_metrics['plans_rejected_unreservable'] == 1
    assert not any(w == 'A' for ivs in tabla.reservations.values() for (_, _, w) in ivs)


def test_ac06_estadia_en_una_ubicacion_suma_las_tareas_seguidas():
    """C1: tres tareas seguidas en la misma celda y una en otra."""
    from types import SimpleNamespace
    from subsystems.simulation.operators import BaseOperator

    op = object.__new__(BaseOperator)
    op._pick_dwell_estimate_equipo = lambda wo: wo.t
    tareas = [SimpleNamespace(ubicacion=(5, 5), t=10.0),
              SimpleNamespace(ubicacion=(5, 5), t=20.0),
              SimpleNamespace(ubicacion=(5, 5), t=5.0),
              SimpleNamespace(ubicacion=(6, 5), t=7.0)]
    assert op._estadia_en_ubicacion(tareas, 0) == 35.0
    assert op._estadia_en_ubicacion(tareas, 1) == 25.0
    assert op._estadia_en_ubicacion(tareas, 3) == 7.0
