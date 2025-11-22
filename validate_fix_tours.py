"""
Script para validar que el fix de tours funciona correctamente
Analiza el archivo JSONL generado y muestra métricas de tours
"""
import json
from collections import defaultdict

def analyze_tours(jsonl_file):
    print("="*80)
    print("VALIDACIÓN DE FIX: TOURS DE GROUND OPERATORS")
    print("="*80)
    print()
    
    # Estructuras para rastrear comportamiento
    agent_tours = defaultdict(list)
    agent_current_tour = defaultdict(lambda: {
        'wo_ids': [],
        'volumes': [],
        'stagings': set(),
        'areas': set(),
        'sequences': [],
        'start_time': None,
        'end_time': None,
        'cargo_peak': 0
    })
    
    work_orders = {}
    
    # Primera pasada: cargar configuración y work orders
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        sim_start = json.loads(first_line)
        
        config = sim_start.get('config', {})
        print(f"Configuración:")
        print(f"  - Capacidad GroundOperator: {config.get('agent_types', [{}])[0].get('capacity', 'N/A')}L")
        print(f"  - Estrategia: {config.get('dispatch_strategy', 'N/A')}")
        print(f"  - Tour Type: {config.get('tour_type', 'N/A')}")
        print()
        
        # Cargar work orders iniciales
        for wo in sim_start.get('initial_work_orders', []):
            work_orders[wo['id']] = wo

    # Segunda pasada: analizar comportamiento de tours
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            event = json.loads(line)
            event_type = event.get('type') or event.get('event_type')
            
            # Actualizar work orders
            if event_type == 'work_order_update':
                wo_id = event['id']
                if wo_id not in work_orders:
                    work_orders[wo_id] = {}
                work_orders[wo_id].update(event)
            
            # Rastrear comportamiento de agentes
            elif event_type == 'estado_agente':
                agent_id = event['agent_id']
                if not agent_id.startswith('GroundOp'):
                    continue
                    
                data = event['data']
                timestamp = event['timestamp']
                status = data['status']
                cargo = data['cargo_volume']
                current_task = data.get('current_task')
                
                tour_info = agent_current_tour[agent_id]
                
                # Rastrear pico de carga
                if cargo > tour_info['cargo_peak']:
                    tour_info['cargo_peak'] = cargo
                
                # Detectar inicio de nuevo tour
                if current_task and status in ['moving', 'picking']:
                    if not tour_info['wo_ids']:
                        tour_info['start_time'] = timestamp
                    
                    if current_task not in tour_info['wo_ids']:
                        tour_info['wo_ids'].append(current_task)
                        
                        if current_task in work_orders:
                            wo = work_orders[current_task]
                            tour_info['volumes'].append(wo.get('volume', 0))
                            tour_info['stagings'].add(wo.get('staging'))
                            tour_info['areas'].add(wo.get('work_area'))
                            tour_info['sequences'].append(wo.get('pick_sequence'))
                
                # Detectar fin de tour
                if status == 'discharging' or (status == 'idle' and cargo == 0 and tour_info['wo_ids']):
                    tour_info['end_time'] = timestamp
                    
                    if tour_info['wo_ids']:
                        agent_tours[agent_id].append({
                            'wo_count': len(tour_info['wo_ids']),
                            'wo_ids': tour_info['wo_ids'].copy(),
                            'total_volume': sum(tour_info['volumes']),
                            'stagings': list(tour_info['stagings']),
                            'areas': list(tour_info['areas']),
                            'sequences': tour_info['sequences'].copy(),
                            'cargo_peak': tour_info['cargo_peak'],
                            'duration': tour_info['end_time'] - tour_info['start_time'] if tour_info['start_time'] and tour_info['end_time'] else 0
                        })
                        
                        # Resetear
                        agent_current_tour[agent_id] = {
                            'wo_ids': [], 'volumes': [], 'stagings': set(), 'areas': set(),
                            'sequences': [], 'start_time': None, 'end_time': None, 'cargo_peak': 0
                        }

    # Análisis de resultados
    print("\n" + "="*80)
    print("RESULTADOS DEL ANÁLISIS")
    print("="*80)
    
    for agent_id, tours in agent_tours.items():
        print(f"\n{agent_id}:")
        print(f"  Total Tours: {len(tours)}")
        
        if tours:
            avg_wo_count = sum(t['wo_count'] for t in tours) / len(tours)
            avg_volume = sum(t['total_volume'] for t in tours) / len(tours)
            avg_cargo_peak = sum(t['cargo_peak'] for t in tours) / len(tours)
            capacity = config.get('agent_types', [{}])[0].get('capacity', 150)
            
            print(f"  Promedio WO por tour: {avg_wo_count:.2f}")
            print(f"  Promedio volumen por tour: {avg_volume:.2f}L")
            print(f"  Promedio carga pico: {avg_cargo_peak:.2f}L")
            print(f"  Utilización promedio: {(avg_cargo_peak / capacity) * 100:.1f}%")
            
            # Mostrar primeros 3 tours
            print(f"\n  Primeros 3 tours:")
            for i, tour in enumerate(tours[:3], 1):
                print(f"    Tour {i}:")
                print(f"      - WO Count: {tour['wo_count']}")
                print(f"      - Volume: {tour['total_volume']}L")
                print(f"      - Cargo Peak: {tour['cargo_peak']}L")
                print(f"      - Stagings: {tour['stagings']}")
                print(f"      - Areas: {tour['areas']}")
                print(f"      - Sequences: {tour['sequences']}")
                print(f"      - Utilización: {(tour['cargo_peak'] / capacity) * 100:.1f}%")

    print("\n" + "="*80)
    print("CRITERIOS DE ÉXITO:")
    print("="*80)
    print()
    
    # Verificar criterios
    for agent_id, tours in agent_tours.items():
        if tours:
            avg_wo_count = sum(t['wo_count'] for t in tours) / len(tours)
            avg_cargo_peak = sum(t['cargo_peak'] for t in tours) / len(tours)
            capacity = config.get('agent_types', [{}])[0].get('capacity', 150)
            utilizacion = (avg_cargo_peak / capacity) * 100
            
            print(f"{agent_id}:")
            print(f"  ✓ WOs por tour >= 5: {avg_wo_count >= 5} ({avg_wo_count:.2f})")
            print(f"  ✓ Utilización >= 70%: {utilizacion >= 70} ({utilizacion:.1f}%)")
            print()

if __name__ == "__main__":
    import sys
    import glob
    
    # Buscar el JSONL más reciente
    jsonl_files = glob.glob("output/simulation_*/replay_*.jsonl")
    if not jsonl_files:
        print("ERROR: No se encontraron archivos JSONL")
        sys.exit(1)
    
    # Ordenar por fecha (más reciente primero)
    jsonl_files.sort(reverse=True)
    latest_jsonl = jsonl_files[0]
    
    print(f"Analizando: {latest_jsonl}")
    print()
    
    analyze_tours(latest_jsonl)
