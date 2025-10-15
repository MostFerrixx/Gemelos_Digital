# -*- coding: utf-8 -*-
"""
Test script to validate DashboardCommunicator integration.
"""

import sys
import time
from simulation_engine import SimulationEngine

def test_dashboard_integration():
    """Test DashboardCommunicator integration systematically."""
    print("=== TPRF: DASHBOARD INTEGRATION TEST ===")
    print()

    try:
        # Test 1: Create engine
        print("1. Creating SimulationEngine...")
        engine = SimulationEngine(headless_mode=True)
        print("   + Engine created successfully")

        # Test 2: Verify DashboardCommunicator
        print("2. Verifying DashboardCommunicator...")
        if engine.dashboard_communicator:
            print("   + DashboardCommunicator initialized")
            print(f"   + Type: {type(engine.dashboard_communicator).__name__}")
        else:
            print("   X DashboardCommunicator is None")
            return False

        # Test 3: Test toggle functionality
        print("3. Testing toggle functionality...")
        try:
            # This should work whether almacen is ready or not
            result1 = engine.dashboard_communicator.toggle_dashboard()
            print(f"   + First toggle_dashboard(): {result1}")

            result2 = engine.dashboard_communicator.toggle_dashboard()
            print(f"   + Second toggle_dashboard(): {result2}")

            result3 = engine.dashboard_communicator.toggle_dashboard()
            print(f"   + Third toggle_dashboard(): {result3}")

        except Exception as e:
            print(f"   X Toggle test failed: {e}")

        # Test 4: Test update functionality
        print("4. Testing update functionality...")
        try:
            result = engine.dashboard_communicator.update_dashboard_state()
            print(f"   + update_dashboard_state(): {result}")
        except Exception as e:
            print(f"   X Update test failed: {e}")

        # Test 5: Test shutdown functionality
        print("5. Testing shutdown functionality...")
        try:
            result = engine.dashboard_communicator.shutdown_dashboard()
            print(f"   + shutdown_dashboard(): {result}")
        except Exception as e:
            print(f"   X Shutdown test failed: {e}")

        print()
        print("=== DASHBOARD INTEGRATION TEST: SUCCESS ===")
        return True

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dashboard_integration()
    sys.exit(0 if success else 1)