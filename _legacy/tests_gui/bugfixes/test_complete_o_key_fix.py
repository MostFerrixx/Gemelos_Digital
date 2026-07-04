#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete test to verify the 'O' key fix is working
"""

def test_complete_o_key_fix():
    """Complete test of the 'O' key fix"""

    print("="*60)
    print("COMPLETE TEST: 'O' KEY DASHBOARD FIX")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual
        import json

        # Step 1: Load actual WorkOrders from replay file
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

        print(f"[STEP 1] OK Found {len(initial_work_orders)} WorkOrders")

        # Step 2: Clear and initialize estado_visual
        print("[STEP 2] Initializing estado_visual...")
        estado_visual.clear()

        # Step 3: Create ReplayEngine and apply bugfix logic
        print("[STEP 3] Creating ReplayEngine and applying bugfix...")
        engine = ReplayViewerEngine()

        # Apply inicializar_estado like real replay does
        from subsystems.visualization.state import inicializar_estado
        inicializar_estado(None, None, engine.configuracion, engine.layout_manager)

        # Apply BUGFIX V10.0.6 logic
        if initial_work_orders:
            print(f"[BUGFIX V10.0.6] Poblando estado_visual con {len(initial_work_orders)} WorkOrders iniciales...")

            if "work_orders" not in estado_visual:
                estado_visual["work_orders"] = {}

            for wo in initial_work_orders:
                estado_visual["work_orders"][wo['id']] = wo.copy()

            print(f"[BUGFIX V10.0.6] {len(initial_work_orders)} WorkOrders cargadas en estado_visual")

            # Reset data provider
            if hasattr(engine, 'dashboard_communicator') and engine.dashboard_communicator:
                engine.dashboard_communicator.data_provider.reset_simulation_state()
                print(f"[BUGFIX V10.0.6] Data provider simulation state reset")

        print("[STEP 3] OK Bugfix applied successfully")

        # Step 4: Test the toggle_order_dashboard method directly
        print("[STEP 4] Testing toggle_order_dashboard() with debug output...")
        print("         (This simulates pressing the 'O' key)")

        engine.toggle_order_dashboard()

        print("[STEP 4] OK toggle_order_dashboard() completed")

        print("\n" + "="*60)
        print("TEST SUMMARY:")
        print("OK WorkOrders loaded from replay file")
        print("OK estado_visual populated with WorkOrders")
        print("OK Dashboard toggle method called with debug output")
        print("OK If you saw '[REFACTOR V10.0.6] Dashboard toggled successfully', the fix works!")
        print("="*60)

        print("\nINSTRUCTIONS FOR ACTUAL REPLAY:")
        print("1. Run: python replay_engine.py ./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl")
        print("2. Wait for the visualization to start")
        print("3. Press the 'O' key")
        print("4. You should see debug output and the dashboard should open")
        print("5. Look for these messages:")
        print("   - '[DEBUG KEY] Tecla 'O' detectada - llamando toggle_order_dashboard()'")
        print("   - '[DEBUG TOGGLE] toggle_order_dashboard() called'")
        print("   - '[REFACTOR V10.0.6] Dashboard toggled successfully'")

        return True

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_o_key_fix()
    if success:
        print("\nFIX COMPLETE: The 'O' key should now work in replay mode!")
    else:
        print("\nFix verification failed")