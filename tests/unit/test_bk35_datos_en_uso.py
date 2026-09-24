# -*- coding: utf-8 -*-
"""
BK-35: la pestana Layout y Datos muestra lo que usa el SIMULADOR (la base),
no el Excel sin aplicar.
  1. "Cargar Work Areas" lee las areas de la base y avisa si el Excel trae otras.
  2. Tabla de stock inicial por ubicacion (la foto con la que arranca cada corrida).
  3. El aviso "el Excel es mas nuevo" compara con la fecha de APLICACION, no con
     la de la base (cada corrida escribe en ella).
"""
import os
import sqlite3
import tempfile

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
XLSX = os.path.join(RAIZ, 'layouts', 'Warehouse_Logic_v3.xlsx')


def _base(areas=('Area_Ground',), foto=None):
    ruta = os.path.join(tempfile.mkdtemp(), 'wh.db')
    c = sqlite3.connect(ruta)
    c.execute("CREATE TABLE locations (location_id TEXT, work_area TEXT, legacy_x INT, legacy_y INT)")
    c.execute("CREATE TABLE inventory (location_id TEXT, sku_code TEXT, qty_available INT, "
              "qty_reserved INT, last_updated REAL)")
    for i, a in enumerate(areas):
        c.execute("INSERT INTO locations VALUES (?, ?, 1, ?)", ('LOC-%03d' % i, a, i))
        c.execute("INSERT INTO inventory VALUES (?, 'SKU001', 0, 0, NULL)", ('LOC-%03d' % i,))
    if foto is not None:
        c.execute("CREATE TABLE inventory_baseline (location_id TEXT PRIMARY KEY, qty_baseline INT)")
        c.executemany("INSERT INTO inventory_baseline VALUES (?, ?)", foto)
    c.commit(); c.close()
    return ruta


@pytest.mark.skipif(not os.path.exists(XLSX), reason='sin Excel v3')
def test_las_areas_salen_de_la_base_y_avisan_diferencias():
    from web_prototype.config_manager import WebConfigurationManager
    m = WebConfigurationManager(RAIZ)
    db = _base(('Area_Ground', 'Area_Frio'))
    areas, origen, avisos = m.work_areas_en_uso(XLSX, db)
    assert origen == 'base' and areas == ['Area_Frio', 'Area_Ground']
    assert any('todavia no se aplicaron' in a and 'Area_High' in a for a in avisos)
    assert any('ya no trae' in a and 'Area_Frio' in a for a in avisos)
    # sin base: el Excel
    areas, origen, _ = m.work_areas_en_uso(XLSX, os.path.join(tempfile.mkdtemp(), 'no.db'))
    assert origen == 'excel' and 'Area_High' in areas


def test_la_tabla_de_stock_muestra_el_stock_inicial(monkeypatch):
    from web_prototype.routers import master_data as md
    db = _base(('Area_Ground', 'Area_High'), foto=[('LOC-000', 63), ('LOC-001', 97)])
    monkeypatch.setattr(md, 'DB_PATH', db)
    r = md.leer_tabla('stock', limit=10)
    assert r['total'] == 2
    # inventory quedo en 0 tras una corrida; se muestra la foto de arranque
    assert [f['stock_inicial'] for f in r['filas']] == [63, 97]
    assert md.leer_tabla('stock', q='Area_High')['total'] == 1


def test_el_aviso_de_excel_nuevo_usa_la_fecha_de_aplicacion(monkeypatch):
    from web_prototype.routers import master_data as md
    db = _base()
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE master_data_meta (clave TEXT PRIMARY KEY, valor TEXT)")
    c.execute("INSERT INTO master_data_meta VALUES ('aplicado_en', '100.0')")
    c.commit(); c.close()
    monkeypatch.setattr(md, 'DB_PATH', db)
    info = md._resumen_bd()
    assert info['aplicado_en'] == 100.0
    assert info['actualizada'] > 100.0          # la base se toco despues (una corrida)


@pytest.mark.skipif(not os.path.exists(XLSX), reason='sin Excel v3')
def test_el_importador_registra_cuando_se_aplico():
    import shutil
    from subsystems.database.importer import import_warehouse_data
    from subsystems.database.database_manager import DatabaseManager
    tmp = os.path.join(tempfile.mkdtemp(), 'wh.db')
    shutil.copy2(os.path.join(RAIZ, 'warehouse.db'), tmp)
    try:
        assert import_warehouse_data(XLSX, db_path=tmp).success
    finally:
        DatabaseManager.reset_instance()
    meta = dict(sqlite3.connect(tmp).execute("SELECT clave, valor FROM master_data_meta"))
    assert float(meta['aplicado_en']) > 0
    assert meta['excel'].endswith('Warehouse_Logic_v3.xlsx')
