# -*- coding: utf-8 -*-
"""
MEJ-1 / WH-xx: caracterizacion de warehouse._validar_y_ajustar_cantidad
(division de una orden en multiples WOs por capacidad del operario).

Se instancia AlmacenMejorado sin __init__ (el metodo solo usa
operator_capacities y max_operator_capacity).
"""
from subsystems.simulation.warehouse import SKU, AlmacenMejorado


def _almacen(operator_capacities=None, max_capacity=150):
    alm = object.__new__(AlmacenMejorado)
    alm.operator_capacities = operator_capacities or {}
    alm.max_operator_capacity = max_capacity
    return alm


def test_wh01_cabe_en_un_viaje():
    alm = _almacen(max_capacity=150)
    sku = SKU("SKU-T1", volumen=5)
    assert alm._validar_y_ajustar_cantidad(sku, 4, "Area_Ground") == [4]  # 20 <= 150


def test_wh01b_borde_exacto_un_viaje():
    alm = _almacen(max_capacity=150)
    sku = SKU("SKU-T2", volumen=30)
    assert alm._validar_y_ajustar_cantidad(sku, 5, "Area_Ground") == [5]  # 150 == 150


def test_wh02_divide_en_multiples_viajes():
    alm = _almacen(max_capacity=150)
    sku = SKU("SKU-T3", volumen=80)  # 150 // 80 = 1 unidad por viaje
    assert alm._validar_y_ajustar_cantidad(sku, 3, "Area_Ground") == [1, 1, 1]


def test_wh03_usa_capacidad_del_area_si_existe():
    alm = _almacen(operator_capacities={"Area_High": 1000}, max_capacity=150)
    sku = SKU("SKU-T4", volumen=80)
    # En Area_High (cap 1000) las 3 unidades (240) caben en un viaje
    assert alm._validar_y_ajustar_cantidad(sku, 3, "Area_High") == [3]


def test_wh04_sku_mas_grande_que_capacidad_no_cuelga():
    """Fix WOs sobredimensionadas: sku.volumen > max_capacity ya no crea WOs
    fantasma (qty=0) ni entra en bucle infinito -- devuelve [] (backorder
    implicito, sin WorkOrder)."""
    alm = _almacen(max_capacity=150)
    sku = SKU("SKU-T5", volumen=200)
    assert alm._validar_y_ajustar_cantidad(sku, 1, "Area_Ground") == []


def test_wh04b_borde_exacto_sku_igual_a_capacidad_no_es_imposible():
    alm = _almacen(max_capacity=150)
    sku = SKU("SKU-T6", volumen=150)
    assert alm._validar_y_ajustar_cantidad(sku, 2, "Area_Ground") == [1, 1]
