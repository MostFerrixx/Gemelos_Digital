#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test replay with automated 'O' key press to verify the debug output
"""

import subprocess
import time
import sys
import threading

def simulate_o_key_press():
    """Simulate 'O' key press after a delay"""
    time.sleep(3)  # Wait 3 seconds for replay to start
    print("\n[SIMULATOR] Enviando tecla 'O' simulada en 2 segundos...")
    time.sleep(2)

    # Try to send the 'O' key using pyautogui if available
    try:
        import pyautogui
        print("[SIMULATOR] Enviando tecla 'o'...")
        pyautogui.press('o')
        print("[SIMULATOR] Tecla 'o' enviada")

        # Wait a bit and then ESC to close
        time.sleep(3)
        print("[SIMULATOR] Enviando ESC para cerrar...")
        pyautogui.press('escape')
        print("[SIMULATOR] ESC enviado")

    except ImportError:
        print("[SIMULATOR] pyautogui no disponible - presiona 'O' manualmente")
        print("[SIMULATOR] INSTRUCCIONES:")
        print("[SIMULATOR] 1. Asegúrate de que la ventana del replay esté enfocada")
        print("[SIMULATOR] 2. Presiona la tecla 'O' para probar el dashboard")
        print("[SIMULATOR] 3. Presiona ESC para cerrar")

def run_replay_test():
    """Run the replay engine for testing"""
    print("="*60)
    print("TESTING REPLAY WITH 'O' KEY DEBUG OUTPUT")
    print("="*60)

    # Start the key press simulator in a separate thread
    key_thread = threading.Thread(target=simulate_o_key_press)
    key_thread.daemon = True
    key_thread.start()

    try:
        # Run the replay engine
        from replay_engine import ReplayViewerEngine

        engine = ReplayViewerEngine()
        print("\n[TEST] ReplayEngine creado - iniciando replay...")
        print("[TEST] Busca el debug output cuando presiones 'O'")

        # Run the replay
        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"
        result = engine.run(replay_file)

        print(f"\n[TEST] Replay terminado con código: {result}")

    except Exception as e:
        print(f"[ERROR] Error durante replay: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_replay_test()