#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test real replay execution to see if bugfix is working
"""

import time
import sys
from pathlib import Path

def test_real_replay_execution():
    """Test actual replay execution to see debug output"""

    print("="*60)
    print("TESTING REAL REPLAY EXECUTION")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual

        # Clear state
        estado_visual.clear()
        print("[TEST] Estado visual cleared")

        # Create ReplayEngine
        engine = ReplayViewerEngine()
        print("[TEST] ReplayEngine created")

        # Mock the run method to just do the initialization part
        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"

        # Simulate just the file loading part
        print(f"[TEST] Simulating file loading from: {Path(replay_file).name}")

        import json
        eventos = []
        simulation_start_event = None
        initial_work_orders = []

        with open(replay_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line.strip())
                        if event.get('event_type') == 'SIMULATION_START':
                            simulation_start_event = event
                            initial_work_orders = event.get('initial_work_orders', [])
                            print(f"[TEST] Found SIMULATION_START with {len(initial_work_orders)} WorkOrders")
                            break
                        else:
                            eventos.append(event)
                    except json.JSONDecodeError as e:
                        print(f"[TEST] JSON decode error: {e}")
                        continue

        print(f"[TEST] Loaded: {len(eventos)} events, {len(initial_work_orders)} initial WorkOrders")

        # Now simulate the estado_visual initialization
        print("[TEST] Simulating inicializar_estado()...")
        from subsystems.visualization.state import inicializar_estado
        configuracion = engine.configuracion
        layout_manager = engine.layout_manager

        inicializar_estado(None, None, configuracion, layout_manager)
        print(f"[TEST] After inicializar_estado: work_orders = {len(estado_visual.get('work_orders', {}))}")

        # Now apply the bugfix logic
        print("[TEST] Applying BUGFIX V10.0.6 logic...")
        if initial_work_orders:
            print(f"[BUGFIX V10.0.6] Poblando estado_visual con {len(initial_work_orders)} WorkOrders iniciales...")

            # Asegurar que el diccionario work_orders existe
            if "work_orders" not in estado_visual:
                estado_visual["work_orders"] = {}

            # Poblar con WorkOrders del archivo .jsonl
            for wo in initial_work_orders:
                estado_visual["work_orders"][wo['id']] = wo.copy()

            print(f"[BUGFIX V10.0.6] {len(initial_work_orders)} WorkOrders cargadas en estado_visual")
            print(f"[BUGFIX V10.0.6] Dashboard data provider now has valid data")

            # Reset data provider
            if hasattr(engine, 'dashboard_communicator') and engine.dashboard_communicator:
                data_provider = engine.dashboard_communicator.data_provider
                if hasattr(data_provider, 'reset_simulation_state'):
                    data_provider.reset_simulation_state()
                    print(f"[BUGFIX V10.0.6] Data provider simulation state reset for new replay")

            # Test dashboard functionality
            print("[TEST] Testing dashboard after bugfix...")
            has_valid = engine.dashboard_communicator.data_provider.has_valid_almacen()
            work_orders = engine.dashboard_communicator.data_provider.get_all_work_orders()
            print(f"[TEST] has_valid_almacen: {has_valid}")
            print(f"[TEST] work_orders count: {len(work_orders)}")

            # Test toggle
            print("[TEST] Testing toggle_order_dashboard()...")
            try:
                result = engine.dashboard_communicator.toggle_dashboard()
                print(f"[TEST] Dashboard toggle result: {result}")

                if result:
                    print("[SUCCESS] Dashboard works after bugfix!")
                    time.sleep(2)
                    shutdown_result = engine.dashboard_communicator.shutdown_dashboard()
                    print(f"[CLEANUP] Shutdown result: {shutdown_result}")
                    return True
                else:
                    print("[FAILED] Dashboard still doesn't work")
                    return False

            except Exception as e:
                print(f"[TEST] Toggle error: {e}")
                return False
        else:
            print("[ERROR] No initial WorkOrders found - this explains why bugfix isn't working!")
            return False

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_replay_execution()
    print("\n" + "="*60)
    if success:
        print("[CONCLUSION] BUGFIX V10.0.6 IS WORKING CORRECTLY")
        print("The issue must be that 'O' key press is not reaching toggle_order_dashboard()")
    else:
        print("[CONCLUSION] BUGFIX V10.0.6 LOGIC HAS ISSUES")
        print("The WorkOrder loading is not working as expected")
    print("="*60)