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

    Cada entrada: {type, capacity, discharge_time, work_area_priorities,
    id, equipo, persona}. `type` es el TIPO BASE del equipo (como se comporta:
    GroundOperator o Forklift); `equipo` trae sus parametros fisicos
    (INIT-11 F1). `persona` es None en los modos historicos.

    Si el config trae `personas` (INIT-11 F1), la flota sale de ahi y de
    `equipos` (ver `resolver_personas`). Si no, de los modos historicos:

    Fuente: `agent_types` si tiene contenido; si esta vacio, el fallback legacy
    por contadores (`num_operarios_terrestres` / `num_montacargas`), que es lo
    que usa el config.json canonico.

    El ORDEN importa (fija `spawn_index` y los IDs): en el fallback, primero
    todos los terrestres y despues todos los montacargas, igual que el
    comportamiento historico.
    """
    configuracion = configuracion or {}

    if configuracion.get('personas'):
        if configuracion.get('agent_types'):
            logger.warning(
                "[WARN][CONFIG] El config define 'personas' y 'agent_types'. "
                "Manda 'personas' (modelo persona + equipo); agent_types se ignora.")
        flota, avisos = resolver_personas(configuracion)
        for aviso in avisos:
            logger.warning("[WARN][CONFIG] %s", aviso)
        return flota

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
        return _con_ids_historicos(
            [_con_equipo_implicito(configuracion, a) for a in flota])

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

    return _con_ids_historicos(
        [_con_equipo_implicito(configuracion, a) for a in flota])


# ---------------------------------------------------------------------------
# INIT-11 F1: personas y equipos separados
# ---------------------------------------------------------------------------
# Tipo base = COMO se comporta un equipo en el motor (secuencia de pick):
# GroundOperator trabaja a nivel de piso; Forklift sube y baja la horquilla.
TIPOS_BASE = ('GroundOperator', 'Forklift')


def _parametros_tiempo(configuracion: Dict[str, Any], tipo_base: str) -> Dict[str, float]:
    """Velocidad y horquilla por defecto de un tipo base: los mismos valores
    que el motor usaba antes de separar persona y equipo (bloque `tiempos`)."""
    tiempos = (configuracion or {}).get('tiempos', {}) or {}
    if tipo_base == 'Forklift':
        velocidad = tiempos.get('speed_factor_forklift', 0.5)   # BK-39: default Real
    else:
        velocidad = tiempos.get('speed_factor_ground', 1.0)
    return {
        'velocidad': float(velocidad),
        'horquilla_s': float(tiempos.get('tiempo_horquilla', 8.0)),
    }


# Prefijo de los ids historicos por tipo (GroundOp-01, Forklift-01...).
PREFIJOS_HISTORICOS = {"GroundOperator": "GroundOp", "Forklift": "Forklift"}


def _con_ids_historicos(flota: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ids de los modos historicos: numerados por tipo en orden de aparicion.
    Antes los ponia `crear_operarios`; vivir aca permite que el resto del
    motor sepa que agente es cual sin tener la lista de operarios."""
    contador: Dict[str, int] = {}
    for agente in flota:
        tipo = agente['type']
        if tipo not in PREFIJOS_HISTORICOS:
            continue  # tipo desconocido: crear_operarios lo descarta con aviso
        contador[tipo] = contador.get(tipo, 0) + 1
        agente['id'] = "%s-%02d" % (PREFIJOS_HISTORICOS[tipo], contador[tipo])
    return flota


def capacidad_por_agente(configuracion: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """{id de agente: capacidad} de la flota resuelta."""
    return {a['id']: a['capacity'] for a in resolver_flota(configuracion) if a.get('id')}


def _con_equipo_implicito(configuracion: Dict[str, Any],
                          agente: Dict[str, Any]) -> Dict[str, Any]:
    """Modo historico: cada agente lleva un equipo implicito cuyo nombre es su
    tipo. Los numeros son exactamente los de antes (equivalencia de F1)."""
    tipo = agente['type']
    agente['id'] = None
    agente['persona'] = None
    agente['equipo'] = dict(_parametros_tiempo(configuracion, tipo),
                            id=tipo, tipo_base=tipo, capacidad=agente['capacity'],
                            tiempo_cambio_s=30.0, cantidad=None)
    return agente


def resolver_equipos(configuracion: Optional[Dict[str, Any]]):
    """Catalogo de equipos declarado en `equipos`, con defaults completos.

    Devuelve `(equipos, avisos)`. Cada equipo:
    {id, tipo_base, capacidad, velocidad, horquilla_s, tiempo_cambio_s, cantidad}.
    Lo que no se declara sale de `fleet_defaults` y del bloque `tiempos`.
    `cantidad` None = sin limite de unidades.
    """
    configuracion = configuracion or {}
    bloque = configuracion.get('equipos') or {}
    equipos: Dict[str, Dict[str, Any]] = {}
    avisos: List[str] = []
    if not isinstance(bloque, dict):
        return equipos, ["'equipos' debe ser un objeto {nombre: definicion}."]

    for nombre, definicion in bloque.items():
        definicion = definicion if isinstance(definicion, dict) else {}
        tipo_base = definicion.get('tipo_base')
        if tipo_base not in TIPOS_BASE:
            avisos.append(
                "El equipo '%s' tiene tipo_base '%s'; debe ser uno de %s. "
                "Equipo descartado." % (nombre, tipo_base, ", ".join(TIPOS_BASE)))
            continue
        defaults = get_fleet_defaults(configuracion, tipo_base)
        tiempos = _parametros_tiempo(configuracion, tipo_base)
        cantidad = definicion.get('cantidad')
        equipos[nombre] = {
            'id': nombre,
            'tipo_base': tipo_base,
            'capacidad': definicion.get('capacidad', defaults.get('capacity')),
            'velocidad': float(definicion.get('velocidad', tiempos['velocidad'])),
            'horquilla_s': float(definicion.get('horquilla_s', tiempos['horquilla_s'])),
            # INIT-11 F2: segundos que cuesta tomarlo o dejarlo en el estacionamiento.
            'tiempo_cambio_s': float(definicion.get('tiempo_cambio_s', 30.0)),
            'cantidad': int(cantidad) if cantidad is not None else None,
        }
    return equipos, avisos


# INIT-11 F2: tipos de tarea que un perfil puede tomar HOY. El task path
# (traslado, actividad) los agrega en F3/F4.
TAREAS_VALIDAS = ('pick', 'putaway')

# Modos de la regla de cambio de perfil (ver `cambio_de_perfil`).
MODOS_CAMBIO = ('inmediato', 'agotar', 'umbral')


def resolver_perfiles(configuracion: Optional[Dict[str, Any]]):
    """Catalogo de perfiles declarado en `perfiles`.  (INIT-11 F2)

    Un perfil dice QUE tipos de tarea toma una persona y CON QUE equipo:
    {nombre: {tareas: [...], equipo: <clave de `equipos`> | None}}.
    Devuelve `(perfiles, avisos)`.
    """
    configuracion = configuracion or {}
    bloque = configuracion.get('perfiles') or {}
    perfiles: Dict[str, Dict[str, Any]] = {}
    avisos: List[str] = []
    if not isinstance(bloque, dict):
        return perfiles, ["'perfiles' debe ser un objeto {nombre: definicion}."]

    equipos, avisos_equipos = resolver_equipos(configuracion)
    avisos.extend(avisos_equipos)

    for nombre, definicion in bloque.items():
        definicion = definicion if isinstance(definicion, dict) else {}
        tareas = [str(t) for t in (definicion.get('tareas') or [])]
        desconocidas = [t for t in tareas if t not in TAREAS_VALIDAS]
        if desconocidas:
            avisos.append(
                "El perfil '%s' declara tareas que el motor todavia no sabe "
                "repartir (%s). Se ignoran; validas: %s."
                % (nombre, ", ".join(desconocidas), ", ".join(TAREAS_VALIDAS)))
            tareas = [t for t in tareas if t in TAREAS_VALIDAS]
        if not tareas:
            avisos.append("El perfil '%s' no toma ninguna tarea valida; se "
                          "descarta." % nombre)
            continue
        equipo_id = definicion.get('equipo')
        if equipo_id is not None and equipo_id not in equipos:
            avisos.append("El perfil '%s' usa el equipo '%s', que no esta "
                          "definido en 'equipos'; se descarta."
                          % (nombre, equipo_id))
            continue
        perfiles[nombre] = {'nombre': nombre, 'tareas': tareas,
                            'equipo': equipo_id}
    return perfiles, avisos


def resolver_cambio_de_perfil(configuracion: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Regla de cambio de perfil: {modo, umbral}.  (INIT-11 F2)

    * `inmediato`: vuelve al perfil de mayor prioridad con trabajo apenas puede.
    * `agotar`: se queda en el perfil actual mientras tenga trabajo.
    * `umbral`: cambia a un perfil mas prioritario solo si acumulo N tareas.
    Default: `umbral` con 3 (cambiar de tarea cuesta tiempo real; ver plan).
    """
    bloque = (configuracion or {}).get('cambio_de_perfil') or {}
    if not isinstance(bloque, dict):
        bloque = {}
    modo = str(bloque.get('modo', 'umbral'))
    if modo not in MODOS_CAMBIO:
        logger.warning("[WARN][CONFIG] cambio_de_perfil.modo '%s' desconocido; "
                       "se usa 'umbral'. Validos: %s", modo, ", ".join(MODOS_CAMBIO))
        modo = 'umbral'
    try:
        umbral = int(bloque.get('umbral', 3))
    except (TypeError, ValueError):
        umbral = 3
    return {'modo': modo, 'umbral': max(1, umbral)}


def resolver_personas(configuracion: Optional[Dict[str, Any]]):
    """Flota a partir de `personas` + `equipos`.  (INIT-11 F1)

    `personas` es una lista de GRUPOS:
      {grupo, cantidad=1, nombres=[], equipo, habilitaciones=[equipo],
       discharge_time, work_area_priorities}
    En F1 cada persona trabaja con UN equipo fijo (el de su grupo). Tomar y
    dejar equipos en estacionamientos llega en F2.

    Reglas de realismo (cada incumplimiento deja un aviso visible y la
    persona NO se crea: sin maquina o sin habilitacion no puede trabajar):
      * el equipo debe existir en `equipos`;
      * la persona debe estar habilitada para ese equipo;
      * no puede haber mas personas con un equipo que unidades del equipo.

    Devuelve `(flota, avisos)`; el orden de la lista fija el spawn.
    """
    configuracion = configuracion or {}
    equipos, avisos = resolver_equipos(configuracion)
    catalogo_perfiles, avisos_perfiles = resolver_perfiles(configuracion)
    avisos.extend(a for a in avisos_perfiles if a not in avisos)
    grupos = configuracion.get('personas') or []
    flota: List[Dict[str, Any]] = []
    usados: Dict[str, int] = {}
    ids_vistos = set()

    for indice, grupo in enumerate(grupos):
        if not isinstance(grupo, dict):
            avisos.append("personas[%d] no es un objeto; se ignora." % indice)
            continue
        nombre_grupo = str(grupo.get('grupo') or ('Grupo%d' % (indice + 1)))
        # INIT-11 F2: perfiles del grupo, en orden de prioridad. Sin perfiles,
        # la persona hace lo de F1: cualquier tarea con su equipo fijo.
        perfiles_grupo, avisos_grupo = _perfiles_del_grupo(
            grupo, nombre_grupo, catalogo_perfiles)
        avisos.extend(avisos_grupo)
        equipo_id = grupo.get('equipo')
        if equipo_id is None and perfiles_grupo:
            # El equipo inicial es el del perfil mas prioritario que use uno.
            equipo_id = next((p['equipo'] for p in perfiles_grupo if p['equipo']),
                             None)
        equipo = equipos.get(equipo_id)
        if equipo is None:
            avisos.append(
                "El grupo '%s' usa el equipo '%s', que no esta definido en "
                "'equipos'. El grupo no se crea." % (nombre_grupo, equipo_id))
            continue
        habilitaciones = grupo.get('habilitaciones')
        if habilitaciones is None:
            # Por defecto: lo que necesita para su equipo y para sus perfiles.
            habilitaciones = [equipo_id] + [p['equipo'] for p in perfiles_grupo
                                            if p['equipo']]
            habilitaciones = list(dict.fromkeys(habilitaciones))
        habilitados = []
        for perfil in perfiles_grupo:
            if perfil['equipo'] is None or perfil['equipo'] in habilitaciones:
                habilitados.append(perfil)
            else:
                avisos.append(
                    "El grupo '%s' tiene el perfil '%s', que necesita '%s', pero "
                    "no esta habilitado para ese equipo. Ese perfil no se le "
                    "asigna." % (nombre_grupo, perfil['nombre'], perfil['equipo']))
        perfiles_grupo = habilitados
        if equipo_id not in habilitaciones:
            avisos.append(
                "El grupo '%s' no esta habilitado para manejar '%s' "
                "(habilitaciones: %s). El grupo no se crea."
                % (nombre_grupo, equipo_id,
                   ", ".join(map(str, habilitaciones)) or "ninguna"))
            continue

        defaults = get_fleet_defaults(configuracion, equipo['tipo_base'])
        nombres = list(grupo.get('nombres') or [])
        cantidad = int(grupo.get('cantidad', max(1, len(nombres))) or 0)
        if len(nombres) > cantidad:
            avisos.append(
                "El grupo '%s' tiene %d nombres para %d personas; se usan los "
                "primeros %d." % (nombre_grupo, len(nombres), cantidad, cantidad))

        for n in range(cantidad):
            if n < len(nombres):
                persona_id = str(nombres[n])
            else:
                persona_id = "%s-%02d" % (nombre_grupo, n + 1)
            if persona_id in ids_vistos:
                avisos.append("La persona '%s' esta repetida; se crea una sola vez."
                              % persona_id)
                continue
            if equipo['cantidad'] is not None and                     usados.get(equipo_id, 0) >= equipo['cantidad']:
                avisos.append(
                    "No hay unidades de '%s' para '%s' (hay %d y ya estan "
                    "asignadas). La persona no se crea."
                    % (equipo_id, persona_id, equipo['cantidad']))
                continue
            usados[equipo_id] = usados.get(equipo_id, 0) + 1
            ids_vistos.add(persona_id)
            flota.append({
                'type': equipo['tipo_base'],
                'capacity': equipo['capacidad'],
                'discharge_time': grupo.get('discharge_time',
                                            defaults.get('discharge_time', 5)),
                'work_area_priorities': copy.deepcopy(
                    grupo.get('work_area_priorities',
                              defaults.get('work_area_priorities', {}))),
                'id': persona_id,
                'equipo': dict(equipo),
                'persona': {'id': persona_id, 'grupo': nombre_grupo,
                            'habilitaciones': list(habilitaciones),
                            'perfiles': [dict(p) for p in perfiles_grupo]},
            })

    return flota, avisos


def _perfiles_del_grupo(grupo: Dict[str, Any], nombre_grupo: str,
                        catalogo: Dict[str, Dict[str, Any]]):
    """Perfiles de un grupo, en el orden declarado (= orden de prioridad)."""
    perfiles, avisos = [], []
    for nombre in (grupo.get('perfiles') or []):
        perfil = catalogo.get(nombre)
        if perfil is None:
            avisos.append("El grupo '%s' usa el perfil '%s', que no esta "
                          "definido en 'perfiles'; se ignora."
                          % (nombre_grupo, nombre))
            continue
        perfiles.append(perfil)
    return perfiles, avisos


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
    from core.work_areas import (equipo_sirve, expected_equipment_for_area,
                                 get_work_area_equipment)

    flota = resolver_flota(configuracion)

    # Areas a considerar: las del mapa explicito + las declaradas por la flota.
    areas = set(get_work_area_equipment(configuracion).keys())
    for agente in flota:
        areas.update((agente.get('work_area_priorities') or {}).keys())

    capacidades: Dict[str, Any] = {}
    for area in areas:
        tipo_requerido = expected_equipment_for_area(configuracion, area)
        disponibles = [a['capacity'] for a in flota
                       if equipo_sirve(tipo_requerido, a['type'],
                                       (a.get('equipo') or {}).get('id'))]
        if disponibles:
            capacidades[area] = min(disponibles)

    todas = [a['capacity'] for a in flota if a.get('capacity') is not None]
    fallback_global = min(todas) if todas else 150

    return capacidades, fallback_global
