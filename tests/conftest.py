# -*- coding: utf-8 -*-
"""
MEJ-1: fixtures compartidas de la suite de red de seguridad.

Los tests instancian DispatcherV11 y helpers del motor con stubs livianos
(sin SimPy real, sin I/O), igual que hacen los entry_points con sys.path.
Ver docs/PLAN_MEJORA_1_RED_SEGURIDAD.md (D2/D3).
"""
import os
import sys

import pytest

# Mismo mecanismo que entry_points/run_generate_replay.py: src/ en sys.path
# para que resuelvan `from subsystems...` y `from core...`.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in (PROJECT_ROOT, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


class FakeEnv:
    """Stub minimo de simpy.Environment: solo expone .now (seteable)."""

    def __init__(self, now=0.0):
        self.now = now


class FakeWO:
    """WorkOrder de juguete con los atributos que toca el dispatcher.

    Atributos verificados contra warehouse.py::WorkOrder (2026-07-04):
    priority (default 99), due_time (None), wave_id (None), work_area,
    pick_sequence, ubicacion (tupla), calcular_volumen_restante().
    """

    _seq = 0

    def __init__(self, work_area="Area_Ground", priority=99, due_time=None,
                 wave_id=None, pick_sequence=1, ubicacion=(0, 0), volumen=10):
        FakeWO._seq += 1
        self.id = "WO-%04d" % FakeWO._seq
        self.work_area = work_area
        self.priority = priority
        self.due_time = due_time
        self.wave_id = wave_id
        self.pick_sequence = pick_sequence
        self.ubicacion = ubicacion
        self._volumen = volumen

    def calcular_volumen_restante(self):
        return self._volumen

    def __repr__(self):
        return "<FakeWO %s area=%s prio=%s>" % (self.id, self.work_area, self.priority)


class FakeOperator:
    """Operario de juguete: can_handle_work_area + capacity + current_position."""

    def __init__(self, areas=("Area_Ground",), capacity=150, current_position=(0, 0),
                 operator_id="OP-TEST"):
        self.areas = set(areas)
        self.capacity = capacity
        self.current_position = current_position
        self.operator_id = operator_id

    def can_handle_work_area(self, work_area):
        return work_area in self.areas


@pytest.fixture
def fake_env():
    return FakeEnv(now=0.0)


@pytest.fixture
def base_config():
    """Config minima con los defaults del motor (contrato pinneado por la
    suite; esquema completo en src/core/config_schema.py)."""
    return {
        "dispatch_strategy": "Optimizacion Global",
        "max_wos_por_tour": 20,
        "radio_cercania": 100,
        "radio_expansion_paso": 50,
        "radio_max_expansiones": 5,
        "cercania_tour_mode": "cost",
    }


@pytest.fixture
def make_wo():
    return FakeWO


@pytest.fixture
def make_operator():
    return FakeOperator


@pytest.fixture
def make_dispatcher(fake_env, base_config):
    """Factory de DispatcherV11 con stubs (sin almacen/calculators/data_manager)."""
    from subsystems.simulation.dispatcher import DispatcherV11

    def _make(config_overrides=None, env=None):
        cfg = dict(base_config)
        if config_overrides:
            cfg.update(config_overrides)
        return DispatcherV11(
            env=env or fake_env,
            almacen=None,
            assignment_calculator=None,
            route_calculator=None,
            data_manager=None,
            configuracion=cfg,
        )

    return _make
