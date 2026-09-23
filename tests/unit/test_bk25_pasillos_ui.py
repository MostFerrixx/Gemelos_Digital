# -*- coding: utf-8 -*-
"""
BK-25 capas 2 y 3 en la web (decision del Director 2026-09-23: apagadas por
defecto, disponibles para pruebas). La validacion del servidor bloquea una
asignacion de pasillos que no se entiende en vez de descartarla en silencio.
"""
import copy
import json
import os

from web_prototype.config_manager import WebConfigurationManager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _validar(extra):
    cfg = copy.deepcopy(json.load(open(os.path.join(PROJECT_ROOT, 'config.json'), encoding='utf-8')))
    cfg.update(extra)
    return WebConfigurationManager(PROJECT_ROOT).validate_config(cfg)


def test_canonico_sin_bloques_de_pasillos_valida():
    ok, errores = _validar({})
    assert ok, errores


def test_zonas_bien_escritas_validan():
    ok, errores = _validar({'zonas_picking': {'enabled': True, 'robo_de_trabajo': True,
                                              'asignacion': {'GroundOperator': [1, 2, 3, 4]}},
                            'pasillos': {'enabled': True, 'capacidad_default': 2}})
    assert ok, errores


def test_pasillos_que_no_se_entienden_bloquean_con_mensaje():
    ok, errores = _validar({'zonas_picking': {'enabled': True,
                                              'asignacion': {'GroundOperator': 'uno al tres'}}})
    assert not ok
    assert any("GroundOperator" in e and "1-3, 5" in e for e in errores)


def test_cupo_negativo_bloquea():
    ok, errores = _validar({'pasillos': {'enabled': True, 'capacidad_default': -1}})
    assert not ok
    assert any('capacidad_default' in e for e in errores)
