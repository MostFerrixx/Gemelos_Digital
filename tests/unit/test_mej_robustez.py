# -*- coding: utf-8 -*-
"""
MEJ-ROBUSTEZ (auditoria 2026-07-10): degradacion por WO ante excepciones a
mitad de tour + watchdog de no-progreso.

Contexto verificado empiricamente antes del fix:
- Una excepcion en un proceso SimPy PROPAGA a env.run() => la corrida entera
  reventaba (sin .jsonl, sin Excel). NO era un cuelgue silencioso.
- El cuelgue real (sin excepcion) viene de WOs nunca asignables/elegibles;
  el guard QA-3 cubre el caso estatico (area sin agente), el watchdog cubre
  lo dinamico (ubicacion inalcanzable, bugs logicos futuros).

Pinea:
- notificar_wo_fallida: contabilidad completa + la terminacion CIERRA.
- _abort_tour: marca fallidas las WOs no completadas, resetea al agente.
- compute_stall_limit: base 7200s, extendido por la agenda inbound.
"""
import pytest

from engines.event_generator import STALL_LIMIT_BASE_S, compute_stall_limit


class FakeEnvNow:
    def __init__(self, now=0.0):
        self.now = now


class FakeAlmacenMin:
    def __init__(self, env):
        self.env = env
        self.eventos = []
        self.contador = 0

    def registrar_evento(self, tipo, datos):
        self.eventos.append((tipo, datos))

    def incrementar_contador_workorders(self):
        self.contador += 1


class FakeOperator:
    type = "GroundOperator"
    id = "OP-1"
    current_position = (0, 0)

    def get_priority_for_work_area(self, work_area):
        return 1


def _wo(make_wo, wo_id):
    wo = make_wo()
    wo.id = wo_id
    wo.status = "in_progress"
    wo.assigned_agent_id = "GroundOperator_OP-1"
    wo.order_id = "ORD-1"
    wo.tour_id = "T-1"
    wo.sku_id = "SKU001"
    wo.sku_name = "SKU001"
    wo.cantidad_total = 5
    wo.cantidad_inicial = 5
    wo.cantidad_restante = 5
    wo.staging_id = 1
    wo.work_group = "WG_A"
    wo.volumen_restante = 5
    wo.tiempo_inicio = 10.0
    wo.tiempo_fin = None
    return wo


# ---------------------------------------------------------------------------
# notificar_wo_fallida
# ---------------------------------------------------------------------------

def test_rb01_wo_fallida_cierra_la_terminacion(make_dispatcher, make_wo, fake_env):
    d = make_dispatcher()
    d.almacen = FakeAlmacenMin(fake_env)
    op = FakeOperator()

    wo = _wo(make_wo, "WO-CRASH-1")
    d.agregar_work_orders([wo])
    d.work_orders_pendientes.remove(wo)
    d.work_orders_asignados["GroundOperator_OP-1"] = [wo]
    d.work_orders_en_progreso["GroundOperator_OP-1"] = wo

    assert not d.simulacion_ha_terminado()

    fake_env.now = 99.0
    d.notificar_wo_fallida(op, wo)

    assert wo.status == "failed"
    assert wo.tiempo_fin == 99.0
    assert wo in d.work_orders_completados          # la terminacion la cuenta
    assert d.work_orders_asignados["GroundOperator_OP-1"] == []
    assert "GroundOperator_OP-1" not in d.work_orders_en_progreso
    assert d.simulacion_ha_terminado()              # cierra, no cuelga
    # NO infla el KPI de completadas exitosas
    assert d.almacen.contador == 0
    # evento visible con status failed
    tipos = [(t, dat.get('status')) for t, dat in d.almacen.eventos
             if t == 'work_order_update']
    assert ('work_order_update', 'failed') in tipos


def test_rb02_wo_fallida_es_idempotente(make_dispatcher, make_wo, fake_env):
    d = make_dispatcher()
    d.almacen = FakeAlmacenMin(fake_env)
    wo = _wo(make_wo, "WO-CRASH-2")
    d.agregar_work_orders([wo])
    d.notificar_wo_fallida(FakeOperator(), wo)
    d.notificar_wo_fallida(FakeOperator(), wo)      # doble aviso: no duplica
    assert d.work_orders_completados.count(wo) == 1


# ---------------------------------------------------------------------------
# _abort_tour (operators)
# ---------------------------------------------------------------------------

def test_rb03_abort_tour_marca_fallidas_y_resetea(make_dispatcher, make_wo, fake_env):
    from subsystems.simulation.operators import GroundOperator

    d = make_dispatcher()
    d.almacen = FakeAlmacenMin(fake_env)

    agente = object.__new__(GroundOperator)
    agente.id = "GroundOp-01"
    agente.type = "GroundOperator"
    agente.env = fake_env
    agente.cargo_volume = 120
    agente.status = "moving"
    agente.current_position = (5, 5)
    almacen = FakeAlmacenMin(fake_env)
    almacen.dispatcher = d
    agente.almacen = almacen

    w1 = _wo(make_wo, "WO-A")                        # en progreso -> failed
    w2 = _wo(make_wo, "WO-B")
    w2.status = "staged"                             # ya completada -> intacta
    d.agregar_work_orders([w1])

    tour = {'work_orders': [w1, w2]}
    agente._abort_tour(tour, RuntimeError("boom de prueba"))

    assert w1.status == "failed"
    assert w2.status == "staged"                     # no se toca lo completado
    assert agente.cargo_volume == 0
    assert agente.status == "idle"
    assert agente in d.operadores_disponibles        # finalizar_tour corrio
    tipos = [t for t, _ in almacen.eventos]
    assert 'agent_tour_crashed' in tipos


# ---------------------------------------------------------------------------
# Watchdog: compute_stall_limit
# ---------------------------------------------------------------------------

def test_rb04_stall_limit_base_y_extension_inbound():
    assert compute_stall_limit([]) == STALL_LIMIT_BASE_S
    assert compute_stall_limit(None) == STALL_LIMIT_BASE_S
    # agenda inbound: un hueco legitimo puede durar hasta la ultima llegada
    schedule = [{'arrival_time': 300}, {'arrival_time': 9000}]
    assert compute_stall_limit(schedule) == 9000 + STALL_LIMIT_BASE_S
    # la base es margen DESPUES de la ultima llegada agendada
    assert compute_stall_limit([{'arrival_time': 100}]) == 100 + STALL_LIMIT_BASE_S
    # basura tolerada
    assert compute_stall_limit([{'arrival_time': 'x'}]) == STALL_LIMIT_BASE_S
