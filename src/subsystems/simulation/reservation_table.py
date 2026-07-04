# -*- coding: utf-8 -*-
"""
ReservationTable - Iniciativa #2 / Opcion C (Time-Window / Reservation Routing)
Digital Twin Warehouse Simulator

Tabla de reservas espacio-temporales: por cada celda, los intervalos de tiempo
[t_in, t_out] que estan ocupados y por que agente. INVARIANTE central (INV):
para toda celda, los intervalos de agentes DISTINTOS son disjuntos (con un margen
de seguridad `clearance`). Conflict-free por construccion: el SpaceTimePlanner solo
acepta una ventana si `is_free` la admite, y solo entonces `reserve` la inserta.

Modelo de ocupacion: al ENTRAR en una celda mediante un paso (frm->to) que parte en
`t` y llega en `t'`, el agente ocupa la celda destino durante [t, t']. Esperar en una
celda extiende su intervalo por `dt_wait`. Las aristas (movimientos dirigidos) se
registran aparte para detectar el conflicto frontal (swap / head-on).

Ley #4: ASCII puro en prints/logs.
"""

import bisect
from typing import Dict, List, Tuple, Optional

# Un intervalo de ocupacion de una celda: (t_in, t_out, agent_id).
Interval = Tuple[float, float, str]
Cell = Tuple[int, int]
Edge = Tuple[Cell, Cell]


class ReservationTable:
    """
    Estructura `reservations: {cell: [Interval, ...]}` con intervalos ORDENADOS por
    t_in y DISJUNTOS entre agentes distintos. `edges: {(frm,to): [Interval,...]}` para
    el chequeo de swap. Memoria acotada via `purge_before` y `release_agent`.
    """

    def __init__(self, clearance: float = 0.0):
        # Margen de seguridad (eps) entre intervalos contiguos de agentes distintos.
        # Con clearance=0 se exige no-solapamiento estricto (bordes pueden tocarse).
        self.clearance = float(clearance)
        self.reservations: Dict[Cell, List[Interval]] = {}
        self.edges: Dict[Edge, List[Interval]] = {}
        # Metricas: inserciones y solapes detectados (DEBE ser 0 por construccion).
        self.reserve_calls = 0
        self.overlap_violations = 0

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def is_free(self, cell: Cell, t_in: float, t_out: float,
                ignore_agent: Optional[str] = None,
                ignore_agents=None) -> bool:
        """
        True si [t_in, t_out] no pisa ninguna reserva de OTRO agente en `cell`.
        Dos intervalos [a,b] y [c,d] se solapan si a < d y c < b. Con `clearance`
        se exige separacion adicional: se expanden los existentes por +/- clearance.
        `ignore_agents` (opcional, aditivo): coleccion de ids EXTRA a ignorar
        ademas de `ignore_agent` (p.ej. el gruero que coloca un pallet).
        """
        ivs = self.reservations.get(cell)
        if not ivs:
            return True
        cl = self.clearance
        for (e_in, e_out, e_agent) in ivs:
            if e_agent == ignore_agent:
                continue
            if ignore_agents is not None and e_agent in ignore_agents:
                continue
            # solapan si t_in < e_out+cl  y  e_in-cl < t_out  (margen a ambos lados)
            if t_in < (e_out + cl) and (e_in - cl) < t_out:
                return False
            # lista ordenada por t_in: si el existente empieza ya despues de t_out+cl,
            # los siguientes tambien => no puede haber mas solapes.
            if e_in - cl >= t_out:
                break
        return True

    def earliest_free(self, cell: Cell, t_from: float, dur: float,
                      ignore_agent: Optional[str] = None) -> Optional[float]:
        """
        MEJ-4 (salto SIPP): primer instante t >= t_from tal que [t, t+dur] esta
        libre de reservas ajenas en `cell`. Permite al planner ESPERAR el fin de
        una permanencia larga (descarga de decenas de segundos) con UN estado en
        vez de miles de pasos dt_wait (que reventaban max_expansions).
        Devuelve None si no hay hueco (no ocurre con intervalos finitos).
        """
        ivs = self.reservations.get(cell)
        if not ivs:
            return float(t_from)
        cl = self.clearance
        t = float(t_from)
        # Intervalos ordenados por t_in: avanzar t hasta salir de cada bloqueo.
        for (e_in, e_out, e_agent) in ivs:
            if e_agent == ignore_agent:
                continue
            if e_in - cl >= t + dur:
                return t  # hueco suficiente antes de este intervalo
            if t < (e_out + cl) and (e_in - cl) < t + dur:
                t = e_out + cl  # saltar al final del bloqueo (con margen)
        return t

    def can_swap(self, frm: Cell, to: Cell, t_in: float, t_out: float,
                 agent_id: str) -> bool:
        """
        True si NO hay conflicto frontal en la arista frm->to: rechaza si otro agente
        tiene reservada la arista INVERSA to->frm en un intervalo que se solapa con
        [t_in, t_out] (se cruzarian atravesandose). Reusa la misma logica de solape.
        """
        rev = self.edges.get((to, frm))
        if not rev:
            return True
        cl = self.clearance
        for (e_in, e_out, e_agent) in rev:
            if e_agent == agent_id:
                continue
            if t_in < (e_out + cl) and (e_in - cl) < t_out:
                return False
        return True

    # ------------------------------------------------------------------
    # Insercion
    # ------------------------------------------------------------------
    def reserve(self, cell: Cell, t_in: float, t_out: float, agent_id: str,
                ignore_agents=None) -> bool:
        """
        Inserta la ocupacion de `cell` para [t_in, t_out] manteniendo orden por t_in.
        Verifica el invariante (assert defensivo): si pisara otra reserva, NO inserta,
        cuenta `overlap_violations` y devuelve False (defensa en profundidad, plan 4.8).
        Devuelve True si se inserto.
        `ignore_agents` (opcional, aditivo): ids cuyas reservas NO bloquean esta
        insercion (caso pallet: ignorar al gruero que lo esta colocando; sus
        permanencias en la celda son el PASADO inmediato, no un conflicto real).
        """
        if not self.is_free(cell, t_in, t_out, ignore_agent=agent_id,
                            ignore_agents=ignore_agents):
            self.overlap_violations += 1
            return False
        ivs = self.reservations.setdefault(cell, [])
        bisect.insort(ivs, (float(t_in), float(t_out), agent_id))
        self.reserve_calls += 1
        return True

    def reserve_move(self, frm: Cell, to: Cell, t_in: float, t_out: float,
                     agent_id: str) -> None:
        """Registra la arista dirigida frm->to (para el chequeo de swap)."""
        if frm == to:
            return
        ivs = self.edges.setdefault((frm, to), [])
        bisect.insort(ivs, (float(t_in), float(t_out), agent_id))

    # ------------------------------------------------------------------
    # Liberacion / purga (memoria acotada)
    # ------------------------------------------------------------------
    def release_agent(self, agent_id: str) -> None:
        """Elimina TODAS las reservas (vertices y aristas) de `agent_id`."""
        empty_cells = []
        for cell, ivs in self.reservations.items():
            kept = [iv for iv in ivs if iv[2] != agent_id]
            if kept:
                self.reservations[cell] = kept
            else:
                empty_cells.append(cell)
        for cell in empty_cells:
            self.reservations.pop(cell, None)
        empty_edges = []
        for edge, ivs in self.edges.items():
            kept = [iv for iv in ivs if iv[2] != agent_id]
            if kept:
                self.edges[edge] = kept
            else:
                empty_edges.append(edge)
        for edge in empty_edges:
            self.edges.pop(edge, None)

    def purge_before(self, t: float) -> None:
        """Purga intervalos ya pasados (t_out < t) para acotar memoria."""
        empty_cells = []
        for cell, ivs in self.reservations.items():
            kept = [iv for iv in ivs if iv[1] >= t]
            if kept:
                self.reservations[cell] = kept
            else:
                empty_cells.append(cell)
        for cell in empty_cells:
            self.reservations.pop(cell, None)
        empty_edges = []
        for edge, ivs in self.edges.items():
            kept = [iv for iv in ivs if iv[1] >= t]
            if kept:
                self.edges[edge] = kept
            else:
                empty_edges.append(edge)
        for edge in empty_edges:
            self.edges.pop(edge, None)

    def total_intervals(self) -> int:
        return sum(len(v) for v in self.reservations.values())

    def __repr__(self):
        return (f"ReservationTable(cells={len(self.reservations)}, "
                f"intervals={self.total_intervals()}, clearance={self.clearance}, "
                f"reserve_calls={self.reserve_calls}, "
                f"overlap_violations={self.overlap_violations})")
