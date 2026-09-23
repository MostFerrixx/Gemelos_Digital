# -*- coding: utf-8 -*-
"""
Donde empieza el turno cada operario.  (BK-29, decision del Director 2026-09-23)

Antes todos nacian alrededor de la primera celda de la zona de salida 1, que
desde BK-25 es un puesto de descarga: con semilla 42 los 4 del canonico
arrancaban en un puesto, en una SALIDA de un solo sentido, en la entrada y
dentro del carril. Cada corrida empezaba con un choque.

Ahora cada operario nace en una celda propia, resuelta con una cadena (manda
el primer nivel que tenga lugar para el):

  1. `inicio_turno.zonas`: rectangulos que define el cliente (sala de
     inicio, oficina de fichaje...).
  2. El estacionamiento de su equipo (INIT-11 F2): el montacargas arranca
     donde se carga. Un estacionamiento es UNA celda con lugar para varias
     maquinas, asi que se usa como ancla y se toman las celdas validas mas
     cercanas (hasta `inicio_turno.radio_estacionamiento`).
  3. Respaldo automatico: las celdas de espera de los ociosos (BK-15), que ya
     estan validadas en cualquier mapa. El operario arranca "ocioso en su
     celda de espera", exactamente el estado al que vuelve sin trabajo.

Toda celda de inicio pasa las MISMAS reglas que una celda de espera (no es
carril, ni salida, ni acceso, ni boca de pasillo) y el conjunto no puede
dejar incomunicada ninguna parte del almacen.

Bloque de configuracion (opcional):

    "inicio_turno": {
      "zonas": {"INI-1": {"x": 0, "y": 28, "ancho": 2, "alto": 2}},
      "usar_estacionamientos": true,
      "radio_estacionamiento": 6
    }

Modulo puro: no conoce SimPy ni mueve agentes.
"""

import logging
from typing import Callable, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

Cell = Tuple[int, int]

RADIO_ESTACIONAMIENTO_DEFAULT = 6


class GestorInicioTurno:
    """Asigna a cada operario su celda de inicio (una por operario)."""

    def __init__(self, configuracion, zonas_espera, estacionamientos=None):
        bloque = (configuracion or {}).get('inicio_turno') or {}
        if not isinstance(bloque, dict):
            bloque = {}
        self.ze = zonas_espera
        self.estacionamientos = estacionamientos
        self.avisos: List[str] = []
        self.tomadas: Dict[str, Cell] = {}
        self.origen: Dict[str, str] = {}
        self.usar_estacionamientos = bool(bloque.get('usar_estacionamientos', True))
        try:
            self.radio = int(bloque.get('radio_estacionamiento',
                                        RADIO_ESTACIONAMIENTO_DEFAULT))
        except (TypeError, ValueError):
            self.radio = RADIO_ESTACIONAMIENTO_DEFAULT
            self.avisos.append("inicio_turno.radio_estacionamiento no es un "
                               "numero; se usa %d." % self.radio)
        self.celdas_zonas: List[Cell] = self._celdas_de_zonas(bloque.get('zonas') or {})
        self._avisado_lleno = False
        for aviso in self.avisos:
            logger.warning("[WARN][CONFIG] %s", aviso)

    # ------------------------------------------------------------- reglas

    def _celdas_de_zonas(self, zonas) -> List[Cell]:
        celdas: List[Cell] = []
        if not isinstance(zonas, dict):
            self.avisos.append("inicio_turno.zonas debe ser un objeto "
                               "{id: {x, y, ancho, alto}}.")
            return celdas
        for zona_id, d in zonas.items():
            d = d if isinstance(d, dict) else {}
            try:
                x, y = int(d['x']), int(d['y'])
                w, h = int(d.get('ancho', 1)), int(d.get('alto', 1))
            except (KeyError, TypeError, ValueError):
                self.avisos.append("La zona de inicio '%s' no tiene x, y validos; "
                                   "se descarta." % zona_id)
                continue
            descartadas = []
            for yy in range(y, y + max(1, h)):
                for xx in range(x, x + max(1, w)):
                    motivo = self.ze.motivo_invalida((xx, yy))
                    if motivo:
                        descartadas.append("(%d, %d) %s" % (xx, yy, motivo))
                    elif (xx, yy) not in celdas:
                        celdas.append((xx, yy))
            if descartadas:
                self.avisos.append("Zona de inicio '%s': se descartan celdas: %s."
                                   % (zona_id, "; ".join(descartadas)))
        return celdas

    def _libre(self, c: Cell) -> bool:
        """Valida, sin duenio, y sin cortar el mapa junto con las ya tomadas."""
        c = tuple(c)
        if self.ze.motivo_invalida(c) is not None:
            return False
        if c in self.tomadas.values() or c in self.ze.asignadas.values():
            return False
        criticas = self.ze.picks | self.ze.descargas | self.ze.muelles
        bloqueadas = set(self.tomadas.values()) | set(self.ze.asignadas.values()) | {c}
        return self.ze._conectadas(criticas, bloqueadas)

    # ------------------------------------------------------------- niveles

    def _de_zonas(self, agent_id, equipo_id, ancla) -> Optional[Cell]:
        return next((c for c in self.celdas_zonas if self._libre(c)), None)

    def _de_estacionamiento(self, agent_id, equipo_id, ancla) -> Optional[Cell]:
        if not self.usar_estacionamientos or self.estacionamientos is None:
            return None
        puntos = [p for p in self.estacionamientos.puntos.values()
                  if p.admite is None or equipo_id in p.admite]
        for punto in puntos:
            dist = self.ze._distancias([tuple(punto.celda)])
            cerca = sorted((d, c[1], c[0]) for c, d in dist.items() if d <= self.radio)
            celda = next(((x, y) for _, y, x in cerca if self._libre((x, y))), None)
            if celda is not None:
                return celda
        if puntos:
            logger.warning("[WARN][INICIO-TURNO] %s: no hay celda libre a %d celdas "
                           "de su estacionamiento; se usa el respaldo.",
                           agent_id, self.radio)
        return None

    def _de_espera(self, agent_id, equipo_id, ancla) -> Optional[Cell]:
        excluir = set(self.tomadas.values())
        celda = self.ze.asignar(agent_id, ancla, excluir=excluir)
        if celda is not None and not self._conecta_con(celda):
            self.ze.liberar(agent_id)
            return None
        return celda

    def _conecta_con(self, celda: Cell) -> bool:
        criticas = self.ze.picks | self.ze.descargas | self.ze.muelles
        bloqueadas = set(self.tomadas.values()) | set(self.ze.asignadas.values())
        return self.ze._conectadas(criticas, bloqueadas | {tuple(celda)})

    def _cualquiera_cerca(self, agent_id, equipo_id, ancla) -> Optional[Cell]:
        """Ultimo recurso: la celda valida libre mas cercana al ancla."""
        dist = self.ze._distancias([tuple(ancla)])
        orden = sorted((d, c[1], c[0]) for c, d in dist.items())
        return next(((x, y) for _, y, x in orden if self._libre((x, y))), None)

    def _niveles(self) -> Iterator[Tuple[str, Callable]]:
        yield 'inicio_turno', self._de_zonas
        yield 'estacionamiento', self._de_estacionamiento
        yield 'espera', self._de_espera
        yield 'cercana', self._cualquiera_cerca

    # ----------------------------------------------------------- asignacion

    def celda_para(self, agent_id: str, equipo_id: Optional[str],
                   ancla: Cell) -> Optional[Cell]:
        """Celda de inicio de este operario (siempre la misma para el).
        `ancla` = referencia para elegir entre celdas equivalentes (la zona
        de salida 1, donde nacian antes). None si el mapa no tiene lugar."""
        if agent_id in self.tomadas:
            return self.tomadas[agent_id]
        # Evaluacion perezosa: el primer nivel que devuelve celda gana.
        origen, celda = next(((nombre, c) for nombre, nivel in self._niveles()
                              for c in [nivel(agent_id, equipo_id, tuple(ancla))]
                              if c is not None), (None, None))
        if celda is None:
            if not self._avisado_lleno:
                self._avisado_lleno = True
                logger.warning("[WARN][INICIO-TURNO] no hay celdas de inicio para "
                               "todos: %s y los que siguen arrancan en la zona de "
                               "salida 1 (pueden chocar).", agent_id)
            return None
        self.tomadas[agent_id] = tuple(celda)
        self.origen[agent_id] = origen
        return tuple(celda)

    def resumen(self) -> Dict[str, object]:
        return {'celdas': dict(self.tomadas), 'origen': dict(self.origen),
                'avisos': list(self.avisos)}

    def __repr__(self):
        return "GestorInicioTurno(%d zonas de inicio, estacionamientos=%s)" % (
            len(self.celdas_zonas), self.estacionamientos is not None)
