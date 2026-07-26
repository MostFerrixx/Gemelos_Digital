# -*- coding: utf-8 -*-
"""
BK-06: capacidad por area vs. flota heterogenea.

Pinnea las tres invariantes del fix (ver docs/PLAN_BK06_CAPACIDAD_AREA.md):

  (a) un area servida por un solo tipo dimensiona por la capacidad de ESE tipo;
  (b) un agente nunca queda habilitado en un area que el mapa asigna a otro tipo;
  (c) ninguna WO generada puede ser irrecogible por un agente compatible con su
      area (la red de seguridad del minimo).
"""
import pytest

from core.fleet import (HISTORIC_FLEET_DEFAULTS, capacidades_por_area,
                        capacidades_por_tipo, resolver_flota)
from core.work_areas import (effective_work_area_priorities,
                             expected_equipment_for_area)
from subsystems.simulation.warehouse import SKU, AlmacenMejorado


CANONICO = {
    "agent_types": [],
    "num_operarios_terrestres": 2,
    "num_montacargas": 2,
    "work_area_equipment": {
        "Area_Ground": "GroundOperator",
        "Area_High": "Forklift",
        "Area_Special": "Forklift",
    },
}


# --------------------------------------------------------------- work_areas

def test_bk06_01_mapa_manda_sobre_convencion():
    """El mapa explicito gana; la convencion de nombres es solo fallback."""
    cfg = {"work_area_equipment": {"Area_Ground": "Forklift"}}
    assert expected_equipment_for_area(cfg, "Area_Ground") == "Forklift"
    # Sin mapa, cae a la convencion historica (nombre "ground" -> terrestre).
    assert expected_equipment_for_area({}, "Area_Ground") == "GroundOperator"
    assert expected_equipment_for_area({}, "Area_High") == "Forklift"


def test_bk06_02_ground_no_queda_habilitado_en_area_de_forklift():
    """(b) La causa raiz: el ground se declaraba apto para Area_High."""
    declaradas = {"Area_Ground": 1, "Area_High": 2, "Area_Special": 3}
    efectivas = effective_work_area_priorities(
        CANONICO, "GroundOperator", declaradas, agent_id="GroundOp-01")
    assert efectivas == {"Area_Ground": 1}
    assert "Area_High" not in efectivas
    assert "Area_Special" not in efectivas


def test_bk06_03_forklift_conserva_sus_areas():
    efectivas = effective_work_area_priorities(
        CANONICO, "Forklift", {"Area_High": 1, "Area_Special": 2})
    assert efectivas == {"Area_High": 1, "Area_Special": 2}


def test_bk06_04_prioridades_declaradas_se_conservan_para_diagnostico():
    """El filtrado no debe borrar la info: se avisa, no se oculta."""
    declaradas = {"Area_Ground": 1, "Area_High": 2}
    efectivas = effective_work_area_priorities(CANONICO, "GroundOperator", declaradas)
    assert declaradas == {"Area_Ground": 1, "Area_High": 2}  # no mutado
    assert efectivas == {"Area_Ground": 1}


# -------------------------------------------------------------------- fleet

def test_bk06_05_flota_canonica_desde_contadores_legacy():
    """El canonico tiene agent_types vacio: la flota sale de los contadores."""
    flota = resolver_flota(CANONICO)
    assert len(flota) == 4
    # Orden historico: primero los terrestres, despues los montacargas
    assert [a["type"] for a in flota] == [
        "GroundOperator", "GroundOperator", "Forklift", "Forklift"]
    assert flota[0]["capacity"] == 150
    assert flota[2]["capacity"] == 1000


def test_bk06_06_agent_types_explicito_tiene_prioridad():
    cfg = dict(CANONICO, agent_types=[
        {"type": "Forklift", "capacity": 777, "discharge_time": 9,
         "work_area_priorities": {"Area_High": 1}},
    ])
    flota = resolver_flota(cfg)
    assert len(flota) == 1
    assert flota[0]["capacity"] == 777
    assert flota[0]["discharge_time"] == 9


def test_bk06_07_fleet_defaults_es_configurable():
    """Principio rector #2: las capacidades ya no estan hardcodeadas."""
    cfg = dict(CANONICO, fleet_defaults={"Forklift": {"capacity": 2500}})
    flota = resolver_flota(cfg)
    forklifts = [a for a in flota if a["type"] == "Forklift"]
    assert all(a["capacity"] == 2500 for a in forklifts)
    # El merge es por clave: lo no sobreescrito se hereda del historico
    assert forklifts[0]["discharge_time"] == \
        HISTORIC_FLEET_DEFAULTS["Forklift"]["discharge_time"]


def test_bk06_08_defaults_historicos_intactos():
    """Sin fleet_defaults, el comportamiento historico no cambia."""
    flota = resolver_flota(CANONICO)
    caps = capacidades_por_tipo(CANONICO)
    assert caps["GroundOperator"] == [150, 150]
    assert caps["Forklift"] == [1000, 1000]
    assert flota[0]["work_area_priorities"] == \
        HISTORIC_FLEET_DEFAULTS["GroundOperator"]["work_area_priorities"]


# ------------------------------------------------------- capacidad por area

def test_bk06_09_area_dimensiona_por_el_equipo_que_la_atiende():
    """(a) EL BUG: con agent_types vacio esto daba {} y todo caia a 150."""
    caps, fallback = capacidades_por_area(CANONICO)
    assert caps["Area_High"] == 1000      # Forklift
    assert caps["Area_Special"] == 1000   # Forklift
    assert caps["Area_Ground"] == 150     # GroundOperator
    assert fallback == 150                # minimo de la flota (conservador)


def test_bk06_10_red_de_seguridad_toma_el_minimo():
    """(c) Con flota heterogenea en un mismo tipo, manda el MAS chico."""
    cfg = dict(CANONICO, agent_types=[
        {"type": "Forklift", "capacity": 1000,
         "work_area_priorities": {"Area_High": 1}},
        {"type": "Forklift", "capacity": 400,
         "work_area_priorities": {"Area_High": 1}},
    ])
    caps, _ = capacidades_por_area(cfg)
    # 400, no 1000: si dimensionara por el maximo, el forklift chico recibiria
    # WOs que no puede levantar -> el bucle de BK-06.
    assert caps["Area_High"] == 400


def test_bk06_11_sin_flota_no_rompe():
    cfg = {"agent_types": [], "num_operarios_terrestres": 0, "num_montacargas": 0}
    caps, fallback = capacidades_por_area(cfg)
    assert caps == {}
    assert fallback == 150  # historico


# --------------------------------------------------- integracion con el WH

def _almacen(configuracion):
    """AlmacenMejorado sin __init__: _validar_y_ajustar_cantidad solo usa
    operator_capacities y max_operator_capacity."""
    alm = object.__new__(AlmacenMejorado)
    alm.operator_capacities, alm.max_operator_capacity = \
        capacidades_por_area(configuracion)
    return alm


def test_bk06_12_wo_de_area_alta_no_se_divide_de_mas():
    """El efecto economico del fix: menos viajes de montacargas."""
    alm = _almacen(CANONICO)
    sku = SKU("SKU-BIG", volumen=200)
    # Antes: capacidad 150 -> 200 > 150 -> se DESCARTABA (backorder implicito).
    # Ahora: Area_High la atiende un Forklift (1000) -> 3 unidades = 600, un viaje.
    assert alm._validar_y_ajustar_cantidad(sku, 3, "Area_High") == [3]


def test_bk06_13_area_terrestre_sigue_limitada():
    """El fix no relaja lo que debe seguir acotado."""
    alm = _almacen(CANONICO)
    sku = SKU("SKU-MED", volumen=80)
    # Area_Ground sigue en 150: 1 unidad por viaje (80*2 = 160 > 150)
    assert alm._validar_y_ajustar_cantidad(sku, 3, "Area_Ground") == [1, 1, 1]


def test_bk06_14_ninguna_wo_generada_es_irrecogible():
    """(c) Invariante global: toda WO cabe en el agente que la va a tomar."""
    caps, fallback = capacidades_por_area(CANONICO)
    alm = _almacen(CANONICO)
    for area, capacidad in caps.items():
        for volumen in (10, 75, 150, 300, 999):
            sku = SKU("SKU-%s-%d" % (area, volumen), volumen=volumen)
            cantidades = alm._validar_y_ajustar_cantidad(sku, 5, area)
            for cantidad in cantidades:
                assert volumen * cantidad <= capacidad, (
                    "WO de %s (%d x %d) excede la capacidad del area (%d)"
                    % (area, cantidad, volumen, capacidad))
