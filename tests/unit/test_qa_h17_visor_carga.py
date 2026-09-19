# -*- coding: utf-8 -*-
"""
QA H-17: el visor debe mostrar la carga y la capacidad REALES del operario
(vienen en cada evento estado_agente), no un valor inventado (100/200).
"""
from web_prototype.app_state import ReplayData


def _estado(capacidad, carga):
    return {'type': 'estado_agente', 'agent_id': 'Forklift-01', 'timestamp': 1.0,
            'data': {'position': [3, 29], 'status': 'moving',
                     'cargo_volume': carga, 'capacidad': capacidad}}


def test_h17_carga_y_capacidad_del_evento_llegan_al_estado():
    rd = ReplayData()
    estado = {'agents': {}, 'work_orders': {}}
    rd._apply_event_to_state(_estado(3000, 993), estado)
    assert estado['agents']['Forklift-01']['capacidad'] == 3000
    assert estado['agents']['Forklift-01']['cargo_volume'] == 993
    rd._apply_event_to_state(_estado(3000, 0), estado)      # descargo
    assert estado['agents']['Forklift-01']['cargo_volume'] == 0
