# -*- coding: utf-8 -*-
"""
BK-25 (capas 2 y 3): los PASILLOS del almacen, deducidos del mapa.

Un pasillo es el conjunto conexo de celdas de picking entre dos bloques de
racks (en WH1 v3: las columnas 1-2, 5-6, ... 29-30, filas 3 a 26). De aca
salen dos cosas que el Director decidio:

- **Cupo por pasillo** (capa 2): un pasillo de 2 celdas de ancho admite 2
  operarios; el tercero espera o va a otro pasillo de su recorrido.
- **Zona de picking** (capa 3): una zona por pasillo, numeradas de izquierda a
  derecha, y a cada operario se le asignan una o varias. Es como lo hacen los
  WMS del mercado (SAP EWM "activity area", Dynamics "zone"): la zona es un
  atributo de la UBICACION, y a quien le toca cada zona es configuracion de
  operacion.

Modulo puro: no conoce SimPy ni mueve agentes.
"""
from collections import deque
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

Celda = Tuple[int, int]


class Pasillo:
    """Un pasillo de picking numerado."""

    def __init__(self, numero: int, celdas: Sequence[Celda]):
        self.numero = int(numero)
        self.celdas: Set[Celda] = {tuple(c) for c in celdas}
        self.columnas = sorted({x for x, _ in self.celdas})
        self.filas = sorted({y for _, y in self.celdas})
        self.bocas: Set[Celda] = set()          # celdas con salida fuera del pasillo

    @property
    def ancho(self) -> int:
        """Ancho = el corte transversal mas angosto (por fila o por columna)."""
        por_fila = [sum(1 for c in self.celdas if c[1] == y) for y in self.filas]
        por_columna = [sum(1 for c in self.celdas if c[0] == x) for x in self.columnas]
        if len(self.columnas) <= len(self.filas):
            return min(por_fila) if por_fila else 0
        return min(por_columna) if por_columna else 0

    def __contains__(self, celda) -> bool:
        return tuple(celda) in self.celdas

    def __repr__(self):
        return ("Pasillo(%d, columnas=%s, filas %d-%d, ancho=%d, celdas=%d)"
                % (self.numero, self.columnas, self.filas[0], self.filas[-1],
                   self.ancho, len(self.celdas)))


class MapaDePasillos:
    """Deduce los pasillos del mapa y responde a que pasillo pertenece una celda."""

    def __init__(self, picks: Iterable[Celda],
                 es_transitable: Callable[[int, int], bool],
                 ancho: int, alto: int):
        self.es_transitable = es_transitable
        self.ancho, self.alto = int(ancho), int(alto)
        self.picks: Set[Celda] = {tuple(p) for p in picks if p}
        self.pasillos: List[Pasillo] = []
        self._de_celda: Dict[Celda, int] = {}
        self._deducir()

    # ------------------------------------------------------------- deduccion
    def _vecinos(self, c: Celda):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dy)
            if 0 <= n[0] < self.ancho and 0 <= n[1] < self.alto:
                yield n

    def _deducir(self):
        pendientes = set(self.picks)
        grupos: List[Set[Celda]] = []
        while pendientes:
            semilla = min(pendientes)
            grupo, cola = set(), deque([semilla])
            pendientes.discard(semilla)
            while cola:
                c = cola.popleft()
                grupo.add(c)
                for n in self._vecinos(c):
                    if n in pendientes:
                        pendientes.discard(n)
                        cola.append(n)
            grupos.append(grupo)
        # numerados de izquierda a derecha (y de arriba abajo si empatan)
        grupos.sort(key=lambda g: (min(x for x, _ in g), min(y for _, y in g)))
        for numero, grupo in enumerate(grupos, start=1):
            pasillo = Pasillo(numero, grupo)
            for c in grupo:
                self._de_celda[c] = numero
            # bocas: celdas con un vecino transitable FUERA del pasillo
            for c in grupo:
                for n in self._vecinos(c):
                    if n not in grupo and self.es_transitable(*n):
                        pasillo.bocas.add(c)
                        break
            self.pasillos.append(pasillo)

    # -------------------------------------------------------------- consulta
    def numero_de(self, celda) -> Optional[int]:
        """Pasillo al que pertenece la celda, o None si no es de picking."""
        return self._de_celda.get(tuple(celda))

    def pasillo(self, numero: int) -> Optional[Pasillo]:
        for p in self.pasillos:
            if p.numero == int(numero):
                return p
        return None

    @property
    def numeros(self) -> List[int]:
        return [p.numero for p in self.pasillos]

    def capacidad_sugerida(self, numero: int) -> int:
        """Por defecto, tantos operarios como ancho tenga el pasillo."""
        p = self.pasillo(numero)
        return max(1, p.ancho) if p else 1

    def resumen(self) -> Dict[str, object]:
        return {
            'pasillos': len(self.pasillos),
            'anchos': {p.numero: p.ancho for p in self.pasillos},
            'celdas': {p.numero: len(p.celdas) for p in self.pasillos},
        }

    def __repr__(self):
        return "MapaDePasillos(%d pasillos, anchos %s)" % (
            len(self.pasillos), sorted({p.ancho for p in self.pasillos}))
