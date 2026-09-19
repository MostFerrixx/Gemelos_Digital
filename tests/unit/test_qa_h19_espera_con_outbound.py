# -*- coding: utf-8 -*-
"""
QA H-19: con el muelle de salida (outbound) activo, las celdas de espera de
los ociosos (BK-15) no pueden caer dentro de los carriles de descarga.

Las zonas de espera se elegian ANTES de que el outbound expandiera cada zona
de descarga a un carril de varias celdas y las marcara no caminables: los
ociosos quedaban intentando llegar para siempre a una celda bloqueada.
"""
import json
import os

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.mark.parametrize("outbound", [False, True])
def test_h19_celdas_de_espera_caminables_y_fuera_de_los_carriles(tmp_path, outbound):
    from engines.event_generator import EventGenerator
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["total_ordenes"] = 5
    cfg["outbound"]["enabled"] = outbound
    ruta = tmp_path / "config.json"
    ruta.write_text(json.dumps(cfg), encoding="utf-8")
    cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)
    try:
        gen = EventGenerator(headless_mode=True, config_path=str(ruta))
        assert gen.crear_simulacion()
        almacen = gen.almacen
        celdas = almacen.zonas_espera.celdas
        assert celdas
        carriles = {s.cell for z in almacen.staging_zones.values() for s in z.slots}
        assert bool(carriles) == outbound
        for c in celdas:
            assert c not in carriles
            assert almacen.layout_manager.is_walkable(*c), c
    finally:
        os.chdir(cwd)
