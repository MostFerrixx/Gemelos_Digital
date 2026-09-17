# -*- coding: utf-8 -*-
"""
Areas de trabajo: quien puede operar en cada area.  (BK-06 / F1)

FUENTE UNICA DE VERDAD del mapa `work_area_equipment` (MEJ-3 QA-3 Opcion B).

Antes de BK-06 esta logica estaba COPIADA en tres lugares
(`event_generator._expected_equipment_for_area`,
`config_manager._expected_equipment_for_area`, `fleet-manager.js`) y, peor,
NINGUNO de ellos era el hot-path de simulacion: el motor decidia la
compatibilidad de un agente con un area mirando solo `work_area_priorities`,
que puede contradecir el mapa. Esa contradiccion es la causa raiz de BK-06
(ver `docs/PLAN_BK06_CAPACIDAD_AREA.md`): un operario terrestre se declaraba
apto para un area de montacargas y recibia WorkOrders que no podia levantar.

Regla: **el mapa manda**. `work_area_priorities` pasa a significar solo lo que
su nombre dice (orden de preferencia entre las areas que el agente PUEDE
servir), no quien puede servir que.

Configurabilidad: el mapa es 100% editable por el cliente desde la UI (tab
Flota). Si quiere que un area la atienda otro tipo de equipo, cambia el mapa;
no hay nada hardcodeado que deba tocar un desarrollador.
"""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

VALID_EQUIPMENT = ('GroundOperator', 'Forklift')

# Fallback historico de migracion: configs viejas sin el mapa explicito.
_GROUND_AREA_RE = re.compile(r'ground|piso|floor|suelo|terrestre|level[_-]?0|l0', re.I)


def equipment_by_naming(area: Any) -> str:
    """Tipo capaz de un area por CONVENCION DE NOMBRES.

    Solo fallback para configs viejas sin `work_area_equipment`.
    """
    return 'GroundOperator' if _GROUND_AREA_RE.search(str(area)) else 'Forklift'


def get_work_area_equipment(configuracion: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Devuelve el mapa area -> tipo de equipo (dict vacio si no hay o es invalido)."""
    wae = (configuracion or {}).get('work_area_equipment', {})
    return wae if isinstance(wae, dict) else {}


def expected_equipment_for_area(configuracion: Optional[Dict[str, Any]], area: Any) -> str:
    """Tipo de agente que corresponde a un area.

    Prioridad: mapa explicito `work_area_equipment` -> convencion de nombres.
    """
    tipo = get_work_area_equipment(configuracion).get(area)
    return tipo if tipo else equipment_by_naming(area)


def equipo_sirve(requerido: Any, tipo_base: str, equipo_id: Optional[str] = None) -> bool:
    """El mapa puede pedir un TIPO BASE ('Forklift') o un EQUIPO concreto
    ('grua_trilateral', INIT-11 F1). Un agente sirve si coincide con cualquiera
    de los dos: el mapa historico sigue valiendo y el cliente puede afinarlo
    por equipo cuando declara `equipos`."""
    return requerido == tipo_base or (equipo_id is not None and requerido == equipo_id)


def effective_work_area_priorities(configuracion: Optional[Dict[str, Any]],
                                   agent_type: str,
                                   declared_priorities: Optional[Dict[str, int]],
                                   agent_id: str = None,
                                   equipo_id: str = None) -> Dict[str, int]:
    """Filtra las prioridades declaradas de un agente dejando SOLO las areas
    que el mapa le asigna a su tipo.

    Es el punto unico por el que el motor entero (dispatcher,
    assignment_calculator, event_generator) hereda la regla: todos consultan
    `get_priority_for_work_area` / `can_handle_work_area`, que leen este dict.

    Emite un [WARN] por cada area descartada: hace VISIBLE una incoherencia de
    configuracion que antes era invisible (y que costo dos corridas detectar).
    """
    declaradas = declared_priorities or {}
    efectivas: Dict[str, int] = {}
    descartadas = []

    for area, prioridad in declaradas.items():
        esperado = expected_equipment_for_area(configuracion, area)
        if equipo_sirve(esperado, agent_type, equipo_id):
            efectivas[area] = prioridad
        else:
            descartadas.append((area, esperado))

    if descartadas:
        detalle = ", ".join("%s(->%s)" % (a, t) for a, t in descartadas)
        logger.warning(
            "[WARN][CONFIG] %s (%s) declara prioridad en areas que "
            "work_area_equipment asigna a otro equipo: %s. Se IGNORAN (el mapa "
            "manda). Si el area deberia atenderla este tipo de agente, "
            "corregi work_area_equipment en el tab Flota.",
            agent_id or agent_type, agent_type, detalle)

    if not efectivas and declaradas:
        logger.warning(
            "[WARN][CONFIG] %s (%s) quedo SIN NINGUN area asignable tras "
            "aplicar work_area_equipment. Ese agente no va a recibir trabajo.",
            agent_id or agent_type, agent_type)

    return efectivas
