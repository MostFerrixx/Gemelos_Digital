#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal replay test to isolate the hang issue
"""

def test_minimal_replay():
    """Test basic replay functionality step by step"""

    print("=== MINIMAL REPLAY TEST ===")

    try:
        # Step 1: Import and create engine
        print("Step 1: Creating ReplayViewerEngine...")
        from replay_engine import ReplayViewerEngine
        engine = ReplayViewerEngine()
        print("Step 1: OK - Engine created")

        # Step 2: Test pygame initialization
        print("Step 2: Testing pygame initialization...")
        engine.inicializar_pygame()
        print("Step 2: OK - Pygame initialized")

        # Step 3: Test file loading
        print("Step 3: Testing file loading...")
        import json
        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"

        eventos = []
        initial_work_orders = []
        simulation_start_event = None

        with open(replay_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line_num > 100:  # Only read first 100 lines to avoid hang
                    break
                if line.strip():
                    try:
                        event = json.loads(line.strip())
                        if event.get('event_type') == 'SIMULATION_START':
                            simulation_start_event = event
                            initial_work_orders = event.get('initial_work_orders', [])
                            print(f"Step 3: Found SIMULATION_START with {len(initial_work_orders)} WorkOrders")
                        else:
                            eventos.append(event)
                    except json.JSONDecodeError as e:
                        print(f"Step 3: JSON error at line {line_num}: {e}")
                        continue

        print(f"Step 3: OK - Loaded {len(eventos)} events, {len(initial_work_orders)} WorkOrders")

        # Step 4: Test estado_visual initialization
        print("Step 4: Testing estado_visual initialization...")
        from subsystems.visualization.state import estado_visual, inicializar_estado

        estado_visual.clear()
        print("Step 4a: estado_visual cleared")

        configuracion = engine.configuracion
        layout_manager = engine.layout_manager
        print("Step 4b: Got configuration and layout_manager")

        inicializar_estado(None, None, configuracion, layout_manager)
        print("Step 4c: inicializar_estado completed")

        print(f"Step 4: OK - estado_visual initialized with keys: {list(estado_visual.keys())}")

        # Step 5: Test WorkOrder population
        print("Step 5: Testing WorkOrder population...")
        if initial_work_orders:
            if "work_orders" not in estado_visual:
                estado_visual["work_orders"] = {}

            for i, wo in enumerate(initial_work_orders[:5]):  # Only first 5 to avoid issues
                estado_visual["work_orders"][wo['id']] = wo.copy()
                if i == 0:
                    print(f"Step 5a: Added sample WorkOrder {wo['id']}")

            print(f"Step 5: OK - Added 5 WorkOrders to estado_visual")
        else:
            print("Step 5: SKIP - No WorkOrders found")

        print("\n=== ALL STEPS COMPLETED SUCCESSFULLY ===")
        print("The hang is likely in pygame main loop or event handling")
        return True

    except Exception as e:
        print(f"ERROR in step: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_minimal_replay()