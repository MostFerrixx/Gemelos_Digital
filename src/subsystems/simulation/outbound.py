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
        # F1.2 (modelo realista de carriles): agrupar por COLUMNA (x). Dentro de cada
        # columna, ordenar de FONDO (y mayor) a FRENTE (y menor) para llenar de atras
        # hacia adelante. Cada columna es un "carril": como mucho UN gruero a la vez.
        cols: Dict[int, List[DockSlot]] = {}
        for s in self.slots:
            cols.setdefault(s.cell[0], []).append(s)
        for x in cols:
            cols[x].sort(key=lambda s: -s.cell[1])  # fondo (y mayor) primero
        self.columns: Dict[int, List[DockSlot]] = cols
        self.lanes: Dict[int, Optional[str]] = {x: None for x in cols}  # x -> agent_id

    def acquire_lane(self, agent_id: str) -> Optional[int]:
        """Toma un carril (columna) LIBRE para `agent_id` y devuelve su x; None si las
        columnas estan todas ocupadas por un gruero (=> el agente espera fuera)."""
        for x in sorted(self.lanes):
            if self.lanes[x] is None:
                self.lanes[x] = agent_id
                return x
        return None

    def release_lane(self, x: int) -> None:
        """Libera el carril (el gruero sale del staging)."""
        if x in self.lanes:
            self.lanes[x] = None

    def deepest_empty_cell(self, x: int) -> Optional["DockSlot"]:
        """Devuelve el DockSlot LIBRE mas al fondo de la columna `x` (llenar de atras
        hacia adelante), o None si la columna esta llena de pallets."""
        for s in self.columns.get(x, []):
            if s.is_free():
                return s
        return None

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


def build_zone_cells(anchor: Tuple[int, int], k: int, is_walkable,
                     exclude=None, grid_w: int = 10**9,
                     grid_h: int = 10**9) -> List[Tuple[int, int]]:
    """
    INICIATIVA #3 / Fase 1: expande una celda ancla de staging a una ZONA de k
    celdas caminables y contiguas (1 pallet por celda).

    Algoritmo DETERMINISTA: anillos de Chebyshev crecientes alrededor del ancla;
    dentro de cada anillo, orden por (-y, x) para preferir la banda del muelle
    (filas inferiores, y mayor) y mantener reproducibilidad. Se descartan celdas
    no caminables, fuera de grilla y las de `exclude` (anclas de otros staging y
    celdas ya asignadas a otras zonas, para que NO se solapen).

    Args:
        anchor: celda ancla (x, y) del staging (de la hoja OutboundStaging).
        k: numero de posiciones deseadas (zone_capacity_default).
        is_walkable: fn(x, y) -> bool (usa collision_matrix del layout).
        exclude: iterable de celdas a evitar (otras anclas / celdas ya usadas).
        grid_w, grid_h: limites de la grilla.

    Returns:
        Lista de hasta k celdas (incluye el ancla primero si es caminable).
    """
    ax, ay = anchor
    excl = set(tuple(c) for c in (exclude or ()))
    excl.discard((ax, ay))  # el ancla siempre se intenta incluir
    cells: List[Tuple[int, int]] = []
    if 0 <= ax < grid_w and 0 <= ay < grid_h and is_walkable(ax, ay):
        cells.append((ax, ay))
    r = 1
    max_r = max(grid_w, grid_h)
    while len(cells) < k and r <= max_r:
        ring = []
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                ring.append((ax + dx, ay + dy))
        ring.sort(key=lambda c: (-c[1], c[0]))  # banda inferior primero, luego x
        for (cx, cy) in ring:
            if len(cells) >= k:
                break
            if not (0 <= cx < grid_w and 0 <= cy < grid_h):
                continue
            if (cx, cy) in excl or (cx, cy) in cells:
                continue
            if is_walkable(cx, cy):
                cells.append((cx, cy))
        r += 1
    return cells[:k]


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
