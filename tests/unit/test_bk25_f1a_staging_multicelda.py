# -*- coding: utf-8 -*-
"""
BK-25 F1.a: una zona de descarga puede tener VARIAS celdas.

La tabla `staging_areas` tenia PRIMARY KEY (staging_id) y el importador usaba
INSERT OR REPLACE: de las 20 celdas de un carril quedaba UNA sola (la ultima,
el fondo del carril). Con el layout WH1 v3, cada carril son 2 columnas x 10
filas y hacen falta todas.
"""
import contextlib
import io
import os
import sqlite3

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXCEL_V3 = os.path.join(PROJECT_ROOT, "layouts", "Warehouse_Logic_v3.xlsx")
EXCEL_CANONICO = os.path.join(PROJECT_ROOT, "layouts", "Warehouse_Logic.xlsx")


def _importar(excel, db_path):
    from subsystems.database.database_manager import DatabaseManager
    from subsystems.database.importer import ExcelImporter
    DatabaseManager.reset_instance()
    db = DatabaseManager.get_instance(db_path)
    with contextlib.redirect_stdout(io.StringIO()):
        db.initialize_schema()
        ExcelImporter(db).import_from_excel(excel)
    DatabaseManager.reset_instance()


def _zonas(db_path):
    con = sqlite3.connect(db_path)
    try:
        filas = con.execute(
            "SELECT staging_id, legacy_x, legacy_y FROM staging_areas ORDER BY rowid").fetchall()
    finally:
        con.close()
    zonas = {}
    for sid, x, y in filas:
        zonas.setdefault(sid, []).append((x, y))
    return zonas


@pytest.mark.skipif(not os.path.exists(EXCEL_V3), reason="falta el Excel del layout v3")
def test_f1a_el_carril_completo_llega_a_la_base(tmp_path):
    db = str(tmp_path / "v3.db")
    _importar(EXCEL_V3, db)
    zonas = _zonas(db)
    assert len(zonas) == 7
    assert all(len(celdas) == 20 for celdas in zonas.values())     # 2 columnas x 10 filas
    assert zonas[1][0] == (3, 30)                                  # el ancla es el FRENTE del carril
    assert (4, 39) in zonas[1]                                     # y el fondo tambien esta


def test_f1a_el_canonico_no_cambia(tmp_path):
    db = str(tmp_path / "canon.db")
    _importar(EXCEL_CANONICO, db)
    zonas = _zonas(db)
    assert len(zonas) == 7
    assert all(len(celdas) == 1 for celdas in zonas.values())
    assert zonas[1][0] == (3, 29)


@pytest.mark.skipif(not os.path.exists(EXCEL_V3), reason="falta el Excel del layout v3")
def test_f1a_una_base_vieja_se_migra_sola(tmp_path):
    """Las bases ya creadas tienen la tabla vieja: CREATE TABLE IF NOT EXISTS no la cambia."""
    db = str(tmp_path / "vieja.db")
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE staging_areas (
            staging_id INTEGER PRIMARY KEY,
            staging_type TEXT DEFAULT 'OUTBOUND',
            legacy_x INTEGER,
            legacy_y INTEGER
        );
        INSERT INTO staging_areas VALUES (1, 'OUTBOUND', 3, 29);
    """)
    con.commit()
    con.close()
    _importar(EXCEL_V3, db)
    zonas = _zonas(db)
    assert len(zonas[1]) == 20
    con = sqlite3.connect(db)
    try:
        sql = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='staging_areas'").fetchone()[0]
    finally:
        con.close()
    assert "PRIMARY KEY (staging_id, legacy_x, legacy_y)" in sql
