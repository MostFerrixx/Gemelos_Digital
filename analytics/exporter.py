# -*- coding: utf-8 -*-
"""
AnalyticsExporter - Modulo extraido de SimulationEngine para generacion de reportes.
Refactorizado desde SimulationEngine._simulacion_completada() y metodos relacionados.
Maneja toda la logica de exportacion de analiticas al final de la simulacion.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from analytics_engine import AnalyticsEngine
from src.subsystems.utils.helpers import exportar_metricas, mostrar_metricas_consola


class AnalyticsExporter:
    """
    Gestor centralizado para exportacion de analiticas y reportes de simulacion.

    Extrae toda la logica de generacion de reportes desde SimulationEngine,
    manteniendo funcionalidad identica con arquitectura mas modular.
    """

    def __init__(self, almacen, configuracion, session_timestamp=None, session_output_dir=None):
        """
        Inicializa AnalyticsExporter con datos de simulacion.

        Args:
            almacen: Objeto AlmacenMejorado con datos de simulacion
            configuracion: Dict de configuracion de la simulacion
            session_timestamp: Timestamp de sesion (opcional)
            session_output_dir: Directorio de salida de sesion (opcional)
        """
        self.almacen = almacen
        self.configuracion = configuracion
        self.session_timestamp = session_timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_output_dir = session_output_dir

        print(f"[ANALYTICS-EXPORTER] Inicializado para exportar analiticas de simulacion")
        print(f"[ANALYTICS-EXPORTER] Session timestamp: {self.session_timestamp}")

    def export_complete_analytics(self):
        """
        Pipeline completo de exportacion de analiticas - Extraido de _simulacion_completada()

        Replica exactamente la funcionalidad de SimulationEngine._simulacion_completada()
        con la misma secuencia de pasos y manejo de errores.
        """
        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS")
        print("="*70)

        if not self.almacen:
            print("Error: No hay datos del almacen para procesar")
            return []

        # Mostrar metricas basicas
        mostrar_metricas_consola(self.almacen)

        timestamp = self.session_timestamp

        # Crear estructura de directorios organizados
        if self.session_output_dir:
            output_dir = self.session_output_dir
        else:
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

        # 2. Exportar eventos crudos
        archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
        if archivo_eventos:
            archivos_generados.append(archivo_eventos)
            print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")

        # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine -> Excel
        print("[3/4] Simulacion completada. Generando reporte de Excel...")
        try:
            # Usar el metodo __init__ original con eventos y configuracion en memoria
            analytics_engine = AnalyticsEngine(self.almacen.event_log, self.configuracion)
            analytics_engine.process_events()

            # Generar archivo Excel con ruta organizada
            excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
            archivo_excel = analytics_engine.export_to_excel(excel_filename)

            # Generar archivo JSON con la misma información
            json_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.json")
            archivo_json = analytics_engine.export_to_json(json_filename)

            if archivo_excel:
                archivos_generados.append(archivo_excel)
                print(f"[3/4] Reporte de Excel generado: {archivo_excel}")
            
            if archivo_json:
                archivos_generados.append(archivo_json)
                print(f"[3/4] Reporte de JSON generado: {archivo_json}")

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

        return archivos_generados

    def export_complete_analytics_with_buffer(self, buffer_eventos=None):
        """
        Pipeline completo con buffer especifico - Extraido de _simulacion_completada_con_buffer()

        Replica exactamente la funcionalidad de SimulationEngine._simulacion_completada_con_buffer()
        manteniendo el manejo de unified timestamp logic.

        Args:
            buffer_eventos: Buffer de eventos especifico (no usado actualmente)
        """
        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS")
        print("="*70)

        if not self.almacen:
            print("Error: No hay datos del almacen para procesar")
            return []

        # Mostrar metricas basicas
        mostrar_metricas_consola(self.almacen)

        # UNIFIED: Use session timestamp instead of generating new one
        timestamp = self.session_timestamp
        output_dir = self.session_output_dir or os.path.join("output", f"simulation_{timestamp}")

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

        # 2. Exportar eventos crudos
        archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
        if archivo_eventos:
            archivos_generados.append(archivo_eventos)
            print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")

        # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine -> Excel
        print("[3/4] Simulacion completada. Generando reporte de Excel...")
        try:
            # Usar el metodo __init__ original con eventos y configuracion en memoria
            analytics_engine = AnalyticsEngine(self.almacen.event_log, self.configuracion)
            analytics_engine.process_events()

            # Generar archivo Excel con ruta organizada
            excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
            archivo_excel = analytics_engine.export_to_excel(excel_filename)

            # Generar archivo JSON con la misma información
            json_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.json")
            archivo_json = analytics_engine.export_to_json(json_filename)

            if archivo_excel:
                archivos_generados.append(archivo_excel)
                print(f"[3/4] Reporte de Excel generado: {archivo_excel}")
            
            if archivo_json:
                archivos_generados.append(archivo_json)
                print(f"[3/4] Reporte de JSON generado: {archivo_json}")

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

        return archivos_generados

    def _exportar_eventos_crudos_organizado(self, output_dir: str, timestamp: str):
        """
        Exporta eventos crudos a directorio organizado.

        Extraido de SimulationEngine._exportar_eventos_crudos_organizado()
        manteniendo funcionalidad identica.

        Args:
            output_dir: Directorio de salida
            timestamp: Timestamp para nombre de archivo

        Returns:
            str: Path del archivo generado o None si falla
        """
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
        """
        Ejecuta visualizer.py automaticamente usando subprocess.

        Extraido de SimulationEngine._ejecutar_visualizador()
        manteniendo funcionalidad identica.

        Args:
            excel_path: Path del archivo Excel de entrada
            timestamp: Timestamp para nombre de archivo de salida
            output_dir: Directorio de salida
        """
        try:
            # Construir rutas dinamicamente
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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