# -*- coding: utf-8 -*-
"""
Saltar tiempos muertos: endpoint /api/motion-times.

En una corrida tipica ~94% del tiempo simulado no se mueve NINGUN agente
(picking, descarga, esperas). El visor usa estos instantes para saltar esos
tramos en vez de reproducir una pantalla congelada.

Contrato que se pinnea aca:
  * `motion_times`: instantes en los que ALGUN agente cambia de celda.
  * `jump_targets`: de esos, los que vienen despues de un hueco > min_gap
    (los unicos que vale la pena saltar).
  * Un agente que emite eventos SIN cambiar de celda no cuenta como movimiento.
"""
import pytest

from web_prototype.app_state import replay_data
from web_prototype.routers.replay import get_motion_times


def _evento(t, agente, x, y):
    return {"type": "estado_agente", "timestamp": t, "agent_id": agente,
            "data": {"position": [x, y], "status": "moving"}}


@pytest.fixture()
def replay_sintetico():
    """Reemplaza el replay global y lo restaura al terminar."""
    originales = replay_data.events
    original_max = replay_data.max_time
    yield
    replay_data.events = originales
    replay_data.max_time = original_max


def test_mt01_detecta_solo_cambios_de_celda(replay_sintetico):
    """Quedarse quieto emitiendo eventos NO es movimiento."""
    replay_data.events = [
        _evento(0.0, "A", 1, 1),
        _evento(0.5, "A", 1, 1),   # mismo lugar: no cuenta
        _evento(1.0, "A", 1, 1),   # mismo lugar: no cuenta
        _evento(1.5, "A", 2, 1),   # se movio
    ]
    replay_data.max_time = 2.0
    r = get_motion_times(min_gap=1.0)
    assert r["motion_times"] == [0.0, 1.5]


def test_mt02_dos_agentes_se_combinan_en_una_linea_de_tiempo(replay_sintetico):
    """Hay movimiento si CUALQUIER agente se mueve."""
    replay_data.events = [
        _evento(0.0, "A", 1, 1),
        _evento(0.0, "B", 5, 5),
        _evento(3.0, "A", 1, 1),   # A quieto
        _evento(3.0, "B", 5, 6),   # B se movio -> hay movimiento en t=3
    ]
    replay_data.max_time = 4.0
    r = get_motion_times(min_gap=1.0)
    assert 3.0 in r["motion_times"]


def test_mt03_jump_targets_marcan_el_final_de_cada_hueco(replay_sintetico):
    """Solo se salta a donde REAPARECE el movimiento tras una pausa larga."""
    replay_data.events = [
        _evento(0.0, "A", 1, 1),
        _evento(0.5, "A", 2, 1),    # continuo (hueco 0.5s < min_gap)
        _evento(100.0, "A", 3, 1),  # tras 99.5s quieto -> destino de salto
        _evento(100.5, "A", 4, 1),  # continuo
        _evento(300.0, "A", 5, 1),  # tras 199.5s quieto -> destino de salto
    ]
    replay_data.max_time = 301.0
    r = get_motion_times(min_gap=1.0)
    assert r["jump_targets"] == [0.0, 100.0, 300.0]


def test_mt04_min_gap_filtra_los_huecos_chicos(replay_sintetico):
    replay_data.events = [
        _evento(0.0, "A", 1, 1),
        _evento(2.0, "A", 2, 1),    # hueco de 2s
        _evento(4.0, "A", 3, 1),    # hueco de 2s
    ]
    replay_data.max_time = 5.0
    # Con min_gap=1 los dos huecos de 2s son saltables
    assert get_motion_times(min_gap=1.0)["jump_targets"] == [0.0, 2.0, 4.0]
    # Con min_gap=5 ninguno lo es
    assert get_motion_times(min_gap=5.0)["jump_targets"] == [0.0]


def test_mt05_replay_vacio_no_rompe(replay_sintetico):
    replay_data.events = []
    replay_data.max_time = 0
    r = get_motion_times(min_gap=1.0)
    assert r["motion_times"] == []
    assert r["jump_targets"] == []


def test_mt06_ignora_eventos_que_no_son_de_agente(replay_sintetico):
    replay_data.events = [
        {"type": "work_order_update", "timestamp": 1.0, "id": "WO-1"},
        {"type": "truck_departed", "timestamp": 2.0},
        _evento(3.0, "A", 1, 1),
    ]
    replay_data.max_time = 4.0
    assert get_motion_times(min_gap=1.0)["motion_times"] == [3.0]


def test_mt07_instantes_ordenados(replay_sintetico):
    """El visor hace busqueda binaria: la lista DEBE venir ordenada."""
    replay_data.events = [
        _evento(5.0, "A", 1, 1),
        _evento(1.0, "B", 9, 9),
        _evento(3.0, "A", 2, 2),
    ]
    replay_data.max_time = 6.0
    tiempos = get_motion_times(min_gap=1.0)["motion_times"]
    assert tiempos == sorted(tiempos)
