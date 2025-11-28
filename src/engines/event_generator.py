# -*- coding: utf-8 -*-
"""
Event Generator Engine - Motor puro de generacion de eventos para replay.
Sin renderizado, sin Pygame, solo SimPy + generacion de .jsonl
"""

import sys
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
            print("[EVENT-GENERATOR] Configuracion cargada exitosamente")
        except ConfigurationError as e:
            print(f"[EVENT-GENERATOR ERROR] Error en configuracion: {e}")
            self.config_manager = None
            self.configuracion = get_default_config()
            print("[EVENT-GENERATOR] Fallback: Usando configuracion por defecto")
        
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
        
        print(f"[EVENT-GENERATOR] Inicializado - Session: {self.session_timestamp}")
    
    def crear_simulacion(self):
        """Crea una nueva simulacion (sin Pygame)"""
        if not self.configuracion:
            print("[EVENT-GENERATOR ERROR] No hay configuracion valida")
            return False
        
        print("[EVENT-GENERATOR] Inicializando arquitectura TMX...")
        
        # 1. Inicializar LayoutManager
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        tmx_file = os.path.join(project_root, self.configuracion.get('layout_file', 'layouts/WH1.tmx'))
        print(f"[EVENT-GENERATOR] Cargando layout: {tmx_file}")
        
        try:
            self.layout_manager = LayoutManager(tmx_file, headless=True)
        except Exception as e:
            print(f"[EVENT-GENERATOR ERROR] No se pudo cargar TMX: {e}")
            return False
        
        # 2. Inicializar Pathfinder
        print("[EVENT-GENERATOR] Inicializando pathfinding...")
        try:
            self.pathfinder = Pathfinder(self.layout_manager.collision_matrix)
            self.route_calculator = RouteCalculator(self.pathfinder)
        except Exception as e:
            print(f"[EVENT-GENERATOR ERROR] No se pudo inicializar pathfinder: {e}")
            return False
        
        # 3. Crear entorno SimPy
        self.env = simpy.Environment()
        
        # 4. Crear DataManager
        layout_file = self.configuracion.get('layout_file', '')
        sequence_file = self.configuracion.get('sequence_file', '')
        self.data_manager = DataManager(layout_file, sequence_file, headless=True)
        
        # 5. Crear calculador de costos
        self.cost_calculator = AssignmentCostCalculator(self.data_manager)
        
        print(f"[EVENT-GENERATOR] Arquitectura TMX inicializada:")
        print(f"  - Dimensiones: {self.layout_manager.grid_width}x{self.layout_manager.grid_height}")
        print(f"  - Puntos de picking: {len(self.layout_manager.picking_points)}")
        print(f"  - Staging areas: {len(self.data_manager.outbound_staging_locations)}")
        
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
        
        # 8. Inicializar almacen y crear ordenes
        self.almacen._crear_catalogo_y_stock()
        self.almacen._generar_flujo_ordenes()
        
        # 9. Capturar snapshot inicial de WorkOrders
        if hasattr(self.almacen, 'dispatcher') and hasattr(self.almacen.dispatcher, 'lista_maestra_work_orders'):
            initial_snapshot = [wo.to_dict() for wo in self.almacen.dispatcher.lista_maestra_work_orders]
            self.almacen.dispatcher.initial_work_orders_snapshot = initial_snapshot
            print(f"[EVENT-GENERATOR] Snapshot inicial capturado: {len(initial_snapshot)} WorkOrders")
        
        # 10. Iniciar proceso del dispatcher
        if hasattr(self.almacen, 'dispatcher') and hasattr(self.almacen.dispatcher, 'dispatcher_process'):
            print("[EVENT-GENERATOR] Iniciando dispatcher...")
            self.env.process(self.almacen.dispatcher.dispatcher_process(self.operarios))
        
        print(f"[EVENT-GENERATOR] Simulacion creada:")
        print(f"  - {len(self.procesos_operarios)} operarios")
        print(f"  - {len(self.almacen.dispatcher.lista_maestra_work_orders)} WorkOrders")
        print(f"  - {self.almacen.total_ordenes} ordenes generadas")
        
        return True
    
    def ejecutar(self):
        """Ejecuta la simulacion y genera archivos de salida"""
        try:
            print("="*60)
            print("GENERADOR DE EVENTOS - GEMELO DIGITAL")
            print(f"Session: {self.session_timestamp}")
            print("Modo: Headless (sin UI)")
            print("="*60)
            
            # Crear simulacion
            if not self.crear_simulacion():
                print("[EVENT-GENERATOR ERROR] Fallo al crear simulacion")
                return False
            
            # Ejecutar simulacion SimPy pura
            print("[EVENT-GENERATOR] Ejecutando simulacion SimPy...")
            step_counter = 0
            
            while not self.almacen.simulacion_ha_terminado():
                try:
                    self.env.run(until=self.env.now + 1.0)
                    step_counter += 1
                    
                    # Log cada 100 pasos
                    if step_counter % 100 == 0:
                        stats = self.almacen.dispatcher.obtener_estadisticas()
                        print(f"[EVENT-GENERATOR] t={self.env.now:.1f}s | "
                              f"Completadas: {stats['completados']}/{stats['total']}")
                
                except simpy.core.EmptySchedule:
                    if self.almacen.simulacion_ha_terminado():
                        break
                    else:
                        print("[EVENT-GENERATOR WARNING] No hay eventos pero simulacion no termino")
                        break
            
            print(f"[EVENT-GENERATOR] Simulacion completada en t={self.env.now:.2f}s")
            
            # Exportar analytics
            print("[EVENT-GENERATOR] Exportando analytics...")
            context = SimulationContext.from_simulation_engine(self)
            analytics_exporter = AnalyticsExporter(context)
            export_result = analytics_exporter.export_complete_analytics()
            
            if not export_result.success:
                print(f"[EVENT-GENERATOR WARNING] Exportacion con errores: {len(export_result.errors)}")
            
            # Generar archivo .jsonl
            print("[EVENT-GENERATOR] Generando archivo .jsonl...")
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
            
            print(f"[EVENT-GENERATOR] Archivo generado: {output_file}")
            print(f"[EVENT-GENERATOR] Eventos capturados: {len(self.replay_buffer)}")
            
            # Exportar métricas de optimización si se solicitó
            if self.output_metrics_path:
                print("[EVENT-GENERATOR] Exportando métricas de optimización...")
                self.export_optimization_metrics(self.output_metrics_path)
                print(f"[EVENT-GENERATOR] Métricas exportadas: {self.output_metrics_path}")
            
            print("="*60)
            print("GENERACION COMPLETADA")
            print(f"Archivos en: {self.session_output_dir}")
            print("="*60)
            
            return True
        
        except KeyboardInterrupt:
            print("\n[EVENT-GENERATOR] Interrupcion del usuario")
            return False
        
        except Exception as e:
            print(f"[EVENT-GENERATOR ERROR] Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_optimization_metrics(self, output_path: str):
        """
        Exporta métricas clave para optimización automática.
        
        Genera un archivo JSON con métricas esenciales que el optimizador
        utilizará para calcular el score de la configuración actual.
        
        Args:
            output_path: Path completo donde guardar el archivo JSON de métricas
        """
        import json
        
        # Obtener estadísticas del dispatcher
        stats = self.almacen.dispatcher.obtener_estadisticas()
        
        # Calcular métricas derivadas
        total_completed = stats['completados']
        total_wo = stats['total']
        total_failed = total_wo - total_completed
        simulation_time = self.env.now
        
        # Calcular tiempo promedio de completación (si hay WOs completadas)
        avg_completion_time = simulation_time / max(total_completed, 1)
        
        # Extraer configuración de recursos
        ground_operators = self.configuracion.get('num_operarios_terrestres', 0)
        forklifts = self.configuracion.get('num_montacargas', 0)
        dispatch_strategy = self.configuracion.get('dispatch_strategy', 'unknown')
        
        # Construir objeto de métricas
        metrics = {
            "total_workorders_completed": total_completed,
            "total_workorders_failed": total_failed,
            "total_workorders": total_wo,
            "avg_completion_time_seconds": avg_completion_time,
            "total_simulation_time_seconds": simulation_time,
            "resource_costs": {
                "ground_operators": ground_operators,
                "forklifts": forklifts
            },
            "dispatch_strategy": dispatch_strategy,
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
