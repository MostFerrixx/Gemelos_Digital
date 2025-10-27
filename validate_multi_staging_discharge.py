"""
Script de validacion: Descarga Multiple en Stagings
Verifica que los operarios descarguen en multiples stagings cuando el tour lo requiera
"""
import json
import sys
from collections import defaultdict

def normalize_agent_id(agent_id):
    """
    Normaliza el agent_id para comparaciones
    Convierte 'GroundOperator_GroundOp-01' a 'GroundOp-01'
    """
    if '_' in agent_id:
        return agent_id.split('_')[1]
    return agent_id

def validate_multi_staging_discharge(jsonl_path):
    """
    Analiza el archivo JSONL para verificar descargas multiples
    """
    print("="*80)
    print("VALIDACION: DESCARGA MULTIPLE EN STAGINGS")
    print("="*80)
    
    # Rastrear tours y descargas
    tours = defaultdict(lambda: {
        'wos': set(),  # Usar set para búsquedas rápidas
        'stagings_expected': set(),
        'stagings_visited': set(),
        'agent_id': None
    })
    
    # Mapeo de WO_ID -> TOUR_ID para relacion directa
    wo_to_tour = {}
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        # Skip metadata line
        first_line = f.readline()
        
        for line in f:
            event = json.loads(line)
            event_type = event.get('type')
            
            # Capturar WOs asignadas
            if event_type == 'work_order_update' and event.get('status') == 'assigned':
                tour_id = event.get('tour_id')
                agent_id = event.get('assigned_agent_id')
                wo_id = event.get('id')
                
                if tour_id and agent_id and wo_id:
                    tours[tour_id]['wos'].add(wo_id)
                    tours[tour_id]['stagings_expected'].add(event['staging'])
                    tours[tour_id]['agent_id'] = agent_id
                    
                    # Mapear WO -> Tour
                    wo_to_tour[wo_id] = tour_id
            
            # Capturar descargas parciales
            elif event_type == 'partial_discharge':
                staging_id = event['staging_id']
                wos_descargadas = event.get('wos_descargadas', [])
                
                # Encontrar el tour al que pertenecen estas WOs
                for wo_id in wos_descargadas:
                    if wo_id in wo_to_tour:
                        tour_id = wo_to_tour[wo_id]
                        tours[tour_id]['stagings_visited'].add(staging_id)
                        # Solo necesitamos registrar una vez por staging
                        break
    
    # Analizar resultados
    print("\nRESULTADO DEL ANALISIS:\n")
    
    tours_multi_staging = 0
    tours_validated = 0
    tours_correct = 0
    
    for tour_id, data in sorted(tours.items()):
        if len(data['stagings_expected']) > 1:
            tours_multi_staging += 1
            tours_validated += 1
            
            stagings_expected_sorted = sorted(list(data['stagings_expected']))
            stagings_visited_sorted = sorted(list(data['stagings_visited']))
            
            # Verificar si visito TODOS los stagings esperados
            correct = data['stagings_visited'] == data['stagings_expected']
            
            if correct:
                tours_correct += 1
            
            print(f"  Tour {tour_id} ({data['agent_id']}):")
            print(f"    - WOs: {len(data['wos'])}")
            print(f"    - Stagings esperados: {stagings_expected_sorted}")
            print(f"    - Stagings visitados: {stagings_visited_sorted}")
            print(f"    - Validacion: {'✓ CORRECTO' if correct else '✗ INCORRECTO'}")
            print()
    
    print(f"\nRESUMEN:")
    print(f"  Total tours analizados: {len(tours)}")
    print(f"  Tours con multiples stagings: {tours_multi_staging}")
    print(f"  Tours correctos (visito todos): {tours_correct}/{tours_multi_staging}")
    
    print("\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)
    
    if tours_correct == tours_multi_staging and tours_multi_staging > 0:
        print("✅ EXITO: Todos los tours multi-staging descargaron en TODOS los stagings")
        print("   El comportamiento de descarga multiple esta funcionando correctamente.")
    elif tours_multi_staging == 0:
        print("⚠️  ADVERTENCIA: No se encontraron tours con multiples stagings para validar")
    else:
        print(f"✗ FALLO: {tours_multi_staging - tours_correct}/{tours_multi_staging} tours NO descargaron correctamente")
    
    print("="*80)

if __name__ == "__main__":
    import glob
    
    # Buscar el archivo JSONL mas reciente
    jsonl_files = glob.glob("output/simulation_*/replay_*.jsonl")
    
    if not jsonl_files:
        print("ERROR: No se encontro ningun archivo replay_*.jsonl en output/")
        sys.exit(1)
    
    # Ordenar por fecha (mas reciente primero)
    jsonl_files.sort(reverse=True)
    latest_jsonl = jsonl_files[0]
    
    print(f"Analizando: {latest_jsonl}\n")
    validate_multi_staging_discharge(latest_jsonl)

