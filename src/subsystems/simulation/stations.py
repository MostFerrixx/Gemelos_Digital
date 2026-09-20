# -*- coding: utf-8 -*-
"""
BK-25 F1.c: la zona de descarga como ESTACION CON TURNO.

Decision del Director (2026-09-19), dibujada en el plan de la iniciativa
(`docs/PLAN_BK25_ESTACION_DESCARGA.md`):

- Un carril de descarga de 2 columnas admite DOS operarios a la vez, uno por
  columna: cada columna es un PUESTO.
- Se entra por el frente (la celda del anden que da a la columna).
- Se sale por EL COSTADO: el puesto de la izquierda sale por la izquierda y el
  de la derecha por la derecha. Las salidas son de un solo sentido y nadie
  puede detenerse en ellas.
- Quien no tiene turno espera en la FILA (delante de su puesto, en el anden) y,
  si la fila esta llena, en el pulmon (las zonas de espera de BK-15).

Este modulo solo DEDUCE y GUARDA esa geometria y reparte los turnos. No mueve
agentes ni conoce SimPy: es testeable en aislamiento.
"""
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

Celda = Tuple[int, int]


class Estacion:
    """Geometria y turnos de una zona de descarga."""

    def __init__(self, staging_id: int, celdas: Sequence[Celda],
                 entradas: Dict[int, Celda], salidas: Dict[int, Celda],
                 colas: Dict[int, List[Celda]], avisos: Sequence[str] = ()):
        self.staging_id = int(staging_id)
        self.celdas = [tuple(c) for c in celdas]
        # Un puesto por COLUMNA: {x: [celdas de la columna, del frente al fondo]}
        self.puestos: Dict[int, List[Celda]] = {}
        for (x, y) in self.celdas:
            self.puestos.setdefault(x, []).append((x, y))
        for x in self.puestos:
            self.puestos[x].sort(key=lambda c: c[1])
        self.entradas = dict(entradas)        # {x del puesto: celda de entrada}
        self.salidas = dict(salidas)          # {x del puesto: celda de salida}
        self.colas = {x: list(v) for x, v in colas.items()}
        self.avisos = list(avisos)
        self.ocupante: Dict[int, Optional[str]] = {x: None for x in self.puestos}

    # ---------------------------------------------------------------- turnos
    def puesto_libre(self) -> Optional[int]:
        """Primer puesto sin ocupante (orden estable por columna)."""
        for x in sorted(self.ocupante):
            if self.ocupante[x] is None:
                return x
        return None

    def tomar(self, agent_id: str, puesto_x: Optional[int] = None) -> Optional[int]:
        """Asigna un puesto al agente. Devuelve la columna, o None si no hay."""
        actual = self.puesto_de(agent_id)
        if actual is not None:
            return actual
        x = puesto_x if puesto_x is not None else self.puesto_libre()
        if x is None or self.ocupante.get(x) is not None:
            return None
        self.ocupante[x] = agent_id
        return x

    def puesto_de(self, agent_id: str) -> Optional[int]:
        for x, quien in self.ocupante.items():
            if quien == agent_id:
                return x
        return None

    def liberar(self, agent_id: str) -> Optional[int]:
        x = self.puesto_de(agent_id)
        if x is not None:
            self.ocupante[x] = None
        return x

    # ------------------------------------------------------------- consultas
    def celda_de_trabajo(self, puesto_x: int) -> Optional[Celda]:
        """Celda donde se descarga: el FRENTE de la columna (sin outbound, la
        unica; con outbound, el hueco libre lo decide `outbound.StagingZone`)."""
        celdas = self.puestos.get(puesto_x) or []
        return celdas[0] if celdas else None

    def celdas_de_fila(self, puesto_x: int) -> List[Celda]:
        return list(self.colas.get(puesto_x) or [])

    def es_salida(self, celda: Celda) -> bool:
        return tuple(celda) in set(self.salidas.values())

    def __repr__(self):
        return ("Estacion(id=%d, puestos=%s, entradas=%s, salidas=%s)"
                % (self.staging_id, sorted(self.puestos), self.entradas, self.salidas))


class GestorEstaciones:
    """Construye una `Estacion` por zona de descarga a partir del mapa."""

    def __init__(self, zonas: Dict[int, Sequence[Celda]],
                 es_transitable: Callable[[int, int], bool],
                 ancho: int, alto: int,
                 picks: Iterable[Celda] = (),
                 cola_max: int = 1):
        self.es_transitable = es_transitable
        self.ancho, self.alto = int(ancho), int(alto)
        self.picks = {tuple(p) for p in picks if p}
        self.cola_max = max(0, int(cola_max))
        self.avisos: List[str] = []
        todas = {tuple(c) for celdas in zonas.values() for c in celdas}
        self.estaciones: Dict[int, Estacion] = {}
        for sid in sorted(zonas):
            celdas = [tuple(c) for c in zonas[sid] if c]
            if not celdas:
                continue
            self.estaciones[sid] = self._deducir(sid, celdas, todas)

    # ------------------------------------------------------------- deduccion
    def _libre(self, celda: Celda, ocupadas) -> bool:
        x, y = celda
        return (0 <= x < self.ancho and 0 <= y < self.alto
                and self.es_transitable(x, y)
                and celda not in ocupadas
                and celda not in self.picks)

    def _deducir(self, sid: int, celdas: List[Celda], todas_las_zonas) -> Estacion:
        avisos: List[str] = []
        columnas: Dict[int, List[Celda]] = {}
        for (x, y) in celdas:
            columnas.setdefault(x, []).append((x, y))
        for x in columnas:
            columnas[x].sort(key=lambda c: c[1])

        # El FRENTE es el lado por el que se puede entrar: arriba (y-1) si esa
        # celda esta libre; si no, abajo (y+1). Zonas de una sola celda: igual.
        y_min = min(y for _, y in celdas)
        y_max = max(y for _, y in celdas)
        arriba_libre = any(self._libre((x, y_min - 1), todas_las_zonas) for x in columnas)
        abajo_libre = any(self._libre((x, y_max + 1), todas_las_zonas) for x in columnas)
        frente_arriba = arriba_libre or not abajo_libre
        if not arriba_libre and not abajo_libre:
            avisos.append("zona %d: no tiene entrada posible por el frente" % sid)

        x_min, x_max = min(columnas), max(columnas)
        entradas: Dict[int, Celda] = {}
        salidas: Dict[int, Celda] = {}
        colas: Dict[int, List[Celda]] = {}
        for x in sorted(columnas):
            columna = columnas[x] if frente_arriba else list(reversed(columnas[x]))
            fx, fy = columna[0]
            entrada = (fx, fy - 1) if frente_arriba else (fx, fy + 1)
            if self._libre(entrada, todas_las_zonas):
                entradas[x] = entrada
            else:
                avisos.append("zona %d, puesto %d: la celda de entrada %s no sirve"
                              % (sid, x, entrada))

            # Salida por SU costado: el puesto mas a la izquierda sale a la
            # izquierda; el mas a la derecha, a la derecha. Si la zona tiene
            # una sola columna, se intenta primero la izquierda.
            lados = [(x - 1, 0)] if x == x_min else []
            if x == x_max:
                lados.append((x + 1, 0))
            if not lados:
                lados = [(x - 1, 0), (x + 1, 0)]     # columna del medio
            elegida = None
            for (sx, _) in lados:
                candidata = (sx, fy)
                if self._libre(candidata, todas_las_zonas):
                    elegida = candidata
                    break
            if elegida is not None:
                salidas[x] = elegida
            else:
                avisos.append("zona %d, puesto %d: no tiene salida lateral" % (sid, x))

            colas[x] = self._deducir_cola(entradas.get(x), frente_arriba,
                                          todas_las_zonas, salidas)
            if self.cola_max and not colas[x]:
                avisos.append("zona %d, puesto %d: no hay lugar para la fila" % (sid, x))
        return Estacion(sid, celdas, entradas, salidas, colas, avisos)

    def _deducir_cola(self, entrada: Optional[Celda], frente_arriba: bool,
                      ocupadas, salidas: Dict[int, Celda]) -> List[Celda]:
        """La fila arranca EN la entrada y sigue alejandose de la zona."""
        if entrada is None or self.cola_max <= 0:
            return []
        paso = -1 if frente_arriba else 1
        cola: List[Celda] = []
        x, y = entrada
        for i in range(self.cola_max):
            celda = (x, y + paso * i)
            if not self._libre(celda, ocupadas) or celda in set(salidas.values()):
                break
            cola.append(celda)
        return cola

    # -------------------------------------------------------------- consulta
    def estacion(self, staging_id: int) -> Optional[Estacion]:
        return self.estaciones.get(int(staging_id))

    def todas_las_salidas(self) -> Dict[Celda, int]:
        """{celda de salida: staging_id} -- las usa la capa de circulacion."""
        out: Dict[Celda, int] = {}
        for sid, est in self.estaciones.items():
            for celda in est.salidas.values():
                out[tuple(celda)] = sid
        return out

    def resumen(self) -> Dict[str, object]:
        return {
            'estaciones': len(self.estaciones),
            'puestos_totales': sum(len(e.puestos) for e in self.estaciones.values()),
            'cola_max': self.cola_max,
            'avisos': [a for e in self.estaciones.values() for a in e.avisos],
        }

    def __repr__(self):
        return "GestorEstaciones(%d zonas, %d puestos)" % (
            len(self.estaciones), sum(len(e.puestos) for e in self.estaciones.values()))
