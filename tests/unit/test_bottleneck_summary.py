# -*- coding: utf-8 -*-
"""
MEJ-BOTTLENECK / BN-xx: caracterizacion de core.replay_utils.build_bottleneck_summary
(consolidado de cuellos de botella: congestion + planner + muelle). Misma
plomeria que INIT-5/INIT-4b: fuente unica para .jsonl, API y hoja Excel.

REGLA CRITICA cubierta por BN-05: el summary va a la metadata del .jsonl que
hashea el gate byte-identico -- NO puede contener valores wall-clock
(avg_plan_ms y similares varian entre corridas identicas y romperian el gate;
paso de verdad al implementarlo, ver docs/CHANGELOG.md 2026-07-06).
"""
import json

from core.replay_utils import build_bottleneck_summary


class _FakeCongestionManager:
    def __init__(self, active=True):
        self.active = active

    def resumen(self):
        return {
            "cooccupation_events_total": 10,
            "distinct_cells_with_cooccupation": 6,
            "max_concurrent_any_cell": 2,
            "top_hotspots": [
                {"cell": [3, 29], "cooccupations": 3, "max_concurrent": 2},
            ] * 12,  # mas de 8 para probar el recorte
        }


class _FakePlanner:
    def shadow_report(self):
        return {
            "segments_planned": 348,
            "plans_found": 347,
            "plans_failed": 1,
            "avg_plan_ms": 0.63,       # wall-clock: NO debe pasar al summary
            "max_plan_ms": 14.29,      # wall-clock: NO debe pasar al summary
            "avg_waits_per_plan": 0.092,
            "table_overlap_violations": 0,
        }


class _FakeAlmacen:
    def __init__(self, cm=None, planner=None, outbound_metrics=None):
        if cm is not None:
            self.congestion_manager = cm
        if planner is not None:
            self.spacetime_planner = planner
        if outbound_metrics is not None:
            self.outbound_metrics = outbound_metrics


def _om():
    return {
        "pallets_staged": 300, "pallets_shipped": 290,
        "slot_wait_events": 5, "slot_wait_time": 42.5, "max_slot_wait": 12.0,
        "lane_full_wait_events": 2, "lane_full_wait_time": 8.0,
        "peak_occupancy": {1: 8, 3: 4},
    }


def test_bn01_todo_activo_consolida_los_tres_bloques():
    bn = build_bottleneck_summary(_FakeAlmacen(
        cm=_FakeCongestionManager(), planner=_FakePlanner(), outbound_metrics=_om()))
    assert bn["available"] is True
    assert bn["congestion"]["cooccupation_events_total"] == 10
    assert bn["planner"]["plans_failed"] == 1
    assert bn["outbound"]["slot_wait_events"] == 5
    json.dumps(bn)  # serializable


def test_bn02_hotspots_recortados_a_8():
    bn = build_bottleneck_summary(_FakeAlmacen(cm=_FakeCongestionManager()))
    assert len(bn["congestion"]["top_hotspots"]) == 8


def test_bn03_todo_apagado_no_disponible():
    bn = build_bottleneck_summary(_FakeAlmacen())
    assert bn["available"] is False
    assert bn["congestion"] is None
    assert bn["planner"] is None
    assert bn["outbound"] is None


def test_bn04_congestion_inactiva_se_ignora():
    bn = build_bottleneck_summary(_FakeAlmacen(cm=_FakeCongestionManager(active=False)))
    assert bn["congestion"] is None
    assert bn["available"] is False


def test_bn05_sin_wall_clock_en_el_summary():
    """El summary va al .jsonl hasheado por el gate: cualquier valor wall-clock
    (ms de CPU) lo volveria no-determinista. Si este test falla, NO agregar el
    campo -- mover ese dato al JSON de diagnostico no hasheado."""
    bn = build_bottleneck_summary(_FakeAlmacen(planner=_FakePlanner()))
    assert "avg_plan_ms" not in bn["planner"]
    assert "max_plan_ms" not in bn["planner"]
    flat = json.dumps(bn)
    assert "_ms" not in flat


def test_bn06_peak_occupancy_claves_string():
    bn = build_bottleneck_summary(_FakeAlmacen(outbound_metrics=_om()))
    assert bn["outbound"]["peak_occupancy"] == {"1": 8, "3": 4}
