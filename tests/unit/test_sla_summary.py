# -*- coding: utf-8 -*-
"""
INIT-4b / SLA-xx: caracterizacion de core.replay_utils.build_sla_summary
(cumplimiento de SLA por pedido, a partir de WorkOrders completadas con
due_time -- INIT-4 C2, opt-in). Mismo patron de plomeria que INIT-5
(build_service_level_summary): fuente unica para .jsonl, API y Excel.
"""
from core.replay_utils import build_sla_summary


class _FakeWO:
    def __init__(self, order_id, due_time, tiempo_fin):
        self.order_id = order_id
        self.due_time = due_time
        self.tiempo_fin = tiempo_fin


class _FakeDispatcher:
    def __init__(self, completadas):
        self.work_orders_completados = completadas


class _FakeAlmacen:
    def __init__(self, completadas):
        self.dispatcher = _FakeDispatcher(completadas)


def test_sla01_pedido_a_tiempo():
    wos = [_FakeWO("ORD-1", due_time=100.0, tiempo_fin=80.0)]
    resumen = build_sla_summary(_FakeAlmacen(wos))
    assert resumen["available"] is True
    assert resumen["total_orders_with_sla"] == 1
    assert resumen["orders_on_time"] == 1
    assert resumen["orders_late"] == 0
    assert resumen["on_time_pct"] == 100.0
    assert resumen["late_orders"] == []


def test_sla02_pedido_vencido():
    wos = [_FakeWO("ORD-1", due_time=100.0, tiempo_fin=150.0)]
    resumen = build_sla_summary(_FakeAlmacen(wos))
    assert resumen["orders_late"] == 1
    assert resumen["orders_on_time"] == 0
    assert resumen["on_time_pct"] == 0.0
    late = resumen["late_orders"][0]
    assert late["order_id"] == "ORD-1"
    assert late["delay_seconds"] == 50.0


def test_sla03_pedido_multi_wo_usa_el_tiempo_fin_maximo():
    """El pedido no esta completo hasta que TODAS sus WOs lo estan -- se usa
    el tiempo_fin mas tardio, no el primero ni un promedio."""
    wos = [
        _FakeWO("ORD-1", due_time=100.0, tiempo_fin=50.0),
        _FakeWO("ORD-1", due_time=100.0, tiempo_fin=120.0),  # esta WO vence el SLA
        _FakeWO("ORD-1", due_time=100.0, tiempo_fin=90.0),
    ]
    resumen = build_sla_summary(_FakeAlmacen(wos))
    assert resumen["total_orders_with_sla"] == 1  # 1 pedido, 3 WOs
    assert resumen["orders_late"] == 1
    assert resumen["late_orders"][0]["completion_time"] == 120.0


def test_sla04_borde_exacto_en_el_limite_es_a_tiempo():
    wos = [_FakeWO("ORD-1", due_time=100.0, tiempo_fin=100.0)]
    resumen = build_sla_summary(_FakeAlmacen(wos))
    assert resumen["orders_on_time"] == 1
    assert resumen["orders_late"] == 0


def test_sla05_mezcla_a_tiempo_y_vencidos_calcula_porcentaje():
    wos = [
        _FakeWO("ORD-1", due_time=100.0, tiempo_fin=90.0),   # a tiempo
        _FakeWO("ORD-2", due_time=50.0, tiempo_fin=80.0),    # vencido
        _FakeWO("ORD-3", due_time=200.0, tiempo_fin=150.0),  # a tiempo
    ]
    resumen = build_sla_summary(_FakeAlmacen(wos))
    assert resumen["total_orders_with_sla"] == 3
    assert resumen["orders_on_time"] == 2
    assert resumen["orders_late"] == 1
    assert resumen["on_time_pct"] == round(2 / 3 * 100, 1)


def test_sla06_wos_sin_due_time_se_ignoran_no_disponible():
    """INIT-4 C2 desactivado (o modo Stochastic): ninguna WO trae due_time."""
    wos = [_FakeWO("ORD-1", due_time=None, tiempo_fin=80.0)]
    resumen = build_sla_summary(_FakeAlmacen(wos))
    assert resumen["available"] is False
    assert resumen["total_orders_with_sla"] == 0
    assert resumen["on_time_pct"] is None
    assert resumen["late_orders"] == []


def test_sla07_sin_work_orders_completadas_no_disponible():
    resumen = build_sla_summary(_FakeAlmacen([]))
    assert resumen["available"] is False


def test_sla08_almacen_none_o_sin_dispatcher_no_rompe():
    assert build_sla_summary(None)["available"] is False
    assert build_sla_summary(object())["available"] is False
