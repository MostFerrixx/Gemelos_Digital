# -*- coding: utf-8 -*-
"""
INIT-7 F1 / IN-1x: llegadas de camiones inbound (InboundProcess).

Pinea con SimPy real (sin motor completo, stub de almacen):
- Modo deterministic: camiones llegan en su arrival_time, descargan
  unload_time*n y publican pallets al buffer con eventos en orden.
- Asignacion de muelle: dock_id explicito respetado; ausente/invalido ->
  muelle con cola mas corta (empate: id menor, determinista).
- Contencion: dos camiones al mismo muelle -> el segundo espera (FIFO).
- Modo stochastic: reproducible bajo seed; respeta pallets_per_truck.
- Metricas inbound_metrics consistentes.
"""
import random

import simpy

from subsystems.simulation.inbound import (
    AsnError, InboundDock, InboundProcess, load_asn_trucks,
)


class FakeAlmacen:
    """Stub minimo: solo lo que InboundProcess consume del almacen real."""

    def __init__(self, env, dock_cells):
        self.env = env
        self.inbound_docks = {
            did: InboundDock(did, cell, env)
            for did, cell in dock_cells.items()
        }
        self.inbound_buffer = []
        self.inbound_metrics = {
            'trucks_received': 0, 'pallets_unloaded': 0, 'units_received': 0,
            'dock_wait_events': 0, 'dock_wait_time': 0.0, 'max_dock_wait': 0.0,
            'buffer_peak': 0,
        }
        self.sku_catalog = {'SKU001': {}, 'SKU002': {}, 'SKU003': {}}
        self.eventos = []

    def registrar_evento(self, tipo, datos):
        self.eventos.append({'t': float(self.env.now), 'tipo': tipo, **datos})


DOCKS = {1: (3, 1), 2: (15, 1), 3: (27, 1)}

CFG_BASE = {
    'enabled': True,
    'arrival_mode': 'deterministic',
    'unload_time_per_pallet': 10.0,
}


def _run(trucks, cfg=None, until=10_000):
    env = simpy.Environment()
    almacen = FakeAlmacen(env, DOCKS)
    proc = InboundProcess(env, almacen, dict(CFG_BASE, **(cfg or {})),
                          trucks=trucks)
    env.process(proc.run())
    env.run(until=until)
    return almacen, proc


def _eventos(almacen, tipo):
    return [e for e in almacen.eventos if e['tipo'] == tipo]


def test_in10_deterministic_llegadas_y_descarga():
    trucks = [
        {'truck_id': 'IN-001', 'arrival_time': 100, 'dock_id': 1,
         'lines': [{'sku_id': 'SKU001', 'quantity': 5},
                   {'sku_id': 'SKU002', 'quantity': 7}]},
        {'truck_id': 'IN-002', 'arrival_time': 400, 'dock_id': 2,
         'lines': [{'sku_id': 'SKU003', 'quantity': 3}]},
    ]
    almacen, proc = _run(trucks)

    arr = _eventos(almacen, 'inbound_truck_arrived')
    assert [(e['truck_id'], e['t']) for e in arr] == [
        ('IN-001', 100.0), ('IN-002', 400.0)]

    # descarga = unload_time_per_pallet * n_lineas (2 pallets -> 20s)
    dep = _eventos(almacen, 'inbound_truck_departed')
    assert [(e['truck_id'], e['t']) for e in dep] == [
        ('IN-001', 120.0), ('IN-002', 410.0)]

    # buffer con 3 pallets, ids deterministas, estado inicial correcto
    assert [p.id for p in almacen.inbound_buffer] == [
        'INP-IN-001-1', 'INP-IN-001-2', 'INP-IN-002-1']
    assert all(p.status == 'in_dock_buffer' for p in almacen.inbound_buffer)
    assert almacen.inbound_buffer[0].t_unloaded == 120.0

    assert proc.trucks_received == 2
    assert proc.pallets_unloaded == 3


def test_in11_dock_explicito_y_fallback_menos_cargado():
    trucks = [
        # dock explicito valido
        {'truck_id': 'A', 'arrival_time': 0, 'dock_id': 3,
         'lines': [{'sku_id': 'SKU001', 'quantity': 1}]},
        # sin dock -> el de cola mas corta con id menor (1)
        {'truck_id': 'B', 'arrival_time': 0,
         'lines': [{'sku_id': 'SKU001', 'quantity': 1}]},
        # dock invalido -> warn + fallback (2, porque 1 y 3 ocupados)
        {'truck_id': 'C', 'arrival_time': 1, 'dock_id': 99,
         'lines': [{'sku_id': 'SKU001', 'quantity': 1}]},
    ]
    almacen, _ = _run(trucks)
    docked = {e['truck_id']: e['dock_id']
              for e in _eventos(almacen, 'inbound_truck_docked')}
    assert docked == {'A': 3, 'B': 1, 'C': 2}


def test_in12_contencion_mismo_muelle_fifo():
    trucks = [
        {'truck_id': 'A', 'arrival_time': 0, 'dock_id': 1,
         'lines': [{'sku_id': 'SKU001', 'quantity': 1}] * 5},   # ocupa 50s
        {'truck_id': 'B', 'arrival_time': 10, 'dock_id': 1,
         'lines': [{'sku_id': 'SKU002', 'quantity': 2}]},
    ]
    almacen, _ = _run(trucks)
    docked = {e['truck_id']: e for e in _eventos(almacen, 'inbound_truck_docked')}
    assert docked['A']['t'] == 0.0
    # B llego a t=10 pero atraca cuando A termina (t=50): espero 40s
    assert docked['B']['t'] == 50.0
    assert docked['B']['wait'] == 40.0
    m = almacen.inbound_metrics
    assert m['dock_wait_events'] == 1
    assert m['dock_wait_time'] == 40.0
    assert m['max_dock_wait'] == 40.0


def test_in13_stochastic_reproducible_bajo_seed():
    def corrida():
        random.seed(42)
        env = simpy.Environment()
        almacen = FakeAlmacen(env, DOCKS)
        cfg = dict(CFG_BASE, arrival_mode='stochastic', truck_interval=100.0,
                   pallets_per_truck=4, units_per_pallet=20)
        env.process(InboundProcess(env, almacen, cfg).run())
        env.run(until=500)
        return almacen

    a1, a2 = corrida(), corrida()
    assert a1.eventos == a2.eventos  # byte-a-byte reproducible

    # 4 camiones en 500s (t=100,200,300,400), 4 pallets c/u
    deps = _eventos(a1, 'inbound_truck_departed')
    assert len(deps) == 4
    assert all(e['pallets_unloaded'] == 4 for e in deps)
    assert all(p.quantity == 20 for p in a1.inbound_buffer)
    assert all(p.sku_id in a1.sku_catalog for p in a1.inbound_buffer)


def test_in14_metricas_consistentes():
    trucks = [
        {'truck_id': 'A', 'arrival_time': 0, 'dock_id': 1,
         'lines': [{'sku_id': 'SKU001', 'quantity': 10},
                   {'sku_id': 'SKU002', 'quantity': 30}]},
    ]
    almacen, _ = _run(trucks)
    m = almacen.inbound_metrics
    assert m['trucks_received'] == 1
    assert m['pallets_unloaded'] == 2
    assert m['units_received'] == 40
    assert m['buffer_peak'] == 2


def test_in15_asn_loader_valida_y_ordena(tmp_path):
    import json
    # desordenado -> el loader reordena por arrival_time
    ok = {'trucks': [
        {'truck_id': 'B', 'arrival_time': 500,
         'lines': [{'sku_id': 'S1', 'quantity': 1}]},
        {'truck_id': 'A', 'arrival_time': 100,
         'lines': [{'sku_id': 'S2', 'quantity': 2}]},
    ]}
    p = tmp_path / 'asn.json'
    p.write_text(json.dumps(ok), encoding='utf-8')
    trucks = load_asn_trucks(str(p))
    assert [t['truck_id'] for t in trucks] == ['A', 'B']

    # archivo inexistente
    try:
        load_asn_trucks(str(tmp_path / 'nope.json'))
        assert False, 'debia lanzar AsnError'
    except AsnError:
        pass

    # quantity invalida
    bad = {'trucks': [{'truck_id': 'X', 'arrival_time': 0,
                       'lines': [{'sku_id': 'S1', 'quantity': 0}]}]}
    p2 = tmp_path / 'bad.json'
    p2.write_text(json.dumps(bad), encoding='utf-8')
    try:
        load_asn_trucks(str(p2))
        assert False, 'debia lanzar AsnError'
    except AsnError:
        pass


def test_in16_asn_canonico_carga():
    """El ASN de ejemplo del repo debe pasar por el loader real."""
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    trucks = load_asn_trucks(os.path.join(root, 'layouts', 'Inbound Test.json'))
    assert len(trucks) == 5
    assert trucks[0]['truck_id'] == 'IN-001'
