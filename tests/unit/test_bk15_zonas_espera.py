# -*- coding: utf-8 -*-
"""
BK-15 (C4): el operario sin trabajo nunca estorba (decision del Director).

Espera en una celda de espera (configurada en `zonas_espera` o elegida por el
simulador) que reserva SIN FIN: los demas lo rodean. Una celda de espera nunca
es un punto de pick, una descarga, un muelle, sus accesos, la boca de un
pasillo, ni una celda que corte el paso.
"""
import os
import shutil

from core.config_schema import validate_config_schema
from subsystems.simulation.idle_zones import GestorZonasEspera

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Mini almacen 9x5: corredor abajo (y=4) con descarga en (4,4); pasillos de
# pick en x=1 y x=6 (y=0..2); racks en el resto de y=0..2; corredor y=3.
#   y=0  .p####p..
#   y=1  .p####p..
#   y=2  .p####p..
#   y=3  .........
#   y=4  ....S....
RACKS = {(x, y) for y in range(3) for x in (2, 3, 4, 5)}
PICKS = [(1, y) for y in range(3)] + [(6, y) for y in range(3)]
DESCARGA = [(4, 4)]


def transitable(x, y):
    return 0 <= x < 9 and 0 <= y < 5 and (x, y) not in RACKS


def _gestor(config=None, n=2):
    return GestorZonasEspera(config or {}, transitable, 9, 5, PICKS, DESCARGA, [], n)


def test_ze01_reglas_de_celda_invalida():
    g = _gestor()
    assert g.motivo_invalida((2, 0)) == "no es una celda transitable del mapa"
    assert g.motivo_invalida((1, 1)) == "es un punto de pick"
    assert g.motivo_invalida((4, 4)) == "es una zona de descarga o un muelle"
    assert g.motivo_invalida((4, 3)) == "es el acceso a una zona de descarga o a un muelle"
    assert g.motivo_invalida((1, 3)) == "es la boca de un pasillo de picking"
    assert g.motivo_invalida((0, 4)) is None


def test_ze02_automaticas_de_borde_cerca_de_la_descarga_y_sin_cortar_el_paso():
    g = _gestor(n=2)
    assert g.automatica
    assert len(g.celdas) == 4                      # 2 agentes + 2 de margen
    for c in g.celdas:
        assert g.motivo_invalida(c) is None
    # la mas cercana a la descarga de las de borde de la fila de abajo
    assert g.celdas[0] in {(2, 4), (6, 4)}


def test_ze03_configuradas_descartan_celdas_invalidas_con_aviso():
    g = _gestor({'zonas_espera': {'Z': {'x': 3, 'y': 4, 'ancho': 3, 'alto': 1}}})
    assert not g.automatica
    assert g.celdas == []                          # (3,4),(5,4) accesos; (4,4) descarga
    assert any("acceso" in a for a in g.avisos)
    g = _gestor({'zonas_espera': {'Z': {'x': 7, 'y': 4, 'ancho': 2}}})
    assert g.celdas == [(7, 4), (8, 4)]


def test_ze04_una_celda_que_corta_el_paso_se_descarta():
    g = _gestor()
    criticas = set(PICKS) | set(DESCARGA)
    fila_3 = [(x, 3) for x in range(9)]
    # Ocupar TODA la fila 3 separa los pasillos de pick de la descarga.
    assert not g._conectadas(criticas, set(fila_3))
    # Si se piden como zona de espera, se aceptan solo las que no cortan.
    g.automatica = False
    aceptadas = g._sin_cortar_el_mapa(fila_3)
    assert 0 < len(aceptadas) < len(fila_3)
    assert g._conectadas(criticas, set(aceptadas))
    assert any("incomunicada" in a for a in g.avisos)


def test_ze05_asigna_la_libre_mas_cercana_y_libera():
    g = _gestor({'zonas_espera': {'Z': {'x': 7, 'y': 4, 'ancho': 2}}})
    assert g.asignar('A', (8, 3)) == (8, 4)
    assert g.asignar('B', (8, 3)) == (7, 4)       # la cercana ya esta tomada
    assert g.asignar('C', (8, 3)) is None         # no quedan celdas
    assert g.asignar('A', (0, 0)) == (8, 4)       # mantiene la suya
    g.liberar('A')
    assert g.asignar('C', (0, 0)) == (8, 4)


def test_ze06_esquema_registra_zonas_espera():
    errores, avisos = validate_config_schema(
        {'zonas_espera': {'Z': {'x': 1, 'y': 2, 'techo': True}}})
    assert errores == []
    assert "clave DESCONOCIDA: 'zonas_espera.Z.techo'" in avisos
    assert not any("'zonas_espera'" in a for a in avisos)


def test_ze07_web_valida_las_zonas_contra_el_mapa_real(tmp_path):
    import json
    from web_prototype.config_manager import WebConfigurationManager
    (tmp_path / "layouts").mkdir()
    for nombre in ("Warehouse_Logic.xlsx", "WH1.tmx"):
        shutil.copy2(os.path.join(PROJECT_ROOT, "layouts", nombre), tmp_path / "layouts" / nombre)
    shutil.copy2(os.path.join(PROJECT_ROOT, "warehouse.db"), tmp_path / "warehouse.db")
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    manager = WebConfigurationManager(str(tmp_path))
    cfg["zonas_espera"] = {"Z": {"x": 5, "y": 29}}
    ok, errores = manager.validate_config(cfg)
    assert ok, errores
    cfg["zonas_espera"] = {"Z": {"x": 3, "y": 28}}   # acceso a la descarga 1
    ok, errores = manager.validate_config(cfg)
    assert not ok and any("acceso" in e for e in errores)
