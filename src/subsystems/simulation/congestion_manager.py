# -*- coding: utf-8 -*-
"""
Congestion Manager - Iniciativa #2 (Congestion y contencion de recursos)
Digital Twin Warehouse Simulator

Capa de OCUPACION DINAMICA encima del mapa estatico (NO toca collision_matrix).
Responsabilidad unica: saber que celdas estan ocupadas en tiempo de simulacion.

FASES:
- Fase 1 (mode='instrument'): SOLO observa y mide co-ocupaciones (dos+ agentes en la
  misma celda en el mismo instante). No cambia el movimiento. Escribe un reporte aparte.
- Fase 3+ (mode='cell'/'cell+corridor'): ademas media adquisicion/espera/liberacion de
  celdas (se anade en esas fases).

Ley #4: ASCII puro en prints/logs.
"""

import json
import os
from typing import Dict, Tuple, Any, Optional


class CongestionManager:
    """
    Gestor de ocupacion dinamica de celdas.

    En Fase 1 funciona como un OBSERVADOR pasivo: cada vez que un agente entra a una
    celda, registra la ocupacion; si la celda ya estaba ocupada por otro agente, cuenta
    una co-ocupacion (violacion de exclusion espacial I1 que hoy ocurre porque los
    agentes se atraviesan).
    """

    # modos en los que la capa esta ACTIVA (observa). 'off' / disabled => inactiva.
    ACTIVE_MODES = ("instrument", "cell", "cell+corridor")
    # modos en los que ademas MEDIA la exclusion por celda (Fase 3+).
    EXCLUSION_MODES = ("cell", "cell+corridor")

    def __init__(self, env: Any, enabled: bool = False, mode: str = "off",
                 config: Optional[Dict[str, Any]] = None):
        self.env = env
        self.enabled = bool(enabled)
        self.mode = mode or "off"
        self.config = config or {}

        # Estado de ocupacion: celda (x,y) -> set de agent_id que la ocupan AHORA.
        self.occupied: Dict[Tuple[int, int], set] = {}

        # --- Metricas de instrumentacion (Fase 1) ---
        # Cada "co-ocupacion" = un instante en que un agente entra a una celda ya ocupada.
        self.cooccupation_events = 0
        self.cooccupation_by_cell: Dict[Tuple[int, int], int] = {}
        self.max_concurrent_by_cell: Dict[Tuple[int, int], int] = {}
        # Conteo en ventana de arranque (para prueba de estres de Fase 2).
        self.cooccupation_startup = 0          # t en [0, startup_window]
        self.startup_window = float(self.config.get("startup_window", 5.0))
        # Pares distintos de agentes que coincidieron (diagnostico).
        self.cooccupation_pairs = 0
        # Muestra acotada de incidentes (no explotar memoria, F12).
        self.samples = []
        self.max_samples = 200

        # --- Fase 3: exclusion por celda (reserva perezosa, plan 4.2) ---
        # owner: celda (x,y) -> agent_id que la POSEE (cap 1). Distinto de `occupied`
        # (que es el metrico observador que cuenta co-ocupaciones para validar I1).
        self.owner: Dict[Tuple[int, int], str] = {}
        # release_events: celda -> simpy.Event que se dispara cuando esa celda se libera.
        # Se crea on-demand para celdas en disputa y se recrea tras dispararse.
        self.release_events: Dict[Tuple[int, int], Any] = {}
        # Metricas F3 de exclusion / watchdog.
        self.acquire_calls = 0          # adquisiciones concedidas (try_acquire True)
        self.wait_episodes = 0          # veces que un agente entro en espera por celda
        self.wait_timeouts = 0          # veces que vencio W sin conseguir la celda
        self.hardcap_incidents = 0      # veces que un agente supero wait_hard_cap
        self.total_moves = 0            # movimientos reales de celda (para watchdog)
        self.last_move_time = 0.0       # ultimo instante de sim con un movimiento real
        self.stall_windows = 0          # ventanas de watchdog sin movimiento (stall)
        self.deadlock_incidents = []    # diagnostico de stalls (acotado)
        self.max_deadlock_incidents = 50

    @property
    def active(self) -> bool:
        """True si la capa debe observar/mediar (segun flag + modo)."""
        return self.enabled and self.mode in self.ACTIVE_MODES

    @property
    def cell_exclusion(self) -> bool:
        """True si ademas de observar, debe MEDIAR la exclusion por celda (Fase 3+)."""
        return self.enabled and self.mode in self.EXCLUSION_MODES

    # ------------------------------------------------------------------
    # API de ocupacion (gated: si no esta activa, no hace nada)
    # ------------------------------------------------------------------
    def enter(self, agent_id: str, cell: Optional[Tuple[int, int]]):
        """Marca que agent_id ocupa `cell`. Detecta co-ocupacion si ya habia otro."""
        if not self.active or cell is None:
            return
        occ = self.occupied.setdefault(cell, set())
        # co-ocupacion: hay al menos otro agente distinto ya en la celda
        others = occ - {agent_id}
        if others:
            self._record_cooccupation(cell, occ | {agent_id})
        occ.add(agent_id)

    def leave(self, agent_id: str, cell: Optional[Tuple[int, int]]):
        """Quita a agent_id de `cell`."""
        if not self.active or cell is None:
            return
        occ = self.occupied.get(cell)
        if occ:
            occ.discard(agent_id)
            if not occ:
                self.occupied.pop(cell, None)

    def move(self, agent_id: str, frm: Optional[Tuple[int, int]],
             to: Optional[Tuple[int, int]]):
        """Mueve a agent_id de `frm` a `to` (leave + enter), si cambian de celda."""
        if not self.active:
            return
        if frm == to:
            # re-entrar a la misma celda no cambia ocupacion
            self.enter(agent_id, to)
            return
        if frm is not None:
            self.leave(agent_id, frm)
        self.enter(agent_id, to)
        # Fase 3: registrar movimiento real (para el watchdog anti-freeze).
        self.total_moves += 1
        try:
            self.last_move_time = float(self.env.now)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Fase 3: API de EXCLUSION por celda (reserva perezosa, plan 4.2/4.3)
    # Estructura `owner` (cap 1) separada del metrico `occupied`. Si la capa NO
    # esta en modo exclusion, try_acquire siempre concede (no bloquea) => el
    # comportamiento de las fases previas no cambia.
    # ------------------------------------------------------------------
    def try_acquire(self, agent_id: str, cell: Optional[Tuple[int, int]]) -> bool:
        """
        Intenta que `agent_id` reserve `cell` (cap 1). Devuelve True si la consigue
        (libre o ya suya), False si la posee otro agente. No bloquea (la espera la
        orquesta el operario con yield sobre release_event(cell) + timeout).
        """
        if not self.cell_exclusion or cell is None:
            return True
        cur = self.owner.get(cell)
        if cur is None or cur == agent_id:
            self.owner[cell] = agent_id
            self.acquire_calls += 1
            return True
        return False

    def release(self, agent_id: str, cell: Optional[Tuple[int, int]]):
        """Libera `cell` si la posee `agent_id` y despierta a quien espere por ella."""
        if not self.cell_exclusion or cell is None:
            return
        if self.owner.get(cell) == agent_id:
            self.owner.pop(cell, None)
            ev = self.release_events.get(cell)
            if ev is not None and not ev.triggered:
                ev.succeed()
            # el evento disparado se descarta; release_event() creara uno fresco.
            self.release_events.pop(cell, None)

    def claim(self, agent_id: str, cell: Optional[Tuple[int, int]]):
        """
        Reserva forzada de `cell` para spawn/teletransporte (celdas asumidas libres
        por la dispersion F2). Si la poseia otro agente lo registra (no deberia pasar
        con staggered_start) y la fuerza, para mantener el invariante 'el agente posee
        su current_position' que hace que el metrico I1 lea 0.
        """
        if not self.cell_exclusion or cell is None:
            return
        prev = self.owner.get(cell)
        if prev is not None and prev != agent_id:
            self._record_deadlock({
                "kind": "claim_conflict",
                "cell": [int(cell[0]), int(cell[1])],
                "prev_owner": str(prev),
                "new_owner": str(agent_id),
                "t": self._now(),
            })
        self.owner[cell] = agent_id

    def release_event(self, cell: Tuple[int, int]) -> Any:
        """Devuelve (creando si hace falta) el simpy.Event de liberacion de `cell`."""
        ev = self.release_events.get(cell)
        if ev is None or ev.triggered:
            ev = self.env.event()
            self.release_events[cell] = ev
        return ev

    def note_wait_episode(self):
        self.wait_episodes += 1

    def note_wait_timeout(self):
        self.wait_timeouts += 1

    def note_hardcap(self, agent_id: str, cell: Tuple[int, int]):
        self.hardcap_incidents += 1
        self._record_deadlock({
            "kind": "wait_hardcap",
            "cell": [int(cell[0]), int(cell[1])],
            "agent": str(agent_id),
            "blocked_by": str(self.owner.get(cell)),
            "t": self._now(),
        })

    def _record_deadlock(self, info: Dict[str, Any]):
        if len(self.deadlock_incidents) < self.max_deadlock_incidents:
            self.deadlock_incidents.append(info)

    def _now(self) -> float:
        try:
            return round(float(self.env.now), 3)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Fase 3: WATCHDOG (DETECTOR/diagnostico; la cesion formal es Fase 5)
    # ------------------------------------------------------------------
    def watchdog_proc(self, operarios):
        """
        Proceso SimPy: cada `watchdog_window` comprueba si hubo algun movimiento real.
        Si no hubo movimiento y hay agentes ACTIVOS (no idle/finished), registra un
        stall (posible deadlock). En Fase 3 NO resuelve (solo deja traza); la
        terminacion en el peor caso la garantiza el cap de wallclock del harness.
        """
        if not self.cell_exclusion:
            return
        window = float(self.config.get("watchdog_window", 5.0))
        if window <= 0:
            return
        last_seen_moves = self.total_moves
        last_seen_t = float(self.env.now)
        while True:
            yield self.env.timeout(window)
            moved = self.total_moves != last_seen_moves
            active = [op for op in operarios
                      if getattr(op, "status", "idle") in ("moving", "working")]
            if not moved and active:
                self.stall_windows += 1
                self._record_deadlock({
                    "kind": "watchdog_stall",
                    "t": self._now(),
                    "window": window,
                    "active_agents": [
                        {"id": str(op.id), "status": op.status,
                         "pos": list(op.current_position) if op.current_position else None}
                        for op in active[:20]
                    ],
                    "owned_cells": len(self.owner),
                })
                print(f"[CONGESTION][WATCHDOG] STALL t={self._now()}: "
                      f"{len(active)} agentes activos sin movimiento en {window}s "
                      f"(stall_windows={self.stall_windows})")
            last_seen_moves = self.total_moves
            last_seen_t = float(self.env.now)

    def start_watchdog(self, operarios):
        """Arranca el watchdog si la exclusion esta activa. Idempotente-safe."""
        if self.cell_exclusion:
            self.env.process(self.watchdog_proc(operarios))
            print(f"[CONGESTION][WATCHDOG] iniciado (window="
                  f"{self.config.get('watchdog_window', 5.0)}s, modo deteccion F3).")

    # ------------------------------------------------------------------
    # Registro de co-ocupacion (agregado; sin spam por tick, F12)
    # ------------------------------------------------------------------
    def _record_cooccupation(self, cell: Tuple[int, int], occupants: set):
        self.cooccupation_events += 1
        self.cooccupation_by_cell[cell] = self.cooccupation_by_cell.get(cell, 0) + 1
        n = len(occupants)
        self.max_concurrent_by_cell[cell] = max(
            self.max_concurrent_by_cell.get(cell, 0), n
        )
        self.cooccupation_pairs += (n - 1)
        t = float(self.env.now)
        if t <= self.startup_window:
            self.cooccupation_startup += 1
        if len(self.samples) < self.max_samples:
            self.samples.append({
                "t": round(t, 3),
                "cell": [int(cell[0]), int(cell[1])],
                "agents": sorted(str(a) for a in occupants),
                "concurrent": n,
            })

    # ------------------------------------------------------------------
    # Reporte
    # ------------------------------------------------------------------
    def resumen(self) -> Dict[str, Any]:
        hotspots = sorted(
            self.cooccupation_by_cell.items(), key=lambda kv: kv[1], reverse=True
        )[:15]
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "active": self.active,
            "cell_exclusion": self.cell_exclusion,
            "startup_window": self.startup_window,
            "cooccupation_events_total": self.cooccupation_events,
            "cooccupation_events_startup_window": self.cooccupation_startup,
            "cooccupation_pairs_total": self.cooccupation_pairs,
            "distinct_cells_with_cooccupation": len(self.cooccupation_by_cell),
            "max_concurrent_any_cell": max(self.max_concurrent_by_cell.values(), default=0),
            "top_hotspots": [
                {"cell": [int(c[0]), int(c[1])],
                 "cooccupations": cnt,
                 "max_concurrent": self.max_concurrent_by_cell.get(c, 0)}
                for c, cnt in hotspots
            ],
            # --- Fase 3: exclusion + watchdog ---
            "exclusion": {
                "acquire_calls": self.acquire_calls,
                "wait_episodes": self.wait_episodes,
                "wait_timeouts": self.wait_timeouts,
                "hardcap_incidents": self.hardcap_incidents,
                "total_moves": self.total_moves,
                "stall_windows": self.stall_windows,
                "deadlock_incidents": len(self.deadlock_incidents),
            },
        }

    def write_report(self, output_dir: str, timestamp: str = "") -> Optional[str]:
        """Escribe el reporte de congestion a un JSON en output_dir. Devuelve el path."""
        if not self.active:
            print(f"[CONGESTION] Capa inactiva (enabled={self.enabled}, mode='{self.mode}'); "
                  f"no se genera reporte.")
            return None
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception:
            pass
        suffix = f"_{timestamp}" if timestamp else ""
        path = os.path.join(output_dir, f"congestion_report{suffix}.json")
        report = self.resumen()
        report["samples"] = self.samples
        report["deadlock_incidents"] = self.deadlock_incidents
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        s = self.resumen()
        print("\n" + "=" * 70)
        print("[CONGESTION] REPORTE DE INSTRUMENTACION (Fase 1)")
        print("=" * 70)
        print(f"  Modo: {s['mode']}")
        print(f"  Co-ocupaciones totales: {s['cooccupation_events_total']}")
        print(f"  Co-ocupaciones en arranque (t<= {s['startup_window']}): "
              f"{s['cooccupation_events_startup_window']}")
        print(f"  Celdas distintas con co-ocupacion: {s['distinct_cells_with_cooccupation']}")
        print(f"  Maximo de agentes simultaneos en una celda: {s['max_concurrent_any_cell']}")
        print(f"  Top hotspots:")
        for h in s["top_hotspots"][:8]:
            print(f"    - celda {tuple(h['cell'])}: {h['cooccupations']} co-ocup, "
                  f"max {h['max_concurrent']} simultaneos")
        print(f"  Reporte: {path}")
        print("=" * 70)
        return path

    def __repr__(self):
        return (f"CongestionManager(enabled={self.enabled}, mode='{self.mode}', "
                f"active={self.active}, cooccup={self.cooccupation_events})")
