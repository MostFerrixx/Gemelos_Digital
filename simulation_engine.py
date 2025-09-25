# -*- coding: utf-8 -*-
"""
Simulation Engine - Motor puro de simulacion sin capacidades de replay.
Refactorizado desde run_simulator.py - Solo simulacion live (visual y headless).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

import pygame
import simpy
import json
import time
import subprocess
from datetime import datetime
import multiprocessing
from multiprocessing import Queue
# REFACTOR: Movido a main.py - no necesario en libreria
# import argparse
import logging


# ELIMINATED: Buffer de eventos para replay - No replay capabilities in pure simulation





# Importaciones de modulos propios
from config.settings import *
from config.colors import *
from simulation.warehouse import AlmacenMejorado
from simulation.operators_workorder import crear_operarios
from analytics_engine import AnalyticsEngine
from simulation.layout_manager import LayoutManager
from simulation.assignment_calculator import AssignmentCostCalculator
from simulation.data_manager import DataManager

from simulation.pathfinder import Pathfinder
from simulation.route_calculator import RouteCalculator
from visualization.state import inicializar_estado, actualizar_metricas_tiempo, toggle_pausa, toggle_dashboard, estado_visual, limpiar_estado, aumentar_velocidad, disminuir_velocidad, obtener_velocidad_simulacion
from visualization.original_renderer import RendererOriginal, renderizar_diagnostico_layout
from visualization.original_dashboard import DashboardOriginal
from utils.helpers import exportar_metricas, mostrar_metricas_consola
from config.settings import SUPPORTED_RESOLUTIONS, LOGICAL_WIDTH, LOGICAL_HEIGHT
# from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper  # Eliminado en limpieza
# ELIMINATED: from simulation_buffer import ReplayBuffer - No replay buffer needed for live simulation
# ELIMINATED: from core.replay_utils import agregar_evento_replay, volcar_replay_a_archivo - No replay utilities needed
from core.config_utils import get_default_config, mostrar_resumen_config

class SimulationEngine:
    """Motor puro de simulacion - Solo capacidades live (visual y headless)"""
    
    def __init__(self, headless_mode=False):
        self.configuracion = None
        self.almacen = None
        self.env = None
        self.pantalla = None
        self.renderer = None
        self.dashboard = None
        self.reloj = None
        self.corriendo = True
        self.headless_mode = headless_mode  # Nuevo: modo headless

        # ELIMINATED: ReplayBuffer instance - No replay capabilities needed for live simulation
        # ELIMINATED: self.replay_buffer = ReplayBuffer() - Pure simulation doesn't need replay buffer
        self.order_dashboard_process = None  # Proceso del dashboard de ordenes
        # REFACTOR: Infraestructura de multiproceso para SimPy Productor
        self.visual_event_queue = None       # Cola de eventos visuales
        self.simulation_process = None       # Proceso de simulacion SimPy
        self.dashboard_data_queue = None     # Cola para comunicacion con el dashboard
        # Nuevos componentes de la arquitectura TMX
        self.layout_manager = None
        self.pathfinder = None
        # Nuevos atributos para escalado dinamico
        self.window_size = (0, 0)
        self.virtual_surface = None
        # Lista de procesos de operarios para verificacion de finalizacion
        self.procesos_operarios = []
        # Bandera para evitar reportes repetidos
        self.simulacion_finalizada_reportada = False
        # NUEVO: Cache de estado anterior para delta updates del dashboard
        self.dashboard_last_state = {}
        
        # ELIMINATED: Motor de visualizacion tipo "replay" - No replay visualization needed
        # ELIMINATED: self.event_buffer = [] - No event buffer for replay playback
        # ELIMINATED: self.playback_time = 0.0 - No playback time control needed
        # ELIMINATED: self.factor_aceleracion = 1.0 - No replay speed control needed
        
    def inicializar_pygame(self):
        # REFACTOR: Pygame ya esta inicializado en crear_simulacion(), solo configurar ventana
        
        PANEL_WIDTH = 400
        # 1. Obtener la clave de resolucion seleccionada por el usuario
        resolution_key = self.configuracion.get('selected_resolution_key', "Pequena (800x800)")
        
        # 2. Buscar el tamano (ancho, alto) en nuestro diccionario
        self.window_size = SUPPORTED_RESOLUTIONS.get(resolution_key, (800, 800))

        print(f"[DISPLAY] Resolucion seleccionada por el usuario: '{resolution_key}' -> {self.window_size[0]}x{self.window_size[1]}")

        # 3. Hacemos la ventana principal mas ancha para acomodar el panel
        main_window_width = self.window_size[0] + PANEL_WIDTH
        main_window_height = self.window_size[1]
        self.pantalla = pygame.display.set_mode((main_window_width, main_window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Simulador de Almacen - Gemelo Digital")
        
        # 4. La superficie virtual mantiene el tamano logico del mapa
        self.virtual_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        print(f"Ventana creada: {main_window_width}x{main_window_height}. Panel UI: {PANEL_WIDTH}px.")
        
        self.reloj = pygame.time.Clock()
        self.renderer = RendererOriginal(self.virtual_surface)
        self.dashboard = DashboardOriginal()
    
    def cargar_configuracion(self):
        """Carga la configuracion desde config.json o usa defaults hardcodeados"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        
        try:
            # Intentar cargar config.json
            if os.path.exists(config_path):
                print(f"[CONFIG] Cargando configuracion desde: {config_path}")
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.configuracion = json.load(f)
                
                # Sanitizar assignment_rules: convertir claves str a int
                if 'assignment_rules' in self.configuracion and self.configuracion['assignment_rules']:
                    sanitized_rules = {}
                    for agent_type, rules in self.configuracion['assignment_rules'].items():
                        sanitized_rules[agent_type] = {int(k): v for k, v in rules.items()}
                    self.configuracion['assignment_rules'] = sanitized_rules
                
                print("[CONFIG] Configuracion cargada exitosamente desde archivo JSON")
            else:
                print("[CONFIG] config.json no encontrado, usando configuracion por defecto")
                self.configuracion = get_default_config()
                print("[CONFIG] Configuracion por defecto cargada")
            
            # Nota: cost_calculator se creara despues de inicializar data_manager
            
            # Mostrar resumen de configuracion cargada
            mostrar_resumen_config(self.configuracion)
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"[CONFIG ERROR] Error al parsear config.json: {e}")
            print("[CONFIG] Usando configuracion por defecto como fallback")
            self.configuracion = get_default_config()
            return True
            
        except Exception as e:
            print(f"[CONFIG ERROR] Error inesperado cargando configuracion: {e}")
            print("[CONFIG] Usando configuracion por defecto como fallback")
            self.configuracion = get_default_config()
            return True
    
    
    
    def crear_simulacion(self):
        """Crea una nueva simulacion"""
        if not self.configuracion:
            print("Error: No hay configuracion valida")
            return False
        
        # ARQUITECTURA TMX OBLIGATORIA - No hay fallback
        print("[SIMULADOR] Inicializando arquitectura TMX (OBLIGATORIO)...")
        
        # REFACTOR: Inicializacion condicional de pygame segun el modo de ejecucion
        import os  # Mover import al nivel superior
        if self.headless_mode:
            # En modo headless, usar driver dummy para evitar ventanas
            os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Usar driver dummy sin ventanas
            pygame.init()
            # Crear superficie dummy minima para TMX sin mostrar ventana
            pygame.display.set_mode((1, 1), pygame.NOFRAME)
        else:
            # En modo visual, NO inicializar pygame aqui - ya esta inicializado en proceso principal
            # Solo configurar el entorno para TMX
            if not pygame.get_init():
                pygame.init()
                pygame.display.set_mode((100, 100))  # Ventana temporal para TMX
        
        # 1. Inicializar LayoutManager con archivo TMX por defecto (OBLIGATORIO)
        tmx_file = os.path.join(os.path.dirname(__file__), "layouts", "WH1.tmx")
        print(f"[TMX] Cargando layout: {tmx_file}")
        
        try:
            self.layout_manager = LayoutManager(tmx_file)
        except Exception as e:
            print(f"[FATAL ERROR] No se pudo cargar archivo TMX: {e}")
            print("[FATAL ERROR] El simulador requiere un archivo TMX valido para funcionar.")
            print("[FATAL ERROR] Sistema legacy eliminado - sin fallback disponible.")
            raise SystemExit(f"Error cargando TMX: {e}")
        
        # 2. Inicializar Pathfinder con collision_matrix del LayoutManager (OBLIGATORIO)
        print("[TMX] Inicializando sistema de pathfinding...")
        try:
            self.pathfinder = Pathfinder(self.layout_manager.collision_matrix)
            # Crear RouteCalculator despues del pathfinder
            self.route_calculator = RouteCalculator(self.pathfinder)
        except Exception as e:
            print(f"[FATAL ERROR] No se pudo inicializar pathfinder: {e}")
            raise SystemExit(f"Error en pathfinder: {e}")
        
        self.env = simpy.Environment()
        
        # El LayoutManager y Pathfinder son OBLIGATORIOS
        if not self.layout_manager or not self.pathfinder:
            raise SystemExit("[FATAL ERROR] LayoutManager y Pathfinder son obligatorios")
        
        # Crear DataManager para el plan maestro
        layout_file = self.configuracion.get('layout_file', '')
        sequence_file = self.configuracion.get('sequence_file', '')
        self.data_manager = DataManager(layout_file, sequence_file)
        
        # Crear el calculador de costos despues de inicializar data_manager
        self.cost_calculator = AssignmentCostCalculator(self.data_manager)
        
        print(f"[TMX] Arquitectura TMX inicializada exitosamente:")
        print(f"  - Dimensiones: {self.layout_manager.grid_width}x{self.layout_manager.grid_height}")
        print(f"  - Puntos de picking: {len(self.layout_manager.picking_points)}")
        print(f"  - OutboundStaging areas: {len(self.data_manager.outbound_staging_locations)}")
        
        self.almacen = AlmacenMejorado(
            self.env,
            self.configuracion,
            layout_manager=self.layout_manager,  # OBLIGATORIO
            pathfinder=self.pathfinder,          # OBLIGATORIO
            data_manager=self.data_manager,      # NUEVO V2.6
            cost_calculator=self.cost_calculator, # NUEVO V2.6
            simulador=self  # REFACTOR: Pasar referencia del simulador
        )
        
        inicializar_estado(self.almacen, self.env, self.configuracion, layout_manager=self.layout_manager)
        
        # Diagnostico del RouteCalculator
        self._diagnosticar_route_calculator()
        
        self.procesos_operarios, self.operarios = crear_operarios(
            self.env,
            self.almacen,
            self.configuracion,
            simulador=self,
            pathfinder=self.pathfinder,  # OBLIGATORIO
            layout_manager=self.layout_manager  # OBLIGATORIO
        )
        
        # INICIALIZAR ESTADO VISUAL DE AGENTES REALES
        self._inicializar_operarios_en_estado_visual(self.operarios)
        
        self.env.process(self._proceso_actualizacion_metricas())
        
        # Inicializar el almacen y crear ordenes
        self.almacen._crear_catalogo_y_stock()
        self.almacen._generar_flujo_ordenes()
        
        # Iniciar proceso del dispatcher V2.6 (CORREGIDO)
        if hasattr(self.almacen, 'dispatcher') and hasattr(self.almacen.dispatcher, 'dispatcher_process'):
            print("[SIMULADOR] Iniciando el proceso del Dispatcher V2.6...")
            self.env.process(self.almacen.dispatcher.dispatcher_process(self.operarios))
        else:
            print("[ERROR] No se pudo encontrar el proceso de dispatcher V2.6 para iniciar.")
        
        print(f"Simulacion V2.6 creada:")
        print(f"  - {len(self.procesos_operarios)} operarios")
        print(f"  - {len(self.almacen.dispatcher.lista_maestra_work_orders)} WorkOrders en lista maestra")
        print(f"  - {self.almacen.total_ordenes} ordenes generadas")
        print(f"  - Master Plan: {len(self.data_manager.puntos_de_picking_ordenados)} puntos de picking")
        if self.layout_manager:
            print(f"  - Layout TMX: ACTIVO ({tmx_file})")
        else:
            print(f"  - Layout TMX: DESACTIVADO (usando legacy)")
        
        print("--- Verificacion de Dimensiones del Layout ---")
        print(f"Ancho en Grilla: {self.layout_manager.grid_width}, Ancho de Tile: {self.layout_manager.tile_width}")
        print(f"Alto en Grilla: {self.layout_manager.grid_height}, Alto de Tile: {self.layout_manager.tile_height}")
        print("------------------------------------------")
        return True
    
    def _proceso_actualizacion_metricas(self):
        """Proceso de actualizacion de metricas"""
        # AUDIT: Importar logging para el proceso de metricas
        import logging
        logger = logging.getLogger(__name__)
        
        # AUDIT: Log de inicio del proceso de metricas (modo headless)
        logger.info("Iniciando proceso de metricas de dashboard...")
        
        while not self.almacen.simulacion_ha_terminado():
            yield self.almacen.adelantar_tiempo(5.0)  # INTERVALO_ACTUALIZACION_METRICAS
            actualizar_metricas_tiempo(estado_visual["operarios"])
        
        # BUGFIX: Log INFO despues de que el bucle termine
        logger.info("Proceso de metricas de dashboard finalizado: la simulacion ha terminado.")
    
    def ejecutar_bucle_principal(self):
        """Bucle principal completo con simulacion y renderizado de agentes."""
        from visualization.original_renderer import renderizar_agentes, renderizar_dashboard
        from visualization.state import estado_visual, obtener_velocidad_simulacion
        
        self.corriendo = True
        while self.corriendo:
            # 1. Manejar eventos (siempre)
            for event in pygame.event.get():
                if not self._manejar_evento(event):
                    self.corriendo = False

            # 2. Logica de Simulacion (SOLO si no ha finalizado)
            if not self.simulacion_finalizada_reportada:
                if not estado_visual["pausa"]:
                    if self._simulacion_activa():
                        try:
                            # REFACTOR V5.3.1: Procesar el siguiente evento disponible sin forzar tiempo
                            self.env.step()
                        except simpy.core.EmptySchedule:
                            # Cuando no hay mas eventos programados
                            pass
                        except Exception as e:
                            print(f"Error en simulacion: {e}")
                            # Continuar sin detener el bucle
                        
                        # Dashboard updates SOLO durante simulacion activa
                        self._actualizar_dashboard_ordenes()
                    else: # Si la simulacion ha terminado
                        print("[SIMULADOR] Condicion de finalizacion cumplida: No hay tareas pendientes y todos los agentes estan ociosos.")
                        print("Simulacion completada y finalizada logicamente.")
                        # La funcion de reporte ahora solo se llama UNA VEZ
                        self._simulacion_completada() 
                        
                        # Dashboard final update UNA VEZ
                        self._actualizar_dashboard_ordenes()
                        
                        # Enviar comando de finalizacion al Dashboard de Ordenes
                        if self.order_dashboard_process and self.order_dashboard_process.is_alive():
                            print("[PIPELINE] Enviando comando de hibernacion al Dashboard de Ordenes...")
                            try:
                                self.dashboard_data_queue.put('__SIMULATION_ENDED__')
                            except Exception as e:
                                print(f"[ERROR] No se pudo enviar el comando de hibernacion al dashboard: {e}")
                        
                        # Marcar como finalizada para evitar repeticion
                        self.simulacion_finalizada_reportada = True

            # 3. Limpiar la pantalla principal
            self.pantalla.fill((240, 240, 240))  # Fondo gris claro

            # 4. Dibujar el mundo de simulacion en la superficie virtual
            self.virtual_surface.fill((25, 25, 25))
            if hasattr(self, 'layout_manager') and self.layout_manager:
                self.renderer.renderizar_mapa_tmx(self.virtual_surface, self.layout_manager.tmx_data)
                from visualization.original_renderer import renderizar_tareas_pendientes
                # Obtener lista de tareas pendientes del dispatcher
                tareas_pendientes = self.almacen.dispatcher.lista_maestra_work_orders if (self.almacen and self.almacen.dispatcher) else []
                renderizar_tareas_pendientes(self.virtual_surface, tareas_pendientes, self.layout_manager)
            # Obtener lista de agentes para renderizar desde estado visual
            from visualization.state import estado_visual
            agentes_para_renderizar = list(estado_visual.get('operarios', {}).values())
            renderizar_agentes(self.virtual_surface, agentes_para_renderizar, self.layout_manager)

            # 5. Escalar la superficie virtual al area de simulacion en la pantalla
            scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
            self.pantalla.blit(scaled_surface, (0, 0))  # Dibujar el mundo a la izquierda

            # 6. Dibujar el dashboard directamente en la pantalla, en el panel derecho
            metricas = {
                'tiempo': self.env.now,
                'workorders_completadas': self.almacen.workorders_completadas_count,
                'tareas_completadas': self.almacen.tareas_completadas_count,
                'total_wos': self.almacen.dispatcher.work_orders_total_inicial
            }
            renderizar_dashboard(self.pantalla, self.window_size[0], metricas, estado_visual["operarios"])

            # 7. La verificacion de finalizacion ahora se maneja en el paso 2

            # 8. Actualizar la pantalla
            pygame.display.flip()
            self.reloj.tick(30)
            
        print("Simulacion terminada. Saliendo de Pygame.")
        pygame.quit()
    
    def _ejecutar_bucle_headless(self):
        """Bucle de ejecucion headless para maxima velocidad"""
        print("="*60)
        print("MODO HEADLESS ACTIVADO - Ejecutando en modo maxima velocidad")
        print("="*60)
        print("Ejecutando en modo Headless...")
        
        try:
            # BUGFIX: En lugar de env.run() indefinido, ejecutar hasta que la simulacion termine
            # Ejecutar eventos SimPy hasta que todas las WorkOrders esten completadas
            step_counter = 0
            while not self.almacen.simulacion_ha_terminado():
                # Avanzar la simulacion en pequenos pasos
                try:
                    # Usar un timeout pequeno para permitir verificar la condicion de terminacion
                    self.env.run(until=self.env.now + 1.0)
                    
                    step_counter += 1
                        
                except simpy.core.EmptySchedule:
                    # No hay mas eventos programados, pero verificar si la simulacion realmente termino
                    if self.almacen.simulacion_ha_terminado():
                        break
                    else:
                        # Si no termino pero no hay eventos, algo esta mal
                        print("Advertencia: No hay eventos programados pero la simulacion no ha terminado")
                        break
            
            print("Simulacion Headless completada.")
            
            # REFACTOR: Buffer ahora manejado por self.replay_buffer
            
            # Llamar a analiticas al finalizar, SIN pasar buffer especifico
            self._simulacion_completada_con_buffer(None)
            
        except KeyboardInterrupt:
            print("\nInterrupcion del usuario en modo headless. Saliendo...")
        except Exception as e:
            print(f"Error en modo headless: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("Modo headless finalizado.")
    
    # ELIMINATED: def _ejecutar_bucle_consumidor(self): - Complete 206-line replay/consumer method removed
    def _ELIMINATED_ejecutar_bucle_consumidor(self):
        """
        BUGFIX PASO 1: Motor de playback_time para restaurar control de velocidad
        
        Este bucle implementa un reloj de reproduccion sincronizado que:
        1. Lee eventos del productor y los almacena con timestamps
        2. Avanza el playback_time segun factor_aceleracion (teclas +/-)
        3. Procesa eventos del buffer solo cuando su timestamp <= playback_time
        """
        print("[CONSUMIDOR-PLAYBACK] Iniciando bucle con motor de playback_time sincronizado...")
        import queue
        import time
        from visualization.original_renderer import renderizar_agentes, renderizar_dashboard, renderizar_tareas_pendientes
        from visualization.state import estado_visual
        
        # Estado de visualizacion
        simulacion_activa = True
        self.metricas_actuales = {}  # Estado de metricas del dashboard
        
        eventos_procesados_total = 0
        ultimo_reporte_tiempo = time.time()
        
        datos_verificados = False
        
        # Resetear el reloj de reproduccion
        self.playback_time = 0.0
        
        for wo_id, wo_data in estado_visual.get('work_orders', {}).items():
            print(f"  WO {wo_id}: status={wo_data.get('status', 'unknown')}")
        print(f"Operarios en estado_visual: {len(estado_visual.get('operarios', {}))}")
        for op_id, op_data in estado_visual.get('operarios', {}).items():
            print(f"  Operario {op_id}: status={op_data.get('status', 'unknown')}, accion={op_data.get('accion', 'unknown')}")
        print(f"Playback time: {self.playback_time}")
        print(f"Buffer de eventos: {len(self.event_buffer)} eventos")
        if self.event_buffer:
            print(f"  Primer evento: timestamp={self.event_buffer[0].get('timestamp', 'unknown')}, tipo={self.event_buffer[0].get('type', 'unknown')}")
        print("=========================================\n")
        
        self.corriendo = True
        while self.corriendo and simulacion_activa:
            # INSTRUMENTACION: Registro del tiempo de inicio del frame
            frame_start_time = time.time()
            # 1. AVANZAR RELOJ DE REPRODUCCION (CONTROLADO POR FACTOR_ACELERACION)
            delta_time = self.reloj.tick(60) / 1000.0  # Delta en segundos (60 FPS base)
            self.playback_time += delta_time * self.factor_aceleracion
            
            # 2. Manejar eventos de usuario (Pygame)
            for event in pygame.event.get():
                if not self._manejar_evento(event):
                    self.corriendo = False
            
            # 3. LLENAR BUFFER: Recibir todos los eventos disponibles del productor
            eventos_recibidos = 0
            
            
            try:
                while True:  # Drenar la cola completamente
                    try:
                        mensaje = self.visual_event_queue.get_nowait()
                        eventos_recibidos += 1
                        
                        # Asignar timestamp del productor, o tiempo actual si no tiene
                        if 'timestamp' not in mensaje or mensaje['timestamp'] is None:
                            # Los eventos sin timestamp se procesan inmediatamente
                            mensaje['timestamp'] = self.playback_time - 0.001
                        
                        # Agregar evento al buffer ordenado por timestamp
                        self.event_buffer.append(mensaje)
                        
                    except queue.Empty:
                        break
                
                    
            except Exception as e:
                print(f"[ERROR-CONSUMIDOR] Error llenando buffer: {e}")
            
            # Ordenar buffer por timestamp para procesamiento cronologico
            self.event_buffer.sort(key=lambda x: x.get('timestamp', 0))
            
            # 4. PROCESAMIENTO DE BUFFER SINCRONIZADO (CAMBIO PRINCIPAL)
            eventos_procesados = 0
            eventos_procesados_este_frame = 0
            
            while self.event_buffer and self.event_buffer[0]['timestamp'] <= self.playback_time:
                # Sacar el primer evento del buffer
                mensaje = self.event_buffer.pop(0)
                eventos_procesados += 1
                eventos_procesados_este_frame += 1
                eventos_procesados_total += 1
                
                # Procesar evento segun su tipo
                if mensaje['type'] == 'estado_agente':
                    agent_id = mensaje['agent_id']
                    data = mensaje['data']
                    
                    # Actualizar estado_visual global directamente
                    if agent_id not in estado_visual["operarios"]:
                        estado_visual["operarios"][agent_id] = {
                            'x': 100, 'y': 100, 'tipo': 'terrestre',
                            'accion': 'Iniciando', 'status': 'idle',
                            'tareas_completadas': 0, 'direccion_x': 0, 'direccion_y': 0
                        }
                    estado_visual["operarios"][agent_id].update(data)
                    
                    # Convertir posicion de grilla a pixeles
                    if 'position' in data and hasattr(self, 'layout_manager') and self.layout_manager:
                        pos = data['position']
                        if isinstance(pos, tuple) and len(pos) == 2:
                            pixel_x, pixel_y = self.layout_manager.grid_to_pixel(pos[0], pos[1])
                            estado_visual["operarios"][agent_id]['x'] = pixel_x
                            estado_visual["operarios"][agent_id]['y'] = pixel_y
                
                elif mensaje['type'] == 'work_order_update':
                    # Procesar eventos de WorkOrder
                    work_order_data = mensaje['data']
                    work_order_id = work_order_data['id']
                    estado_visual["work_orders"][work_order_id] = work_order_data.copy()
                    print(f"[PLAYBACK-WO] WorkOrder {work_order_id}: {work_order_data['status']} @ {self.playback_time:.1f}s")
                
                elif mensaje['type'] == 'metricas_dashboard':
                    # Procesar metricas del dashboard
                    metricas = mensaje['data']
                    self.metricas_actuales = metricas
                    workorders_c = metricas.get('workorders_completadas', metricas.get('wos_completadas', 0))  # Backwards compatibility
                    tareas_c = metricas.get('tareas_completadas', 0)
                    print(f"[PLAYBACK-METRICAS] T={self.playback_time:.1f}s (sim:{metricas['tiempo']:.1f}s), WOs:{workorders_c}, Tareas:{tareas_c}, Factor:{self.factor_aceleracion:.1f}x")
                    
                    # Actualizar dashboard de ordenes si esta activo
                    self._actualizar_dashboard_ordenes()
                
                elif mensaje['type'] == 'simulation_completed':
                    print(f"[PLAYBACK] Simulacion completada a los {self.playback_time:.1f}s de reproduccion")
                    simulacion_activa = False
                    
                elif mensaje['type'] == 'simulation_error':
                    print(f"[PLAYBACK] Error: {mensaje['error']}")
                    simulacion_activa = False
            
            # 5. RENDERIZADO
            if self.corriendo:
                # Limpiar la pantalla principal
                self.pantalla.fill((240, 240, 240))

                # Dibujar el mundo de simulacion en la superficie virtual
                self.virtual_surface.fill((25, 25, 25))
                if hasattr(self, 'layout_manager') and self.layout_manager:
                    self.renderer.renderizar_mapa_tmx(self.virtual_surface, self.layout_manager.tmx_data)
                    # Obtener lista de tareas pendientes del dispatcher
                    tareas_pendientes = self.almacen.dispatcher.lista_maestra_work_orders if (self.almacen and self.almacen.dispatcher) else []
                    renderizar_tareas_pendientes(self.virtual_surface, tareas_pendientes, self.layout_manager)
                # Obtener lista de agentes para renderizar desde estado visual
                from visualization.state import estado_visual
                agentes_para_renderizar = list(estado_visual.get('operarios', {}).values())
                renderizar_agentes(self.virtual_surface, agentes_para_renderizar, self.layout_manager)

                # Escalar la superficie virtual al area de simulacion en la pantalla
                scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
                self.pantalla.blit(scaled_surface, (0, 0))

                # Renderizar dashboard
                renderizar_dashboard(self.pantalla, self.window_size[0], self.metricas_actuales, estado_visual["operarios"])

                # HUD de motor de playback mejorado
                self._renderizar_hud_playback_motor(eventos_recibidos, eventos_procesados_este_frame, len(self.event_buffer))

                # Actualizar pantalla
                pygame.display.flip()
            
            # DASHBOARD: Actualizar dashboard de ordenes en modo replay
            # ELIMINATED: self._actualizar_dashboard_ordenes_replay() - Replay dashboard update removed
            
            # INSTRUMENTACION: Logging de rendimiento de frames
            frame_end_time = time.time()
            frame_duration_ms = (frame_end_time - frame_start_time) * 1000
            if frame_duration_ms > 16:  # Un frame deberia durar ~16ms para 60 FPS
                print(f"[PERF-WARN] Frame largo detectado: {frame_duration_ms:.2f} ms. Eventos procesados: {eventos_procesados_este_frame}. Buffer: {len(self.event_buffer)}. Playback Time: {self.playback_time:.2f}s")
        
        # PIPELINE DE ANALITICAS AL FINALIZAR
        print("[CONSUMIDOR-FINAL] Finalizando simulacion e iniciando pipeline de analiticas...")
        
        # Esperar a que termine el proceso SimPy
        if self.simulation_process and self.simulation_process.is_alive():
            print("[CONSUMIDOR-FINAL] Esperando finalizacion del proceso SimPy...")
            self.simulation_process.join(timeout=10)
            if self.simulation_process.is_alive():
                print("[CONSUMIDOR-FINAL] Forzando terminacion del proceso SimPy...")
                self.simulation_process.terminate()
                self.simulation_process.join(timeout=5)
        
        # Cerrar Dashboard de Ordenes si esta abierto
        if self.order_dashboard_process and self.order_dashboard_process.is_alive():
            print("[CONSUMIDOR-FINAL] Cerrando Dashboard de Ordenes...")
            try:
                if self.dashboard_data_queue:
                    self.dashboard_data_queue.put_nowait('__EXIT_COMMAND__')
            except:
                pass
            self.order_dashboard_process.join(timeout=3)
            if self.order_dashboard_process.is_alive():
                self.order_dashboard_process.terminate()
        
        # Reportar finalizacion (las analiticas ya se procesaron en el productor)
        print("[CONSUMIDOR-FINAL] Pipeline de analiticas completado en el proceso productor.")
        print("[CONSUMIDOR-FINAL] Revise el directorio 'output/' para los archivos generados.")
        
        print("[CONSUMIDOR-FINAL] Bucle de consumidor terminado.")
        pygame.quit()
    
    def _crear_almacen_mock(self):
        """Crea un mock del almacen para el dashboard cuando no hay datos del productor"""
        class AlmacenMock:
            def __init__(self):
                self.tareas_completadas_count = 0
                self.total_tareas = 0
                self.tareas_zona_a = []
                self.tareas_zona_b = []
                self.num_operarios_total = 4
                self.num_traspaletas = 2
                self.num_montacargas = 2
                self.traspaletas = MockResource(2)
                self.montacargas = MockResource(2)
                
            def get_workorders_completadas(self):
                return []
                
            def get_workorders_pendientes(self):
                return []
                
            def calcular_progreso_workorders(self):
                return (0.0, 0, 0)  # progreso_porcentaje, cantidad_recogida, cantidad_total
                
            def simulacion_ha_terminado(self):
                return False
                
        class MockResource:
            def __init__(self, capacity):
                self.capacity = capacity
                self.users = []
                
        return AlmacenMock()
    
    # ELIMINATED: def _renderizar_replay_frame() - Replay frame rendering method removed
    def _ELIMINATED_renderizar_replay_frame(self, operarios_visual, eventos_recibidos, eventos_procesados):
        """Renderiza un frame del motor de replay"""
        # Limpiar pantalla
        self.pantalla.fill((240, 240, 240))  # Fondo gris claro
        
        # Renderizar mapa TMX si esta disponible
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
        
        # HUD de informacion del motor de replay
        self._renderizar_hud_replay(eventos_recibidos, eventos_procesados, len(operarios_visual))
        
        # Actualizar pantalla
        pygame.display.flip()
    
    # ELIMINATED: def _renderizar_agentes_replay() - Replay agent rendering method removed
    def _ELIMINATED_renderizar_agentes_replay(self, surface, operarios_visual):
        """Renderiza los agentes en la superficie especificada"""
        for agent_id, data in operarios_visual.items():
            x = data.get('x', 100)
            y = data.get('y', 100)
            tipo = data.get('tipo', 'terrestre')
            
            # Color segun tipo
            color = (0, 150, 255) if tipo == 'montacargas' else (255, 100, 0)  # Azul o naranja
            
            # Dibujar agente como circulo
            pygame.draw.circle(surface, color, (int(x), int(y)), 8)
            
            # Dibujar ID del agente
            font = pygame.font.Font(None, 16)
            texto = font.render(agent_id[-1], True, (255, 255, 255))  # Solo ultimo caracter
            surface.blit(texto, (int(x) - 5, int(y) - 20))
    
    # ELIMINATED: def _renderizar_hud_replay() - Replay HUD rendering method removed
    def _ELIMINATED_renderizar_hud_replay(self, eventos_recibidos, eventos_procesados, agentes_activos):
        """Renderiza el HUD del motor de replay"""
        font = pygame.font.Font(None, 24)
        textos = [
            f"MOTOR DE REPLAY (PRODUCTOR-CONSUMIDOR)",
            f"Tiempo de reproduccion: {self.playback_time:.1f}s",
            f"Velocidad: {self.factor_aceleracion:.1f}x",
            f"Buffer: {len(self.event_buffer)} eventos",
            f"Recibidos: {eventos_recibidos} | Procesados: {eventos_procesados}",
            f"Agentes activos: {agentes_activos}",
            f"PID SimPy: {self.simulation_process.pid}",
            f"",
            f"Controles: +/- (velocidad), ESC (salir)"
        ]
        
        for i, texto in enumerate(textos):
            superficie_texto = font.render(texto, True, (50, 50, 50))
            self.pantalla.blit(superficie_texto, (10, 10 + i * 25))
    
    # ELIMINATED: def _renderizar_hud_replay_mejorado() - Enhanced replay HUD method removed
    def _ELIMINATED_renderizar_hud_replay_mejorado(self, eventos_recibidos, agentes_activos):
        """Renderiza el HUD del motor de replay mejorado"""
        from visualization.state import estado_visual
        
        font = pygame.font.Font(None, 20)
        y_offset = self.window_size[1] - 120  # Esquina inferior izquierda
        
        textos = [
            f"MOTOR DE REPLAY v2.0",
            f"Tiempo: {self.playback_time:.1f}s | Velocidad: {self.factor_aceleracion:.1f}x",
            f"Eventos/frame: {eventos_recibidos} | Agentes: {agentes_activos}",
            f"WorkOrders: {len(estado_visual['work_orders']) if 'work_orders' in estado_visual else 0}",
            f"Controles: +/- velocidad, O dashboard, ESC salir"
        ]
        
        for i, texto in enumerate(textos):
            superficie_texto = font.render(texto, True, (80, 80, 80))
            self.pantalla.blit(superficie_texto, (10, y_offset + i * 20))
    
    # ELIMINATED: def _renderizar_hud_playback_motor() - Playback motor HUD method removed
    def _ELIMINATED_renderizar_hud_playback_motor(self, eventos_recibidos, eventos_procesados, buffer_size):
        """Renderiza el HUD del motor de playback sincronizado"""
        from visualization.state import estado_visual
        
        font = pygame.font.Font(None, 18)
        y_offset = self.window_size[1] - 140  # Esquina inferior izquierda
        
        # Calcular ratio de sincronizacion
        sync_ratio = eventos_procesados / max(1, eventos_recibidos) if eventos_recibidos > 0 else 1.0
        
        textos = [
            f"MOTOR PLAYBACK v1.0 - CONTROL DE VELOCIDAD",
            f"Playback Time: {self.playback_time:.2f}s | Factor: {self.factor_aceleracion:.1f}x",
            f"Eventos: Recibidos:{eventos_recibidos} Procesados:{eventos_procesados} Buffer:{buffer_size}",
            f"Sincronizacion: {sync_ratio:.2f} | Agentes: {len(estado_visual.get('operarios', {}))}",
            f"WorkOrders: {len(estado_visual.get('work_orders', {}))}",
            f"TECLAS: +/- para cambiar velocidad | ESC salir",
            f"ESTADO: {'REPRODUCIENDO' if buffer_size > 0 or eventos_recibidos > 0 else 'EN ESPERA'}"
        ]
        
        for i, texto in enumerate(textos):
            color = (0, 255, 0) if i == 1 else (80, 80, 80)  # Resaltar tiempo de playback
            superficie_texto = font.render(texto, True, color)
            self.pantalla.blit(superficie_texto, (10, y_offset + i * 18))
    
    # ELIMINATED: def _finalizar_replay_engine() - Replay engine finalization method removed
    def _ELIMINATED_finalizar_replay_engine(self):
        """Finaliza el motor de replay y limpia recursos"""
        print(f"[REPLAY-ENGINE] Finalizando motor de replay...")
        print(f"[REPLAY-ENGINE] Eventos restantes en buffer: {len(self.event_buffer)}")
        
        # Cleanup del proceso SimPy
        if self.simulation_process and self.simulation_process.is_alive():
            print("[REPLAY-ENGINE] Esperando finalizacion del proceso SimPy...")
            self.simulation_process.join(timeout=10)
            if self.simulation_process.is_alive():
                print("[REPLAY-ENGINE] Forzando terminacion del proceso SimPy...")
                self.simulation_process.terminate()
        
        print("[REPLAY-ENGINE] Motor de replay terminado.")
        pygame.quit()
    
    def _manejar_evento(self, evento):
        """Maneja los eventos de pygame"""
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
                print(f"Simulacion {'pausada' if pausado else 'reanudada'}")
            elif evento.key == pygame.K_r:
                self._reiniciar_simulacion()
            elif evento.key == pygame.K_m:
                if self.almacen:
                    mostrar_metricas_consola(self.almacen)
            elif evento.key == pygame.K_x:
                if self.almacen:
                    archivo = exportar_metricas(self.almacen)
                    if archivo:
                        print(f"Metricas exportadas a: {archivo}")
            elif evento.key == pygame.K_d:
                visible = toggle_dashboard()
                self.dashboard.visible = visible
                print(f"Dashboard {'mostrado' if visible else 'oculto'}")
            # ELIMINATED: elif evento.key == pygame.K_EQUALS - Replay speed control removed for pure simulation
            # ELIMINATED: Replay speed increase logic - No replay speed control needed in live simulation
            # ELIMINATED: elif evento.key == pygame.K_MINUS - Replay speed control removed for pure simulation
            # ELIMINATED: Replay speed decrease logic - No replay speed control needed in live simulation
            elif evento.key == pygame.K_o:  # Tecla O para Dashboard de Ordenes
                print("[DIAGNOSTICO-TECLA] Tecla 'O' detectada.")
                # ESCRIBIR TAMBIEN A ARCHIVO PARA GARANTIZAR CAPTURA
                with open('diagnostico_tecla_o.txt', 'a', encoding='utf-8') as f:
                    import time
                    f.write(f"[{time.strftime('%H:%M:%S')}] DIAGNOSTICO-TECLA: Tecla 'O' detectada.\n")
                    f.write(f"[{time.strftime('%H:%M:%S')}] Estado almacen: {'Existe' if self.almacen else 'No Existe'}\n")
                print(f"[DEBUG-DASHBOARD] Intento de abrir dashboard. Estado de self.almacen: {'Existe' if self.almacen else 'No Existe'}")
                self.toggle_order_dashboard()
            # Funciones de diagnostico desactivadas en limpieza
        
        return True
    
    def _renderizar_frame(self):
        """Renderiza un frame completo"""
        # Si tenemos layout_manager, usar el sistema TMX unificado (sin escalado)
        if self.layout_manager:
            # Limpiar pantalla
            self.pantalla.fill((245, 245, 245))  # COLOR_FONDO
            
            # 1. Renderizar el mapa TMX de fondo (correspondencia 1:1)
            self.layout_manager.render(self.pantalla)
            
            # 2. Renderizar operarios directamente (sin escalado - correspondencia 1:1)
            # Las coordenadas en estado_visual ya estan en pixeles TMX centrados
            self.renderer.renderizar_operarios_solamente(self.layout_manager)
        else:
            # Sistema legacy
            self.renderer.renderizar_frame_completo()
        
        if self.dashboard.visible and self.almacen and self.env:
            self.dashboard.actualizar_datos(self.env, self.almacen)
            self.dashboard.renderizar(self.pantalla, self.almacen)
        
        self.renderer.dibujar_mensaje_pausa()
        pygame.display.flip()
    
    # Unused debug method removed in final cleanup
    
    def _simulacion_activa(self):
        """Verifica si la simulacion esta activa usando nueva logica robusta"""
        if self.almacen is None or self.env is None:
            return False
        
        # Usar la nueva logica centralizada de finalizacion
        return not self.almacen.simulacion_ha_terminado()
    
    def _simulacion_completada(self):
        """Maneja la finalizacion de la simulacion con pipeline automatizado"""
        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS")
        print("="*70)
        
        if not self.almacen:
            print("Error: No hay datos del almacen para procesar")
            return
        
        # Mostrar metricas basicas
        mostrar_metricas_consola(self.almacen)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Crear estructura de directorios organizados
        output_base_dir = "output"
        output_dir = os.path.join(output_base_dir, f"simulation_{timestamp}")
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"[SETUP] Directorio de salida creado: {output_dir}")
        except Exception as e:
            print(f"[ERROR] No se pudo crear directorio de salida: {e}")
            # Fallback: usar directorio actual
            output_dir = "."
        
        archivos_generados = []
        
        # 1. Exportar metricas JSON basicas
        archivo_json = os.path.join(output_dir, f"simulacion_completada_{timestamp}.json")
        exportar_metricas(self.almacen, archivo_json)
        archivos_generados.append(archivo_json)
        print(f"[1/4] Metricas JSON guardadas: {archivo_json}")
        
        # 2. Exportar eventos crudos (modificar almacen para usar output_dir)
        archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
        if archivo_eventos:
            archivos_generados.append(archivo_eventos)
            print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")
        
        # ELIMINATED: 2.5. VOLCADO DE REPLAY BUFFER - No replay capabilities in pure simulation
        # ELIMINATED: Replay buffer dumping logic removed - live simulation doesn't generate replay files
        # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine -> Excel
        print("[3/4] Simulacion completada. Generando reporte de Excel...")
        try:
            # Usar el metodo __init__ original con eventos y configuracion en memoria
            analytics_engine = AnalyticsEngine(self.almacen.event_log, self.configuracion)
            analytics_engine.process_events()
            
            # Generar archivo Excel con ruta organizada
            excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
            archivo_excel = analytics_engine.export_to_excel(excel_filename)
            
            if archivo_excel:
                archivos_generados.append(archivo_excel)
                print(f"[3/4] Reporte de Excel generado: {archivo_excel}")
                
                # 4. PIPELINE AUTOMATIZADO: Visualizer -> PNG
                print("[4/4] Reporte de Excel generado. Creando imagen de heatmap...")
                self._ejecutar_visualizador(archivo_excel, timestamp, output_dir)
                
            else:
                print("[ERROR] No se pudo generar el reporte de Excel")
                
        except Exception as e:
            print(f"[ERROR] Error en pipeline de analiticas: {e}")
            import traceback
            traceback.print_exc()
        
        # Resumen final
        print("\n" + "="*70)
        print("PROCESO COMPLETADO")
        print("="*70)
        print("Archivos generados:")
        for i, archivo in enumerate(archivos_generados, 1):
            print(f"  {i}. {archivo}")
        print("="*70)
        print("\nPresiona R para reiniciar o ESC para salir")
    
    def _simulacion_completada_con_buffer(self, buffer_eventos):
        """Maneja la finalizacion de la simulacion con buffer de eventos especifico"""
        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS")
        print("="*70)
        
        if not self.almacen:
            print("Error: No hay datos del almacen para procesar")
            return
        
        # Mostrar metricas basicas
        mostrar_metricas_consola(self.almacen)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Crear estructura de directorios organizados
        output_base_dir = "output"
        output_dir = os.path.join(output_base_dir, f"simulation_{timestamp}")
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"[SETUP] Directorio de salida creado: {output_dir}")
        except Exception as e:
            print(f"[ERROR] No se pudo crear directorio de salida: {e}")
            # Fallback: usar directorio actual
            output_dir = "."
        
        archivos_generados = []
        
        # 1. Exportar metricas JSON basicas
        archivo_json = os.path.join(output_dir, f"simulacion_completada_{timestamp}.json")
        exportar_metricas(self.almacen, archivo_json)
        archivos_generados.append(archivo_json)
        print(f"[1/4] Metricas JSON guardadas: {archivo_json}")
        
        # 2. Exportar eventos crudos (modificar almacen para usar output_dir)
        archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
        if archivo_eventos:
            archivos_generados.append(archivo_eventos)
            print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")

        # ELIMINATED: 2.5. VOLCADO DE REPLAY BUFFER - No replay capabilities in pure simulation
        # ELIMINATED: Replay buffer dumping logic removed - live simulation doesn't generate replay files

        # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine -> Excel
        print("[3/4] Simulacion completada. Generando reporte de Excel...")
        try:
            # Usar el metodo __init__ original con eventos y configuracion en memoria
            analytics_engine = AnalyticsEngine(self.almacen.event_log, self.configuracion)
            analytics_engine.process_events()
            
            # Generar archivo Excel con ruta organizada
            excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
            archivo_excel = analytics_engine.export_to_excel(excel_filename)
            
            if archivo_excel:
                archivos_generados.append(archivo_excel)
                print(f"[3/4] Reporte de Excel generado: {archivo_excel}")
                
                # 4. PIPELINE AUTOMATIZADO: Visualizer -> PNG
                print("[4/4] Reporte de Excel generado. Creando imagen de heatmap...")
                self._ejecutar_visualizador(archivo_excel, timestamp, output_dir)
                
            else:
                print("[ERROR] No se pudo generar el reporte de Excel")
                
        except Exception as e:
            print(f"[ERROR] Error en pipeline de analiticas: {e}")
            import traceback
            traceback.print_exc()
        
        # Resumen final
        print("\n" + "="*70)
        print("PROCESO COMPLETADO")
        print("="*70)
        print("Archivos generados:")
        for i, archivo in enumerate(archivos_generados, 1):
            print(f"  {i}. {archivo}")
        print("="*70)
        print("\nPresiona R para reiniciar o ESC para salir")
    
    def _exportar_eventos_crudos_organizado(self, output_dir: str, timestamp: str):
        """Exporta eventos crudos a directorio organizado"""
        import json
        
        filename = os.path.join(output_dir, f"raw_events_{timestamp}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.almacen.event_log, f, indent=2, ensure_ascii=False)
            print(f"[ANALYTICS] Eventos exportados a: {filename} ({len(self.almacen.event_log)} eventos)")
            return filename
        except Exception as e:
            print(f"[ANALYTICS] Error exportando eventos: {e}")
            return None
    
    def _ejecutar_visualizador(self, excel_path: str, timestamp: str, output_dir: str):
        """Ejecuta visualizer.py automaticamente usando subprocess"""
        try:
            # Construir rutas dinamicamente
            script_dir = os.path.dirname(os.path.abspath(__file__))
            visualizer_path = os.path.join(script_dir, "visualizer.py")
            tmx_path = os.path.join(script_dir, self.configuracion.get('layout_file', 'layouts/WH1.tmx'))
            output_filename = os.path.join(output_dir, f"warehouse_heatmap_{timestamp}.png")
            
            # Verificar que los archivos existen
            if not os.path.exists(visualizer_path):
                print(f"[ERROR] visualizer.py no encontrado en: {visualizer_path}")
                return
            
            if not os.path.exists(tmx_path):
                print(f"[ERROR] Archivo TMX no encontrado: {tmx_path}")
                return
            
            if not os.path.exists(excel_path):
                print(f"[ERROR] Archivo Excel no encontrado: {excel_path}")
                return
            
            # Construir comando para visualizer.py
            cmd = [
                sys.executable,  # Python ejecutable actual
                visualizer_path,
                "--excel_path", excel_path,
                "--tmx_path", tmx_path,
                "--output_path", output_filename,
                "--layer_name", "Capa de patrones 1",  # Nombre de capa TMX conocido
                "--pixel_scale", "16"  # Escala por defecto
            ]
            
            print(f"[VISUALIZER] Ejecutando comando: {' '.join(cmd)}")
            
            # Ejecutar visualizer.py de forma robusta
            result = subprocess.run(
                cmd,
                cwd=script_dir,  # Ejecutar en el directorio del script
                capture_output=True,
                text=True,
                timeout=300  # Timeout de 5 minutos
            )
            
            if result.returncode == 0:
                print(f"[4/4] Imagen de heatmap generada exitosamente: {output_filename}")
                # Mostrar output del visualizer si es util
                if result.stdout:
                    # Filtrar solo las lineas importantes del output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '[VISUALIZER]' in line or 'PROCESAMIENTO COMPLETADO' in line:
                            print(f"  {line}")
            else:
                print(f"[ERROR] visualizer.py fallo con codigo: {result.returncode}")
                if result.stderr:
                    print(f"[ERROR] Error del visualizer: {result.stderr}")
                if result.stdout:
                    print(f"[ERROR] Output del visualizer: {result.stdout}")
                    
        except subprocess.TimeoutExpired:
            print("[ERROR] visualizer.py tomo demasiado tiempo (>5 min) - proceso terminado")
        except Exception as e:
            print(f"[ERROR] Error ejecutando visualizer.py: {e}")
            import traceback
            traceback.print_exc()
    
    def _reiniciar_simulacion(self):
        """Reinicia la simulacion"""
        print("Reiniciando simulacion...")
        
        limpiar_estado()
        self.almacen = None
        self.env = None
        # Resetear bandera de reporte
        self.simulacion_finalizada_reportada = False
        
        if self.obtener_configuracion():
            self.crear_simulacion()
            print("Simulacion reiniciada exitosamente")
        else:
            print("Reinicio cancelado")
    
    def toggle_order_dashboard(self):
        """Alternar visibilidad del dashboard de ordenes (multiproceso)"""
        if self.order_dashboard_process is None or not self.order_dashboard_process.is_alive():
            # Crear proceso del dashboard si no existe
            if self.almacen:
                try:
                    from git.visualization.order_dashboard import launch_dashboard_process
                    
                    # Crear cola para comunicacion
                    self.dashboard_data_queue = Queue()
                    
                    # AUDIT: Instrumentar creacion de proceso Dashboard
                    print("[DASHBOARD] Creando proceso Dashboard de Ordenes...")
                    
                    # Crear proceso separado para el dashboard
                    self.order_dashboard_process = multiprocessing.Process(
                        target=launch_dashboard_process,
                        args=(self.dashboard_data_queue,)
                    )
                    
                    # AUDIT: Log antes de iniciar proceso Dashboard
                    print("[DASHBOARD] Iniciando proceso Dashboard...")
                    self.order_dashboard_process.start()
                    print(f"[DASHBOARD] Proceso Dashboard iniciado (PID: {self.order_dashboard_process.pid})")
                    print("Dashboard de Ordenes abierto en proceso separado - Presiona 'O' nuevamente para cerrar")
                    
                    # NUEVO: Enviar estado completo inicial inmediatamente despues del arranque
                    if self.almacen and self.almacen.dispatcher:
                        # Modo simulacion activa
                        self._enviar_estado_completo_inicial()
                    else:
                        # Modo replay
                        self._enviar_estado_completo_inicial_replay()
                    
                    # SYNC FIX: Verificar si simulacion ya termino y enviar comando de hibernacion
                    if self.simulacion_finalizada_reportada:
                        try:
                            self.dashboard_data_queue.put('__SIMULATION_ENDED__')
                            print("[DASHBOARD-SYNC] Comando __SIMULATION_ENDED__ enviado a dashboard post-simulacion")
                        except Exception as e:
                            print(f"[DASHBOARD-SYNC] Error enviando comando de hibernacion: {e}")
                    
                except ImportError as e:
                    print(f"Error importando launch_dashboard_process: {e}")
                except Exception as e:
                    print(f"Error creando dashboard: {e}")
            else:
                print("No hay simulacion activa para mostrar ordenes")
        else:
            # NUEVO: Cierre graceful del proceso dashboard
            try:
                if self.order_dashboard_process.is_alive():
                    # Enviar mensaje de cierre por la cola
                    if self.dashboard_data_queue:
                        try:
                            self.dashboard_data_queue.put_nowait('__EXIT_COMMAND__')
                            print("[DASHBOARD] Comando de cierre enviado")
                        except:
                            pass  # Cola llena, proceder con terminacion
                    
                    # Esperar cierre graceful
                    self.order_dashboard_process.join(timeout=3)
                    
                    # Si no responde, terminacion forzada
                    if self.order_dashboard_process.is_alive():
                        print("[DASHBOARD] Timeout - forzando terminacion")
                        self.order_dashboard_process.terminate()
                        self.order_dashboard_process.join(timeout=1)
                        print("[PROCESS-LIFECYCLE] Join post-terminate Dashboard completado")
                    else:
                        print("[PROCESS-LIFECYCLE] Dashboard terminado exitosamente via join()")
                        
                self.order_dashboard_process = None
                self.dashboard_data_queue = None
                print("Dashboard de Ordenes cerrado correctamente")
            except Exception as e:
                print(f"Error cerrando dashboard: {e}")
                self.order_dashboard_process = None
                self.dashboard_data_queue = None
    
    def _enviar_estado_completo_inicial(self):
        """
        NUEVO: Envia el estado completo de todas las WorkOrders al dashboard recien iniciado
        Protocolo anti-condicion de carrera: full_state antes que deltas
        """
        if (self.dashboard_data_queue and 
            self.almacen and 
            self.almacen.dispatcher):
            
            try:
                # Obtener estado completo actual (activas + historicas)
                lista_viva = self.almacen.dispatcher.lista_maestra_work_orders
                lista_historica = self.almacen.dispatcher.work_orders_completadas_historicas
                lista_completa = lista_viva + lista_historica
                
                # Generar snapshot completo de todas las WorkOrders
                full_state_data = []
                for work_order in lista_completa:
                    wo_state = {
                        "id": work_order.id,
                        "order_id": work_order.order_id,
                        "tour_id": work_order.tour_id,
                        "sku_id": work_order.sku.id if work_order.sku else "N/A",
                        "status": work_order.status,
                        "ubicacion": work_order.ubicacion,
                        "work_area": work_order.work_area,
                        "cantidad_restante": work_order.cantidad_restante,
                        "volumen_restante": work_order.calcular_volumen_restante(),
                        "assigned_agent_id": work_order.assigned_agent_id
                    }
                    full_state_data.append(wo_state)
                
                # Crear mensaje de estado completo con formato estructurado
                import time
                full_state_message = {
                    'type': 'full_state',
                    'timestamp': time.time(),
                    'data': full_state_data
                }
                
                # Enviar estado completo inicial
                self.dashboard_data_queue.put_nowait(full_state_message)
                
                # Inicializar cache de estado para deltas futuros
                self.dashboard_last_state = {}
                for work_order_data in full_state_data:
                    self.dashboard_last_state[work_order_data['id']] = work_order_data

            except Exception as e:
                pass
    
    def _actualizar_dashboard_ordenes(self):
        """Enviar datos actualizados al dashboard de ordenes si esta activo"""
        # INSTRUMENTACION: Verificar enlace de comunicacion
        print(f"[COMMS-LINK] Verificando enlace... Proceso dashboard existe: {self.order_dashboard_process is not None}")
        
        if (self.order_dashboard_process and 
            self.order_dashboard_process.is_alive() and 
            self.dashboard_data_queue and 
            self.almacen and 
            self.almacen.dispatcher):
            
            # INSTRUMENTACION: Estado del proceso y cola
            is_alive_status = self.order_dashboard_process.is_alive()
            queue_size = self.dashboard_data_queue.qsize() if hasattr(self.dashboard_data_queue, 'qsize') else "unknown"
            print(f"[COMMS-LINK] |-- Proceso dashboard vivo: {is_alive_status}. Cola size: {queue_size}. Intentando enviar datos...")
            
            if not is_alive_status:
                print("[COMMS-LINK] |-- !ERROR! El proceso se reporta como no vivo. No se enviaran datos.")
                return
            
            try:
                # OPTIMIZADO: Sistema de delta updates para reducir latencia
                
                # PASO 1: Obtener ambas listas (activas + historicas)
                lista_viva = self.almacen.dispatcher.lista_maestra_work_orders
                lista_historica = self.almacen.dispatcher.work_orders_completadas_historicas
                lista_completa = lista_viva + lista_historica
                
                # PASO 2: Calcular deltas (solo WorkOrders que cambiaron)
                delta_updates = []
                estado_actual = {}
                
                for work_order in lista_completa:
                    # Crear snapshot del estado actual
                    wo_state = {
                        "id": work_order.id,
                        "order_id": work_order.order_id,
                        "tour_id": work_order.tour_id,
                        "sku_id": work_order.sku.id if work_order.sku else "N/A",
                        "status": work_order.status,
                        "ubicacion": work_order.ubicacion,
                        "work_area": work_order.work_area,
                        "cantidad_restante": work_order.cantidad_restante,
                        "volumen_restante": work_order.calcular_volumen_restante(),
                        "assigned_agent_id": work_order.assigned_agent_id
                    }
                    
                    estado_actual[work_order.id] = wo_state
                    
                    # Comparar con estado anterior
                    estado_anterior = self.dashboard_last_state.get(work_order.id)
                    
                    # Si es nueva o cambio algun campo relevante, anadir al delta
                    if (estado_anterior is None or
                        estado_anterior["status"] != wo_state["status"] or
                        estado_anterior["cantidad_restante"] != wo_state["cantidad_restante"] or
                        estado_anterior["assigned_agent_id"] != wo_state["assigned_agent_id"] or
                        estado_anterior["volumen_restante"] != wo_state["volumen_restante"]):
                        
                        delta_updates.append(wo_state)
                
                print(f"[COMMS-LINK] ? Delta calculado: {len(delta_updates)} cambios de {len(lista_completa)} total ({len(lista_viva)} activas + {len(lista_historica)} historicas)")
                
                # PASO 3: Enviar deltas con formato estructurado (si hay cambios)
                if delta_updates:
                    try:
                        # NUEVO: Envolver deltas en formato de protocolo estructurado
                        import time
                        delta_message = {
                            'type': 'delta',
                            'timestamp': time.time(),
                            'data': delta_updates
                        }
                        
                        self.dashboard_data_queue.put_nowait(delta_message)
                    except Exception as e:
                        pass
                else:
                    # No hay cambios, no enviar nada
                    pass
                
                # PASO 4: Actualizar estado anterior para proxima comparacion
                self.dashboard_last_state = estado_actual
                    
            except Exception as e:
                # Error en serializacion - no critico
                print(f"[COMMS-LINK] ? Error critico en serializacion: {e}")
                pass
        else:
            # INSTRUMENTACION: Diagnostico cuando no se envian datos
            if not self.order_dashboard_process:
                print("[COMMS-LINK] |-- No hay proceso dashboard creado")
            elif not self.order_dashboard_process.is_alive():
                print("[COMMS-LINK] |-- Proceso dashboard no esta vivo")
            elif not self.dashboard_data_queue:
                print("[COMMS-LINK] |-- No hay cola de datos")
            elif not self.almacen:
                print("[COMMS-LINK] |-- No hay almacen inicializado")
            elif not self.almacen.dispatcher:
                print("[COMMS-LINK] |-- No hay dispatcher inicializado")
    
    # ELIMINATED: def _enviar_estado_completo_inicial_replay() - Replay initial state method removed
    def _ELIMINATED_enviar_estado_completo_inicial_replay(self):
        """
        REPLAY: Envia el estado completo de WorkOrders desde estado_visual al dashboard recien iniciado
        Adaptado especificamente para modo replay
        """
        if self.dashboard_data_queue:
            try:
                from visualization.state import estado_visual
                
                # Obtener WorkOrders desde estado_visual (datos del replay)
                work_orders = estado_visual.get('work_orders', {})
                
                # Generar snapshot completo
                full_state_data = []
                for work_order_id, work_order_data in work_orders.items():
                    full_state_data.append(work_order_data)
                
                # Crear mensaje de estado completo
                import time
                full_state_message = {
                    'type': 'full_state',
                    'timestamp': time.time(),
                    'data': full_state_data
                }
                
                # Enviar estado completo inicial
                self.dashboard_data_queue.put_nowait(full_state_message)
                print(f"[REPLAY-DASHBOARD] Estado completo inicial enviado: {len(full_state_data)} WorkOrders")
                
                # Inicializar cache para deltas futuros
                self.dashboard_last_state = {}
                for work_order_data in full_state_data:
                    self.dashboard_last_state[work_order_data['id']] = work_order_data.copy()
                
            except Exception as e:
                print(f"[REPLAY-DASHBOARD] Error enviando estado inicial: {e}")
    
    # ELIMINATED: def _actualizar_dashboard_ordenes_replay() - Replay dashboard update method removed
    def _ELIMINATED_actualizar_dashboard_ordenes_replay(self):
        """
        REPLAY: Enviar datos actualizados al dashboard usando estado_visual
        Adaptado especificamente para modo replay
        """
        if (self.order_dashboard_process and 
            self.order_dashboard_process.is_alive() and 
            self.dashboard_data_queue):
            
            try:
                from visualization.state import estado_visual
                
                # Obtener WorkOrders actuales desde estado_visual
                work_orders = estado_visual.get('work_orders', {})
                
                # Calcular deltas (solo WorkOrders que cambiaron)
                delta_updates = []
                estado_actual = {}
                
                for work_order_id, work_order_data in work_orders.items():
                    estado_actual[work_order_id] = work_order_data.copy()
                    
                    # Comparar con estado anterior para detectar cambios
                    if (work_order_id not in self.dashboard_last_state or 
                        self.dashboard_last_state[work_order_id] != work_order_data):
                        delta_updates.append(work_order_data)
                
                # Enviar solo si hay cambios
                if delta_updates:
                    import time
                    delta_message = {
                        'type': 'delta_update',
                        'timestamp': time.time(),
                        'data': delta_updates
                    }
                    
                    self.dashboard_data_queue.put_nowait(delta_message)
                    print(f"[REPLAY-DASHBOARD] Delta enviado: {len(delta_updates)} WorkOrders actualizadas")
                    
                    # Actualizar cache
                    self.dashboard_last_state = estado_actual.copy()
                
            except Exception as e:
                print(f"[REPLAY-DASHBOARD] Error actualizando dashboard: {e}")
    
    def _inicializar_operarios_en_estado_visual(self, agentes):
        """Inicializa estado visual basandose en agentes reales creados"""
        from visualization.state import estado_visual
        
        if not agentes:
            print("[VISUAL-STATE] No hay agentes para inicializar en estado visual")
            return
        
        print(f"[VISUAL-STATE] Inicializando estado visual para {len(agentes)} agentes reales...")
        
        # Limpiar estado visual existente
        estado_visual["operarios"] = {}
        
        # Obtener posiciones usando TMX (OBLIGATORIO)
        if not self.almacen.data_manager or not self.almacen.data_manager.outbound_staging_locations:
            raise SystemExit("[FATAL ERROR] Se requiere DataManager con outbound_staging_locations para inicializar estado visual")
        
        # Usar outbound staging del DataManager como posiciones iniciales
        depot_point = self.almacen.data_manager.outbound_staging_locations[1]  # Staging ID 1
        
        # Crear entradas de estado visual para cada agente real
        for i, agente in enumerate(agentes):
            # Calcular posicion en grilla para distribucion visual
            grid_x = depot_point[0] + (i % 3)  # Distribuir en una grilla 3x3
            grid_y = depot_point[1] + (i // 3)
            
            # Validar que la posicion sea caminable
            if not self.layout_manager.is_walkable(grid_x, grid_y):
                # Buscar posicion caminable cercana
                fallback_pos = self.layout_manager.get_random_walkable_point()
                if fallback_pos:
                    grid_x, grid_y = fallback_pos
                else:
                    grid_x, grid_y = depot_point  # Ultimo recurso: depot original
            
            # Convertir a pixeles
            pixel_x, pixel_y = self.layout_manager.grid_to_pixel(grid_x, grid_y)
            
            # Offset para Forklifts
            if agente.type == "Forklift":
                pixel_y += self.layout_manager.tile_height
            
            # Mapear tipo de agente a tipo visual
            tipo_visual = 'terrestre' if agente.type == 'GroundOperator' else 'montacargas'
            
            # Crear entrada en estado visual usando el ID real del agente
            estado_visual["operarios"][agente.id] = {
                'x': pixel_x,
                'y': pixel_y,
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': tipo_visual
            }
            
            print(f"  [VISUAL-STATE] {agente.id} ({agente.type}) -> posicion ({pixel_x}, {pixel_y})")
        
        print(f"[VISUAL-STATE] Estado visual inicializado para {len(estado_visual['operarios'])} agentes reales")
    
    def _diagnosticar_route_calculator(self):
        """Metodo de diagnostico para el RouteCalculator V2.6"""
        print("\n--- DIAGNOSTICO DEL CALCULADOR DE RUTAS V2.6 ---")
        if not self.almacen or not self.almacen.dispatcher:
            print("El almacen o el dispatcher no estan listos.")
            return

        # Tomar la posicion inicial del primer depot como punto de partida
        start_pos = self.almacen.data_manager.outbound_staging_locations[1]
        print(f"Punto de partida para el diagnostico: Depot en {start_pos}")

        # V2.6: Analizar tareas de la lista maestra en lugar de lineas pendientes
        if hasattr(self.almacen.dispatcher, 'lista_maestra_work_orders') and self.almacen.dispatcher.lista_maestra_work_orders:
            total_work_orders = len(self.almacen.dispatcher.lista_maestra_work_orders)
            sample_size = min(10, total_work_orders)
            print(f"Analizando {sample_size} WorkOrders de {total_work_orders} en la lista maestra...")
            
            for i in range(sample_size):
                work_order = self.almacen.dispatcher.lista_maestra_work_orders[i]
                print(f"  WorkOrder {i+1}: Seq {work_order.pick_sequence}, SKU {work_order.sku.id}, Pos {work_order.ubicacion}")
        else:
            print("No hay tareas en la lista maestra para diagnosticar")
        
        print("V2.6: RouteCalculator integrado con DataManager y AssignmentCostCalculator")
        print("-------------------------------------------\n")
    
    def ejecutar(self):
        """Metodo principal de ejecucion - Modo automatizado sin UI"""
        try:
            # NUEVO ORDEN: Configuracion JSON -> TMX -> Pygame -> Simulacion
            print("[SIMULATOR] Iniciando en modo automatizado (sin UI de configuracion)")
            
            if not self.cargar_configuracion():
                print("Error al cargar configuracion. Saliendo...")
                return
            
            if not self.crear_simulacion():
                print("Error al crear la simulacion. Saliendo...")
                return
            
            # BIFURCACION PRINCIPAL: Headless vs Visual vs Multiproceso
            if self.headless_mode:
                # Modo headless: maxima velocidad sin interfaz grafica
                self._ejecutar_bucle_headless()
            else:
                # REFACTOR: Modo visual con arquitectura Productor-Consumidor
                print("[SIMULATOR] Iniciando modo visual con multiproceso...")
                
                # 1. Crear cola de comunicacion
                self.visual_event_queue = multiprocessing.Queue()
                
                # 2. Lanzar proceso de simulacion SimPy
                print("[SIMULATOR] Lanzando proceso de simulacion SimPy...")
                self.simulation_process = multiprocessing.Process(
                    target=_run_simulation_process_static,
                    args=(self.visual_event_queue, self.configuracion)
                )
                self.simulation_process.start()
                print(f"[SIMULATOR] Proceso SimPy iniciado (PID: {self.simulation_process.pid})")
                
                # 3. ESPERAR un poco para que el proceso hijo configure SDL primero
                import time
                time.sleep(0.5)
                print("[SIMULATOR] Inicializando interfaz pygame en proceso principal...")
                
                # 4. Inicializar interfaz Pygame DESPUES del proceso hijo
                self.inicializar_pygame()
                
                print("[SIMULATOR] Iniciando bucle principal de visualizacion...")
                print("[SIMULATOR] Presiona ESC para salir, SPACE para pausar")
                
                # 5. Ejecutar bucle de visualizacion principal
                self.ejecutar_bucle_principal()
            
        except KeyboardInterrupt:
            print("\nInterrupcion del usuario. Saliendo...")
        except Exception as e:
            print(f"Error inesperado: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.limpiar_recursos()

    def limpiar_recursos(self):
        """Limpia todos los recursos incluyendo procesos"""
        if self.simulation_process and self.simulation_process.is_alive():
            print("[CLEANUP] Terminando proceso de simulacion...")
            self.simulation_process.terminate()
            self.simulation_process.join(timeout=5)
        
        limpiar_estado()
        pygame.quit()
        print("Recursos liberados. Hasta luego!")

def _run_simulation_process_static(visual_event_queue, configuracion):
    """
    REFACTOR: Funcion estatica para proceso separado de simulacion SimPy
    
    Esta funcion ejecuta en un proceso hijo y contiene toda la logica
    de inicializacion y ejecucion de SimPy, enviando eventos de estado
    a traves de la cola de multiproceso.
    
    NOTA: Debe ser funcion estatica para evitar problemas de pickle
    """
    # AUDIT: Configurar logging al inicio del proceso simulation_producer
    import logging
    logging.basicConfig(
        level=logging.DEBUG,  # AUDIT: Cambiar a DEBUG para ver todos los logs
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    
    # AUDIT: Log de inicio del proceso productor de simulacion
    logger.info("Iniciando proceso productor de simulacion...")
    
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))
    
    import pygame
    import simpy
    from simulation.warehouse import AlmacenMejorado
    from simulation.operators_workorder import crear_operarios
    from simulation.layout_manager import LayoutManager
    from simulation.assignment_calculator import AssignmentCostCalculator
    from simulation.data_manager import DataManager
    from simulation.pathfinder import Pathfinder
    from simulation.route_calculator import RouteCalculator
    
    try:
        print("[PROCESO-SIMPY] Iniciando proceso de simulacion separado...")
        
        # ARQUITECTURA TMX OBLIGATORIA - Inicializacion en proceso hijo
        print("[PROCESO-SIMPY] Inicializando arquitectura TMX...")
        
        # REFACTOR: PyTMX requiere pygame display inicializado - usar driver dummy para proceso multiproceso
        import os
        # Configurar SDL para evitar conflictos con proceso padre
        os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Usar driver dummy para evitar ventanas en proceso hijo
        os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Tambien desactivar audio para evitar conflictos
        pygame.init()
        # Usar flags especificos para proceso hijo
        pygame.display.set_mode((1, 1), pygame.NOFRAME | pygame.HIDDEN)  # Superficie dummy minima
        
        # 1. Inicializar LayoutManager
        tmx_file = os.path.join(os.path.dirname(__file__), "layouts", "WH1.tmx")
        print(f"[PROCESO-SIMPY] Cargando layout: {tmx_file}")
        layout_manager = LayoutManager(tmx_file)
        
        # 2. Inicializar Pathfinder
        print("[PROCESO-SIMPY] Inicializando pathfinding...")
        pathfinder = Pathfinder(layout_manager.collision_matrix)
        route_calculator = RouteCalculator(pathfinder)
        
        # 3. Crear entorno SimPy
        env = simpy.Environment()
        
        # 4. Crear DataManager
        layout_file = configuracion.get('layout_file', '')
        sequence_file = configuracion.get('sequence_file', '')
        data_manager = DataManager(layout_file, sequence_file)
        
        # 5. Crear calculador de costos
        cost_calculator = AssignmentCostCalculator(data_manager)
        
        # 6. REFACTOR: Crear AlmacenMejorado con cola de eventos
        print("[PROCESO-SIMPY] Creando AlmacenMejorado con cola de eventos...")
        almacen = AlmacenMejorado(
            env,
            configuracion,
            layout_manager=layout_manager,
            pathfinder=pathfinder,
            data_manager=data_manager,
            cost_calculator=cost_calculator,
            simulador=None,  # En proceso hijo no hay simulador principal
            visual_event_queue=visual_event_queue  # NUEVO: Pasar cola
        )
        
        # 7. Inicializar estado visual EN EL PROCESO HIJO (con cola)
        from visualization.state import inicializar_estado_con_cola
        inicializar_estado_con_cola(almacen, env, configuracion, 
                                   layout_manager, visual_event_queue)
        
        # 8. Crear operarios
        print("[PROCESO-SIMPY] Creando operarios...")
        procesos_operarios, operarios = crear_operarios(
            env, almacen, configuracion,
            simulador=None,  # TODO: En proceso hijo no hay referencia al simulador principal
            pathfinder=pathfinder, layout_manager=layout_manager
        )
        
        # 9. Proceso de actualizacion de metricas simple
        def proceso_actualizacion_metricas():
            while True:
                yield almacen.adelantar_tiempo(5.0)
                # Las metricas ahora se envian via cola
                pass
        
        env.process(proceso_actualizacion_metricas())
        
        # 10. Inicializar almacen y crear ordenes
        almacen._crear_catalogo_y_stock()
        almacen._generar_flujo_ordenes()
        
        # 11. Proceso de envio de estado del almacen para el dashboard
        def enviar_estado_almacen():
            while True:
                try:
                    # Crear estado del almacen para el dashboard
                    estado_almacen = {
                        'tareas_completadas_count': almacen.tareas_completadas_count,
                        'total_tareas': getattr(almacen, 'total_tareas', len(almacen.dispatcher.lista_maestra_work_orders) if hasattr(almacen, 'dispatcher') else 0),
                        'tareas_zona_a': [],  # Simplificado por ahora
                        'tareas_zona_b': [],  # Simplificado por ahora
                        'num_operarios_total': almacen.num_operarios_total,
                        'tiempo_simulacion': env.now
                    }
                    
                    visual_event_queue.put({
                        'type': 'almacen_state',
                        'data': estado_almacen,
                        'timestamp': env.now
                    })
                except Exception as e:
                    print(f"[ERROR-ESTADO] Error enviando estado del almacen: {e}")
                
                yield env.timeout(5.0)  # Enviar cada 5 segundos simulados
        
        env.process(enviar_estado_almacen())

        # 12. NUEVO: Proceso de metricas del dashboard
        def proceso_metricas_dashboard(env, almacen, event_queue):
            """
            Proceso SimPy que calcula y emite metricas para el dashboard periodicamente
            """
            # AUDIT: Log de inicio del proceso de metricas
            logger.info("Iniciando proceso de metricas de dashboard...")
            
            while True:
                # AUDIT: Log DEBUG en cada iteracion del bucle
                logger.debug("Proceso de metricas de dashboard: Tick de ejecucion.")
                
                try:
                    # a. Calcular Metricas del almacen - DUAL COUNTERS
                    tiempo = env.now
                    
                    # Contadores duales: WorkOrders y Tareas (PickingTasks)
                    workorders_completadas = almacen.workorders_completadas_count  # Contador real de WorkOrders
                    tareas_completadas = almacen.tareas_completadas_count  # Contador legacy de PickingTasks
                    wos_pendientes = len(almacen.dispatcher.lista_maestra_work_orders) if hasattr(almacen, 'dispatcher') and almacen.dispatcher.lista_maestra_work_orders else 0
                    wos_totales = workorders_completadas + wos_pendientes
                    progreso = (workorders_completadas / wos_totales * 100) if wos_totales > 0 else 0.0
                    
                    # b. Construir el Mensaje - DUAL METRICS
                    mensaje = {
                        'type': 'metricas_dashboard',
                        'data': {
                            'tiempo': tiempo,
                            'workorders_completadas': workorders_completadas,  # KPI principal
                            'tareas_completadas': tareas_completadas,  # Metrica granular
                            'wos_pendientes': wos_pendientes,
                            'wos_totales': wos_totales,
                            'progreso': progreso,
                            'timestamp': env.now
                        }
                    }
                    
                    # c. Enviar el Mensaje a la cola
                    print(f"[METRICAS-DASHBOARD] T={tiempo:.1f}s - WOs:{workorders_completadas}, Tareas:{tareas_completadas}, Pendientes:{wos_pendientes}, Progreso:{progreso:.1f}%")
                    event_queue.put(mensaje)
                    
                except Exception as e:
                    print(f"[ERROR-METRICAS] Error calculando metricas del dashboard: {e}")
                
                # d. Esperar intervalo antes de proxima actualizacion
                yield env.timeout(1.0)  # Actualizar cada 1 segundo simulado
        
        # Lanzar el proceso de metricas junto con otros procesos
        print("[PROCESO-SIMPY] LANZANDO PROCESO DE METRICAS DEL DASHBOARD")
        env.process(proceso_metricas_dashboard(env, almacen, visual_event_queue))
        print("[PROCESO-SIMPY] Proceso de metricas registrado en SimPy")
        
        # 12. Iniciar dispatcher
        if hasattr(almacen, 'dispatcher'):
            print("[PROCESO-SIMPY] Iniciando dispatcher V2.6...")
            env.process(almacen.dispatcher.dispatcher_process(operarios))
        
        print(f"[PROCESO-SIMPY] Simulacion creada: {len(procesos_operarios)} agentes")
        print("[PROCESO-SIMPY] EJECUTANDO SIMULACION CON env.run()...")
        
        # AUDIT: Log antes de la llamada a env.run()
        logger.info("Iniciando bucle de eventos principal de SimPy...")
        
        # 12. EJECUTAR SIMULACION COMPLETA
        env.run()
        
        # AUDIT: Log inmediatamente despues de la llamada a env.run()
        logger.info("Bucle de eventos principal de SimPy ha finalizado. Procediendo a la limpieza...")
        
        print("[PROCESO-SIMPY] Simulacion completada.")
        
        # 13. Procesar analiticas en el proceso productor y enviar resultados
        print("[PROCESO-SIMPY] Procesando analiticas en proceso productor...")
        try:
            # Importar el pipeline de analiticas
            from analytics_engine import AnalyticsEngine
            from datetime import datetime
            import os
            
            def mostrar_metricas_consola_productor(almacen):
                print(f"Tareas completadas: {almacen.tareas_completadas_count}")
                print(f"Tiempo total de simulacion: {env.now:.2f}")
                
            mostrar_metricas_consola_productor(almacen)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Crear estructura de directorios organizados
            output_base_dir = "output"
            output_dir = os.path.join(output_base_dir, f"simulation_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            
            # Pipeline automatizado: AnalyticsEngine -> Excel
            excel_filename = f"analytics_warehouse_{timestamp}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)
            
            analytics_engine = AnalyticsEngine(almacen.event_log, configuracion)
            analytics_engine.process_events()
            
            # Exportar a Excel
            archivo_excel = analytics_engine.export_to_excel(excel_filename)
            print(f"[PROCESO-SIMPY] Excel generado: {archivo_excel}")
            
            import time
            queue_size_before = visual_event_queue.qsize()
            put_start_time = time.time()
            
            # Enviar evento de finalizacion con informacion de archivos generados
            visual_event_queue.put({
                'type': 'simulation_completed',
                'timestamp': env.now,
                'message': 'Simulacion SimPy completada exitosamente',
                'analytics_completed': True,
                'excel_file': archivo_excel,
                'output_dir': output_dir
            })
            
            put_end_time = time.time()
            put_duration_ms = (put_end_time - put_start_time) * 1000
            queue_size_after = visual_event_queue.qsize()
            
        except Exception as e:
            print(f"[ERROR-PROCESO-SIMPY] Error en pipeline de analiticas: {e}")
            import traceback
            traceback.print_exc()
            
            # Enviar evento de finalizacion aunque fallen las analiticas
            visual_event_queue.put({
                'type': 'simulation_completed',
                'timestamp': env.now,
                'message': 'Simulacion completada con errores en analiticas',
                'analytics_completed': False,
                'error': str(e)
            })
        
    except Exception as e:
        print(f"[ERROR-PROCESO-SIMPY] Error en proceso de simulacion: {e}")
        import traceback
        traceback.print_exc()
        # Enviar evento de error
        visual_event_queue.put({
            'type': 'simulation_error',
            'error': str(e),
            'message': 'Error en proceso de simulacion SimPy'
        })
    finally:
        # AUDIT: Log final del proceso productor de simulacion
        logger.info("Proceso productor de simulacion finalizado limpiamente.")
        print("[PROCESO-SIMPY] Proceso de simulacion terminado.")

# Retornar a la clase SimuladorAlmacen (continuacion)

    def _run_simulation_process(self, visual_event_queue, configuracion):
        """Wrapper para llamar a la funcion estatica"""
        _run_simulation_process_static(visual_event_queue, configuracion)
    
    def _proceso_actualizacion_metricas_subprocess(self):
        """Version del proceso de metricas para el subprocess"""
        # Esta funcion no es usada en la version static, pero se deja por compatibilidad
        pass
    
    def limpiar_recursos(self):
        """Limpia todos los recursos incluyendo procesos"""
        if self.simulation_process and self.simulation_process.is_alive():
            print("[CLEANUP] Terminando proceso de simulacion...")
            self.simulation_process.terminate()
            self.simulation_process.join(timeout=5)
        
        limpiar_estado()
        pygame.quit()
        print("Recursos liberados. Hasta luego!")
    
    def _diagnosticar_data_manager(self):
        print("\n--- DIAGNOSTICO DEL DATA MANAGER ---")
        config = self.configuracion
        if config.get('layout_file') and config.get('sequence_file'):
            data_manager = DataManager(config['layout_file'], config['sequence_file'])
            if not data_manager.puntos_de_picking_ordenados:
                print("  [FALLO] El DataManager no pudo cargar o procesar los puntos de picking.")
            else:
                print("  [EXITO] El DataManager se ha cargado correctamente.")
        else:
            print("  [ERROR] Faltan las rutas a los archivos tmx o sequence_csv en la configuracion.")
        print("------------------------------------\n")

    # All unused debug methods removed in final cleanup
    

# REMOVIDO: DashboardWindow pygame_gui - Reemplazado por PyQt6 Dashboard





