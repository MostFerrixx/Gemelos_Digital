# -*- coding: utf-8 -*-
"""
Script de prueba para generar config.json programáticamente
sin necesidad de la interfaz gráfica.
"""

import json
import os

def generar_config_prueba():
    """Genera un config.json de prueba con la estructura del nuevo configurador"""

    config = {
        "total_ordenes": 300,
        "distribucion_tipos": {
            "pequeno": {"porcentaje": 60, "volumen": 5},
            "mediano": {"porcentaje": 30, "volumen": 25},
            "grande": {"porcentaje": 10, "volumen": 80}
        },
        "capacidad_carro": 150,
        "dispatch_strategy": "Optimizacion Global",
        "tour_type": "Tour Mixto (Multi-Destino)",
        "layout_file": "layouts/WH1.tmx",
        "sequence_file": "layouts/Warehouse_Logic.xlsx",
        "map_scale": 1.3,
        "selected_resolution_key": "Pequena (800x800)",
        "num_operarios_terrestres": 2,
        "num_montacargas": 1,
        "num_operarios_total": 3,
        "capacidad_montacargas": 1000,
        "tiempo_descarga_por_tarea": 5,
        "assignment_rules": {
            "GroundOperator": {},
            "Forklift": {}
        },
        "outbound_staging_distribution": {
            "1": 100, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0
        },
        "agent_types": [
            # 2 Operarios Terrestres
            {
                "type": "GroundOperator",
                "capacity": 150,
                "discharge_time": 5,
                "work_area_priorities": {
                    "Area_Ground": 1,
                    "Area_Piso_L1": 2
                }
            },
            {
                "type": "GroundOperator",
                "capacity": 150,
                "discharge_time": 5,
                "work_area_priorities": {
                    "Area_Ground": 1,
                    "Area_Piso_L1": 2
                }
            },
            # 1 Montacargas
            {
                "type": "Forklift",
                "capacity": 1000,
                "discharge_time": 5,
                "work_area_priorities": {
                    "Area_Rack": 1
                }
            }
        ],
        "num_operarios": 3,
        "tareas_zona_a": 0,
        "tareas_zona_b": 0
    }

    config_path = "config.json"

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print(f"[TEST] Config de prueba generado exitosamente: {config_path}")
    print(f"[TEST] Total de agentes: {len(config['agent_types'])}")
    print(f"[TEST] Operarios Terrestres: {config['num_operarios_terrestres']}")
    print(f"[TEST] Montacargas: {config['num_montacargas']}")
    print(f"[TEST] Work Areas usadas: Area_Ground, Area_Piso_L1, Area_Rack")

    # Mostrar estructura de agent_types
    print("\n[TEST] Estructura de agent_types:")
    for idx, agent in enumerate(config['agent_types']):
        print(f"  [{idx}] {agent['type']}: capacity={agent['capacity']}, "
              f"work_areas={list(agent['work_area_priorities'].keys())}")

    return config

if __name__ == "__main__":
    generar_config_prueba()
