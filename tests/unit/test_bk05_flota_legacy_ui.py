# -*- coding: utf-8 -*-
"""
BK-05: la UI debe poder mostrar y guardar una flota definida en forma LEGACY.

El config.json canonico define la flota con los contadores
(`num_operarios_terrestres` / `num_montacargas`) y deja `agent_types` vacio. La
pestana Flota solo sabe representar `agent_types`, asi que quedaba VACIA y su
panel de cobertura bloqueaba el guardado, aunque el motor corriera perfecto.

El fix materializa la flota en la UI pidiendosela al backend, que la resuelve
con la MISMA funcion que usa el motor (`core.fleet.resolver_flota`, fuente
unica desde BK-06) y devuelve las areas EFECTIVAS (filtradas por
`work_area_equipment`).

Estos tests pinnean el contrato de esa resolucion.
"""
import copy
import json
import os

import pytest

from core.fleet import resolver_flota
from core.work_areas import effective_work_area_priorities
from web_prototype.config_manager import WebConfigurationManager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture(scope="module")
def manager():
    return WebConfigurationManager(PROJECT_ROOT)


@pytest.fixture(scope="module")
def canonico():
    with open(os.path.join(PROJECT_ROOT, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _materializar(config):
    """Replica lo que hace el endpoint /api/configurator/resolve-fleet."""
    flota = resolver_flota(config)
    for agente in flota:
        agente["work_area_priorities"] = effective_work_area_priorities(
            config, agente.get("type"), agente.get("work_area_priorities"))
    return flota


def _config_como_lo_guarda_la_ui(config):
    """El config que serializa la UI tras materializar la flota."""
    salida = copy.deepcopy(config)
    flota = _materializar(config)
    salida["agent_types"] = flota
    salida["num_operarios_terrestres"] = sum(
        1 for a in flota if a["type"] == "GroundOperator")
    salida["num_montacargas"] = sum(1 for a in flota if a["type"] == "Forklift")
    salida["num_operarios_total"] = len(flota)
    return salida


def test_bk05_01_canonico_usa_flota_legacy(canonico):
    """Premisa del bug: el canonico NO lista agentes, solo contadores."""
    assert canonico.get("agent_types") == []
    assert canonico.get("num_operarios_terrestres", 0) > 0
    assert canonico.get("num_montacargas", 0) > 0


def test_bk05_02_materializa_un_agente_por_contador(canonico):
    flota = _materializar(canonico)
    esperados = (canonico["num_operarios_terrestres"] + canonico["num_montacargas"])
    assert len(flota) == esperados
    assert sum(1 for a in flota if a["type"] == "GroundOperator") == \
        canonico["num_operarios_terrestres"]
    assert sum(1 for a in flota if a["type"] == "Forklift") == \
        canonico["num_montacargas"]


def test_bk05_03_capacidades_son_las_del_motor(canonico):
    """La UI no inventa capacidades: usa las que aplicaria el motor."""
    flota = _materializar(canonico)
    ground = [a for a in flota if a["type"] == "GroundOperator"]
    forklift = [a for a in flota if a["type"] == "Forklift"]
    assert all(a["capacity"] == 150 for a in ground)
    assert all(a["capacity"] == 1000 for a in forklift)


def test_bk05_04_devuelve_areas_efectivas_no_declaradas(canonico):
    """BK-06: el mapa manda. La UI no debe prometer areas que el motor ignora.

    El default historico del GroundOperator declara Area_High y Area_Special,
    pero el mapa se las asigna al Forklift: no deben aparecer.
    """
    flota = _materializar(canonico)
    for agente in flota:
        for area in agente["work_area_priorities"]:
            esperado = canonico["work_area_equipment"][area]
            assert agente["type"] == esperado, (
                "%s quedo con el area %s, que corresponde a %s"
                % (agente["type"], area, esperado))


def test_bk05_05_ninguna_area_queda_sin_agente(canonico):
    """Sin esto, el panel de cobertura seguiria bloqueando el guardado."""
    flota = _materializar(canonico)
    cubiertas = set()
    for agente in flota:
        cubiertas.update(agente["work_area_priorities"].keys())
    for area in canonico["work_area_equipment"]:
        assert area in cubiertas, "El area %s quedo sin agente" % area


def test_bk05_06_el_config_de_la_ui_es_guardable(manager, canonico):
    """EL BUG: esto es lo que antes fallaba con 'La flota esta vacia'."""
    ok, errores = manager.validate_config(_config_como_lo_guarda_la_ui(canonico))
    assert ok, "El config que produce la UI no valida: %s" % errores


def test_bk05_07_el_canonico_legacy_siempre_fue_valido(manager, canonico):
    """El bloqueo era del FRONTEND: el backend ya aceptaba la forma legacy."""
    ok, errores = manager.validate_config(canonico)
    assert ok, errores


def test_bk05_08_flota_realmente_vacia_sigue_siendo_invalida(manager, canonico):
    """No se relajo la proteccion: 0 agentes de verdad sigue sin poder guardarse."""
    vacio = copy.deepcopy(canonico)
    vacio["agent_types"] = []
    vacio["num_operarios_terrestres"] = 0
    vacio["num_montacargas"] = 0
    vacio["num_operarios_total"] = 0
    ok, errores = manager.validate_config(vacio)
    assert not ok
    assert any("flota esta vacia" in e.lower() for e in errores), errores


def test_bk05_09_flota_explicita_no_se_toca(canonico):
    """Si el config YA lista agentes, se respetan tal cual (no se re-deriva)."""
    explicito = copy.deepcopy(canonico)
    explicito["agent_types"] = [
        {"type": "Forklift", "capacity": 777, "discharge_time": 9,
         "work_area_priorities": {"Area_High": 1}},
    ]
    flota = _materializar(explicito)
    assert len(flota) == 1
    assert flota[0]["capacity"] == 777
    assert flota[0]["discharge_time"] == 9
