# -*- coding: utf-8 -*-
"""
INIT-7 F3 / IN-3x: estrategias de slotting conmutables.

Pinea:
- sku_candidate_locations: solo ubicaciones del propio SKU, orden por
  pick_sequence (coherencia del modelo de inventario: 1 SKU por ubicacion).
- resolve_slotting: fija (menor seq), cercana (Manhattan al muelle real),
  abc (A cerca del staging de salida, C lejos, B fija) + fallbacks
  deterministas cuando faltan datos.
- compute_abc_classes: terciles por demanda, empates deterministas.
"""
from subsystems.simulation.inbound import (
    SLOTTING_STRATEGIES, compute_abc_classes, resolve_slotting,
    sku_candidate_locations,
)

# SKU001 vive en 3 ubicaciones; muelle en (3, 1); staging salida en (3, 29).
PUNTOS = [
    {"sku_initial": "SKU001", "x": 2, "y": 3, "pick_sequence": 5,
     "location_id": "LOC-CERCA-MUELLE", "WorkArea": "Area_Ground"},
    {"sku_initial": "SKU001", "x": 10, "y": 27, "pick_sequence": 1,
     "location_id": "LOC-FIJA", "WorkArea": "Area_Ground"},
    {"sku_initial": "SKU001", "x": 4, "y": 28, "pick_sequence": 9,
     "location_id": "LOC-CERCA-STAGING", "WorkArea": "Area_High"},
    {"sku_initial": "SKU002", "x": 8, "y": 8, "pick_sequence": 2,
     "location_id": "LOC-OTRO", "WorkArea": "Area_Ground"},
]
DOCK = (3, 1)
STAGING = (3, 29)


def test_in30_candidatas_solo_del_sku_y_ordenadas():
    c = sku_candidate_locations("SKU001", PUNTOS)
    assert [x["location_id"] for x in c] == [
        "LOC-FIJA", "LOC-CERCA-MUELLE", "LOC-CERCA-STAGING"]  # por pick_sequence
    assert sku_candidate_locations("SKU999", PUNTOS) == []


def test_in31_fija_por_sku():
    t = resolve_slotting("fija_por_sku", "SKU001", PUNTOS,
                         dock_cell=DOCK, staging_cell=STAGING)
    assert t["location_id"] == "LOC-FIJA"  # menor pick_sequence, ignora muelle


def test_in32_cercana_al_muelle():
    t = resolve_slotting("cercana_al_muelle", "SKU001", PUNTOS, dock_cell=DOCK)
    assert t["location_id"] == "LOC-CERCA-MUELLE"  # Manhattan 3 vs 33 vs 28

    # sin muelle conocido -> fallback determinista a fija
    t2 = resolve_slotting("cercana_al_muelle", "SKU001", PUNTOS, dock_cell=None)
    assert t2["location_id"] == "LOC-FIJA"


def test_in33_abc_rotacion():
    # clase A -> cerca del staging de salida (Manhattan 8 vs 9 vs 3)
    a = resolve_slotting("abc_rotacion", "SKU001", PUNTOS,
                         staging_cell=STAGING, abc_class="A")
    assert a["location_id"] == "LOC-CERCA-STAGING"

    # clase C -> lejos del staging (la de mayor distancia)
    c = resolve_slotting("abc_rotacion", "SKU001", PUNTOS,
                         staging_cell=STAGING, abc_class="C")
    assert c["location_id"] == "LOC-CERCA-MUELLE"  # dist 28, la mayor

    # clase B -> comportamiento fijo
    b = resolve_slotting("abc_rotacion", "SKU001", PUNTOS,
                         staging_cell=STAGING, abc_class="B")
    assert b["location_id"] == "LOC-FIJA"

    # sin staging de referencia -> fallback a fija
    s = resolve_slotting("abc_rotacion", "SKU001", PUNTOS,
                         staging_cell=None, abc_class="A")
    assert s["location_id"] == "LOC-FIJA"


def test_in34_clases_abc_terciles_deterministas():
    demand = {"S1": 100, "S2": 90, "S3": 50, "S4": 40, "S5": 10, "S6": 5}
    classes = compute_abc_classes(demand)
    assert classes == {"S1": "A", "S2": "A", "S3": "B", "S4": "B",
                       "S5": "C", "S6": "C"}

    # empate de demanda -> desempate por sku_id ASC (determinista)
    tie = compute_abc_classes({"SB": 10, "SA": 10, "SC": 10})
    assert tie == {"SA": "A", "SB": "B", "SC": "C"}

    assert compute_abc_classes({}) == {}


def test_in35_estrategias_declaradas():
    assert SLOTTING_STRATEGIES == (
        "fija_por_sku", "cercana_al_muelle", "abc_rotacion")
    # SKU inexistente -> None en cualquier estrategia
    for s in SLOTTING_STRATEGIES:
        assert resolve_slotting(s, "SKU999", PUNTOS, dock_cell=DOCK,
                                staging_cell=STAGING, abc_class="A") is None
