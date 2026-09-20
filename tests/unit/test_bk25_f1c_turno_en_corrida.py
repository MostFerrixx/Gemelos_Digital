# -*- coding: utf-8 -*-
"""
BK-25 F1.c: la estacion con turno, en una corrida real (canonico, semilla 42).

Con la estacion activa, dos operarios no pueden estar a la vez en la misma
celda de descarga: el segundo espera turno. La feature es opt-in: sin el
bloque `estaciones` el motor se comporta como siempre.
"""
import contextlib
import io
import json
import os

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _correr(tmp_path, monkeypatch, estaciones):
    from engines.event_generator import EventGenerator
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["total_ordenes"] = 25
    if estaciones is None:
        cfg.pop("estaciones", None)      # el canonico ya la trae encendida
    else:
        cfg["estaciones"] = estaciones
    ruta = tmp_path / "config.json"
    ruta.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("WAREHOUSE_SEED", "42")
    monkeypatch.chdir(PROJECT_ROOT)
    gen = EventGenerator(headless_mode=True, config_path=str(ruta))
    with contextlib.redirect_stdout(io.StringIO()):
        gen.ejecutar()
    return gen.almacen


def test_f1c_apagada_por_defecto(tmp_path, monkeypatch):
    almacen = _correr(tmp_path, monkeypatch, None)
    assert almacen.estaciones is None


def test_f1c_con_turno_nadie_comparte_la_celda_de_descarga(tmp_path, monkeypatch):
    almacen = _correr(tmp_path, monkeypatch, {"enabled": True, "cola_max": 1})
    gestor = almacen.estaciones
    assert gestor is not None and gestor.estaciones
    # todas las tareas terminaron y nadie se quedo con un turno tomado
    assert almacen.dispatcher.simulacion_ha_terminado()
    for est in gestor.estaciones.values():
        assert all(quien is None for quien in est.ocupante.values())
    # ninguna co-ocupacion en las celdas de descarga
    celdas_descarga = {c for est in gestor.estaciones.values() for c in est.celdas}
    puntos = almacen.congestion_manager.resumen().get("top_hotspots", [])
    for punto in puntos:
        assert tuple(punto["cell"]) not in celdas_descarga, punto
