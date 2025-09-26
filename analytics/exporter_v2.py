# -*- coding: utf-8 -*-
"""
AnalyticsExporter V2 - Version mejorada con arquitectura robusta.
Fase 2 del refactor - Implementa SimulationContext y ExportResult patterns.
Mantiene compatibilidad con funcionalidad existente mientras mejora robustez.
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from typing import Optional

from analytics_engine import AnalyticsEngine
from utils.helpers import exportar_metricas, mostrar_metricas_consola
from .context import SimulationContext, ExportResult


class AnalyticsExporter:
    """
    Gestor robusto para exportacion de analiticas y reportes de simulacion.

    Version 2.0 con mejoras arquitectonicas:
    - SimulationContext para encapsulacion de datos
    - ExportResult para manejo estructurado de resultados
    - Rollback automatico en caso de fallo
    - Logging y debugging mejorado
    """

    def __init__(self, simulation_context: SimulationContext):
        """
        Inicializa AnalyticsExporter con contexto de simulacion.

        Args:
            simulation_context: Contexto unificado con todos los datos necesarios
        """
        # Validar contexto
        simulation_context.validate()

        self.context = simulation_context

        print(f"[ANALYTICS-EXPORTER V2] Inicializado con contexto de simulacion")
        print(f"[ANALYTICS-EXPORTER V2] Session: {self.context.session_timestamp}")
        print(f"[ANALYTICS-EXPORTER V2] Output: {self.context.session_output_dir}")

    @classmethod
    def from_legacy_params(cls, almacen, configuracion, session_timestamp=None, session_output_dir=None):
        """
        Factory method para compatibilidad con API legacy.

        Permite usar AnalyticsExporter V2 con parametros del V1.

        Args:
            almacen: Objeto AlmacenMejorado
            configuracion: Dict de configuracion
            session_timestamp: Timestamp de sesion (opcional)
            session_output_dir: Directorio de salida (opcional)

        Returns:
            AnalyticsExporter: Instancia configurada con contexto
        """
        context = SimulationContext(
            almacen=almacen,
            configuracion=configuracion,
            session_timestamp=session_timestamp,
            session_output_dir=session_output_dir
        )
        return cls(context)

    def export_complete_analytics(self) -> ExportResult:
        """
        Pipeline completo de exportacion de analiticas con manejo robusto.

        Mejoras sobre V1:
        - Retorna ExportResult estructurado
        - Rollback automatico en caso de fallo
        - Timing automatico de ejecucion
        - Error handling mejorado

        Returns:
            ExportResult: Resultado detallado de la exportacion
        """
        start_time = time.time()
        result = ExportResult()

        # Configurar metadatos de exportacion
        result.export_metadata = self.context.get_export_metadata()
        result.rollback_info['output_dir'] = self.context.session_output_dir

        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS V2")
        print("="*70)

        if not self.context.almacen:
            result.add_error("No hay datos del almacen para procesar")
            return result

        try:
            # Mostrar metricas basicas
            mostrar_metricas_consola(self.context.almacen)

            # Crear estructura de directorios organizados
            output_dir = self.context.session_output_dir
            timestamp = self.context.session_timestamp

            try:
                os.makedirs(output_dir, exist_ok=True)
                print(f"[SETUP] Directorio de salida creado: {output_dir}")
            except Exception as e:
                result.add_warning(f"No se pudo crear directorio de salida: {e}")
                # Fallback: usar directorio actual
                output_dir = "."
                result.rollback_info['output_dir'] = output_dir

            # 1. Exportar metricas JSON basicas
            try:
                archivo_json = os.path.join(output_dir, f"simulacion_completada_{timestamp}.json")
                exportar_metricas(self.context.almacen, archivo_json)
                result.add_file(archivo_json)
                print(f"[1/4] Metricas JSON guardadas: {archivo_json}")
            except Exception as e:
                result.add_error(f"Error exportando metricas JSON: {e}")

            # 2. Exportar eventos crudos
            try:
                archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
                if archivo_eventos:
                    result.add_file(archivo_eventos)
                    print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")
                else:
                    result.add_warning("No se pudieron exportar eventos crudos")
            except Exception as e:
                result.add_error(f"Error exportando eventos crudos: {e}")

            # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine -> Excel
            print("[3/4] Simulacion completada. Generando reporte de Excel...")
            try:
                # Usar el metodo __init__ original con eventos y configuracion en memoria
                analytics_engine = AnalyticsEngine(self.context.event_log, self.context.configuracion)
                analytics_engine.process_events()

                # Generar archivo Excel con ruta organizada
                excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
                archivo_excel = analytics_engine.export_to_excel(excel_filename)

                if archivo_excel:
                    result.add_file(archivo_excel)
                    print(f"[3/4] Reporte de Excel generado: {archivo_excel}")

                    # 4. PIPELINE AUTOMATIZADO: Visualizer -> PNG
                    print("[4/4] Reporte de Excel generado. Creando imagen de heatmap...")
                    try:
                        png_file = self._ejecutar_visualizador(archivo_excel, timestamp, output_dir)
                        if png_file:
                            result.add_file(png_file)
                    except Exception as e:
                        result.add_warning(f"Error generando heatmap PNG: {e}")

                else:
                    result.add_error("No se pudo generar el reporte de Excel")

            except Exception as e:
                result.add_error(f"Error en pipeline de analiticas: {e}")

            # Timing final
            end_time = time.time()
            result.set_execution_time(start_time, end_time)

            # Resumen final
            print("\n" + "="*70)
            print("PROCESO COMPLETADO V2")
            print("="*70)
            print(result.get_summary())
            print("="*70)

            return result

        except Exception as e:
            # Error critico - rollback automatico
            result.add_error(f"Error critico en exportacion: {e}")
            result.set_execution_time(start_time, time.time())

            print(f"[ROLLBACK] Error critico detectado: {e}")
            if result.rollback_on_failure():
                print("[ROLLBACK] Rollback completado exitosamente")
            else:
                print("[ROLLBACK] Rollback tuvo problemas - verificar manualmente")

            return result

    def export_complete_analytics_with_buffer(self, buffer_eventos=None) -> ExportResult:
        """
        Pipeline completo con buffer especifico - Version mejorada con ExportResult.

        Args:
            buffer_eventos: Buffer de eventos especifico (heredado de V1, no usado)

        Returns:
            ExportResult: Resultado detallado de la exportacion
        """
        start_time = time.time()
        result = ExportResult()

        # Configurar metadatos
        result.export_metadata = self.context.get_export_metadata()
        result.export_metadata['buffer_mode'] = True
        result.rollback_info['output_dir'] = self.context.session_output_dir

        print("\n" + "="*70)
        print("SIMULACION COMPLETADA - INICIANDO PIPELINE DE ANALITICAS V2 (WITH BUFFER)")
        print("="*70)

        if not self.context.almacen:
            result.add_error("No hay datos del almacen para procesar")
            return result

        try:
            # Mostrar metricas basicas
            mostrar_metricas_consola(self.context.almacen)

            # UNIFIED: Use session timestamp and output dir from context
            timestamp = self.context.session_timestamp
            output_dir = self.context.session_output_dir

            try:
                os.makedirs(output_dir, exist_ok=True)
                print(f"[SETUP] Directorio de salida creado: {output_dir}")
            except Exception as e:
                result.add_warning(f"No se pudo crear directorio de salida: {e}")
                output_dir = "."
                result.rollback_info['output_dir'] = output_dir

            # Mismo pipeline que export_complete_analytics
            # 1. Exportar metricas JSON basicas
            try:
                archivo_json = os.path.join(output_dir, f"simulacion_completada_{timestamp}.json")
                exportar_metricas(self.context.almacen, archivo_json)
                result.add_file(archivo_json)
                print(f"[1/4] Metricas JSON guardadas: {archivo_json}")
            except Exception as e:
                result.add_error(f"Error exportando metricas JSON: {e}")

            # 2. Exportar eventos crudos
            try:
                archivo_eventos = self._exportar_eventos_crudos_organizado(output_dir, timestamp)
                if archivo_eventos:
                    result.add_file(archivo_eventos)
                    print(f"[2/4] Eventos detallados guardados: {archivo_eventos}")
            except Exception as e:
                result.add_error(f"Error exportando eventos crudos: {e}")

            # 3. PIPELINE AUTOMATIZADO: AnalyticsEngine -> Excel
            print("[3/4] Simulacion completada. Generando reporte de Excel...")
            try:
                analytics_engine = AnalyticsEngine(self.context.event_log, self.context.configuracion)
                analytics_engine.process_events()

                excel_filename = os.path.join(output_dir, f"simulation_report_{timestamp}.xlsx")
                archivo_excel = analytics_engine.export_to_excel(excel_filename)

                if archivo_excel:
                    result.add_file(archivo_excel)
                    print(f"[3/4] Reporte de Excel generado: {archivo_excel}")

                    # 4. PIPELINE AUTOMATIZADO: Visualizer -> PNG
                    print("[4/4] Reporte de Excel generado. Creando imagen de heatmap...")
                    try:
                        png_file = self._ejecutar_visualizador(archivo_excel, timestamp, output_dir)
                        if png_file:
                            result.add_file(png_file)
                    except Exception as e:
                        result.add_warning(f"Error generando heatmap PNG: {e}")
                else:
                    result.add_error("No se pudo generar el reporte de Excel")

            except Exception as e:
                result.add_error(f"Error en pipeline de analiticas: {e}")

            # Timing final
            end_time = time.time()
            result.set_execution_time(start_time, end_time)

            # Resumen final
            print("\n" + "="*70)
            print("PROCESO COMPLETADO V2 (WITH BUFFER)")
            print("="*70)
            print(result.get_summary())
            print("="*70)

            return result

        except Exception as e:
            # Error critico - rollback automatico
            result.add_error(f"Error critico en exportacion with buffer: {e}")
            result.set_execution_time(start_time, time.time())

            print(f"[ROLLBACK] Error critico detectado: {e}")
            if result.rollback_on_failure():
                print("[ROLLBACK] Rollback completado exitosamente")
            else:
                print("[ROLLBACK] Rollback tuvo problemas - verificar manualmente")

            return result

    def _exportar_eventos_crudos_organizado(self, output_dir: str, timestamp: str) -> Optional[str]:
        """
        Exporta eventos crudos a directorio organizado.

        Version mejorada con mejor error handling.

        Args:
            output_dir: Directorio de salida
            timestamp: Timestamp para nombre de archivo

        Returns:
            Optional[str]: Path del archivo generado o None si falla
        """
        filename = os.path.join(output_dir, f"raw_events_{timestamp}.json")

        try:
            if not self.context.event_log:
                print("[ANALYTICS V2] Warning: No hay eventos para exportar")
                return None

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.context.event_log, f, indent=2, ensure_ascii=False)
            print(f"[ANALYTICS V2] Eventos exportados a: {filename} ({len(self.context.event_log)} eventos)")
            return filename
        except Exception as e:
            print(f"[ANALYTICS V2] Error exportando eventos: {e}")
            return None

    def _ejecutar_visualizador(self, excel_path: str, timestamp: str, output_dir: str) -> Optional[str]:
        """
        Ejecuta visualizer.py automaticamente usando subprocess.

        Version mejorada con mejor error handling y retorno de path generado.

        Args:
            excel_path: Path del archivo Excel de entrada
            timestamp: Timestamp para nombre de archivo de salida
            output_dir: Directorio de salida

        Returns:
            Optional[str]: Path del archivo PNG generado o None si falla
        """
        output_filename = os.path.join(output_dir, f"warehouse_heatmap_{timestamp}.png")

        try:
            # Construir rutas dinamicamente
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            visualizer_path = os.path.join(script_dir, "visualizer.py")
            tmx_path = os.path.join(script_dir, self.context.configuracion.get('layout_file', 'layouts/WH1.tmx'))

            # Verificar que los archivos existen
            missing_files = []
            if not os.path.exists(visualizer_path):
                missing_files.append(f"visualizer.py: {visualizer_path}")
            if not os.path.exists(tmx_path):
                missing_files.append(f"TMX file: {tmx_path}")
            if not os.path.exists(excel_path):
                missing_files.append(f"Excel file: {excel_path}")

            if missing_files:
                for missing in missing_files:
                    print(f"[ERROR V2] Archivo no encontrado: {missing}")
                return None

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

            print(f"[VISUALIZER V2] Ejecutando comando: {' '.join(cmd)}")

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
                return output_filename
            else:
                print(f"[ERROR V2] visualizer.py fallo con codigo: {result.returncode}")
                if result.stderr:
                    print(f"[ERROR V2] Error del visualizer: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("[ERROR V2] visualizer.py tomo demasiado tiempo (>5 min) - proceso terminado")
            return None
        except Exception as e:
            print(f"[ERROR V2] Error ejecutando visualizer.py: {e}")
            return None