# -*- coding: utf-8 -*-
"""
BK-25 F1.c: la zona de descarga como estacion con turno.

Reglas del Director: un puesto por columna del carril, entrada por el frente,
salida por SU costado (izquierda para la columna izquierda, derecha para la
derecha) y fila delante de la entrada.
"""
import os

from subsystems.simulation.stations import GestorEstaciones

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Mini mapa 10x12: racks arriba (y<=4), anden y=5..7, carril de 2x4 en x=3..4,
# y=8..11, con pasillos libres a los costados.
CARRIL = [(x, y) for x in (3, 4) for y in range(8, 12)]


def _transitable(x, y):
    return 0 <= x < 10 and 0 <= y < 12 and y > 4


def _gestor(cola_max=1, zonas=None, transitable=None, ancho=10, alto=12):
    return GestorEstaciones(zonas or {1: sorted(CARRIL, key=lambda c: (c[1], c[0]))},
                            transitable or _transitable, ancho, alto, cola_max=cola_max)


def test_f1c_un_puesto_por_columna():
    est = _gestor().estacion(1)
    assert sorted(est.puestos) == [3, 4]
    assert est.celda_de_trabajo(3) == (3, 8)          # el frente de la columna
    assert est.celda_de_trabajo(4) == (4, 8)


def test_f1c_entrada_por_el_frente_y_salida_por_su_costado():
    est = _gestor().estacion(1)
    assert est.entradas == {3: (3, 7), 4: (4, 7)}     # el anden, justo arriba
    assert est.salidas == {3: (2, 8), 4: (5, 8)}      # izquierda la izquierda, derecha la derecha
    assert est.es_salida((2, 8)) and est.es_salida((5, 8))
    assert not est.es_salida((3, 7))


def test_f1c_la_fila_arranca_en_la_entrada_y_se_aleja():
    est = _gestor(cola_max=3).estacion(1)
    assert est.celdas_de_fila(3) == [(3, 7), (3, 6), (3, 5)]
    assert est.celdas_de_fila(4)[0] == (4, 7)


def test_f1c_los_turnos_son_dos_y_se_liberan():
    est = _gestor().estacion(1)
    assert est.tomar('A') == 3
    assert est.tomar('B') == 4
    assert est.tomar('C') is None                     # no hay tercer puesto
    assert est.puesto_de('A') == 3
    assert est.liberar('A') == 3
    assert est.tomar('C') == 3


def test_f1c_zona_sin_salida_lateral_avisa():
    """Racks pegados a los dos costados: no hay salida posible."""
    def encerrado(x, y):
        return _transitable(x, y) and not (x in (2, 5) and y >= 8)
    g = _gestor(transitable=encerrado)
    avisos = g.resumen()['avisos']
    assert any('no tiene salida lateral' in a for a in avisos)


def test_f1c_geometria_real_del_layout_v3():
    """Sobre el mapa real: 7 carriles de 2 columnas, entrada en la fila 29."""
    import json
    from subsystems.simulation.layout_manager import LayoutManager
    import contextlib, io
    ruta = os.path.join(PROJECT_ROOT, 'layouts', 'WH1 v3.tmx')
    if not os.path.exists(ruta):
        return
    with contextlib.redirect_stdout(io.StringIO()):
        lm = LayoutManager(ruta, headless=True)
    zonas = {}
    for sid, x0 in enumerate(range(3, 29, 4), start=1):
        zonas[sid] = [(x, y) for y in range(30, 40) for x in (x0, x0 + 1)]
    g = GestorEstaciones(zonas, lm.is_walkable, lm.grid_width, lm.grid_height, cola_max=1)
    est = g.estacion(1)
    assert sorted(est.puestos) == [3, 4]
    assert est.entradas == {3: (3, 29), 4: (4, 29)}   # el anden nuevo
    assert est.salidas == {3: (2, 30), 4: (5, 30)}
    assert g.resumen()['puestos_totales'] == 14       # 7 carriles x 2
    assert not g.resumen()['avisos']
