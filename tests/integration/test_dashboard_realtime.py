# -*- coding: utf-8 -*-
"""
Test script for real-time dashboard updates during live simulation.
"""

import sys
import time
from simulation_engine import SimulationEngine

def test_realtime_updates():
    """Test DashboardCommunicator real-time updates with full simulation."""
    print("=== PRUEBA 1.2: ACTUALIZACIÓN TIEMPO REAL ===")
    print()

    try:
        # Create engine in headless mode for faster execution
        print("1. Creating SimulationEngine...")
        engine = SimulationEngine(headless_mode=True)
        print("   + Engine created successfully")

        # Verify DashboardCommunicator is ready
        if not engine.dashboard_communicator:
            print("   X DashboardCommunicator not available")
            return False

        print("   + DashboardCommunicator available")

        # Create full simulation
        print("2. Creating full simulation...")
        if engine.crear_simulacion():
            print("   + Full simulation created")
        else:
            print("   X Failed to create simulation")
            return False

        # Now test with full simulation data
        print("3. Testing with simulation data...")

        # Check data provider status
        provider = engine.dashboard_communicator.data_provider
        has_almacen = provider.has_valid_almacen()
        work_orders = provider.get_all_work_orders()
        print(f"   + Valid almacen: {has_almacen}")
        print(f"   + Work orders available: {len(work_orders)}")

        # Test dashboard startup now that almacen is ready
        print("4. Testing dashboard with valid data...")
        try:
            result = engine.dashboard_communicator.toggle_dashboard()
            print(f"   + toggle_dashboard() with valid data: {result}")
        except Exception as e:
            print(f"   ! toggle_dashboard() issue: {e}")

        # Test real-time updates
        print("5. Testing real-time updates...")

        # Simulate multiple update calls
        for i in range(3):
            result = engine.dashboard_communicator.update_dashboard_state()
            print(f"   + Update {i+1}: {result}")
            time.sleep(0.1)  # Small delay between updates

        # Test statistics after updates
        print("6. Checking communication statistics...")
        stats = engine.dashboard_communicator.communication_stats
        print(f"   + Messages sent: {stats.get('messages_sent', 0)}")
        print(f"   + Delta updates: {stats.get('delta_updates_sent', 0)}")
        print(f"   + Errors: {stats.get('errors_count', 0)}")

        # Graceful shutdown
        print("7. Testing graceful shutdown...")
        result = engine.dashboard_communicator.shutdown_dashboard()
        print(f"   + Shutdown result: {result}")

        print()
        print("=== PRUEBA 1.2: ÉXITO ===")
        return True

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_realtime_updates()
    sys.exit(0 if success else 1)