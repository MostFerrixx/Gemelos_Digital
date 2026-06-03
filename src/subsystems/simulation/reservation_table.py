# -*- coding: utf-8 -*-
"""
ReservationTable - Iniciativa #2 / Opcion C (Time-Window / Reservation Routing)
Digital Twin Warehouse Simulator

Tabla de reservas espacio-temporales: por cada celda, los intervalos de tiempo
[t_in, t_out] que estan ocupados y por que agente. Invariante central (INV):
para toda celda, los intervalos de agentes DISTINTOS son disjuntos.

ESTADO: ESQUELETO (Fase 0). Las firmas existen; la logica se implementa en Fase 1.
Mientras tanto NADIE la instancia salvo `timewindow_active`, asi que con el flag
apagado el comportamiento es byte-identico al actual.

Ley #4: ASCII puro en prints/logs.
"""

from typing import Dict, List, Tuple, Optional

# Un intervalo de ocupacion de una celda: (t_in, t_out, agent_id).
Interval = Tuple[float, float, str]
Cell = Tuple[int, int]


class ReservationTable:
    """
    Estructura `reservations: {cell: [Interval, ...]}` con intervalos ORDENADOS por
    t_in y DISJUNTOS entre agentes distintos. Conflict-free por construccion: el
    SpaceTimePlanner solo acepta una ventana si `is_free` la admite, y solo entonces
    `reserve` la inserta.

    Fase 0: esqueleto (firmas). Fase 1: implementacion + invariante + asserts.
    """

    def __init__(self, clearance: float = 0.0):
        # Margen de seguridad (eps) entre intervalos contiguos de agentes distintos.
        self.clearance = float(clearance)
        self.reservations: Dict[Cell, List[Interval]] = {}
        # Metricas (Fase 1): inserciones, rechazos, solapes detectados (debe ser 0).
        self.reserve_calls = 0
        self.overlap_violations = 0

    # --- API (Fase 1 implementa) ---
    def is_free(self, cell: Cell, t_in: float, t_out: float,
                ignore_agent: Optional[str] = None) -> bool:
        """True si [t_in, t_out] no pisa ninguna reserva de OTRO agente en `cell`."""
        raise NotImplementedError("ReservationTable.is_free: Fase 1")

    def reserve(self, cell: Cell, t_in: float, t_out: float, agent_id: str) -> None:
        """Inserta la ocupacion manteniendo orden e invariante de disjuncion."""
        raise NotImplementedError("ReservationTable.reserve: Fase 1")

    def can_swap(self, frm: Cell, to: Cell, t_in: float, t_out: float,
                 agent_id: str) -> bool:
        """False si hay conflicto frontal (head-on/swap) en la arista frm->to."""
        raise NotImplementedError("ReservationTable.can_swap: Fase 1")

    def release_agent(self, agent_id: str) -> None:
        """Elimina TODAS las reservas futuras de `agent_id` (re-planificacion)."""
        raise NotImplementedError("ReservationTable.release_agent: Fase 1")

    def purge_before(self, t: float) -> None:
        """Purga intervalos ya pasados (t_out < t) para acotar memoria."""
        raise NotImplementedError("ReservationTable.purge_before: Fase 1")

    def __repr__(self):
        return (f"ReservationTable(cells={len(self.reservations)}, "
                f"clearance={self.clearance})")
