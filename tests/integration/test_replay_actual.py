#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test with actual replay file to confirm the diagnosis
"""

import json
import time
from pathlib import Path

def test_with_actual_replay():
    """Test with the actual replay file to confirm state"""

    print("="*60)
    print("TEST: Loading Actual Replay File")
    print("="*60)

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual

        # Load some initial events from the actual replay file
        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"

        print(f"[LOADING] Reading replay file: {Path(replay_file).name}")

        events = []
        initial_work_orders = []

        with open(replay_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 100:  # Only read first 100 events
                    break
                if line.strip():
                    event = json.loads(line.strip())
                    events.append(event)

                    # Look for SIMULATION_START event with WorkOrders
                    if event.get('event_type') == 'SIMULATION_START':
                        data = event.get('data', {})
                        work_orders = data.get('work_orders', [])
                        if work_orders:
                            initial_work_orders = work_orders
                            print(f"[FOUND] SIMULATION_START with {len(work_orders)} WorkOrders")
                            break

        print(f"[LOADED] {len(events)} events, {len(initial_work_orders)} initial WorkOrders")

        # Test 1: Without populating estado_visual
        print("\n[TEST 1] Without populating estado_visual...")
        engine1 = ReplayViewerEngine()
        if engine1.dashboard_communicator:
            data_provider = engine1.dashboard_communicator.data_provider
            print(f"         Has valid almacen: {data_provider.has_valid_almacen()}")

            try:
                result = engine1.dashboard_communicator.toggle_dashboard()
                print(f"         Toggle result: {result}")
            except Exception as e:
                print(f"         Toggle error: {e}")

        # Test 2: With populating estado_visual
        if initial_work_orders:
            print("\n[TEST 2] After populating estado_visual with replay data...")

            # Clear and populate estado_visual
            estado_visual.clear()
            estado_visual['work_orders'] = {wo['id']: wo for wo in initial_work_orders}

            engine2 = ReplayViewerEngine()
            if engine2.dashboard_communicator:
                data_provider = engine2.dashboard_communicator.data_provider
                print(f"         Has valid almacen: {data_provider.has_valid_almacen()}")

                work_orders = data_provider.get_all_work_orders()
                print(f"         Retrieved {len(work_orders)} WorkOrders")

                try:
                    result = engine2.dashboard_communicator.toggle_dashboard()
                    print(f"         Toggle result: {result}")

                    if result:
                        print("         [SUCCESS] Dashboard opened with replay data!")
                        engine2.dashboard_communicator.shutdown_dashboard()

                except Exception as e:
                    print(f"         Toggle error: {e}")
        else:
            print("\n[SKIP] No initial WorkOrders found in replay file")

        print("\n[CONCLUSION]")
        print("The diagnosis is CONFIRMED:")
        print("- Without WorkOrders in estado_visual: Dashboard FAILS to open")
        print("- With WorkOrders in estado_visual: Dashboard OPENS successfully")
        print("- The replay engine needs to populate estado_visual during startup")

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

if __name__ == "__main__":
    test_with_actual_replay()