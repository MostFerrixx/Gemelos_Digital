# -*- coding: utf-8 -*-
"""
Flota: resolucion unica de que agentes existen y con que capacidad. (BK-06 / F2)

PROBLEMA QUE RESUELVE
---------------------
La flota estaba definida en DOS lugares que no se hablaban:

* `operators.crear_operarios()` la instanciaba, con las capacidades
  **hardcodeadas** (150 / 1000) cuando `agent_types` venia vacio.
* `warehouse.__init__` derivaba `operator_capacities` leyendo SOLO
  `agent_types`, asi que con el canonico (`agent_types: []`) quedaba ciega y
  dimensionaba TODAS las areas con un default de 150 -- incluidas las de
  montacargas, que cargan 1000. Ese es el bug BK-06.

Ademas el almacen se construye ANTES que los operarios, asi que no puede
"preguntarle" a la flota: necesita resolverla desde la configuracion.

Este modulo es esa resolucion, y la usan los dos lados. Una sola definicion de
flota, sin numeros magicos repartidos por el motor.

CONFIGURABILIDAD (principio rector #2)
--------------------------------------
Las capacidades del fallback dejan de estar hardcodeadas en el codigo: salen de
`fleet_defaults` en config.json, editable por el cliente. Los defaults del
modulo reproducen EXACTAMENTE el comportamiento historico, asi que una config
sin el bloque se comporta igual que siempre.
"""

import copy
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Defaults historicos (los que estaban hardcodeados en operators.crear_operarios).
# Cambiarlos aca cambia el comportamiento de configs sin `fleet_defaults`.
HISTORIC_FLEET_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "GroundOperator": {
        "capacity": 150,
        "discharge_time": 5,
        "work_area_priorities": {"Area_Ground": 1, "Area_High": 2, "Area_Special": 3},
    },
    "Forklift": {
        "capacity": 1000,
        "discharge_time": 5,
        "work_area_priorities": {"Area_High": 1, "Area_Special": 2},
    },
}

# Conteos por defecto del fallback legacy (identicos a los historicos).
_DEFAULT_COUNTS = {"num_operarios_terrestres": 2, "num_montacargas": 1}


def get_fleet_defaults(configuracion: Optional[Dict[str, Any]],
                       agent_type: str) -> Dict[str, Any]:
    """Parametros por defecto de un tipo de agente.

    Orden: `fleet_defaults[tipo]` de config -> defaults historicos del modulo.
    El merge es por clave, asi que el cliente puede sobreescribir solo la
    capacidad y heredar el resto.
    """
    base = copy.deepcopy(HISTORIC_FLEET_DEFAULTS.get(agent_type, {}))
    bloque = (configuracion or {}).get('fleet_defaults', {})
    if isinstance(bloque, dict):
        override = bloque.get(agent_type)
        if isinstance(override, dict):
            for clave, valor in override.items():
                base[clave] = copy.deepcopy(valor)
    return base


def resolver_flota(configuracion: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Devuelve la especificacion de la flota: una entrada por AGENTE.

    Cada entrada: {type, capacity, discharge_time, work_area_priorities}.

    Fuente: `agent_types` si tiene contenido; si esta vacio, el fallback legacy
    por contadores (`num_operarios_terrestres` / `num_montacargas`), que es lo
    que usa el config.json canonico.

    El ORDEN importa (fija `spawn_index` y los IDs): en el fallback, primero
    todos los terrestres y despues todos los montacargas, igual que el
    comportamiento historico.
    """
    configuracion = configuracion or {}
    agent_types = configuracion.get('agent_types', [])

    flota: List[Dict[str, Any]] = []

    if agent_types:
        for agent_config in agent_types:
            tipo = agent_config.get('type', 'GroundOperator')
            defaults = get_fleet_defaults(configuracion, tipo)
            flota.append({
                "type": tipo,
                "capacity": agent_config.get('capacity', defaults.get('capacity', 150)),
                "discharge_time": agent_config.get(
                    'discharge_time', defaults.get('discharge_time', 5)),
                "work_area_priorities": agent_config.get(
                    'work_area_priorities',
                    defaults.get('work_area_priorities', {})),
            })
        return flota

    # --- Fallback legacy por contadores (el caso del config.json canonico) ---
    n_ground = configuracion.get('num_operarios_terrestres',
                                 _DEFAULT_COUNTS['num_operarios_terrestres'])
    n_fork = configuracion.get('num_montacargas',
                               _DEFAULT_COUNTS['num_montacargas'])

    for tipo, cantidad in (("GroundOperator", n_ground), ("Forklift", n_fork)):
        defaults = get_fleet_defaults(configuracion, tipo)
        for _ in range(int(cantidad or 0)):
            flota.append({
                "type": tipo,
                "capacity": defaults.get('capacity'),
                "discharge_time": defaults.get('discharge_time'),
                "work_area_priorities": copy.deepcopy(
                    defaults.get('work_area_priorities', {})),
            })

    return flota


def capacidades_por_tipo(configuracion: Optional[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """{tipo de agente: [capacidades de cada agente de ese tipo]} segun la flota real."""
    resultado: Dict[str, List[Any]] = {}
    for agente in resolver_flota(configuracion):
        resultado.setdefault(agente['type'], []).append(agente['capacity'])
    return resultado


def capacidades_por_area(configuracion: Optional[Dict[str, Any]]):
    """Capacidad de dimensionado de WorkOrders por area.  (BK-06 F2)

    Devuelve `(capacidades, fallback_global)`:
      * `capacidades`: {area: capacidad} para cada area conocida.
      * `fallback_global`: capacidad a usar en un area no listada.

    La capacidad de un area sale de los agentes cuyo tipo el mapa
    `work_area_equipment` asigna a ESA area, tomando el **minimo** de sus
    capacidades (red de seguridad): asi toda WO generada cabe en CUALQUIER
    agente que pueda tomarla, y el bucle de WOs irrecogibles se vuelve
    imposible por construccion.

    Sin flota, se cae al historico 150 para no alterar configs degeneradas.
    """
    from core.work_areas import expected_equipment_for_area, get_work_area_equipment

    flota = resolver_flota(configuracion)

    caps_por_tipo: Dict[str, List[Any]] = {}
    for agente in flota:
        caps_por_tipo.setdefault(agente['type'], []).append(agente['capacity'])

    # Areas a considerar: las del mapa explicito + las declaradas por la flota.
    areas = set(get_work_area_equipment(configuracion).keys())
    for agente in flota:
        areas.update((agente.get('work_area_priorities') or {}).keys())

    capacidades: Dict[str, Any] = {}
    for area in areas:
        tipo_requerido = expected_equipment_for_area(configuracion, area)
        disponibles = caps_por_tipo.get(tipo_requerido, [])
        if disponibles:
            capacidades[area] = min(disponibles)

    todas = [a['capacity'] for a in flota if a.get('capacity') is not None]
    fallback_global = min(todas) if todas else 150

    return capacidades, fallback_global
