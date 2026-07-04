# -*- coding: utf-8 -*-
"""
MEJ-1 / AL-xx: caracterizacion de la Allocation Layer V12.1 (order_strategies).

_coerce_int/_coerce_float (parsing defensivo de priority/due_time) y
_allocate_across_locations (asignacion FCFS multi-ubicacion con mutacion de
qty_free y area preferida).
"""
import pytest

from subsystems.simulation.order_strategies import (
    DeterministicOrderStrategy,
    _coerce_float,
    _coerce_int,
)


# ---------- AL-01: coerciones defensivas ----------

@pytest.mark.parametrize("valor,esperado", [
    (None, None),
    ("", None),
    ("5", 5),
    (5, 5),
    (5.9, 5),          # int() trunca
    ("-3", -3),
    ("abc", None),
    ("5.5", None),     # int("5.5") -> ValueError -> None
    ([], None),
])
def test_al01_coerce_int(valor, esperado):
    assert _coerce_int(valor) == esperado


@pytest.mark.parametrize("valor,esperado", [
    (None, None),
    ("", None),
    ("5.5", 5.5),
    (3, 3.0),
    ("-1.25", -1.25),
    ("abc", None),
    ({}, None),
])
def test_al01_coerce_float(valor, esperado):
    assert _coerce_float(valor) == esperado


# ---------- AL-02..05: _allocate_across_locations ----------

def _strategy():
    # Sin __init__ (que exige file_path y lee disco): el metodo bajo prueba
    # no usa estado de instancia.
    return object.__new__(DeterministicOrderStrategy)


def _loc(location_id, qty_free, work_area="Area_Ground"):
    return {"location_id": location_id, "qty_free": qty_free, "work_area": work_area}


def test_al02_stock_exacto_en_una_ubicacion():
    locs = [_loc("L1", 10)]
    allocations, taken = _strategy()._allocate_across_locations(locs, requested=10)
    assert taken == 10
    assert allocations == [(locs[0], 10)]
    assert locs[0]["qty_free"] == 0  # mutacion in place (FCFS entre pedidos)


def test_al03_split_entre_ubicaciones_en_orden():
    locs = [_loc("L1", 4), _loc("L2", 4), _loc("L3", 50)]
    allocations, taken = _strategy()._allocate_across_locations(locs, requested=10)
    assert taken == 10
    assert [(l["location_id"], q) for l, q in allocations] == [("L1", 4), ("L2", 4), ("L3", 2)]
    assert locs[2]["qty_free"] == 48


def test_al04_stock_insuficiente_asignacion_parcial():
    locs = [_loc("L1", 3)]
    allocations, taken = _strategy()._allocate_across_locations(locs, requested=10)
    assert taken == 3  # parcial: el resto es backorder (ship_partial)
    assert allocations == [(locs[0], 3)]


def test_al05_stock_cero_sin_asignaciones():
    locs = [_loc("L1", 0)]
    allocations, taken = _strategy()._allocate_across_locations(locs, requested=5)
    assert taken == 0
    assert allocations == []


def test_al06_area_preferida_primero_con_fallback():
    locs = [_loc("L1", 5, work_area="Area_High"),
            _loc("L2", 5, work_area="Area_Ground"),
            _loc("L3", 5, work_area="Area_High")]
    allocations, taken = _strategy()._allocate_across_locations(
        locs, requested=8, preferred_area="Area_Ground")
    assert taken == 8
    # Primero agota la preferida (L2), luego cae al resto en orden (L1)
    assert [(l["location_id"], q) for l, q in allocations] == [("L2", 5), ("L1", 3)]
