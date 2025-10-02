#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 'O' key functionality in actual replay with full debug output
"""

def test_o_key_in_replay():
    """Test the O key during actual replay execution"""

    print("="*60)
    print("TESTING 'O' KEY IN ACTUAL REPLAY WITH DEBUG")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual

        # Clear state first
        estado_visual.clear()
        print("[TEST] estado_visual cleared")

        # Create ReplayEngine
        engine = ReplayViewerEngine()
        print("[TEST] ReplayEngine created")

        # Simulate the replay loading process manually
        import json

        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"
        print(f"[TEST] Loading replay file: {replay_file}")

        # Load SIMULATION_START event
        initial_work_orders = []
        with open(replay_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line.strip())
                    if event.get('event_type') == 'SIMULATION_START':
                        initial_work_orders = event.get('initial_work_orders', [])
                        print(f"[TEST] Found SIMULATION_START with {len(initial_work_orders)} WorkOrders")
                        break

        # Simulate inicializar_estado
        print("[TEST] Calling inicializar_estado...")
        from subsystems.visualization.state import inicializar_estado
        inicializar_estado(None, None, engine.configuracion, engine.layout_manager)

        print("[TEST] After inicializar_estado:")
        print(f"[TEST] estado_visual keys: {list(estado_visual.keys())}")
        print(f"[TEST] work_orders in estado_visual: {'work_orders' in estado_visual}")
        if 'work_orders' in estado_visual:
            print(f"[TEST] work_orders count: {len(estado_visual['work_orders'])}")

        # Apply the BUGFIX V10.0.6 manually
        print("[TEST] Applying BUGFIX V10.0.6...")
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

        print("[TEST] After BUGFIX V10.0.6:")
        print(f"[TEST] estado_visual keys: {list(estado_visual.keys())}")
        print(f"[TEST] work_orders count: {len(estado_visual.get('work_orders', {}))}")

        # Now test the 'O' key functionality
        print("\n[TEST] Testing 'O' key functionality...")
        print("[TEST] This should show data provider debug output:")

        # Simulate pressing 'O' key
        engine.toggle_order_dashboard()

        return True

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_o_key_in_replay()
    print("\n" + "="*60)
    if success:
        print("TEST COMPLETED - Check debug output above")
    else:
        print("TEST FAILED")
    print("="*60)