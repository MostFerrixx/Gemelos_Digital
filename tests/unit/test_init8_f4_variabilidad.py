# -*- coding: utf-8 -*-
"""
INIT-8 F4 / T8-4x: variabilidad Log-Normal de tiempos + packing por clase.

Pinea:
- OFF (default) -> identidad EXACTA (mismo objeto devuelto: gate intacto).
- Log-Normal con MEDIA preservada (E[X] = t), acotada en 0, cola derecha.
- Reproducible bajo semilla (random global / WAREHOUSE_SEED).
- CRITICO: el pick se muestrea UNA vez por WO (cache) -- la reserva del
  planner y el timeout real ven la MISMA muestra.
- Packing por clase suma a la descarga (pack=0 = neutro exacto).
"""
import random

import pytest

from subsystems.simulation.operators import GroundOperator
from subsystems.simulation.warehouse import SKU


def _operator(var=None, clases=None, discharge_time=5):
    import math
    op = object.__new__(GroundOperator)
    op.discharge_time = discharge_time
    op.picking_time = None
    op.pick_time_base = None
    op.pick_time_por_unidad = 0.0
    op.pick_time_por_volumen = 0.0
    op.pick_time_por_kg = 0.0
    op.pick_time_minimo = 0.0
    op.clases_manejo = clases or {}
    _var = var or {}
    op.var_enabled = bool(_var.get("enabled", False))
    _cv = max(0.0, float(_var.get("cv", 0.25) or 0.0))
    op.var_sigma = math.sqrt(math.log(1.0 + _cv * _cv)) if _cv > 0 else 0.0
    return op


class FakeWO:
    def __init__(self, clase="GENERAL", qty=2):
        self.cantidad_inicial = qty
        self.sku = SKU("S", volumen=1, peso=1.0, clase=clase)


def test_t840_off_es_identidad_de_objeto():
    op = _operator(var=None)
    t = 5  # int historico
    assert op._tiempo_estocastico(t) is t          # MISMO objeto, ni float()
    wo = FakeWO()
    assert op._tiempo_pick_final(wo) == 5          # historico exacto
    assert op._tiempo_descarga_final(wo) is op.discharge_time  # sin pack, sin var


def test_t841_media_preservada_y_reproducible():
    op = _operator(var={"enabled": True, "cv": 0.25})
    random.seed(42)
    muestras = [op._tiempo_estocastico(10.0) for _ in range(4000)]
    media = sum(muestras) / len(muestras)
    assert media == pytest.approx(10.0, rel=0.02)  # E[X] = t (2% tolerancia)
    assert min(muestras) > 0                        # acotada en cero SIEMPRE
    mediana = sorted(muestras)[len(muestras) // 2]
    assert mediana < media                          # cola derecha (asimetria)

    random.seed(42)
    muestras2 = [op._tiempo_estocastico(10.0) for _ in range(4000)]
    assert muestras == muestras2                    # reproducible bajo semilla


def test_t842_pick_muestreado_una_vez_por_wo():
    """La muestra se cachea en la WO: reserva del planner y timeout real ven
    EL MISMO valor (sin esto el plan espacio-temporal se desincroniza)."""
    op = _operator(var={"enabled": True, "cv": 0.4})
    random.seed(7)
    wo = FakeWO()
    t1 = op._tiempo_pick_final(wo)
    t2 = op._tiempo_pick_final(wo)   # segunda llamada (el timeout real)
    t3 = op._tiempo_pick_final(wo)
    assert t1 == t2 == t3            # misma muestra, no re-sampleo
    # otra WO -> otra muestra (no un valor global congelado)
    otras = {op._tiempo_pick_final(FakeWO()) for _ in range(5)}
    assert len(otras) == 5


def test_t843_pack_por_clase_en_descarga():
    clases = {"fragil_demo": {"mult": 1.0, "recargo": 0.0, "pack": 12.0}}
    op = _operator(var=None, clases=clases, discharge_time=5)
    # con pack: descarga = 5 + 12 = 17 (sin variabilidad, determinista)
    assert op._tiempo_descarga_final(FakeWO(clase="fragil_demo")) == 17.0
    # clase sin pack o desconocida -> discharge intacto (neutro exacto)
    assert op._tiempo_descarga_final(FakeWO(clase="GENERAL")) is op.discharge_time
    # pack corrupto -> 0.0 sin crash
    op.clases_manejo = {"rota": {"pack": "mucho"}}
    assert op._clase_pack(FakeWO(clase="rota")) == 0.0


def test_t844_putaway_load_muestreado():
    op = _operator(var={"enabled": True, "cv": 0.3},
                   clases={"pesado": {"mult": 1.5, "recargo": 5.0}})

    class _Almacen:
        inbound_config = {"putaway_load_time": 10.0}
    op.almacen = _Almacen()

    random.seed(11)
    vals = {op._putaway_load_time(FakeWO(clase="pesado")) for _ in range(5)}
    assert len(vals) == 5                       # muestrea de verdad
    assert all(v > 0 for v in vals)
    # media ~ 10*1.5+5 = 20
    random.seed(11)
    n = 2000
    media = sum(op._putaway_load_time(FakeWO(clase="pesado"))
                for _ in range(n)) / n
    assert media == pytest.approx(20.0, rel=0.03)


def test_t845_aud81_dwell_de_staging_incluye_pack():
    """AUD8-1: la reserva del planner para el staging suma el packing por
    clase. Con packs 0 -> discharge*n EXACTO (identidad IEEE, gate)."""
    clases = {"extra_grande": {"pack": 20.0}, "pequeno": {"pack": 3.0}}
    op = _operator(var=None, clases=clases, discharge_time=5)
    wos = [FakeWO(clase="extra_grande"), FakeWO(clase="pequeno"),
           FakeWO(clase="GENERAL")]
    # 5*3 + 20 + 3 + 0 = 38
    assert op._staging_dwell_estimate(wos) == 38.0
    # sin packs: EXACTO discharge*n (neutralidad byte-identica)
    op2 = _operator(var=None, clases={}, discharge_time=5)
    assert op2._staging_dwell_estimate(wos) == 15.0
