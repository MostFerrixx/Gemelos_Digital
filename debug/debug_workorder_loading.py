#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug why WorkOrder loading is not working in ReplayEngine
"""

import json
from pathlib import Path

def debug_current_loading_logic():
    """Debug the current loading logic"""

    replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"

    print("="*60)
    print("DEBUGGING CURRENT WORKORDER LOADING LOGIC")
    print("="*60)

    try:
        # Simulate the current ReplayEngine logic
        eventos = []
        simulation_start_event = None
        initial_work_orders = []

        with open(replay_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        event = json.loads(line.strip())

                        # This is the current logic from replay_engine.py line 485-494
                        if event.get('event_type') == 'SIMULATION_START':
                            simulation_start_event = event
                            initial_work_orders = event.get('initial_work_orders', [])
                            print(f"[DEBUG] Found SIMULATION_START at line {line_num}")
                            print(f"[DEBUG] initial_work_orders key exists: {'initial_work_orders' in event}")
                            print(f"[DEBUG] initial_work_orders length: {len(initial_work_orders)}")

                            if initial_work_orders:
                                sample_wo = initial_work_orders[0]
                                print(f"[DEBUG] Sample WorkOrder keys: {list(sample_wo.keys())}")
                                print(f"[DEBUG] Sample WorkOrder: {sample_wo}")
                            break
                        else:
                            eventos.append(event)

                    except json.JSONDecodeError as e:
                        print(f"[ERROR] JSON decode error at line {line_num}: {e}")

        print(f"\n[RESULT] simulation_start_event: {simulation_start_event is not None}")
        print(f"[RESULT] initial_work_orders count: {len(initial_work_orders)}")

        # Test the estado_visual population logic
        if initial_work_orders:
            print(f"\n[TEST] Would populate estado_visual with {len(initial_work_orders)} WorkOrders")

            # Show what the population would look like
            estado_visual_mock = {"work_orders": {}}
            for wo in initial_work_orders[:3]:  # Just first 3 for display
                estado_visual_mock["work_orders"][wo['id']] = wo.copy()
                print(f"  - {wo['id']}: {wo.get('status', 'no_status')}")

            print(f"[TEST] estado_visual would have {len(estado_visual_mock['work_orders'])} WorkOrders")

        else:
            print("[PROBLEM] No initial_work_orders found - this explains the dashboard issue!")

    except Exception as e:
        print(f"[ERROR] Debug failed: {e}")

if __name__ == "__main__":
    debug_current_loading_logic()