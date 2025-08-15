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

print("=" * 70)
print("SIMULADOR DE ALMACEN - SISTEMA CORE LIMPIO")
print("=" * 70)

# Importaciones de módulos propios
from config.window_config import VentanaConfiguracion
from config.settings import *
from config.colors import *
from simulation.warehouse import AlmacenMejorado
from simulation.operators import crear_operarios
from simulation.layout_manager import LayoutManager

# VERIFICACIÓN DE ENTORNO: Confirmar que cargamos el LayoutManager correcto
print(f"[ENTORNO] Cargando LayoutManager desde: {LayoutManager.__module__}")
try:
    import simulation.layout_manager
    print(f"[ENTORNO] Archivo LayoutManager: {simulation.layout_manager.__file__}")
except AttributeError:
    print(f"[ENTORNO] No se pudo obtener ruta del archivo LayoutManager")
from simulation.pathfinder import Pathfinder
from visualization.state import inicializar_estado, actualizar_metricas_tiempo, toggle_pausa, toggle_dashboard, estado_visual, limpiar_estado, aumentar_velocidad, disminuir_velocidad, obtener_velocidad_simulacion
from visualization.original_renderer import RendererOriginal
from visualization.original_dashboard import DashboardOriginal
from utils.helpers import exportar_metricas, mostrar_metricas_consola
# from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper  # Eliminado en limpieza

print("INFO: Sistema TMX Visual activado")

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
        
    def inicializar_pygame(self):
        """Reinicializa pygame con dimensiones TMX exactas (ya inicializado en crear_simulacion)"""
        pygame.display.set_caption("Simulador de Almacen - Gemelo Digital (TMX)")
        
        # IMPORTANTE: Este método se llama DESPUÉS de crear_simulacion()
        # para que ya tengamos el layout_manager disponible
        if not hasattr(self, 'layout_manager') or not self.layout_manager:
            raise SystemExit("[FATAL ERROR] Debe cargar TMX antes de reinicializar pygame")
        
        # Calcular dimensiones exactas del mapa TMX
        map_width = self.layout_manager.grid_width * self.layout_manager.tile_width
        map_height = self.layout_manager.grid_height * self.layout_manager.tile_height
        
        print(f"[TMX WINDOW] Dimensiones calculadas desde TMX:")
        print(f"  - Grilla: {self.layout_manager.grid_width}x{self.layout_manager.grid_height}")
        print(f"  - Tile size: {self.layout_manager.tile_width}x{self.layout_manager.tile_height}")
        print(f"  - Tamaño ventana: {map_width}x{map_height} (correspondencia 1:1)")
        
        # Crear ventana con dimensiones exactas del TMX (correspondencia 1:1)
        self.pantalla = pygame.display.set_mode((map_width, map_height))
        
        print(f"[TMX WINDOW] Ventana creada: {map_width}x{map_height} píxeles")
        print(f"[TMX WINDOW] Sin escalado - correspondencia 1:1 píxel TMX : píxel pantalla")
        
        self.reloj = pygame.time.Clock()
        self.renderer = RendererOriginal(self.pantalla)
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
        tmx_file = "C:\\Users\\ferri\\OneDrive\\Escritorio\\Gemelos Digital\\layouts\\WH1.tmx"
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
        
        procesos_operarios = crear_operarios(
            self.env,
            self.almacen,
            self.configuracion,
            pathfinder=self.pathfinder  # OBLIGATORIO
        )
        
        # FORZAR INICIALIZACIÓN DE OPERARIOS EN ESTADO VISUAL
        self._inicializar_operarios_en_estado_visual()
        
        self.env.process(self._proceso_actualizacion_metricas())
        
        print(f"Simulacion creada:")
        print(f"  - {len(procesos_operarios)} operarios")
        print(f"  - {self.almacen.total_tareas} tareas totales")
        if hasattr(self.almacen, 'tareas_zona_a'):
            print(f"  - Zona A: {len(self.almacen.tareas_zona_a)} tareas")
            print(f"  - Zona B: {len(self.almacen.tareas_zona_b)} tareas")
        if self.layout_manager:
            print(f"  - Layout TMX: ACTIVO ({tmx_file})")
        else:
            print(f"  - Layout TMX: DESACTIVADO (usando legacy)")
        return True
    
    def _proceso_actualizacion_metricas(self):
        """Proceso de actualización de métricas"""
        while True:
            yield self.env.timeout(INTERVALO_ACTUALIZACION_METRICAS)
            actualizar_metricas_tiempo()
    
    def ejecutar_bucle_principal(self):
        """Ejecuta el bucle principal de la simulación"""
        print("\nIniciando simulacion...")
        
        # Monitor de bounds desactivado en limpieza
        print("Controles disponibles:")
        print("  ESPACIO: Pausa/Reanuda")
        print("  R: Reiniciar")
        print("  M: Mostrar metricas")
        print("  X: Exportar datos")
        print("  D: Toggle dashboard")
        print("  +: Aumentar velocidad")
        print("  -: Disminuir velocidad")
        print("  ESC: Salir")
        print()
        
        while self.corriendo:
            for evento in pygame.event.get():
                if not self._manejar_evento(evento):
                    return False
            
            if not estado_visual["pausa"] and self._simulacion_activa():
                try:
                    # Aplicar factor de velocidad al paso de simulación
                    velocidad = obtener_velocidad_simulacion()
                    paso_ajustado = STEP_SIMULACION * velocidad
                    self.env.run(until=self.env.now + paso_ajustado)
                except simpy.core.EmptySchedule:
                    print("Simulacion completada!")
                    self._simulacion_completada()
            
            self._renderizar_frame()
            self.reloj.tick(FPS)
        
        return True
    
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
            self.renderer.renderizar_operarios_solamente()
        else:
            # Sistema legacy
            self.renderer.renderizar_frame_completo()
        
        if self.dashboard.visible and self.almacen and self.env:
            self.dashboard.actualizar_datos(self.env, self.almacen)
            self.dashboard.renderizar(self.pantalla, self.almacen)
        
        self.renderer.dibujar_mensaje_pausa()
        pygame.display.flip()
    
    def _renderizar_tmx_escalado(self):
        """Renderiza el mapa TMX aplicando escalado para la ventana actual"""
        if not self.layout_manager:
            return
        
        from config.settings import ANCHO_PANTALLA, ALTO_PANTALLA
        
        # Calcular factores de escala
        ancho_ventana, alto_ventana = self.pantalla.get_size()
        factor_x = ancho_ventana / ANCHO_PANTALLA
        factor_y = alto_ventana / ALTO_PANTALLA
        
        # Crear superficie temporal con tamaño lógico
        temp_surface = pygame.Surface((ANCHO_PANTALLA, ALTO_PANTALLA))
        
        # Renderizar TMX en superficie temporal
        self.layout_manager.render(temp_surface)
        
        # Escalar y dibujar en pantalla principal
        scaled_surface = pygame.transform.scale(temp_surface, (ancho_ventana, alto_ventana))
        self.pantalla.blit(scaled_surface, (0, 0))
    
    def _simulacion_activa(self):
        """Verifica si la simulación está activa"""
        return (self.almacen is not None and 
                self.env is not None and 
                self.almacen.hay_tareas_pendientes())
    
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
    
    def _diagnosticar_navegacion(self):
        """Diagnóstico del sistema de navegación"""
        try:
            from utils.strict_lane_system import sistema_carriles_estricto
            
            if sistema_carriles_estricto:
                estadisticas = sistema_carriles_estricto.obtener_estadisticas_carriles()
                
                print("\n" + "="*40)
                print("=== DIAGNÓSTICO DE NAVEGACIÓN ===")
                print("="*40)
                print(f"Puntos válidos totales: {estadisticas['total_puntos_validos']}")
                print(f"Conexiones totales: {estadisticas['total_conexiones']}")
                print(f"Puntos actualmente ocupados: {estadisticas['puntos_ocupados']}")
                print(f"Operarios activos: {estadisticas['operarios_activos']}")
                print()
                
                if estadisticas['puntos_ocupados'] > estadisticas['operarios_activos'] * 2:
                    print("[ALERTA] POSIBLE CONGESTIÓN DETECTADA")
                else:
                    print("[OK] No se detectó congestión")
                
                # Mostrar posiciones de operarios
                from visualization.state import estado_visual
                print("\nPOSICIONES DE OPERARIOS:")
                for op_id, operario in estado_visual.get("operarios", {}).items():
                    x, y = operario.get('x', 0), operario.get('y', 0)
                    tipo = operario.get('tipo', 'desconocido')
                    accion = operario.get('accion', 'Sin acción')
                    print(f"  Operario {op_id} ({tipo}): ({x}, {y}) - {accion}")
                
                print("="*40)
            else:
                print("[ERROR] Sistema de carriles no disponible")
        except Exception as e:
            print(f"[ERROR] Error en diagnóstico de navegación: {e}")
    
    def _diagnosticar_colisiones(self):
        """Diagnóstico del sistema de colisiones"""
        try:
            from utils.strict_lane_system import sistema_carriles_estricto
            from utils.strict_lane_system import diagnosticar_colisiones
            
            print("\n" + "="*40)
            print("=== DIAGNÓSTICO DE COLISIONES ===")
            print("="*40)
            
            reporte = diagnosticar_colisiones()
            if reporte:
                print("[OK] Diagnóstico completado")
            else:
                print("[ERROR] No se pudo generar el diagnóstico")
            
            print("="*40)
        except Exception as e:
            print(f"[ERROR] Error en diagnóstico de colisiones: {e}")
    
    def _diagnosticar_pasillos(self):
        """Diagnóstico específico de pasillos verticales"""
        try:
            import time
            from utils.strict_lane_system import sistema_carriles_estricto
            
            print("\n" + "="*50)
            print("=== DIAGNÓSTICO DE PASILLOS VERTICALES ===")
            print("="*50)
            
            if sistema_carriles_estricto:
                total_pasillos = len(sistema_carriles_estricto.pasillos_verticales)
                pasillos_ocupados = len(sistema_carriles_estricto.pasillos_ocupados)
                operarios_picking = len(sistema_carriles_estricto.operarios_en_picking)
                
                print(f"\n[PASILLOS] PASILLOS VERTICALES:")
                print(f"  Total pasillos: {total_pasillos}")
                print(f"  Pasillos ocupados: {pasillos_ocupados}")
                print(f"  Operarios en picking: {operarios_picking}")
                
                if pasillos_ocupados > 0:
                    print(f"\n[OCUPADOS] PASILLOS OCUPADOS:")
                    for columna, operario_id in sistema_carriles_estricto.pasillos_ocupados.items():
                        if operario_id in sistema_carriles_estricto.operarios_en_picking:
                            picking_info = sistema_carriles_estricto.operarios_en_picking[operario_id]
                            tiempo_picking = time.time() - picking_info['tiempo_inicio']
                            print(f"  Pasillo {columna}: Operario {operario_id} (picking {tiempo_picking:.1f}s)")
                        else:
                            print(f"  Pasillo {columna}: Operario {operario_id}")
                
                print(f"\n[ANALISIS] ANÁLISIS DE CONFLICTOS:")
                conflictos = 0
                for columna in range(total_pasillos):
                    if columna in sistema_carriles_estricto.pasillos_ocupados:
                        # Verificar si hay operarios esperando para entrar
                        from visualization.state import estado_visual
                        for op_id, operario in estado_visual.get("operarios", {}).items():
                            if operario.get('accion', '').startswith(f'Esperando pasillo {columna}'):
                                conflictos += 1
                
                if conflictos == 0:
                    print("  [OK] No se detectaron conflictos")
                else:
                    print(f"  [ALERTA] {conflictos} conflictos detectados")
                
                print(f"\n[RECOMENDACIONES] RECOMENDACIONES:")
                if pasillos_ocupados / total_pasillos > 0.5:
                    print("  [ALERTA] Alta ocupación de pasillos - considerar optimización")
                else:
                    print("  [OK] Sistema funcionando óptimamente")
                
            else:
                print("[ERROR] Sistema de carriles no disponible")
            
            print("="*50)
            
        except Exception as e:
            print(f"[ERROR] Error en diagnóstico de pasillos: {e}")
            import traceback
            traceback.print_exc()
    
    def _toggle_debug_navegacion(self):
        """Activa/desactiva el modo debug de navegación"""
        print("[INFO] Función toggle debug no implementada actualmente")
    
    def _diagnosticar_deadlocks(self):
        """Diagnóstico del sistema de deadlocks y negociación"""
        try:
            from utils.deadlock_resolver import obtener_diagnostico_deadlocks
            
            print("\n" + "="*50)
            print("=== DIAGNÓSTICO DE DEADLOCKS Y NEGOCIACIÓN ===")
            print("="*50)
            
            diagnostico = obtener_diagnostico_deadlocks()
            
            print(f"Operarios en espera: {diagnostico['operarios_esperando']}")
            print(f"Operarios cediendo paso: {diagnostico['operarios_cediendo_paso']}")
            print(f"Tiempo máximo de espera: {diagnostico['tiempo_espera_max']:.1f}s")
            
            if diagnostico['operarios_esperando'] == 0:
                print("[OK] No hay operarios esperando")
            elif diagnostico['tiempo_espera_max'] > 10.0:
                print(f"[ALERTA] Tiempo de espera muy alto ({diagnostico['tiempo_espera_max']:.1f}s)")
            
            if diagnostico['operarios_cediendo_paso'] > 0:
                print(f"[COOPERACION] {diagnostico['operarios_cediendo_paso']} operarios cediendo paso")
            
            print("="*50)
            
        except Exception as e:
            print(f"[ERROR] Error en diagnóstico de deadlocks: {e}")
            import traceback
            traceback.print_exc()
    
    def _mostrar_reporte_violaciones(self):
        """Mostrar reporte de violaciones de bounds detectadas"""
        try:
            from realtime_bounds_monitor import get_violations_report
            
            print("\n" + "="*60)
            print("=== REPORTE VIOLACIONES DE BOUNDS ===")
            print("="*60)
            
            report = get_violations_report()
            
            if report['total_violations'] == 0:
                print("[OK] NO SE DETECTARON VIOLACIONES DE BOUNDS")
                print("Los operarios han permanecido dentro del layout")
            else:
                print(f"[ALERT] {report['total_violations']} VIOLACIONES DETECTADAS")
                
                if 'by_operator' in report:
                    print("\nViolaciones por operario:")
                    for op_id, count in report['by_operator'].items():
                        print(f"  Operario {op_id}: {count} violaciones")
                
                if 'violation_types' in report:
                    print("\nTipos de violaciones:")
                    for v_type, count in report['violation_types'].items():
                        print(f"  {v_type}: {count} veces")
                
                if 'first_violation' in report and report['first_violation']:
                    first = report['first_violation']
                    print(f"\nPrimera violación:")
                    print(f"  Operario: {first['operario_id']}")
                    print(f"  Posición: ({first['position'][0]:.1f}, {first['position'][1]:.1f})")
                    print(f"  Acción: {first['accion']}")
                    print(f"  Tipo: {first['violation_type']}")
                
                if 'last_violation' in report and report['last_violation']:
                    last = report['last_violation']
                    print(f"\nÚltima violación:")
                    print(f"  Operario: {last['operario_id']}")
                    print(f"  Posición: ({last['position'][0]:.1f}, {last['position'][1]:.1f})")
                    print(f"  Acción: {last['accion']}")
                    print(f"  Tipo: {last['violation_type']}")
            
            # Mostrar estado TMX actual
            from tmx_coordinate_system import tmx_coords
            if tmx_coords.is_tmx_active():
                bounds = tmx_coords.get_bounds()
                print(f"\nBounds TMX activos: 0-{bounds['max_x']} x 0-{bounds['max_y']}")
            else:
                print("\n[WARNING] Sistema TMX no activo")
            
            print("="*60)
            
        except Exception as e:
            print(f"[ERROR] Error obteniendo reporte de violaciones: {e}")
    

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