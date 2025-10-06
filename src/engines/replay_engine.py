# -*- coding: utf-8 -*-
"""
ReplayViewerEngine - Motor puro para visualizacion de archivos .jsonl de replay.
Refactorizado desde run_simulator.py V9.2.2 - Solo capacidades de visualizacion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

import pygame
import json
import time
from datetime import datetime
import logging
import argparse

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
from subsystems.visualization.renderer import RendererOriginal, renderizar_diagnostico_layout
from subsystems.visualization.dashboard import DashboardOriginal

# REFACTOR V11: Config utilities - Necesarios para cargar configuracion
# ConfigurationManager replaces cargar_configuracion logic
from core.config_manager import ConfigurationManager, ConfigurationError
from core.config_utils import get_default_config, mostrar_resumen_config

class ReplayViewerEngine:
    """Motor puro para visualizacion de archivos .jsonl de replay existentes"""

    def __init__(self):
        # REFACTOR: ConfigurationManager integration
        try:
            self.config_manager = ConfigurationManager()
            self.config_manager.validate_configuration()  # Validar configuración cargada
            self.configuracion = self.config_manager.configuration
            print("[REPLAY-ENGINE] ConfigurationManager integrado exitosamente")
        except ConfigurationError as e:
            print(f"[REPLAY-ENGINE ERROR] Error en configuracion: {e}")
            # Fallback: usar configuración por defecto
            self.config_manager = None
            self.configuracion = get_default_config()
            print("[REPLAY-ENGINE] Fallback: Usando configuracion por defecto")

        self.pantalla = None
        self.renderer = None
        self.dashboard = None
        self.reloj = None
        self.corriendo = True
        self.order_dashboard_process = None
        self.layout_manager = None
        self.window_size = (0, 0)
        self.virtual_surface = None

        # KEEP: Replay visualization motor - Core para mostrar replay
        self.event_buffer = []           # Buffer de eventos para replay
        self.playback_time = 0.0         # Reloj de reproduccion interno
        self.factor_aceleracion = 1.0    # Factor de velocidad de reproduccion

    def inicializar_pygame(self):
        """Inicializa ventana de Pygame para visualizacion de replay"""
        # KEEP: Todo el metodo - Necesario para crear ventana

        PANEL_WIDTH = 400
        # 1. Obtener la clave de resolucion seleccionada por el usuario
        resolution_key = self.configuracion.get('selected_resolution_key', "Pequena (800x800)")

        # 2. Buscar el tamaño (ancho, alto) en nuestro diccionario
        self.window_size = SUPPORTED_RESOLUTIONS.get(resolution_key, (800, 800))

        print(f"[DISPLAY] Resolucion seleccionada por el usuario: '{resolution_key}' -> {self.window_size[0]}x{self.window_size[1]}")

        # 3. Hacemos la ventana principal más ancha para acomodar el panel
        main_window_width = self.window_size[0] + PANEL_WIDTH
        main_window_height = self.window_size[1]
        self.pantalla = pygame.display.set_mode((main_window_width, main_window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Replay Viewer - Gemelo Digital")

        # 4. La superficie virtual mantiene el tamaño lógico del mapa
        self.virtual_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        print(f"Ventana creada: {main_window_width}x{main_window_height}. Panel UI: {PANEL_WIDTH}px.")

        self.reloj = pygame.time.Clock()
        self.renderer = RendererOriginal(self.virtual_surface)
        self.dashboard = DashboardOriginal()

    # REFACTOR: Method replaced by ConfigurationManager integration in __init__
    # Original method preserved below (commented out) for reference
    def cargar_configuracion(self):
        """
        ORIGINAL METHOD - Now handled by ConfigurationManager in __init__

        Carga la configuración desde config.json o usa defaults hardcodeados

        MIGRATION NOTE: This method has been replaced by ConfigurationManager
        integration in __init__(). Configuration is now loaded automatically
        during ReplayViewerEngine instantiation with robust error handling.

        Original functionality moved to:
        - core.config_manager.ConfigurationManager._load_configuration()
        - core.config_manager.ConfigurationManager._sanitize_assignment_rules()
        """
        # COMMENTED OUT - Original implementation preserved for reference
        # KEEP: Todo el método - Necesario para configurar el replay viewer
        #
        # config_path = os.path.join(os.path.dirname(__file__), "config.json")
        #
        # try:
        #     # Intentar cargar config.json
        #     if os.path.exists(config_path):
        #         print(f"[CONFIG] Cargando configuración desde: {config_path}")
        #         with open(config_path, 'r', encoding='utf-8') as f:
        #             self.configuracion = json.load(f)
        #
        #         # KEEP: Sanitización - Necesaria para compatibilidad
        #         # Sanitizar assignment_rules: convertir claves str a int
        #         if 'assignment_rules' in self.configuracion and self.configuracion['assignment_rules']:
        #             sanitized_rules = {}
        #             for agent_type, rules in self.configuracion['assignment_rules'].items():
        #                 sanitized_rules[agent_type] = {int(k): v for k, v in rules.items()}
        #             self.configuracion['assignment_rules'] = sanitized_rules
        #
        #         print("[CONFIG] Configuración cargada exitosamente desde archivo JSON")
        #     else:
        #         print("[CONFIG] config.json no encontrado, usando configuración por defecto")
        #         self.configuracion = get_default_config()
        #         print("[CONFIG] Configuración por defecto cargada")
        #
        #     # ELIMINATED: cost_calculator - No needed for replay visualization
        #     # ELIMINATED: # Nota: cost_calculator se creará después de inicializar data_manager
        #
        #     # Mostrar resumen de configuración cargada
        #     mostrar_resumen_config(self.configuracion)
        #
        #     return True
        #
        # except json.JSONDecodeError as e:
        #     print(f"[CONFIG ERROR] Error al parsear config.json: {e}")
        #     print("[CONFIG] Usando configuración por defecto como fallback")
        #     self.configuracion = get_default_config()
        #     return True
        #
        # except Exception as e:
        #     print(f"[CONFIG ERROR] Error inesperado cargando configuración: {e}")
        #     print("[CONFIG] Usando configuración por defecto como fallback")
        #     self.configuracion = get_default_config()
        #     return True

        # NEW IMPLEMENTATION: Return success since config is loaded in __init__
        return True

    # ELIMINATED: def crear_simulacion(self) - No simulation creation needed for replay viewer
    # Todo el método eliminado ya que el replay viewer no crea simulaciones
    def inicializar_layout_para_visualizacion(self):
        """Inicializa solo el layout manager para mostrar el mapa TMX en replay"""
        # KEEP: Solo la parte de layout - Necesaria para mostrar el mapa de fondo

        if not self.configuracion:
            print("Error: No hay configuración válida")
            return False

        print("[REPLAY-VIEWER] Inicializando layout TMX para visualización...")

        # Inicializar pygame si no está inicializado
        if not pygame.get_init():
            pygame.init()
            pygame.display.set_mode((100, 100))  # Ventana temporal para TMX

        # 1. Inicializar LayoutManager con archivo TMX por defecto (OBLIGATORIO para mostrar mapa)
        tmx_file = os.path.join(os.path.dirname(__file__), "layouts", "WH1.tmx")
        print(f"[TMX] Cargando layout: {tmx_file}")

        try:
            self.layout_manager = LayoutManager(tmx_file)
        except Exception as e:
            print(f"[FATAL ERROR] No se pudo cargar archivo TMX: {e}")
            print("[FATAL ERROR] El replay viewer requiere un archivo TMX válido para mostrar el mapa.")
            raise SystemExit(f"Error cargando TMX: {e}")


        print(f"[TMX] Layout inicializado para replay viewer:")
        print(f"  - Dimensiones: {self.layout_manager.grid_width}x{self.layout_manager.grid_height}")
        print(f"  - Puntos de picking: {len(self.layout_manager.picking_points)}")

        return True

    # ELIMINATED: def _proceso_actualizacion_metricas(self) - No simulation metrics needed

    def ejecutar_bucle_visualizacion_replay(self):
        """Bucle principal para visualización de replay - versión simplificada"""
        # KEEP: Core visualization loop - Necesario para mostrar replay

        from subsystems.visualization.renderer import renderizar_agentes, renderizar_dashboard
        from subsystems.visualization.state import estado_visual, obtener_velocidad_simulacion

        self.corriendo = True
        while self.corriendo:
            # 1. KEEP: Manejar eventos (siempre necesario)
            for event in pygame.event.get():
                if not self._manejar_evento(event):
                    self.corriendo = False

            # 3. Renderizado - Core para mostrar replay
            self.pantalla.fill((240, 240, 240))  # Fondo gris claro

            # 4. Dibujar el mundo de replay en la superficie virtual
            self.virtual_surface.fill((25, 25, 25))
            if hasattr(self, 'layout_manager') and self.layout_manager:
                self.renderer.renderizar_mapa_tmx(self.virtual_surface, self.layout_manager.tmx_data)

            # Obtener lista de agentes para renderizar desde estado visual
            from subsystems.visualization.state import estado_visual
            agentes_para_renderizar = list(estado_visual.get('operarios', {}).values())
            renderizar_agentes(self.virtual_surface, agentes_para_renderizar, self.layout_manager)

            # 5. KEEP: Escalar la superficie virtual al área de simulación en la pantalla
            scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
            self.pantalla.blit(scaled_surface, (0, 0))  # Dibujar el mundo a la izquierda

            # 6. KEEP: Dibujar el dashboard - Modificado para replay
            # ELIMINATED: renderizar_dashboard(self.pantalla, self.window_size[0], self.almacen, estado_visual["operarios"])
            # Renderizar dashboard simplificado para replay
            self._renderizar_dashboard_replay()

            # 7. ELIMINATED: Verificación de finalización - No simulation to finish

            # 8. KEEP: Actualizar la pantalla
            pygame.display.flip()
            self.reloj.tick(30)

        print("Replay viewer terminado. Saliendo de Pygame.")
        pygame.quit()

    def _renderizar_dashboard_replay(self):
        """Renderiza dashboard simplificado para replay viewer"""
        # KEEP: Simplified dashboard for replay
        font = pygame.font.Font(None, 24)

        # Panel derecho para información de replay
        panel_x = self.window_size[0]
        panel_width = 380

        # Fondo del panel
        pygame.draw.rect(self.pantalla, (50, 50, 50),
                        (panel_x, 0, panel_width, self.window_size[1]))

        # Información del replay
        textos = [
            "REPLAY VIEWER",
            f"Tiempo: {self.playback_time:.1f}s",
            f"Velocidad: {self.factor_aceleracion:.1f}x",
            f"Buffer: {len(self.event_buffer)} eventos",
            "",
            "Controles:",
            "+/- : Cambiar velocidad",
            "SPACE : Pausa",
            "ESC : Salir"
        ]

        for i, texto in enumerate(textos):
            color = (255, 255, 255) if i == 0 else (200, 200, 200)
            superficie_texto = font.render(texto, True, color)
            self.pantalla.blit(superficie_texto, (panel_x + 10, 20 + i * 30))


    def _renderizar_replay_frame(self, operarios_visual, eventos_recibidos, eventos_procesados):
        """Renderiza un frame del motor de replay"""
        # KEEP: Core frame rendering - Needed for replay visualization

        # Limpiar pantalla
        self.pantalla.fill((240, 240, 240))  # Fondo gris claro

        # Renderizar mapa TMX si está disponible
        if hasattr(self, 'layout_manager') and self.layout_manager:
            # Renderizar en superficie virtual primero
            self.virtual_surface.fill((25, 25, 25))
            self.renderer.renderizar_mapa_tmx(self.virtual_surface, self.layout_manager.tmx_data)

            # Renderizar agentes en superficie virtual
            self._renderizar_agentes_replay(self.virtual_surface, operarios_visual)

            # Escalar a pantalla principal
            scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
            self.pantalla.blit(scaled_surface, (0, 0))
        else:
            # Renderizado simple sin mapa
            self._renderizar_agentes_replay(self.pantalla, operarios_visual)

        # HUD de información del motor de replay
        self._renderizar_hud_replay(eventos_recibidos, eventos_procesados, len(operarios_visual))

        # Actualizar pantalla
        pygame.display.flip()

    def _renderizar_agentes_replay(self, surface, operarios_visual):
        """Renderiza los agentes en la superficie especificada"""
        # KEEP: Agent rendering - Core for replay visualization

        for agent_id, data in operarios_visual.items():
            x = data.get('x', 100)
            y = data.get('y', 100)
            tipo = data.get('tipo', 'terrestre')

            # Color según tipo
            color = (0, 150, 255) if tipo == 'montacargas' else (255, 100, 0)  # Azul o naranja

            # Dibujar agente como círculo
            pygame.draw.circle(surface, color, (int(x), int(y)), 8)

            # Dibujar ID del agente
            font = pygame.font.Font(None, 16)
            texto = font.render(agent_id[-1], True, (255, 255, 255))  # Solo último carácter
            surface.blit(texto, (int(x) - 5, int(y) - 20))

    def _renderizar_hud_replay(self, eventos_recibidos, eventos_procesados, agentes_activos):
        """Renderiza el HUD del motor de replay"""
        # KEEP: HUD rendering - Useful for replay debugging

        font = pygame.font.Font(None, 24)
        textos = [
            f"REPLAY VIEWER ENGINE",
            f"Tiempo de reproducción: {self.playback_time:.1f}s",
            f"Velocidad: {self.factor_aceleracion:.1f}x",
            f"Buffer: {len(self.event_buffer)} eventos",
            f"Recibidos: {eventos_recibidos} | Procesados: {eventos_procesados}",
            f"Agentes activos: {agentes_activos}",
            f"",
            f"Controles: +/- (velocidad), ESC (salir)"
        ]

        for i, texto in enumerate(textos):
            superficie_texto = font.render(texto, True, (50, 50, 50))
            self.pantalla.blit(superficie_texto, (10, 10 + i * 25))


    def _manejar_evento(self, evento):
        """Maneja los eventos de pygame"""
        # KEEP: Most of event handling - Core for user interaction

        if evento.type == pygame.QUIT:
            return False

        elif evento.type == pygame.VIDEORESIZE:
            self.pantalla = pygame.display.set_mode((evento.w, evento.h), pygame.RESIZABLE)
            self.renderer.actualizar_escala(evento.w, evento.h)

        elif evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                return False
            elif evento.key == pygame.K_SPACE:
                pausado = toggle_pausa()
                print(f"Replay {'pausado' if pausado else 'reanudado'}")


            elif evento.key == pygame.K_EQUALS or evento.key == pygame.K_KP_PLUS:  # Tecla + o +
                # KEEP: Velocidad control - Core for replay playback speed
                factores = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
                if self.factor_aceleracion in factores and factores.index(self.factor_aceleracion) < len(factores) - 1:
                    self.factor_aceleracion = factores[factores.index(self.factor_aceleracion) + 1]
                else:
                    self.factor_aceleracion = factores[-1]
                print(f"[REPLAY] Velocidad de reproducción: {self.factor_aceleracion:.1f}x")

            elif evento.key == pygame.K_MINUS or evento.key == pygame.K_KP_MINUS:  # Tecla - o -
                # KEEP: Velocidad control - Core for replay playback speed
                factores = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
                if self.factor_aceleracion in factores and factores.index(self.factor_aceleracion) > 0:
                    self.factor_aceleracion = factores[factores.index(self.factor_aceleracion) - 1]
                else:
                    self.factor_aceleracion = factores[0]
                print(f"[REPLAY] Velocidad de reproducción: {self.factor_aceleracion:.1f}x")

            elif evento.key == pygame.K_o:  # Tecla O para Dashboard de Órdenes
                print("[REPLAY-VIEWER] Tecla 'O' detectada.")
                # KEEP: Dashboard toggle - Useful for replay analysis
                self.toggle_order_dashboard()

            # ELIMINATED: Funciones de diagnóstico - Not needed for replay viewer

        return True


    def toggle_order_dashboard(self):
        """Toggle del dashboard de órdenes (PyQt6)"""
        # KEEP: Dashboard functionality - Useful for replay analysis

        if self.order_dashboard_process and self.order_dashboard_process.is_alive():
            print("[DASHBOARD] Cerrando dashboard de órdenes...")
            self.order_dashboard_process.terminate()
            self.order_dashboard_process = None
            print("[DASHBOARD] Dashboard cerrado")
        else:
            print("[DASHBOARD] Abriendo dashboard de órdenes...")
            # ELIMINATED: Complex simulation data passing - Simplified for replay
            self._iniciar_dashboard_ordenes_replay()

    def _iniciar_dashboard_ordenes_replay(self):
        """Inicia dashboard simplificado para replay viewer"""
        # KEEP: Simplified dashboard startup

        try:
            # ELIMINATED: Complex multiprocessing setup - Simplified
            print("[DASHBOARD] Dashboard para replay viewer iniciado")
        except Exception as e:
            print(f"[DASHBOARD] Error iniciando dashboard: {e}")

    # ELIMINATED: All diagnostic methods - Not needed for replay viewer

    # ELIMINATED: def _diagnosticar_route_calculator(self) - No routing needed for replay

    # ELIMINATED: def _inicializar_operarios_en_estado_visual(self) - No simulation agents needed

    # ELIMINATED: def ejecutar(self) - Main execution simplified to replay-only

    def run(self, jsonl_file_path):
        """Metodo principal - Ejecuta el motor de replay completo desde archivo .jsonl"""
        # MOVED: Complete replay execution logic from run_replay_viewer.py

        print(f"[REPLAY] Cargando archivo: {jsonl_file_path}")

        # Cargar todos los eventos del archivo .jsonl en memoria
        eventos = []
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
                                # BUGFIX: Leer total fijo de WorkOrders del evento SIMULATION_START
                                total_work_orders_fijo = event.get('total_work_orders', None)
                                if total_work_orders_fijo is not None:
                                    print(f"[REPLAY] Encontrado total_work_orders fijo: {total_work_orders_fijo}")
                                else:
                                    print(f"[REPLAY] WARNING: total_work_orders no encontrado en SIMULATION_START (replay antiguo)")
                                print(f"[REPLAY] Encontrado SIMULATION_START con {len(initial_work_orders)} WorkOrders iniciales")
                            else:
                                # BUGFIX: Incluir TODOS los eventos incluyendo SIMULATION_END
                                eventos.append(event)
                                if event.get('event_type') == 'SIMULATION_END':
                                    print(f"[BUGFIX] SIMULATION_END incluido en eventos: {event}")

                        except json.JSONDecodeError as e:
                            print(f"[REPLAY] Error parseando linea: {e}")
                            continue

            print(f"[REPLAY] {len(eventos)} eventos cargados exitosamente")

        except Exception as e:
            print(f"[REPLAY ERROR] No se pudo cargar archivo de replay: {e}")
            return 1

        # Inicializar pygame
        pygame.init()

        # Crear ventana con espacio para dashboard
        warehouse_width = 960
        dashboard_width = 380
        window_width = warehouse_width + dashboard_width
        window_height = 1000
        window_size = (window_width, window_height)
        self.pantalla = pygame.display.set_mode(window_size)
        pygame.display.set_caption("Simulador de Almacen - Modo Replay")
        self.reloj = pygame.time.Clock()

        # REFACTOR V11: IPC Manager for PyQt6 Dashboard - STUB for smoke test
        # TODO: Implement IPC manager using communication subsystem
        class IPCManagerStub:
            """Stub class for IPC manager during smoke test"""
            def start_ui_process(self): return False
            def stop_ui_process(self): pass
            def is_ui_process_alive(self): return False
            def send_simulation_metadata(self, metadata): pass
            def send_batch_work_orders(self, orders): return 0
            def send_work_order_delta(self, data): pass
            def cleanup(self): pass

        ipc_manager = IPCManagerStub()
        dashboard_process_started = False
        print("[IPC-MANAGER] STUB: Dashboard deshabilitado para prueba de humo")

        # Cargar configuracion desde el evento SIMULATION_START
        configuracion = simulation_start_event.get('config', {}) if simulation_start_event else {}

        # Override internal config with replay config
        if configuracion:
            print("[REPLAY] Usando configuracion desde archivo de replay")
            self.configuracion = configuracion
        # REFACTOR: Configuration now loaded in __init__ via ConfigurationManager
        elif not self.configuracion:
            print("Error: Configuracion no disponible")
            return 1

        # Inicializar arquitectura TMX basica (necesaria para renderizado)
        from subsystems.simulation.layout_manager import LayoutManager
        from subsystems.visualization.renderer import RendererOriginal
        from subsystems.visualization.state import inicializar_estado, estado_visual

        # Cargar TMX - REFACTOR V11: Path relative to project root
        project_root = os.path.join(os.path.dirname(__file__), "..", "..")
        tmx_file = os.path.join(project_root, "layouts", "WH1.tmx")
        self.layout_manager = LayoutManager(tmx_file)

        # Crear superficies
        virtual_surface = pygame.Surface((warehouse_width, warehouse_width))  # Superficie virtual para el mapa
        self.renderer = RendererOriginal(virtual_surface)
        self.virtual_surface = virtual_surface
        self.window_size = window_size

        # Inicializar estado visual basico
        inicializar_estado(None, None, configuracion, self.layout_manager)

        # FEATURE: Motor de Estado Continuo del Dashboard de Replay
        dashboard_wos_state = {}  # Estado persistente de WorkOrders para el dashboard
        print("[DASHBOARD-STATE] Motor de estado continuo inicializado")

        # Configurar estado inicial con WorkOrders si estan disponibles
        if initial_work_orders:
            for wo in initial_work_orders:
                estado_visual["work_orders"][wo['id']] = wo.copy()
                # FEATURE: Poblar el estado continuo del dashboard
                dashboard_wos_state[wo['id']] = wo.copy()
            print(f"[REPLAY] {len(initial_work_orders)} WorkOrders cargadas en estado inicial")
            print(f"[DASHBOARD-STATE] {len(dashboard_wos_state)} WorkOrders pobladas en estado continuo")

            print("=========================================\n")

        # Procesar primer evento para obtener posiciones iniciales de agentes
        agentes_iniciales = {}
        for evento in eventos[:10]:  # Solo mirar los primeros eventos
            if evento.get('type') == 'estado_agente':
                agent_id = evento.get('agent_id')
                data = evento.get('data', {})
                if agent_id and 'position' in data:
                    agentes_iniciales[agent_id] = data

        # Configurar agentes en estado visual
        for agent_id, data in agentes_iniciales.items():
            estado_visual["operarios"][agent_id] = data.copy()

        print(f"[REPLAY] {len(agentes_iniciales)} agentes encontrados en estado inicial")
        print("[REPLAY] Iniciando bucle de visualizacion...")

        # Inicializar motor de playback
        playback_time = 0.0
        replay_speed = 1.0
        velocidades_permitidas = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
        processed_event_indices = set()  # Trackear eventos ya procesados
        replay_finalizado = False  # BUGFIX: Control de finalizacion del replay

        print(f"[REPLAY] Motor de playback inicializado - {len(eventos)} eventos total")
        print(f"[REPLAY] Estado inicial: replay_finalizado = {replay_finalizado}")

        # REFACTOR V8.0: Control de dashboard PyQt6
        dashboard_visible = False

        def start_pyqt_dashboard():
            """Iniciar dashboard PyQt6 en proceso separado"""
            nonlocal dashboard_process_started
            if not dashboard_process_started:
                success = ipc_manager.start_ui_process()
                if success:
                    dashboard_process_started = True
                    print("[PYQT6-DASHBOARD] Proceso iniciado exitosamente")

                    # Enviar metadata inicial
                    metadata = {
                        'type': 'simulation_start',
                        'config': configuracion,
                        'total_work_orders': len(initial_work_orders) if initial_work_orders else 0
                    }
                    ipc_manager.send_simulation_metadata(metadata)

                    # Enviar WorkOrders iniciales
                    if initial_work_orders:
                        ipc_manager.send_batch_work_orders(initial_work_orders)
                        print(f"[PYQT6-DASHBOARD] {len(initial_work_orders)} WorkOrders iniciales enviadas")
                else:
                    print("[PYQT6-DASHBOARD] Error iniciando proceso")

        # Placeholder para inicio del dashboard PyQt6 (se inicia al presionar 'O')
        print("[PYQT6-DASHBOARD] Dashboard listo para iniciarse (presiona 'O')")

        # Bucle principal de replay con motor temporal
        corriendo = True
        replay_pausado = False  # Control de pausa sincronizada del replay
        while corriendo:
            time_delta = self.reloj.tick(30) / 1000.0

            # Manejar eventos de pygame
            for event in pygame.event.get():
                # REFACTOR V8.0: Eventos para proceso principal (sin pygame_gui)
                if event.type == pygame.QUIT:
                    corriendo = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        corriendo = False
                    elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                        # Aumentar velocidad al siguiente nivel
                        current_index = velocidades_permitidas.index(replay_speed) if replay_speed in velocidades_permitidas else 2
                        if current_index < len(velocidades_permitidas) - 1:
                            replay_speed = velocidades_permitidas[current_index + 1]
                            print(f"[REPLAY] Velocidad aumentada a {replay_speed:.2f}x")
                    elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                        # Disminuir velocidad al nivel anterior
                        current_index = velocidades_permitidas.index(replay_speed) if replay_speed in velocidades_permitidas else 2
                        if current_index > 0:
                            replay_speed = velocidades_permitidas[current_index - 1]
                            print(f"[REPLAY] Velocidad disminuida a {replay_speed:.2f}x")
                    elif event.key == pygame.K_SPACE:
                        # Toggle pausa sincronizada del replay
                        replay_pausado = not replay_pausado
                        print(f"[REPLAY] {'Pausado' if replay_pausado else 'Reanudado'}")
                    elif event.key == pygame.K_o:
                        # BUGFIX V8.0: Manejador PyQt6 Dashboard con gestion de procesos
                        if ipc_manager.is_ui_process_alive():
                            # Proceso activo - terminarlo
                            print("[PYQT6-DASHBOARD] Cerrando dashboard...")
                            ipc_manager.stop_ui_process()
                            dashboard_process_started = False
                            print("[PYQT6-DASHBOARD] Dashboard cerrado")
                        else:
                            # Proceso inactivo - iniciarlo
                            print("[PYQT6-DASHBOARD] Iniciando dashboard...")
                            success = ipc_manager.start_ui_process()
                            if success:
                                dashboard_process_started = True
                                print("[PYQT6-DASHBOARD] Dashboard iniciado exitosamente")

                                # Enviar metadata inicial de simulacion
                                metadata = {
                                    'type': 'simulation_start',
                                    'config': configuracion,
                                    'total_work_orders': len(initial_work_orders) if initial_work_orders else 0
                                }
                                ipc_manager.send_simulation_metadata(metadata)

                                # Enviar WorkOrders iniciales si existen
                                if initial_work_orders:
                                    sent_count = ipc_manager.send_batch_work_orders(initial_work_orders)
                                    print(f"[PYQT6-DASHBOARD] {sent_count} WorkOrders iniciales enviadas")
                            else:
                                print("[PYQT6-DASHBOARD] Error iniciando dashboard")
                # REMOVIDO: pygame_gui.UI_BUTTON_PRESSED - No necesario en PyQt6

            # REFACTOR ARQUITECTONICO: Procesar eventos ANTES de avanzar el tiempo
            # Obtener lote de eventos para el tiempo actual (solo si no esta pausado)
            eventos_a_procesar = []
            if not replay_pausado:
                for i, evento in enumerate(eventos):
                    if i not in processed_event_indices:
                        event_timestamp = evento.get('timestamp', 0.0)
                        # BUGFIX: Manejar timestamps None
                        if event_timestamp is None:
                            event_timestamp = 0.0
                        if event_timestamp <= playback_time:
                            eventos_a_procesar.append((i, evento))

            # Actualizar estado de agentes con eventos procesados
            for event_index, evento in eventos_a_procesar:
                processed_event_indices.add(event_index)

                # BUGFIX: Detectar evento SIMULATION_END y pausar replay
                if evento.get('event_type') == 'SIMULATION_END':
                    replay_finalizado = True
                    print(f"[BUGFIX] SIMULATION_END detectado en playback_time={playback_time:.3f}s")
                    print(f"[BUGFIX] Replay pausado - replay_finalizado = {replay_finalizado}")

                if evento.get('type') == 'estado_agente':
                    agent_id = evento.get('agent_id')
                    event_data = evento.get('data', {})
                    event_timestamp = evento.get('timestamp', 0.0)

                    real_time = time.time()

                    if agent_id and event_data:
                        # Inicializar agente si no existe
                        if agent_id not in estado_visual["operarios"]:
                            estado_visual["operarios"][agent_id] = {}

                        # CRITICO: Usar .update() para fusionar datos sin perder claves existentes
                        estado_visual["operarios"][agent_id].update(event_data)

                        # BUGFIX 2025-10-05: Recalcular coordenadas pixel desde grid position
                        # El JSONL contiene coordenadas de esquina (grid_x * 32) en lugar de centro
                        # Usamos grid_to_pixel() para calcular coordenadas centradas correctas
                        if 'position' in event_data:
                            position = event_data['position']
                            if isinstance(position, (list, tuple)) and len(position) == 2:
                                grid_x, grid_y = position[0], position[1]

                                # Recalcular coordenadas pixel centradas
                                if self.layout_manager:
                                    pixel_x, pixel_y = self.layout_manager.grid_to_pixel(grid_x, grid_y)

                                    # Sobrescribir coordenadas pixel incorrectas del JSONL
                                    estado_visual["operarios"][agent_id]['x'] = pixel_x
                                    estado_visual["operarios"][agent_id]['y'] = pixel_y
                                else:
                                    # Fallback si layout_manager no disponible (no deberia ocurrir)
                                    print(f"[REPLAY-WARNING] layout_manager no disponible para agent {agent_id}")

                        # BUGFIX: Extraer WorkOrders anidadas en tour_details
                        tour_details = event_data.get('tour_details', [])
                        if tour_details:
                            # Inicializar diccionario work_orders si no existe
                            if 'work_orders' not in estado_visual:
                                estado_visual['work_orders'] = {}

                            # Extraer cada WorkOrder de la lista tour_details
                            for work_order in tour_details:
                                wo_id = work_order.get('id')
                                if wo_id:
                                    estado_visual['work_orders'][wo_id] = work_order.copy()

                elif evento.get('type') == 'work_order_update':
                    # Procesar actualizacion de Work Order
                    work_order_data = evento.get('data', {})
                    work_order_id = work_order_data.get('id')
                    event_timestamp = evento.get('timestamp', 0.0)

                    real_time = time.time()
                    status = work_order_data.get('status', 'unknown')
                    # BUGFIX: Manejar timestamp None
                    if event_timestamp is None:
                        event_timestamp = 0.0

                    if work_order_id:
                        # Actualizar Work Order en estado visual
                        if 'work_orders' not in estado_visual:
                            estado_visual['work_orders'] = {}
                        estado_visual['work_orders'][work_order_id] = work_order_data.copy()

                        # FEATURE: Actualizar estado continuo del dashboard
                        dashboard_wos_state[work_order_id] = work_order_data.copy()
                        print(f"[DASHBOARD-STATE] WO {work_order_id} actualizada: status={status}")

            # REFACTOR ARQUITECTONICO: Avanzar tiempo DESPUES de procesar eventos
            # BUGFIX: Solo avanzar tiempo si el replay NO ha finalizado y NO esta pausado
            if not replay_finalizado and not replay_pausado:
                delta_time = self.reloj.get_time() / 1000.0  # Convertir ms a segundos
                playback_time += delta_time * replay_speed

            # Limpiar pantalla
            self.pantalla.fill((240, 240, 240))
            virtual_surface.fill((25, 25, 25))

            # Renderizar mapa TMX
            if hasattr(self.layout_manager, 'tmx_data') and self.layout_manager.tmx_data:
                self.renderer.renderizar_mapa_tmx(virtual_surface, self.layout_manager.tmx_data)

            # Renderizar agentes con posiciones actualizadas
            from subsystems.visualization.renderer import renderizar_agentes
            if estado_visual.get("operarios"):
                # CRITICO: Convertir diccionario a lista para renderizar_agentes
                operarios_a_renderizar = []
                for agent_id, agent_data in estado_visual["operarios"].items():
                    agente = agent_data.copy()
                    agente['id'] = agent_id  # Asegurar que el ID este presente
                    operarios_a_renderizar.append(agente)

                renderizar_agentes(virtual_surface, operarios_a_renderizar, self.layout_manager)

            # BUGFIX 2025-10-05: Escalar uniformemente para mantener proporcion 1:1
            # Calcula ratio uniforme usando el menor dimension disponible
            scale_ratio = min(warehouse_width / 960.0, window_height / 960.0)
            scaled_width = int(960 * scale_ratio)
            scaled_height = int(960 * scale_ratio)

            # Escalar superficie manteniendo proporcion de aspecto
            scaled_warehouse = pygame.transform.smoothscale(
                virtual_surface,
                (scaled_width, scaled_height)
            )

            # Centrar la superficie escalada en el area disponible
            offset_x = (warehouse_width - scaled_width) // 2
            offset_y = (window_height - scaled_height) // 2

            # Llenar fondo del area de warehouse (para bordes si hay)
            warehouse_rect = pygame.Rect(0, 0, warehouse_width, window_height)
            pygame.draw.rect(self.pantalla, (40, 40, 40), warehouse_rect)

            # Blit superficie escalada centrada
            self.pantalla.blit(scaled_warehouse, (offset_x, offset_y))

            # Renderizar Dashboard de Agentes
            from subsystems.visualization.renderer import renderizar_dashboard

            # Preparar metricas para el dashboard - DUAL COUNTERS
            # Contar WorkOrders completadas segun contrato de renderizar_dashboard
            work_orders = estado_visual.get('work_orders', {})
            workorders_completadas = sum(1 for wo in work_orders.values() if wo.get('status') == 'staged')

            # Contar tareas completadas procesando los eventos acumulados hasta playback_time
            tareas_completadas = 0
            for evento in eventos:
                # BUGFIX: Validacion defensiva contra timestamp None que causaba TypeError
                timestamp = evento.get('timestamp', 0)
                if timestamp is None:
                    timestamp = 0  # Fallback seguro

                if timestamp <= playback_time:
                    if evento.get('type') == 'task_completed' or evento.get('type') == 'operation_completed':
                        tareas_completadas += 1

            # BUGFIX: Usar total fijo de WorkOrders si esta disponible
            total_wos_a_usar = total_work_orders_fijo if total_work_orders_fijo is not None else len(work_orders)

            metricas = {
                'tiempo': playback_time,
                'workorders_completadas': workorders_completadas,  # KPI principal
                'tareas_completadas': tareas_completadas,  # Metrica granular
                'total_wos': total_wos_a_usar
            }

            # Preparar operarios para el dashboard (convertir a formato esperado)
            operarios_dashboard = []
            for agent_id, agent_data in estado_visual.get('operarios', {}).items():
                operario = agent_data.copy()
                operario['id'] = agent_id
                operarios_dashboard.append(operario)

            # Renderizar dashboard en el lado derecho
            renderizar_dashboard(self.pantalla, warehouse_width, metricas, operarios_dashboard)

            # Mostrar informacion de replay en la parte superior del almacen
            font = pygame.font.Font(None, 20)
            info_text = font.render(f"REPLAY: Tiempo {playback_time:.2f}s | Velocidad: {replay_speed:.2f}x | Eventos {len(processed_event_indices)}/{len(eventos)}", True, (255, 255, 255))
            self.pantalla.blit(info_text, (10, 10))

            # Mostrar informacion de controles y dashboard
            controls_text = font.render("CONTROLES: +/- velocidad | SPACE pausa | O dashboard | ESC salir", True, (255, 255, 255))
            self.pantalla.blit(controls_text, (10, 35))

            # REFACTOR V8.0: IPC communication con PyQt6 Dashboard
            if dashboard_process_started and ipc_manager and not replay_pausado:
                # Enviar actualizaciones de WorkOrders al dashboard PyQt6
                for wo_id, wo_data in dashboard_wos_state.items():
                    ipc_manager.send_work_order_delta(wo_data)

                # Verificar estado del proceso UI
                if not ipc_manager.is_ui_process_alive():
                    dashboard_process_started = False
                    print("[PYQT6-DASHBOARD] Proceso terminado inesperadamente")

            pygame.display.flip()

        # REFACTOR V8.0: Cleanup PyQt6 Dashboard
        if ipc_manager:
            print("[CLEANUP] Deteniendo dashboard PyQt6...")
            ipc_manager.cleanup()

        pygame.quit()
        print("[REPLAY] Modo replay terminado")
        return 0

    def limpiar_recursos(self):
        """Limpia recursos al cerrar"""
        # KEEP: Resource cleanup - Essential for proper shutdown

        if self.order_dashboard_process and self.order_dashboard_process.is_alive():
            print("[CLEANUP] Cerrando dashboard...")
            self.order_dashboard_process.terminate()

        pygame.quit()
        print("[CLEANUP] Recursos limpiados exitosamente")

