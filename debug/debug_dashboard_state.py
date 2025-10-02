# -*- coding: utf-8 -*-
"""
Debug script to trace dashboard_communicator state changes.
"""

import sys
from simulation_engine import SimulationEngine

def debug_dashboard_state():
    """Debug where dashboard_communicator becomes None."""
    print("=== DEBUG: DASHBOARD STATE CHANGES ===")
    print()

    try:
        # Create engine
        print("1. Creating SimulationEngine...")
        engine = SimulationEngine(headless_mode=True)

        # Check initial state
        print("2. Initial dashboard_communicator state:")
        print(f"   Type: {type(engine.dashboard_communicator)}")
        print(f"   Is None: {engine.dashboard_communicator is None}")

        if engine.dashboard_communicator:
            print("   + DashboardCommunicator initialized correctly")
        else:
            print("   X DashboardCommunicator is None after __init__")
            return False

        # Call crear_simulacion and check state
        print("3. Calling crear_simulacion()...")
        result = engine.crear_simulacion()
        print(f"   crear_simulacion() returned: {result}")

        print("4. Dashboard_communicator state after crear_simulacion():")
        print(f"   Type: {type(engine.dashboard_communicator)}")
        print(f"   Is None: {engine.dashboard_communicator is None}")

        if engine.dashboard_communicator:
            print("   + DashboardCommunicator still available")

            # Test it works
            provider = engine.dashboard_communicator.data_provider
            has_almacen = provider.has_valid_almacen()
            work_orders = provider.get_all_work_orders()
            print(f"   + Valid almacen: {has_almacen}")
            print(f"   + Work orders: {len(work_orders)}")

            return True
        else:
            print("   X DashboardCommunicator became None after crear_simulacion()")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_dashboard_state()
    sys.exit(0 if success else 1)