# -*- coding: utf-8 -*-
"""
ReplayViewerEngine - Motor puro para visualizacion de archivos .jsonl de replay.
Refactorizado desde run_simulator.py V9.2.2 - Solo capacidades de visualizacion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

# --- FEATURE FLAG FOR EVENT SOURCING ARCHITECTURE ---
# REPLAY-VIEWER-FIX: Forcing Event Sourcing to True as this is the only supported mode for replay.
USE_EVENT_SOURCING = True
# ----------------------------------------------------

import pygame
from communication.ipc_protocols import (
    EventType,
    BaseEvent,
    StateResetEvent,
    StateSnapshotEvent,
    WorkOrderStatusChangedEvent,
    WorkOrderAssignedEvent,
    WorkOrderProgressUpdatedEvent,
)
import pygame_gui
import json
import time
from datetime import datetime
import logging
import argparse
from copy import deepcopy

# REFACTOR V11: Importaciones actualizadas a arquitectura subsystems/
from subsystems.config.settings import *
from subsystems.config.colors import *
from subsystems.config.settings import SUPPORTED_RESOLUTIONS, LOGICAL_WIDTH, LOGICAL_HEIGHT

from subsystems.simulation.layout_manager import LayoutManager

# REFACTOR V11: Visualization subsystem imports
from subsystems.visualization.state import (
    inicializar_estado,
    actualizar_metricas_tiempo,
    toggle_pausa,
    toggle_dashboard,
    estado_visual,
    limpiar_estado,
    aumentar_velocidad,
    disminuir_velocidad,
    obtener_velocidad_simulacion
)
from subsystems.visualization.renderer import RendererOriginal, renderizar_diagnostico_layout, renderizar_agentes, renderizar_rutas_tours
from subsystems.visualization.dashboard import DashboardOriginal, DashboardGUI, DashboardWorldClass
from subsystems.visualization.dashboard_modern import ModernDashboard
from subsystems.visualization.dashboard_world_class import DashboardWorldClass as DashboardWC
from subsystems.visualization.replay_scrubber import REPLAY_SEEK_EVENT, ReplayScrubber

# REFACTOR V11: Config utilities - Necesarios para cargar configuracion
# ConfigurationManager replaces cargar_configuracion logic
from core.config_manager import ConfigurationManager, ConfigurationError
from core.config_utils import get_default_config, mostrar_resumen_config

# V12: Dashboard Communicator
from communication.dashboard_communicator import DashboardCommunicator


class ReplayViewerEngine:
    """Motor puro para visualizacion de archivos .jsonl de replay existentes"""

    def __init__(self):
        # REFACTOR: ConfigurationManager integration
        try:
            self.config_manager = ConfigurationManager()
            self.config_manager.validate_configuration()  # Validar configuracion cargada
            self.configuracion = self.config_manager.configuration
            print("[REPLAY-ENGINE] ConfigurationManager integrado exitosamente")
        except ConfigurationError as e:
            print(f"[REPLAY-ENGINE ERROR] Error en configuracion: {e}")
            # Fallback: usar configuracion por defecto
            self.config_manager = None
            self.configuracion = get_default_config()
            print("[REPLAY-ENGINE] Fallback: Usando configuracion por defecto")

        self.pantalla = None
        self.renderer = None
        self.dashboard = None
        self.dashboard_gui = None  # Nueva instancia de DashboardGUI
        self.ui_manager = None     # UIManager de pygame_gui
        self.reloj = None
        self.corriendo = True
        self.order_dashboard_process = None
        self.layout_manager = None
        self.window_size = (0, 0)
        self.virtual_surface = None
        self.replay_scrubber = None  # ReplayScrubber para navegacion temporal

        # V12: Dashboard Communicator & Event Sourcing Initialization
        # In this branch, we always use the event sourcing model.
        self.dashboard_communicator = DashboardCommunicator()

        # KEEP: Replay visualization motor - Core para mostrar replay
        self.event_buffer = []           # Buffer de eventos para replay
        self.playback_time = 0.0         # Reloj de reproduccion interno
        self.factor_aceleracion = 1.0    # Factor de velocidad de reproduccion
        self.dashboard_wos_state = {}
        self.processed_event_indices = set()  # Indices de eventos procesados
        self.replay_finalizado = False
        self.temporal_sync_in_progress = False

        # NEW: Event processing queue to smooth out updates
        self.last_event_idx_enqueued = -1
        self.event_processing_queue = []

        # HOLISTIC SOLUTION: Authoritative state computed from events
        self.authoritative_wo_state = {}  # Single source of truth for Work Orders
        self.temporal_mode_active = False  # Flag to indicate temporal navigation mode

        # For event sourcing model
        self.event_stream = []
        self._wo_state_cache_for_delta = {}

        if USE_EVENT_SOURCING:
            print("[ARCH] Event Sourcing model is ENABLED.")
        else:
            print("[ARCH] Event Sourcing model is DISABLED. Using legacy state management.")

    def inicializar_pygame(self):
        """Inicializa ventana de Pygame para visualizacion de replay en modo ventana REDIMENSIONABLE."""
        pygame.init() # Asegurarse de que Pygame esté inicializado

        # Volver a un tamaño de ventana inicial razonable y redimensionable
        DEFAULT_SIM_WIDTH = 960
        DEFAULT_SIM_HEIGHT = 800
        PANEL_WIDTH = 440

        initial_window_width = DEFAULT_SIM_WIDTH + PANEL_WIDTH
        initial_window_height = DEFAULT_SIM_HEIGHT

        self.pantalla = pygame.display.set_mode((initial_window_width, initial_window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Replay Viewer - Gemelo Digital (Redimensionable)")

        # `self.window_size` se refiere al área de la simulación
        self.window_size = (DEFAULT_SIM_WIDTH, DEFAULT_SIM_HEIGHT)
        print(f"[DISPLAY] Ventana inicial redimensionable: {initial_window_width}x{initial_window_height}")
        print(f"[DISPLAY] Área de simulación inicial: {self.window_size[0]}x{self.window_size[1]}")

        # La superficie virtual mantiene el tamaño lógico del mapa, no cambia
        self.virtual_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

        self.reloj = pygame.time.Clock()
        self.renderer = RendererOriginal(self.virtual_surface)
        
        # Inicializar el dashboard y otros componentes de la UI
        self._inicializar_pygame_gui()

    def _inicializar_pygame_gui(self):
        """
        Inicializa Dashboard World-Class con pygame nativo.
        
        DASHBOARD WORLD-CLASS: Integracion del nuevo dashboard profesional
        usando pygame nativo (sin pygame_gui) para maximo control y estabilidad.
        """
        print("[DASHBOARD-WC] Iniciando Dashboard World-Class...")
        try:
            # Crear Dashboard World-Class con posicion izquierda
            self.dashboard = DashboardWC(
                panel_width=440,
                panel_position='left'
            )
            print("[DASHBOARD-WC] Dashboard World-Class creado exitosamente")
            print("[DASHBOARD-WC] Panel izquierdo activo (440px)")
            
            # Sincronizar referencia para compatibilidad
            self.dashboard_gui = self.dashboard
            self.ui_manager = None  # No se usa pygame_gui
            
        except Exception as e:
            print(f"[DASHBOARD-WC ERROR] Error inicializando Dashboard World-Class: {e}")
            print(f"[DASHBOARD-WC ERROR] Tipo de error: {type(e).__name__}")
            import traceback
            print(f"[DASHBOARD-WC ERROR] Traceback: {traceback.format_exc()}")
            print("[DASHBOARD-WC] Fallback: Continuando sin dashboard")
            self.dashboard = None
            self.dashboard_gui = None
            self.ui_manager = None

    def _inicializar_replay_scrubber(self):
        """
        Inicializa el ReplayScrubber para navegacion temporal.
        """
        print("[REPLAY-SCRUBBER] Iniciando ReplayScrubber...")
        try:
            # Obtener dimensiones de la ventana
            screen_width, screen_height = self.pantalla.get_size()
            
            # Configurar posicion del scrubber (parte inferior de la ventana)
            scrubber_width = screen_width - 40  # Margen de 20px a cada lado
            scrubber_height = 30
            scrubber_x = 20
            scrubber_y = screen_height - scrubber_height - 20  # 20px desde abajo
            
            # Configurar fuente y colores
            font = pygame.font.Font(None, 24)
            colors = {
                'surface_0': (45, 45, 45),      # Fondo oscuro
                'border_primary': (70, 70, 70), # Borde
                'accent_blue': (100, 150, 255), # Progreso
                'accent_purple': (150, 100, 255), # Thumb
                'text_primary': (255, 255, 255), # Texto principal
                'text_secondary': (200, 200, 200) # Texto secundario
            }
            
            # Crear instancia del ReplayScrubber
            self.replay_scrubber = ReplayScrubber(
                x=scrubber_x,
                y=scrubber_y,
                width=scrubber_width,
                height=scrubber_height,
                font=font,
                colors=colors
            )
            
            print("[REPLAY-SCRUBBER] ReplayScrubber inicializado exitosamente")
            print(f"[REPLAY-SCRUBBER] Posicion: ({scrubber_x}, {scrubber_y}), Tamaño: {scrubber_width}x{scrubber_height}")
            
        except Exception as e:
            print(f"[REPLAY-SCRUBBER ERROR] Error inicializando ReplayScrubber: {e}")
            print(f"[REPLAY-SCRUBBER ERROR] Tipo de error: {type(e).__name__}")
            import traceback
            print(f"[REPLAY-SCRUBBER ERROR] Traceback: {traceback.format_exc()}")
            print("[REPLAY-SCRUBBER] Fallback: Continuando sin ReplayScrubber")
            self.replay_scrubber = None

    def run(self, jsonl_file_path):
        """Metodo principal - Ejecuta el motor de replay completo desde archivo .jsonl"""
        print(f"[REPLAY] Cargando archivo: {jsonl_file_path}")
        self.eventos = []
        simulation_start_event = None
        initial_work_orders = []
        total_work_orders_fijo = None
        try:
            with open(jsonl_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            if event.get('event_type') == 'SIMULATION_START':
                                simulation_start_event = event
                                initial_work_orders = event.get('initial_work_orders', [])
                                total_work_orders_fijo = event.get('total_work_orders', None)
                            else:
                                self.eventos.append(event)
                        except json.JSONDecodeError as e:
                            print(f"[REPLAY] Error parseando linea: {e}")
                            continue
            self.max_time = self.eventos[-1].get('timestamp', 0.0) if self.eventos else 0.0
            print(f"[REPLAY] {len(self.eventos)} eventos cargados. Duracion: {self.max_time:.2f}s")
        except Exception as e:
            print(f"[REPLAY ERROR] No se pudo cargar archivo de replay: {e}")
            return 1

        pygame.init()
        self.window_size = (960, 1000)
        self.inicializar_pygame()
        warehouse_width, dashboard_width = 960, 380
        
        configuracion = simulation_start_event.get('config', {}) if simulation_start_event else {}
        if configuracion:
            self.configuracion = configuracion
        elif not self.configuracion:
            print("Error: Configuracion no disponible")
            return 1

        from subsystems.visualization.state import inicializar_estado, estado_visual
        project_root = os.path.join(os.path.dirname(__file__), "..", "..")
        tmx_file = os.path.join(project_root, "layouts", "WH1.tmx")
        self.layout_manager = LayoutManager(tmx_file)
        virtual_surface = pygame.Surface((warehouse_width, warehouse_width))
        
        # Inicializar ReplayScrubber - DESHABILITADO (redundante con dashboard)
        # self._inicializar_replay_scrubber()
        self.renderer = RendererOriginal(virtual_surface)
        self.virtual_surface = virtual_surface
        inicializar_estado(None, None, configuracion, self.layout_manager)
        dashboard_wos_state = {}
        if initial_work_orders:
            for wo in initial_work_orders:
                estado_visual["work_orders"][wo['id']] = wo.copy()
                dashboard_wos_state[wo['id']] = wo.copy()
            estado_visual["metricas"]["total_wos"] = len(initial_work_orders)
            if total_work_orders_fijo is not None:
                estado_visual["metricas"]["total_wos"] = total_work_orders_fijo

        # CRITICAL FIX: Initialize self.dashboard_wos_state with initial data
        self.dashboard_wos_state = dashboard_wos_state.copy()
        print(f"[DEBUG-ReplayEngine] Initialized dashboard_wos_state with {len(self.dashboard_wos_state)} WorkOrders")

        agentes_iniciales = {}
        for evento in self.eventos[:50]:
            if evento.get('type') == 'estado_agente':
                agent_id = evento.get('agent_id')
                data = evento.get('data', {})
                if agent_id and 'position' in data and agent_id not in agentes_iniciales:
                    agentes_iniciales[agent_id] = data
        for agent_id, data in agentes_iniciales.items():
            estado_visual["operarios"][agent_id] = data.copy()

        # --- NEW FIX: Sync initial agent tasks with the dashboard ---
        print("[SYNC] Sincronizando estado inicial de tareas de agentes con el dashboard...")
        initial_sync_timestamp = 0.1 # Use a small non-zero timestamp for the event
        for agent_id, agent_data in estado_visual["operarios"].items():
            initial_task_id = agent_data.get('current_task')
            if initial_task_id and initial_task_id in self.dashboard_wos_state:
                wo_state = self.dashboard_wos_state[initial_task_id]
                if wo_state.get('status') == 'released':
                    print(f"[SYNC] Agente inicial {agent_id} tiene tarea {initial_task_id}. Actualizando estado a 'in_progress'.")
                    self._emit_event(WorkOrderStatusChangedEvent(
                        timestamp=initial_sync_timestamp,
                        wo_id=initial_task_id,
                        old_status=wo_state.get('status'),
                        new_status='in_progress',
                        agent_id=agent_id
                    ))
                    # Also update our internal state to prevent duplicate events
                    self.dashboard_wos_state[initial_task_id]['status'] = 'in_progress'
        # --- END NEW FIX ---


        self.initial_estado_visual = deepcopy(estado_visual)
        print("[REPLAY] Estado visual inicial guardado.")

        # --- FEATURE: Keyframe Caching ---
        # DISABLED: This feature is architecturally flawed and causes state corruption before playback begins.
        # It processes events in 30-second batches, which was the source of the 30-second periodic updates.
        # Disabling it ensures a clean state for the main playback loop.
        # self.keyframes = {0.0: deepcopy(self.initial_estado_visual)}
        # KEYFRAME_INTERVAL = 30.0  # Segundos
        # next_keyframe_time = KEYFRAME_INTERVAL
        #
        # temp_estado_visual_for_keyframes = deepcopy(self.initial_estado_visual)
        # temp_processed_indices = set()
        #
        # for i, evento in enumerate(self.eventos):
        #     event_timestamp = evento.get('timestamp') or 0.0
        #     if event_timestamp >= next_keyframe_time:
        #         print(f"[REPLAY] Creando keyframe en {next_keyframe_time:.2f}s")
        #         # Procesar eventos hasta este punto para generar el estado del keyframe
        #         events_for_keyframe = []
        #         for j, sub_evento in enumerate(self.eventos):
        #             if j not in temp_processed_indices and (sub_evento.get('timestamp') or 0.0) < next_keyframe_time:
        #                  events_for_keyframe.append((j, sub_evento))
        #
        #         self._process_event_batch(events_for_keyframe, silent=True)
        #         for index, _ in events_for_keyframe:
        #             temp_processed_indices.add(index)
        #
        #         self.keyframes[next_keyframe_time] = deepcopy(temp_estado_visual_for_keyframes)
        #         next_keyframe_time += KEYFRAME_INTERVAL
        # print(f"[REPLAY] {len(self.keyframes)} keyframes creados.")
        # --- Fin Keyframe Caching ---

        playback_time = 0.0
        self.playback_time = 0.0
        replay_speed = 1.0
        velocidades_permitidas = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
        self.processed_event_indices = set()
        replay_finalizado = False
        corriendo = True
        replay_pausado = False

        while corriendo:
            time_delta = self.reloj.tick(60) / 1000.0

            for event in pygame.event.get():
                if self.dashboard: self.dashboard.handle_mouse_event(event)
                
                # --- MANEJO DE VENTANA REDIMENSIONABLE ---
                if event.type == pygame.VIDEORESIZE:
                    new_width, new_height = event.w, event.h
                    self.pantalla = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
                    
                    # Recalcular el área de la simulación (pantalla total - panel)
                    PANEL_WIDTH = 440 # Asegurarse que el valor sea consistente
                    self.window_size = (new_width - PANEL_WIDTH, new_height)
                    print(f"[DISPLAY] Ventana redimensionada a: {new_width}x{new_height}. Nueva área de sim: {self.window_size[0]}x{self.window_size[1]}")
                    # El dashboard y otros elementos se adaptarán en el siguiente ciclo de renderizado
                # ------------------------------------------

                # if self.replay_scrubber: self.replay_scrubber.handle_event(event)  # DESHABILITADO
                if event.type == REPLAY_SEEK_EVENT:
                    playback_time = self.seek_to_time(event.target_time)
                    replay_finalizado = (playback_time >= self.max_time)
                    continue
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    corriendo = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_PLUS, pygame.K_KP_PLUS):
                        current_index = velocidades_permitidas.index(replay_speed) if replay_speed in velocidades_permitidas else 2
                        if current_index < len(velocidades_permitidas) - 1: replay_speed = velocidades_permitidas[current_index + 1]
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        current_index = velocidades_permitidas.index(replay_speed) if replay_speed in velocidades_permitidas else 2
                        if current_index > 0: replay_speed = velocidades_permitidas[current_index - 1]
                    elif event.key == pygame.K_SPACE:
                        replay_pausado = not replay_pausado
                    elif event.key == pygame.K_o:
                        # This logic seems to be from a previous implementation.
                        # The dashboard is now started via the communicator.
                        # Let's clean this up.
                        if not self.dashboard_communicator.is_dashboard_active:
                            self.dashboard_communicator.start_dashboard()
                            # Send initial STATE_SNAPSHOT when dashboard opens mid-replay
                            if USE_EVENT_SOURCING:
                                import time
                                time.sleep(0.5)  # Give dashboard time to initialize
                            self._send_initial_state_snapshot()
                        else:
                            self.dashboard_communicator.shutdown_dashboard()

            # V12: Check for messages from the dashboard
            if self.dashboard_communicator.is_dashboard_active:
                msg = self.dashboard_communicator.get_pending_message()
                if msg and isinstance(msg, dict):
                    msg_type = msg.get('type')
                    if msg_type == 'SEEK_TIME':
                        replay_pausado = True
                        target_time = msg.get('timestamp', 0.0)
                        playback_time = self.seek_to_time(target_time)
                    elif msg_type == 'SEEK_COMPLETE':
                        replay_pausado = False

            if not replay_pausado and not replay_finalizado:
                playback_time += time_delta * replay_speed
                self.playback_time = playback_time

                if self.dashboard_communicator.is_dashboard_active:
                    self._sync_dashboard_time(playback_time)

                # Enqueue new events based on playback_time
                for i in range(self.last_event_idx_enqueued + 1, len(self.eventos)):
                    evento = self.eventos[i]
                    if (evento.get('timestamp') or 0.0) <= playback_time:
                        self.event_processing_queue.append((i, evento))
                        self.last_event_idx_enqueued = i
                    else:
                        break  # Events are sorted by time

                # Process a manageable chunk of events per frame
                EVENTS_PER_FRAME_CHUNK = 100
                chunk_to_process = self.event_processing_queue[:EVENTS_PER_FRAME_CHUNK]
                self.event_processing_queue = self.event_processing_queue[EVENTS_PER_FRAME_CHUNK:]

                if chunk_to_process:
                    print(f"[DEBUG] Processing chunk of {len(chunk_to_process)} events. Queue size: {len(self.event_processing_queue)}")
                    self._process_event_batch(chunk_to_process)
                    
                    # Check if the simulation ended in this chunk
                    last_event_in_chunk_index = chunk_to_process[-1][0]
                    if self.eventos[last_event_in_chunk_index].get('event_type') == 'SIMULATION_END':
                        replay_finalizado = True

            if self.playback_time >= self.max_time:
                replay_finalizado = True
                self.playback_time = self.max_time

            if estado_visual.get("operarios"): 
                actualizar_metricas_tiempo(estado_visual["operarios"])
            
            self._calcular_metricas_modern_dashboard(estado_visual)
            self._calcular_throughput_min(estado_visual)

            self.pantalla.fill((240, 240, 240))
            virtual_surface.fill((25, 25, 25))
            if hasattr(self.layout_manager, 'tmx_data'): self.renderer.renderizar_mapa_tmx(virtual_surface, self.layout_manager.tmx_data)
            
            # Renderizar rutas de tours (antes que los agentes para que las rutas esten debajo)
            renderizar_rutas_tours(virtual_surface, estado_visual, self.layout_manager)
            
            # Renderizar agentes
            if estado_visual.get("operarios"):
                operarios_a_renderizar = [dict(d, id=id) for id, d in estado_visual["operarios"].items()]
                renderizar_agentes(virtual_surface, operarios_a_renderizar, self.layout_manager)

            scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
            self.pantalla.blit(scaled_surface, (440, 0))

            if self.dashboard:
                estado_visual['metricas']['max_time'] = self.max_time
                self.dashboard.render(self.pantalla, estado_visual, offset_x=0)

            font = pygame.font.Font(None, 20)
            info_text = font.render(f"REPLAY: Tiempo {self.playback_time:.2f}s | Velocidad: {replay_speed:.2f}x | Eventos {len(self.processed_event_indices)}/{len(self.eventos)}", True, (255, 255, 255))
            self.pantalla.blit(info_text, (450, 10))

            pygame.display.flip()

        pygame.quit()
        print("[REPLAY] Modo replay terminado")
        sys.exit(0)

    def _process_event_batch(self, eventos_a_procesar, silent=False):
        """
        Process batch of events and emit granular typed events.
        """
        for event_index, evento in eventos_a_procesar:
            self.processed_event_indices.add(event_index)
            event_type = evento.get('type')
            timestamp = evento.get('timestamp', 0.0)

            # ===== WorkOrder Events =====
            if event_type == 'work_order_update':
                wo_id = evento.get('id')
                if not wo_id:
                    continue

                # Update internal state cache
                self.dashboard_wos_state[wo_id] = evento.copy()
                
                # CRITICAL FIX: Update estado_visual["work_orders"] so metrics work correctly
                if wo_id not in estado_visual["work_orders"]:
                    estado_visual["work_orders"][wo_id] = {}
                
                # Get current status before update
                old_status = estado_visual["work_orders"][wo_id].get('status', 'none')
                estado_visual["work_orders"][wo_id].update(evento)
                new_status = estado_visual["work_orders"][wo_id].get('status', 'unknown')
                
                # Track WO assignment to operators for tour visualization
                assigned_agent_id = evento.get('assigned_agent_id')
                if assigned_agent_id:
                    # Convertir ID completo (ej: "GroundOperator_GroundOp-01") a ID corto (ej: "GroundOp-01")
                    # Buscar el ID corto en los operarios del estado
                    agent_id_corto = None
                    for key in estado_visual["operarios"].keys():
                        # Verificar si el ID completo contiene el ID corto o viceversa
                        if key in assigned_agent_id or assigned_agent_id in key:
                            agent_id_corto = key
                            break
                    
                    # Si no se encuentra, intentar convertir manualmente
                    if not agent_id_corto:
                        # Ejemplos: "GroundOperator_GroundOp-01" -> "GroundOp-01"
                        if "GroundOp-" in assigned_agent_id:
                            agent_id_corto = assigned_agent_id.replace("GroundOperator_", "")
                        elif "Forklift-" in assigned_agent_id:
                            agent_id_corto = assigned_agent_id.replace("Forklift_", "")
                    
                    # Usar ID corto si se encuentra
                    if agent_id_corto:
                        if agent_id_corto not in estado_visual["operarios"]:
                            estado_visual["operarios"][agent_id_corto] = {}
                        
                        if 'work_orders_asignadas' not in estado_visual["operarios"][agent_id_corto]:
                            estado_visual["operarios"][agent_id_corto]['work_orders_asignadas'] = []
                        
                        # Add WO to agent's tour if not already present
                        if wo_id not in estado_visual["operarios"][agent_id_corto]['work_orders_asignadas']:
                            estado_visual["operarios"][agent_id_corto]['work_orders_asignadas'].append(wo_id)

                # Forward the complete, original event directly to the dashboard process
                if not silent and self.dashboard_communicator:
                    self.dashboard_communicator._send_message_with_retry(evento, max_retries=1, timeout=0.1)

            # ===== Partial Discharge Events =====
            elif event_type == 'partial_discharge':
                agent_id = evento.get('agent_id')
                cargo_restante = evento.get('cargo_restante', 0)
                volumen_descargado = evento.get('volumen_descargado', 0)
                
                if agent_id:
                    # Actualizar inmediatamente el cargo_volume en estado_visual
                    if agent_id not in estado_visual["operarios"]:
                        estado_visual["operarios"][agent_id] = {}
                    
                    # Obtener volumen ANTERIOR para comparacion
                    volumen_anterior = estado_visual["operarios"][agent_id].get('carga', 0)
                    
                    # ACTUALIZAR EL VOLUMEN EN EL ESTADO VISUAL
                    estado_visual["operarios"][agent_id]['carga'] = cargo_restante
                    estado_visual["operarios"][agent_id]['cargo_volume'] = cargo_restante
                    
                    print(f"[PARTIAL-DISCHARGE] {agent_id}: {volumen_anterior}L -> {cargo_restante}L (descargados {volumen_descargado}L) en t={timestamp:.1f}s")
                    
                    # DEBUG: Verificar que el valor se actualizo
                    nuevo_valor = estado_visual["operarios"][agent_id].get('carga', 'ERROR')
                    print(f"[DEBUG-VOLUME] Valor en estado_visual despues de update: {nuevo_valor}L")

            # ===== Agent Events =====
            elif event_type == 'estado_agente':
                agent_id = evento.get('agent_id')
                data = evento.get('data', {})
                
                if agent_id:
                    # Get previous state for comparison
                    prev_agent_state = estado_visual["operarios"].get(agent_id, {})

                    # Update visual state for Pygame rendering FIRST
                    if agent_id not in estado_visual["operarios"]:
                        estado_visual["operarios"][agent_id] = {}
                    estado_visual["operarios"][agent_id].update(data)
                    
                    # Track tour information: extract WO IDs from tour_actual if available
                    if 'tour_actual' in data and data['tour_actual']:
                        tour_info = data['tour_actual']
                        if isinstance(tour_info, dict) and 'work_orders' in tour_info:
                            # Update work_orders_asignadas from tour
                            wo_ids = [wo.get('id', wo) if isinstance(wo, dict) else wo 
                                     for wo in tour_info['work_orders']]
                            estado_visual["operarios"][agent_id]['work_orders_asignadas'] = wo_ids
                    
                    # DEBUG: Track status changes for utilization calculation
                    if 'status' in data and data['status'] != prev_agent_state.get('status'):
                        print(f"[DEBUG-UTIL] {agent_id}: {prev_agent_state.get('status', 'None')} -> {data['status']}")

                    # --- NEW LOGIC: Sync dashboard from agent state ---
                    new_task_id = data.get('current_task')
                    old_task_id = prev_agent_state.get('current_task')

                    if new_task_id != old_task_id:
                        # Agent started a new task
                        if new_task_id and new_task_id in self.dashboard_wos_state:
                            wo_state = self.dashboard_wos_state[new_task_id]
                            # If the WO was 'released' or 'assigned', it's now 'in_progress'.
                            if wo_state.get('status') in ['released', 'assigned']:
                                if not silent:
                                    self._emit_event(WorkOrderStatusChangedEvent(
                                        timestamp=timestamp,
                                        wo_id=new_task_id,
                                        old_status=wo_state.get('status'),
                                        new_status='in_progress',
                                        agent_id=agent_id
                                    ))
                                # Also update our internal state to prevent duplicate events
                                self.dashboard_wos_state[new_task_id]['status'] = 'in_progress'
                    # --- END NEW LOGIC ---

                    # Original debug log for position
                    if 'position' in data:
                        position = data.get('position', [0, 0])
                        # print(f"[DEBUG-AGENT] Updated position for {agent_id}: {position}")

    def _emit_event(self, event: BaseEvent, block: bool = True):
        """Serializa y envía un evento al dashboard."""
        if self.dashboard_communicator:
            self.dashboard_communicator.send_event(event, block=block)

    def _send_initial_state_snapshot(self):
        """Envía el STATE_SNAPSHOT inicial al dashboard cuando se inicia."""
        print("[DEBUG-EVENT] Sending initial STATE_SNAPSHOT to dashboard")

        # Convertir dashboard_wos_state a lista para el snapshot
        work_orders_list = []
        for wo_id, wo_data in self.dashboard_wos_state.items():
            work_orders_list.append(wo_data)

        # Crear el snapshot inicial
        initial_snapshot = StateSnapshotEvent(
            timestamp=self.playback_time,
            work_orders=work_orders_list,
            operators=[],  # Por ahora vacío, se puede expandir después
            metrics={
                'total_work_orders': len(work_orders_list),
                'completed_work_orders': 0,
                'current_time': self.playback_time
            }
        )

        # Enviar el snapshot
        self._emit_event(initial_snapshot)
        print(f"[DEBUG-EVENT] Initial STATE_SNAPSHOT sent with {len(work_orders_list)} WorkOrders")


    def seek_to_time(self, target_time):
        """
        Emite eventos para reconstruir el estado en el dashboard a un tiempo específico.
        """
        print(f"[EVENT-ENGINE] Seeking to {target_time:.2f}s")

        # 1. Emitir STATE_RESET para limpiar el dashboard
        self._emit_event(StateResetEvent(timestamp=target_time, reason="seek", target_time=target_time))

        # 2. Encontrar todos los eventos hasta el tiempo objetivo
        # En una implementación completa, esto podría usar un event store optimizado.
        # Aquí, simplemente filtramos la lista en memoria.
        events_to_replay = [e for e in self.eventos if (e.get('timestamp') or 0.0) <= target_time]

        # 3. Calcular el snapshot a partir de los eventos
        state_snapshot = self._compute_snapshot_from_events(events_to_replay, target_time)

        # 4. Emitir STATE_SNAPSHOT con el estado reconstruido
        self._emit_event(StateSnapshotEvent(
            timestamp=target_time,
            work_orders=state_snapshot['work_orders'],
            operators=state_snapshot['operators'],
            metrics=state_snapshot['metrics']
        ))

        # 5. Actualizar el estado interno del ReplayEngine
        self.playback_time = target_time
        # Simulamos el reprocesamiento para el UI local de Pygame
        self.processed_event_indices = {i for i, e in enumerate(self.eventos) if (e.get('timestamp') or 0.0) <= target_time}

        # BUGFIX: Reset the engine's internal state cache to match the snapshot.
        # This ensures that when playback resumes, change detection in _process_event_batch
        # compares against the correct historical state.
        self.dashboard_wos_state = {wo['id']: wo for wo in state_snapshot['work_orders']}

        # NEW: Reset event processing queue after a seek
        self.event_processing_queue = []
        if self.processed_event_indices:
            self.last_event_idx_enqueued = max(self.processed_event_indices)
        else:
            self.last_event_idx_enqueued = -1

        # Update the global estado_visual for the Pygame UI
        global estado_visual
        estado_visual['work_orders'] = {wo['id']: wo for wo in state_snapshot['work_orders']}
        estado_visual['operarios'] = {op['id']: op for op in state_snapshot['operators']}
        estado_visual['metricas'] = state_snapshot['metrics']
        
        # Sync time
        self._sync_dashboard_time(target_time)

        print(f"[EVENT-ENGINE] Seek complete: {len(events_to_replay)} events processed for snapshot.")
        return target_time

    def _compute_snapshot_from_events(self, events: list, target_time: float) -> dict:
        """
        Reconstruye y devuelve un snapshot del estado del mundo a partir de una secuencia de eventos.
        """
        # FIX: Start with a deepcopy of the initial state, not the current state.
        initial_wos = deepcopy(self.initial_estado_visual.get('work_orders', {}))
        state = {
            'work_orders': initial_wos,
            'operators': {},
            'metrics': {}
        }

        # Apply event changes sequentially up to the target_time
        for event in events:
            event_type = event.get('type')
            if event_type == 'work_order_update':
                wo_id = event.get('id')
                if wo_id:
                    # FIX: Create WO if it doesn't exist (for WOs created during simulation)
                    if wo_id not in state['work_orders']:
                        state['work_orders'][wo_id] = {}

                    # The event contains the updated state for the WO at that timestamp.
                    # We just need to apply all its fields.
                    prev_wo = state['work_orders'][wo_id].copy()
                    state['work_orders'][wo_id].update(event)

                    new_agent = event.get('assigned_agent_id')
                    old_agent = prev_wo.get('assigned_agent_id')

                    if new_agent != old_agent:
                        # Un-assign from old agent
                        if old_agent and old_agent in state["operators"]:
                            if state["operators"][old_agent].get('current_task') == wo_id:
                                state["operators"][old_agent]['current_task'] = None
                                state["operators"][old_agent]['current_work_area'] = None

                        # Assign to new agent
                        if new_agent and new_agent in state["operators"]:
                            state["operators"][new_agent]['current_task'] = wo_id
                            work_area = event.get('work_area')
                            if work_area:
                                state["operators"][new_agent]['current_work_area'] = work_area
                    
                    # FIX: Also update work_orders_asignadas for the assigned agent
                    # Moved OUTSIDE the conditional blocks to ensure it runs even if agent not yet in state
                    # or if assignment didn't change but we need to populate the list.
                    assigned_agent_id = event.get('assigned_agent_id')
                    if assigned_agent_id:
                        # Resolve short ID
                        agent_id_corto = None
                        for key in state["operators"].keys():
                            if key in assigned_agent_id or assigned_agent_id in key:
                                agent_id_corto = key
                                break
                        
                        if not agent_id_corto:
                            if "GroundOp-" in assigned_agent_id:
                                agent_id_corto = assigned_agent_id.replace("GroundOperator_", "")
                            elif "Forklift-" in assigned_agent_id:
                                agent_id_corto = assigned_agent_id.replace("Forklift_", "")
                        
                        if agent_id_corto:
                            if agent_id_corto not in state["operators"]:
                                state["operators"][agent_id_corto] = {}
                            
                            if 'work_orders_asignadas' not in state["operators"][agent_id_corto]:
                                state["operators"][agent_id_corto]['work_orders_asignadas'] = []
                            
                            if wo_id not in state["operators"][agent_id_corto]['work_orders_asignadas']:
                                state["operators"][agent_id_corto]['work_orders_asignadas'].append(wo_id)

            elif event_type == 'estado_agente':
                agent_id = event.get('agent_id')
                if agent_id:
                    if agent_id not in state['operators']:
                        state['operators'][agent_id] = {}
                    data = event.get('data', {})
                    state['operators'][agent_id].update(data)

                    # FIX: Reconstruct work_orders_asignadas from tour_actual
                    if 'tour_actual' in data and data['tour_actual']:
                        tour_info = data['tour_actual']
                        if isinstance(tour_info, dict) and 'work_orders' in tour_info:
                            wo_ids = [wo.get('id', wo) if isinstance(wo, dict) else wo 
                                     for wo in tour_info['work_orders']]
                            state['operators'][agent_id]['work_orders_asignadas'] = wo_ids

        # Convert dicts to lists for the snapshot payload
        state['work_orders'] = list(state['work_orders'].values())
        
        operators_list = []
        for op_id, op_data in state['operators'].items():
            op_data['id'] = op_id # Add the ID into the dictionary
            operators_list.append(op_data)
        state['operators'] = operators_list

        # Calculate metrics based on the reconstructed state
        completed_wos = sum(1 for wo in state['work_orders'] if wo.get('status') == 'staged')
        state['metrics'] = {
            'total_work_orders': len(state['work_orders']),
            'completed_work_orders': completed_wos,
            'current_time': target_time
        }

        return state

    def _sync_dashboard_time(self, current_time):
        """
        Sync dashboard time slider with current playback time.
        """
        try:
            if USE_EVENT_SOURCING:
                # Event Sourcing mode: Send TIME_TICK event
                from communication.ipc_protocols import TimeTickEvent
                self._emit_event(TimeTickEvent(
                    timestamp=current_time,
                    elapsed_time=current_time,
                    total_duration=self.max_time
                ), block=False)
            else:
                # Legacy mode: Send TIME_UPDATE message
                message = {
                    'type': 'TIME_UPDATE',
                    'timestamp': current_time,
                    'max_time': self.max_time
                }
                self.dashboard_communicator._send_message_with_retry(message, max_retries=1)
        except Exception as e:
            print(f"[DEBUG-ReplayEngine] Failed to sync dashboard time: {e}")

    def _calcular_metricas_modern_dashboard(self, estado_visual):
        """
        Calcula las métricas que necesita el ModernDashboard.
        
        Args:
            estado_visual: Dict con el estado actual de la simulación
        """
        if "metricas" not in estado_visual:
            estado_visual["metricas"] = {}
        
        total_wos = estado_visual["metricas"].get("total_wos", 0)
        
        work_orders = estado_visual.get("work_orders", {})
        workorders_completadas = 0
        tareas_completadas = 0
        
        for wo_id, wo_data in work_orders.items():
            status = wo_data.get('status', 'unknown')
            if status in ['staged', 'Completada', 'COMPLETED']:
                workorders_completadas += 1
                tareas_completadas += 3
        
        tiempo_simulacion = self.playback_time
        
        estado_visual["metricas"]["tiempo"] = tiempo_simulacion
        estado_visual["metricas"]["workorders_completadas"] = workorders_completadas
        estado_visual["metricas"]["total_wos"] = total_wos
        estado_visual["metricas"]["tareas_completadas"] = tareas_completadas
        
        if total_wos > 0 and int(tiempo_simulacion) % 10 == 0:
            print(f"[METRICAS] WO: {workorders_completadas}/{total_wos}, Tareas: {tareas_completadas}, Tiempo: {tiempo_simulacion:.1f}s")

    def _calcular_throughput_min(self, estado_visual):
        """Calcula throughput por minuto (WO completadas / minuto)."""
        if "metricas" not in estado_visual:
            estado_visual["metricas"] = {}
        tiempo = self.playback_time
        completadas = estado_visual["metricas"].get("workorders_completadas", 0)
        
        # Calculate throughput: WOs per minute
        if tiempo > 0:
            throughput = (completadas / tiempo) * 60.0
        else:
            throughput = 0.0
        
        estado_visual["metricas"]["throughput_min"] = throughput

    def limpiar_recursos(self):
        """Limpia recursos al cerrar"""
        if self.dashboard_communicator and self.dashboard_communicator.is_dashboard_active:
            print("[CLEANUP] Cerrando dashboard...")
            self.dashboard_communicator.shutdown_dashboard()

        pygame.quit()
        print("[CLEANUP] Recursos limpiados exitosamente")
        sys.exit(0)