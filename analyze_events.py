# -*- coding: utf-8 -*-
"""
Script para analizar los tipos de eventos disponibles en raw_events.json
y diagnosticar por qué AnalyticsEngine no procesa correctamente los datos.
"""

import json
import pandas as pd
from collections import Counter

def analyze_event_types(json_file_path):
    """
    Analiza los tipos de eventos disponibles en el archivo JSON.
    """
    print(f"=" * 70)
    print(f"ANALISIS DE TIPOS DE EVENTOS: {json_file_path}")
    print(f"=" * 70)
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        print(f"Total de eventos: {len(events)}")
        
        # Contar tipos de eventos
        event_types = [event.get('tipo', 'SIN_TIPO') for event in events]
        type_counts = Counter(event_types)
        
        print(f"\nTipos de eventos encontrados:")
        for event_type, count in type_counts.most_common():
            print(f"  {event_type}: {count} eventos")
        
        # Analizar eventos específicos
        print(f"\n" + "-" * 50)
        print("ANALISIS DETALLADO DE EVENTOS")
        print("-" * 50)
        
        # 1. Eventos de agentes
        agent_events = [e for e in events if e.get('tipo') == 'estado_agente']
        print(f"\n1. EVENTOS DE AGENTES (estado_agente): {len(agent_events)}")
        if agent_events:
            sample_agent = agent_events[0]
            print(f"   Estructura del primer evento:")
            for key, value in sample_agent.items():
                print(f"     {key}: {type(value).__name__} = {value}")
        
        # 2. Eventos de work orders completadas
        wo_completed = [e for e in events if e.get('tipo') == 'work_order_completed']
        print(f"\n2. WORK ORDERS COMPLETADAS: {len(wo_completed)}")
        if wo_completed:
            sample_wo = wo_completed[0]
            print(f"   Estructura del primer evento:")
            for key, value in sample_wo.items():
                print(f"     {key}: {type(value).__name__} = {value}")
        
        # 3. Eventos de tareas completadas
        task_completed = [e for e in events if e.get('tipo') == 'task_completed']
        print(f"\n3. TAREAS COMPLETADAS (task_completed): {len(task_completed)}")
        if task_completed:
            sample_task = task_completed[0]
            print(f"   Estructura del primer evento:")
            for key, value in sample_task.items():
                print(f"     {key}: {type(value).__name__} = {value}")
        
        # 4. Verificar si hay eventos con 'data' field
        events_with_data = [e for e in events if 'data' in e]
        print(f"\n4. EVENTOS CON CAMPO 'data': {len(events_with_data)}")
        if events_with_data:
            sample_data = events_with_data[0]
            print(f"   Estructura del primer evento con 'data':")
            for key, value in sample_data.items():
                if key == 'data':
                    print(f"     {key}: {type(value).__name__}")
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            print(f"       {subkey}: {type(subvalue).__name__} = {subvalue}")
                else:
                    print(f"     {key}: {type(value).__name__} = {value}")
        
        # 5. Verificar agent_id en eventos de agentes
        agent_ids = set()
        for event in agent_events:
            if 'agent_id' in event:
                agent_ids.add(event['agent_id'])
        
        print(f"\n5. AGENT IDs UNICOS ENCONTRADOS: {len(agent_ids)}")
        for agent_id in sorted(agent_ids):
            print(f"   {agent_id}")
        
        # 6. Verificar posiciones en eventos de agentes
        positions_found = 0
        for event in agent_events:
            if 'position' in event and isinstance(event['position'], list) and len(event['position']) >= 2:
                positions_found += 1
        
        print(f"\n6. EVENTOS CON POSICIONES VALIDAS: {positions_found}/{len(agent_events)}")
        
        return True
        
    except Exception as e:
        print(f"ERROR analizando eventos: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Función principal del análisis.
    """
    print("ANALIZADOR DE EVENTOS - DIAGNOSTICO DE ANALYTICS ENGINE")
    print("=" * 70)
    
    # Buscar el archivo raw_events más reciente
    import os
    from pathlib import Path
    
    output_dir = Path("output")
    if not output_dir.exists():
        print("ERROR: Directorio 'output' no encontrado")
        return 1
    
    raw_files = list(output_dir.rglob("raw_events_*.json"))
    if not raw_files:
        print("ERROR: No se encontraron archivos raw_events en 'output'")
        return 1
    
    # Ordenar por fecha de modificación
    latest_file = max(raw_files, key=lambda f: f.stat().st_mtime)
    print(f"Archivo más reciente encontrado: {latest_file}")
    
    # Analizar el archivo
    success = analyze_event_types(str(latest_file))
    
    if success:
        print("\n" + "=" * 70)
        print("ANALISIS COMPLETADO")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("ANALISIS FALLIDO")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
