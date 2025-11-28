# -*- coding: utf-8 -*-
"""
Generate Replay - Entry point para generar archivos .jsonl
Sin UI, solo generacion de eventos para replay
"""

import sys
import os
import argparse

# Add src/ to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from engines.event_generator import EventGenerator


def main():
    """Funcion principal - Genera archivo .jsonl sin UI"""
    
    # CLI argument parsing
    parser = argparse.ArgumentParser(
        description="Generate Replay - Headless Simulation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulacion basica con config.json por defecto
  python run_generate_replay.py
  
  # Simulacion con configuracion personalizada
  python run_generate_replay.py --config config_test.json
  
  # Simulacion con exportacion de metricas para optimizacion
  python run_generate_replay.py --output-metrics temp_metrics/output.json
  
  # Combinacion: config personalizada + metricas
  python run_generate_replay.py --config custom.json --output-metrics metrics.json
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path a archivo config.json personalizado (default: config.json en raiz del proyecto)'
    )
    
    parser.add_argument(
        '--output-metrics',
        type=str,
        default=None,
        metavar='PATH',
        help='Path donde exportar metricas de optimizacion en formato JSON'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("GENERADOR DE REPLAY - GEMELO DIGITAL")
    print("Modo: Headless (maxima velocidad, sin interfaz)")
    if args.config:
        print(f"Config: {args.config}")
    if args.output_metrics:
        print(f"Metricas: {args.output_metrics}")
    print("="*60)
    print()
    
    # Crear generador y ejecutar
    generator = EventGenerator(
        headless_mode=True,
        config_path=args.config,
        output_metrics_path=args.output_metrics
    )
    
    success = generator.ejecutar()
    
    if success:
        print("\nExito: Archivos generados en output/")
        if args.output_metrics:
            print(f"Metricas exportadas: {args.output_metrics}")
        return 0
    else:
        print("\nError: Fallo al generar archivos")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)