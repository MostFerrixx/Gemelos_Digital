# -*- coding: utf-8 -*-
"""
MEJ-1 / SL-xx: caracterizacion de core.replay_utils.build_service_level_summary
(INIT-5: nivel de servicio / backorders; fuente unica de .jsonl, API y Excel).
"""
from core.replay_utils import build_service_level_summary


class _FakeValidationResult:
    def __init__(self, allocation_summary, unfilled_demand):
        self.allocation_summary = allocation_summary
        self.unfilled_demand = unfilled_demand


class _FakeAlmacen:
    def __init__(self, vr):
        self._vr = vr

    def get_order_validation_result(self):
        return self._vr


def test_sl01_modo_determinista_transporta_resumen():
    vr = _FakeValidationResult(
        allocation_summary={
            "allocation_rate": 44.6,
            "total_qty_requested": 803,
            "total_qty_allocated": 358,
            "total_qty_unfilled": 445,
            "backorder_items_count": 2,
        },
        unfilled_demand=[
            {"order_id": "ORD-A", "sku": "SKU026", "qty": 329},
            {"order_id": "ORD-B", "sku": "SKU030", "qty": 116},
            {"order_id": "ORD-A", "sku": "SKU031", "qty": 10},  # mismo pedido
        ],
    )
    resumen = build_service_level_summary(_FakeAlmacen(vr))
    assert resumen["available"] is True
    assert resumen["mode"] == "deterministic"
    assert resumen["fill_rate_pct"] == 44.6
    assert resumen["total_requested"] == 803
    assert resumen["total_served"] == 358
    assert resumen["total_unfilled"] == 445
    assert resumen["orders_short"] == 2  # ORD-A cuenta una sola vez
    assert resumen["backorder_items"] == 2
    assert len(resumen["unfilled"]) == 3


def test_sl02_modo_estocastico_no_disponible():
    resumen = build_service_level_summary(_FakeAlmacen(None))
    assert resumen["available"] is False
    assert resumen["mode"] == "stochastic"
    assert resumen["fill_rate_pct"] is None
    assert resumen["unfilled"] == []


def test_sl03_almacen_none_o_sin_metodo_no_rompe():
    assert build_service_level_summary(None)["available"] is False
    assert build_service_level_summary(object())["available"] is False
