# -*- coding: utf-8 -*-
"""
Live Simulation Launcher - Aplicacion pura de simulacion sin capacidades de replay.
Refactorizado desde main.py - Solo simulacion live (visual y headless).
"""

import argparse
import os
import json
import time
import multiprocessing
import pygame
import sys

# Add src directory to Python path to allow for absolute imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import del motor de simulacion puro
from engines.simulation_engine import SimulationEngine


# ELIMINATED: ejecutar_modo_replay() function - All replay functionality removed for pure simulation
# ELIMINATED: Complete 405-line function for replay viewer capabilities
# def ejecutar_modo_replay(jsonl_file_path):
#     """
#     ELIMINATED: Replay functionality - This launcher only supports live simulation
#     """
#     pass


def main():
    """Funcion principal - Solo simulacion live (visual y headless)"""
    # Configurar argparse - ELIMINADO: --replay argument
    parser = argparse.ArgumentParser(description='Digital Twin Warehouse Live Simulator')
    parser.add_argument('--headless', action='store_true',
                       help='Ejecuta la simulacion en modo headless (sin UI)')
    # ELIMINATED: parser.add_argument('--replay', ...) - No replay support in pure simulation
    args = parser.parse_args()

    print("="*60)
    print("SIMULADOR DE ALMACEN - GEMELO DIGITAL")
    print("Simulacion Live v2.6 - Sin Capacidades de Replay")

    # ELIMINATED: Replay mode conditional - Only live simulation supported
    if args.headless:
        print("Modo HEADLESS - Maxima Velocidad")
    else:
        print("Modo Visual - Con Interfaz Grafica")
    print("="*60)
    print()

    # ELIMINATED: args.replay conditional block - No replay mode support
    # ELIMINATED: ejecutar_modo_replay() call - Function removed

    if args.headless:
        # MODO HEADLESS (existente)
        simulador = SimulationEngine(headless_mode=True)
        simulador.ejecutar()
    else:
        # MODO VISUAL (existente)
        print("INSTRUCCIONES:")
        print("1. Use 'python configurator.py' para crear/modificar configuraciones")
        print("2. Use 'python run_live_simulation.py' para modo visual")
        print("3. Use 'python run_live_simulation.py --headless' para modo de maxima velocidad")
        # ELIMINATED: "4. Use 'python main.py --replay archivo.jsonl' para modo replay viewer"
        print()
        print("El simulador buscara 'config.json' en el directorio actual.")
        print("Si no existe, usara configuracion por defecto.")
        print()

        simulador = SimulationEngine(headless_mode=False)
        simulador.ejecutar()


if __name__ == "__main__":
    main()