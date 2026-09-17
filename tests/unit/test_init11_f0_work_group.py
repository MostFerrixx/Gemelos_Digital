# -*- coding: utf-8 -*-
"""
INIT-11 F0 / BK-12: el Work Group de una WorkOrder sale del DATO REAL de la
ubicacion (Excel/DB), no de una derivacion por nombre del area.

Antes, con el canonico, Area_High y Area_Special quedaban en WG_A aunque el
Excel dice WG_B y WG_C. La derivacion por nombre queda solo como respaldo.
"""
from types import SimpleNamespace

from subsystems.simulation.warehouse import AlmacenMejorado, SKU, WorkOrder


def _almacen(puntos):
    alm = object.__new__(AlmacenMejorado)
    alm.data_manager = SimpleNamespace(puntos_de_picking_ordenados=puntos)
    return alm


PUNTOS = [
    {'x': 1, 'y': 2, 'WorkArea': 'Area_Ground', 'WorkGroup': 'WG_A', 'location_id': 'L1'},
    {'x': 3, 'y': 4, 'WorkArea': 'Area_High', 'WorkGroup': 'WG_B', 'location_id': 'L2'},
    {'x': 5, 'y': 6, 'WorkArea': 'Area_Special', 'WorkGroup': 'WG_C'},
    {'x': 7, 'y': 8, 'WorkArea': 'Area_Ground', 'WorkGroup': 'WG_Default', 'location_id': 'L4'},
]


def _wo(work_area, work_group=None):
    return WorkOrder('WO-1', 'ORD-1', 'T-1', SKU('S1', 1), 1, (0, 0),
                     work_area, 1, work_group=work_group)


def test_wg01_busca_por_location_id():
    assert _almacen(PUNTOS)._obtener_work_group(None, None, 'L2') == 'WG_B'


def test_wg02_busca_por_coordenada_y_area():
    alm = _almacen(PUNTOS)
    assert alm._obtener_work_group((5, 6), 'Area_Special') == 'WG_C'
    # misma coordenada con otra area no coincide
    assert alm._obtener_work_group((5, 6), 'Area_Ground') is None


def test_wg03_location_id_desconocido_cae_a_coordenada():
    alm = _almacen(PUNTOS)
    assert alm._obtener_work_group((3, 4), 'Area_High', 'NO_EXISTE') == 'WG_B'


def test_wg04_sin_dato_o_placeholder_devuelve_none():
    alm = _almacen(PUNTOS)
    assert alm._obtener_work_group((9, 9), 'Area_Ground') is None
    # WG_Default es el relleno del migrador cuando el Excel no trae grupo
    assert alm._obtener_work_group(None, None, 'L4') is None
    assert _almacen(None)._obtener_work_group((1, 2), 'Area_Ground') is None


def test_wg05_la_orden_usa_el_grupo_real():
    assert _wo('Area_High', 'WG_B').work_group == 'WG_B'


def test_wg06_sin_grupo_real_usa_el_respaldo_por_nombre():
    assert _wo('Area_Ground').work_group == 'WG_A'
    assert _wo('Zona_Piso').work_group == 'WG_B'
    assert _wo('Rack_Alto').work_group == 'WG_C'
    assert _wo('Area_High').work_group == 'WG_A'
    assert _wo(None).work_group == 'WG_A'


def test_wg07_work_group_no_entra_en_to_dict():
    """initial_work_orders de la metadata no cambia de forma."""
    assert 'work_group' not in _wo('Area_High', 'WG_B').to_dict()
