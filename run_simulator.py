# -*- coding: utf-8 -*-
"""
Ejecutor del Simulador de Almacen - Version simplificada sin caracteres problemáticos.
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
import argparse
import logging


# === BUFFER DE EVENTOS PARA REPLAY ===
# REFACTOR: Buffer centralizado ahora manejado por instancia de ReplayBuffer en SimuladorAlmacen



def agregar_evento_replay(buffer, evento):
    """Agrega un evento al búfer de replay"""
    buffer.add_event(evento)

def volcar_replay_a_archivo(buffer, archivo_salida, configuracion, almacen=None, initial_work_orders_snapshot=None):
    """Vuelca el búfer completo a un archivo .jsonl"""
    
    # REFACTOR: Usar la instancia de ReplayBuffer recibida como parámetro
    eventos_a_volcar = buffer.get_events()
    print(f"[VOLCADO-REFACTOR] Usando ReplayBuffer con {len(eventos_a_volcar)} eventos")
    
    # Contar eventos para volcado (logging mínimo)
    wo_events = [e for e in eventos_a_volcar if e.get('type') == 'work_order_update']
    estado_events = [e for e in eventos_a_volcar if e.get('type') == 'estado_agente']
    print(f"[REPLAY-EXPORT] Volcando {len(wo_events)} work_order_update + {len(estado_events)} estado_agente de {len(eventos_a_volcar)} total")
    
    # ELIMINADO: Sistema de respaldo artificial que causaba replay errático
    # Los eventos reales del headless son de alta fidelidad y ya no necesitan respaldo sintético
    
    try:
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            # Escribir metadata de la simulación primero
            metadata = {
                'event_type': 'SIMULATION_START',
                'timestamp': 0,
                'config': configuracion,
                'total_events_captured': len(eventos_a_volcar)
            }
            
            # BUGFIX: Añadir total de WorkOrders al evento SIMULATION_START
            if almacen and hasattr(almacen, 'dispatcher') and hasattr(almacen.dispatcher, 'work_orders_total_inicial'):
                total_work_orders = almacen.dispatcher.work_orders_total_inicial
                metadata['total_work_orders'] = total_work_orders
                print(f"[REPLAY-METADATA] Añadido total_work_orders: {total_work_orders} al evento SIMULATION_START")
            else:
                print(f"[REPLAY-METADATA] WARNING: No se pudo obtener total de WorkOrders del almacen")
            
            # REFACTOR: Usar instantanea capturada en t=0 en lugar de estado al final
            if initial_work_orders_snapshot and len(initial_work_orders_snapshot) > 0:
                metadata['initial_work_orders'] = initial_work_orders_snapshot
                print(f"[REPLAY-METADATA] Añadidas {len(initial_work_orders_snapshot)} initial_work_orders desde instantanea t=0")
            else:
                print(f"[REPLAY-METADATA] WARNING: No se recibio instantanea inicial de WorkOrders")
            
            f.write(json.dumps(metadata, ensure_ascii=False) + '\n')
            
            # Escribir todos los eventos
            for evento in eventos_a_volcar:
                f.write(json.dumps(evento, ensure_ascii=False) + '\n')
            
            # Escribir evento final
            final_event = {
                'event_type': 'SIMULATION_END',
                'timestamp': eventos_a_volcar[-1]['timestamp'] if eventos_a_volcar else 0
            }
            f.write(json.dumps(final_event, ensure_ascii=False) + '\n')
            
        print(f"[REPLAY-BUFFER] {len(eventos_a_volcar)} eventos guardados en {archivo_salida}")
        return True
        
    except Exception as e:
        print(f"[REPLAY-BUFFER] ERROR al escribir archivo: {e}")
        return False

# Importaciones de módulos propios
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
from simulation_buffer import ReplayBuffer

class SimuladorAlmacen:
    """Clase principal que coordina toda la simulación"""
    
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
        
        # REFACTOR: Nueva instancia de ReplayBuffer para estado explícito
        self.replay_buffer = ReplayBuffer()
        
        # REFACTOR: Buffer de replay ahora manejado por self.replay_buffer
        self.order_dashboard_process = None  # Proceso del dashboard de órdenes
        # REFACTOR: Infraestructura de multiproceso para SimPy Productor
        self.visual_event_queue = None       # Cola de eventos visuales
        self.simulation_process = None       # Proceso de simulación SimPy
        self.dashboard_data_queue = None     # Cola para comunicación con el dashboard
        # Nuevos componentes de la arquitectura TMX
        self.layout_manager = None
        self.pathfinder = None
        # Nuevos atributos para escalado dinámico
        self.window_size = (0, 0)
        self.virtual_surface = None
        # Lista de procesos de operarios para verificación de finalización
        self.procesos_operarios = []
        # Bandera para evitar reportes repetidos
        self.simulacion_finalizada_reportada = False
        # NUEVO: Cache de estado anterior para delta updates del dashboard
        self.dashboard_last_state = {}
        
        # REFACTOR FINAL: Motor de visualización tipo "replay"
        self.event_buffer = []           # Buffer de eventos recibidos del productor
        self.playback_time = 0.0         # Reloj de reproducción interno
        self.factor_aceleracion = 1.0    # Factor de velocidad de reproducción
        
    def inicializar_pygame(self):
        # REFACTOR: Pygame ya está inicializado en crear_simulacion(), solo configurar ventana
        
        PANEL_WIDTH = 400
        # 1. Obtener la clave de resolución seleccionada por el usuario
        resolution_key = self.configuracion.get('selected_resolution_key', "Pequeña (800x800)")
        
        # 2. Buscar el tamaño (ancho, alto) en nuestro diccionario
        self.window_size = SUPPORTED_RESOLUTIONS.get(resolution_key, (800, 800))

        print(f"[DISPLAY] Resolución seleccionada por el usuario: '{resolution_key}' -> {self.window_size[0]}x{self.window_size[1]}")

        # 3. Hacemos la ventana principal más ancha para acomodar el panel
        main_window_width = self.window_size[0] + PANEL_WIDTH
        main_window_height = self.window_size[1]
        self.pantalla = pygame.display.set_mode((main_window_width, main_window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Simulador de Almacén - Gemelo Digital")
        
        # 4. La superficie virtual mantiene el tamaño lógico del mapa
        self.virtual_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        print(f"Ventana creada: {main_window_width}x{main_window_height}. Panel UI: {PANEL_WIDTH}px.")
        
        self.reloj = pygame.time.Clock()
        self.renderer = RendererOriginal(self.virtual_surface)
        self.dashboard = DashboardOriginal()
    
    def cargar_configuracion(self):
        """Carga la configuración desde config.json o usa defaults hardcodeados"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        
        try:
            # Intentar cargar config.json
            if os.path.exists(config_path):
                print(f"[CONFIG] Cargando configuración desde: {config_path}")
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.configuracion = json.load(f)
                
                # Sanitizar assignment_rules: convertir claves str a int
                if 'assignment_rules' in self.configuracion and self.configuracion['assignment_rules']:
                    sanitized_rules = {}
                    for agent_type, rules in self.configuracion['assignment_rules'].items():
                        sanitized_rules[agent_type] = {int(k): v for k, v in rules.items()}
                    self.configuracion['assignment_rules'] = sanitized_rules
                
                print("[CONFIG] Configuración cargada exitosamente desde archivo JSON")
            else:
                print("[CONFIG] config.json no encontrado, usando configuración por defecto")
                self.configuracion = self._get_default_config()
                print("[CONFIG] Configuración por defecto cargada")
            
            # Nota: cost_calculator se creará después de inicializar data_manager
            
            # Mostrar resumen de configuración cargada
            self._mostrar_resumen_config()
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"[CONFIG ERROR] Error al parsear config.json: {e}")
            print("[CONFIG] Usando configuración por defecto como fallback")
            self.configuracion = self._get_default_config()
            return True
            
        except Exception as e:
            print(f"[CONFIG ERROR] Error inesperado cargando configuración: {e}")
            print("[CONFIG] Usando configuración por defecto como fallback")
            self.configuracion = self._get_default_config()
            return True
    
    def _get_default_config(self) -> dict:
        """Retorna la configuración por defecto hardcodeada"""
        return {
            # Configuración de tareas de picking
            'total_ordenes': 300,
            'distribucion_tipos': {
                'pequeno': {'porcentaje': 60, 'volumen': 5},
                'mediano': {'porcentaje': 30, 'volumen': 25},
                'grande': {'porcentaje': 10, 'volumen': 80}
            },
            'capacidad_carro': 150,
            
            # Configuración de estrategias
            'strategy': 'Zoning and Snake',
            'dispatch_strategy': 'Ejecución de Plan (Filtro por Prioridad)',
            
            # Configuración de layout
            'layout_file': 'layouts/WH1.tmx',
            'sequence_file': 'layouts/Warehouse_Logic.xlsx',
            
            # Configuración de ventana
            'selected_resolution_key': 'Pequeña (800x800)',
            
            # Configuración de operarios
            'num_operarios_terrestres': 1,
            'num_montacargas': 1,
            'num_operarios_total': 2,
            'capacidad_montacargas': 1000,
            
            # Configuración de asignación de recursos
            'assignment_rules': {
                "GroundOperator": {1: 1},
                "Forklift": {1: 2, 2: 1, 3: 1, 4: 1, 5: 1}
            },
            
            # Compatibilidad con código existente
            'tareas_zona_a': 0,
            'tareas_zona_b': 0,
            'num_operarios': 2
        }
    
    def _mostrar_resumen_config(self):
        """Muestra un resumen de la configuración cargada"""
        config = self.configuracion
        print("\n" + "="*50)
        print("CONFIGURACIÓN DE SIMULACIÓN CARGADA")
        print("="*50)
        print(f"Total de órdenes: {config.get('total_ordenes', 'N/A')}")
        print(f"Operarios terrestres: {config.get('num_operarios_terrestres', 'N/A')}")
        print(f"Montacargas: {config.get('num_montacargas', 'N/A')}")
        print(f"Estrategia de despacho: {config.get('dispatch_strategy', 'N/A')}")
        print(f"Layout: {config.get('layout_file', 'N/A')}")
        print(f"Secuencia: {config.get('sequence_file', 'N/A')}")
        print("="*50 + "\n")
    
    def crear_simulacion(self):
        """Crea una nueva simulación"""
        if not self.configuracion:
            print("Error: No hay configuracion valida")
            return False
        
        # ARQUITECTURA TMX OBLIGATORIA - No hay fallback
        print("[SIMULADOR] Inicializando arquitectura TMX (OBLIGATORIO)...")
        
        # REFACTOR: Inicialización condicional de pygame según el modo de ejecución
        import os  # Mover import al nivel superior
        if self.headless_mode:
            # En modo headless, usar driver dummy para evitar ventanas
            os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Usar driver dummy sin ventanas
            pygame.init()
            # Crear superficie dummy mínima para TMX sin mostrar ventana
            pygame.display.set_mode((1, 1), pygame.NOFRAME)
        else:
            # En modo visual, NO inicializar pygame aquí - ya está inicializado en proceso principal
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
            print("[FATAL ERROR] El simulador requiere un archivo TMX válido para funcionar.")
            print("[FATAL ERROR] Sistema legacy eliminado - sin fallback disponible.")
            raise SystemExit(f"Error cargando TMX: {e}")
        
        # 2. Inicializar Pathfinder con collision_matrix del LayoutManager (OBLIGATORIO)
        print("[TMX] Inicializando sistema de pathfinding...")
        try:
            self.pathfinder = Pathfinder(self.layout_manager.collision_matrix)
            # Crear RouteCalculator después del pathfinder
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
        
        # Crear el calculador de costos después de inicializar data_manager
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
        
        # Diagnóstico del RouteCalculator
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
        
        # Inicializar el almacén y crear órdenes
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
        print(f"  - {self.almacen.total_ordenes} órdenes generadas")
        print(f"  - Master Plan: {len(self.data_manager.puntos_de_picking_ordenados)} puntos de picking")
        if self.layout_manager:
            print(f"  - Layout TMX: ACTIVO ({tmx_file})")
        else:
            print(f"  - Layout TMX: DESACTIVADO (usando legacy)")
        
        print("--- Verificación de Dimensiones del Layout ---")
        print(f"Ancho en Grilla: {self.layout_manager.grid_width}, Ancho de Tile: {self.layout_manager.tile_width}")
        print(f"Alto en Grilla: {self.layout_manager.grid_height}, Alto de Tile: {self.layout_manager.tile_height}")
        print("------------------------------------------")
        return True
    
    def _proceso_actualizacion_metricas(self):
        """Proceso de actualización de métricas"""
        # AUDIT: Importar logging para el proceso de métricas
        import logging
        logger = logging.getLogger(__name__)
        
        # AUDIT: Log de inicio del proceso de métricas (modo headless)
        logger.info("Iniciando proceso de métricas de dashboard...")
        
        while not self.almacen.simulacion_ha_terminado():
            yield self.almacen.adelantar_tiempo(5.0)  # INTERVALO_ACTUALIZACION_METRICAS
            actualizar_metricas_tiempo(estado_visual["operarios"])
        
        # BUGFIX: Log INFO después de que el bucle termine
        logger.info("Proceso de métricas de dashboard finalizado: la simulación ha terminado.")
    
    def ejecutar_bucle_principal(self):
        """Bucle principal completo con simulación y renderizado de agentes."""
        from visualization.original_renderer import renderizar_agentes, renderizar_dashboard
        from visualization.state import estado_visual, obtener_velocidad_simulacion
        
        self.corriendo = True
        while self.corriendo:
            # 1. Manejar eventos (siempre)
            for event in pygame.event.get():
                if not self._manejar_evento(event):
                    self.corriendo = False

            # 2. Lógica de Simulación (SOLO si no ha finalizado)
            if not self.simulacion_finalizada_reportada:
                if not estado_visual["pausa"]:
                    if self._simulacion_activa():
                        try:
                            # REFACTOR V5.3.1: Procesar el siguiente evento disponible sin forzar tiempo
                            self.env.step()
                        except simpy.core.EmptySchedule:
                            # Cuando no hay más eventos programados
                            pass
                        except Exception as e:
                            print(f"Error en simulación: {e}")
                            # Continuar sin detener el bucle
                        
                        # Dashboard updates SOLO durante simulación activa
                        self._actualizar_dashboard_ordenes()
                    else: # Si la simulación ha terminado
                        print("[SIMULADOR] Condición de finalización cumplida: No hay tareas pendientes y todos los agentes están ociosos.")
                        print("Simulación completada y finalizada lógicamente.")
                        # La función de reporte ahora solo se llama UNA VEZ
                        self._simulacion_completada() 
                        
                        # Dashboard final update UNA VEZ
                        self._actualizar_dashboard_ordenes()
                        
                        # Enviar comando de finalización al Dashboard de Órdenes
                        if self.order_dashboard_process and self.order_dashboard_process.is_alive():
                            print("[PIPELINE] Enviando comando de hibernación al Dashboard de Órdenes...")
                            try:
                                self.dashboard_data_queue.put('__SIMULATION_ENDED__')
                            except Exception as e:
                                print(f"[ERROR] No se pudo enviar el comando de hibernación al dashboard: {e}")
                        
                        # Marcar como finalizada para evitar repetición
                        self.simulacion_finalizada_reportada = True

            # 3. Limpiar la pantalla principal
            self.pantalla.fill((240, 240, 240))  # Fondo gris claro

            # 4. Dibujar el mundo de simulación en la superficie virtual
            self.virtual_surface.fill((25, 25, 25))
            if hasattr(self, 'layout_manager') and self.layout_manager:
                self.renderer.renderizar_mapa_tmx(self.virtual_surface, self.layout_manager.tmx_data)
                from visualization.original_renderer import renderizar_tareas_pendientes
                renderizar_tareas_pendientes(self.virtual_surface, self.layout_manager)
            renderizar_agentes(self.virtual_surface)

            # 5. Escalar la superficie virtual al área de simulación en la pantalla
            scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
            self.pantalla.blit(scaled_surface, (0, 0))  # Dibujar el mundo a la izquierda

            # 6. Dibujar el dashboard directamente en la pantalla, en el panel derecho
            renderizar_dashboard(self.pantalla, self.window_size[0], self.almacen, estado_visual["operarios"])

            # 7. La verificación de finalización ahora se maneja en el paso 2

            # 8. Actualizar la pantalla
            pygame.display.flip()
            self.reloj.tick(30)
            
        print("Simulación terminada. Saliendo de Pygame.")
        pygame.quit()
    
    def _ejecutar_bucle_headless(self):
        """Bucle de ejecución headless para máxima velocidad"""
        print("="*60)
        print("MODO HEADLESS ACTIVADO - Ejecutando en modo máxima velocidad")
        print("="*60)
        print("Ejecutando en modo Headless...")
        
        try:
            # BUGFIX: En lugar de env.run() indefinido, ejecutar hasta que la simulación termine
            # Ejecutar eventos SimPy hasta que todas las WorkOrders estén completadas
            step_counter = 0
            while not self.almacen.simulacion_ha_terminado():
                # Avanzar la simulación en pequeños pasos
                try:
                    # Usar un timeout pequeño para permitir verificar la condición de terminación
                    self.env.run(until=self.env.now + 1.0)
                    
                    # AUDIT: Diagnóstico periódico del buffer cada 10 pasos
                    step_counter += 1
                    if step_counter % 10 == 0:
                        buffer_size = len(self.replay_buffer.get_events())
                        print(f"[AUDIT-BUFFER] Paso {step_counter}: Buffer tiene {buffer_size} eventos")
                        
                except simpy.core.EmptySchedule:
                    # No hay más eventos programados, pero verificar si la simulación realmente terminó
                    if self.almacen.simulacion_ha_terminado():
                        break
                    else:
                        # Si no terminó pero no hay eventos, algo está mal
                        print("Advertencia: No hay eventos programados pero la simulación no ha terminado")
                        break
            
            print("Simulación Headless completada.")
            
            # REFACTOR: Buffer ahora manejado por self.replay_buffer
            
            # Llamar a analíticas al finalizar, SIN pasar buffer específico
            self._simulacion_completada_con_buffer(None)
            
        except KeyboardInterrupt:
            print("\nInterrupción del usuario en modo headless. Saliendo...")
        except Exception as e:
            print(f"Error en modo headless: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("Modo headless finalizado.")
    
    def _ejecutar_bucle_consumidor(self):
        """
        BUGFIX PASO 1: Motor de playback_time para restaurar control de velocidad
        
        Este bucle implementa un reloj de reproducción sincronizado que:
        1. Lee eventos del productor y los almacena con timestamps
        2. Avanza el playback_time según factor_aceleracion (teclas +/-)
        3. Procesa eventos del buffer solo cuando su timestamp <= playback_time
        """
        print("[CONSUMIDOR-PLAYBACK] Iniciando bucle con motor de playback_time sincronizado...")
        import queue
        import time
        from visualization.original_renderer import renderizar_agentes, renderizar_dashboard, renderizar_tareas_pendientes
        from visualization.state import estado_visual
        
        # Estado de visualización
        simulacion_activa = True
        self.metricas_actuales = {}  # Estado de métricas del dashboard
        
        # [AUDIT-BACKPRESSURE] Instrumentación del Consumidor
        eventos_procesados_total = 0
        ultimo_reporte_tiempo = time.time()
        
        # AUDIT: Variable de control para verificación de datos única
        datos_verificados = False
        
        # Resetear el reloj de reproducción
        self.playback_time = 0.0
        
        # SONDA 3: Estado antes de iniciar el bucle principal de renderizado
        print(f"\n=== SONDA 3: ANTES DEL BUCLE PRINCIPAL DE RENDERIZADO ===")
        print(f"Work Orders en estado_visual: {len(estado_visual.get('work_orders', {}))}")
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
            # INSTRUMENTACIÓN: Registro del tiempo de inicio del frame
            frame_start_time = time.time()
            # 1. AVANZAR RELOJ DE REPRODUCCIÓN (CONTROLADO POR FACTOR_ACELERACION)
            delta_time = self.reloj.tick(60) / 1000.0  # Delta en segundos (60 FPS base)
            self.playback_time += delta_time * self.factor_aceleracion
            
            # 2. Manejar eventos de usuario (Pygame)
            for event in pygame.event.get():
                if not self._manejar_evento(event):
                    self.corriendo = False
            
            # 3. LLENAR BUFFER: Recibir todos los eventos disponibles del productor
            eventos_recibidos = 0
            
            # [AUDIT-BACKPRESSURE] Monitorear cola antes del drenado
            queue_size_before_drain = self.visual_event_queue.qsize()
            if queue_size_before_drain > 0:
                print(f"[CONSUMIDOR-AUDIT] Iniciando drenado de cola. Tamaño: {queue_size_before_drain}")
            
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
                
                # [AUDIT-BACKPRESSURE] Reportar drenado completado
                if eventos_recibidos > 0:
                    queue_size_after_drain = self.visual_event_queue.qsize()
                    print(f"[CONSUMIDOR-AUDIT] Drenado completado. Eventos recibidos: {eventos_recibidos}, Cola restante: {queue_size_after_drain}")
                    
            except Exception as e:
                print(f"[ERROR-CONSUMIDOR] Error llenando buffer: {e}")
            
            # Ordenar buffer por timestamp para procesamiento cronológico
            self.event_buffer.sort(key=lambda x: x.get('timestamp', 0))
            
            # 4. PROCESAMIENTO DE BUFFER SINCRONIZADO (CAMBIO PRINCIPAL)
            eventos_procesados = 0
            eventos_procesados_este_frame = 0
            
            # [AUDIT-BACKPRESSURE] Reportar estado periódicamente
            tiempo_actual = time.time()
            if tiempo_actual - ultimo_reporte_tiempo >= 2.0:  # Cada 2 segundos
                buffer_size = len(self.event_buffer)
                queue_size = self.visual_event_queue.qsize()
                print(f"[CONSUMIDOR-AUDIT] Reporte periódico: Buffer: {buffer_size} eventos, Cola: {queue_size}, Procesados totales: {eventos_procesados_total}")
                ultimo_reporte_tiempo = tiempo_actual
            while self.event_buffer and self.event_buffer[0]['timestamp'] <= self.playback_time:
                # Sacar el primer evento del buffer
                mensaje = self.event_buffer.pop(0)
                eventos_procesados += 1
                eventos_procesados_este_frame += 1
                eventos_procesados_total += 1
                
                # Procesar evento según su tipo
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
                    
                    # Convertir posición de grilla a píxeles
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
                    # Procesar métricas del dashboard
                    metricas = mensaje['data']
                    self.metricas_actuales = metricas
                    workorders_c = metricas.get('workorders_completadas', metricas.get('wos_completadas', 0))  # Backwards compatibility
                    tareas_c = metricas.get('tareas_completadas', 0)
                    print(f"[PLAYBACK-METRICAS] T={self.playback_time:.1f}s (sim:{metricas['tiempo']:.1f}s), WOs:{workorders_c}, Tareas:{tareas_c}, Factor:{self.factor_aceleracion:.1f}x")
                    
                    # Actualizar dashboard de órdenes si está activo
                    self._actualizar_dashboard_ordenes()
                
                elif mensaje['type'] == 'simulation_completed':
                    print(f"[PLAYBACK] Simulación completada a los {self.playback_time:.1f}s de reproducción")
                    simulacion_activa = False
                    
                elif mensaje['type'] == 'simulation_error':
                    print(f"[PLAYBACK] Error: {mensaje['error']}")
                    simulacion_activa = False
            
            # 5. RENDERIZADO
            if self.corriendo:
                # Limpiar la pantalla principal
                self.pantalla.fill((240, 240, 240))

                # Dibujar el mundo de simulación en la superficie virtual
                self.virtual_surface.fill((25, 25, 25))
                if hasattr(self, 'layout_manager') and self.layout_manager:
                    self.renderer.renderizar_mapa_tmx(self.virtual_surface, self.layout_manager.tmx_data)
                    renderizar_tareas_pendientes(self.virtual_surface, self.layout_manager)
                renderizar_agentes(self.virtual_surface)

                # Escalar la superficie virtual al área de simulación en la pantalla
                scaled_surface = pygame.transform.smoothscale(self.virtual_surface, self.window_size)
                self.pantalla.blit(scaled_surface, (0, 0))

                # Renderizar dashboard
                renderizar_dashboard(self.pantalla, self.window_size[0], self.metricas_actuales, estado_visual["operarios"])

                # HUD de motor de playback mejorado
                self._renderizar_hud_playback_motor(eventos_recibidos, eventos_procesados_este_frame, len(self.event_buffer))

                # Actualizar pantalla
                pygame.display.flip()
            
            # DASHBOARD: Actualizar dashboard de órdenes en modo replay
            self._actualizar_dashboard_ordenes_replay()
            
            # INSTRUMENTACIÓN: Logging de rendimiento de frames
            frame_end_time = time.time()
            frame_duration_ms = (frame_end_time - frame_start_time) * 1000
            if frame_duration_ms > 16:  # Un frame debería durar ~16ms para 60 FPS
                print(f"[PERF-WARN] Frame largo detectado: {frame_duration_ms:.2f} ms. Eventos procesados: {eventos_procesados_este_frame}. Buffer: {len(self.event_buffer)}. Playback Time: {self.playback_time:.2f}s")
        
        # PIPELINE DE ANALÍTICAS AL FINALIZAR
        print("[CONSUMIDOR-FINAL] Finalizando simulación e iniciando pipeline de analíticas...")
        
        # Esperar a que termine el proceso SimPy
        if self.simulation_process and self.simulation_process.is_alive():
            print("[CONSUMIDOR-FINAL] Esperando finalización del proceso SimPy...")
            self.simulation_process.join(timeout=10)
            if self.simulation_process.is_alive():
                print("[CONSUMIDOR-FINAL] Forzando terminación del proceso SimPy...")
                self.simulation_process.terminate()
                self.simulation_process.join(timeout=5)
        
        # Cerrar Dashboard de Órdenes si está abierto
        if self.order_dashboard_process and self.order_dashboard_process.is_alive():
            print("[CONSUMIDOR-FINAL] Cerrando Dashboard de Órdenes...")
            try:
                if self.dashboard_data_queue:
                    self.dashboard_data_queue.put_nowait('__EXIT_COMMAND__')
            except:
                pass
            self.order_dashboard_process.join(timeout=3)
            if self.order_dashboard_process.is_alive():
                self.order_dashboard_process.terminate()
        
        # Reportar finalización (las analíticas ya se procesaron en el productor)
        print("[CONSUMIDOR-FINAL] Pipeline de analíticas completado en el proceso productor.")
        print("[CONSUMIDOR-FINAL] Revise el directorio 'output/' para los archivos generados.")
        
        print("[CONSUMIDOR-FINAL] Bucle de consumidor terminado.")
        pygame.quit()
    
    def _crear_almacen_mock(self):
        """Crea un mock del almacén para el dashboard cuando no hay datos del productor"""
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
    
    def _renderizar_replay_frame(self, operarios_visual, eventos_recibidos, eventos_procesados):
        """Renderiza un frame del motor de replay"""
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
        font = pygame.font.Font(None, 24)
        textos = [
            f"MOTOR DE REPLAY (PRODUCTOR-CONSUMIDOR)",
            f"Tiempo de reproducción: {self.playback_time:.1f}s",
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
    
    def _renderizar_hud_replay_mejorado(self, eventos_recibidos, agentes_activos):
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
    
    def _renderizar_hud_playback_motor(self, eventos_recibidos, eventos_procesados, buffer_size):
        """Renderiza el HUD del motor de playback sincronizado"""
        from visualization.state import estado_visual
        
        font = pygame.font.Font(None, 18)
        y_offset = self.window_size[1] - 140  # Esquina inferior izquierda
        
        # Calcular ratio de sincronización
        sync_ratio = eventos_procesados / max(1, eventos_recibidos) if eventos_recibidos > 0 else 1.0
        
        textos = [
            f"MOTOR PLAYBACK v1.0 - CONTROL DE VELOCIDAD",
            f"Playback Time: {self.playback_time:.2f}s | Factor: {self.factor_aceleracion:.1f}x",
            f"Eventos: Recibidos:{eventos_recibidos} Procesados:{eventos_procesados} Buffer:{buffer_size}",
            f"Sincronización: {sync_ratio:.2f} | Agentes: {len(estado_visual.get('operarios', {}))}",
            f"WorkOrders: {len(estado_visual.get('work_orders', {}))}",
            f"TECLAS: +/- para cambiar velocidad | ESC salir",
            f"ESTADO: {'REPRODUCIENDO' if buffer_size > 0 or eventos_recibidos > 0 else 'EN ESPERA'}"
        ]
        
        for i, texto in enumerate(textos):
            color = (0, 255, 0) if i == 1 else (80, 80, 80)  # Resaltar tiempo de playback
            superficie_texto = font.render(texto, True, color)
            self.pantalla.blit(superficie_texto, (10, y_offset + i * 18))
    
    def _finalizar_replay_engine(self):
        """Finaliza el motor de replay y limpia recursos"""
        print(f"[REPLAY-ENGINE] Finalizando motor de replay...")
        print(f"[REPLAY-ENGINE] Eventos restantes en buffer: {len(self.event_buffer)}")
        
        # Cleanup del proceso SimPy
        if self.simulation_process and self.simulation_process.is_alive():
            print("[REPLAY-ENGINE] Esperando finalización del proceso SimPy...")
            self.simulation_process.join(timeout=10)
            if self.simulation_process.is_alive():
                print("[REPLAY-ENGINE] Forzando terminación del proceso SimPy...")
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
            elif evento.key == pygame.K_EQUALS or evento.key == pygame.K_KP_PLUS:  # Tecla + o +
                # REFACTOR FINAL: Control de velocidad local del motor de replay
                factores = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
                if self.factor_aceleracion in factores and factores.index(self.factor_aceleracion) < len(factores) - 1:
                    self.factor_aceleracion = factores[factores.index(self.factor_aceleracion) + 1]
                else:
                    self.factor_aceleracion = factores[-1]
                print(f"[REPLAY] Velocidad de reproducción: {self.factor_aceleracion:.1f}x")
            elif evento.key == pygame.K_MINUS or evento.key == pygame.K_KP_MINUS:  # Tecla - o -
                # REFACTOR FINAL: Control de velocidad local del motor de replay
                factores = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
                if self.factor_aceleracion in factores and factores.index(self.factor_aceleracion) > 0:
                    self.factor_aceleracion = factores[factores.index(self.factor_aceleracion) - 1]
                else:
                    self.factor_aceleracion = factores[0]
                print(f"[REPLAY] Velocidad de reproducción: {self.factor_aceleracion:.1f}x")
            elif evento.key == pygame.K_o:  # Tecla O para Dashboard de Órdenes
                print("[DIAGNOSTICO-TECLA] Tecla 'O' detectada.")
                # ESCRIBIR TAMBIÉN A ARCHIVO PARA GARANTIZAR CAPTURA
                with open('diagnostico_tecla_o.txt', 'a', encoding='utf-8') as f:
                    import time
                    f.write(f"[{time.strftime('%H:%M:%S')}] DIAGNOSTICO-TECLA: Tecla 'O' detectada.\n")
                    f.write(f"[{time.strftime('%H:%M:%S')}] Estado almacen: {'Existe' if self.almacen else 'No Existe'}\n")
                print(f"[DEBUG-DASHBOARD] Intento de abrir dashboard. Estado de self.almacen: {'Existe' if self.almacen else 'No Existe'}")
                self.toggle_order_dashboard()
            # Funciones de diagnóstico desactivadas en limpieza
        
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
            # Las coordenadas en estado_visual ya están en píxeles TMX centrados
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
        """Verifica si la simulación está activa usando nueva lógica robusta"""
        if self.almacen is None or self.env is None:
            return False
        
        # Usar la nueva lógica centralizada de finalización
        return not self.almacen.simulacion_ha_terminado()
    
    def _simulacion_completada(self):
        """Maneja la finalización de la simulación con pipeline automatizado"""
        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS")
        print("="*70)
        
        if not self.almacen:
            print("Error: No hay datos del almacén para procesar")
            return
        
        # Mostrar métricas básicas
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
        
        # 1. Exportar métricas JSON básicas
        archivo_json = os.path.join(output_dir, f"simulacion_completada_{timestamp}.json")
        exportar_metricas(self.almacen, archivo_json)
        archivos_generados.append(archivo_json)
        print(f"[1/4] Métricas JSON guardadas: {archivo_json}")
        
        # 2. Exportar eventos crudos (modificar almacén para usar output_dir)
        archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
        if archivo_eventos:
            archivos_generados.append(archivo_eventos)
            print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")
        
        # 2.5. VOLCADO DE REPLAY BUFFER (Solo en modo headless)
        print(f"[DEBUG] Verificando headless_mode: {self.headless_mode}")
        if self.headless_mode:
            archivo_replay = os.path.join(output_dir, f"replay_events_{timestamp}.jsonl")
            try:
                # BUGFIX: Verificar estado del buffer inmediatamente antes del volcado
                buffer_size = len(self.replay_buffer.get_events())
                print(f"[VOLCADO-DEBUG] Buffer actual tiene {buffer_size} eventos antes del volcado")
                
                # REFACTOR: Pasar instantanea inicial capturada en t=0
                initial_snapshot = getattr(self.almacen, 'initial_work_orders_snapshot', None)
                volcar_replay_a_archivo(self.replay_buffer, archivo_replay, self.configuracion, self.almacen, initial_snapshot)
                archivos_generados.append(archivo_replay)
                print(f"[2.5/4] Eventos de replay guardados: {archivo_replay}")
            except Exception as e:
                print(f"[ERROR] Fallo crítico al volcar el replay: {e}")
        else:
            print(f"[DEBUG] No se volca replay porque headless_mode es False")
        # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine → Excel
        print("[3/4] Simulación completada. Generando reporte de Excel...")
        try:
            # Usar el método __init__ original con eventos y configuración en memoria
            analytics_engine = AnalyticsEngine(self.almacen.event_log, self.configuracion)
            analytics_engine.process_events()
            
            # Generar archivo Excel con ruta organizada
            excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
            archivo_excel = analytics_engine.export_to_excel(excel_filename)
            
            if archivo_excel:
                archivos_generados.append(archivo_excel)
                print(f"[3/4] Reporte de Excel generado: {archivo_excel}")
                
                # 4. PIPELINE AUTOMATIZADO: Visualizer → PNG
                print("[4/4] Reporte de Excel generado. Creando imagen de heatmap...")
                self._ejecutar_visualizador(archivo_excel, timestamp, output_dir)
                
            else:
                print("[ERROR] No se pudo generar el reporte de Excel")
                
        except Exception as e:
            print(f"[ERROR] Error en pipeline de analíticas: {e}")
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
        """Maneja la finalización de la simulación con buffer de eventos específico"""
        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS")
        print("="*70)
        
        if not self.almacen:
            print("Error: No hay datos del almacén para procesar")
            return
        
        # Mostrar métricas básicas
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
        
        # 1. Exportar métricas JSON básicas
        archivo_json = os.path.join(output_dir, f"simulacion_completada_{timestamp}.json")
        exportar_metricas(self.almacen, archivo_json)
        archivos_generados.append(archivo_json)
        print(f"[1/4] Métricas JSON guardadas: {archivo_json}")
        
        # 2. Exportar eventos crudos (modificar almacén para usar output_dir)
        archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
        if archivo_eventos:
            archivos_generados.append(archivo_eventos)
            print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")
        
        # 2.5. VOLCADO DE REPLAY BUFFER (Solo en modo headless)
        print(f"[DEBUG] Verificando headless_mode: {self.headless_mode}")
        if self.headless_mode:
            archivo_replay = os.path.join(output_dir, f"replay_events_{timestamp}.jsonl")
            try:
                # AUDIT: Estado crítico del buffer antes de volcado
                eventos = self.replay_buffer.get_events()
                buffer_size = len(eventos)
                print(f"[AUDIT-ID] Volcando buffer con id: {id(self.replay_buffer)}")
                print(f"[AUDIT-CRITICAL] JUSTO ANTES DE VOLCADO: Buffer contiene {buffer_size} eventos")
                
                # Mostrar tipos de eventos en buffer para diagnóstico
                event_types = {}
                for event in eventos:
                    event_type = event.get('type', 'unknown')
                    event_types[event_type] = event_types.get(event_type, 0) + 1
                print(f"[AUDIT-CRITICAL] Tipos de eventos: {event_types}")
                
                # REFACTOR: Pasar instantanea inicial capturada en t=0
                initial_snapshot = getattr(self.almacen, 'initial_work_orders_snapshot', None)
                volcar_replay_a_archivo(self.replay_buffer, archivo_replay, self.configuracion, self.almacen, initial_snapshot)
                archivos_generados.append(archivo_replay)
                print(f"[2.5/4] Eventos de replay guardados: {archivo_replay}")
            except Exception as e:
                print(f"[ERROR] Fallo crítico al volcar el replay: {e}")
        else:
            print(f"[DEBUG] No se volca replay porque headless_mode es False")
        
        # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine → Excel
        print("[3/4] Simulación completada. Generando reporte de Excel...")
        try:
            # Usar el método __init__ original con eventos y configuración en memoria
            analytics_engine = AnalyticsEngine(self.almacen.event_log, self.configuracion)
            analytics_engine.process_events()
            
            # Generar archivo Excel con ruta organizada
            excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
            archivo_excel = analytics_engine.export_to_excel(excel_filename)
            
            if archivo_excel:
                archivos_generados.append(archivo_excel)
                print(f"[3/4] Reporte de Excel generado: {archivo_excel}")
                
                # 4. PIPELINE AUTOMATIZADO: Visualizer → PNG
                print("[4/4] Reporte de Excel generado. Creando imagen de heatmap...")
                self._ejecutar_visualizador(archivo_excel, timestamp, output_dir)
                
            else:
                print("[ERROR] No se pudo generar el reporte de Excel")
                
        except Exception as e:
            print(f"[ERROR] Error en pipeline de analíticas: {e}")
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
        """Ejecuta visualizer.py automáticamente usando subprocess"""
        try:
            # Construir rutas dinámicamente
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
                # Mostrar output del visualizer si es útil
                if result.stdout:
                    # Filtrar solo las líneas importantes del output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '[VISUALIZER]' in line or 'PROCESAMIENTO COMPLETADO' in line:
                            print(f"  {line}")
            else:
                print(f"[ERROR] visualizer.py falló con código: {result.returncode}")
                if result.stderr:
                    print(f"[ERROR] Error del visualizer: {result.stderr}")
                if result.stdout:
                    print(f"[ERROR] Output del visualizer: {result.stdout}")
                    
        except subprocess.TimeoutExpired:
            print("[ERROR] visualizer.py tomó demasiado tiempo (>5 min) - proceso terminado")
        except Exception as e:
            print(f"[ERROR] Error ejecutando visualizer.py: {e}")
            import traceback
            traceback.print_exc()
    
    def _reiniciar_simulacion(self):
        """Reinicia la simulación"""
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
        """Alternar visibilidad del dashboard de órdenes (multiproceso)"""
        if self.order_dashboard_process is None or not self.order_dashboard_process.is_alive():
            # Crear proceso del dashboard si no existe
            if self.almacen:
                try:
                    from git.visualization.order_dashboard import launch_dashboard_process
                    
                    # Crear cola para comunicación
                    self.dashboard_data_queue = Queue()
                    
                    # AUDIT: Instrumentar creación de proceso Dashboard
                    print("[DASHBOARD] Creando proceso Dashboard de Órdenes...")
                    
                    # Crear proceso separado para el dashboard
                    self.order_dashboard_process = multiprocessing.Process(
                        target=launch_dashboard_process,
                        args=(self.dashboard_data_queue,)
                    )
                    
                    # AUDIT: Log antes de iniciar proceso Dashboard
                    print("[DASHBOARD] Iniciando proceso Dashboard...")
                    self.order_dashboard_process.start()
                    print(f"[DASHBOARD] Proceso Dashboard iniciado (PID: {self.order_dashboard_process.pid})")
                    print("Dashboard de Órdenes abierto en proceso separado - Presiona 'O' nuevamente para cerrar")
                    
                    # NUEVO: Enviar estado completo inicial inmediatamente después del arranque
                    if self.almacen and self.almacen.dispatcher:
                        # Modo simulación activa
                        self._enviar_estado_completo_inicial()
                    else:
                        # Modo replay
                        self._enviar_estado_completo_inicial_replay()
                    
                    # SYNC FIX: Verificar si simulación ya terminó y enviar comando de hibernación
                    if self.simulacion_finalizada_reportada:
                        try:
                            self.dashboard_data_queue.put('__SIMULATION_ENDED__')
                            print("[DASHBOARD-SYNC] Comando __SIMULATION_ENDED__ enviado a dashboard post-simulación")
                        except Exception as e:
                            print(f"[DASHBOARD-SYNC] Error enviando comando de hibernación: {e}")
                    
                except ImportError as e:
                    print(f"Error importando launch_dashboard_process: {e}")
                except Exception as e:
                    print(f"Error creando dashboard: {e}")
            else:
                print("No hay simulación activa para mostrar órdenes")
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
                            pass  # Cola llena, proceder con terminación
                    
                    # Esperar cierre graceful
                    self.order_dashboard_process.join(timeout=3)
                    
                    # Si no responde, terminación forzada
                    if self.order_dashboard_process.is_alive():
                        print("[DASHBOARD] Timeout - forzando terminación")
                        self.order_dashboard_process.terminate()
                        self.order_dashboard_process.join(timeout=1)
                        print("[PROCESS-LIFECYCLE] Join post-terminate Dashboard completado")
                    else:
                        print("[PROCESS-LIFECYCLE] Dashboard terminado exitosamente via join()")
                        
                self.order_dashboard_process = None
                self.dashboard_data_queue = None
                print("Dashboard de Órdenes cerrado correctamente")
            except Exception as e:
                print(f"Error cerrando dashboard: {e}")
                self.order_dashboard_process = None
                self.dashboard_data_queue = None
    
    def _enviar_estado_completo_inicial(self):
        """
        NUEVO: Envía el estado completo de todas las WorkOrders al dashboard recién iniciado
        Protocolo anti-condición de carrera: full_state antes que deltas
        """
        if (self.dashboard_data_queue and 
            self.almacen and 
            self.almacen.dispatcher):
            
            try:
                # Obtener estado completo actual (activas + históricas)
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
                print(f"[DEBUG-SENDER] Enviando datos de WO (full_state): {len(full_state_data)} WorkOrders, primeras 2: {full_state_data[:2] if full_state_data else 'VACIO'}")
                print(f"[DEBUG-SENDER] Enviando datos de WO: {full_state_message}")
                self.dashboard_data_queue.put_nowait(full_state_message)
                print(f"[COMMS-PROTOCOL] ✅ Estado completo inicial enviado: {len(full_state_data)} WorkOrders")
                
                # Inicializar cache de estado para deltas futuros
                self.dashboard_last_state = {}
                for work_order_data in full_state_data:
                    self.dashboard_last_state[work_order_data['id']] = work_order_data
                
            except Exception as e:
                print(f"[COMMS-PROTOCOL] ❌ Error enviando estado completo inicial: {e}")
    
    def _actualizar_dashboard_ordenes(self):
        """Enviar datos actualizados al dashboard de órdenes si está activo"""
        # INSTRUMENTACIÓN: Verificar enlace de comunicación
        print(f"[COMMS-LINK] Verificando enlace... Proceso dashboard existe: {self.order_dashboard_process is not None}")
        
        if (self.order_dashboard_process and 
            self.order_dashboard_process.is_alive() and 
            self.dashboard_data_queue and 
            self.almacen and 
            self.almacen.dispatcher):
            
            # INSTRUMENTACIÓN: Estado del proceso y cola
            is_alive_status = self.order_dashboard_process.is_alive()
            queue_size = self.dashboard_data_queue.qsize() if hasattr(self.dashboard_data_queue, 'qsize') else "unknown"
            print(f"[COMMS-LINK] |-- Proceso dashboard vivo: {is_alive_status}. Cola size: {queue_size}. Intentando enviar datos...")
            
            if not is_alive_status:
                print("[COMMS-LINK] |-- ¡ERROR! El proceso se reporta como no vivo. No se enviarán datos.")
                return
            
            try:
                # OPTIMIZADO: Sistema de delta updates para reducir latencia
                
                # PASO 1: Obtener ambas listas (activas + históricas)
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
                    
                    # Si es nueva o cambió algún campo relevante, añadir al delta
                    if (estado_anterior is None or
                        estado_anterior["status"] != wo_state["status"] or
                        estado_anterior["cantidad_restante"] != wo_state["cantidad_restante"] or
                        estado_anterior["assigned_agent_id"] != wo_state["assigned_agent_id"] or
                        estado_anterior["volumen_restante"] != wo_state["volumen_restante"]):
                        
                        delta_updates.append(wo_state)
                
                print(f"[COMMS-LINK] 🔄 Delta calculado: {len(delta_updates)} cambios de {len(lista_completa)} total ({len(lista_viva)} activas + {len(lista_historica)} históricas)")
                
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
                        
                        print(f"[DEBUG-SENDER] Enviando datos de WO (delta): {len(delta_updates)} WorkOrders, primeras 2: {delta_updates[:2] if delta_updates else 'VACIO'}")
                        print(f"[DEBUG-SENDER] Enviando datos de WO: {delta_message}")
                        self.dashboard_data_queue.put_nowait(delta_message)
                        print(f"[COMMS-PROTOCOL] ✅ Delta enviado exitosamente ({len(delta_updates)} WorkOrders cambiadas)")
                    except Exception as e:
                        print(f"[COMMS-PROTOCOL] ⚠️  Error enviando delta: {e} (Cola posiblemente llena)")
                        pass
                else:
                    # No hay cambios, no enviar nada
                    print("[COMMS-PROTOCOL] 📍 Sin cambios - no se envían datos")
                
                # PASO 4: Actualizar estado anterior para próxima comparación
                self.dashboard_last_state = estado_actual
                    
            except Exception as e:
                # Error en serialización - no crítico
                print(f"[COMMS-LINK] ❌ Error crítico en serialización: {e}")
                pass
        else:
            # INSTRUMENTACIÓN: Diagnóstico cuando no se envían datos
            if not self.order_dashboard_process:
                print("[COMMS-LINK] |-- No hay proceso dashboard creado")
            elif not self.order_dashboard_process.is_alive():
                print("[COMMS-LINK] |-- Proceso dashboard no está vivo")
            elif not self.dashboard_data_queue:
                print("[COMMS-LINK] |-- No hay cola de datos")
            elif not self.almacen:
                print("[COMMS-LINK] |-- No hay almacén inicializado")
            elif not self.almacen.dispatcher:
                print("[COMMS-LINK] |-- No hay dispatcher inicializado")
    
    def _enviar_estado_completo_inicial_replay(self):
        """
        REPLAY: Envía el estado completo de WorkOrders desde estado_visual al dashboard recién iniciado
        Adaptado específicamente para modo replay
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
    
    def _actualizar_dashboard_ordenes_replay(self):
        """
        REPLAY: Enviar datos actualizados al dashboard usando estado_visual
        Adaptado específicamente para modo replay
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
        """Inicializa estado visual basándose en agentes reales creados"""
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
            # Calcular posición en grilla para distribución visual
            grid_x = depot_point[0] + (i % 3)  # Distribuir en una grilla 3x3
            grid_y = depot_point[1] + (i // 3)
            
            # Validar que la posición sea caminable
            if not self.layout_manager.is_walkable(grid_x, grid_y):
                # Buscar posición caminable cercana
                fallback_pos = self.layout_manager.get_random_walkable_point()
                if fallback_pos:
                    grid_x, grid_y = fallback_pos
                else:
                    grid_x, grid_y = depot_point  # Último recurso: depot original
            
            # Convertir a píxeles
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
            
            print(f"  [VISUAL-STATE] {agente.id} ({agente.type}) -> posición ({pixel_x}, {pixel_y})")
        
        print(f"[VISUAL-STATE] Estado visual inicializado para {len(estado_visual['operarios'])} agentes reales")
    
    def _diagnosticar_route_calculator(self):
        """Método de diagnóstico para el RouteCalculator V2.6"""
        print("\n--- DIAGNÓSTICO DEL CALCULADOR DE RUTAS V2.6 ---")
        if not self.almacen or not self.almacen.dispatcher:
            print("El almacén o el dispatcher no están listos.")
            return

        # Tomar la posición inicial del primer depot como punto de partida
        start_pos = self.almacen.data_manager.outbound_staging_locations[1]
        print(f"Punto de partida para el diagnóstico: Depot en {start_pos}")

        # V2.6: Analizar tareas de la lista maestra en lugar de líneas pendientes
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
        """Método principal de ejecución - Modo automatizado sin UI"""
        try:
            # NUEVO ORDEN: Configuración JSON → TMX → Pygame → Simulación
            print("[SIMULATOR] Iniciando en modo automatizado (sin UI de configuración)")
            
            if not self.cargar_configuracion():
                print("Error al cargar configuracion. Saliendo...")
                return
            
            if not self.crear_simulacion():
                print("Error al crear la simulacion. Saliendo...")
                return
            
            # BIFURCACIÓN PRINCIPAL: Headless vs Visual vs Multiproceso
            if self.headless_mode:
                # Modo headless: máxima velocidad sin interfaz gráfica
                self._ejecutar_bucle_headless()
            else:
                # REFACTOR: Modo visual con arquitectura Productor-Consumidor
                print("[SIMULATOR] Iniciando modo visual con multiproceso...")
                
                # 1. Crear cola de comunicación
                self.visual_event_queue = multiprocessing.Queue()
                
                # 2. Lanzar proceso de simulación SimPy
                print("[SIMULATOR] Lanzando proceso de simulación SimPy...")
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
                
                # 4. Inicializar interfaz Pygame DESPUÉS del proceso hijo
                self.inicializar_pygame()
                
                print("[SIMULATOR] Iniciando bucle principal de visualización...")
                print("[SIMULATOR] Presiona ESC para salir, SPACE para pausar")
                
                # 5. Ejecutar bucle de visualización como Consumidor
                self._ejecutar_bucle_consumidor()
            
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
            print("[CLEANUP] Terminando proceso de simulación...")
            self.simulation_process.terminate()
            self.simulation_process.join(timeout=5)
        
        limpiar_estado()
        pygame.quit()
        print("Recursos liberados. Hasta luego!")

def _run_simulation_process_static(visual_event_queue, configuracion):
    """
    REFACTOR: Función estática para proceso separado de simulación SimPy
    
    Esta función ejecuta en un proceso hijo y contiene toda la lógica
    de inicialización y ejecución de SimPy, enviando eventos de estado
    a través de la cola de multiproceso.
    
    NOTA: Debe ser función estática para evitar problemas de pickle
    """
    # AUDIT: Configurar logging al inicio del proceso simulation_producer
    import logging
    logging.basicConfig(
        level=logging.DEBUG,  # AUDIT: Cambiar a DEBUG para ver todos los logs
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    
    # AUDIT: Log de inicio del proceso productor de simulación
    logger.info("Iniciando proceso productor de simulación...")
    
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
        print("[PROCESO-SIMPY] Iniciando proceso de simulación separado...")
        
        # ARQUITECTURA TMX OBLIGATORIA - Inicialización en proceso hijo
        print("[PROCESO-SIMPY] Inicializando arquitectura TMX...")
        
        # REFACTOR: PyTMX requiere pygame display inicializado - usar driver dummy para proceso multiproceso
        import os
        # Configurar SDL para evitar conflictos con proceso padre
        os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Usar driver dummy para evitar ventanas en proceso hijo
        os.environ['SDL_AUDIODRIVER'] = 'dummy'  # También desactivar audio para evitar conflictos
        pygame.init()
        # Usar flags específicos para proceso hijo
        pygame.display.set_mode((1, 1), pygame.NOFRAME | pygame.HIDDEN)  # Superficie dummy mínima
        
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
        
        # 9. Proceso de actualización de métricas simple
        def proceso_actualizacion_metricas():
            while True:
                yield almacen.adelantar_tiempo(5.0)
                # Las métricas ahora se envían vía cola
                pass
        
        env.process(proceso_actualizacion_metricas())
        
        # 10. Inicializar almacén y crear órdenes
        almacen._crear_catalogo_y_stock()
        almacen._generar_flujo_ordenes()
        
        # 11. Proceso de envío de estado del almacén para el dashboard
        def enviar_estado_almacen():
            while True:
                try:
                    # Crear estado del almacén para el dashboard
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
                    print(f"[ERROR-ESTADO] Error enviando estado del almacén: {e}")
                
                yield env.timeout(5.0)  # Enviar cada 5 segundos simulados
        
        env.process(enviar_estado_almacen())

        # 12. NUEVO: Proceso de métricas del dashboard
        def proceso_metricas_dashboard(env, almacen, event_queue):
            """
            Proceso SimPy que calcula y emite métricas para el dashboard periódicamente
            """
            # AUDIT: Log de inicio del proceso de métricas
            logger.info("Iniciando proceso de métricas de dashboard...")
            
            while True:
                # AUDIT: Log DEBUG en cada iteración del bucle
                logger.debug("Proceso de métricas de dashboard: Tick de ejecución.")
                
                try:
                    # a. Calcular Métricas del almacén - DUAL COUNTERS
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
                            'tareas_completadas': tareas_completadas,  # Métrica granular
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
                    print(f"[ERROR-METRICAS] Error calculando métricas del dashboard: {e}")
                
                # d. Esperar intervalo antes de próxima actualización
                yield env.timeout(1.0)  # Actualizar cada 1 segundo simulado
        
        # Lanzar el proceso de métricas junto con otros procesos
        print("[PROCESO-SIMPY] LANZANDO PROCESO DE METRICAS DEL DASHBOARD")
        env.process(proceso_metricas_dashboard(env, almacen, visual_event_queue))
        print("[PROCESO-SIMPY] Proceso de metricas registrado en SimPy")
        
        # 12. Iniciar dispatcher
        if hasattr(almacen, 'dispatcher'):
            print("[PROCESO-SIMPY] Iniciando dispatcher V2.6...")
            env.process(almacen.dispatcher.dispatcher_process(operarios))
        
        print(f"[PROCESO-SIMPY] Simulación creada: {len(procesos_operarios)} agentes")
        print("[PROCESO-SIMPY] EJECUTANDO SIMULACIÓN CON env.run()...")
        
        # AUDIT: Log antes de la llamada a env.run()
        logger.info("Iniciando bucle de eventos principal de SimPy...")
        
        # 12. EJECUTAR SIMULACIÓN COMPLETA
        env.run()
        
        # AUDIT: Log inmediatamente después de la llamada a env.run()
        logger.info("Bucle de eventos principal de SimPy ha finalizado. Procediendo a la limpieza...")
        
        print("[PROCESO-SIMPY] Simulación completada.")
        
        # 13. Procesar analíticas en el proceso productor y enviar resultados
        print("[PROCESO-SIMPY] Procesando analíticas en proceso productor...")
        try:
            # Importar el pipeline de analíticas
            from analytics_engine import AnalyticsEngine
            from datetime import datetime
            import os
            
            def mostrar_metricas_consola_productor(almacen):
                print(f"Tareas completadas: {almacen.tareas_completadas_count}")
                print(f"Tiempo total de simulación: {env.now:.2f}")
                
            mostrar_metricas_consola_productor(almacen)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Crear estructura de directorios organizados
            output_base_dir = "output"
            output_dir = os.path.join(output_base_dir, f"simulation_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            
            # Pipeline automatizado: AnalyticsEngine → Excel
            excel_filename = f"analytics_warehouse_{timestamp}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)
            
            analytics_engine = AnalyticsEngine(almacen.event_log, configuracion)
            analytics_engine.process_events()
            
            # Exportar a Excel
            archivo_excel = analytics_engine.export_to_excel(excel_filename)
            print(f"[PROCESO-SIMPY] Excel generado: {archivo_excel}")
            
            # [AUDIT-BACKPRESSURE] Instrumentación del Productor (simulation_completed)
            import time
            queue_size_before = visual_event_queue.qsize()
            put_start_time = time.time()
            print(f"[PRODUCTOR-AUDIT] SIMULATION_COMPLETED: Intentando poner evento. Tamaño actual de la cola: {queue_size_before}")
            
            # Enviar evento de finalización con información de archivos generados
            visual_event_queue.put({
                'type': 'simulation_completed',
                'timestamp': env.now,
                'message': 'Simulación SimPy completada exitosamente',
                'analytics_completed': True,
                'excel_file': archivo_excel,
                'output_dir': output_dir
            })
            
            put_end_time = time.time()
            put_duration_ms = (put_end_time - put_start_time) * 1000
            queue_size_after = visual_event_queue.qsize()
            print(f"[PRODUCTOR-AUDIT] SIMULATION_COMPLETED: Evento puesto con éxito. Duración: {put_duration_ms:.2f}ms. Tamaño nueva cola: {queue_size_after}")
            
        except Exception as e:
            print(f"[ERROR-PROCESO-SIMPY] Error en pipeline de analíticas: {e}")
            import traceback
            traceback.print_exc()
            
            # Enviar evento de finalización aunque fallen las analíticas
            visual_event_queue.put({
                'type': 'simulation_completed',
                'timestamp': env.now,
                'message': 'Simulación completada con errores en analíticas',
                'analytics_completed': False,
                'error': str(e)
            })
        
    except Exception as e:
        print(f"[ERROR-PROCESO-SIMPY] Error en proceso de simulación: {e}")
        import traceback
        traceback.print_exc()
        # Enviar evento de error
        visual_event_queue.put({
            'type': 'simulation_error',
            'error': str(e),
            'message': 'Error en proceso de simulación SimPy'
        })
    finally:
        # AUDIT: Log final del proceso productor de simulación
        logger.info("Proceso productor de simulación finalizado limpiamente.")
        print("[PROCESO-SIMPY] Proceso de simulación terminado.")

# Retornar a la clase SimuladorAlmacen (continuación)

    def _run_simulation_process(self, visual_event_queue, configuracion):
        """Wrapper para llamar a la función estática"""
        _run_simulation_process_static(visual_event_queue, configuracion)
    
    def _proceso_actualizacion_metricas_subprocess(self):
        """Versión del proceso de métricas para el subprocess"""
        # Esta función no es usada en la versión static, pero se deja por compatibilidad
        pass
    
    def limpiar_recursos(self):
        """Limpia todos los recursos incluyendo procesos"""
        if self.simulation_process and self.simulation_process.is_alive():
            print("[CLEANUP] Terminando proceso de simulación...")
            self.simulation_process.terminate()
            self.simulation_process.join(timeout=5)
        
        limpiar_estado()
        pygame.quit()
        print("Recursos liberados. Hasta luego!")
    
    def _diagnosticar_data_manager(self):
        print("\n--- DIAGNÓSTICO DEL DATA MANAGER ---")
        config = self.configuracion
        if config.get('layout_file') and config.get('sequence_file'):
            data_manager = DataManager(config['layout_file'], config['sequence_file'])
            if not data_manager.puntos_de_picking_ordenados:
                print("  [FALLO] El DataManager no pudo cargar o procesar los puntos de picking.")
            else:
                print("  [ÉXITO] El DataManager se ha cargado correctamente.")
        else:
            print("  [ERROR] Faltan las rutas a los archivos tmx o sequence_csv en la configuración.")
        print("------------------------------------\n")

    # All unused debug methods removed in final cleanup
    

def ejecutar_modo_replay(jsonl_file_path):
    """
    Ejecuta el modo replay cargando y visualizando eventos desde un archivo .jsonl
    """
    import multiprocessing
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
                        elif event.get('event_type') != 'SIMULATION_END':
                            eventos.append(event)
                            
                    except json.JSONDecodeError as e:
                        print(f"[REPLAY] Error parseando línea: {e}")
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
    pantalla = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Simulador de Almacén - Modo Replay")
    reloj = pygame.time.Clock()
    
    # Cargar configuración desde el evento SIMULATION_START
    configuracion = simulation_start_event.get('config', {}) if simulation_start_event else {}
    
    # Inicializar arquitectura TMX básica (necesaria para renderizado)
    from simulation.layout_manager import LayoutManager
    from visualization.original_renderer import RendererOriginal
    from visualization.state import inicializar_estado, estado_visual
    
    # Cargar TMX
    tmx_file = os.path.join(os.path.dirname(__file__), "layouts", "WH1.tmx")
    layout_manager = LayoutManager(tmx_file)
    
    # Crear superficies
    virtual_surface = pygame.Surface((warehouse_width, warehouse_width))  # Superficie virtual para el mapa
    renderer = RendererOriginal(virtual_surface)
    
    # Inicializar estado visual básico
    inicializar_estado(None, None, configuracion, layout_manager)
    
    # Configurar estado inicial con WorkOrders si están disponibles
    if initial_work_orders:
        for wo in initial_work_orders:
            estado_visual["work_orders"][wo['id']] = wo.copy()
        print(f"[REPLAY] {len(initial_work_orders)} WorkOrders cargadas en estado inicial")
        
        # SONDA 1: Estado después de procesar initial_work_orders del SIMULATION_START
        print(f"\n=== SONDA 1: DESPUÉS DE PROCESAR INITIAL_WORK_ORDERS ===")
        print(f"Work Orders cargadas: {len(estado_visual['work_orders'])}")
        for wo_id, wo_data in estado_visual["work_orders"].items():
            print(f"  WO {wo_id}: status={wo_data.get('status', 'unknown')}")
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
    print("[REPLAY] Iniciando bucle de visualización...")
    
    # Inicializar motor de playback
    playback_time = 0.0
    replay_speed = 1.0
    velocidades_permitidas = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    processed_event_indices = set()  # Trackear eventos ya procesados
    
    print(f"[REPLAY] Motor de playback inicializado - {len(eventos)} eventos total")
    
    # Variables para gestión del Dashboard de Órdenes en modo replay
    order_dashboard_process = None
    dashboard_data_queue = None
    dashboard_last_state = {}  # Cache para detección de cambios
    dashboard_initialized = False  # REFACTOR: Flag para evitar re-inicialización
    last_processed_wo_events = set()  # REFACTOR: Track eventos WO ya procesados para deltas
    
    # AUDIT: Auto-trigger para capturar estado del dashboard después de 3 segundos
    import time
    auto_trigger_time = time.time() + 3.0
    auto_triggered = False
    
    # Bucle principal de replay con motor temporal
    corriendo = True
    while corriendo:
        # Manejar eventos de pygame
        for event in pygame.event.get():
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
                elif event.key == pygame.K_o:
                    # Tecla 'O' para toggle Dashboard de Órdenes
                    print("[REPLAY-DASHBOARD] Tecla 'O' detectada - Toggle dashboard")
                    if order_dashboard_process is None or not order_dashboard_process.is_alive():
                        # Abrir dashboard
                        try:
                            from git.visualization.order_dashboard import launch_dashboard_process
                            from multiprocessing import Queue
                            
                            # Crear cola para comunicación
                            dashboard_data_queue = Queue()
                            
                            # Crear proceso separado para el dashboard
                            order_dashboard_process = multiprocessing.Process(
                                target=launch_dashboard_process,
                                args=(dashboard_data_queue,)
                            )
                            
                            order_dashboard_process.start()
                            print(f"[REPLAY-DASHBOARD] Dashboard abierto (PID: {order_dashboard_process.pid})")
                            
                            # REFACTOR: Marcar dashboard como inicializado y enviar estado inicial UNA VEZ
                            dashboard_initialized = True
                            
                            # BUGFIX: Reconstruir estado inicial filtrado por playback_time
                            estado_reconstruido = {}
                            
                            # Procesar TODOS los eventos desde el principio, filtrando por playback_time
                            for evento in eventos:
                                event_timestamp = evento.get('timestamp', 0.0)
                                if event_timestamp is None:
                                    event_timestamp = 0.0
                                
                                # CRITICAL: Solo procesar eventos cuyo timestamp <= playback_time actual
                                if event_timestamp <= playback_time:
                                    # Procesar evento SIMULATION_START (WorkOrders iniciales)
                                    if evento.get('event_type') == 'SIMULATION_START':
                                        # Inicializar con WorkOrders del metadata
                                        if initial_work_orders:
                                            for wo in initial_work_orders:
                                                estado_reconstruido[wo['id']] = wo.copy()
                                    
                                    # Procesar eventos work_order_update
                                    elif evento.get('type') == 'work_order_update':
                                        work_order_data = evento.get('data', {})
                                        work_order_id = work_order_data.get('id')
                                        
                                        if work_order_id:
                                            if work_order_id in estado_reconstruido:
                                                estado_reconstruido[work_order_id].update(work_order_data)
                                            else:
                                                estado_reconstruido[work_order_id] = work_order_data.copy()
                            
                            if estado_reconstruido:
                                full_state_data = list(estado_reconstruido.values())
                                
                                # SONDA 2: Estado después de procesar eventos work_order_update en timestamp=0
                                if playback_time == 0.0:
                                    print(f"\n=== SONDA 2: DESPUÉS DE PROCESAR EVENTOS TIMESTAMP=0 ===")
                                    print(f"Work Orders reconstruidas: {len(estado_reconstruido)}")
                                    for wo_id, wo_data in estado_reconstruido.items():
                                        print(f"  WO {wo_id}: status={wo_data.get('status', 'unknown')}")
                                    print("=========================================\n")
                                
                                # AUDIT: Sonda DEBUG-EMISOR - Instrumentar estado antes del envio
                                status_summary = {}
                                for wo_data in full_state_data:
                                    status = wo_data.get('status', 'unknown')
                                    status_summary[status] = status_summary.get(status, 0) + 1
                                
                                # AUDIT: Sonda de comparación temporal - detectar desacoplamiento
                                import time
                                real_time = time.time()
                                print(f"[DEBUG-EMISOR] REPLAY enviando {len(full_state_data)} WorkOrders. Estados: {status_summary}. Playback_time: {playback_time}")
                                print(f"[TEMPORAL-AUDIT] WorkOrder_States_Time: {playback_time:.3f} | RealTime: {real_time:.3f}")
                                
                                full_state_message = {
                                    'type': 'full_state',
                                    'timestamp': playback_time,
                                    'data': full_state_data
                                }
                                # AUDIT: Verificar estados en el momento de activacion del dashboard
                                status_count = {}
                                for wo_data in full_state_data:
                                    status = wo_data.get('status', 'unknown')
                                    status_count[status] = status_count.get(status, 0) + 1
                                print(f"\n=== AUDIT: ESTADO AL PRESIONAR 'O' ===")
                                print(f"Total WorkOrders: {len(full_state_data)}")
                                print(f"Estados encontrados: {status_count}")
                                print(f"Playback time actual: {playback_time}")
                                if full_state_data:
                                    print(f"Primera WO: {full_state_data[0]['id']} = {full_state_data[0].get('status', 'unknown')}")
                                    print(f"Ultima WO: {full_state_data[-1]['id']} = {full_state_data[-1].get('status', 'unknown')}")
                                print("===================================\n")
                                
                                dashboard_data_queue.put_nowait(full_state_message)
                                print(f"[REPLAY-DASHBOARD] Estado inicial enviado: {len(full_state_data)} WorkOrders")
                                
                                # Actualizar cache
                                dashboard_last_state = {wo['id']: wo.copy() for wo in full_state_data}
                            
                        except ImportError as e:
                            print(f"[REPLAY-DASHBOARD] Error importando dashboard: {e}")
                        except Exception as e:
                            print(f"[REPLAY-DASHBOARD] Error abriendo dashboard: {e}")
                    else:
                        # Cerrar dashboard
                        try:
                            if dashboard_data_queue:
                                try:
                                    dashboard_data_queue.put_nowait('__EXIT_COMMAND__')
                                except:
                                    pass
                            
                            order_dashboard_process.join(timeout=3)
                            
                            if order_dashboard_process.is_alive():
                                order_dashboard_process.terminate()
                                order_dashboard_process.join(timeout=1)
                            
                            order_dashboard_process = None
                            dashboard_data_queue = None
                            dashboard_last_state = {}
                            dashboard_initialized = False  # REFACTOR: Reset flag
                            last_processed_wo_events = set()  # REFACTOR: Reset tracking
                            print("[REPLAY-DASHBOARD] Dashboard cerrado")
                            
                        except Exception as e:
                            print(f"[REPLAY-DASHBOARD] Error cerrando dashboard: {e}")
        
        # AUDIT: Auto-trigger para capturar estado del dashboard
        if not auto_triggered and time.time() >= auto_trigger_time:
            print("[AUDIT-AUTO] Auto-triggering dashboard apertura para capturar estado...")
            auto_triggered = True
            # Simular tecla 'O' presionada
            if order_dashboard_process is None or not order_dashboard_process.is_alive():
                # Abrir dashboard
                try:
                    from git.visualization.order_dashboard import launch_dashboard_process
                    from multiprocessing import Queue
                    
                    # Crear cola para comunicación
                    dashboard_data_queue = Queue()
                    
                    # Crear proceso separado para el dashboard
                    order_dashboard_process = multiprocessing.Process(
                        target=launch_dashboard_process,
                        args=(dashboard_data_queue,)
                    )
                    
                    order_dashboard_process.start()
                    print(f"[AUDIT-AUTO] Dashboard abierto automáticamente (PID: {order_dashboard_process.pid})")
                    
                    # REFACTOR: Marcar dashboard como inicializado y enviar estado inicial UNA VEZ
                    dashboard_initialized = True
                    
                    # BUGFIX: Reconstruir estado inicial filtrado por playback_time
                    estado_reconstruido = {}
                    
                    # Procesar TODOS los eventos desde el principio, filtrando por playback_time
                    for evento in eventos:
                        event_timestamp = evento.get('timestamp', 0.0)
                        if event_timestamp is None:
                            event_timestamp = 0.0
                        
                        # CRITICAL: Solo procesar eventos cuyo timestamp <= playback_time actual
                        if event_timestamp <= playback_time:
                            # Procesar evento SIMULATION_START (WorkOrders iniciales)
                            if evento.get('event_type') == 'SIMULATION_START':
                                # Inicializar con WorkOrders del metadata
                                if initial_work_orders:
                                    for wo in initial_work_orders:
                                        estado_reconstruido[wo['id']] = wo.copy()
                            
                            # Procesar eventos work_order_update
                            elif evento.get('type') == 'work_order_update':
                                work_order_data = evento.get('data', {})
                                work_order_id = work_order_data.get('id')
                                
                                if work_order_id:
                                    if work_order_id in estado_reconstruido:
                                        estado_reconstruido[work_order_id].update(work_order_data)
                                    else:
                                        estado_reconstruido[work_order_id] = work_order_data.copy()
                    
                    if estado_reconstruido:
                        full_state_data = list(estado_reconstruido.values())
                        
                        # SONDA 2: Estado después de procesar eventos work_order_update en timestamp=0
                        if playback_time == 0.0:
                            print(f"\n=== SONDA 2: DESPUÉS DE PROCESAR EVENTOS TIMESTAMP=0 ===")
                            print(f"Work Orders reconstruidas: {len(estado_reconstruido)}")
                            for wo_id, wo_data in estado_reconstruido.items():
                                print(f"  WO {wo_id}: status={wo_data.get('status', 'unknown')}")
                            print("=========================================\n")
                        
                        # AUDIT: Sonda DEBUG-EMISOR - Instrumentar estado antes del envio
                        status_summary = {}
                        for wo_data in full_state_data:
                            status = wo_data.get('status', 'unknown')
                            status_summary[status] = status_summary.get(status, 0) + 1
                        
                        # AUDIT: Sonda de comparación temporal - detectar desacoplamiento
                        real_time = time.time()
                        print(f"[DEBUG-EMISOR] REPLAY enviando {len(full_state_data)} WorkOrders. Estados: {status_summary}. Playback_time: {playback_time}")
                        print(f"[TEMPORAL-AUDIT] WorkOrder_States_Time: {playback_time:.3f} | RealTime: {real_time:.3f}")
                        
                        full_state_message = {
                            'type': 'full_state',
                            'timestamp': playback_time,
                            'data': full_state_data
                        }
                        # AUDIT: Verificar estados en el momento de activacion del dashboard
                        status_count = {}
                        for wo_data in full_state_data:
                            status = wo_data.get('status', 'unknown')
                            status_count[status] = status_count.get(status, 0) + 1
                        print(f"\n=== AUDIT: ESTADO AL PRESIONAR 'O' (AUTO) ===")
                        print(f"Total WorkOrders: {len(full_state_data)}")
                        print(f"Estados encontrados: {status_count}")
                        print(f"Playback time actual: {playback_time}")
                        if full_state_data:
                            print(f"Primera WO: {full_state_data[0]['id']} = {full_state_data[0].get('status', 'unknown')}")
                            print(f"Ultima WO: {full_state_data[-1]['id']} = {full_state_data[-1].get('status', 'unknown')}")
                        print("===================================\n")
                        
                        dashboard_data_queue.put_nowait(full_state_message)
                        print(f"[AUDIT-AUTO] Estado inicial enviado: {len(full_state_data)} WorkOrders")
                        
                        # Terminar replay después de capturar audit
                        print("[AUDIT-AUTO] Terminando replay después de capturar datos de auditoría")
                        corriendo = False
                        
                except Exception as e:
                    print(f"[AUDIT-AUTO] Error abriendo dashboard automáticamente: {e}")
        
        # Avanzar tiempo de playback usando delta time
        delta_time = reloj.get_time() / 1000.0  # Convertir ms a segundos
        playback_time += delta_time * replay_speed
        
        # Obtener lote de eventos para el tiempo actual
        eventos_a_procesar = []
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
            
            if evento.get('type') == 'estado_agente':
                agent_id = evento.get('agent_id')
                event_data = evento.get('data', {})
                event_timestamp = evento.get('timestamp', 0.0)
                
                # AUDIT: Sonda de comparación temporal - eventos visuales
                import time
                real_time = time.time()
                if agent_id and 'position' in event_data:  # Solo loggear eventos de movimiento
                    print(f"[TEMPORAL-AUDIT] Visual_Agent_Movement: {event_timestamp:.3f} | Playback_time: {playback_time:.3f} | Agent: {agent_id}")
                
                if agent_id and event_data:
                    # Inicializar agente si no existe
                    if agent_id not in estado_visual["operarios"]:
                        estado_visual["operarios"][agent_id] = {}
                    
                    # CRÍTICO: Usar .update() para fusionar datos sin perder claves existentes
                    estado_visual["operarios"][agent_id].update(event_data)
                    
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
                # Procesar actualización de Work Order
                work_order_data = evento.get('data', {})
                work_order_id = work_order_data.get('id')
                event_timestamp = evento.get('timestamp', 0.0)
                
                # AUDIT: Sonda de comparación temporal - eventos WorkOrder
                import time
                real_time = time.time()
                status = work_order_data.get('status', 'unknown')
                # BUGFIX: Manejar timestamp None
                if event_timestamp is None:
                    event_timestamp = 0.0
                print(f"[TEMPORAL-AUDIT] WorkOrder_Update: {event_timestamp:.3f} | Playback_time: {playback_time:.3f} | WO: {work_order_id} | Status: {status}")
                
                if work_order_id:
                    # Actualizar Work Order en estado visual
                    if 'work_orders' not in estado_visual:
                        estado_visual['work_orders'] = {}
                    estado_visual['work_orders'][work_order_id] = work_order_data.copy()
        
        # REFACTOR: Sistema de delta updates optimizado para Dashboard de Órdenes
        if order_dashboard_process and order_dashboard_process.is_alive() and dashboard_data_queue and dashboard_initialized:
            try:
                # Detectar nuevos eventos work_order_update desde el último frame
                new_wo_events = []
                for event_index, evento in eventos_a_procesar:
                    if evento.get('type') == 'work_order_update' and event_index not in last_processed_wo_events:
                        new_wo_events.append(evento)
                        last_processed_wo_events.add(event_index)
                
                # Enviar deltas solo si hay nuevos eventos WorkOrder
                if new_wo_events:
                    delta_data = []
                    for evento in new_wo_events:
                        work_order_data = evento.get('data', {})
                        if work_order_data and work_order_data.get('id'):
                            delta_data.append(work_order_data.copy())
                    
                    if delta_data:
                        delta_message = {
                            'type': 'delta_update',
                            'timestamp': playback_time,
                            'data': delta_data
                        }
                        dashboard_data_queue.put_nowait(delta_message)
                        print(f"[DELTA-UPDATE] Enviado {len(delta_data)} WorkOrder updates al dashboard")
                        
            except Exception as e:
                print(f"[REPLAY-DASHBOARD] Error enviando deltas: {e}")
        
        # Limpiar pantalla
        pantalla.fill((240, 240, 240))
        virtual_surface.fill((25, 25, 25))
        
        # Renderizar mapa TMX
        if hasattr(layout_manager, 'tmx_data') and layout_manager.tmx_data:
            renderer.renderizar_mapa_tmx(virtual_surface, layout_manager.tmx_data)
        
        # Renderizar agentes con posiciones actualizadas
        from visualization.original_renderer import renderizar_agentes
        if estado_visual.get("operarios"):
            # CRÍTICO: Convertir diccionario a lista para renderizar_agentes
            operarios_a_renderizar = []
            for agent_id, agent_data in estado_visual["operarios"].items():
                agente = agent_data.copy()
                agente['id'] = agent_id  # Asegurar que el ID esté presente
                operarios_a_renderizar.append(agente)
            
            renderizar_agentes(virtual_surface, operarios_a_renderizar, layout_manager)
        
        # Escalar y mostrar superficie virtual del almacén
        scaled_warehouse = pygame.transform.smoothscale(virtual_surface, (warehouse_width, window_height))
        pantalla.blit(scaled_warehouse, (0, 0))
        
        # Renderizar Dashboard de Agentes
        from visualization.original_renderer import renderizar_dashboard
        
        # Preparar métricas para el dashboard - DUAL COUNTERS
        # Contar WorkOrders completadas según contrato de renderizar_dashboard
        work_orders = estado_visual.get('work_orders', {})
        workorders_completadas = sum(1 for wo in work_orders.values() if wo.get('status') == 'completed')
        
        # Contar tareas completadas procesando los eventos acumulados hasta playback_time
        tareas_completadas = 0
        for evento in eventos:
            # BUGFIX: Validación defensiva contra timestamp None que causaba TypeError
            timestamp = evento.get('timestamp', 0)
            if timestamp is None:
                timestamp = 0  # Fallback seguro
            
            if timestamp <= playback_time:
                if evento.get('type') == 'task_completed' or evento.get('type') == 'operation_completed':
                    tareas_completadas += 1
        
        # BUGFIX: Usar total fijo de WorkOrders si está disponible
        total_wos_a_usar = total_work_orders_fijo if total_work_orders_fijo is not None else len(work_orders)
        
        metricas = {
            'tiempo': playback_time,
            'workorders_completadas': workorders_completadas,  # KPI principal
            'tareas_completadas': tareas_completadas,  # Métrica granular
            'total_wos': total_wos_a_usar
        }
        
        # Preparar operarios para el dashboard (convertir a formato esperado)
        operarios_dashboard = []
        for agent_id, agent_data in estado_visual.get('operarios', {}).items():
            operario = agent_data.copy()
            operario['id'] = agent_id
            operarios_dashboard.append(operario)
        
        # Renderizar dashboard en el lado derecho
        renderizar_dashboard(pantalla, warehouse_width, metricas, operarios_dashboard)
        
        # Mostrar información de replay en la parte superior del almacén
        font = pygame.font.Font(None, 20)
        info_text = font.render(f"REPLAY: Tiempo {playback_time:.2f}s | Velocidad: {replay_speed:.2f}x | Eventos {len(processed_event_indices)}/{len(eventos)}", True, (255, 255, 255))
        pantalla.blit(info_text, (10, 10))
        
        # Mostrar información de controles y dashboard
        controls_text = font.render("CONTROLES: +/- velocidad | ESC salir | O dashboard", True, (255, 255, 255))
        pantalla.blit(controls_text, (10, 35))
        
        dashboard_status = "Dashboard: ACTIVO" if (order_dashboard_process and order_dashboard_process.is_alive()) else "Dashboard: INACTIVO"
        dashboard_text = font.render(dashboard_status, True, (0, 255, 0) if (order_dashboard_process and order_dashboard_process.is_alive()) else (128, 128, 128))
        pantalla.blit(dashboard_text, (10, 60))
        
        pygame.display.flip()
        reloj.tick(30)  # 30 FPS
    
    # Limpieza del Dashboard de Órdenes antes de salir
    if order_dashboard_process and order_dashboard_process.is_alive():
        try:
            print("[REPLAY-DASHBOARD] Cerrando dashboard antes de salir...")
            if dashboard_data_queue:
                try:
                    dashboard_data_queue.put_nowait('__EXIT_COMMAND__')
                except:
                    pass  # Cola llena, proceder con terminación
            
            order_dashboard_process.join(timeout=3)
            
            if order_dashboard_process.is_alive():
                order_dashboard_process.terminate()
                order_dashboard_process.join(timeout=1)
            
            print("[REPLAY-DASHBOARD] Dashboard cerrado correctamente")
        except Exception as e:
            print(f"[REPLAY-DASHBOARD] Error cerrando dashboard: {e}")
    
    pygame.quit()
    print("[REPLAY] Modo replay terminado")
    return 0


def main():
    """Función principal - Modo automatizado con soporte headless"""
    # Configurar argparse
    parser = argparse.ArgumentParser(description='Digital Twin Warehouse Simulator')
    parser.add_argument('--headless', action='store_true', 
                       help='Ejecuta la simulación en modo headless (sin UI)')
    parser.add_argument('--replay', type=str, metavar='FILE.jsonl',
                       help='Ejecuta en modo Replay Viewer consumiendo un archivo .jsonl')
    args = parser.parse_args()
    
    print("="*60)
    print("SIMULADOR DE ALMACEN - GEMELO DIGITAL")
    print("Sistema de Navegación Inteligente v2.6")
    
    if args.replay:
        print("Modo REPLAY VIEWER - Visualización de Archivo .jsonl")
        print(f"Archivo: {args.replay}")
    elif args.headless:
        print("Modo HEADLESS - Máxima Velocidad")
    else:
        print("Modo Visual - Con Interfaz Gráfica")
    print("="*60)
    print()
    
    if args.replay:
        # MODO REPLAY VIEWER
        if not os.path.exists(args.replay):
            print(f"Error: Archivo de replay no encontrado: {args.replay}")
            return 1
        
        print(f"[SIMULATOR] Iniciando en modo replay viewer")
        return ejecutar_modo_replay(args.replay)
        
    elif args.headless:
        # MODO HEADLESS (existente)
        simulador = SimuladorAlmacen(headless_mode=True)
        simulador.ejecutar()
    else:
        # MODO VISUAL (existente)
        print("INSTRUCCIONES:")
        print("1. Use 'python configurator.py' para crear/modificar configuraciones")
        print("2. Use 'python run_simulator.py' para modo visual")
        print("3. Use 'python run_simulator.py --headless' para modo de máxima velocidad")
        print("4. Use 'python run_simulator.py --replay archivo.jsonl' para modo replay viewer")
        print()
        print("El simulador buscará 'config.json' en el directorio actual.")
        print("Si no existe, usará configuración por defecto.")
        print()
        
        simulador = SimuladorAlmacen(headless_mode=False)
        simulador.ejecutar()

if __name__ == "__main__":
    main()