# -*- coding: utf-8 -*-
"""
QA H-47: el optimizador tiene que variar la flota REAL. Con `agent_types` (el
canonico) el motor ignora los contadores num_operarios_terrestres /
num_montacargas: los 4 trials de QA-11.1 corrieron con la misma flota 2+2 y el
puntaje solo cambiaba por el costo nominal (se "recomendaba" 2+2).
"""
import contextlib
import io
import json
import os
import tempfile

import pytest

from tools.optimizer import flota_de_trial

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_flota_de_trial_repite_las_plantillas():
    base = [{'type': 'GroundOperator', 'capacity': 150},
            {'type': 'Forklift', 'capacity': 1000, 'work_area_priorities': {'Area_High': 1}}]
    flota = flota_de_trial(base, 5, 3)
    assert [a['type'] for a in flota].count('GroundOperator') == 5
    assert [a['type'] for a in flota].count('Forklift') == 3
    assert all(a['capacity'] == 1000 for a in flota if a['type'] == 'Forklift')
    flota[-1]['capacity'] = 1                       # copias, no la misma plantilla
    assert base[1]['capacity'] == 1000


def test_el_trial_simula_la_flota_pedida_y_la_cobra():
    from engines.event_generator import EventGenerator
    cfg = json.load(open(os.path.join(RAIZ, 'config.json'), encoding='utf-8'))
    if not cfg.get('agent_types'):
        pytest.skip('el canonico no usa agent_types')
    cfg['agent_types'] = flota_de_trial(cfg['agent_types'], 5, 3)
    cfg['num_operarios_terrestres'], cfg['num_montacargas'] = 99, 99   # deben ignorarse
    ruta = os.path.join(tempfile.mkdtemp(), 'c.json')
    json.dump(cfg, open(ruta, 'w'))
    cwd = os.getcwd()
    try:
        os.chdir(RAIZ)
        with contextlib.redirect_stdout(io.StringIO()):
            gen = EventGenerator(headless_mode=True, config_path=ruta)
            gen.crear_simulacion()
            salida = os.path.join(tempfile.mkdtemp(), 'm.json')
            gen.export_optimization_metrics(salida)
    finally:
        os.chdir(cwd)
    assert len(gen.operarios) == 8
    costos = json.load(open(salida, encoding='utf-8'))['resource_costs']
    assert costos == {'ground_operators': 5, 'forklifts': 3}
