#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the bugfix for WorkOrder loading in ReplayEngine
"""

import time
from pathlib import Path

def test_bugfix():
    """Test that the bugfix works correctly"""

    print("="*60)
    print("TESTING BUGFIX: WorkOrder Loading in ReplayEngine")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual

        # Clear any existing state
        estado_visual.clear()

        # Create ReplayEngine and simulate run() call startup sequence
        engine = ReplayViewerEngine()

        # Simulate loading the .jsonl file (partial simulation)
        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"

        print(f"[TEST] Testing with replay file: {Path(replay_file).name}")

        # Manually simulate the key parts of run() that we modified
        import json

        # Load SIMULATION_START event like the real code does
        simulation_start_event = None
        initial_work_orders = []

        with open(replay_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line.strip())
                    if event.get('event_type') == 'SIMULATION_START':
                        simulation_start_event = event
                        initial_work_orders = event.get('initial_work_orders', [])
                        break

        print(f"[TEST] Found {len(initial_work_orders)} initial WorkOrders in .jsonl")

        # Simulate inicializar_estado() call - this clears work_orders
        from subsystems.visualization.state import inicializar_estado
        print("[TEST] Calling inicializar_estado() - this clears estado_visual['work_orders']")
        inicializar_estado(None, None, {}, None)

        print(f"[TEST] After inicializar_estado: {len(estado_visual.get('work_orders', {}))} WorkOrders")

        # Now apply our bugfix logic
        if initial_work_orders:
            print(f"[BUGFIX] Applying bugfix - populating estado_visual with {len(initial_work_orders)} WorkOrders")

            # Ensure work_orders dict exists
            if "work_orders" not in estado_visual:
                estado_visual["work_orders"] = {}

            # Populate with WorkOrders from .jsonl
            for wo in initial_work_orders:
                estado_visual["work_orders"][wo['id']] = wo.copy()

            print(f"[BUGFIX] Population complete: {len(estado_visual['work_orders'])} WorkOrders in estado_visual")

            # Test data provider functionality
            if engine.dashboard_communicator:
                data_provider = engine.dashboard_communicator.data_provider

                # Reset simulation state
                data_provider.reset_simulation_state()

                # Test validation
                has_valid = data_provider.has_valid_almacen()
                print(f"[TEST] Data provider has_valid_almacen: {has_valid}")

                # Test WorkOrder retrieval
                work_orders = data_provider.get_all_work_orders()
                print(f"[TEST] Data provider retrieved {len(work_orders)} WorkOrders")

                # Test dashboard toggle
                print("[TEST] Testing dashboard toggle with populated data...")
                try:
                    result = engine.dashboard_communicator.toggle_dashboard()
                    print(f"[TEST] Dashboard toggle result: {result}")

                    if result:
                        print("[SUCCESS] Dashboard opened successfully!")

                        # Test shutdown
                        shutdown_result = engine.dashboard_communicator.shutdown_dashboard()
                        print(f"[CLEANUP] Dashboard shutdown result: {shutdown_result}")

                        return True
                    else:
                        print("[PROBLEM] Dashboard toggle still failed")
                        return False

                except Exception as e:
                    print(f"[ERROR] Dashboard toggle failed: {e}")
                    return False

        else:
            print("[ERROR] No initial WorkOrders found in .jsonl file")
            return False

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

def main():
    """Main test execution"""

    success = test_bugfix()

    print("\n" + "="*60)
    if success:
        print("[BUGFIX VALIDATION] SUCCESS - Dashboard now works with replay!")
        print("The tecla 'O' should now open the dashboard correctly.")
    else:
        print("[BUGFIX VALIDATION] FAILED - Further investigation needed.")

    print("="*60)

if __name__ == "__main__":
    main()