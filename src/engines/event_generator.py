# -*- coding: utf-8 -*-
"""
Event Generator Engine - Motor puro de generacion de eventos para replay.
Sin renderizado, sin Pygame, solo SimPy + generacion de .jsonl
"""

import sys

import logging

logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)
import os

import simpy
from datetime import datetime

# Imports de subsystems
from subsystems.simulation.warehouse import AlmacenMejorado
from subsystems.simulation.operators import crear_operarios
from subsystems.simulation.layout_manager import LayoutManager
from subsystems.simulation.assignment_calculator import AssignmentCostCalculator
from subsystems.simulation.data_manager import DataManager
from subsystems.simulation.pathfinder import Pathfinder
from subsystems.simulation.route_calculator import RouteCalculator

# Imports de core
from core.config_manager import ConfigurationManager, ConfigurationError
from core.config_utils import get_default_config
from core.replay_utils import volcar_replay_a_archivo

# Imports de analytics
from analytics.exporter_v2 import AnalyticsExporter
from analytics.context import SimulationContext

# Replay buffer
from simulation_buffer import ReplayBuffer


# MEJ-ROBUSTEZ (auditoria 2026-07-10): watchdog de NO-PROGRESO. Si ninguna WO
# se cierra durante este lapso de tiempo de SIMULACION, la corrida esta
# deadlockeada (p.ej. una WO en ubicacion inalcanzable de un TMX custom, o un
# bug logico futuro: los agentes quedan en idle-loop de 0.5s y env.now crece
# para siempre). El guard QA-3 de areas sin agente atrapa el caso estatico
# ANTES de correr; esto es la red de ULTIMO recurso para lo dinamico.
# 7200 s de sim >> cualquier hueco legitimo (esperar un camion inbound, olas).
STALL_LIMIT_BASE_S = 7200.0


def compute_stall_limit(inbound_schedule):
    """Limite de no-progreso en segundos de SIM. Con agenda inbound, un hueco
    legitimo puede durar hasta la ULTIMA llegada agendada (los agentes esperan
    el camion sin completar nada): se extiende el limite a esa cota + base."""
    max_arrival = 0.0
    for truck in inbound_schedule or []:
        try:
            max_arrival = max(max_arrival, float(truck.get('arrival_time', 0)))
        except (TypeError, ValueError):
            continue
    return max(STALL_LIMIT_BASE_S, max_arrival + STALL_LIMIT_BASE_S)


class EventGenerator:
    """
    Motor puro de generacion de eventos para archivos .jsonl
    
    Extrae solo la logica esencial de SimulationEngine:
    - Inicializacion de subsystems (AlmacenMejorado, Dispatcher, Operators)
    - Ejecucion de simulacion SimPy pura (sin Pygame)
    - Generacion de archivos .jsonl para replay
    - Exportacion de analytics (Excel)
    
    NO incluye:
    - Renderizado en tiempo real
    - Pygame
    - Multiproceso visual
    - Dashboard en tiempo real
    """
    
    def __init__(self, headless_mode=True, config_path=None, output_metrics_path=None):
        """
        Inicializa el generador de eventos
        
        Args:
            headless_mode: Siempre True (sin UI)
            config_path: Path opcional a archivo config.json personalizado
            output_metrics_path: Path opcional para exportar métricas de optimización
        """
        self.output_metrics_path = output_metrics_path
        # Cargar configuracion
        try:
            self.config_manager = ConfigurationManager(config_path=config_path)
            self.config_manager.validate_configuration()
            self.configuracion = self.config_manager.configuration
            logger.info("[EVENT-GENERATOR] Configuracion cargada exitosamente")
        except ConfigurationError as e:
            logger.error(f"[EVENT-GENERATOR ERROR] Error en configuracion: {e}")
            self.config_manager = None
            self.configuracion = get_default_config()
            logger.info("[EVENT-GENERATOR] Fallback: Usando configuracion por defecto")
        
        # Entorno SimPy
        self.env = None
        self.almacen = None
        
        # Timestamps para compatibilidad con SimulationContext
        self.session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_output_dir = os.path.join("output", f"simulation_{self.session_timestamp}")
        
        # Replay buffer
        self.replay_buffer = ReplayBuffer()
        
        # TMX components
        self.layout_manager = None
        self.pathfinder = None
        self.data_manager = None
        self.cost_calculator = None
        self.route_calculator = None
        
        # Operarios
        self.operarios = []
        self.procesos_operarios = []
        
        logger.info(f"[EVENT-GENERATOR] Inicializado - Session: {self.session_timestamp}")
    
    def crear_simulacion(self):
        """Crea una nueva simulacion (sin Pygame)"""
        if not self.configuracion:
            logger.error("[EVENT-GENERATOR ERROR] No hay configuracion valida")
            return False

        # Semilla determinista via variable de entorno WAREHOUSE_SEED.
        # Uso: SET WAREHOUSE_SEED=42 (Windows) / export WAREHOUSE_SEED=42 (Linux)
        # Sin la variable -> comportamiento estocastico de produccion (sin cambios).
        import random as _random
        _seed_env = os.environ.get('WAREHOUSE_SEED')
        if _seed_env is not None:
            _random.seed(int(_seed_env))
            logger.info(f"[EVENT-GENERATOR] Semilla fijada: WAREHOUSE_SEED={_seed_env} (modo determinista)")

        logger.info("[EVENT-GENERATOR] Inicializando arquitectura TMX...")
        
        # 1. Inicializar LayoutManager
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        tmx_file = os.path.join(project_root, self.configuracion.get('layout_file', 'layouts/WH1.tmx'))
        logger.info(f"[EVENT-GENERATOR] Cargando layout: {tmx_file}")
        
        try:
            self.layout_manager = LayoutManager(tmx_file, headless=True)
        except Exception as e:
            logger.error(f"[EVENT-GENERATOR ERROR] No se pudo cargar TMX: {e}")
            return False
        
        # 2. Inicializar Pathfinder
        logger.info("[EVENT-GENERATOR] Inicializando pathfinding...")
        try:
            self.pathfinder = Pathfinder(self.layout_manager.collision_matrix)
            self.route_calculator = RouteCalculator(self.pathfinder)
        except Exception as e:
            logger.error(f"[EVENT-GENERATOR ERROR] No se pudo inicializar pathfinder: {e}")
            return False
        
        # 3. Crear entorno SimPy
        self.env = simpy.Environment()
        
        # 4. Crear DataManager
        layout_file = self.configuracion.get('layout_file', '')
        sequence_file = self.configuracion.get('sequence_file', '')
        self.data_manager = DataManager(layout_file, sequence_file, headless=True)
        
        # 5. Crear calculador de costos
        self.cost_calculator = AssignmentCostCalculator(self.data_manager)
        
        logger.info(f"[EVENT-GENERATOR] Arquitectura TMX inicializada:")
        logger.info(f"  - Dimensiones: {self.layout_manager.grid_width}x{self.layout_manager.grid_height}")
        logger.info(f"  - Puntos de picking: {len(self.layout_manager.picking_points)}")
        logger.info(f"  - Staging areas: {len(self.data_manager.outbound_staging_locations)}")
        
        # 6. Crear AlmacenMejorado
        self.almacen = AlmacenMejorado(
            self.env,
            self.configuracion,
            layout_manager=self.layout_manager,
            pathfinder=self.pathfinder,
            data_manager=self.data_manager,
            cost_calculator=self.cost_calculator,
            route_calculator=self.route_calculator,
            simulador=None,  # No hay simulador en modo headless
            visual_event_queue=None,  # No hay cola visual
            replay_buffer=self.replay_buffer  # SI hay replay buffer
        )
        
        # 7. Crear operarios
        self.procesos_operarios, self.operarios = crear_operarios(
            self.env,
            self.almacen,
            self.configuracion,
            simulador=None,
            pathfinder=self.pathfinder,
            layout_manager=self.layout_manager
        )

        # 7b. Iniciativa #2 / Fase 3: arrancar el watchdog de congestion (solo cell mode).
        cm = getattr(self.almacen, 'congestion_manager', None)
        if cm is not None and getattr(cm, 'cell_exclusion', False):
            cm.start_watchdog(self.operarios)

        # 7c. INICIATIVA #3 / Fase 0: arranque del proceso outbound (camion).
        # Fase 0 = gate listo pero outbound_process es None (no se instancia el
        # camion hasta Fase 2). Con el flag off la condicion es falsa => no-op =>
        # .jsonl byte-identico al baseline.
        if getattr(self.almacen, 'outbound_enabled', False) and \
           getattr(self.almacen, 'outbound_process', None) is not None:
            self.env.process(self.almacen.outbound_process.run())

        # 7d. INIT-7 / F1: arranque del proceso inbound (llegadas de camiones).
        # Con inbound off (default, bloque ausente en el canonico) la condicion
        # es falsa => no-op => .jsonl byte-identico al baseline.
        if getattr(self.almacen, 'inbound_enabled', False) and \
           getattr(self.almacen, 'inbound_process', None) is not None:
            self.env.process(self.almacen.inbound_process.run())

        # 8. Inicializar almacen y crear ordenes
        self.almacen._crear_catalogo_y_stock()
        self.almacen._generar_flujo_ordenes()
        
        # 9. Capturar snapshot inicial de WorkOrders
        if hasattr(self.almacen, 'dispatcher') and hasattr(self.almacen.dispatcher, 'lista_maestra_work_orders'):
            initial_snapshot = [wo.to_dict() for wo in self.almacen.dispatcher.lista_maestra_work_orders]
            self.almacen.dispatcher.initial_work_orders_snapshot = initial_snapshot
            logger.info(f"[EVENT-GENERATOR] Snapshot inicial capturado: {len(initial_snapshot)} WorkOrders")
        
        # 9b. QA hardening (BK-04): chequeo preventivo de la flota ANTES de correr. Cubre
        # el bypass del configurador (config.json a mano, --config, optimizer, presets
        # viejos): si no hay agentes, no hay WorkOrders, o un area queda sin un agente
        # capaz del tipo correcto, se ABORTA con mensaje en vez de colgarse (while True del
        # outbound / espera del dispatcher).
        ok_flota, msg_flota = self._validar_flota_cubre_areas()
        if not ok_flota:
            logger.error(f"[EVENT-GENERATOR ERROR] {msg_flota}")
            return False

        # 10. Iniciar proceso del dispatcher
        if hasattr(self.almacen, 'dispatcher') and hasattr(self.almacen.dispatcher, 'dispatcher_process'):
            logger.info("[EVENT-GENERATOR] Iniciando dispatcher...")
            self.env.process(self.almacen.dispatcher.dispatcher_process(self.operarios))
        
        logger.info(f"[EVENT-GENERATOR] Simulacion creada:")
        logger.info(f"  - {len(self.procesos_operarios)} operarios")
        logger.info(f"  - {len(self.almacen.dispatcher.lista_maestra_work_orders)} WorkOrders")
        logger.info(f"  - {self.almacen.total_ordenes} ordenes generadas")
        
        return True

    def _expected_equipment_for_area(self, area):
        # QA-3 (Opcion B): tipo capaz de un area. FUENTE DE VERDAD = el mapa explicito
        # config['work_area_equipment'] (editable en la UI). La convencion de nombres
        # (regex) queda SOLO como fallback para configs viejas sin el mapa. Misma logica en
        # config_manager._expected_equipment_for_area y fleet-manager.js.
        wae = (self.configuracion or {}).get('work_area_equipment', {})
        if isinstance(wae, dict):
            t = wae.get(area)
            if t:
                return t
        import re
        if re.search(r'ground|piso|floor|suelo|terrestre|level[_-]?0|l0', str(area), re.I):
            return 'GroundOperator'
        return 'Forklift'

    def _validar_flota_cubre_areas(self):
        """QA-1/QA-2/QA-3: valida la flota construida ANTES de env.run. Devuelve (ok, msg).
        - >=1 agente (QA-2) y >=1 WorkOrder (evita el cuelgue de outbound con 0 ordenes).
        - cada area con WOs cubierta por un agente capaz (QA-1 cobertura).
        - con agent_types EXPLICITO, ademas por un agente del TIPO correcto (QA-3); con
          flota fallback (agent_types vacio) el tipo NO se exige (es el default interno)."""
        operarios = self.operarios or []
        if len(operarios) == 0:
            return False, ("La flota no tiene agentes (0 operarios). Simulacion cancelada "
                           "para no quedar colgada. Configura al menos un grupo de agentes.")
        try:
            wos = list(self.almacen.dispatcher.lista_maestra_work_orders)
        except Exception:
            wos = []
        if not wos:
            return False, ("No hay WorkOrders que simular (0 ordenes). Simulacion cancelada "
                           "para no quedar colgada (el outbound correria indefinidamente).")
        areas = set()
        for wo in wos:
            wa = getattr(wo, 'work_area', None)
            if wa:
                areas.add(str(wa))
        was_fallback = not (self.configuracion or {}).get('agent_types')
        for area in sorted(areas):
            cubridores = [op for op in operarios if op.can_handle_work_area(area)]
            if not cubridores:
                return False, ("El area '" + area + "' no tiene ningun agente capaz "
                               "asignado. Simulacion cancelada (evita cuelgue).")
            if not was_fallback:
                exp = self._expected_equipment_for_area(area)
                if not any(getattr(op, 'type', None) == exp for op in cubridores):
                    return False, ("El area '" + area + "' la cubre un tipo de agente "
                                   "incorrecto; requiere un " + exp + ". Simulacion cancelada.")
        return True, ''

    def ejecutar(self):
        """Ejecuta la simulacion y genera archivos de salida"""
        try:
            logger.info("="*60)
            logger.info("GENERADOR DE EVENTOS - GEMELO DIGITAL")
            logger.info(f"Session: {self.session_timestamp}")
            logger.info("Modo: Headless (sin UI)")
            logger.info("="*60)
            
            # Crear simulacion
            if not self.crear_simulacion():
                logger.error("[EVENT-GENERATOR ERROR] Fallo al crear simulacion")
                return False
            
            # Ejecutar simulacion SimPy pura
            logger.info("[EVENT-GENERATOR] Ejecutando simulacion SimPy...")
            step_counter = 0

            # MEJ-ROBUSTEZ: watchdog de no-progreso (ver compute_stall_limit).
            _stall_limit = compute_stall_limit(
                getattr(self.almacen, 'inbound_schedule', []))
            _last_done = -1
            _t_last_progress = 0.0

            while not self.almacen.simulacion_ha_terminado():
                try:
                    self.env.run(until=self.env.now + 1.0)
                    step_counter += 1

                    # Log cada 100 pasos
                    if step_counter % 100 == 0:
                        stats = self.almacen.dispatcher.obtener_estadisticas()
                        logger.info(f"[EVENT-GENERATOR] t={self.env.now:.1f}s | "
                              f"Completadas: {stats['completados']}/{stats['total']}")

                    # MEJ-ROBUSTEZ: si nada se cierra por > stall_limit de
                    # tiempo de SIM, hay deadlock -> abortar con diagnostico
                    # y seguir al volcado (el .jsonl parcial se conserva).
                    _done = len(self.almacen.dispatcher.work_orders_completados)
                    if _done != _last_done:
                        _last_done = _done
                        _t_last_progress = self.env.now
                    elif self.env.now - _t_last_progress > _stall_limit:
                        self._diagnosticar_stall(_stall_limit)
                        break

                except simpy.core.EmptySchedule:
                    if self.almacen.simulacion_ha_terminado():
                        break
                    else:
                        logger.warning("[EVENT-GENERATOR WARNING] No hay eventos pero simulacion no termino")
                        break
            
            logger.info(f"[EVENT-GENERATOR] Simulacion completada en t={self.env.now:.2f}s")
            
            # Exportar analytics
            logger.info("[EVENT-GENERATOR] Exportando analytics...")
            context = SimulationContext.from_simulation_engine(self)
            analytics_exporter = AnalyticsExporter(context)
            export_result = analytics_exporter.export_complete_analytics()
            
            if not export_result.success:
                logger.warning(f"[EVENT-GENERATOR WARNING] Exportacion con errores: {len(export_result.errors)}")
            
            # Generar archivo .jsonl
            logger.info("[EVENT-GENERATOR] Generando archivo .jsonl...")
            os.makedirs(self.session_output_dir, exist_ok=True)
            output_file = os.path.join(self.session_output_dir, f"replay_{self.session_timestamp}.jsonl")
            initial_snapshot = getattr(self.almacen.dispatcher, 'initial_work_orders_snapshot', [])
            
            volcar_replay_a_archivo(
                self.replay_buffer,
                output_file,
                self.configuracion,
                self.almacen,
                initial_snapshot
            )
            
            logger.info(f"[EVENT-GENERATOR] Archivo generado: {output_file}")
            logger.info(f"[EVENT-GENERATOR] Eventos capturados: {len(self.replay_buffer)}")

            # INICIATIVA #2 - Fase 1: reporte de instrumentacion de congestion (si activa).
            # Se escribe a un JSON aparte para NO contaminar el replay .jsonl.
            cm = getattr(self.almacen, 'congestion_manager', None)
            if cm is not None and getattr(cm, 'active', False):
                cm.write_report(self.session_output_dir, self.session_timestamp)

            # INICIATIVA #2 - OPCION C / Fase 1: reporte del planner espacio-temporal
            # en modo SOMBRA (metricas de coste + validacion de disjuncion). JSON aparte.
            planner = getattr(self.almacen, 'spacetime_planner', None)
            if planner is not None and hasattr(planner, 'shadow_report'):
                try:
                    import json as _json
                    rep = planner.shadow_report()
                    # MINI-FIX reservas: adjuntar metricas outbound al reporte JSON
                    # (diagnostico persistente; el stream del runner web no es fiable).
                    _om = getattr(self.almacen, 'outbound_metrics', None)
                    rep['outbound_metrics'] = _om if _om else 'outbound_off_o_sin_metricas'
                    suffix = f"_{self.session_timestamp}" if self.session_timestamp else ""
                    tw_path = os.path.join(self.session_output_dir,
                                           f"timewindow_shadow_report{suffix}.json")
                    with open(tw_path, "w", encoding="utf-8") as _f:
                        _json.dump(rep, _f, indent=2)
                    logger.info("\n" + "=" * 70)
                    logger.info("[TIMEWINDOW] REPORTE PLANNER ESPACIO-TEMPORAL (metricas)")
                    logger.info("=" * 70)
                    logger.info(f"  Tramos planificados: {rep.get('segments_planned')}")
                    logger.info(f"  Planes encontrados: {rep.get('plans_found')} | "
                          f"fallidos: {rep.get('plans_failed')}")
                    logger.info(f"  Solapes en reservas (DEBE ser 0): "
                          f"{rep.get('table_overlap_violations')}")
                    logger.info(f"  Coste planificacion: avg={rep.get('avg_plan_ms')}ms, "
                          f"max={round(rep.get('max_plan_ms', 0), 4)}ms")
                    logger.info(f"  Expansiones A*: avg={rep.get('avg_expansions')}, "
                          f"max={rep.get('max_expansions_in_a_plan')}, "
                          f"cap_hits={rep.get('expansion_cap_hits')}")
                    logger.info(f"  Esperas insertadas/plan: {rep.get('avg_waits_per_plan')}")
                    logger.info(f"  Reporte: {tw_path}")
                    logger.info("=" * 70)
                except Exception as _e:
                    logger.warning(f"[TIMEWINDOW][WARN] no se pudo escribir reporte sombra: {_e}")

            # MINI-FIX reservas: telemetria del subsistema outbound (si esta activo).
            # Imprime el desglose de reservas de pallet (ok/fail) para diagnosticar
            # los solapes de la tabla que NO vienen del planner.
            try:
                _om = getattr(self.almacen, 'outbound_metrics', None)
                if _om:
                    logger.info("[OUTBOUND] METRICAS: " + ", ".join(
                        f"{k}={v}" for k, v in sorted(_om.items())))
            except Exception as _e:
                logger.info(f"[OUTBOUND][WARN] no se pudieron imprimir metricas: {_e}")

            # INIT-7 F1: telemetria del subsistema inbound (si esta activo).
            try:
                _im = getattr(self.almacen, 'inbound_metrics', None)
                if _im:
                    logger.info("[INBOUND] METRICAS: " + ", ".join(
                        f"{k}={v}" for k, v in sorted(_im.items())))
            except Exception as _e:
                logger.info(f"[INBOUND][WARN] no se pudieron imprimir metricas: {_e}")

            # Exportar métricas de optimización si se solicitó
            if self.output_metrics_path:
                logger.info("[EVENT-GENERATOR] Exportando metricas de optimizacion...")
                self.export_optimization_metrics(self.output_metrics_path)
                logger.info(f"[EVENT-GENERATOR] Metricas exportadas: {self.output_metrics_path}")
            
            logger.info("="*60)
            logger.info("GENERACION COMPLETADA")
            logger.info(f"Archivos en: {self.session_output_dir}")
            logger.info("="*60)
            
            return True
        
        except KeyboardInterrupt:
            logger.info("\n[EVENT-GENERATOR] Interrupcion del usuario")
            return False
        
        except Exception as e:
            logger.error(f"[EVENT-GENERATOR ERROR] Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _diagnosticar_stall(self, stall_limit):
        """
        MEJ-ROBUSTEZ: banner de diagnostico al abortar por no-progreso.
        Lista las WOs sin cerrar (con su work_area/ubicacion) y las areas que
        la flota sirve, para que el problema sea accionable sin debuggear.
        La corrida sigue al volcado: el .jsonl parcial + Excel se generan.
        """
        d = self.almacen.dispatcher
        sin_cerrar = [wo for wo in d.lista_maestra_work_orders
                      if wo not in d.work_orders_completados]
        areas_flota = set()
        for op in (self.operarios or []):
            prios = getattr(op, 'work_area_priorities', {}) or {}
            areas_flota.update(k for k, v in prios.items() if v < 999)

        logger.error("=" * 70)
        logger.error("[WATCHDOG] SIMULACION ABORTADA POR NO-PROGRESO")
        logger.error(f"[WATCHDOG] Ninguna WO se cerro en {stall_limit:.0f}s de "
                     f"sim (t={self.env.now:.0f}s). Deadlock probable.")
        logger.error(f"[WATCHDOG] WOs sin cerrar: {len(sin_cerrar)} de "
                     f"{len(d.lista_maestra_work_orders)}. Primeras 5:")
        for wo in sin_cerrar[:5]:
            logger.error(f"[WATCHDOG]   {wo.id} status={wo.status} "
                         f"area={wo.work_area} ubicacion={wo.ubicacion} "
                         f"task={getattr(wo, 'task_type', 'pick')}")
        logger.error(f"[WATCHDOG] Areas servidas por la flota: "
                     f"{sorted(areas_flota) or 'NINGUNA'}")
        logger.error("[WATCHDOG] Causas tipicas: ubicacion inalcanzable en el "
                     "TMX, area sin agente capaz (el guard QA-3 cubre el caso "
                     "estatico), o pallet inbound que nunca aterrizo.")
        logger.error("[WATCHDOG] El .jsonl PARCIAL se genera igual para "
                     "inspeccion en el visor.")
        logger.error("=" * 70)
        try:
            self.almacen.registrar_evento('simulation_stalled', {
                'stall_limit_s': stall_limit,
                'sim_time': float(self.env.now),
                'unfinished_work_orders': len(sin_cerrar),
                'unfinished_sample': [wo.id for wo in sin_cerrar[:10]],
            })
        except Exception:
            pass

    def export_optimization_metrics(self, output_path: str):
        """
        Exporta métricas clave para optimización automática.
        
        Genera un archivo JSON con métricas esenciales que el optimizador
        utilizará para calcular el score de la configuración actual.
        
        Args:
            output_path: Path completo donde guardar el archivo JSON de métricas
        """
        import json
        from core.replay_utils import (build_inbound_summary,
                                        build_service_level_summary,
                                        build_sla_summary)

        # Obtener estadísticas del dispatcher
        stats = self.almacen.dispatcher.obtener_estadisticas()

        # Calcular métricas derivadas
        total_completed = stats['completados']
        total_wo = stats['total']
        total_failed = total_wo - total_completed
        simulation_time = self.env.now

        # AUDIT menores 2026-07-10: picks EXITOSOS solamente (sin putaway,
        # sin WOs failed). Con inbound activo, throughput_wo_per_s mezcla
        # picks+putaway con el tiempo extendido de la recepcion: comparar
        # configs con/sin inbound por ese KPI es enganoso. Este es el limpio.
        total_picks_completed = sum(
            1 for wo in self.almacen.dispatcher.work_orders_completados
            if getattr(wo, 'task_type', 'pick') != 'putaway'
            and getattr(wo, 'status', '') != 'failed')

        # Calcular tiempo promedio de completación (si hay WOs completadas)
        avg_completion_time = simulation_time / max(total_completed, 1)

        # Extraer configuración de recursos
        ground_operators = self.configuracion.get('num_operarios_terrestres', 0)
        forklifts = self.configuracion.get('num_montacargas', 0)
        dispatch_strategy = self.configuracion.get('dispatch_strategy', 'unknown')

        # MEJ-2 v2: nivel de servicio (mismo patron/fuente que INIT-5). En modo
        # estocastico (sin validacion de stock) available=False y
        # fill_rate_pct=None -- consistente con como ya se muestra "N/A" en el
        # visor/API/Excel, no es un caso especial nuevo.
        service_level = build_service_level_summary(self.almacen)

        # MEJ-SLA-OPT: cumplimiento de SLA (INIT-4b) para que el optimizador
        # pueda penalizar configs que hacen vencer pedidos. Sin due_time en
        # ningun pedido -> available=False y orders_late=0 (score identico).
        sla_summary = build_sla_summary(self.almacen)

        # INIT-7 F4: KPIs de inbound para comparar estrategias de slotting en el
        # A/B. Con inbound off available=False -> avg_* = None (se filtran como
        # los otros opcionales, no ensucian la media con ceros que no pasaron).
        inbound_summary = build_inbound_summary(self.almacen)

        # Construir objeto de métricas
        metrics = {
            "total_workorders_completed": total_completed,
            "total_workorders_failed": total_failed,
            "total_workorders": total_wo,
            # AUDIT menores: base del KPI limpio throughput_picks_per_s.
            "total_picks_completed": total_picks_completed,
            "avg_completion_time_seconds": avg_completion_time,
            "total_simulation_time_seconds": simulation_time,
            "resource_costs": {
                "ground_operators": ground_operators,
                "forklifts": forklifts
            },
            "dispatch_strategy": dispatch_strategy,
            "fill_rate_pct": service_level.get("fill_rate_pct"),
            "service_level": service_level,
            "orders_late": sla_summary.get("orders_late", 0),
            "sla_summary": sla_summary,
            # INIT-7 F4: comparables del slotting (None si inbound off).
            "avg_dock_to_stock": inbound_summary.get("avg_dock_to_stock"),
            "avg_putaway_distance": inbound_summary.get("avg_putaway_distance"),
            # INIT-7 F5: contencion cruzada + fill-rate con rescates cross-dock
            # (None si inbound off / sin rescates -- el A/B filtra los None).
            "avg_putaway_wait": inbound_summary.get("avg_putaway_wait"),
            "fill_rate_effective_pct": service_level.get("fill_rate_effective_pct"),
            "inbound_summary": inbound_summary,
            "timestamp": self.session_timestamp,
            "session_output_dir": self.session_output_dir
        }
        
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Escribir JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)


# Export
__all__ = ['EventGenerator']
