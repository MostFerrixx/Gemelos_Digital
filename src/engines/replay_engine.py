# -*- coding: utf-8 -*-
"""
ReplayViewerEngine - Motor puro para visualizacion de archivos .jsonl de replay.
Refactorizado desde run_simulator.py V9.2.2 - Solo capacidades de visualizacion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

# --- FEATURE FLAG FOR EVENT SOURCING ARCHITECTURE ---
USE_EVENT_SOURCING = os.getenv('USE_EVENT_SOURCING', 'false').lower() == 'true'
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
from subsystems.visualization.renderer import RendererOriginal, renderizar_diagnostico_layout, renderizar_agentes
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
        """Inicializa ventana de Pygame para visualizacion de replay"""
        # KEEP: Todo el metodo - Necesario para crear ventana

        PANEL_WIDTH = 440
        # 1. Obtener la clave de resolucion seleccionada por el usuario
        resolution_key = self.configuracion.get('selected_resolution_key', "Pequena (800x800)")

        # 2. Buscar el tamano (ancho, alto) en nuestro diccionario
        self.window_size = SUPPORTED_RESOLUTIONS.get(resolution_key, (800, 800))

        print(f"[DISPLAY] Resolucion seleccionada por el usuario: '{resolution_key}' -> {self.window_size[0]}x{self.window_size[1]}")

        # 3. Hacemos la ventana principal mas ancha para acomodar el panel
        main_window_width = self.window_size[0] + PANEL_WIDTH
        main_window_height = self.window_size[1]
        self.pantalla = pygame.display.set_mode((main_window_width, main_window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Replay Viewer - Gemelo Digital")

        # 4. La superficie virtual mantiene el tamano logico del mapa
        self.virtual_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        print(f"Ventana creada: {main_window_width}x{main_window_height}. Panel UI: {PANEL_WIDTH}px.")

        self.reloj = pygame.time.Clock()
        self.renderer = RendererOriginal(self.virtual_surface)
        
        # PYGAME_GUI FASE 2.5: Inicializar UIManager y DashboardGUI refactorizada
        self._inicializar_pygame_gui()
        
        # NOTA: la creacion del ModernDashboard se realiza en _inicializar_pygame_gui().
        # Aqui evitamos crear una segunda instancia para no duplicar elementos UI.

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

        self.initial_estado_visual = deepcopy(estado_visual)
        print("[REPLAY] Estado visual inicial guardado.")

        # --- FEATURE: Keyframe Caching ---
        self.keyframes = {0.0: deepcopy(self.initial_estado_visual)}
        KEYFRAME_INTERVAL = 30.0  # Segundos
        next_keyframe_time = KEYFRAME_INTERVAL

        temp_estado_visual_for_keyframes = deepcopy(self.initial_estado_visual)
        temp_processed_indices = set()

        for i, evento in enumerate(self.eventos):
            event_timestamp = evento.get('timestamp') or 0.0
            if event_timestamp >= next_keyframe_time:
                print(f"[REPLAY] Creando keyframe en {next_keyframe_time:.2f}s")
                # Procesar eventos hasta este punto para generar el estado del keyframe
                events_for_keyframe = []
                for j, sub_evento in enumerate(self.eventos):
                    if j not in temp_processed_indices and (sub_evento.get('timestamp') or 0.0) < next_keyframe_time:
                         events_for_keyframe.append((j, sub_evento))

                self._process_event_batch(events_for_keyframe, temp_estado_visual_for_keyframes, None)
                for index, _ in events_for_keyframe:
                    temp_processed_indices.add(index)

                self.keyframes[next_keyframe_time] = deepcopy(temp_estado_visual_for_keyframes)
                next_keyframe_time += KEYFRAME_INTERVAL
        print(f"[REPLAY] {len(self.keyframes)} keyframes creados.")
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
                        self.dashboard_communicator.toggle_dashboard()
                        if self.dashboard_communicator.is_dashboard_active:
                            self.dashboard_communicator.update_dashboard_state()
            
            # V12: Check for messages from the dashboard
            if self.dashboard_communicator.is_dashboard_active:
                msg = self.dashboard_communicator.get_pending_message()
                if msg:
                    print(f"[DEBUG-ReplayEngine] Received message: {msg}")
                if msg and isinstance(msg, dict):
                    msg_type = msg.get('type')
                    print(f"[DEBUG-ReplayEngine] Message type: {msg_type}")
                    if msg_type == 'SEEK_TIME':
                        replay_pausado = True
                        target_time = msg.get('timestamp', 0.0)
                        playback_time = self.seek_to_time(target_time)
                        print(f"[REPLAY_ENGINE] Seek command received. Emitting RESET/SNAPSHOT events for t={target_time:.2f}s.")
                    elif msg_type == 'SEEK_COMPLETE':
                        replay_pausado = False
                        print(f"[REPLAY_ENGINE] SEEK_COMPLETE received. Resuming playback.")

            if not replay_pausado and not replay_finalizado:
                playback_time += time_delta * replay_speed
                self.playback_time = playback_time

                # Sync dashboard time slider with current playback time
                if self.dashboard_communicator.is_dashboard_active:
                    self._sync_dashboard_time(playback_time)
                eventos_a_procesar = []
                for i, evento in enumerate(self.eventos):
                    if i not in self.processed_event_indices and (evento.get('timestamp') or 0.0) <= playback_time:
                        eventos_a_procesar.append((i, evento))
                if eventos_a_procesar:
                    self._process_event_batch(eventos_a_procesar, estado_visual, dashboard_wos_state)
                    # CRITICAL FIX: Sync dashboard_wos_state with processed data
                    self.dashboard_wos_state.update(dashboard_wos_state)
                    print(f"[DEBUG-ReplayEngine] Synced dashboard_wos_state: {len(self.dashboard_wos_state)} WorkOrders")

                    # HOLISTIC: Update dashboard only if not in temporal mode
                    if self.dashboard_communicator.is_dashboard_active and not self.temporal_mode_active:
                        self.dashboard_communicator.update_dashboard_state()

                    if self.eventos[eventos_a_procesar[-1][0]].get('event_type') == 'SIMULATION_END':
                        replay_finalizado = True

            if self.playback_time >= self.max_time:
                replay_finalizado = True
                self.playback_time = self.max_time

            if estado_visual.get("operarios"): actualizar_metricas_tiempo(estado_visual["operarios"])
            self._calcular_metricas_modern_dashboard(estado_visual)
            self._calcular_throughput_min(estado_visual)

            self.pantalla.fill((240, 240, 240))
            virtual_surface.fill((25, 25, 25))
            if hasattr(self.layout_manager, 'tmx_data'): self.renderer.renderizar_mapa_tmx(virtual_surface, self.layout_manager.tmx_data)
            if estado_visual.get("operarios"):
                operarios_a_renderizar = [dict(d, id=id) for id, d in estado_visual["operarios"].items()]
                renderizar_agentes(virtual_surface, operarios_a_renderizar, self.layout_manager)

            scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
            self.pantalla.blit(scaled_surface, (440, 0))

            if self.dashboard:
                estado_visual['metricas']['max_time'] = self.max_time
                self.dashboard.render(self.pantalla, estado_visual, offset_x=0)

            # Renderizar ReplayScrubber - DESHABILITADO (redundante con dashboard)
            # if self.replay_scrubber:
            #     self.replay_scrubber.update(playback_time, self.max_time)
            #     self.replay_scrubber.draw(self.pantalla)

            font = pygame.font.Font(None, 20)
            info_text = font.render(f"REPLAY: Tiempo {self.playback_time:.2f}s | Velocidad: {replay_speed:.2f}x | Eventos {len(self.processed_event_indices)}/{len(self.eventos)}", True, (255, 255, 255))
            self.pantalla.blit(info_text, (450, 10))

            pygame.display.flip()

        pygame.quit()
        print("[REPLAY] Modo replay terminado")
        return 0

    def _process_event_batch(self, eventos_a_procesar, estado_visual, dashboard_wos_state):
        """
        Procesa un lote de eventos para actualizar el estado visual."""
        # In this branch, we always use the event sourcing model.
        for event_index, evento in eventos_a_procesar:
            self.processed_event_indices.add(event_index)
            self._convert_and_emit_raw_event(evento)

    def _convert_and_emit_raw_event(self, evento: dict):
        """Convierte un evento JSON crudo en uno o más eventos tipados y los emite."""
        event_type = evento.get('type')
        if event_type == 'work_order_update':
            self._convert_and_emit_wo_update_event(evento)
        # Aquí se podrían manejar otros tipos de eventos como 'estado_agente'

    def _convert_and_emit_wo_update_event(self, evento: dict):
        """Maneja la conversión de un evento 'work_order_update'."""
        wo_id = evento.get('id')
        if not wo_id: return

        timestamp = evento.get('timestamp')
        new_status = evento.get('status')
        new_agent = evento.get('assigned_agent_id')
        cantidad = evento.get('cantidad_restante', 0)
        volumen = evento.get('volumen_restante', 0.0)

        old_state = self._wo_state_cache_for_delta.get(wo_id, {})
        old_status = old_state.get('status')

        if new_status and old_status != new_status:
            self._emit_event(WorkOrderStatusChangedEvent(
                timestamp=timestamp, wo_id=wo_id, old_status=old_status or "unknown",
                new_status=new_status, agent_id=new_agent
            ))

        if new_agent and old_state.get('assigned_agent_id') != new_agent:
            self._emit_event(WorkOrderAssignedEvent(
                timestamp=timestamp, wo_id=wo_id, agent_id=new_agent,
                timestamp_assigned=timestamp
            ))

        if old_state.get('cantidad_restante') != cantidad or old_state.get('volumen_restante') != volumen:
            self._emit_event(WorkOrderProgressUpdatedEvent(
                timestamp=timestamp, wo_id=wo_id, cantidad_restante=cantidad,
                volumen_restante=volumen, progress_percentage=self._calculate_progress(evento)
            ))

        self._wo_state_cache_for_delta[wo_id] = evento

    def _calculate_progress(self, evento: dict) -> float:
        return 0.0  # Lógica de cálculo de progreso pendiente

    def _emit_event(self, event: BaseEvent):
        """Serializa y envía un evento al dashboard."""
        if self.dashboard_communicator:
            self.dashboard_communicator.send_event(event)


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
        state_snapshot = self._compute_snapshot_from_events(events_to_replay)

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

        print(f"[EVENT-ENGINE] Seek complete: {len(events_to_replay)} events processed for snapshot.")
        return target_time

    def _compute_snapshot_from_events(self, events: list) -> dict:
        """
        Reconstruye y devuelve un snapshot del estado del mundo a partir de una secuencia de eventos.
        """
        state = {
            'work_orders': {},
            'operators': {},
            'metrics': {}
        }
        # Este método es una simulación de cómo el dashboard reconstruiría el estado.
        # Procesa los eventos crudos para generar un estado final.
        for event in events:
            event_type = event.get('type')
            if event_type == 'work_order_update':
                wo_id = event.get('id')
                if wo_id:
                    if wo_id not in state['work_orders']:
                        state['work_orders'][wo_id] = {}
                    state['work_orders'][wo_id].update(event)
            elif event_type == 'estado_agente':
                agent_id = event.get('agent_id')
                if agent_id:
                    if agent_id not in state['operators']:
                        state['operators'][agent_id] = {}
                    state['operators'][agent_id].update(event.get('data', {}))

        # Convertir a listas de diccionarios para el snapshot
        state['work_orders'] = list(state['work_orders'].values())
        state['operators'] = list(state['operators'].values())

        return state

    def _sync_dashboard_time(self, current_time):
        """
        Sync dashboard time slider with current playback time.
        """
        try:
            # Send time update message to dashboard
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
            if status in ['completed', 'Completada', 'COMPLETED']:
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
        if tiempo > 0:
            estado_visual["metricas"]["throughput_min"] = (completadas / max(tiempo, 1e-6)) * 60.0
        else:
            estado_visual["metricas"]["throughput_min"] = 0.0

    def limpiar_recursos(self):
        """Limpia recursos al cerrar"""
        if self.dashboard_communicator and self.dashboard_communicator.is_dashboard_active:
            print("[CLEANUP] Cerrando dashboard...")
            self.dashboard_communicator.shutdown_dashboard()

        pygame.quit()
        print("[CLEANUP] Recursos limpiados exitosamente")