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

# ARREGLO CRÍTICO: Aplicar patch ANTES de importar las clases renderer
try:
    exec(open('direct_layout_patch.py', encoding='utf-8').read())
    print("INFO: Patch TMX aplicado ANTES de imports")
except FileNotFoundError:
    print("Warning: Patch directo de layout no encontrado")

# ARREGLO WH1: Aplicar arreglo para selección correcta de WH1
try:
    exec(open('fix_wh1_selection.py', encoding='utf-8').read())
    print("INFO: Arreglo WH1 aplicado - Selección correcta habilitada")
except FileNotFoundError:
    print("Warning: Arreglo WH1 no encontrado")

# SISTEMA TMX UNIFICADO: Activar bounds checking
try:
    from universal_bounds_checker import install_bounds_checking
    bounds_checker = install_bounds_checking()
    print("INFO: Sistema de bounds checking universal instalado")
except ImportError:
    print("Warning: Sistema de bounds checking no disponible")

# FORZAR ACTIVACIÓN TMX: Asegurar que WH1 siempre se active
try:
    from force_tmx_activation import force_tmx_activation, patch_direct_layout_to_use_tmx
    
    # Activar TMX inmediatamente
    tmx_success = force_tmx_activation()
    visual_success = patch_direct_layout_to_use_tmx()
    
    if tmx_success and visual_success:
        print("INFO: TMX ACTIVADO EXITOSAMENTE - Operarios usarán bounds correctos")
        
        # ALINEAR COORDENADAS TMX: Sincronizar visual con pathfinding
        try:
            from align_tmx_coordinates import patch_coordinate_systems
            if patch_coordinate_systems():
                print("INFO: COORDENADAS TMX ALINEADAS - Visual sincronizado con pathfinding")
            else:
                print("WARNING: No se pudieron alinear coordenadas TMX")
        except ImportError:
            print("WARNING: Align TMX coordinates no disponible")
        
        # CORREGIR VISUAL TMX REAL: Mostrar layout verdadero, no patrón de test
        try:
            from fix_tmx_visual_real import fix_tmx_visual_rendering
            if fix_tmx_visual_rendering():
                print("INFO: VISUAL TMX REAL CORREGIDO - Mostrando layout WH1 verdadero")
            else:
                print("WARNING: No se pudo corregir visual TMX real")
        except ImportError:
            print("WARNING: Fix TMX visual real no disponible")
        
        # FORZAR TEXTURAS TMX: Desactivar sistema legacy y usar solo TMX
        try:
            from force_tmx_textures import force_tmx_texture_system
            if force_tmx_texture_system():
                print("INFO: SISTEMA DE TEXTURAS TMX FORZADO - Solo TMX visible")
            else:
                print("WARNING: No se pudo forzar sistema TMX")
        except ImportError:
            print("WARNING: Force TMX textures no disponible")
        
        # ARREGLAR LAYOUT DE PANTALLA: Optimizar dimensiones y viewport
        try:
            from fix_screen_layout import fix_screen_layout
            if fix_screen_layout():
                print("INFO: LAYOUT DE PANTALLA OPTIMIZADO - Todo debería ser visible")
            else:
                print("WARNING: No se pudo optimizar layout de pantalla")
        except ImportError:
            print("WARNING: Fix screen layout no disponible")
        
        # ARREGLO INTEGRAL: Layout selection y posicionamiento de operarios
        try:
            from fix_layout_selection_and_positioning import apply_comprehensive_fixes
            if apply_comprehensive_fixes():
                print("INFO: LAYOUT SELECTION Y POSICIONAMIENTO CORREGIDOS")
            else:
                print("WARNING: Algunos arreglos integrales fallaron")
        except ImportError:
            print("WARNING: Arreglos integrales no disponibles")
        
        # FORZAR INICIALIZACIÓN DE OPERARIOS: Asegurar que aparezcan en estado visual
        try:
            from force_operator_initialization import ensure_operators_visible
            ensure_operators_visible()
            print("INFO: OPERARIOS FORZADOS A ESTADO VISUAL")
        except ImportError:
            print("WARNING: Force operator initialization no disponible")
        
        # PATCHEAR RENDERIZADO DE OPERARIOS: Solución completa y definitiva
        try:
            from fix_operator_rendering_complete import force_patch_operator_rendering, fix_screen_dimensions
            
            # Aplicar patch de renderizado mejorado
            render_ok = force_patch_operator_rendering()
            
            if render_ok:
                print("INFO: RENDERIZADO OPERARIOS CORREGIDO - Función mejorada aplicada")
            else:
                print("WARNING: No se pudo aplicar renderizado mejorado")
                
        except ImportError:
            print("WARNING: Patch mejorado de renderizado no disponible")
    else:
        print("WARNING: TMX no se pudo activar completamente")
        
except ImportError:
    print("Warning: Forzar activación TMX no disponible")

# MONITOR EN TIEMPO REAL: Detectar violaciones de bounds
try:
    from realtime_bounds_monitor import start_realtime_monitoring
    print("INFO: Monitor bounds en tiempo real disponible")
except ImportError:
    print("Warning: Monitor bounds no disponible")

# Importaciones de módulos propios
from enhanced_config_window import EnhancedConfigWindow
from config.settings import *
from config.colors import *
from simulation.warehouse import AlmacenMejorado
from simulation.operators import crear_operarios
from visualization.state import inicializar_estado, actualizar_metricas_tiempo, toggle_pausa, toggle_dashboard, estado_visual, limpiar_estado, aumentar_velocidad, disminuir_velocidad, obtener_velocidad_simulacion
from visualization.original_renderer import RendererOriginal
from visualization.original_dashboard import DashboardOriginal
from utils.helpers import exportar_metricas, mostrar_metricas_consola
from dynamic_pathfinding_integration import get_dynamic_pathfinding_wrapper

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
        
    def inicializar_pygame(self):
        """Inicializa pygame y crea la ventana principal"""
        pygame.init()
        pygame.display.set_caption("Simulador de Almacen - Gemelo Digital (Modular)")
        
        self.pantalla = pygame.display.set_mode(
            (ANCHO_PANTALLA, ALTO_PANTALLA), 
            pygame.RESIZABLE
        )
        
        self.reloj = pygame.time.Clock()
        self.renderer = RendererOriginal(self.pantalla)
        self.dashboard = DashboardOriginal()
    
    def obtener_configuracion(self):
        """Obtiene la configuración del usuario"""
        print("Abriendo ventana de configuracion...")
        ventana_config = EnhancedConfigWindow()
        config = ventana_config.mostrar()
        
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
        
        # Configurar pathfinding dinámico si se usa layout personalizado
        if self.configuracion.get('use_dynamic_layout', False):
            layout_path = self.configuracion.get('selected_layout_path')
            if layout_path:
                print(f"[SIMULADOR] Configurando layout dinamico: {layout_path}")
                
                # INICIALIZAR SISTEMA TMX UNIFICADO
                try:
                    from dynamic_layout_loader import DynamicLayoutLoader
                    from tmx_coordinate_system import initialize_tmx_system
                    
                    loader = DynamicLayoutLoader("layouts")
                    layout_data = loader.load_layout(layout_path)
                    
                    if layout_data:
                        # Activar sistema TMX unificado
                        success = initialize_tmx_system(layout_data)
                        if success:
                            print("[TMX_SYSTEM] Sistema TMX unificado ACTIVADO")
                            print(f"[TMX_SYSTEM] Layout: {layout_data['info']['name']}")
                            print(f"[TMX_SYSTEM] Bounds: {layout_data['info']['width']}x{layout_data['info']['height']}")
                            print("[TMX_SYSTEM] Operarios respetarán límites TMX")
                        else:
                            print("[TMX_SYSTEM] Warning: No se pudo activar sistema TMX")
                    else:
                        print("[TMX_SYSTEM] Error: No se pudo cargar layout data")
                        
                except Exception as e:
                    print(f"[TMX_SYSTEM] Error: {e}")
                
                # Configurar pathfinding wrapper (mantener compatibilidad)
                wrapper = get_dynamic_pathfinding_wrapper()
                if wrapper.initialize_with_layout(layout_path):
                    print("[SIMULADOR] Layout dinamico configurado exitosamente para pathfinding")
                    print("[SIMULADOR] OPERARIOS USARAN SISTEMA TMX PARA MOVIMIENTO")
                else:
                    print("[SIMULADOR] Warning: No se pudo cargar layout dinamico, usando layout por defecto")
        else:
            print("[SIMULADOR] Usando layout por defecto (no TMX)")
        
        self.env = simpy.Environment()
        
        self.almacen = AlmacenMejorado(
            self.env,
            self.configuracion  # Pasar configuración completa
        )
        
        inicializar_estado(self.almacen, self.env, self.configuracion)
        
        procesos_operarios = crear_operarios(
            self.env,
            self.almacen,
            self.configuracion  # Pasar configuración completa
        )
        
        # FORZAR INICIALIZACIÓN DE OPERARIOS EN ESTADO VISUAL
        self._inicializar_operarios_en_estado_visual()
        
        self.env.process(self._proceso_actualizacion_metricas())
        
        print(f"Simulacion creada:")
        print(f"  - {len(procesos_operarios)} operarios")
        print(f"  - {self.almacen.total_tareas} tareas totales")
        print(f"  - Zona A: {len(self.almacen.tareas_zona_a)} tareas")
        print(f"  - Zona B: {len(self.almacen.tareas_zona_b)} tareas")
        if self.configuracion.get('use_dynamic_layout', False):
            print(f"  - Layout dinamico: {self.configuracion.get('selected_layout_path', 'N/A')}")
        return True
    
    def _proceso_actualizacion_metricas(self):
        """Proceso de actualización de métricas"""
        while True:
            yield self.env.timeout(INTERVALO_ACTUALIZACION_METRICAS)
            actualizar_metricas_tiempo()
    
    def ejecutar_bucle_principal(self):
        """Ejecuta el bucle principal de la simulación"""
        print("\nIniciando simulacion...")
        
        # INICIAR MONITOR EN TIEMPO REAL
        try:
            from realtime_bounds_monitor import start_realtime_monitoring
            if start_realtime_monitoring():
                print("INFO: Monitor de bounds en tiempo real iniciado")
            else:
                print("Warning: No se pudo iniciar monitor de bounds")
        except ImportError:
            print("Warning: Monitor de bounds no disponible")
        print("Controles disponibles:")
        print("  ESPACIO: Pausa/Reanuda")
        print("  R: Reiniciar")
        print("  M: Mostrar metricas")
        print("  X: Exportar datos")
        print("  D: Toggle dashboard")
        print("  N: Diagnostico navegacion")
        print("  C: Diagnostico colisiones")
        print("  P: Diagnostico pasillos")
        print("  K: Diagnostico deadlocks")
        print("  V: Reporte violaciones bounds")
        print("  F1: Debug navegacion")
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
            elif evento.key == pygame.K_n:  # N para diagnóstico de navegación
                self._diagnosticar_navegacion()
            elif evento.key == pygame.K_c:  # C para diagnóstico de colisiones
                self._diagnosticar_colisiones()
            elif evento.key == pygame.K_F1:  # F1 para activar debug
                self._toggle_debug_navegacion()
            elif evento.key == pygame.K_p:  # P para diagnóstico de pasillos
                self._diagnosticar_pasillos()
            elif evento.key == pygame.K_k:  # K para diagnóstico de deadlocks
                self._diagnosticar_deadlocks()
            elif evento.key == pygame.K_v:  # V para reporte de violaciones de bounds
                self._mostrar_reporte_violaciones()
        
        return True
    
    def _renderizar_frame(self):
        """Renderiza un frame completo"""
        self.renderer.renderizar_frame_completo()
        
        if self.dashboard.visible and self.almacen and self.env:
            self.dashboard.actualizar_datos(self.env, self.almacen)
            self.dashboard.renderizar(self.pantalla, self.almacen)
        
        self.renderer.dibujar_mensaje_pausa()
        pygame.display.flip()
    
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
        """Forzar inicialización de operarios en estado visual"""
        from visualization.state import estado_visual
        from config.settings import POS_DEPOT
        
        if not self.configuracion:
            return
            
        num_terrestres = self.configuracion.get('num_operarios_terrestres', 0)
        num_montacargas = self.configuracion.get('num_montacargas', 0)
        
        print(f"Inicializando {num_terrestres} operarios terrestres y {num_montacargas} montacargas en estado visual...")
        
        # Limpiar operarios existentes
        estado_visual["operarios"] = {}
        
        # Crear operarios terrestres
        for i in range(1, num_terrestres + 1):
            x = POS_DEPOT[0] - (i * 40)  # Espaciados horizontalmente
            y = POS_DEPOT[1]
            
            estado_visual["operarios"][i] = {
                'x': x,
                'y': y,
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'terrestre'
            }
        
        # Crear montacargas
        for i in range(num_terrestres + 1, num_terrestres + num_montacargas + 1):
            x = POS_DEPOT[0] - ((i - num_terrestres) * 40)
            y = POS_DEPOT[1] + 60  # Más abajo que los terrestres
            
            estado_visual["operarios"][i] = {
                'x': x,
                'y': y,
                'accion': 'En Estacionamiento',
                'tareas_completadas': 0,
                'direccion_x': 0,
                'direccion_y': 0,
                'tipo': 'montacargas'
            }
        
        total_operarios = len(estado_visual["operarios"])
        print(f"Operarios inicializados en estado visual: {total_operarios}")
        
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
            self.inicializar_pygame()
            
            if not self.obtener_configuracion():
                print("Configuracion cancelada. Saliendo...")
                return
            
            if not self.crear_simulacion():
                print("Error al crear la simulacion. Saliendo...")
                return
            
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