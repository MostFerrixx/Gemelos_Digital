# -*- coding: utf-8 -*-
"""
Zonas de espera de operarios ociosos.  (BK-15, decision del Director 2026-09-18)

En la operacion real, quien no tiene trabajo espera en un lugar donde no
molesta (y si molesta, se corre). En la simulacion eso se garantiza asi:
el agente sin trabajo camina a una celda de espera y la RESERVA SIN FIN; los
demas planifican alrededor de el como de un obstaculo fijo. La reserva se
libera sola cuando recibe su proxima tarea.

Bloque de configuracion (opcional):

    "zonas_espera": {
      "ZE-1": {"x": 5, "y": 29, "ancho": 1, "alto": 1}
    }

Cada zona es un rectangulo del mapa; se usan sus celdas validas. Si no se
declara ninguna, el simulador elige las celdas solo (ver `_automaticas`).

Nunca puede ser celda de espera:
  * una celda no transitable o fuera del mapa;
  * un punto de pick, una zona de descarga o un muelle;
  * el acceso a una zona de descarga o a un muelle (a 1 celda);
  * la boca de un pasillo de picking (vecina de un punto de pick);
  * una celda que, ocupada, deje incomunicado un punto de pick, una zona de
    descarga o un muelle (se verifica recorriendo el mapa).
"""

import logging
from collections import deque
from typing import Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

Cell = Tuple[int, int]

# Una estadia "sin fin" en la tabla de reservas (segundos).
ESPERA_ABIERTA_S = 1.0e9


class GestorZonasEspera:
    """Celdas de espera y a que agente esta asignada cada una."""

    def __init__(self, configuracion, es_transitable, ancho: int, alto: int,
                 picks: Iterable[Cell], descargas: Iterable[Cell],
                 muelles: Iterable[Cell], n_agentes: int = 4):
        self.es_transitable = es_transitable
        self.ancho, self.alto = int(ancho), int(alto)
        self.picks: Set[Cell] = {tuple(c) for c in picks}
        self.descargas: Set[Cell] = {tuple(c) for c in descargas}
        self.muelles: Set[Cell] = {tuple(c) for c in muelles}
        self.avisos: List[str] = []
        self.asignadas: Dict[str, Cell] = {}
        self.automatica = False

        bloque = (configuracion or {}).get('zonas_espera') or {}
        if bloque:
            candidatas = self._de_configuracion(bloque)
            limite = None
        else:
            # Sin configuracion: una celda por agente mas dos de margen.
            self.automatica = True
            candidatas = self._automaticas()
            limite = n_agentes + 2
        self.celdas: List[Cell] = self._sin_cortar_el_mapa(candidatas, limite)
        if not self.celdas:
            self.avisos.append(
                "No hay ninguna celda de espera valida: los operarios sin trabajo "
                "se quedaran donde terminaron (y pueden estorbar).")
        for aviso in self.avisos:
            logger.warning("[WARN][CONFIG] %s", aviso)

    # ------------------------------------------------------------- reglas

    def _dentro(self, c: Cell) -> bool:
        return 0 <= c[0] < self.ancho and 0 <= c[1] < self.alto

    def _vecinos(self, c: Cell):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dy)
            if self._dentro(n) and self.es_transitable(*n):
                yield n

    def motivo_invalida(self, c: Cell) -> Optional[str]:
        """Por que `c` no puede ser celda de espera (None si puede)."""
        if not self._dentro(c) or not self.es_transitable(*c):
            return "no es una celda transitable del mapa"
        if c in self.picks:
            return "es un punto de pick"
        if c in self.descargas or c in self.muelles:
            return "es una zona de descarga o un muelle"
        for d in self.descargas | self.muelles:
            if abs(d[0] - c[0]) + abs(d[1] - c[1]) <= 1:
                return "es el acceso a una zona de descarga o a un muelle"
        if any(n in self.picks for n in self._vecinos(c)):
            return "es la boca de un pasillo de picking"
        return None

    def _de_configuracion(self, bloque) -> List[Cell]:
        celdas: List[Cell] = []
        if not isinstance(bloque, dict):
            self.avisos.append("'zonas_espera' debe ser un objeto {id: {x, y, ancho, alto}}.")
            return celdas
        for zona_id, d in bloque.items():
            d = d if isinstance(d, dict) else {}
            try:
                x, y = int(d['x']), int(d['y'])
                w, h = int(d.get('ancho', 1)), int(d.get('alto', 1))
            except (KeyError, TypeError, ValueError):
                self.avisos.append("La zona de espera '%s' no tiene x, y validos; "
                                   "se descarta." % zona_id)
                continue
            descartadas = []
            for yy in range(y, y + max(1, h)):
                for xx in range(x, x + max(1, w)):
                    motivo = self.motivo_invalida((xx, yy))
                    if motivo:
                        descartadas.append("(%d, %d) %s" % (xx, yy, motivo))
                    elif (xx, yy) not in celdas:
                        celdas.append((xx, yy))
            if descartadas:
                self.avisos.append("Zona de espera '%s': se descartan celdas: %s."
                                   % (zona_id, "; ".join(descartadas)))
        return celdas

    def _automaticas(self) -> List[Cell]:
        """Sin configuracion: celdas validas de BORDE (a lo sumo 3 vecinos:
        fuera de la circulacion) ordenadas por cercania a las zonas de descarga
        (donde termina cada recorrido: la caminata a la espera es corta). Las
        celdas interiores quedan solo como ultimo recurso."""
        dist = self._distancias(self.descargas or self.muelles)
        candidatas = [(x, y) for y in range(self.alto) for x in range(self.ancho)
                      if self.motivo_invalida((x, y)) is None]

        def vecinos(c):
            return sum(1 for _ in self._vecinos(c))

        # BK-25: la franja de circulacion DELANTE de las zonas de descarga (entre
        # los racks y los carriles) es por donde pasa todo el almacen. Es la mas
        # cercana, asi que ganaba siempre, y con flota grande los que esperaban la
        # tapaban entre todos (medido: 16 operarios, 60% del tiempo parados y
        # 23.910 rutas sin solucion). Queda como ULTIMO recurso.
        franja = self._franja_de_circulacion()

        candidatas.sort(key=lambda c: (c[1] in franja, vecinos(c) > 3,
                                       dist.get(c, 10 ** 6),
                                       vecinos(c), -c[1], c[0]))
        return candidatas

    def _franja_de_circulacion(self) -> Set[int]:
        """Filas entre el ultimo rack de picking y la primera celda de descarga."""
        if not self.picks or not self.descargas:
            return set()
        ultimo_pick = max(y for _, y in self.picks)
        primera_descarga = min(y for _, y in self.descargas)
        if primera_descarga <= ultimo_pick:
            return set()
        return set(range(ultimo_pick + 1, primera_descarga))

    def _distancias(self, origenes) -> Dict[Cell, int]:
        dist: Dict[Cell, int] = {}
        cola = deque()
        for o in origenes:
            dist[tuple(o)] = 0
            cola.append(tuple(o))
        while cola:
            c = cola.popleft()
            for n in self._vecinos(c):
                if n not in dist:
                    dist[n] = dist[c] + 1
                    cola.append(n)
        return dist

    def _sin_cortar_el_mapa(self, candidatas: List[Cell],
                            limite: Optional[int] = None) -> List[Cell]:
        """Acepta cada celda solo si, con ella (y las ya aceptadas) ocupadas,
        siguen conectados todos los puntos de pick, descargas y muelles."""
        criticas = self.picks | self.descargas | self.muelles
        aceptadas: List[Cell] = []
        for c in candidatas:
            if limite is not None and len(aceptadas) >= limite:
                break
            bloqueadas = set(aceptadas) | {c}
            if self._conectadas(criticas, bloqueadas):
                aceptadas.append(c)
            elif not self.automatica:
                self.avisos.append("La celda de espera %s dejaria incomunicada "
                                   "parte del almacen; se descarta." % (c,))
        return aceptadas

    def _conectadas(self, criticas: Set[Cell], bloqueadas: Set[Cell]) -> bool:
        objetivo = {c for c in criticas if c not in bloqueadas and self._dentro(c)
                    and self.es_transitable(*c)}
        if not objetivo:
            return True
        inicio = next(iter(sorted(objetivo)))
        vistos = {inicio}
        cola = deque([inicio])
        while cola:
            c = cola.popleft()
            for n in self._vecinos(c):
                if n not in vistos and n not in bloqueadas:
                    vistos.add(n)
                    cola.append(n)
        return objetivo <= vistos

    # ------------------------------------------------------------ asignacion

    def asignar(self, agent_id: str, desde: Cell,
                excluir: Iterable[Cell] = ()) -> Optional[Cell]:
        """Celda de espera libre mas cercana (por camino) para este agente.
        `excluir`: celdas que ya tienen duenio por otra via (BK-29: inicio)."""
        if agent_id in self.asignadas:
            return self.asignadas[agent_id]
        ocupadas = set(self.asignadas.values()) | {tuple(c) for c in excluir}
        libres = [c for c in self.celdas if c not in ocupadas]
        if not libres:
            return None
        dist = self._distancias([tuple(desde)])
        celda = min(libres, key=lambda c: (dist.get(c, 10 ** 6), c[1], c[0]))
        self.asignadas[agent_id] = celda
        return celda

    def liberar(self, agent_id: str) -> None:
        self.asignadas.pop(agent_id, None)

    def celda_de(self, agent_id: str) -> Optional[Cell]:
        return self.asignadas.get(agent_id)
