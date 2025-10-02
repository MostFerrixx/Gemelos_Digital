#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the PyQt6 dashboard fix to ensure it opens the correct dashboard
"""

def test_pyqt6_dashboard_fix():
    """Test that the correct PyQt6 dashboard is being used"""

    print("="*60)
    print("TESTING PYQT6 DASHBOARD FIX V10.0.7")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual
        import json

        # Step 1: Load WorkOrders from replay file
        print("[STEP 1] Loading WorkOrders from replay file...")
        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"
        initial_work_orders = []

        with open(replay_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line.strip())
                    if event.get('event_type') == 'SIMULATION_START':
                        initial_work_orders = event.get('initial_work_orders', [])
                        break

        print(f"[STEP 1] Found {len(initial_work_orders)} WorkOrders")

        # Step 2: Initialize estado_visual
        print("[STEP 2] Initializing estado_visual...")
        estado_visual.clear()

        # Step 3: Create ReplayEngine and apply bugfix
        print("[STEP 3] Creating ReplayEngine and applying bugfix...")
        engine = ReplayViewerEngine()

        # Apply inicializar_estado
        from subsystems.visualization.state import inicializar_estado
        inicializar_estado(None, None, engine.configuracion, engine.layout_manager)

        # Apply BUGFIX V10.0.6 logic
        if initial_work_orders:
            print(f"[BUGFIX V10.0.6] Populating estado_visual with {len(initial_work_orders)} WorkOrders...")

            if "work_orders" not in estado_visual:
                estado_visual["work_orders"] = {}

            for wo in initial_work_orders:
                estado_visual["work_orders"][wo['id']] = wo.copy()

            print(f"[BUGFIX V10.0.6] {len(initial_work_orders)} WorkOrders loaded in estado_visual")

            # Reset data provider
            if hasattr(engine, 'dashboard_communicator') and engine.dashboard_communicator:
                engine.dashboard_communicator.data_provider.reset_simulation_state()
                print(f"[BUGFIX V10.0.6] Data provider state reset")

        print("[STEP 3] Bugfix applied successfully")

        # Step 4: Test the dashboard function import
        print("[STEP 4] Testing PyQt6 dashboard import...")
        try:
            dashboard_target = engine.dashboard_communicator._get_dashboard_target_function()
            print(f"[STEP 4] Dashboard target function: {dashboard_target.__name__}")
            print(f"[STEP 4] Dashboard module: {dashboard_target.__module__}")

            if "pyqt_dashboard" in dashboard_target.__module__:
                print("[SUCCESS] PyQt6 dashboard target function imported correctly!")
            else:
                print(f"[ERROR] Wrong dashboard module: {dashboard_target.__module__}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to import dashboard function: {e}")
            return False

        # Step 5: Test the dashboard toggle
        print("[STEP 5] Testing dashboard toggle with PyQt6...")

        try:
            result = engine.dashboard_communicator.toggle_dashboard()
            print(f"[STEP 5] Dashboard toggle result: {result}")

            if result:
                print("[SUCCESS] PyQt6 dashboard opened successfully!")
                print("[INFO] Look for PyQt6 process messages instead of Tkinter!")

                # Wait a bit then close
                import time
                time.sleep(3)
                shutdown_result = engine.dashboard_communicator.shutdown_dashboard()
                print(f"[CLEANUP] Shutdown result: {shutdown_result}")
                return True
            else:
                print("[FAILED] Dashboard failed to open")
                return False

        except Exception as e:
            print(f"[STEP 5] Toggle error: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pyqt6_dashboard_fix()
    print("\n" + "="*60)
    if success:
        print("BUGFIX V10.0.7 SUCCESS: PyQt6 dashboard is now being used!")
        print("The 'O' key should now open the correct PyQt6 dashboard in replay mode.")
    else:
        print("BUGFIX V10.0.7 FAILED: PyQt6 dashboard fix needs more work")
    print("="*60)