# -*- coding: utf-8 -*-
"""
Subsistema INBOUND (INIT-7) - F1: LLEGADAS.

Entidades del muelle de recepcion: camiones que llegan (segun ASN determinista
o intervalo estocastico), ocupan un muelle (dock), descargan pallets a un
buffer y se van. Los pallets quedan en `almacen.inbound_buffer` esperando el
putaway (F2); en F1 NADIE los consume todavia.

Espejo estructural de outbound.py (OutboundProcess). Diferencias deliberadas:
- Los muelles son simpy.Resource(capacity=1): la cola de camiones es FIFO y
  DETERMINISTA (sin polling).
- El camion es una entidad virtual (no navega la grilla), igual que el camion
  del outbound. El pallet vive en el buffer del muelle hasta que un operario
  lo tome en F2 (navegara hasta el ancla del muelle).
- Buffer sin tope en F1 (el backpressure real aparece en F2 cuando el putaway
  no da abasto y se decida si el camion espera buffer libre).

Reglas del proyecto respetadas:
- Ley #3: la configuracion vive en config.json (bloque `inbound`, opt-in).
- Ley #4: ASCII-only en prints/logging (consola Windows cp1252).
- Ley #6: cadena headless -> jsonl -> viewer; eventos via registrar_evento.
- Con `inbound.enabled=false` (o bloque ausente) NADA de este modulo se
  ejecuta => .jsonl byte-identico al baseline.
"""

import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple

try:
    import simpy
except ImportError:  # pragma: no cover - simpy es dependencia dura del motor
    simpy = None


# Estados del ciclo de vida de un pallet inbound (F2 agrega los de putaway).
INPALLET_IN_BUFFER = "in_dock_buffer"      # descargado, espera putaway
INPALLET_PUTAWAY = "putaway_assigned"      # F2: WO de putaway asignada
INPALLET_STORED = "stored"                 # F2: depositado en ubicacion


class InboundPallet:
    """
    Carga unitaria que llega en un camion (1 linea del ASN = 1 pallet).
    """

    def __init__(self, pallet_id: str, truck_id: str, dock_id: int,
                 sku_id: str, quantity: int, t_unloaded: float = 0.0):
        self.id = pallet_id
        self.truck_id = truck_id
        self.dock_id = dock_id
        self.sku_id = sku_id
        self.quantity = quantity
        self.t_unloaded = t_unloaded
        self.status = INPALLET_IN_BUFFER
        # F2: dock-to-stock (se completa al depositar).
        self.t_stored: Optional[float] = None
        self.target_location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "truck_id": self.truck_id,
            "dock_id": self.dock_id,
            "sku_id": self.sku_id,
            "quantity": self.quantity,
            "t_unloaded": self.t_unloaded,
            "status": self.status,
            "t_stored": self.t_stored,
            "target_location": self.target_location,
        }

    def __repr__(self):
        return (f"InboundPallet({self.id}, {self.sku_id}x{self.quantity}, "
                f"dock={self.dock_id}, {self.status})")


class InboundDock:
    """
    Muelle de recepcion: ancla fisica (celda del grid, hoja InboundDocks) +
    recurso SimPy de capacidad 1 (un camion a la vez, cola FIFO determinista).
    """

    def __init__(self, dock_id: int, cell: Tuple[int, int], env: Any):
        self.dock_id = dock_id
        self.cell = tuple(cell)
        self.resource = simpy.Resource(env, capacity=1) if simpy else None

    def queue_len(self) -> int:
        """Camiones esperando + ocupando este muelle (para elegir el menos cargado)."""
        if self.resource is None:
            return 0
        return len(self.resource.queue) + len(self.resource.users)

    def __repr__(self):
        return f"InboundDock({self.dock_id}, cell={self.cell}, q={self.queue_len()})"


class AsnError(ValueError):
    """ASN invalido o ilegible (mensaje ASCII accionable)."""


def load_asn_trucks(asn_path: str) -> List[Dict[str, Any]]:
    """
    Lee y valida un archivo ASN (contrato en docs/PLAN_INIT7_INBOUND.md).

    Devuelve la lista de camiones ORDENADA por arrival_time (el contrato pide
    orden cronologico, pero se tolera y reordena si viene desordenado).

    Raises:
        AsnError: archivo inexistente, JSON invalido o contrato roto.
    """
    if not os.path.exists(asn_path):
        raise AsnError(f"Archivo ASN no encontrado: {asn_path}")
    try:
        with open(asn_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise AsnError(f"ASN ilegible ({asn_path}): {e}")

    trucks = data.get("trucks")
    if not isinstance(trucks, list) or not trucks:
        raise AsnError(f"ASN sin lista 'trucks' valida: {asn_path}")

    for i, truck in enumerate(trucks):
        if not truck.get("truck_id"):
            raise AsnError(f"ASN: camion #{i} sin truck_id")
        at = truck.get("arrival_time")
        if not isinstance(at, (int, float)) or at < 0:
            raise AsnError(f"ASN: camion {truck.get('truck_id')} con "
                           f"arrival_time invalido: {at!r}")
        lines = truck.get("lines")
        if not isinstance(lines, list) or not lines:
            raise AsnError(f"ASN: camion {truck.get('truck_id')} sin lineas")
        for line in lines:
            if not line.get("sku_id"):
                raise AsnError(f"ASN: linea sin sku_id en camion "
                               f"{truck.get('truck_id')}")
            qty = line.get("quantity")
            if not isinstance(qty, (int, float)) or qty <= 0:
                raise AsnError(f"ASN: quantity invalida ({qty!r}) en camion "
                               f"{truck.get('truck_id')}")

    return sorted(trucks, key=lambda t: (t["arrival_time"], t["truck_id"]))


class InboundProcess:
    """
    Proceso de llegadas de camiones inbound (F1).

    Modo 'deterministic': reproduce el ASN (cada camion en su arrival_time).
    Modo 'stochastic': un camion cada `truck_interval` segundos con
    `pallets_per_truck` pallets de SKUs muestreados del catalogo (reproducible
    bajo WAREHOUSE_SEED, igual que el resto del motor).

    Cada camion es su PROPIO proceso SimPy: dos camiones pueden descargar en
    muelles distintos a la vez, y si apuntan al mismo muelle el segundo espera
    en la cola FIFO del Resource.
    """

    def __init__(self, env: Any, almacen: Any, config: Dict[str, Any],
                 trucks: Optional[List[Dict[str, Any]]] = None):
        """
        Args:
            env: simpy.Environment del motor.
            almacen: AlmacenMejorado (usa inbound_docks, inbound_buffer,
                     inbound_metrics, registrar_evento, sku_catalog).
            config: bloque config["inbound"].
            trucks: lista pre-cargada (tests); si es None y el modo es
                    deterministic, se carga de config["asn_file_path"].
        """
        self.env = env
        self.almacen = almacen
        self.config = config or {}
        self.arrival_mode = str(self.config.get("arrival_mode", "deterministic"))
        self.asn_file_path = self.config.get("asn_file_path")
        self.truck_interval = float(self.config.get("truck_interval", 600.0))
        self.pallets_per_truck = int(self.config.get("pallets_per_truck", 10))
        self.unload_time_per_pallet = float(
            self.config.get("unload_time_per_pallet", 15.0))
        self.units_per_pallet = int(self.config.get("units_per_pallet", 20))
        self._trucks = trucks
        self.trucks_received = 0
        self.pallets_unloaded = 0

    # ------------------------------------------------------------------
    # Generadores SimPy
    # ------------------------------------------------------------------

    def run(self):
        """Proceso raiz: agenda las llegadas segun el modo configurado."""
        if self.arrival_mode == "stochastic":
            yield from self._run_stochastic()
        else:
            yield from self._run_deterministic()

    def _run_deterministic(self):
        trucks = self._trucks
        if trucks is None:
            if not self.asn_file_path:
                print("[INBOUND][ERROR] modo deterministic sin asn_file_path; "
                      "no llegan camiones.")
                return
            try:
                trucks = load_asn_trucks(self.asn_file_path)
            except AsnError as e:
                print(f"[INBOUND][ERROR] {e}; no llegan camiones.")
                return

        print(f"[INBOUND] F1: {len(trucks)} camiones agendados (ASN).")
        for truck in trucks:
            arrival = float(truck["arrival_time"])
            if arrival > self.env.now:
                yield self.env.timeout(arrival - self.env.now)
            self.env.process(self._truck_process(
                truck_id=str(truck["truck_id"]),
                lines=truck["lines"],
                requested_dock=truck.get("dock_id"),
            ))

    def _run_stochastic(self):
        """Camiones sinteticos cada truck_interval (reproducible bajo seed).

        Los SKUs se muestrean del catalogo ORDENADO (el orden de un dict no es
        contrato); quantity fija = units_per_pallet (sin ruido extra en F1).
        """
        catalog = sorted(getattr(self.almacen, "sku_catalog", {}) or {})
        if not catalog:
            print("[INBOUND][ERROR] modo stochastic sin sku_catalog; "
                  "no llegan camiones.")
            return
        print(f"[INBOUND] F1: modo stochastic (1 camion cada "
              f"{self.truck_interval:.0f}s, {self.pallets_per_truck} pallets).")
        n = 0
        while True:
            yield self.env.timeout(self.truck_interval)
            n += 1
            lines = [{"sku_id": random.choice(catalog),
                      "quantity": self.units_per_pallet}
                     for _ in range(self.pallets_per_truck)]
            self.env.process(self._truck_process(
                truck_id=f"IN-S{n}", lines=lines, requested_dock=None))

    def _truck_process(self, truck_id: str, lines: List[Dict[str, Any]],
                       requested_dock: Optional[int]):
        """Ciclo de UN camion: llegar -> muelle -> descargar -> partir."""
        t_arrival = float(self.env.now)
        dock = self._select_dock(requested_dock)
        if dock is None:
            print(f"[INBOUND][ERROR] {truck_id}: no hay muelles definidos "
                  f"(hoja InboundDocks vacia?); camion descartado.")
            return

        self.almacen.registrar_evento('inbound_truck_arrived', {
            'truck_id': truck_id,
            'dock_id': dock.dock_id,
            'n_pallets': len(lines),
        })

        with dock.resource.request() as req:
            yield req
            wait = float(self.env.now) - t_arrival
            m = getattr(self.almacen, 'inbound_metrics', None)
            if m is not None and wait > 0:
                m['dock_wait_events'] = m.get('dock_wait_events', 0) + 1
                m['dock_wait_time'] = m.get('dock_wait_time', 0.0) + wait
                m['max_dock_wait'] = max(m.get('max_dock_wait', 0.0), wait)

            self.almacen.registrar_evento('inbound_truck_docked', {
                'truck_id': truck_id,
                'dock_id': dock.dock_id,
                'wait': round(wait, 2),
            })

            # Descarga: unload_time POR PALLET (espejo de loading_time del
            # outbound). Se descarga todo y recien entonces se publican los
            # pallets al buffer (el camion abre puertas una vez).
            n = len(lines)
            yield self.env.timeout(self.unload_time_per_pallet * n)

            buffer = getattr(self.almacen, 'inbound_buffer', None)
            for i, line in enumerate(lines, start=1):
                pallet = InboundPallet(
                    pallet_id=f"INP-{truck_id}-{i}",
                    truck_id=truck_id,
                    dock_id=dock.dock_id,
                    sku_id=str(line["sku_id"]),
                    quantity=int(line["quantity"]),
                    t_unloaded=float(self.env.now),
                )
                if buffer is not None:
                    buffer.append(pallet)
                self.pallets_unloaded += 1
                if m is not None:
                    m['pallets_unloaded'] = m.get('pallets_unloaded', 0) + 1
                    m['units_received'] = (m.get('units_received', 0)
                                           + pallet.quantity)
                self.almacen.registrar_evento('inbound_pallet_unloaded', {
                    'pallet_id': pallet.id,
                    'truck_id': truck_id,
                    'dock_id': dock.dock_id,
                    'sku_id': pallet.sku_id,
                    'quantity': pallet.quantity,
                })

            if m is not None:
                m['trucks_received'] = m.get('trucks_received', 0) + 1
                if buffer is not None:
                    m['buffer_peak'] = max(m.get('buffer_peak', 0), len(buffer))
            self.trucks_received += 1

            backlog = len(buffer) if buffer is not None else 0
            print(f"[INBOUND] {truck_id} descargo {n} pallets en muelle "
                  f"{dock.dock_id} (t={self.env.now:.0f}s). "
                  f"Buffer={backlog}.")
            self.almacen.registrar_evento('inbound_truck_departed', {
                'truck_id': truck_id,
                'dock_id': dock.dock_id,
                'pallets_unloaded': n,
                'buffer_backlog': backlog,
            })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _select_dock(self, requested_dock: Optional[int]) -> Optional[InboundDock]:
        """dock_id explicito del ASN si existe; si no, el muelle con la cola
        mas corta (empate -> dock_id menor: determinista)."""
        docks = getattr(self.almacen, 'inbound_docks', {}) or {}
        if not docks:
            return None
        if requested_dock is not None:
            dock = docks.get(requested_dock)
            if dock is not None:
                return dock
            print(f"[INBOUND][WARN] dock_id={requested_dock} no existe; "
                  f"se asigna muelle libre.")
        return min(docks.values(), key=lambda d: (d.queue_len(), d.dock_id))

    def __repr__(self):
        return (f"InboundProcess(mode={self.arrival_mode}, "
                f"T={self.truck_interval}, P={self.pallets_per_truck})")
