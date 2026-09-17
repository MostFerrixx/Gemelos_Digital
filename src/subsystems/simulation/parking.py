# -*- coding: utf-8 -*-
"""
Estacionamientos de equipos.  (INIT-11 F2)

Donde viven las maquinas cuando nadie las usa. Una persona que necesita otro
equipo va hasta un estacionamiento, deja el que lleva y toma el otro; si no
hay unidad libre o no hay lugar para dejar la suya, ese trabajo no se le
asigna (en la realidad tampoco podria hacerlo).

Bloque de configuracion (opcional; sin el, nadie cambia de equipo):

    "estacionamientos": {
      "EST-1": {"x": 2, "y": 28, "capacidad": 4, "admite": ["grua"]}
    }

`admite` ausente = admite cualquier equipo. Las coordenadas se validan contra
el mapa, igual que las zonas de salida y los muelles.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Estacionamiento:
    """Un punto del mapa con lugar para N equipos."""

    def __init__(self, id_punto: str, celda, capacidad: int, admite: Optional[List[str]]):
        self.id = id_punto
        self.celda = celda                      # (x, y) en grilla
        self.capacidad = capacidad
        self.admite = admite                    # None = cualquiera
        self.guardados: List[str] = []          # ids de equipo estacionados

    def acepta(self, equipo_id: str) -> bool:
        if self.admite is not None and equipo_id not in self.admite:
            return False
        return len(self.guardados) < self.capacidad

    def tiene(self, equipo_id: str) -> bool:
        return equipo_id in self.guardados

    def __repr__(self):
        return "Estacionamiento(%s, %s, %d/%d)" % (
            self.id, self.celda, len(self.guardados), self.capacidad)


class GestorEstacionamientos:
    """Inventario de equipos libres repartido por los estacionamientos."""

    def __init__(self, configuracion: Dict[str, Any], equipos: Dict[str, Dict[str, Any]],
                 en_uso: Dict[str, int] = None, layout_manager: Any = None):
        self.equipos = equipos or {}
        self.puntos: Dict[str, Estacionamiento] = {}
        self.avisos: List[str] = []
        self._ilimitados = {eid for eid, e in self.equipos.items()
                            if e.get('cantidad') is None}

        self._cargar_puntos((configuracion or {}).get('estacionamientos') or {},
                            layout_manager)
        self._repartir_unidades_libres(en_uso or {})
        for aviso in self.avisos:
            logger.warning("[WARN][CONFIG] %s", aviso)

    # ------------------------------------------------------------------ carga

    def _cargar_puntos(self, bloque, layout_manager):
        if not isinstance(bloque, dict):
            self.avisos.append("'estacionamientos' debe ser un objeto "
                               "{id: {x, y, capacidad, admite}}.")
            return
        for id_punto, definicion in bloque.items():
            definicion = definicion if isinstance(definicion, dict) else {}
            try:
                celda = (int(definicion['x']), int(definicion['y']))
            except (KeyError, TypeError, ValueError):
                self.avisos.append("El estacionamiento '%s' no tiene coordenadas "
                                   "(x, y) validas; se descarta." % id_punto)
                continue
            if not self._celda_valida(celda, layout_manager):
                self.avisos.append(
                    "El estacionamiento '%s' esta en %s, que no es una celda "
                    "transitable del mapa; se descarta." % (id_punto, celda))
                continue
            try:
                capacidad = int(definicion.get('capacidad', 1))
            except (TypeError, ValueError):
                capacidad = 1
            admite = definicion.get('admite')
            if admite is not None and not isinstance(admite, list):
                admite = [admite]
            if admite is not None:
                desconocidos = [e for e in admite if e not in self.equipos]
                if desconocidos:
                    self.avisos.append(
                        "El estacionamiento '%s' admite equipos que no existen "
                        "(%s); se ignoran." % (id_punto, ", ".join(map(str, desconocidos))))
                    admite = [e for e in admite if e in self.equipos]
            self.puntos[id_punto] = Estacionamiento(
                id_punto, celda, max(1, capacidad), admite)

    @staticmethod
    def _celda_valida(celda, layout_manager) -> bool:
        if layout_manager is None:
            return True                      # sin mapa (tests): no se valida
        x, y = celda
        ancho = getattr(layout_manager, 'grid_width', None)
        alto = getattr(layout_manager, 'grid_height', None)
        if ancho is not None and alto is not None:
            if not (0 <= x < ancho and 0 <= y < alto):
                return False
        comprobar = getattr(layout_manager, 'is_walkable', None)
        return bool(comprobar(x, y)) if callable(comprobar) else True

    def _repartir_unidades_libres(self, en_uso: Dict[str, int]):
        """Las unidades que nadie tiene en la mano arrancan estacionadas."""
        for equipo_id, equipo in self.equipos.items():
            cantidad = equipo.get('cantidad')
            if cantidad is None:
                continue                     # sin limite: siempre hay una libre
            libres = int(cantidad) - int(en_uso.get(equipo_id, 0))
            for _ in range(max(0, libres)):
                punto = self._punto_con_lugar(equipo_id)
                if punto is None:
                    self.avisos.append(
                        "No hay estacionamiento con lugar para una unidad libre "
                        "de '%s'; esa unidad queda fuera de juego." % equipo_id)
                    break
                punto.guardados.append(equipo_id)

    def _punto_con_lugar(self, equipo_id: str) -> Optional[Estacionamiento]:
        for punto in self.puntos.values():
            if punto.acepta(equipo_id):
                return punto
        return None

    # --------------------------------------------------------------- consulta

    def hay_disponible(self, equipo_id: Optional[str]) -> bool:
        """True si alguien podria tomar ese equipo ahora mismo."""
        if equipo_id is None or equipo_id in self._ilimitados:
            return True
        return any(p.tiene(equipo_id) for p in self.puntos.values())

    def punto_para_cambio(self, equipo_actual: Optional[str],
                          equipo_nuevo: Optional[str]) -> Optional[Estacionamiento]:
        """Estacionamiento donde la persona puede dejar el equipo que lleva y
        tomar el que necesita. Devuelve None si no existe tal lugar."""
        if equipo_actual == equipo_nuevo:
            return None
        candidatos = []
        for punto in self.puntos.values():
            if equipo_nuevo is not None and equipo_nuevo not in self._ilimitados \
                    and not punto.tiene(equipo_nuevo):
                continue
            if equipo_actual is not None and equipo_actual not in self._ilimitados:
                # Ojo: al sacar el equipo nuevo se libera un lugar.
                libera = 1 if (equipo_nuevo is not None and punto.tiene(equipo_nuevo)) else 0
                admitido = (punto.admite is None or equipo_actual in punto.admite)
                if not admitido or len(punto.guardados) - libera >= punto.capacidad:
                    continue
            candidatos.append(punto)
        if not candidatos:
            return None
        # Determinista: el de id menor entre los que sirven.
        return min(candidatos, key=lambda p: p.id)

    # ---------------------------------------------------------------- cambios

    def ejecutar_cambio(self, punto: Estacionamiento, equipo_actual: Optional[str],
                        equipo_nuevo: Optional[str]) -> None:
        """Aplica el intercambio en el inventario del punto."""
        if equipo_nuevo is not None and punto.tiene(equipo_nuevo):
            punto.guardados.remove(equipo_nuevo)
        if equipo_actual is not None and equipo_actual not in self._ilimitados:
            punto.guardados.append(equipo_actual)

    def tiempo_de_cambio(self, equipo_actual: Optional[str],
                         equipo_nuevo: Optional[str]) -> float:
        """Segundos que cuesta dejar uno y tomar el otro (`tiempo_cambio_s`)."""
        total = 0.0
        for equipo_id in (equipo_actual, equipo_nuevo):
            if equipo_id is None:
                continue
            equipo = self.equipos.get(equipo_id) or {}
            total += float(equipo.get('tiempo_cambio_s', 30.0))
        return total
