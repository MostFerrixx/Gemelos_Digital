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

class SimuladorAlmacen:
    """Clase principal que coordina toda la simulación"""
    
    def __init__(self):
        self.configuracion = None
        self.almacen = None
        self.env = None
        self.pantalla = None
        self.renderer = None
        self.dashboard = None
        self.reloj = None
        self.corriendo = True
        self.order_dashboard_process = None  # Proceso del dashboard de órdenes
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
        
    def inicializar_pygame(self):
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
            
            # Crear el calculador de costos
            self.cost_calculator = AssignmentCostCalculator(self.configuracion['assignment_rules'])
            
            # Mostrar resumen de configuración cargada
            self._mostrar_resumen_config()
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"[CONFIG ERROR] Error al parsear config.json: {e}")
            print("[CONFIG] Usando configuración por defecto como fallback")
            self.configuracion = self._get_default_config()
            self.cost_calculator = AssignmentCostCalculator(self.configuracion['assignment_rules'])
            return True
            
        except Exception as e:
            print(f"[CONFIG ERROR] Error inesperado cargando configuración: {e}")
            print("[CONFIG] Usando configuración por defecto como fallback")
            self.configuracion = self._get_default_config()
            self.cost_calculator = AssignmentCostCalculator(self.configuracion['assignment_rules'])
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
        
        # IMPORTANTE: Inicializar pygame antes de cargar TMX (PyTMX lo requiere)
        pygame.init()
        pygame.display.set_mode((100, 100))  # Ventana temporal para inicializar display
        
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
            cost_calculator=self.cost_calculator # NUEVO V2.6
        )
        
        inicializar_estado(self.almacen, self.env, self.configuracion, layout_manager=self.layout_manager)
        
        # Diagnóstico del RouteCalculator
        self._diagnosticar_route_calculator()
        
        self.procesos_operarios, self.operarios = crear_operarios(
            self.env,
            self.almacen,
            self.configuracion,
            pathfinder=self.pathfinder,  # OBLIGATORIO
            layout_manager=self.layout_manager  # OBLIGATORIO
        )
        
        # FORZAR INICIALIZACIÓN DE OPERARIOS EN ESTADO VISUAL
        self._inicializar_operarios_en_estado_visual()
        
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
        while True:
            yield self.env.timeout(5.0)  # INTERVALO_ACTUALIZACION_METRICAS
            actualizar_metricas_tiempo(estado_visual["operarios"])
    
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
                        velocidad = obtener_velocidad_simulacion()
                        try:
                            # Avanzar simulación con control de velocidad
                            step_time = 0.1 / velocidad  # STEP_SIMULACION
                            self.env.run(until=self.env.now + step_time)
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
                aumentar_velocidad()
            elif evento.key == pygame.K_MINUS or evento.key == pygame.K_KP_MINUS:  # Tecla - o -
                disminuir_velocidad()
            elif evento.key == pygame.K_o:  # Tecla O para Dashboard de Órdenes
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
                    
                    # Crear proceso separado para el dashboard
                    self.order_dashboard_process = multiprocessing.Process(
                        target=launch_dashboard_process,
                        args=(self.dashboard_data_queue,)
                    )
                    
                    # Iniciar el proceso
                    self.order_dashboard_process.start()
                    print("Dashboard de Órdenes abierto en proceso separado - Presiona 'O' nuevamente para cerrar")
                    
                    # NUEVO: Enviar estado completo inicial inmediatamente después del arranque
                    self._enviar_estado_completo_inicial()
                    
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
                        "level": work_order.level,
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
            print(f"[COMMS-LINK] └─ Proceso dashboard vivo: {is_alive_status}. Cola size: {queue_size}. Intentando enviar datos...")
            
            if not is_alive_status:
                print("[COMMS-LINK] └─ ¡ERROR! El proceso se reporta como no vivo. No se enviarán datos.")
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
                        "level": work_order.level,
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
                print("[COMMS-LINK] └─ No hay proceso dashboard creado")
            elif not self.order_dashboard_process.is_alive():
                print("[COMMS-LINK] └─ Proceso dashboard no está vivo")
            elif not self.dashboard_data_queue:
                print("[COMMS-LINK] └─ No hay cola de datos")
            elif not self.almacen:
                print("[COMMS-LINK] └─ No hay almacén inicializado")
            elif not self.almacen.dispatcher:
                print("[COMMS-LINK] └─ No hay dispatcher inicializado")
    
    def _inicializar_operarios_en_estado_visual(self):
        """Inicialización de operarios con soporte TMX"""
        from visualization.state import estado_visual
        
        if not self.configuracion:
            return
            
        num_terrestres = self.configuracion.get('num_operarios_terrestres', 0)
        num_montacargas = self.configuracion.get('num_montacargas', 0)
        total_operarios = num_terrestres + num_montacargas
        
        print(f"Inicializando {num_terrestres} operarios terrestres y {num_montacargas} montacargas...")
        
        # Limpiar operarios existentes
        estado_visual["operarios"] = {}
        
        # Obtener posiciones usando TMX (OBLIGATORIO)
        if not self.almacen.data_manager or not self.almacen.data_manager.outbound_staging_locations:
            raise SystemExit("[FATAL ERROR] Se requiere DataManager con outbound_staging_locations para inicializar operarios")
        
        # Usar outbound staging del DataManager como posiciones iniciales
        depot_point = self.almacen.data_manager.outbound_staging_locations[1]  # Staging ID 1
        pixel_positions = []
        
        # Distribuir operarios alrededor del depot en PÍXELES
        for i in range(total_operarios):
            # Calcular posición en grilla
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
            
            # Convertir a píxeles (ÚNICA FUENTE DE VERDAD)
            pixel_x, pixel_y = self.layout_manager.grid_to_pixel(grid_x, grid_y)
            pixel_positions.append((pixel_x, pixel_y))
        
        print(f"[OPERARIOS] Posiciones calculadas desde TMX depot: {depot_point}")
        print(f"[OPERARIOS] {len(pixel_positions)} operarios posicionados en píxeles")
        
        # Crear operarios terrestres - SOLO PÍXELES
        for i in range(1, num_terrestres + 1):
            if i-1 < len(pixel_positions):
                pixel_x, pixel_y = pixel_positions[i-1]
            else:
                pixel_x, pixel_y = pixel_positions[0]  # Usar primera posición como fallback
            
            estado_visual["operarios"][i] = {
                'x': pixel_x,
                'y': pixel_y,
                # NO hay grid_x, grid_y - solo píxeles
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'terrestre'
            }
        
        # Crear montacargas - SOLO PÍXELES
        for i in range(num_terrestres + 1, num_terrestres + num_montacargas + 1):
            idx = i - 1
            if idx < len(pixel_positions):
                pixel_x, pixel_y = pixel_positions[idx]
                # Offset en píxeles para montacargas
                pixel_y += self.layout_manager.tile_height
            else:
                pixel_x, pixel_y = pixel_positions[0]  # Usar primera posición como fallback
                pixel_y += self.layout_manager.tile_height
            
            estado_visual["operarios"][i] = {
                'x': pixel_x,
                'y': pixel_y,
                # NO hay grid_x, grid_y - solo píxeles
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'montacargas'
            }
        
        total_created = len(estado_visual["operarios"])
        print(f"Operarios inicializados: {total_created}")
        
        for op_id, op_data in estado_visual["operarios"].items():
            print(f"  Operario {op_id}: {op_data['tipo']} en ({op_data['x']}, {op_data['y']})")
    
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
    
    def limpiar_recursos(self):
        """Limpia todos los recursos"""
        limpiar_estado()
        pygame.quit()
        print("Recursos liberados. Hasta luego!")
    
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
            
            # Inicializar pygame DESPUÉS de cargar TMX
            self.inicializar_pygame()
            
            print("[SIMULATOR] Iniciando bucle principal de simulación...")
            print("[SIMULATOR] Presiona ESC para salir, SPACE para pausar, R para reiniciar")
            
            self.ejecutar_bucle_principal()
            
        except KeyboardInterrupt:
            print("\nInterrupcion del usuario. Saliendo...")
        except Exception as e:
            print(f"Error inesperado: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.limpiar_recursos()
    
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
    

def main():
    """Función principal - Modo automatizado"""
    print("="*60)
    print("SIMULADOR DE ALMACEN - GEMELO DIGITAL")
    print("Sistema de Navegación Inteligente v2.6")
    print("Modo Automatizado - Sin UI de Configuración")
    print("="*60)
    print()
    print("INSTRUCCIONES:")
    print("1. Use 'python configurator.py' para crear/modificar configuraciones")
    print("2. Use 'python run_simulator.py' para ejecutar simulaciones automáticamente")
    print()
    print("El simulador buscará 'config.json' en el directorio actual.")
    print("Si no existe, usará configuración por defecto.")
    print()
    
    simulador = SimuladorAlmacen()
    simulador.ejecutar()

if __name__ == "__main__":
    main()