# -*- coding: utf-8 -*-
"""
QA bloque 10.
  H-44: "Default" usa config_default.json (valores de fabrica) y ese archivo
        tiene que ser COHERENTE con los datos del proyecto (antes era un dict
        viejo con el mapa WH1 de 30x30 y el Excel anterior).
  H-45: "Abrir Visor" abre la ultima corrida (/api/replays/latest).
"""
import json
import os
import tempfile
import time

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT = os.path.join(RAIZ, 'config_default.json')


def test_default_lee_el_archivo_de_fabrica():
    from web_prototype.config_manager import WebConfigurationManager
    cfg = WebConfigurationManager(RAIZ)._get_default_config()
    assert cfg == json.load(open(DEFAULT, encoding='utf-8'))


def test_config_default_es_coherente_con_los_datos():
    from web_prototype.config_manager import WebConfigurationManager
    from web_prototype.routers.master_data import _validar_excel, validar_tmx
    cfg = json.load(open(DEFAULT, encoding='utf-8'))
    mapa = os.path.join(RAIZ, cfg['layout_file'])
    excel = os.path.join(RAIZ, cfg['sequence_file'])
    assert os.path.exists(mapa), cfg['layout_file']
    assert os.path.exists(excel), cfg['sequence_file']
    ok, errores = WebConfigurationManager(RAIZ).validate_config(cfg)
    assert ok, errores
    r = _validar_excel(excel, mapa)                 # el Excel encaja en el mapa
    assert r['valido'], r['errores']
    assert validar_tmx(mapa)['valido']


def test_ultima_corrida(monkeypatch):
    from web_prototype.routers import replay as rutas
    raiz = tempfile.mkdtemp()
    monkeypatch.setattr(rutas, 'PROJECT_ROOT', raiz)
    assert rutas.ultima_corrida() == {'disponible': False}
    for i, nombre in enumerate(('simulation_1', 'simulation_2')):
        d = os.path.join(raiz, 'output', nombre)
        os.makedirs(d)
        ruta = os.path.join(d, 'replay_%d.jsonl' % i)
        open(ruta, 'w').write('{}')
        os.utime(ruta, (time.time() + i * 10, time.time() + i * 10))
    r = rutas.ultima_corrida()
    assert r['disponible'] and r['replay'] == 'output/simulation_2/replay_1.jsonl'
