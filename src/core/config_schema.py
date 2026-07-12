# -*- coding: utf-8 -*-
"""
MEJ-3: Esquema UNICO de configuracion (config.json) del Gemelo Digital.

Este modulo es la FUENTE DE VERDAD de que claves existen, que tipo tienen y
quien las lee. Se usa para VALIDAR (deteccion de claves desconocidas / typos y
errores de tipo); NO muta la configuracion: el motor sigue leyendo el dict
original con sus .get() y defaults historicos (byte-identico garantizado).

Consumidores:
- core/config_manager.ConfigurationManager (motor): loguea warnings/errores.
- web_prototype/config_manager.WebConfigurationManager (UI): idem al validar.
- tests/unit/test_config_schema.py: pinea el contrato.

Politica:
- Clave DESCONOCIDA (typo tipo 'priority_dispatch_enable') -> WARNING con nombre.
- Clave LEGACY (purgada en MEJ-3, sin efecto en el motor) -> WARNING "sin efecto".
- Tipo invalido en clave conocida -> ERROR (el motor fallaria o la ignoraria).

Ley #4: ASCII puro en mensajes.
"""
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, ValidationError


# Claves que EXISTIERON y fueron purgadas en MEJ-3 (2026-07-04) por no tener
# ningun lector en la cadena viva. Si aparecen (preset viejo), no rompen nada:
# el motor las ignora. Se avisa para que el usuario no crea que hacen algo.
LEGACY_KEYS_TOP = {
    "num_operarios", "num_ground_operators", "num_forklifts", "num_work_orders",
    "tareas_zona_a", "tareas_zona_b", "assignment_rules", "capacidad_carro",
    "capacidad_montacargas", "tiempo_descarga_por_tarea", "map_scale",
}
LEGACY_KEYS_CONGESTION = {
    # Claves del enfoque F3 (exclusion por celda, jubilado por timewindow) y
    # parametros sin lector. Solo tienen efecto si mode='cell'/'cell+corridor'.
    "wait_timeout", "wait_hard_cap", "backoff_base", "backoff_jitter",
    "max_repath", "repath_cost_factor", "watchdog_window", "allow_swap",
    "aging_rate",
}


class PickTimeModel(BaseModel):
    """INIT-4 C1 + INIT-8 F2: tiempo de pick escalable. Neutro = historico."""
    model_config = ConfigDict(extra="allow")
    base: Optional[float] = None
    por_unidad: Optional[float] = None
    por_volumen: Optional[float] = None
    por_kg: Optional[float] = None   # INIT-8 F2: s por kg manipulado
    minimo: Optional[float] = None


class VelocidadPorCargaConfig(BaseModel):
    """INIT-8 F3: velocidad segun carga transportada (opt-in, default off).
    factor_tiempo = 1/(1 - min(kg*reduccion_por_kg, reduccion_max)).
    Calibracion: Indian Army 2022 (22 kg => -18.5% => 0.0084/kg).
    Lector: operators._factor_carga_tiempo (aplica en _recorrer_tramo,
    consistente con el plan espacio-temporal)."""
    model_config = ConfigDict(extra="allow")
    enabled: Optional[bool] = None
    reduccion_por_kg: Optional[float] = None
    reduccion_max: Optional[float] = None
    aplica_forklift: Optional[bool] = None


class ClaseManejoConfig(BaseModel):
    """INIT-8 F2/F4: parametros de tiempo por clase de manejo del SKU.
    Pick/putaway-load: t_final = t * mult + recargo. Descarga en staging:
    discharge + pack (segundos de empaque por clase, F4, default 0).
    Neutro = {mult: 1.0, recargo: 0.0, pack: 0.0}.
    Lectores: operators._clase_params / _clase_pack."""
    model_config = ConfigDict(extra="allow")
    mult: Optional[float] = None
    recargo: Optional[float] = None
    pack: Optional[float] = None


class VariabilidadConfig(BaseModel):
    """INIT-8 F4: variabilidad Log-Normal de tiempos (opt-in, default off).
    Media preservada (E[X] = t); cv = coef. de variacion. Log-Normal y NO
    Normal/Triangular por Law/Simio 2024 (acotada en 0, cola derecha).
    Reproducible bajo WAREHOUSE_SEED. Lector: operators._tiempo_estocastico."""
    model_config = ConfigDict(extra="allow")
    enabled: Optional[bool] = None
    cv: Optional[float] = None


class TiemposConfig(BaseModel):
    """Bloque 'tiempos' (calibracion C5 + INIT-4 C1)."""
    model_config = ConfigDict(extra="allow")
    cell_size_m: Optional[float] = None
    time_per_cell: Optional[float] = None
    speed_factor_ground: Optional[float] = None
    speed_factor_forklift: Optional[float] = None
    tiempo_picking_por_linea: Optional[float] = None
    tiempo_horquilla: Optional[float] = None
    pick_time_model: Optional[PickTimeModel] = None
    # INIT-8 F2: {clase_manejo: {mult, recargo}} (hoja SkuCatalog)
    clases_manejo: Optional[Dict[str, ClaseManejoConfig]] = None
    # INIT-8 F3: velocidad segun carga (opt-in)
    velocidad_por_carga: Optional[VelocidadPorCargaConfig] = None
    # INIT-8 F4: variabilidad Log-Normal de tiempos (opt-in)
    variabilidad: Optional[VariabilidadConfig] = None


class TimewindowConfig(BaseModel):
    """Sub-bloque congestion.timewindow (Iniciativa 2 Opcion C, ACTIVO)."""
    model_config = ConfigDict(extra="allow")
    shadow: Optional[bool] = None
    clearance: Optional[float] = None
    dt_wait: Optional[float] = None
    max_expansions: Optional[int] = None
    plan_horizon: Optional[float] = None
    allow_diagonal: Optional[bool] = None


class CongestionConfig(BaseModel):
    """Bloque 'congestion' (Iniciativa 2). VIVO y ACTIVO en el canonico."""
    model_config = ConfigDict(extra="allow")
    enabled: Optional[bool] = None
    mode: Optional[str] = None  # off|instrument|cell|cell+corridor|timewindow
    startup_window: Optional[float] = None
    staggered_start: Optional[bool] = None   # VIVO: spawn escalonado
    spawn_offset: Optional[float] = None     # VIVO: offset del spawn escalonado
    timewindow: Optional[TimewindowConfig] = None


class OutboundConfig(BaseModel):
    """Bloque 'outbound' (Iniciativa 3: camiones/staging)."""
    model_config = ConfigDict(extra="allow")
    enabled: Optional[bool] = None
    dispatch_policy: Optional[str] = None
    truck_interval: Optional[float] = None
    truck_capacity: Optional[int] = None
    loading_time: Optional[float] = None
    zone_capacity_default: Optional[int] = None
    slot_wait_alert: Optional[float] = None
    slot_poll_dt: Optional[float] = None
    dwell_scaffold: Optional[float] = None


class InboundConfig(BaseModel):
    """
    Bloque 'inbound' (INIT-7: recepcion y putaway). Opt-in: NO esta en el
    canonico; bloque ausente o enabled=false => comportamiento historico
    byte-identico. Lectores: F1 InboundProcess (llegadas), F2 putaway,
    F3 slotting. En F0 solo existe el contrato.
    """
    model_config = ConfigDict(extra="allow")
    enabled: Optional[bool] = None
    arrival_mode: Optional[str] = None       # deterministic | stochastic
    asn_file_path: Optional[str] = None      # modo deterministic
    truck_interval: Optional[float] = None   # modo stochastic (segundos)
    pallets_per_truck: Optional[int] = None  # modo stochastic
    units_per_pallet: Optional[int] = None   # modo stochastic (qty por pallet)
    num_trucks: Optional[int] = None         # modo stochastic (agenda finita, F2)
    unload_time_per_pallet: Optional[float] = None
    putaway_load_time: Optional[float] = None  # F2: cargar pallet en muelle (s)
    # fija_por_sku | cercana_al_muelle | abc_rotacion (F3)
    slotting_strategy: Optional[str] = None
    # F5a: prioridad de la flota compartida. picks_first (default historico:
    # putaway solo con flota ociosa) | putaway_first (la recepcion manda).
    putaway_priority: Optional[str] = None
    # F5b: el stock recibido rescata backorders de la MISMA corrida (pick
    # dinamico post-putaway). Solo modo deterministic; default false.
    cross_dock_enabled: Optional[bool] = None


class WavesConfig(BaseModel):
    """INIT-4 C3: olas por release diferido (opt-in)."""
    model_config = ConfigDict(extra="allow")
    enabled: Optional[bool] = None
    release_times: Optional[Dict[str, float]] = None


class AgentTypeConfig(BaseModel):
    """Un grupo de agentes de la flota (agent_types[])."""
    model_config = ConfigDict(extra="allow")
    type: Optional[str] = None               # GroundOperator | Forklift
    capacity: Optional[float] = None
    discharge_time: Optional[float] = None
    work_area_priorities: Optional[Dict[str, int]] = None


class DistribucionTipo(BaseModel):
    model_config = ConfigDict(extra="allow")
    porcentaje: Optional[float] = None
    volumen: Optional[float] = None


class WarehouseConfig(BaseModel):
    """
    Esquema completo de config.json. Cada campo anota su LECTOR real.
    Los campos son opcionales: el motor tiene defaults propios; el esquema
    valida tipos y detecta desconocidas, no impone presencia (eso lo hacen
    REQUIRED_KEYS del motor y validate_config de la web).
    """
    model_config = ConfigDict(extra="allow")

    # --- Generacion de ordenes (order_strategies.py) ---
    order_generation_mode: Optional[str] = None      # stochastic | deterministic
    order_file_path: Optional[str] = None
    fulfillment_policy: Optional[str] = None         # ship_partial | fill_or_kill
    total_ordenes: Optional[int] = None              # warehouse.py
    distribucion_tipos: Optional[Dict[str, DistribucionTipo]] = None

    # --- Despacho (dispatcher.py) ---
    dispatch_strategy: Optional[str] = None
    tour_type: Optional[str] = None
    max_wos_por_tour: Optional[int] = None
    radio_cercania: Optional[int] = None             # BK-01
    radio_expansion_paso: Optional[int] = None       # H-6
    radio_max_expansiones: Optional[int] = None      # H-6
    cercania_tour_mode: Optional[str] = None         # BK-03: cost | greedy_nn
    priority_dispatch_enabled: Optional[bool] = None  # INIT-4 C2 (opt-in)
    waves: Optional[WavesConfig] = None              # INIT-4 C3 (opt-in)

    # --- Flota (operators.py) ---
    agent_types: Optional[List[AgentTypeConfig]] = None
    work_area_equipment: Optional[Dict[str, str]] = None  # QA-3 Opcion B
    # Fallback historico cuando agent_types esta vacio (operators.crear_operarios):
    num_operarios_terrestres: Optional[int] = None
    num_montacargas: Optional[int] = None
    # LEGACY-INFORMATIVO: solo se imprime (warehouse.py) y lo exige REQUIRED_KEYS.
    num_operarios_total: Optional[int] = None

    # --- Layout y datos (layout_manager / data_manager) ---
    layout_file: Optional[str] = None
    sequence_file: Optional[str] = None

    # --- Outbound / staging (warehouse.py, outbound.py) ---
    outbound_staging_distribution: Optional[Dict[str, float]] = None
    outbound: Optional[OutboundConfig] = None
    # INIT-6 Opcion B: destino de negocio -> staging_id (warehouse._resolver_staging_id)
    destino_staging_map: Optional[Dict[str, int]] = None

    # --- Inbound (INIT-7, opt-in; lectores en F1/F2/F3) ---
    inbound: Optional[InboundConfig] = None

    # --- Congestion (Iniciativa 2, ACTIVA) ---
    congestion: Optional[CongestionConfig] = None

    # --- Tiempos (operators.py / C5 / INIT-4 C1) ---
    tiempos: Optional[TiemposConfig] = None


def _extras_of(model: Optional[BaseModel]) -> Dict[str, Any]:
    if model is None:
        return {}
    return dict(model.model_extra or {})


def validate_config_schema(config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Valida `config` contra el esquema. Devuelve (errors, warnings).
    - errors: tipos invalidos en claves conocidas (el motor fallaria/ignoraria).
    - warnings: claves desconocidas (posible typo) o legacy sin efecto.
    NUNCA lanza; NUNCA muta config.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(config, dict):
        return (["la configuracion debe ser un objeto JSON"], [])

    try:
        model = WarehouseConfig.model_validate(config)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(p) for p in err.get("loc", ()))
            errors.append("tipo invalido en '%s': %s" % (loc, err.get("msg", "")))
        # Con errores de tipo no se puede inspeccionar extras de forma fiable.
        return (errors, warnings)

    # Claves desconocidas / legacy en el nivel superior.
    for key in _extras_of(model):
        if key in LEGACY_KEYS_TOP:
            warnings.append("clave LEGACY sin efecto: '%s' (purgada en MEJ-3; "
                            "el motor no la lee)" % key)
        else:
            warnings.append("clave DESCONOCIDA: '%s' (posible typo; el motor "
                            "la ignorara en silencio)" % key)

    # Sub-bloques.
    if model.congestion is not None:
        for key in _extras_of(model.congestion):
            if key in LEGACY_KEYS_CONGESTION:
                warnings.append("clave LEGACY sin efecto: 'congestion.%s' "
                                "(enfoque F3 jubilado)" % key)
            else:
                warnings.append("clave DESCONOCIDA: 'congestion.%s'" % key)
        if model.congestion.timewindow is not None:
            for key in _extras_of(model.congestion.timewindow):
                warnings.append("clave DESCONOCIDA: 'congestion.timewindow.%s'" % key)
    for block_name in ("outbound", "tiempos", "waves", "inbound"):
        block = getattr(model, block_name)
        if block is not None:
            for key in _extras_of(block):
                warnings.append("clave DESCONOCIDA: '%s.%s'" % (block_name, key))
    if model.tiempos is not None and model.tiempos.pick_time_model is not None:
        for key in _extras_of(model.tiempos.pick_time_model):
            warnings.append("clave DESCONOCIDA: 'tiempos.pick_time_model.%s'" % key)

    return (errors, warnings)


def log_schema_check(config: Dict[str, Any], logger_print=print,
                     origin: str = "CONFIG") -> Tuple[List[str], List[str]]:
    """
    Helper de conveniencia: valida y ESCRIBE los hallazgos con el print/logger
    que se le pase (ASCII, Ley #4). Devuelve (errors, warnings) para el caller.
    """
    errors, warnings = validate_config_schema(config)
    for w in warnings:
        logger_print("[%s][SCHEMA][WARN] %s" % (origin, w))
    for e in errors:
        logger_print("[%s][SCHEMA][ERROR] %s" % (origin, e))
    if not errors and not warnings:
        logger_print("[%s][SCHEMA] OK: sin claves desconocidas ni tipos invalidos" % origin)
    return (errors, warnings)
