# -*- coding: utf-8 -*-
"""
QA H-28: el visor debe dibujar el mapa con el que se corrio el replay cargado.

Correr desde la web no modifica config.json, asi que al probar otro layout la
simulacion usaba el mapa nuevo (30x42) y el visor seguia dibujando el de
config.json (30x30): el dibujo no coincidia con lo que pasaba.
"""
import json
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _replay(tmp_path, metadata):
    ruta = tmp_path / "replay_test.jsonl"
    lineas = [json.dumps(metadata), json.dumps({"type": "SIMULATION_END", "timestamp": 1.0})]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return str(ruta)


def test_h28_el_replay_recuerda_su_layout(tmp_path, monkeypatch):
    from web_prototype import app_state
    ruta = _replay(tmp_path, {"type": "SIMULATION_START", "timestamp": 0,
                              "config": {"layout_file": "layouts/WH1 v2.tmx"},
                              "initial_work_orders": []})
    monkeypatch.setattr(app_state, "REPLAY_FILE", ruta)
    assert app_state.ReplayData().layout_file == "layouts/WH1 v2.tmx"


def test_h28_sin_layout_en_la_metadata_no_rompe(tmp_path, monkeypatch):
    from web_prototype import app_state
    ruta = _replay(tmp_path, {"type": "SIMULATION_START", "timestamp": 0})
    monkeypatch.setattr(app_state, "REPLAY_FILE", ruta)
    assert app_state.ReplayData().layout_file is None
