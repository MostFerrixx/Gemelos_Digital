# -*- coding: utf-8 -*-
"""
INIT-6 Opcion B: destino de negocio (tienda/zona de reparto) -> staging_id,
via destino_staging_map. Orden de precedencia en
AlmacenMejorado._resolver_staging_id(): staging_id explicito > destino
mapeado > fallback aleatorio de siempre (sin regresion si no hay destino).
"""
import json

from subsystems.simulation.order_strategies import DeterministicOrderStrategy, ParsedOrder
from subsystems.simulation.warehouse import AlmacenMejorado


def _almacen(destino_staging_map=None, outbound_staging_distribution=None):
    alm = object.__new__(AlmacenMejorado)
    alm.destino_staging_map = destino_staging_map or {}
    alm.outbound_staging_distribution = outbound_staging_distribution or {
        "1": 100, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0
    }
    return alm


def test_staging_id_explicito_tiene_prioridad_sobre_destino():
    alm = _almacen(destino_staging_map={"TIENDA_NORTE": 5})
    order = ParsedOrder(order_id="ORD-1", staging_id=2, destino="TIENDA_NORTE")
    assert alm._resolver_staging_id(order) == 2


def test_destino_mapeado_resuelve_a_su_staging_id():
    alm = _almacen(destino_staging_map={"TIENDA_NORTE": 5, "TIENDA_SUR": 3})
    order = ParsedOrder(order_id="ORD-1", destino="TIENDA_NORTE")
    assert alm._resolver_staging_id(order) == 5

    order2 = ParsedOrder(order_id="ORD-2", destino="TIENDA_SUR")
    assert alm._resolver_staging_id(order2) == 3


def test_destino_no_mapeado_cae_al_fallback_aleatorio():
    # Distribucion con un solo staging activo -> el fallback es determinista.
    alm = _almacen(destino_staging_map={"TIENDA_NORTE": 5},
                    outbound_staging_distribution={"1": 0, "2": 100, "3": 0,
                                                    "4": 0, "5": 0, "6": 0, "7": 0})
    order = ParsedOrder(order_id="ORD-1", destino="DESTINO_DESCONOCIDO")
    assert alm._resolver_staging_id(order) == 2


def test_sin_destino_ni_staging_id_cae_al_fallback_aleatorio_sin_regresion():
    alm = _almacen(destino_staging_map={"TIENDA_NORTE": 5},
                    outbound_staging_distribution={"1": 0, "2": 0, "3": 100,
                                                    "4": 0, "5": 0, "6": 0, "7": 0})
    order = ParsedOrder(order_id="ORD-1")
    assert alm._resolver_staging_id(order) == 3


def test_valor_no_numerico_en_el_mapa_no_crashea_cae_al_fallback():
    """REVIEW 2026-07-06: config editado a mano con staging_id no numerico
    ("tres") no debe crashear la generacion de pedidos -- WARN + fallback."""
    alm = _almacen(destino_staging_map={"TIENDA_NORTE": "tres"},
                    outbound_staging_distribution={"1": 0, "2": 100, "3": 0,
                                                    "4": 0, "5": 0, "6": 0, "7": 0})
    order = ParsedOrder(order_id="ORD-1", destino="TIENDA_NORTE")
    assert alm._resolver_staging_id(order) == 2  # fallback determinista

    # Un valor numerico como string SI debe aceptarse (JSON a mano con "5").
    alm2 = _almacen(destino_staging_map={"TIENDA_NORTE": "5"})
    order2 = ParsedOrder(order_id="ORD-2", destino="TIENDA_NORTE")
    assert alm2._resolver_staging_id(order2) == 5


def test_parseo_json_lee_campo_destino(tmp_path):
    orders_file = tmp_path / "orders.json"
    orders_file.write_text(json.dumps({
        "orders": [
            {"order_id": "ORD-1", "destino": "TIENDA_NORTE",
             "items": [{"sku_id": "SKU001", "quantity": 2}]},
            {"order_id": "ORD-2",
             "items": [{"sku_id": "SKU002", "quantity": 1}]},
        ]
    }), encoding="utf-8")

    strategy = DeterministicOrderStrategy(str(orders_file), fulfillment_policy="ship_partial")
    strategy._parse_json()

    by_id = {o.order_id: o for o in strategy.parsed_orders}
    assert by_id["ORD-1"].destino == "TIENDA_NORTE"
    assert by_id["ORD-2"].destino is None


def test_parseo_csv_lee_campo_destino(tmp_path):
    orders_file = tmp_path / "orders.csv"
    orders_file.write_text(
        "order_id,sku_id,quantity,destino\n"
        "ORD-1,SKU001,2,TIENDA_SUR\n"
        "ORD-2,SKU002,1,\n",
        encoding="utf-8",
    )

    strategy = DeterministicOrderStrategy(str(orders_file), fulfillment_policy="ship_partial")
    strategy._parse_csv()

    by_id = {o.order_id: o for o in strategy.parsed_orders}
    assert by_id["ORD-1"].destino == "TIENDA_SUR"
    assert by_id["ORD-2"].destino is None
