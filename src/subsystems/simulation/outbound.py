# -*- coding: utf-8 -*-
"""
Subsistema OUTBOUND (Iniciativa #3) - Fase 0: ANDAMIAJE.

Entidades del muelle de salida: pallets persistentes que ocupan posiciones de
aforo (1 pallet por celda) y un proceso de despacho/expedicion que los retira.

FASE 0 (este archivo): solo firmas + logica minima de las estructuras de datos
(Pallet, DockSlot, StagingZone) y el ESQUELETO del OutboundProcess. NADA se
arranca ni altera la simulacion mientras `config.json["outbound"]["enabled"]`
sea False. La logica activa (crear pallets al descargar, reservar slots,
backpressure, camion) se implementa en Fases 1-2.

Reglas del proyecto respetadas:
- Ley #3: la configuracion vive en config.json; aqui solo se consume.
- Ley #4: ASCII-only en prints/logging (consola Windows cp1252).
- Ley #6: no rompe la cadena headless -> jsonl -> viewer; los eventos del muelle
  se emitiran via almacen.registrar_evento (Fases 1-2).
"""

from typing import Dict, List, Optional, Tuple, Any


# Estados del ciclo de vida de un pallet (documentados; usados desde Fase 1).
PALLET_STAGED = "staged"          # depositado, ocupa un slot, espera camion
PALLET_AWAITING_LOAD = "awaiting_load"  # seleccionado por un camion
PALLET_LOADING = "loading"        # cargandose en el camion
PALLET_SHIPPED = "shipped"        # retirado; el slot queda libre


class Pallet:
    """
    Carga unitaria depositada en el muelle (1 WorkOrder descargada = 1 pallet).

    FASE 0: estructura de datos pasiva. Se INSTANCIA en Fase 1 (al descargar).
    """

    def __init__(self, pallet_id: str, wo_id: str, order_id: str,
                 staging_id: int, cell: Optional[Tuple[int, int]] = None,
                 t_staged: float = 0.0, volumen: int = 0):
        self.id = pallet_id
        self.wo_id = wo_id
        self.order_id = order_id
        self.staging_id = staging_id
        self.cell = cell                # posicion fisica en la zona (x, y)
        self.t_staged = t_staged
        self.volumen = volumen
        self.status = PALLET_STAGED
        self.t_shipped: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "wo_id": self.wo_id,
            "order_id": self.order_id,
            "staging_id": self.staging_id,
            "cell": self.cell,
            "t_staged": self.t_staged,
            "volumen": self.volumen,
            "status": self.status,
            "t_shipped": self.t_shipped,
        }

    def __repr__(self):
        return (f"Pallet({self.id}, staging={self.staging_id}, "
                f"cell={self.cell}, {self.status})")


class DockSlot:
    """
    Posicion de aforo del muelle: UNA celda de grilla con capacidad 1 pallet.

    FASE 0: estructura pasiva. La integracion con la ReservationTable (reservar
    la celda mientras el slot esta ocupado) se cablea en Fase 1.
    """

    def __init__(self, cell: Tuple[int, int]):
        self.cell = cell
        self.occupied_by: Optional[str] = None   # pallet_id o None

    def is_free(self) -> bool:
        return self.occupied_by is None

    def assign(self, pallet_id: str) -> None:
        self.occupied_by = pallet_id

    def release(self) -> None:
        self.occupied_by = None

    def __repr__(self):
        st = "free" if self.is_free() else f"by={self.occupied_by}"
        return f"DockSlot({self.cell}, {st})"


class StagingZone:
    """
    Zona de aforo de un staging_id: conjunto de DockSlots (capacidad 1 c/u).

    FASE 0: se construye desde la lista de celdas que entrega el data_manager,
    pero solo si outbound.enabled. No participa todavia en la descarga.
    """

    def __init__(self, staging_id: int, cells: List[Tuple[int, int]]):
        self.staging_id = staging_id
        self.slots: List[DockSlot] = [DockSlot(tuple(c)) for c in cells]

    @property
    def capacity(self) -> int:
        return len(self.slots)

    def free_slot(self) -> Optional[DockSlot]:
        """Devuelve el primer slot libre (orden fijo => determinista) o None."""
        for s in self.slots:
            if s.is_free():
                return s
        return None

    def occupancy(self) -> int:
        return sum(0 if s.is_free() else 1 for s in self.slots)

    def is_full(self) -> bool:
        return self.free_slot() is None

    def __repr__(self):
        return (f"StagingZone(id={self.staging_id}, "
                f"{self.occupancy()}/{self.capacity})")


class OutboundProcess:
    """
    Proceso de despacho/expedicion (camion). ESQUELETO en Fase 0.

    Fase 2: generador SimPy que, segun politica (interval/batch/schedule), retira
    pallets 'staged', los marca 'shipped', libera sus slots (y la reserva de la
    celda en la ReservationTable) y emite eventos truck_*/pallet_* al jsonl.

    Fase 0: existe la firma; `run()` NO hace nada y NO se arranca (el gate de
    event_generator solo lo arranca si enabled, y aun asi es un no-op seguro).
    """

    def __init__(self, env: Any, almacen: Any, config: Dict[str, Any]):
        self.env = env
        self.almacen = almacen
        self.config = config or {}
        self.policy = self.config.get("dispatch_policy", "interval")
        self.truck_interval = float(self.config.get("truck_interval", 20.0))
        self.truck_capacity = int(self.config.get("truck_capacity", 8))
        self.loading_time = float(self.config.get("loading_time", 2.0))
        self.trucks_dispatched = 0
        self.pallets_shipped = 0

    def run(self):
        """
        FASE 0: stub no-op. No retira pallets ni avanza el reloj.
        (Generador vacio: si se arrancara por error, termina de inmediato.)
        """
        print("[OUTBOUND] OutboundProcess.run() stub (Fase 0): no-op.")
        return
        yield  # marca este metodo como generador (inalcanzable en Fase 0)

    def __repr__(self):
        return (f"OutboundProcess(policy={self.policy}, "
                f"T={self.truck_interval}, C={self.truck_capacity})")
