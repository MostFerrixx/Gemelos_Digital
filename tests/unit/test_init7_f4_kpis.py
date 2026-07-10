# -*- coding: utf-8 -*-
"""
INIT-7 F4 / IN-4x: KPIs de recepcion/putaway (build_inbound_summary).

Pinea:
- available=False sin inbound (motor intacto).
- Promedios derivados (dock-to-stock, distancia) y transporte de la estrategia.
- REGLA BN-05: el summary NO contiene claves wall-clock (rompen el gate).
"""
from core.replay_utils import build_inbound_summary


class FakeAlmacen:
    def __init__(self, metrics=None, slotting=None, docks=0):
        if metrics is not None:
            self.inbound_metrics = metrics
        if slotting is not None:
            self.inbound_slotting = slotting
        self.inbound_docks = {i: object() for i in range(docks)}


def test_in40_sin_inbound_no_disponible():
    class Bare:
        pass
    assert build_inbound_summary(Bare()) == {'available': False}
    assert build_inbound_summary(None) == {'available': False}


def test_in41_promedios_y_transporte():
    metrics = {
        'trucks_received': 3, 'pallets_unloaded': 10, 'pallets_stored': 8,
        'units_received': 200,
        'dock_to_stock_total': 800.0, 'max_dock_to_stock': 250.0,
        'putaway_distance_total': 160.0, 'max_putaway_distance': 40.0,
        'dock_wait_events': 2, 'dock_wait_time': 90.0, 'max_dock_wait': 60.0,
        'buffer_peak': 5,
    }
    s = build_inbound_summary(FakeAlmacen(metrics, 'cercana_al_muelle', docks=3))
    assert s['available'] is True
    assert s['slotting_strategy'] == 'cercana_al_muelle'
    assert s['docks_count'] == 3
    assert s['pallets_stored'] == 8
    assert s['avg_dock_to_stock'] == 100.0   # 800 / 8
    assert s['avg_putaway_distance'] == 20.0  # 160 / 8
    assert s['max_dock_to_stock'] == 250.0
    assert s['buffer_peak'] == 5


def test_in42_cero_guardados_promedios_none():
    metrics = {'pallets_unloaded': 4, 'pallets_stored': 0,
               'dock_to_stock_total': 0.0, 'putaway_distance_total': 0.0}
    s = build_inbound_summary(FakeAlmacen(metrics, 'fija_por_sku'))
    assert s['available'] is True
    assert s['avg_dock_to_stock'] is None   # sin division por cero
    assert s['avg_putaway_distance'] is None


def test_in43_sin_wall_clock_regla_bn05():
    """El summary viaja en la metadata del .jsonl: NINGUNA clave puede oler a
    wall-clock (avg_plan_ms rompio el gate una vez -- test BN-05)."""
    metrics = {'pallets_stored': 1, 'dock_to_stock_total': 10.0,
               'putaway_distance_total': 5.0}
    s = build_inbound_summary(FakeAlmacen(metrics, 'abc_rotacion'))
    banned = ('_ms', 'perf_counter', 'wall', 'clock', 'real_time', 'elapsed')
    for key in s:
        low = key.lower()
        assert not any(b in low for b in banned), key
