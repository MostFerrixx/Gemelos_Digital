# -*- coding: utf-8 -*-
"""
INIT-6 Opcion A: un camion no debe mezclar pallets de zonas de staging (rutas)
distintas. Antes, OutboundProcess.run() tomaba FIFO de TODO staged_pallets sin
mirar staging_id -- un camion podia llevarse pallets de la zona 1 y la zona 2
juntos, aunque representen rutas/destinos distintos. El fix agrupa por la zona
del pallet mas antiguo antes de cargar.

Usa un simpy.Environment real (liviano, sin GUI/IO) porque OutboundProcess.run()
es un generador SimPy -- necesita eventos reales para sus yield timeout().
"""
import simpy

from subsystems.simulation.outbound import OutboundProcess, Pallet


class FakeAlmacen:
    def __init__(self):
        self.staged_pallets = []
        self.outbound_metrics = {}
        self.reservation_table = None
        self.staging_zones = {}
        self.eventos = []

    def registrar_evento(self, tipo, datos):
        self.eventos.append((tipo, datos))


def _make_pallet(pallet_id, staging_id, t_staged):
    return Pallet(pallet_id=pallet_id, wo_id="WO-%s" % pallet_id,
                  order_id="ORD-%s" % pallet_id, staging_id=staging_id,
                  cell=(0, 0), t_staged=t_staged, volumen=1)


def test_un_camion_no_mezcla_pallets_de_zonas_distintas():
    almacen = FakeAlmacen()
    # Zona 1 tiene 2 pallets (los mas viejos); zona 2 tiene 3 pallets.
    almacen.staged_pallets = [
        _make_pallet("P1", staging_id=1, t_staged=0.0),
        _make_pallet("P2", staging_id=2, t_staged=1.0),
        _make_pallet("P3", staging_id=1, t_staged=2.0),
        _make_pallet("P4", staging_id=2, t_staged=3.0),
        _make_pallet("P5", staging_id=2, t_staged=4.0),
    ]
    almacen.staged_pallets.sort(key=lambda p: (p.t_staged, p.id))

    env = simpy.Environment()
    proc = OutboundProcess(env=env, almacen=almacen,
                            config={"dispatch_policy": "interval",
                                    "truck_interval": 10, "truck_capacity": 8,
                                    "loading_time": 0.1})
    env.process(proc.run())
    env.run(until=11)  # deja pasar exactamente 1 ciclo de camion

    departed = [d for (t, d) in almacen.eventos if t == "truck_departed"]
    assert len(departed) == 1
    # El pallet mas antiguo es P1 (staging=1, t=0.0) -> el camion sirve zona 1.
    assert departed[0]["staging_id"] == 1

    shipped = [d for (t, d) in almacen.eventos if t == "pallet_shipped"]
    assert {d["pallet_id"] for d in shipped} == {"P1", "P3"}, (
        "El camion debio llevarse SOLO los pallets de staging=1 (P1, P3), "
        "sin mezclar con los de staging=2"
    )
    # Los pallets de la zona 2 siguen esperando (no se perdieron, no se enviaron de mas).
    assert {p.id for p in almacen.staged_pallets} == {"P2", "P4", "P5"}


def test_zona_mas_antigua_se_sirve_primero_sin_inanicion():
    """Con 2 ciclos de camion, la zona 2 (que quedo esperando) debe servirse
    en el segundo ciclo -- no queda esperando para siempre."""
    almacen = FakeAlmacen()
    almacen.staged_pallets = [
        _make_pallet("P1", staging_id=1, t_staged=0.0),
        _make_pallet("P2", staging_id=2, t_staged=1.0),
    ]
    almacen.staged_pallets.sort(key=lambda p: (p.t_staged, p.id))

    env = simpy.Environment()
    proc = OutboundProcess(env=env, almacen=almacen,
                            config={"dispatch_policy": "interval",
                                    "truck_interval": 10, "truck_capacity": 8,
                                    "loading_time": 0.1})
    env.process(proc.run())
    env.run(until=21)  # 2 ciclos de camion

    departed = [d for (t, d) in almacen.eventos if t == "truck_departed"]
    assert len(departed) == 2
    assert departed[0]["staging_id"] == 1
    assert departed[1]["staging_id"] == 2
    assert almacen.staged_pallets == []


def test_capacidad_limita_dentro_de_la_misma_zona():
    """truck_capacity sigue respetandose DENTRO de la zona elegida."""
    almacen = FakeAlmacen()
    almacen.staged_pallets = [
        _make_pallet("P%d" % i, staging_id=1, t_staged=float(i))
        for i in range(5)
    ]
    almacen.staged_pallets.sort(key=lambda p: (p.t_staged, p.id))

    env = simpy.Environment()
    proc = OutboundProcess(env=env, almacen=almacen,
                            config={"dispatch_policy": "interval",
                                    "truck_interval": 10, "truck_capacity": 2,
                                    "loading_time": 0.1})
    env.process(proc.run())
    env.run(until=11)

    shipped = [d for (t, d) in almacen.eventos if t == "pallet_shipped"]
    assert len(shipped) == 2
    assert len(almacen.staged_pallets) == 3
