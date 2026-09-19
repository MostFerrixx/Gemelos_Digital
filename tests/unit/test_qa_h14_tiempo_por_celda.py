# -*- coding: utf-8 -*-
"""
QA H-14: el tiempo por celda configurado debe gobernar el movimiento.

El planificador anti-colision (activo en el canonico) se creaba con
time_per_cell=0.1 fijo: todo el movimiento sale de su plan, asi que el perfil
"Real" (1.0 s/celda) elegido en la web no cambiaba la velocidad de nadie.
"""
import json
import os

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.mark.parametrize("tpc", [0.1, 1.0, 0.37])
def test_h14_el_planner_usa_el_tiempo_por_celda_de_la_config(tmp_path, tpc):
    from engines.event_generator import EventGenerator
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["total_ordenes"] = 5
    cfg["tiempos"]["time_per_cell"] = tpc
    ruta = tmp_path / "config.json"
    ruta.write_text(json.dumps(cfg), encoding="utf-8")
    cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)
    try:
        gen = EventGenerator(headless_mode=True, config_path=str(ruta))
        assert gen.crear_simulacion()
        planner = gen.almacen.spacetime_planner
        assert planner is not None
        assert planner.time_per_cell == pytest.approx(tpc)
        assert planner._dur(0.5) == pytest.approx(tpc * 0.5)
    finally:
        os.chdir(cwd)
