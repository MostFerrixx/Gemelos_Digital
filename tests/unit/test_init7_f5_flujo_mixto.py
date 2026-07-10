# -*- coding: utf-8 -*-
"""
INIT-7 F5 / IN-5x: flujo mixto -- prioridad de flota compartida (F5a) y
cross-docking (F5b).

Pinea:
- putaway_priority='putaway_first': el putaway elegible se asigna ANTES que
  los picks; 'picks_first' (default) conserva el comportamiento historico.
- Metrica de contencion cruzada (espera pallet listo -> asignacion).
- _rescatar_backorders_cross_dock: FIFO por orden del archivo, tope por
  cantidad del pallet, decrementa pendientes, hereda prioridad/due_time.
- _preparar_cross_dock: solo modo deterministic; en estocastico se desactiva.
- build_service_level_summary: fill_rate_effective_pct solo si hubo rescates
  (con cross-dock off la metadata es identica a la historica -> gate).
"""
import pytest

from core.replay_utils import build_service_level_summary
from subsystems.simulation.warehouse import AlmacenMejorado, SKU, WorkOrder


class FakeEnvNow:
    def __init__(self, now=0.0):
        self.now = now


class FakeAlmacenMin:
    """Para _asignar_putaway via dispatcher (mismo stub que F2)."""

    def __init__(self, env):
        self.env = env
        self.eventos = []
        self.contador = 0
        self.inbound_metrics = {}

    def registrar_evento(self, tipo, datos):
        self.eventos.append((tipo, datos))

    def incrementar_contador_workorders(self):
        self.contador += 1


class PutawayOperator:
    def __init__(self, areas=("Area_Ground",), operator_id="OP-1"):
        self.type = "GroundOperator"
        self.id = operator_id
        self.current_position = (0, 0)
        self._areas = set(areas)

    def get_priority_for_work_area(self, work_area):
        return 1 if work_area in self._areas else 999

    def can_handle_work_area(self, work_area):
        return work_area in self._areas


def _wo_putaway(make_wo, wo_id, ready_at=None):
    wo = make_wo(work_area="Area_Ground")
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
# F5a: prioridad de flota + contencion cruzada
# ---------------------------------------------------------------------------

def test_in50_putaway_first_asigna_putaway_antes_que_picks(
        make_dispatcher, make_wo, fake_env):
    d = make_dispatcher({'inbound': {'putaway_priority': 'putaway_first'}})
    d.almacen = FakeAlmacenMin(fake_env)
    op = PutawayOperator()

    pick = make_wo(work_area="Area_Ground")
    put = _wo_putaway(make_wo, "WO-PUT-A-1", ready_at=0.0)
    d.agregar_work_orders([pick, put])

    tour = d.solicitar_asignacion(op)
    assert tour is not None
    assert tour.get('tour_type') == 'putaway'   # putaway ANTES que el pick
    assert tour['work_orders'] == [put]
    assert pick in d.work_orders_pendientes     # el pick sigue en cola


def test_in51_picks_first_default_y_prioridad_invalida(make_dispatcher):
    d = make_dispatcher()
    assert d.putaway_priority == 'picks_first'  # default historico
    d2 = make_dispatcher({'inbound': {'putaway_priority': 'lo_que_sea'}})
    assert d2.putaway_priority == 'picks_first'  # invalida -> fallback


def test_in52_metrica_espera_pallet_a_asignacion(
        make_dispatcher, make_wo, fake_env):
    fake_env.now = 100.0
    d = make_dispatcher()
    d.almacen = FakeAlmacenMin(fake_env)
    op = PutawayOperator()

    put = _wo_putaway(make_wo, "WO-PUT-B-1", ready_at=40.0)  # listo en t=40
    d.agregar_work_orders([put])

    tour = d.solicitar_asignacion(op)  # sin picks -> fallback putaway
    assert tour['work_orders'] == [put]
    m = d.almacen.inbound_metrics
    assert m['putaway_wait_events'] == 1
    assert m['putaway_wait_total'] == 60.0   # 100 - 40
    assert m['max_putaway_wait'] == 60.0


# ---------------------------------------------------------------------------
# F5b: cross-docking
# ---------------------------------------------------------------------------

class _CaptureDispatcher:
    def __init__(self):
        self.agregadas = []

    def agregar_work_orders(self, wos):
        self.agregadas.extend(wos)


class _FakeOrder:
    def __init__(self, order_id, priority=None, due_time=None):
        self.order_id = order_id
        self.priority = priority
        self.due_time = due_time


def _bare_almacen_xd(backorders):
    a = object.__new__(AlmacenMejorado)
    a.env = FakeEnvNow(now=500.0)
    a.cross_dock_enabled = True
    a.cross_dock_backorders = backorders
    a._xd_counter = 0
    a.catalogo_skus = {'SKU001': SKU('SKU001', volumen=5)}
    a.inbound_metrics = {}
    a.dispatcher = _CaptureDispatcher()
    a.eventos = []
    a.registrar_evento = lambda tipo, datos: a.eventos.append((tipo, datos))
    # capacidad: sin split (1 WO por rescate)
    a._validar_y_ajustar_cantidad = (
        lambda sku, cantidad_original, work_area: [cantidad_original])
    a._resolver_staging_id = lambda order: 3
    a._seleccionar_staging_id = lambda: 1
    return a


def _wo_putaway_almacen(qty=24):
    """Putaway WO recien depositada (lo que recibe el rescate)."""
    sku = SKU('SKU001', volumen=5)
    wo = WorkOrder(
        work_order_id='WO-PUT-T-1', order_id='IN-001', tour_id='PUTAWAY',
        sku=sku, cantidad=qty, ubicacion=(3, 1), work_area='Area_Ground',
        pick_sequence=7, staging_id=1, location_id='LOC-010')
    wo.pallet_id = 'INP-IN-001-1'
    wo.target_location = (4, 8)
    return wo


def test_in53_rescate_fifo_con_tope_de_pallet():
    backorders = [
        {'order_id': 'ORD-A', 'sku_id': 'SKU001', 'qty_pending': 10,
         'order': _FakeOrder('ORD-A', priority=1, due_time=900.0)},
        {'order_id': 'ORD-B', 'sku_id': 'SKU001', 'qty_pending': 30,
         'order': _FakeOrder('ORD-B')},
        {'order_id': 'ORD-C', 'sku_id': 'SKU999', 'qty_pending': 99,
         'order': None},  # otro SKU: no se toca
    ]
    a = _bare_almacen_xd(backorders)
    a._rescatar_backorders_cross_dock(_wo_putaway_almacen(qty=24))

    # FIFO: ORD-A completo (10), ORD-B parcial (14 de 30); ORD-C intacto
    assert backorders[0]['qty_pending'] == 0
    assert backorders[1]['qty_pending'] == 16
    assert backorders[2]['qty_pending'] == 99

    wos = a.dispatcher.agregadas
    assert [(w.order_id, w.cantidad_inicial) for w in wos] == [
        ('ORD-A', 10), ('ORD-B', 14)]
    # el pick nace en la ubicacion donde el putaway guardo el stock
    assert all(w.ubicacion == (4, 8) and w.location_id == 'LOC-010'
               for w in wos)
    # hereda prioridad/due_time del pedido original
    assert wos[0].priority == 1 and wos[0].due_time == 900.0
    assert wos[1].priority == 99 and wos[1].due_time is None
    # staging resuelto via destino del pedido (stub -> 3)
    assert wos[0].staging_id == 3

    m = a.inbound_metrics
    assert m['cross_dock_units_rescued'] == 24
    assert m['cross_dock_picks_created'] == 2
    assert [e[0] for e in a.eventos].count('cross_dock_pick_created') == 2


def test_in54_sin_flag_o_sin_backorders_no_hace_nada():
    a = _bare_almacen_xd([])
    a._rescatar_backorders_cross_dock(_wo_putaway_almacen())
    assert a.dispatcher.agregadas == []

    a2 = _bare_almacen_xd([{'order_id': 'X', 'sku_id': 'SKU001',
                            'qty_pending': 5, 'order': None}])
    a2.cross_dock_enabled = False
    a2._rescatar_backorders_cross_dock(_wo_putaway_almacen())
    assert a2.dispatcher.agregadas == []


def test_in55_preparar_cross_dock_requiere_deterministic():
    a = object.__new__(AlmacenMejorado)
    a.inbound_config = {'cross_dock_enabled': True}
    a.configuracion = {'order_generation_mode': 'stochastic'}
    a._preparar_cross_dock()
    assert a.cross_dock_enabled is False  # estocastico -> se desactiva

    class _VR:
        unfilled_demand = [
            {'order_id': 'ORD-1', 'sku_id': 'SKU009', 'qty_unfilled': 12}]

    class _Strategy:
        parsed_orders = [_FakeOrder('ORD-1', priority=5)]

        def get_validation_result(self):
            # el stash lee DIRECTO de la estrategia (no de
            # almacen._last_validation_result, que se asigna despues)
            return _VR()

    b = object.__new__(AlmacenMejorado)
    b.inbound_config = {'cross_dock_enabled': True}
    b.configuracion = {'order_generation_mode': 'deterministic'}
    b.order_strategy = _Strategy()
    b._preparar_cross_dock()
    assert b.cross_dock_enabled is True
    assert len(b.cross_dock_backorders) == 1
    bo = b.cross_dock_backorders[0]
    assert bo['sku_id'] == 'SKU009' and bo['qty_pending'] == 12
    assert bo['order'].priority == 5  # pedido original enlazado


def test_in56_fill_rate_efectivo_solo_con_rescates():
    class _VR:
        allocation_summary = {'allocation_rate': 80.0,
                              'total_qty_requested': 100,
                              'total_qty_allocated': 80,
                              'total_qty_unfilled': 20,
                              'backorder_items_count': 2}
        unfilled_demand = [{'order_id': 'O1'}, {'order_id': 'O2'}]

    class _Almacen:
        def get_order_validation_result(self):
            return _VR()

    # sin rescates: claves nuevas AUSENTES (metadata identica a la historica)
    a = _Almacen()
    a.inbound_metrics = {'cross_dock_units_rescued': 0}
    s = build_service_level_summary(a)
    assert 'fill_rate_effective_pct' not in s
    assert 'units_rescued_cross_dock' not in s
    assert s['fill_rate_pct'] == 80.0

    # con rescates: fill-rate efectivo = (80 + 15) / 100
    b = _Almacen()
    b.inbound_metrics = {'cross_dock_units_rescued': 15}
    s2 = build_service_level_summary(b)
    assert s2['units_rescued_cross_dock'] == 15
    assert s2['fill_rate_effective_pct'] == 95.0
    assert s2['fill_rate_pct'] == 80.0  # la foto t=0 NO se reescribe
