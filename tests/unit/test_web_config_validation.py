# -*- coding: utf-8 -*-
"""
MEJ-1 / CF-xx: caracterizacion de WebConfigurationManager.validate_config
(la barrera que protege al motor de configs invalidas: BK-04 + QA-1/2/3).

CF-01 usa el config.json y el layouts/Warehouse_Logic.xlsx REALES del repo:
pinea el contrato config <-> layout canonico.
"""
import copy
import json
import os

import pytest

from web_prototype.config_manager import WebConfigurationManager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture(scope="module")
def manager():
    return WebConfigurationManager(PROJECT_ROOT)


@pytest.fixture()
def canonical_config():
    with open(os.path.join(PROJECT_ROOT, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _agente(tipo, areas, prioridad_inicial=1):
    return {
        "type": tipo,
        "capacity": 150 if tipo == "GroundOperator" else 1000,
        "discharge_time": 5,
        "work_area_priorities": {a: i + prioridad_inicial for i, a in enumerate(areas)},
    }


def test_cf01_config_canonico_valida_ok(manager, canonical_config):
    ok, errors = manager.validate_config(canonical_config)
    assert ok, "El config.json canonico debe validar. Errores: %s" % errors


def test_cf02_flota_vacia_y_cero_operarios_rechazada(manager, canonical_config):
    cfg = copy.deepcopy(canonical_config)
    cfg["agent_types"] = []
    cfg["num_operarios_terrestres"] = 0
    cfg["num_montacargas"] = 0
    ok, errors = manager.validate_config(cfg)
    assert not ok
    assert any("flota esta vacia" in e for e in errors)


def test_cf03_area_sin_agente_rechazada_nombrando_area(manager, canonical_config):
    cfg = copy.deepcopy(canonical_config)
    # Flota explicita que solo cubre Area_Ground -> Area_High/Area_Special huerfanas
    cfg["agent_types"] = [_agente("GroundOperator", ["Area_Ground"])]
    ok, errors = manager.validate_config(cfg)
    assert not ok
    assert any("Area_High" in e and "ningun agente" in e for e in errors)
    assert any("Area_Special" in e and "ningun agente" in e for e in errors)


def test_cf04_tipo_de_equipo_incorrecto_rechazado(manager, canonical_config):
    cfg = copy.deepcopy(canonical_config)
    # Todas las areas cubiertas, pero Area_High por un GroundOperator (requiere Forklift)
    cfg["agent_types"] = [
        _agente("GroundOperator", ["Area_Ground", "Area_High"]),
        _agente("Forklift", ["Area_Special"]),
    ]
    ok, errors = manager.validate_config(cfg)
    assert not ok
    assert any("Area_High" in e and "tipo" in e and "Forklift" in e for e in errors)


def test_cf05a_radio_cercania_fuera_de_rango(manager, canonical_config):
    cfg = copy.deepcopy(canonical_config)
    cfg["radio_cercania"] = 501
    ok, errors = manager.validate_config(cfg)
    assert not ok
    assert any("radio_cercania" in e for e in errors)


def test_cf05b_waves_release_excede_horizonte(manager, canonical_config):
    cfg = copy.deepcopy(canonical_config)
    cfg["waves"] = {"enabled": True, "release_times": {"1": 0, "2": 2_000_000}}
    ok, errors = manager.validate_config(cfg)
    assert not ok
    assert any("release_times" in e and "max horizon" in e for e in errors)


def test_cf05c_waves_release_negativo(manager, canonical_config):
    cfg = copy.deepcopy(canonical_config)
    cfg["waves"] = {"enabled": True, "release_times": {"1": -5}}
    ok, errors = manager.validate_config(cfg)
    assert not ok
    assert any("must be >= 0" in e for e in errors)


def test_cf06_total_ordenes_invalido(manager, canonical_config):
    cfg = copy.deepcopy(canonical_config)
    cfg["total_ordenes"] = 0
    ok, errors = manager.validate_config(cfg)
    assert not ok
    assert any("total_ordenes" in e for e in errors)
