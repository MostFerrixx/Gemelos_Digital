# -*- coding: utf-8 -*-
"""
MEJ-3 / SC-xx: contrato del esquema unico de configuracion
(core/config_schema.py): claves desconocidas -> warning, legacy -> warning
"sin efecto", tipos invalidos -> error, canonico -> limpio.
"""
import copy
import json
import os

from core.config_schema import validate_config_schema

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _canonical():
    with open(os.path.join(PROJECT_ROOT, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def test_sc01_config_canonico_limpio():
    errors, warnings = validate_config_schema(_canonical())
    assert errors == [], errors
    assert warnings == [], warnings


def test_sc02_typo_en_flag_detectado():
    cfg = _canonical()
    cfg["priority_dispatch_enable"] = True  # typo: falta la 'd'
    errors, warnings = validate_config_schema(cfg)
    assert errors == []
    assert any("priority_dispatch_enable" in w and "DESCONOCIDA" in w
               for w in warnings)


def test_sc03_clave_legacy_avisada_como_sin_efecto():
    cfg = _canonical()
    cfg["tareas_zona_a"] = 0
    cfg["capacidad_carro"] = 150
    errors, warnings = validate_config_schema(cfg)
    assert errors == []
    assert any("tareas_zona_a" in w and "LEGACY" in w for w in warnings)
    assert any("capacidad_carro" in w and "LEGACY" in w for w in warnings)


def test_sc04_clave_legacy_f3_en_congestion():
    cfg = _canonical()
    cfg["congestion"]["wait_timeout"] = 0.5
    errors, warnings = validate_config_schema(cfg)
    assert errors == []
    assert any("congestion.wait_timeout" in w and "LEGACY" in w for w in warnings)


def test_sc05_clave_desconocida_anidada():
    cfg = _canonical()
    cfg["congestion"]["timewindow"]["sombra"] = True  # typo de 'shadow'
    errors, warnings = validate_config_schema(cfg)
    assert errors == []
    assert any("congestion.timewindow.sombra" in w for w in warnings)


def test_sc06_tipo_invalido_es_error():
    cfg = _canonical()
    cfg["total_ordenes"] = "trescientos"
    errors, warnings = validate_config_schema(cfg)
    assert any("total_ordenes" in e for e in errors)


def test_sc07_release_times_no_numerico_es_error():
    cfg = _canonical()
    cfg["waves"] = {"enabled": True, "release_times": {"1": "abc"}}
    errors, warnings = validate_config_schema(cfg)
    assert any("release_times" in e for e in errors)


def test_sc08_no_muta_la_config():
    cfg = _canonical()
    cfg["clave_rara"] = {"x": 1}
    antes = copy.deepcopy(cfg)
    validate_config_schema(cfg)
    assert cfg == antes


def test_sc09_config_no_dict():
    errors, warnings = validate_config_schema("no soy un dict")
    assert errors and warnings == []
