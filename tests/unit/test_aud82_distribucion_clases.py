# -*- coding: utf-8 -*-
"""
AUD8-2 (auditoria INIT-8): distribucion_tipos reconectada a las clases de
manejo reales (SKU.clase). El filtro historico por substring del id nunca
matcheaba ('PEQ' in 'SKU001') y la mezcla era uniforme.
"""
import json
import os

from subsystems.simulation.order_strategies import skus_por_clase
from subsystems.simulation.warehouse import SKU

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

CATALOGO = [
    SKU("SKU001", 1, peso=0.2, clase="pequeno"),
    SKU("SKU002", 3, peso=5.0, clase="mediano"),
    SKU("SKU003", 70, peso=80.0, clase="extra_grande"),
    SKU("SKU004", 1, peso=0.3, clase="pequeno"),
]


def test_ad01_filtra_por_clase_real():
    assert [s.id for s in skus_por_clase(CATALOGO, "pequeno")] == ["SKU001", "SKU004"]
    assert [s.id for s in skus_por_clase(CATALOGO, "extra_grande")] == ["SKU003"]
    # clase sin SKUs -> [] (el caller hace fallback + WARN)
    assert skus_por_clase(CATALOGO, "voluminoso") == []
    # SKU legacy sin atributo clase -> cuenta como GENERAL
    class Legacy:
        id = "X"
    legacy = Legacy()
    assert skus_por_clase([legacy], "GENERAL") == [legacy]
    assert skus_por_clase([legacy], "pequeno") == []


def test_ad02_canonico_usa_las_5_clases_y_suma_100():
    with open(os.path.join(PROJECT_ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    dist = cfg["distribucion_tipos"]
    assert set(dist) == {"pequeno", "mediano", "voluminoso", "pesado",
                         "extra_grande"}
    assert sum(v["porcentaje"] for v in dist.values()) == 100
    # el campo 'volumen' DEPRECATED ya no viaja en el canonico
    assert all("volumen" not in v for v in dist.values())
