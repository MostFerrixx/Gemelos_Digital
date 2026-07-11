# -*- coding: utf-8 -*-
"""
INIT-8 F3 / T8-3x: velocidad segun carga transportada.

Pinea:
- OFF (default) -> factor 1.0 EXACTO (speed * 1.0 es identidad IEEE =>
  gate byte-identico sin el bloque).
- Calibracion Indian Army: 22 kg => reduccion 18.5% => factor tiempo ~1.227.
- reduccion_max acota el piso; clamp de seguridad a 0.9.
- Forklift exento por default (aplica_forklift).
- El espejo cargo_peso: pick suma, descarga resta, resets a 0.
"""
import pytest

from subsystems.simulation.operators import GroundOperator
from subsystems.simulation.warehouse import SKU


def _operator(vc=None, tipo="GroundOperator"):
    op = object.__new__(GroundOperator)
    op.type = tipo
    _vc = vc or {}
    op.vc_enabled = bool(_vc.get("enabled", False))
    op.vc_reduccion_por_kg = float(_vc.get("reduccion_por_kg", 0.0084) or 0.0)
    op.vc_reduccion_max = min(0.9, float(_vc.get("reduccion_max", 0.5) or 0.0))
    op.vc_aplica_forklift = bool(_vc.get("aplica_forklift", False))
    op.cargo_peso = 0.0
    return op


VC_ON = {"enabled": True, "reduccion_por_kg": 0.0084, "reduccion_max": 0.5}


def test_t830_off_es_identidad_exacta():
    op = _operator(vc=None)
    op.cargo_peso = 999.0
    assert op._factor_carga_tiempo() == 1.0        # off -> 1.0 exacto
    op2 = _operator(vc=VC_ON)
    assert op2._factor_carga_tiempo() == 1.0       # on pero sin peso -> 1.0


def test_t831_calibracion_indian_army():
    """22 kg -> -18.5% de velocidad -> factor de tiempo 1/(1-0.1848)."""
    op = _operator(vc=VC_ON)
    op.cargo_peso = 22.0
    f = op._factor_carga_tiempo()
    assert f == pytest.approx(1.0 / (1.0 - 22.0 * 0.0084))
    assert f == pytest.approx(1.227, abs=0.01)
    # velocidad efectiva: 1.35 m/s / 1.227 ~= 1.10 m/s (el dato del estudio)
    assert 1.35 / f == pytest.approx(1.10, abs=0.01)


def test_t832_tope_de_reduccion():
    op = _operator(vc=VC_ON)
    op.cargo_peso = 500.0   # absurdo: sin tope seria reduccion > 100%
    assert op._factor_carga_tiempo() == pytest.approx(1.0 / (1.0 - 0.5))  # 2.0
    # clamp de seguridad: reduccion_max nunca supera 0.9 aunque el config diga 5
    op2 = _operator(vc={"enabled": True, "reduccion_por_kg": 1.0,
                        "reduccion_max": 5.0})
    op2.cargo_peso = 100.0
    assert op2._factor_carga_tiempo() == pytest.approx(1.0 / (1.0 - 0.9))


def test_t833_forklift_exento_por_default():
    fk = _operator(vc=VC_ON, tipo="Forklift")
    fk.cargo_peso = 40.0
    assert fk._factor_carga_tiempo() == 1.0        # la maquina carga, no el cuerpo
    fk2 = _operator(vc=dict(VC_ON, aplica_forklift=True), tipo="Forklift")
    fk2.cargo_peso = 40.0
    assert fk2._factor_carga_tiempo() > 1.0        # opt-in explicito


def test_t834_espejo_cargo_peso():
    """add_cargo/clear_cargo y el patron pick (+peso antes de zerear qty)."""
    op = _operator(vc=VC_ON)
    op.cargo_volume = 0

    class WO:
        sku = SKU("S", volumen=2, peso=12.5, clase="pesado")
        cantidad_restante = 3
        cantidad_inicial = 3

        def calcular_volumen_restante(self):
            return self.cantidad_restante * self.sku.volumen

    wo = WO()
    # patron de pick real: volumen y peso ANTES de zerear cantidad_restante
    op.cargo_volume += wo.calcular_volumen_restante()
    op.cargo_peso += wo.cantidad_restante * getattr(wo.sku, 'peso', 0.0)
    assert op.cargo_peso == pytest.approx(37.5)
    assert op._factor_carga_tiempo() > 1.2         # 37.5 kg pesa en la marcha

    # descarga (patron staging): resta por WO
    op.cargo_peso -= wo.cantidad_inicial * getattr(wo.sku, 'peso', 0.0)
    assert op.cargo_peso == pytest.approx(0.0)
    assert op._factor_carga_tiempo() == 1.0

    op.cargo_peso = 10.0
    op.clear_cargo()
    assert op.cargo_peso == 0.0
