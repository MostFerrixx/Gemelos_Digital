# -*- coding: utf-8 -*-
"""
INIT-8 F2 / T8-2x: tiempos por clase de manejo y peso.

Pinea:
- COMPAT EXACTA: sin pick_time_model, sin clases_manejo -> tiempo historico
  identico (la rama neutra que protegia el gate sigue intacta para configs
  viejas/presets).
- Formula F2: t = (base + por_unidad*qty + por_volumen*vol + por_kg*peso)
  * clase.mult + clase.recargo, con piso 'minimo'.
- Clase desconocida / sin SKU -> neutro (1.0, 0.0).
- Putaway load escalado por clase.
- El config canonico trae la calibracion (docs/PLAN_INIT8_TIEMPOS.md).
"""
import json
import os

import pytest

from subsystems.simulation.operators import GroundOperator
from subsystems.simulation.warehouse import SKU

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class FakeWO:
    def __init__(self, qty=2, volumen=1, peso=0.0, clase="GENERAL"):
        self.cantidad_inicial = qty
        self.sku = SKU("SKU-T", volumen=volumen, peso=peso, clase=clase)


def _operator(tiempos=None, discharge_time=5.0):
    """GroundOperator minimo sin tocar SimPy (solo el bloque de tiempos)."""
    op = object.__new__(GroundOperator)
    cfg = {"tiempos": tiempos} if tiempos else {}
    # replicar EXACTAMENTE el parseo del __init__ real (bloque tiempos)
    _tiempos = cfg.get("tiempos", {}) or {}
    op.discharge_time = discharge_time
    _pick = _tiempos.get("tiempo_picking_por_linea", None)
    op.picking_time = float(_pick) if _pick is not None else None
    _ptm = _tiempos.get("pick_time_model", {}) or {}
    _b = _ptm.get("base", None)
    op.pick_time_base = float(_b) if _b is not None else None
    op.pick_time_por_unidad = float(_ptm.get("por_unidad", 0.0) or 0.0)
    op.pick_time_por_volumen = float(_ptm.get("por_volumen", 0.0) or 0.0)
    op.pick_time_por_kg = float(_ptm.get("por_kg", 0.0) or 0.0)
    op.pick_time_minimo = float(_ptm.get("minimo", 0.0) or 0.0)
    _cm = _tiempos.get("clases_manejo", {})
    op.clases_manejo = _cm if isinstance(_cm, dict) else {}
    return op


CLASES = {
    "pequeno": {"mult": 0.8, "recargo": 0.0},
    "extra_grande": {"mult": 2.2, "recargo": 15.0},
}


def test_t820_compat_exacta_sin_bloques():
    """Configs viejas (sin pick_time_model ni clases_manejo) -> historico."""
    op = _operator(tiempos=None, discharge_time=5.0)
    assert op._compute_pick_time(FakeWO(qty=7, peso=85.0, clase="pesado")) == 5.0

    # incluso CON clases_manejo pero clase neutra/desconocida -> historico
    op2 = _operator(tiempos={"clases_manejo": CLASES})
    assert op2._compute_pick_time(FakeWO(clase="GENERAL")) == 5.0


def test_t821_formula_completa_por_clase_y_peso():
    tiempos = {
        "pick_time_model": {"base": 10.0, "por_unidad": 2.0,
                            "por_volumen": 0.0, "por_kg": 0.15, "minimo": 5.0},
        "clases_manejo": CLASES,
    }
    op = _operator(tiempos=tiempos)

    # polera: qty=2, 0.2kg c/u, clase pequeno (mult 0.8)
    polera = FakeWO(qty=2, volumen=1, peso=0.2, clase="pequeno")
    # (10 + 2*2 + 0.15*0.4) * 0.8 = 14.06 * 0.8 = 11.248
    assert op._compute_pick_time(polera) == pytest.approx(11.248)

    # refrigerador: qty=1, 85kg, extra_grande (mult 2.2, recargo 15)
    fridge = FakeWO(qty=1, volumen=120, peso=85.0, clase="extra_grande")
    # (10 + 2*1 + 0.15*85) * 2.2 + 15 = 24.75 * 2.2 + 15 = 69.45
    assert op._compute_pick_time(fridge) == pytest.approx(69.45)

    # EL PUNTO de INIT-8: el refrigerador tarda ~6x mas que la polera
    assert op._compute_pick_time(fridge) > 5 * op._compute_pick_time(polera)


def test_t822_piso_minimo_y_clase_desconocida():
    tiempos = {
        "pick_time_model": {"base": 1.0, "por_unidad": 0.0,
                            "por_volumen": 0.0, "por_kg": 0.0, "minimo": 5.0},
        "clases_manejo": CLASES,
    }
    op = _operator(tiempos=tiempos)
    # pequeno: 1.0 * 0.8 = 0.8 -> piso 5.0
    assert op._compute_pick_time(FakeWO(clase="pequeno")) == 5.0
    # clase que no esta en el bloque -> neutro (1.0, 0.0) -> base 1.0 -> piso
    assert op._compute_pick_time(FakeWO(clase="clase_inventada")) == 5.0
    # params corruptos -> neutro sin crash
    op.clases_manejo = {"rota": {"mult": "no-numero"}}
    assert op._clase_params(FakeWO(clase="rota")) == (1.0, 0.0)


def test_t823_putaway_load_escalado_por_clase():
    op = _operator(tiempos={"clases_manejo": CLASES})

    class _Almacen:
        inbound_config = {"putaway_load_time": 10.0}
    op.almacen = _Almacen()

    # pallet de linea blanca: 10 * 2.2 + 15 = 37s; neutro: 10s exacto
    assert op._putaway_load_time(FakeWO(clase="extra_grande")) == pytest.approx(37.0)
    assert op._putaway_load_time(FakeWO(clase="GENERAL")) == 10.0


def test_t824_canonico_trae_la_calibracion():
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    t = cfg["tiempos"]
    assert t["pick_time_model"]["base"] == 10.0
    assert t["pick_time_model"]["por_kg"] == 0.15
    cm = t["clases_manejo"]
    assert set(cm) == {"pequeno", "mediano", "voluminoso", "pesado",
                       "extra_grande", "GENERAL"}
    assert cm["extra_grande"]["mult"] > cm["mediano"]["mult"] > cm["pequeno"]["mult"]
