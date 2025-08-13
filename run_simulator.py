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
from visualization.state import inicializar_estado, actualizar_metricas_tiempo, toggle_pausa, toggle_dashboard, estado_visual, limpiar_estado, aumentar_velocidad, disminuir_velocidad, obtener_velocidad_simulacion
from visualization.original_renderer import RendererOriginal
from visualization.original_dashboard import DashboardOriginal
from utils.helpers import exportar_metricas, mostrar_metricas_consola

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
        
        self.env.process(self._proceso_actualizacion_metricas())
        
        print(f"Simulacion creada:")
        print(f"  - {len(procesos_operarios)} operarios")
        print(f"  - {self.almacen.total_tareas} tareas totales")
        print(f"  - Zona A: {len(self.almacen.tareas_zona_a)} tareas")
        print(f"  - Zona B: {len(self.almacen.tareas_zona_b)} tareas")
        return True
    
    def _proceso_actualizacion_metricas(self):
        """Proceso de actualización de métricas"""
        while True:
            yield self.env.timeout(INTERVALO_ACTUALIZACION_METRICAS)
            actualizar_metricas_tiempo()
    
    def ejecutar_bucle_principal(self):
        """Ejecuta el bucle principal de la simulación"""
        print("\nIniciando simulacion...")
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