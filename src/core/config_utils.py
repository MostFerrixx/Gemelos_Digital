# -*- coding: utf-8 -*-
"""
Utilidades de configuracion para el simulador.
Modulo extraido de run_simulator.py para modularizacion incremental.
"""


def get_default_config() -> dict:
    """Retorna la configuracion por defecto hardcodeada"""
    return {
        # Configuracion de tareas de picking
        'total_ordenes': 300,
        'distribucion_tipos': {
            'pequeno': {'porcentaje': 60, 'volumen': 5},
            'mediano': {'porcentaje': 30, 'volumen': 25},
            'grande': {'porcentaje': 10, 'volumen': 80}
        },
        'capacidad_carro': 150,

        # Configuracion de estrategias
        'strategy': 'Zoning and Snake',
        'dispatch_strategy': 'Ejecucion de Plan (Filtro por Prioridad)',
        'tour_type': 'Tour Mixto (Multi-Destino)',

        # Configuracion de layout
        'layout_file': 'layouts/WH1.tmx',
        'sequence_file': 'layouts/Warehouse_Logic.xlsx',

        # Configuracion de ventana
        'selected_resolution_key': 'Pequena (800x800)',

        # Configuracion de operarios
        'num_operarios_terrestres': 1,
        'num_montacargas': 1,
        'num_operarios_total': 2,
        'capacidad_montacargas': 1000,

        # Configuracion de asignacion de recursos
        'assignment_rules': {
            "GroundOperator": {1: 1},
            "Forklift": {1: 2, 2: 1, 3: 1, 4: 1, 5: 1}
        },

        # Compatibilidad con codigo existente
        'tareas_zona_a': 0,
        'tareas_zona_b': 0,
        'num_operarios': 2
    }


def mostrar_resumen_config(configuracion: dict) -> None:
    """Muestra un resumen de la configuracion cargada"""
    config = configuracion
    print("\n" + "="*50)
    print("CONFIGURACION DE SIMULACION CARGADA")
    print("="*50)
    print(f"Total de ordenes: {config.get('total_ordenes', 'N/A')}")
    print(f"Operarios terrestres: {config.get('num_operarios_terrestres', 'N/A')}")
    print(f"Montacargas: {config.get('num_montacargas', 'N/A')}")
    print(f"Estrategia de despacho: {config.get('dispatch_strategy', 'N/A')}")
    print(f"Layout: {config.get('layout_file', 'N/A')}")
    print(f"Secuencia: {config.get('sequence_file', 'N/A')}")
    print("="*50 + "\n")