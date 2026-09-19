# -*- coding: utf-8 -*-
"""
QA H-26: con el muelle de salida activo, la corrida termina cuando el ultimo
pallet sube al camion, no cuando la ultima tarea llega a la zona de descarga.
Antes quedaban 1-3 pallets sin despachar al cortar la simulacion.
"""
import contextlib
import io
import json
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_h26_no_quedan_pallets_sin_despachar(tmp_path, monkeypatch):
    from engines.event_generator import EventGenerator
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["total_ordenes"] = 8
    cfg["outbound"]["enabled"] = True
    cfg["outbound"]["truck_interval"] = 300     # camion lento: fuerza la espera
    ruta = tmp_path / "config.json"
    ruta.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("WAREHOUSE_SEED", "42")
    monkeypatch.chdir(PROJECT_ROOT)
    gen = EventGenerator(headless_mode=True, config_path=str(ruta))
    with contextlib.redirect_stdout(io.StringIO()):
        assert gen.crear_simulacion()
        a = gen.almacen
        while not a.simulacion_ha_terminado() and a.env.now < 50000:
            a.env.run(until=a.env.now + 1.0)
    staged = a.outbound_metrics["pallets_staged"]
    assert staged > 0
    assert a.outbound_process.pallets_shipped == staged
    assert a.staged_pallets == []
