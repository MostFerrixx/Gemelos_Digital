# -*- coding: utf-8 -*-
"""
QA-8.1 (N3): el panel de recepcion del visor lee `metrics.inbound_summary` del
snapshot. La API lo mandaba solo en el nivel superior y el panel no aparecia
nunca.
"""
from web_prototype.routers import replay as rutas


def test_snapshot_trae_inbound_summary_dentro_de_metrics(monkeypatch):
    rd = rutas.replay_data
    resumen = {'available': True, 'trucks_received': 3, 'pallets_stored': 12}
    monkeypatch.setattr(rd, 'inbound_summary', resumen, raising=False)
    monkeypatch.setattr(rd, 'snapshots', {}, raising=False)
    monkeypatch.setattr(rd, 'events', [], raising=False)
    snap = rutas.get_snapshot(0.0)
    assert snap['metrics']['inbound_summary'] == resumen
    assert snap['inbound_summary'] == resumen
