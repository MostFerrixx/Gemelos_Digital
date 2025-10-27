# -*- coding: utf-8 -*-
"""
Generate Replay - Entry point para generar archivos .jsonl
Sin UI, solo generacion de eventos para replay
"""

import sys
import os

# Add src/ to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from engines.event_generator import EventGenerator


def main():
    """Funcion principal - Genera archivo .jsonl sin UI"""
    
    print("="*60)
    print("GENERADOR DE REPLAY - GEMELO DIGITAL")
    print("Modo: Headless (maxima velocidad, sin interfaz)")
    print("="*60)
    print()
    
    # Crear generador y ejecutar
    generator = EventGenerator(headless_mode=True)
    success = generator.ejecutar()
    
    if success:
        print("\nExito: Archivos generados en output/")
        return 0
    else:
        print("\nError: Fallo al generar archivos")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)