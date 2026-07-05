# -*- coding: utf-8 -*-
"""
INIT-1: la ubicacion de picking de una WO en modo Stochastic debe corresponder
al SKU real que la WO transporta (sku_initial del punto de picking), no a un
round-robin ciego sobre todos los puntos.

Se instancia AlmacenMejorado sin __init__ (igual que test_warehouse_cantidades.py):
generate_work_orders solo necesita los atributos/metodos usados abajo.
"""
from subsystems.simulation.order_strategies import StochasticOrderStrategy
from subsystems.simulation.warehouse import SKU, AlmacenMejorado


class FakeDataManager:
    def __init__(self, puntos):
        self.puntos_de_picking_ordenados = puntos


def _almacen(puntos, catalogo_skus, total_ordenes=10):
    alm = object.__new__(AlmacenMejorado)
    alm.operator_capacities = {}
    alm.max_operator_capacity = 150
    alm.outbound_staging_distribution = {"1": 100}
    alm.total_ordenes = total_ordenes
    alm.distribucion_tipos = {"pequeno": {"porcentaje": 100, "volumen": 5}}
    alm.catalogo_skus = catalogo_skus
    alm.data_manager = FakeDataManager(puntos)
    return alm


def test_init1_wo_va_a_ubicacion_real_del_sku():
    """Con un solo SKU en el catalogo y su unico punto de picking real,
    TODAS las WOs generadas deben usar esa ubicacion -- no la del otro punto
    (que pertenece a un SKU distinto)."""
    catalogo = {"SKU-PEQ-001": SKU("SKU-PEQ-001", volumen=5)}
    puntos = [
        {"ubicacion_grilla": (1, 1), "WorkArea": "Area_Ground",
         "pick_sequence": 1, "sku_initial": "SKU-PEQ-001", "qty_initial": 100},
        {"ubicacion_grilla": (99, 99), "WorkArea": "Area_High",
         "pick_sequence": 2, "sku_initial": "SKU-OTHER-999", "qty_initial": 100},
    ]
    alm = _almacen(puntos, catalogo, total_ordenes=15)

    wos = StochasticOrderStrategy().generate_work_orders(alm)

    assert len(wos) > 0
    for wo in wos:
        assert wo.ubicacion == (1, 1), (
            "WO %s fue a %s, deberia ir a (1,1) (unico punto real del SKU)"
            % (wo.work_order_id, wo.ubicacion)
        )
        assert wo.work_area == "Area_Ground"
        assert wo.pick_sequence == 1


def test_init1_multiples_puntos_del_mismo_sku_son_todos_validos():
    """Si un SKU tiene mas de un punto de picking real, cualquiera de esos
    puntos es un resultado valido (nunca el de otro SKU)."""
    catalogo = {"SKU-PEQ-001": SKU("SKU-PEQ-001", volumen=5)}
    puntos = [
        {"ubicacion_grilla": (1, 1), "WorkArea": "Area_Ground",
         "pick_sequence": 1, "sku_initial": "SKU-PEQ-001", "qty_initial": 50},
        {"ubicacion_grilla": (2, 2), "WorkArea": "Area_Ground",
         "pick_sequence": 2, "sku_initial": "SKU-PEQ-001", "qty_initial": 50},
        {"ubicacion_grilla": (99, 99), "WorkArea": "Area_High",
         "pick_sequence": 3, "sku_initial": "SKU-OTHER-999", "qty_initial": 100},
    ]
    alm = _almacen(puntos, catalogo, total_ordenes=20)

    wos = StochasticOrderStrategy().generate_work_orders(alm)

    valid_locations = {(1, 1), (2, 2)}
    assert len(wos) > 0
    for wo in wos:
        assert wo.ubicacion in valid_locations


def test_init1_fallback_si_sku_no_tiene_punto_real():
    """Si el catalogo tiene un SKU sin ningun punto de picking real (dato
    inconsistente), no debe crashear: usa el fallback round-robin existente."""
    catalogo = {"SKU-PEQ-001": SKU("SKU-PEQ-001", volumen=5)}
    puntos = [
        {"ubicacion_grilla": (5, 5), "WorkArea": "Area_Ground",
         "pick_sequence": 1, "sku_initial": "SKU-OTHER-999", "qty_initial": 100},
    ]
    alm = _almacen(puntos, catalogo, total_ordenes=5)

    wos = StochasticOrderStrategy().generate_work_orders(alm)

    assert len(wos) > 0
    for wo in wos:
        assert wo.ubicacion == (5, 5)  # unico punto disponible via fallback
