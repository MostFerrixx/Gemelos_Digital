# -*- coding: utf-8 -*-
"""
Replay Viewer Launcher - Punto de entrada simplificado para el visualizador de replay.
Refactorizado para ser solo un lanzador puro - toda la logica esta en ReplayViewerEngine.
"""

import argparse
import os

# Import del motor de replay - Toda la magia esta aqui
from replay_engine import ReplayViewerEngine


def main():
    """Launcher principal - Solo parseo de argumentos y delegacion al motor"""

    # Configurar argparse
    parser = argparse.ArgumentParser(description='Digital Twin Warehouse Replay Viewer')
    parser.add_argument('replay', type=str, metavar='FILE.jsonl',
                       help='Archivo .jsonl de replay para visualizar')
    args = parser.parse_args()

    print("="*60)
    print("REPLAY VIEWER - GEMELO DIGITAL")
    print("Visualizador de Archivos .jsonl v10.0")
    print("Modo REPLAY VIEWER - Visualizacion de Archivo .jsonl")
    print(f"Archivo: {args.replay}")
    print("="*60)
    print()

    # Validar archivo existe
    if not os.path.exists(args.replay):
        print(f"Error: Archivo de replay no encontrado: {args.replay}")
        return 1

    print(f"[REPLAY-VIEWER] Iniciando visualizador de replay")

    # SIMPLICIDAD EXTREMA: Solo crear motor y ejecutar
    engine = ReplayViewerEngine()
    return engine.run(args.replay)


if __name__ == "__main__":
    main()