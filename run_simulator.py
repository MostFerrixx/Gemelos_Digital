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
from datetime import datetime

# Importaciones de módulos propios
from config.window_config import VentanaConfiguracion
from config.settings import *
from config.colors import *
from simulation.warehouse import AlmacenMejorado
from simulation.operators import crear_operarios
from simulation.layout_manager import LayoutManager

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
    
    def obtener_configuracion(self):
        """Obtiene la configuración del usuario"""
        print("Abriendo ventana de configuracion...")
        ventana_config = VentanaConfiguracion()
        config = ventana_config.obtener_configuracion()
        
        if config is None:
            print("Configuracion cancelada")
            return False
        
        self.configuracion = config
        print(f"Configuracion obtenida: {config}")
        print(f"[DEBUG-RUNNER] Configuración recibida: {self.configuracion}")
        return True
    
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
        
        print(f"[TMX] Arquitectura TMX inicializada exitosamente:")
        print(f"  - Dimensiones: {self.layout_manager.grid_width}x{self.layout_manager.grid_height}")
        print(f"  - Puntos de picking: {len(self.layout_manager.picking_points)}")
        print(f"  - Puntos de depot: {len(self.layout_manager.depot_points)}")
        
        self.env = simpy.Environment()
        
        # El LayoutManager y Pathfinder son OBLIGATORIOS
        if not self.layout_manager or not self.pathfinder:
            raise SystemExit("[FATAL ERROR] LayoutManager y Pathfinder son obligatorios")
        
        self.almacen = AlmacenMejorado(
            self.env,
            self.configuracion,
            layout_manager=self.layout_manager  # OBLIGATORIO
        )
        
        inicializar_estado(self.almacen, self.env, self.configuracion, layout_manager=self.layout_manager)
        
        # Diagnóstico del RouteCalculator
        self._diagnosticar_route_calculator()
        
        self.procesos_operarios = crear_operarios(
            self.env,
            self.almacen,
            self.configuracion,
            pathfinder=self.pathfinder,  # OBLIGATORIO
            layout_manager=self.layout_manager  # OBLIGATORIO
        )
        
        # FORZAR INICIALIZACIÓN DE OPERARIOS EN ESTADO VISUAL
        self._inicializar_operarios_en_estado_visual()
        
        self.env.process(self._proceso_actualizacion_metricas())
        
        print(f"Simulacion creada:")
        print(f"  - {len(self.procesos_operarios)} operarios")
        print(f"  - {len(self.almacen.dispatcher.lineas_pendientes)} líneas de orden pendientes")
        if hasattr(self.almacen, 'tareas_zona_a'):
            print(f"  - Zona A: {len(self.almacen.tareas_zona_a)} tareas")
            print(f"  - Zona B: {len(self.almacen.tareas_zona_b)} tareas")
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
            actualizar_metricas_tiempo()
    
    def ejecutar_bucle_principal(self):
        """Bucle principal completo con simulación y renderizado de agentes."""
        from visualization.original_renderer import renderizar_agentes, renderizar_dashboard
        from visualization.state import estado_visual, obtener_velocidad_simulacion
        
        self.corriendo = True
        while self.corriendo:
            # 1. Manejar eventos
            for event in pygame.event.get():
                if not self._manejar_evento(event):
                    self.corriendo = False

            # 2. Avance del motor de simulación SimPy
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
                else: # Si la simulación ha terminado
                    if not self.simulacion_finalizada_reportada:
                        print("[SIMULADOR] Condición de finalización cumplida: No hay tareas pendientes y todos los agentes están ociosos.")
                        print("Simulación completada y finalizada lógicamente.")
                        # La función de reporte ahora solo se llama UNA VEZ
                        self._simulacion_completada() 
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
            renderizar_dashboard(self.pantalla, self.window_size[0], self.almacen)

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
        return not self.almacen.simulacion_ha_terminado(self.procesos_operarios)
    
    def _simulacion_completada(self):
        """Maneja la finalización de la simulación"""
        print("\n" + "="*50)
        print("SIMULACION COMPLETADA")
        print("="*50)
        
        if self.almacen:
            mostrar_metricas_consola(self.almacen)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo = f"simulacion_completada_{timestamp}.json"
            exportar_metricas(self.almacen, archivo)
            print(f"Resultados guardados en: {archivo}")
        
        print("\nPresiona R para reiniciar o ESC para salir")
    
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
        if not self.layout_manager or not self.layout_manager.depot_points:
            raise SystemExit("[FATAL ERROR] Se requiere LayoutManager con depot_points para inicializar operarios")
        
        # Usar depot points del TMX como posiciones iniciales
        depot_point = self.layout_manager.depot_points[0]  # Primer punto de depot
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
        """Método de diagnóstico para el RouteCalculator"""
        print("\n--- DIAGNÓSTICO DEL CALCULADOR DE RUTAS ---")
        if not self.almacen or not self.almacen.dispatcher:
            print("El almacén o el dispatcher no están listos.")
            return

        # Tomar la posición inicial del primer depot como punto de partida
        start_pos = self.layout_manager.depot_points[0]
        print(f"Punto de partida para el diagnóstico: Depot en {start_pos}")

        # Tomar una muestra de las líneas de orden pendientes
        candidate_lines = self.almacen.dispatcher.lineas_pendientes[:20]
        print(f"Analizando las primeras {len(candidate_lines)} líneas de orden...")

        nearest_task_info = self.route_calculator.find_nearest_task(
            start_pos, 
            candidate_lines, 
            self.almacen.inventory_manager
        )

        if nearest_task_info:
            print("\n--- RESULTADO ---")
            print("¡Cálculo exitoso!")
            line = nearest_task_info['line']
            loc = nearest_task_info['location']
            dist = nearest_task_info['distance']
            print(f"La tarea más cercana es para la orden '{line.order_id}' (SKU: {line.sku.id}).")
            print(f"Ubicación óptima: {loc}")
            print(f"Distancia de ruta real: {dist} pasos.")
            
            # Mostrar estadísticas del caché
            cache_stats = self.route_calculator.get_cache_stats()
            print(f"Estadísticas del caché: {cache_stats}")
        else:
            print("\n--- RESULTADO ---")
            print("No se encontró ninguna tarea cercana accesible.")
        print("-------------------------------------------\n")
    
    def limpiar_recursos(self):
        """Limpia todos los recursos"""
        limpiar_estado()
        pygame.quit()
        print("Recursos liberados. Hasta luego!")
    
    def ejecutar(self):
        """Método principal de ejecución"""
        try:
            # NUEVO ORDEN: Configuración → TMX → Pygame
            if not self.obtener_configuracion():
                print("Configuracion cancelada. Saliendo...")
                return
            
            if not self.crear_simulacion():
                print("Error al crear la simulacion. Saliendo...")
                return
            
            # Inicializar pygame DESPUÉS de cargar TMX
            self.inicializar_pygame()
            
            self.ejecutar_bucle_principal()
            
        except KeyboardInterrupt:
            print("\nInterrupcion del usuario. Saliendo...")
        except Exception as e:
            print(f"Error inesperado: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.limpiar_recursos()
    
    # All unused debug methods removed in final cleanup
    

def main():
    """Función principal"""
    print("="*60)
    print("SIMULADOR DE ALMACEN - GEMELO DIGITAL")
    print("Sistema de Navegación Inteligente v2.0")
    print("Version Modular Refactorizada")
    print("="*60)
    print()
    
    simulador = SimuladorAlmacen()
    simulador.ejecutar()

if __name__ == "__main__":
    main()