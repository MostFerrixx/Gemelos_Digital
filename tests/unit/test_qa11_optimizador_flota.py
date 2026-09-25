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


def test_el_estado_trae_cada_trial_con_su_flota_simulada(tmp_path):
    import optuna
    from optuna.distributions import IntDistribution
    from web_prototype.optimization_runner import OptimizationRunner
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    storage = 'sqlite:///' + (tmp_path / 'o.db').as_posix()
    st = optuna.create_study(study_name='qa', storage=storage, direction='maximize')
    dist = {'num_operarios_terrestres': IntDistribution(1, 20), 'num_montacargas': IntDistribution(1, 10)}
    st.add_trial(optuna.trial.create_trial(
        params={'num_operarios_terrestres': 5, 'num_montacargas': 3}, distributions=dist, value=1.5,
        user_attrs={'flota_simulada': {'terrestres': 5, 'montacargas': 3}, 'tareas_por_hora': 300.0,
                    'total_cost_per_hour': 225}))
    r = OptimizationRunner().status(study_name='qa', storage=storage)
    t = r['trials'][0]
    assert t['estado'] == 'COMPLETE' and t['puntaje'] == 1.5
    assert t['params']['num_operarios_terrestres'] == 5
    assert t['flota_simulada'] == {'terrestres': 5, 'montacargas': 3}
    assert t['tareas_por_hora'] == 300.0 and t['costo_por_hora'] == 225


def test_detener_cierra_los_trials_cortados_y_el_total_es_lo_pedido(tmp_path):
    import optuna
    from optuna.trial import TrialState
    from web_prototype.optimization_runner import OptimizationRunner
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    storage = 'sqlite:///' + (tmp_path / 'o.db').as_posix()
    st = optuna.create_study(study_name='qa', storage=storage, direction='maximize')
    st.set_user_attr('n_trials_pedidos', 12)
    st.ask()                                          # un trial que quedo corriendo
    runner = OptimizationRunner()
    r = runner.status(study_name='qa', storage=storage)
    assert r['n_trials_total'] == 12                  # H-50: lo pedido, no lo creado
    assert r['trials'][0]['estado'] == 'CORTADO'      # H-49: sin estudio corriendo
    runner._study_name, runner._storage = 'qa', storage
    runner._marcar_cortados()
    assert optuna.load_study(study_name='qa', storage=storage).trials[0].state == TrialState.FAIL
