# -*- coding: utf-8 -*-
"""
QA-8.10: el simulador usa warehouse.db como copia de trabajo del stock y la
restaura al arrancar cada corrida desde `inventory_baseline`.

Dos errores medidos:
  1. Solo el modo determinista restauraba: en modo aleatorio el stock que
     sumaba cada putaway quedaba en la base para las corridas siguientes.
  2. "Aplicar Excel" no borraba `inventory_baseline`: la foto seguia siendo
     la del Excel anterior (360 ubicaciones con el v3 de 384) y el stock
     nuevo nunca se usaba.
"""
import os
import shutil
import sqlite3
import tempfile

import pytest

from subsystems.simulation.warehouse import AlmacenMejorado
from subsystems.simulation.order_strategies import StochasticOrderStrategy

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class _Alto(Exception):
    pass


class _DM:
    def __init__(self):
        self.restauraciones = 0

    def restore_inventory_baseline(self):
        self.restauraciones += 1
        return True


def test_la_corrida_aleatoria_restaura_el_stock_antes_de_generar():
    alm = object.__new__(AlmacenMejorado)
    alm.data_manager = _DM()
    estrategia = StochasticOrderStrategy()

    def generar(_almacen):
        assert alm.data_manager.restauraciones == 1      # restaurado ANTES
        raise _Alto()
    estrategia.generate_work_orders = generar
    alm.order_strategy = estrategia
    with pytest.raises(_Alto):
        alm._generar_flujo_ordenes()


def test_aplicar_excel_borra_la_foto_vieja_del_stock():
    excel = os.path.join(PROJECT_ROOT, 'layouts', 'Warehouse_Logic_v3.xlsx')
    base = os.path.join(PROJECT_ROOT, 'warehouse.db')
    if not (os.path.exists(excel) and os.path.exists(base)):
        pytest.skip('sin Excel v3 o sin base')
    from subsystems.database.importer import import_warehouse_data
    from subsystems.database.database_manager import DatabaseManager
    tmp = os.path.join(tempfile.mkdtemp(), 'wh.db')
    shutil.copy2(base, tmp)
    conn = sqlite3.connect(tmp)
    conn.execute("CREATE TABLE IF NOT EXISTS inventory_baseline "
                 "(location_id TEXT PRIMARY KEY, qty_baseline INTEGER NOT NULL)")
    conn.execute("INSERT OR REPLACE INTO inventory_baseline VALUES ('LOC-001', 999999)")
    conn.commit(); conn.close()
    try:
        res = import_warehouse_data(excel, db_path=tmp)
        assert res.success, res.errors
    finally:
        DatabaseManager.reset_instance()
    conn = sqlite3.connect(tmp)
    existe = conn.execute("SELECT count(*) FROM sqlite_master "
                          "WHERE name='inventory_baseline'").fetchone()[0]
    conn.close()
    assert existe == 0
