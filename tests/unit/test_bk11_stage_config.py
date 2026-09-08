# -*- coding: utf-8 -*-
"""
BK-11: "Run Simulation" ya NO pisa el config.json canonico.

Antes, `startSimulation()` hacia POST /api/configurator/config: escribia el
canonico con lo que tuviera el formulario y recien despues corria. Nadie pedia
guardar, asi que una pestana con estado viejo podia alterar la configuracion del
proyecto en silencio (incidente real: dejo la congestion apagada en el canonico,
626 -> 614 WorkOrders).

Ahora la corrida usa una copia TEMPORAL en temp_web/ y el canonico solo cambia
con "Aplicar Configuracion".
"""
import json
import os

import pytest

from web_prototype.app_state import PROJECT_ROOT
from web_prototype.routers.runners import StageConfigRequest, stage_simulation_config

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")


@pytest.fixture()
def canonico():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def temporales_previos():
    """Limpia los temporales que cree el test (no toca los de otras corridas)."""
    creados = []
    yield creados
    for p in creados:
        try:
            os.remove(p)
        except OSError:
            pass


def _abs(rel):
    return os.path.join(PROJECT_ROOT, rel)


def test_bk11_01_no_toca_el_canonico(canonico, temporales_previos):
    """LA invariante del fix: preparar una corrida NO modifica config.json."""
    with open(CONFIG_PATH, "rb") as f:
        antes = f.read()

    modificado = json.loads(json.dumps(canonico))
    modificado["congestion"]["enabled"] = not canonico["congestion"]["enabled"]
    modificado["total_ordenes"] = 7

    r = stage_simulation_config(StageConfigRequest(config=modificado))
    assert r["success"], r
    temporales_previos.append(_abs(r["config_path"]))

    with open(CONFIG_PATH, "rb") as f:
        despues = f.read()
    assert antes == despues, "stage-config modifico el config.json canonico"


def test_bk11_02_el_temporal_tiene_lo_que_se_mando(canonico, temporales_previos):
    modificado = json.loads(json.dumps(canonico))
    modificado["total_ordenes"] = 123
    modificado["congestion"]["enabled"] = False
    modificado["congestion"]["mode"] = "off"

    r = stage_simulation_config(StageConfigRequest(config=modificado))
    assert r["success"], r
    path = _abs(r["config_path"])
    temporales_previos.append(path)

    with open(path, "r", encoding="utf-8") as f:
        escrito = json.load(f)
    assert escrito["total_ordenes"] == 123
    assert escrito["congestion"]["enabled"] is False

    # ...y el canonico conserva SU valor, distinto del temporal
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        actual = json.load(f)
    assert actual["total_ordenes"] == canonico["total_ordenes"]
    assert actual["congestion"]["enabled"] == canonico["congestion"]["enabled"]


def test_bk11_03_el_temporal_vive_en_temp_web(canonico, temporales_previos):
    """temp_web/ es el temp del PROYECTO (disco D, gitignoreado, purga 24h)."""
    r = stage_simulation_config(StageConfigRequest(config=canonico))
    assert r["success"], r
    rel = r["config_path"]
    temporales_previos.append(_abs(rel))
    assert rel.replace("\\", "/").startswith("temp_web/")
    assert not os.path.isabs(rel), "no exponer rutas absolutas del servidor"


def test_bk11_04_config_invalido_no_corre_y_explica(canonico):
    """Se sigue validando: el error util de antes no se perdio."""
    roto = json.loads(json.dumps(canonico))
    roto["agent_types"] = []
    roto["num_operarios_terrestres"] = 0
    roto["num_montacargas"] = 0

    r = stage_simulation_config(StageConfigRequest(config=roto))
    assert r["success"] is False
    assert r["errors"]
    assert any("flota" in e.lower() for e in r["errors"]), r["errors"]


def test_bk11_05_config_invalido_no_deja_basura(canonico):
    """Si no valida, no se escribe ningun temporal."""
    temp_dir = os.path.join(PROJECT_ROOT, "temp_web")
    antes = set(os.listdir(temp_dir)) if os.path.isdir(temp_dir) else set()

    roto = json.loads(json.dumps(canonico))
    roto["agent_types"] = []
    roto["num_operarios_terrestres"] = 0
    roto["num_montacargas"] = 0
    stage_simulation_config(StageConfigRequest(config=roto))

    despues = set(os.listdir(temp_dir)) if os.path.isdir(temp_dir) else set()
    assert despues == antes, "se creo un temporal para un config invalido"
