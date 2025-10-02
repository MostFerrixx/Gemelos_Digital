#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug why the 'O' key press is not working in replay mode
"""

import time
from pathlib import Path

def debug_o_key_functionality():
    """Debug the current 'O' key handling in replay mode"""

    print("="*60)
    print("DEBUGGING 'O' KEY FUNCTIONALITY IN REPLAY")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual

        # Clear state
        estado_visual.clear()

        # Create ReplayEngine
        engine = ReplayViewerEngine()

        print(f"[DEBUG] ReplayEngine created")
        print(f"[DEBUG] dashboard_communicator exists: {engine.dashboard_communicator is not None}")

        if engine.dashboard_communicator:
            print(f"[DEBUG] dashboard_communicator type: {type(engine.dashboard_communicator)}")
            print(f"[DEBUG] data_provider exists: {engine.dashboard_communicator.data_provider is not None}")

            # Test the data provider state
            data_provider = engine.dashboard_communicator.data_provider
            print(f"[DEBUG] data_provider type: {type(data_provider)}")

            # Check if has_valid_almacen works
            try:
                has_valid = data_provider.has_valid_almacen()
                print(f"[DEBUG] has_valid_almacen: {has_valid}")
            except Exception as e:
                print(f"[DEBUG] has_valid_almacen error: {e}")

            # Check WorkOrders count
            try:
                work_orders = data_provider.get_all_work_orders()
                print(f"[DEBUG] work_orders count: {len(work_orders)}")
            except Exception as e:
                print(f"[DEBUG] get_all_work_orders error: {e}")

            # Test toggle_order_dashboard directly
            print("\n[TEST] Testing toggle_order_dashboard() directly...")
            try:
                engine.toggle_order_dashboard()
                print("[TEST] toggle_order_dashboard() completed")
            except Exception as e:
                print(f"[TEST] toggle_order_dashboard() error: {e}")

        else:
            print("[ERROR] dashboard_communicator is None!")

    except Exception as e:
        print(f"[ERROR] Debug failed: {e}")
        import traceback
        traceback.print_exc()

def debug_with_loaded_workorders():
    """Debug after loading WorkOrders like the bugfix does"""

    print("\n" + "="*60)
    print("DEBUGGING WITH LOADED WORKORDERS")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual
        import json

        # Load WorkOrders from actual replay file
        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"
        initial_work_orders = []

        with open(replay_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line.strip())
                    if event.get('event_type') == 'SIMULATION_START':
                        # CORRECT: Look for initial_work_orders directly in event
                        work_orders = event.get('initial_work_orders', [])
                        if work_orders:
                            initial_work_orders = work_orders
                            break

        print(f"[DEBUG] Found {len(initial_work_orders)} WorkOrders in replay file")

        # Clear and populate estado_visual like the bugfix does
        estado_visual.clear()
        if initial_work_orders:
            estado_visual["work_orders"] = {wo['id']: wo for wo in initial_work_orders}
            print(f"[DEBUG] Populated estado_visual with {len(estado_visual['work_orders'])} WorkOrders")

        # Create ReplayEngine
        engine = ReplayViewerEngine()

        if engine.dashboard_communicator:
            # Reset data provider state like bugfix does
            engine.dashboard_communicator.data_provider.reset_simulation_state()

            # Test validation
            data_provider = engine.dashboard_communicator.data_provider
            has_valid = data_provider.has_valid_almacen()
            work_orders = data_provider.get_all_work_orders()

            print(f"[DEBUG] After reset - has_valid_almacen: {has_valid}")
            print(f"[DEBUG] After reset - work_orders count: {len(work_orders)}")

            # Test toggle
            print("\n[TEST] Testing toggle with loaded WorkOrders...")
            try:
                result = engine.dashboard_communicator.toggle_dashboard()
                print(f"[TEST] Dashboard toggle result: {result}")

                if result:
                    print("[SUCCESS] Dashboard opened!")
                    # Give it a moment then close
                    time.sleep(2)
                    shutdown_result = engine.dashboard_communicator.shutdown_dashboard()
                    print(f"[CLEANUP] Shutdown result: {shutdown_result}")
                else:
                    print("[FAILED] Dashboard failed to open")

            except Exception as e:
                print(f"[TEST] Toggle error: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"[ERROR] Debug with WorkOrders failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_o_key_functionality()
    debug_with_loaded_workorders()