# -*- coding: utf-8 -*-
"""
BK-36 (decision del Director 2026-09-25): guardar una configuracion replica
todo lo necesario (mapa + dependencias, base en uso, Excel, pedidos, ASN) y
cargarla la deja TAL CUAL se guardo. Ademas, ninguna configuracion valida si
su mapa no encaja con la base que va a usar el motor.
"""
import json
import os
import shutil
import sqlite3

import pytest

from web_prototype import replicas
from web_prototype.config_manager import WebConfigurationManager

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAPA_V3 = os.path.join(RAIZ, 'layouts', 'WH1 v3.tmx')


def _proyecto(tmp_path):
    if not (os.path.exists(MAPA_V3) and os.path.exists(os.path.join(RAIZ, 'warehouse.db'))):
        pytest.skip('sin mapa v3 o sin base')
    cfg = json.load(open(os.path.join(RAIZ, 'config.json'), encoding='utf-8'))
    (tmp_path / 'layouts').mkdir()
    for nombre in (os.path.basename(cfg['layout_file']), os.path.basename(cfg['sequence_file']),
                   'custom_warehouse_tileset.png'):
        shutil.copy2(os.path.join(RAIZ, 'layouts', nombre), tmp_path / 'layouts' / nombre)
    replicas._copiar_base(os.path.join(RAIZ, 'warehouse.db'), str(tmp_path / 'warehouse.db'))
    (tmp_path / 'uploads').mkdir()
    (tmp_path / 'uploads' / 'pedidos.csv').write_text('order_id,sku_id,quantity\nA,SKU001,1\n')
    cfg['order_file_path'] = 'uploads/pedidos.csv'
    json.dump(cfg, open(tmp_path / 'config.json', 'w', encoding='utf-8'), indent=2)
    return WebConfigurationManager(str(tmp_path)), cfg


def _stock(db):
    return sqlite3.connect(db).execute("SELECT sum(qty_available) FROM inventory").fetchone()[0]


def test_el_mapa_declara_su_imagen_como_dependencia():
    if not os.path.exists(MAPA_V3):
        pytest.skip('sin mapa v3')
    assert 'custom_warehouse_tileset.png' in replicas.dependencias_tmx(MAPA_V3)


def test_guardar_replica_y_cargar_tal_cual(tmp_path):
    m, cfg = _proyecto(tmp_path)
    ok, pid, errores = m.save_configuration('prueba', '', cfg)
    assert ok, errores
    carpeta = tmp_path / 'data' / 'config_presets' / pid
    assert (carpeta / 'mapa' / 'WH1 v3.tmx').exists()
    assert (carpeta / 'mapa' / 'custom_warehouse_tileset.png').exists()
    assert (carpeta / 'datos' / 'warehouse.db').exists()
    assert (carpeta / 'archivos' / 'pedidos.csv').exists()
    stock_guardado = _stock(str(tmp_path / 'warehouse.db'))

    # despues de guardar cambian los datos en uso (otro Excel, una corrida...)
    c = sqlite3.connect(str(tmp_path / 'warehouse.db'))
    c.execute("UPDATE inventory SET qty_available = 0"); c.commit(); c.close()

    config, respaldo, avisos = m.cargar_con_replica(pid)
    assert _stock(str(tmp_path / 'warehouse.db')) == stock_guardado    # datos restaurados
    assert respaldo == 'warehouse.db.bak'
    assert _stock(str(tmp_path / 'warehouse.db.bak')) == 0            # los de antes, respaldados
    assert config['layout_file'].startswith('data/config_presets/%s/mapa/' % pid)
    assert config['order_file_path'].endswith('/archivos/pedidos.csv')
    assert avisos == []
    ok, errores = m.validate_config(config)                          # corre con su mapa
    assert ok, errores


def test_una_copia_modificada_avisa(tmp_path):
    m, cfg = _proyecto(tmp_path)
    ok, pid, _ = m.save_configuration('prueba', '', cfg)
    copia = tmp_path / 'data' / 'config_presets' / pid / 'archivos' / 'pedidos.csv'
    copia.write_text('otra cosa')
    _, _, avisos = m.cargar_con_replica(pid)
    assert any('cambio' in a and 'order_file_path' in a for a in avisos)


def test_experimento_usa_una_copia_descartable_de_la_base(tmp_path):
    m, cfg = _proyecto(tmp_path)
    ok, pid, _ = m.save_configuration('prueba', '', cfg)
    config = m.config_para_experimento(pid, str(tmp_path / 'temp_web'))
    assert config['database_file'].startswith('temp_web/replica_')
    assert os.path.exists(tmp_path / config['database_file'])


def test_borrar_elimina_la_replica(tmp_path):
    m, cfg = _proyecto(tmp_path)
    ok, pid, _ = m.save_configuration('prueba', '', cfg)
    assert m.delete_configuration(pid)[0]
    assert not (tmp_path / 'data' / 'config_presets' / pid).exists()


def test_un_mapa_que_no_encaja_con_la_base_no_valida(tmp_path):
    m, cfg = _proyecto(tmp_path)
    v2 = os.path.join(RAIZ, 'layouts', 'WH1 v2.tmx')
    if not os.path.exists(v2):
        pytest.skip('sin WH1 v2')
    shutil.copy2(v2, tmp_path / 'layouts' / 'WH1 v2.tmx')
    cfg = dict(cfg, layout_file='layouts/WH1 v2.tmx')     # 2 columnas mas angosto
    ok, errores = m.validate_config(cfg)
    assert not ok and any('FUERA' in e for e in errores)


def test_no_se_borra_una_replica_en_uso(tmp_path):
    m, cfg = _proyecto(tmp_path)
    ok, pid, _ = m.save_configuration('prueba', '', cfg)
    config, _, _ = m.cargar_con_replica(pid)
    assert m.save_config(config)[0]                 # se aplica: config.json usa la replica
    ok, errores = m.delete_configuration(pid)
    assert not ok and 'usa archivos de esta replica' in errores[0]


def test_h60_aplicar_reemplaza_y_no_deja_claves_viejas(tmp_path):
    """QA H-60: aplicar el canonico despues de otra config dejaba en config.json
    las claves que el canonico no trae (merge). Caso real: `personas` quedaba y
    mandaba sobre la flota; la corrida no era la de la pantalla."""
    cm, cfg = _proyecto(tmp_path)
    otra = dict(cfg, waves={'enabled': True, 'release_times': {'W1': 0}},
                priority_dispatch_enabled=True)
    ok, err = cm.save_config(otra)
    assert ok, err
    ok, err = cm.save_config(cfg)
    assert ok, err
    vigente = json.load(open(tmp_path / 'config.json', encoding='utf-8'))
    assert 'waves' not in vigente and 'priority_dispatch_enabled' not in vigente
    assert cm.ultimas_quitadas == ['priority_dispatch_enabled', 'waves']
    assert vigente == cfg


def test_h60_aplicar_sin_cambios_deja_el_archivo_igual(tmp_path):
    """Reemplazar no debe reordenar: el orden de claves viaja en la metadata
    del .jsonl (gate byte-identico) y ensucia los diffs de git."""
    cm, cfg = _proyecto(tmp_path)
    ok, err = cm.save_config(cfg)
    assert ok, err
    antes = open(tmp_path / 'config.json', 'rb').read()
    desordenada = dict(reversed(list(cfg.items())))
    ok, err = cm.save_config(desordenada)
    assert ok, err
    assert open(tmp_path / 'config.json', 'rb').read() == antes
