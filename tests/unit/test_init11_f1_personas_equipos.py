# -*- coding: utf-8 -*-
"""
INIT-11 F1: personas y equipos separados.

Cubre la resolucion de la flota (core.fleet), la compatibilidad area-equipo
(core.work_areas), la construccion de operarios con su equipo y la
validacion del configurador web. La equivalencia de extremo a extremo (misma
simulacion con la flota canonica escrita como personas) la corre
`scripts/check_equivalencia_personas.py`.
"""
import copy
import os
import shutil

import simpy

from core.fleet import (capacidad_por_agente, capacidades_por_area,
                        resolver_equipos, resolver_flota, resolver_personas)
from core.config_schema import validate_config_schema
from core.work_areas import effective_work_area_priorities, equipo_sirve
from subsystems.simulation.operators import Forklift, GroundOperator, crear_operarios

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

BASE = {
    "tiempos": {"speed_factor_ground": 1.0, "speed_factor_forklift": 0.8,
                "tiempo_horquilla": 2},
    "work_area_equipment": {"Area_Ground": "GroundOperator",
                            "Area_High": "Forklift",
                            "Area_Special": "grua_trilateral"},
}


def _config(**extra):
    c = copy.deepcopy(BASE)
    c.update(extra)
    return c


EQUIPOS = {
    "transpaleta": {"tipo_base": "GroundOperator"},
    "grua": {"tipo_base": "Forklift", "capacidad": 900, "velocidad": 0.7,
             "horquilla_s": 6, "cantidad": 2},
    "grua_trilateral": {"tipo_base": "Forklift", "capacidad": 800, "cantidad": 1},
}


# ------------------------------------------------------------ modo historico

def test_pe01_modo_historico_lleva_equipo_implicito_con_los_mismos_numeros():
    flota = resolver_flota(_config(num_operarios_terrestres=1, num_montacargas=1))
    ground, fork = flota
    assert ground["id"] == "GroundOp-01" and fork["id"] == "Forklift-01"
    assert ground["persona"] is None
    assert ground["equipo"] == {"id": "GroundOperator", "tipo_base": "GroundOperator",
                                "capacidad": 150, "velocidad": 1.0,
                                "horquilla_s": 2.0, "tiempo_cambio_s": 30.0,
                                "cantidad": None}
    assert fork["equipo"]["velocidad"] == 0.8 and fork["equipo"]["capacidad"] == 1000


def test_pe02_ids_historicos_se_numeran_por_tipo_en_orden():
    tipos = ["GroundOperator", "Forklift", "GroundOperator"]
    flota = resolver_flota(_config(agent_types=[{"type": t} for t in tipos]))
    assert [a["id"] for a in flota] == ["GroundOp-01", "Forklift-01", "GroundOp-02"]


# ------------------------------------------------------------ equipos

def test_pe03_equipo_completa_lo_no_declarado_con_defaults():
    equipos, avisos = resolver_equipos(_config(equipos=EQUIPOS))
    assert avisos == []
    assert equipos["transpaleta"] == {"id": "transpaleta", "tipo_base": "GroundOperator",
                                      "capacidad": 150, "velocidad": 1.0,
                                      "horquilla_s": 2.0, "tiempo_cambio_s": 30.0,
                                      "cantidad": None}
    assert equipos["grua"]["horquilla_s"] == 6.0


def test_pe04_equipo_con_tipo_base_invalido_se_descarta_con_aviso():
    equipos, avisos = resolver_equipos(_config(equipos={"robot": {"tipo_base": "AGV"}}))
    assert equipos == {}
    assert "robot" in avisos[0]


# ------------------------------------------------------------ personas

def test_pe05_grupo_con_nombres_y_numeracion_automatica():
    cfg = _config(equipos=EQUIPOS, personas=[
        {"grupo": "Pickers", "cantidad": 3, "nombres": ["Ana"], "equipo": "transpaleta",
         "work_area_priorities": {"Area_Ground": 1}},
    ])
    flota, avisos = resolver_personas(cfg)
    assert avisos == []
    assert [a["id"] for a in flota] == ["Ana", "Pickers-02", "Pickers-03"]
    assert flota[0]["persona"] == {"id": "Ana", "grupo": "Pickers",
                                   "habilitaciones": ["transpaleta"],
                                   "perfiles": []}  # sin perfiles: F1 puro
    assert flota[0]["type"] == "GroundOperator"


def test_pe06_persona_no_habilitada_no_se_crea():
    cfg = _config(equipos=EQUIPOS, personas=[
        {"grupo": "Nuevos", "equipo": "grua", "habilitaciones": ["transpaleta"]},
    ])
    flota, avisos = resolver_personas(cfg)
    assert flota == []
    assert "no esta habilitado" in avisos[0]


def test_pe07_no_hay_mas_personas_que_unidades_del_equipo():
    cfg = _config(equipos=EQUIPOS, personas=[
        {"grupo": "Grueros", "cantidad": 3, "equipo": "grua"},
    ])
    flota, avisos = resolver_personas(cfg)
    assert [a["id"] for a in flota] == ["Grueros-01", "Grueros-02"]
    assert "No hay unidades de 'grua'" in avisos[0]


def test_pe08_equipo_inexistente_y_nombre_repetido():
    cfg = _config(equipos=EQUIPOS, personas=[
        {"grupo": "X", "equipo": "carro"},
        {"grupo": "A", "nombres": ["Juan"], "equipo": "transpaleta"},
        {"grupo": "B", "nombres": ["Juan"], "equipo": "transpaleta"},
    ])
    flota, avisos = resolver_personas(cfg)
    assert [a["id"] for a in flota] == ["Juan"]
    assert any("'carro'" in a for a in avisos)
    assert any("repetida" in a for a in avisos)


def test_pe09_personas_manda_sobre_agent_types():
    cfg = _config(equipos=EQUIPOS, agent_types=[{"type": "GroundOperator"}] * 5,
                  personas=[{"grupo": "G", "equipo": "grua"}])
    flota = resolver_flota(cfg)
    assert [a["id"] for a in flota] == ["G-01"]
    assert capacidad_por_agente(cfg) == {"G-01": 900}


# ------------------------------------------------------------ areas

def test_pe10_area_acepta_tipo_base_o_equipo_concreto():
    assert equipo_sirve("Forklift", "Forklift", "grua")
    assert equipo_sirve("grua_trilateral", "Forklift", "grua_trilateral")
    assert not equipo_sirve("grua_trilateral", "Forklift", "grua")
    prios = {"Area_High": 1, "Area_Special": 2}
    assert effective_work_area_priorities(BASE, "Forklift", prios,
                                          equipo_id="grua") == {"Area_High": 1}
    assert effective_work_area_priorities(BASE, "Forklift", prios,
                                          equipo_id="grua_trilateral") == prios


def test_pe11_capacidad_por_area_usa_el_equipo_que_el_area_exige():
    cfg = _config(equipos=EQUIPOS, personas=[
        {"grupo": "P", "equipo": "transpaleta", "work_area_priorities": {"Area_Ground": 1}},
        {"grupo": "G", "equipo": "grua", "work_area_priorities": {"Area_High": 1}},
        {"grupo": "T", "equipo": "grua_trilateral",
         "work_area_priorities": {"Area_Special": 1}},
    ])
    capacidades, _ = capacidades_por_area(cfg)
    assert capacidades == {"Area_Ground": 150, "Area_High": 800, "Area_Special": 800}


# ------------------------------------------------------------ operarios

def test_pe12_el_operario_toma_velocidad_horquilla_y_capacidad_del_equipo():
    cfg = _config(equipos=EQUIPOS, personas=[
        {"grupo": "G", "nombres": ["Rosa"], "equipo": "grua",
         "work_area_priorities": {"Area_High": 1}},
        {"grupo": "P", "equipo": "transpaleta",
         "work_area_priorities": {"Area_Ground": 1}},
    ])
    _, operarios = crear_operarios(simpy.Environment(), None, cfg)
    rosa, picker = operarios
    assert isinstance(rosa, Forklift) and isinstance(picker, GroundOperator)
    assert (rosa.id, rosa.capacity, rosa.default_speed, rosa.lift_time) == \
        ("Rosa", 900, 0.7, 6.0)
    assert rosa.equipo_id == "grua" and rosa.persona["grupo"] == "G"
    assert rosa.work_area_priorities == {"Area_High": 1}
    assert picker.default_speed == 1.0 and picker.spawn_index == 1


def test_pe13_operario_historico_conserva_sus_valores():
    cfg = _config(num_operarios_terrestres=0, num_montacargas=1)
    _, (fork,) = crear_operarios(simpy.Environment(), None, cfg)
    assert (fork.id, fork.capacity, fork.default_speed, fork.lift_time) == \
        ("Forklift-01", 1000, 0.8, 2.0)
    assert fork.equipo_id == "Forklift" and fork.persona is None


# ------------------------------------------------------------ esquema y web

def test_pe14_esquema_registra_personas_y_equipos():
    errores, avisos = validate_config_schema(_config(
        equipos={"grua": {"tipo_base": "Forklift", "color": "rojo"}},
        personas=[{"grupo": "G", "equipo": "grua", "turno": 1}]))
    assert errores == []
    assert "clave DESCONOCIDA: 'equipos.grua.color'" in avisos
    assert "clave DESCONOCIDA: 'personas[0].turno'" in avisos
    assert not any("'equipos'" in a or "'personas'" in a for a in avisos)


def _manager(tmp_path):
    from web_prototype.config_manager import WebConfigurationManager
    (tmp_path / "layouts").mkdir()
    # los archivos que nombra el config canonico (cambian al adoptar otro layout)
    for nombre in ['WH1 v3.tmx', 'WH1.tmx', 'Warehouse_Logic.xlsx', 'Warehouse_Logic_v3.xlsx']:
        origen = os.path.join(PROJECT_ROOT, "layouts", nombre)
        if os.path.exists(origen):
            shutil.copy2(origen, tmp_path / "layouts" / nombre)
    return WebConfigurationManager(str(tmp_path))


def _config_web():
    import json
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["equipos"] = {"transpaleta": {"tipo_base": "GroundOperator"},
                      "grua": {"tipo_base": "Forklift", "cantidad": 1}}
    cfg["personas"] = [
        {"grupo": "P", "equipo": "transpaleta", "work_area_priorities": {"Area_Ground": 1}},
        {"grupo": "G", "equipo": "grua",
         "work_area_priorities": {"Area_High": 1, "Area_Special": 2}},
    ]
    return cfg


def test_pe15_web_acepta_una_flota_de_personas_coherente(tmp_path):
    ok, errores = _manager(tmp_path).validate_config(_config_web())
    assert ok, errores


def test_pe16_web_bloquea_personas_incoherentes(tmp_path):
    cfg = _config_web()
    cfg["personas"][1]["cantidad"] = 2          # hay 1 sola grua
    cfg["personas"][0]["work_area_priorities"] = {"Area_High": 1}  # nadie en Ground
    ok, errores = _manager(tmp_path).validate_config(cfg)
    assert not ok
    assert any("No hay unidades de 'grua'" in e for e in errores)
    assert any("'Area_Ground'" in e for e in errores)


def test_pe17_web_acepta_un_equipo_declarado_en_el_mapa_de_areas(tmp_path):
    cfg = _config_web()
    cfg["work_area_equipment"]["Area_Special"] = "grua"
    manager = _manager(tmp_path)
    ok, errores = manager.validate_config(cfg)
    assert ok, errores
    cfg["work_area_equipment"]["Area_Special"] = "dron"
    ok, errores = manager.validate_config(cfg)
    assert any("'dron'" in e for e in errores)
