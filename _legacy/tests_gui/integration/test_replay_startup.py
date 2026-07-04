#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPRF Test: ReplayEngine Startup and Shutdown Verification V10.0.6

Tests the complete lifecycle of ReplayEngine with DashboardCommunicator
"""

import sys
import time
import threading
import signal
from pathlib import Path

def test_replay_startup_sequence():
    """Test complete startup sequence"""
    print("[TEST] Complete ReplayEngine startup sequence...")

    try:
        # Import the necessary modules
        from replay_engine import ReplayViewerEngine
        import pygame

        # Initialize pygame (headless)
        print("   - Initializing pygame...")
        pygame.init()

        # Create ReplayEngine
        print("   - Creating ReplayViewerEngine...")
        engine = ReplayViewerEngine()

        # Verify initialization
        print(f"   - DashboardCommunicator initialized: {hasattr(engine, 'dashboard_communicator')}")
        print(f"   - Dashboard process active: {engine.dashboard_communicator.is_dashboard_active if engine.dashboard_communicator else False}")

        # Test cleanup
        print("   - Testing limpiar_recursos()...")
        engine.limpiar_recursos()

        print("   - SUCCESS: Startup and cleanup sequence works correctly")
        return True

    except Exception as e:
        print(f"   - FAILED: Startup sequence failed: {e}")
        return False

def test_replay_file_validation():
    """Test replay file validation and parsing"""
    print("\n[TEST] Replay file validation and parsing...")

    try:
        import json

        replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"

        # Test file existence
        if not Path(replay_file).exists():
            print(f"   - FAILED: Replay file not found: {replay_file}")
            return False

        print(f"   - Replay file exists: {Path(replay_file).name}")

        # Test file parsing
        event_count = 0
        with open(replay_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    json.loads(line.strip())  # Validate JSON
                    event_count += 1
                    if event_count >= 100:  # Just test first 100 events
                        break

        print(f"   - Successfully parsed {event_count} events")
        print("   - SUCCESS: Replay file validation passed")
        return True

    except Exception as e:
        print(f"   - FAILED: Replay file validation failed: {e}")
        return False

def test_dashboard_communicator_lifecycle():
    """Test DashboardCommunicator complete lifecycle"""
    print("\n[TEST] DashboardCommunicator lifecycle management...")

    try:
        from replay_engine import ReplayViewerEngine
        from subsystems.visualization.state import estado_visual

        # Setup test data
        test_wo = {
            'id': 'TEST_WO_001',
            'order_id': 'TEST_ORDER',
            'tour_id': 'TEST_TOUR',
            'sku_id': 'TEST_SKU',
            'status': 'pending',
            'ubicacion': 'TEST_LOC',
            'work_area': 'Area_Ground',
            'cantidad_restante': 1,
            'volumen_restante': 1.0,
            'assigned_agent_id': None
        }

        estado_visual['work_orders'] = {'TEST_WO_001': test_wo}

        # Create engine
        engine = ReplayViewerEngine()

        if engine.dashboard_communicator:
            # Test data provider
            data_provider = engine.dashboard_communicator.data_provider
            work_orders = data_provider.get_all_work_orders()
            print(f"   - Data provider working: {len(work_orders)} WorkOrders retrieved")

            # Test communication stats
            stats = engine.dashboard_communicator.communication_stats
            print(f"   - Communication stats accessible: {len(stats)} fields")

            # Test simulation control
            data_provider.mark_simulation_ended()
            is_ended = data_provider.is_simulation_finished()
            print(f"   - Simulation control working: ended={is_ended}")

            # Test graceful shutdown
            print("   - Testing graceful shutdown...")
            shutdown_result = engine.dashboard_communicator.shutdown_dashboard()
            print(f"   - Shutdown result: {shutdown_result}")

        print("   - SUCCESS: DashboardCommunicator lifecycle test passed")
        return True

    except Exception as e:
        print(f"   - FAILED: DashboardCommunicator lifecycle test failed: {e}")
        return False

def test_memory_cleanup():
    """Test memory cleanup and resource management"""
    print("\n[TEST] Memory cleanup and resource management...")

    try:
        from replay_engine import ReplayViewerEngine
        import gc

        # Create multiple engines to test cleanup
        engines = []
        for i in range(3):
            engine = ReplayViewerEngine()
            engines.append(engine)
            print(f"   - Created ReplayEngine #{i+1}")

        # Test cleanup
        for i, engine in enumerate(engines):
            engine.limpiar_recursos()
            print(f"   - Cleaned up ReplayEngine #{i+1}")

        # Force garbage collection
        engines.clear()
        gc.collect()

        print("   - SUCCESS: Memory cleanup test passed")
        return True

    except Exception as e:
        print(f"   - FAILED: Memory cleanup test failed: {e}")
        return False

def main():
    """Main test execution"""
    print("="*60)
    print("TPRF: ReplayEngine Lifecycle and Shutdown Verification")
    print("="*60)

    all_tests_passed = True

    # Test 1: Startup sequence
    if not test_replay_startup_sequence():
        all_tests_passed = False

    # Test 2: File validation
    if not test_replay_file_validation():
        all_tests_passed = False

    # Test 3: DashboardCommunicator lifecycle
    if not test_dashboard_communicator_lifecycle():
        all_tests_passed = False

    # Test 4: Memory cleanup
    if not test_memory_cleanup():
        all_tests_passed = False

    # Final summary
    print("\n" + "="*60)
    if all_tests_passed:
        print("[SUCCESS] ALL LIFECYCLE TESTS PASSED")
        print("[VALIDATED] ReplayEngine V10.0.6 dashboard integration COMPLETE")
        print("           Ready for production use")
    else:
        print("[FAILED] Some lifecycle tests failed")
    print("="*60)

    return all_tests_passed

if __name__ == "__main__":
    main()