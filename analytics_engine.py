# -*- coding: utf-8 -*-
"""
Analytics Engine para generar reportes ejecutivos en Excel.
Procesa eventos de simulación y calcula métricas clave de rendimiento.
"""

import pandas as pd
import json
import argparse
from typing import List, Dict
from datetime import datetime, timedelta
from openpyxl.formatting.rule import ColorScaleRule


class AnalyticsEngine:
    """Motor de analíticas para generar reportes ejecutivos a partir de eventos de simulación"""
    
    def __init__(self, event_log: list, config: dict):
        """
        Inicializa el motor de analíticas.
        
        Args:
            event_log: Lista de eventos capturados durante la simulación
            config: Configuración utilizada en la simulación
        """
        self.event_log = event_log
        self.config = config
        self.events_df = None
        self.summary_kpis = None
        self.agent_performance = None
        self.heatmap_data = None
        
        print(f"[ANALYTICS-ENGINE] Inicializado con {len(event_log)} eventos")
    
    @classmethod
    def from_json_file(cls, json_filepath: str):
        """
        Constructor alternativo que carga eventos desde un archivo raw_events.json.
        
        Args:
            json_filepath: Ruta al archivo raw_events.json
            
        Returns:
            Nueva instancia de AnalyticsEngine cargada desde archivo
        """
        print(f"[ANALYTICS-ENGINE] Cargando eventos desde: {json_filepath}")
        
        try:
            with open(json_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extraer eventos y configuración del archivo JSON
            if isinstance(data, dict):
                # Formato: {"events": [...], "config": {...}}
                event_log = data.get('events', [])
                config = data.get('config', {})
            elif isinstance(data, list):
                # Formato: Lista directa de eventos (sin configuración embebida)
                event_log = data
                config = {}
                print("[ANALYTICS-ENGINE] ADVERTENCIA: No se encontró configuración en el archivo JSON")
            else:
                raise ValueError("Formato de archivo JSON no reconocido")
            
            print(f"[ANALYTICS-ENGINE] Cargados {len(event_log)} eventos del archivo")
            return cls(event_log=event_log, config=config)
            
        except FileNotFoundError:
            print(f"[ANALYTICS-ENGINE] ERROR: Archivo no encontrado: {json_filepath}")
            raise
        except json.JSONDecodeError as e:
            print(f"[ANALYTICS-ENGINE] ERROR: Archivo JSON malformado: {e}")
            raise
        except Exception as e:
            print(f"[ANALYTICS-ENGINE] ERROR al cargar archivo: {e}")
            raise
    
    def process_events(self):
        """
        Método principal que procesa todos los eventos y calcula métricas.
        """
        print("[ANALYTICS-ENGINE] Procesando eventos...")
        
        # Convertir eventos a DataFrame para facilitar análisis
        if not self.event_log:
            print("[ANALYTICS-ENGINE] ADVERTENCIA: No hay eventos para procesar")
            return
        
        self.events_df = pd.DataFrame(self.event_log)
        print(f"[ANALYTICS-ENGINE] DataFrame creado con {len(self.events_df)} filas")
        
        # Calcular métricas
        self.summary_kpis = self._calculate_summary_kpis()
        self.agent_performance = self._calculate_agent_performance()
        self.heatmap_data = self._calculate_heatmap_data()
        
        print("[ANALYTICS-ENGINE] Procesamiento completado")
    
    def _calculate_summary_kpis(self) -> pd.DataFrame:
        """
        Calcula las métricas clave para la hoja "Resumen Ejecutivo".
        
        Returns:
            DataFrame con métricas de resumen ejecutivo
        """
        print("[ANALYTICS-ENGINE] Calculando KPIs de resumen ejecutivo...")
        
        if self.events_df is None or self.events_df.empty:
            return pd.DataFrame()
        
        # Tiempo total de simulación
        tiempo_inicio = self.events_df['timestamp'].min()
        tiempo_fin = self.events_df['timestamp'].max()
        tiempo_total_sim = tiempo_fin - tiempo_inicio
        tiempo_total_horas = tiempo_total_sim / 60  # Asumir que timestamp está en minutos
        
        # Total de tareas completadas
        task_completed_events = self.events_df[self.events_df['event_type'] == 'task_completed']
        total_tareas_completadas = len(task_completed_events)
        
        # Productividad (Tareas/Hora)
        if tiempo_total_horas > 0:
            productividad = total_tareas_completadas / tiempo_total_horas
        else:
            productividad = 0
        
        # Crear DataFrame de resumen
        summary_data = {
            'Métrica': [
                'Tiempo Total de Simulación (horas)',
                'Total de Tareas Completadas',
                'Productividad (Tareas/Hora)',
                'Tiempo de Inicio (sim)',
                'Tiempo de Fin (sim)'
            ],
            'Valor': [
                round(tiempo_total_horas, 2),
                total_tareas_completadas,
                round(productividad, 2),
                round(tiempo_inicio, 2),
                round(tiempo_fin, 2)
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        print(f"[ANALYTICS-ENGINE] KPIs calculados: {len(summary_df)} métricas")
        return summary_df
    
    def _calculate_agent_performance(self) -> pd.DataFrame:
        """
        Calcula las métricas de rendimiento por agente usando reconstrucción de estados.
        Nueva lógica precisa basada en eventos discharge_completed.
        
        Returns:
            DataFrame con métricas de rendimiento por agente
        """
        print("[ANALYTICS-ENGINE] Calculando rendimiento de agentes con lógica refactorizada...")
        
        if self.events_df is None or self.events_df.empty:
            return pd.DataFrame()
        
        # Tiempo total de simulación para cálculo de tiempo ocioso
        tiempo_total_simulacion = self.events_df['timestamp'].max() - self.events_df['timestamp'].min()
        
        # Obtener lista única de agentes
        agent_ids = self.events_df['agent_id'].unique()
        performance_data = []
        
        for agent_id in agent_ids:
            # Filtrar y ordenar eventos por agente
            agent_events = self.events_df[self.events_df['agent_id'] == agent_id].sort_values('timestamp')
            
            # Tareas completadas por agente
            task_events = agent_events[agent_events['event_type'] == 'task_completed']
            tareas_completadas = len(task_events)
            
            # Tiempo de picking (suma directa de tiempos de picking)
            tiempo_picking_total = 0
            if not task_events.empty:
                for _, event in task_events.iterrows():
                    if 'data' in event and event['data'] and 'tiempo_picking' in event['data']:
                        tiempo_picking_total += event['data']['tiempo_picking']
            
            # Tiempo de viaje (diferencias entre eventos agent_moved)
            tiempo_viaje = 0
            move_events = agent_events[agent_events['event_type'] == 'agent_moved']
            if not move_events.empty and not agent_events.empty:
                agent_events_with_diff = agent_events.copy()
                agent_events_with_diff['time_diff'] = agent_events_with_diff['timestamp'].diff()
                move_events_with_diff = agent_events_with_diff[agent_events_with_diff['event_type'] == 'agent_moved']
                tiempo_viaje = move_events_with_diff['time_diff'].fillna(0).sum()
            
            # NUEVA MÉTRICA: Tiempo de descarga (suma de tiempos de discharge_completed)
            tiempo_descarga_total = 0
            discharge_completed_events = agent_events[agent_events['event_type'] == 'discharge_completed']
            if not discharge_completed_events.empty:
                for _, event in discharge_completed_events.iterrows():
                    if 'data' in event and event['data'] and 'tiempo_total_descarga' in event['data']:
                        # Convertir de segundos a minutos para consistencia con otros tiempos
                        tiempo_descarga_total += event['data']['tiempo_total_descarga'] / 60
            
            # CORREGIDO: Tiempo_Total_Activo = Viaje + Picking + Descarga
            tiempo_total_activo = tiempo_viaje + tiempo_picking_total + tiempo_descarga_total
            
            # CORREGIDO: Tiempo_Ocioso = Tiempo_Total_Simulacion - Tiempo_Total_Activo
            tiempo_ocioso = max(0, tiempo_total_simulacion - tiempo_total_activo)
            
            # Utilización de capacidad (de eventos de descarga)
            discharge_events = agent_events[agent_events['event_type'] == 'discharge_started']
            utilizacion_capacidad_promedio = 0
            if not discharge_events.empty:
                capacidades = []
                for _, event in discharge_events.iterrows():
                    if 'data' in event and event['data']:
                        carga = event['data'].get('carga_actual', 0)
                        capacidad_max = event['data'].get('capacidad_maxima', 1)
                        if capacidad_max > 0:
                            capacidades.append((carga / capacidad_max) * 100)
                
                if capacidades:
                    utilizacion_capacidad_promedio = sum(capacidades) / len(capacidades)
            
            # Determinar tipo de agente
            agent_type = "Desconocido"
            if not agent_events.empty:
                first_event = agent_events.iloc[0]
                if 'data' in first_event and first_event['data'] and 'agent_type' in first_event['data']:
                    agent_type = first_event['data']['agent_type']
            
            performance_data.append({
                'Agent_ID': agent_id,
                'Tipo_Agente': agent_type,
                'Tareas_Completadas': tareas_completadas,
                'Tiempo_Total_Activo': round(tiempo_total_activo, 2),
                'Tiempo_Picking': round(tiempo_picking_total, 2),
                'Tiempo_Viaje': round(tiempo_viaje, 2),
                'Tiempo_Descarga': round(tiempo_descarga_total, 2),  # NUEVA COLUMNA
                'Tiempo_Ocioso': round(tiempo_ocioso, 2),
                'Utilizacion_Capacidad_Promedio_Pct': round(utilizacion_capacidad_promedio, 2),
                'Eventos_Totales': len(agent_events)
            })
        
        performance_df = pd.DataFrame(performance_data)
        print(f"[ANALYTICS-ENGINE] Rendimiento refactorizado calculado para {len(performance_df)} agentes")
        return performance_df
    
    def _calculate_heatmap_data(self) -> pd.DataFrame:
        """
        Calcula los datos necesarios para generar heatmaps de actividad en el almacén.
        Analiza tiempo de tránsito y tiempo de trabajo por coordenada.
        
        Returns:
            DataFrame con columnas: x, y, tiempo_trabajo, tiempo_transito, tiempo_total
        """
        print("[ANALYTICS-ENGINE] Calculando datos de heatmap...")
        
        if self.events_df is None or self.events_df.empty:
            return pd.DataFrame()
        
        # Obtener dimensiones del almacén desde configuración
        # Valores por defecto si no están disponibles
        warehouse_width = self.config.get('warehouse_width', 50)
        warehouse_height = self.config.get('warehouse_height', 35)
        
        print(f"[ANALYTICS-ENGINE] Dimensiones del almacén: {warehouse_width}x{warehouse_height}")
        
        # Crear DataFrame base con todas las coordenadas del almacén
        heatmap_data = []
        for x in range(warehouse_width):
            for y in range(warehouse_height):
                heatmap_data.append({
                    'x': x,
                    'y': y,
                    'tiempo_trabajo': 0.0,
                    'tiempo_transito': 0.0,
                    'tiempo_total': 0.0
                })
        
        heatmap_df = pd.DataFrame(heatmap_data)
        print(f"[ANALYTICS-ENGINE] Creada grilla base con {len(heatmap_df)} coordenadas")
        
        # Calcular tiempo de tránsito (eventos agent_moved)
        move_events = self.events_df[self.events_df['event_type'] == 'agent_moved']
        transito_count = 0
        
        for _, event in move_events.iterrows():
            if 'data' in event and event['data'] and 'position' in event['data']:
                try:
                    position = event['data']['position']
                    if isinstance(position, list) and len(position) >= 2:
                        x, y = int(position[0]), int(position[1])
                        # Verificar que las coordenadas estén dentro del rango válido
                        if 0 <= x < warehouse_width and 0 <= y < warehouse_height:
                            # Buscar la fila correspondiente e incrementar tiempo_transito
                            mask = (heatmap_df['x'] == x) & (heatmap_df['y'] == y)
                            heatmap_df.loc[mask, 'tiempo_transito'] += 1.0  # 1 unidad de tiempo por movimiento
                            transito_count += 1
                except (ValueError, TypeError, IndexError):
                    # Saltar eventos con coordenadas malformadas
                    continue
        
        print(f"[ANALYTICS-ENGINE] Procesados {transito_count} eventos de tránsito")
        
        # Calcular tiempo de trabajo (eventos task_completed)
        task_events = self.events_df[self.events_df['event_type'] == 'task_completed']
        trabajo_count = 0
        
        for _, event in task_events.iterrows():
            if 'data' in event and event['data']:
                try:
                    # Buscar coordenadas en task_ubicacion O location (ambos formatos de evento)
                    ubicacion = None
                    if 'task_ubicacion' in event['data']:
                        ubicacion = event['data']['task_ubicacion']
                    elif 'location' in event['data']:
                        ubicacion = event['data']['location']
                    
                    tiempo_picking = event['data'].get('tiempo_picking', 0)
                    
                    if ubicacion and isinstance(ubicacion, list) and len(ubicacion) >= 2 and tiempo_picking > 0:
                        x, y = int(ubicacion[0]), int(ubicacion[1])
                        # Verificar que las coordenadas estén dentro del rango válido
                        if 0 <= x < warehouse_width and 0 <= y < warehouse_height:
                            # Buscar la fila correspondiente e incrementar tiempo_trabajo
                            mask = (heatmap_df['x'] == x) & (heatmap_df['y'] == y)
                            heatmap_df.loc[mask, 'tiempo_trabajo'] += tiempo_picking
                            trabajo_count += 1
                except (ValueError, TypeError, IndexError):
                    # Saltar eventos con coordenadas o tiempo malformados
                    continue
        
        print(f"[ANALYTICS-ENGINE] Procesados {trabajo_count} eventos de trabajo")
        
        # Calcular tiempo total (suma de trabajo y tránsito)
        heatmap_df['tiempo_total'] = heatmap_df['tiempo_trabajo'] + heatmap_df['tiempo_transito']
        
        # Estadísticas de resumen
        total_tiempo_trabajo = heatmap_df['tiempo_trabajo'].sum()
        total_tiempo_transito = heatmap_df['tiempo_transito'].sum()
        coordenadas_activas = len(heatmap_df[heatmap_df['tiempo_total'] > 0])
        
        print(f"[ANALYTICS-ENGINE] Heatmap calculado: {coordenadas_activas} coordenadas activas")
        print(f"[ANALYTICS-ENGINE] Tiempo total trabajo: {total_tiempo_trabajo:.2f}, tránsito: {total_tiempo_transito:.2f}")
        
        return heatmap_df
    
    def export_to_excel(self, filepath: str):
        """
        Exporta todos los DataFrames a un archivo Excel con múltiples hojas.
        
        Args:
            filepath: Ruta del archivo Excel a crear
        """
        print(f"[ANALYTICS-ENGINE] Exportando reporte a: {filepath}")
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # Hoja 1: Resumen Ejecutivo
                if self.summary_kpis is not None and not self.summary_kpis.empty:
                    self.summary_kpis.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)
                    print("[ANALYTICS-ENGINE] Hoja 'Resumen Ejecutivo' exportada")
                else:
                    # Crear hoja vacía si no hay datos
                    pd.DataFrame({'Mensaje': ['No hay datos de KPIs disponibles']}).to_excel(
                        writer, sheet_name='Resumen Ejecutivo', index=False)
                
                # Hoja 2: Rendimiento de Agentes
                if self.agent_performance is not None and not self.agent_performance.empty:
                    self.agent_performance.to_excel(writer, sheet_name='Rendimiento de Agentes', index=False)
                    print("[ANALYTICS-ENGINE] Hoja 'Rendimiento de Agentes' exportada")
                else:
                    # Crear hoja vacía si no hay datos
                    pd.DataFrame({'Mensaje': ['No hay datos de agentes disponibles']}).to_excel(
                        writer, sheet_name='Rendimiento de Agentes', index=False)
                
                # Hoja 3: Configuración
                config_df = pd.DataFrame([
                    {'Parámetro': key, 'Valor': str(value)}
                    for key, value in self.config.items()
                ])
                config_df.to_excel(writer, sheet_name='Configuracion', index=False)
                print("[ANALYTICS-ENGINE] Hoja 'Configuracion' exportada")
                
                # Hoja 4: Datos de Heatmap
                if self.heatmap_data is not None and not self.heatmap_data.empty:
                    self.heatmap_data.to_excel(writer, sheet_name='HeatmapData', index=False)
                    print("[ANALYTICS-ENGINE] Hoja 'HeatmapData' exportada")
                else:
                    # Crear hoja vacía si no hay datos
                    pd.DataFrame({'Mensaje': ['No hay datos de heatmap disponibles']}).to_excel(
                        writer, sheet_name='HeatmapData', index=False)
                
                # Hoja 5: Visual Heatmap
                self._add_visual_heatmap_sheet(writer)
            
            print(f"[ANALYTICS-ENGINE] Reporte exportado exitosamente: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"[ANALYTICS-ENGINE] ERROR al exportar: {e}")
            return None
    
    def _add_visual_heatmap_sheet(self, writer):
        """
        Crea una hoja VisualHeatmap con representación gráfica del almacén coloreada
        según intensidad de actividad usando formato condicional.
        
        Args:
            writer: pandas ExcelWriter object
        """
        print("[ANALYTICS-ENGINE] Creando hoja VisualHeatmap...")
        
        if self.heatmap_data is None or self.heatmap_data.empty:
            # Crear hoja vacía si no hay datos
            pd.DataFrame({'Mensaje': ['No hay datos de heatmap para visualización']}).to_excel(
                writer, sheet_name='VisualHeatmap', index=False)
            print("[ANALYTICS-ENGINE] Hoja 'VisualHeatmap' vacía creada")
            return
        
        # Pivotar datos de formato largo (x, y, tiempo_total) a matriz 2D
        # x será las columnas, y será las filas
        heatmap_matrix = self.heatmap_data.pivot(
            index='y',           # Filas (eje vertical)
            columns='x',         # Columnas (eje horizontal)
            values='tiempo_total' # Valores de las celdas
        )
        
        # Ordenar índice y columnas para presentación correcta del almacén
        # y=0 en la parte superior, x=0 en la izquierda
        heatmap_matrix = heatmap_matrix.sort_index(ascending=False)  # y invertido (arriba-abajo)
        heatmap_matrix = heatmap_matrix.sort_index(axis=1)           # x normal (izquierda-derecha)
        
        # Rellenar valores NaN con 0 (coordenadas sin actividad)
        heatmap_matrix = heatmap_matrix.fillna(0)
        
        print(f"[ANALYTICS-ENGINE] Matriz de heatmap creada: {heatmap_matrix.shape[0]}x{heatmap_matrix.shape[1]}")
        
        # Escribir matriz en nueva hoja sin índices ni cabeceras (puramente visual)
        heatmap_matrix.to_excel(
            writer, 
            sheet_name='VisualHeatmap', 
            index=False,    # Sin etiquetas de fila
            header=False    # Sin etiquetas de columna
        )
        
        # Obtener el objeto worksheet de openpyxl para aplicar formato condicional
        worksheet = writer.sheets['VisualHeatmap']
        
        # Calcular rango de celdas a formatear
        num_rows = heatmap_matrix.shape[0]
        num_cols = heatmap_matrix.shape[1]
        
        # Convertir a notación de Excel (A1:ZZ99)
        from openpyxl.utils import get_column_letter
        start_cell = 'A1'
        end_col_letter = get_column_letter(num_cols)
        end_cell = f'{end_col_letter}{num_rows}'
        cell_range = f'{start_cell}:{end_cell}'
        
        print(f"[ANALYTICS-ENGINE] Aplicando formato condicional al rango: {cell_range}")
        
        # Crear regla de formato condicional: Verde-Amarillo-Rojo
        # Verde = baja actividad, Amarillo = media, Rojo = alta actividad
        color_scale = ColorScaleRule(
            start_type='min',        # Valores mínimos
            start_color='00FF00',    # Verde para baja actividad
            mid_type='percentile',   # Percentil 50 (mediana)
            mid_value=50,
            mid_color='FFFF00',      # Amarillo para actividad media
            end_type='max',          # Valores máximos  
            end_color='FF0000'       # Rojo para alta actividad
        )
        
        # Aplicar la regla al rango de datos
        worksheet.conditional_formatting.add(cell_range, color_scale)
        
        # Ajustar ancho de columnas para mejor visualización
        for col in range(1, num_cols + 1):
            col_letter = get_column_letter(col)
            worksheet.column_dimensions[col_letter].width = 3  # Celdas estrechas tipo pixel
        
        # Ajustar alto de filas
        for row in range(1, num_rows + 1):
            worksheet.row_dimensions[row].height = 15  # Filas compactas
        
        print(f"[ANALYTICS-ENGINE] Hoja 'VisualHeatmap' creada con formato condicional aplicado")


def main():
    """Función principal para ejecución independiente del AnalyticsEngine"""
    parser = argparse.ArgumentParser(
        description='Motor de Analíticas para Simulador de Almacén - Procesamiento independiente de eventos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python analytics_engine.py raw_events_20250826_011557.json report_output.xlsx
  python analytics_engine.py events.json analysis_report.xlsx
        """
    )
    
    parser.add_argument(
        'input_json', 
        help='Ruta al archivo raw_events.json de entrada'
    )
    parser.add_argument(
        'output_excel', 
        help='Ruta del archivo Excel de salida para el reporte'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar información detallada del procesamiento'
    )
    
    args = parser.parse_args()
    
    try:
        print("=" * 70)
        print("ANALYTICS ENGINE - PROCESAMIENTO INDEPENDIENTE")
        print("=" * 70)
        
        # Cargar AnalyticsEngine desde archivo JSON
        engine = AnalyticsEngine.from_json_file(args.input_json)
        
        # Procesar eventos y calcular métricas
        engine.process_events()
        
        # Exportar reporte a Excel
        result = engine.export_to_excel(args.output_excel)
        
        if result:
            print("=" * 70)
            print("PROCESAMIENTO COMPLETADO EXITOSAMENTE")
            print(f"Reporte generado: {result}")
            print("=" * 70)
        else:
            print("ERROR: Fallo la exportacion del reporte")
            return 1
            
    except FileNotFoundError as e:
        print(f"ERROR: Archivo no encontrado - {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Archivo JSON malformado - {e}")
        return 1
    except Exception as e:
        print(f"ERROR INESPERADO: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())


print("[OK] Módulo 'analytics_engine' cargado - Motor de analíticas para reportes ejecutivos.")