# -*- coding: utf-8 -*-
"""
INIT-7 F2 / IN-2x: putaway (muelle -> ubicacion).

Pinea:
- build_stochastic_schedule: agenda FINITA, reproducible bajo seed.
- resolve_target_fija_por_sku: menor pick_sequence, None si SKU desconocido.
- Dispatcher: WOs putaway van a su cola propia (no contaminan pools de pick)
  pero SI cuentan en lista_maestra (terminacion las espera).
- _asignar_putaway: inelegible hasta pallet_ready; FIFO por tiempo listo;
  filtro de work_area (equipamiento); estructura del tour; 1 pallet por viaje.
- Terminacion: no acaba con putaway pendiente; acaba al completarlo.
"""
import random

import pytest

from subsystems.simulation.inbound import (
    build_stochastic_schedule, resolve_target_fija_por_sku,
)


class FakeAlmacenMin:
    """Solo lo que tocan _marcar_asignados / notificar_completado_individual."""

    def __init__(self, env):
        self.env = env
        self.eventos = []
        self.contador = 0

    def registrar_evento(self, tipo, datos):
        self.eventos.append((tipo, datos))

    def incrementar_contador_workorders(self):
        self.contador += 1


class PutawayOperator:
    """Operario minimo para _asignar_putaway."""

    def __init__(self, areas=("Area_Ground",), operator_id="OP-1"):
        self.type = "GroundOperator"
        self.id = operator_id
        self.current_position = (0, 0)
        self._areas = set(areas)

    def get_priority_for_work_area(self, work_area):
        return 1 if work_area in self._areas else 999


def _wo_putaway(make_wo, wo_id, work_area="Area_Ground", ready_at=None):
    wo = make_wo(work_area=work_area)
    wo.id = wo_id
    wo.task_type = 'putaway'
    wo.pallet_id = "INP-" + wo_id
    wo.dock_id = 1
    wo.pallet_ready = ready_at is not None
    wo.tiempo_pallet_listo = ready_at
    wo.target_location = (5, 5)
    wo.status = "released"
    wo.assigned_agent_id = None
    wo.cantidad_total = 10
    wo.cantidad_restante = 10
    wo.cantidad_inicial = 10
    wo.order_id = "TRUCK-X"
    wo.tour_id = "PUTAWAY"
    wo.sku_id = "SKU001"
    wo.sku_name = "SKU001"
    wo.staging_id = 1
    wo.work_group = "WG_A"
    wo.location_id = "LOC-001"
    wo.volumen_restante = 10
    wo.tiempo_inicio = None
    wo.tiempo_fin = None
    return wo


# ---------------------------------------------------------------------------
# Agenda estocastica y slotting
# ---------------------------------------------------------------------------

def test_in20_agenda_estocastica_finita_y_reproducible():
    cfg = {"truck_interval": 100.0, "pallets_per_truck": 3,
           "units_per_pallet": 15, "num_trucks": 4}
    catalog = {"SKU00%d" % i: {} for i in range(1, 6)}

    random.seed(7)
    a = build_stochastic_schedule(cfg, catalog)
    random.seed(7)
    b = build_stochastic_schedule(cfg, catalog)

    assert a == b  # reproducible
    assert len(a) == 4  # FINITA (num_trucks)
    assert [t["arrival_time"] for t in a] == [100.0, 200.0, 300.0, 400.0]
    assert all(len(t["lines"]) == 3 for t in a)
    assert all(l["quantity"] == 15 for t in a for l in t["lines"])
    assert all(l["sku_id"] in catalog for t in a for l in t["lines"])


def test_in21_slotting_fija_por_sku():
    puntos = [
        {"sku_initial": "SKU001", "x": 10, "y": 5, "pick_sequence": 7,
         "location_id": "LOC-B", "WorkArea": "Area_High"},
        {"sku_initial": "SKU001", "x": 4, "y": 3, "pick_sequence": 2,
         "location_id": "LOC-A", "WorkArea": "Area_Ground"},
        {"sku_initial": "SKU002", "x": 8, "y": 8, "pick_sequence": 1,
         "location_id": "LOC-C", "WorkArea": "Area_Ground"},
    ]
    t = resolve_target_fija_por_sku("SKU001", puntos)
    # menor pick_sequence gana
    assert (t["cell"], t["location_id"], t["work_area"]) == (
        (4, 3), "LOC-A", "Area_Ground")
    assert resolve_target_fija_por_sku("SKU999", puntos) is None


# ---------------------------------------------------------------------------
# Dispatcher: cola propia + elegibilidad + asignacion
# ---------------------------------------------------------------------------

def test_in22_putaway_va_a_cola_propia_y_cuenta_en_maestra(make_dispatcher, make_wo):
    d = make_dispatcher()
    pick = make_wo()
    put = _wo_putaway(make_wo, "WO-PUT-T1-1", ready_at=None)
    d.agregar_work_orders([pick, put])

    assert pick in d.work_orders_pendientes
    assert put not in d.work_orders_pendientes      # NO contamina pools de pick
    assert put in d.putaway_pendientes
    assert len(d.lista_maestra_work_orders) == 2    # terminacion la espera
    assert d.work_orders_total_inicial == 2


def test_in23_asignacion_putaway(make_dispatcher, make_wo, fake_env):
    d = make_dispatcher()
    d.almacen = FakeAlmacenMin(fake_env)
    op = PutawayOperator(areas=("Area_Ground",))

    w1 = _wo_putaway(make_wo, "WO-PUT-T1-1", ready_at=None)      # no aterrizo
    w2 = _wo_putaway(make_wo, "WO-PUT-T1-2", ready_at=50.0)      # listo t=50
    w3 = _wo_putaway(make_wo, "WO-PUT-T1-3", ready_at=20.0)      # listo t=20
    w4 = _wo_putaway(make_wo, "WO-PUT-T1-4", work_area="Area_High",
                     ready_at=5.0)                               # area ajena
    d.agregar_work_orders([w1, w2, w3, w4])

    # ningun pick pendiente -> solicitar_asignacion cae al putaway
    tour = d.solicitar_asignacion(op)
    assert tour is not None
    assert tour['tour_type'] == 'putaway'
    assert tour['num_stops'] == 1                    # 1 pallet por viaje
    assert tour['work_orders'] == [w3]               # FIFO por tiempo listo
    assert w3 not in d.putaway_pendientes
    assert w3.status == "assigned"

    # siguiente: w2 (w1 sigue sin aterrizar, w4 es de area ajena)
    op2 = PutawayOperator(operator_id="OP-2")
    tour2 = d.solicitar_asignacion(op2)
    assert tour2['work_orders'] == [w2]

    # nada mas elegible para este operario
    op3 = PutawayOperator(operator_id="OP-3")
    assert d.solicitar_asignacion(op3) is None

    # el de Area_High solo lo toma un operario que sirva esa area
    op_high = PutawayOperator(areas=("Area_High",), operator_id="OP-H")
    tour4 = d.solicitar_asignacion(op_high)
    assert tour4['work_orders'] == [w4]


def test_in24_terminacion_espera_putaway(make_dispatcher, make_wo, fake_env):
    d = make_dispatcher()
    d.almacen = FakeAlmacenMin(fake_env)
    op = PutawayOperator()

    put = _wo_putaway(make_wo, "WO-PUT-T9-1", ready_at=0.0)
    d.agregar_work_orders([put])

    assert not d.simulacion_ha_terminado()           # pendiente => NO termina

    tour = d.solicitar_asignacion(op)
    assert tour['work_orders'] == [put]
    assert not d.simulacion_ha_terminado()           # asignada => NO termina

    d.notificar_completado_individual(op, put)
    d.finalizar_tour(op)
    assert d.simulacion_ha_terminado()               # completada => termina
    assert d.almacen.contador == 1                   # contador estandar


def test_in25_sin_putaway_el_flujo_no_cambia(make_dispatcher, make_operator):
    """Con inbound off (sin WOs putaway) los fallbacks devuelven None igual
    que antes: el gate byte-identico depende de esto."""
    d = make_dispatcher()
    op = PutawayOperator()
    assert d.solicitar_asignacion(op) is None
    assert d.putaway_pendientes == []
