# -*- coding: utf-8 -*-
"""
Test script for dashboard graceful shutdown during cleanup.
"""

import sys
import time
from simulation_engine import SimulationEngine

def test_graceful_cleanup():
    """Test DashboardCommunicator graceful shutdown during cleanup."""
    print("=== PRUEBA 1.3: CIERRE LIMPIO ===")
    print()

    try:
        # Create engine and full simulation
        print("1. Creating SimulationEngine with full simulation...")
        engine = SimulationEngine(headless_mode=True)

        if not engine.crear_simulacion():
            print("   X Failed to create simulation")
            return False

        print("   + Engine and simulation created successfully")

        # Verify DashboardCommunicator is ready
        if not engine.dashboard_communicator:
            print("   X DashboardCommunicator not available")
            return False

        # Start dashboard to test cleanup with active dashboard
        print("2. Starting dashboard for cleanup test...")
        dashboard_started = engine.dashboard_communicator.toggle_dashboard()
        print(f"   + Dashboard started: {dashboard_started}")

        # Send some updates to ensure dashboard is active
        print("3. Sending updates to ensure dashboard is active...")
        for i in range(2):
            result = engine.dashboard_communicator.update_dashboard_state()
            print(f"   + Update {i+1}: {result}")

        # Check communication stats before cleanup
        stats_before = engine.dashboard_communicator.communication_stats
        print("4. Stats before cleanup:")
        print(f"   + Messages sent: {stats_before.get('messages_sent', 0)}")
        print(f"   + Errors: {stats_before.get('errors_count', 0)}")

        # Test graceful cleanup
        print("5. Testing graceful cleanup via limpiar_recursos()...")
        try:
            engine.limpiar_recursos()
            print("   + limpiar_recursos() executed successfully")

            # Check if dashboard_communicator is properly cleaned up
            print("6. Verifying cleanup results...")
            if hasattr(engine, 'dashboard_communicator'):
                if engine.dashboard_communicator:
                    # Try to use it and see if it's still functional
                    try:
                        stats_after = engine.dashboard_communicator.communication_stats
                        print("   + DashboardCommunicator still accessible after cleanup")
                        print(f"   + Final messages sent: {stats_after.get('messages_sent', 0)}")
                    except Exception as e:
                        print(f"   ! DashboardCommunicator not fully functional after cleanup: {e}")
                else:
                    print("   + DashboardCommunicator properly set to None during cleanup")
            else:
                print("   + DashboardCommunicator attribute removed during cleanup")

        except Exception as e:
            print(f"   X Error during cleanup: {e}")
            return False

        print()
        print("=== PRUEBA 1.3: EXITO ===")
        return True

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_graceful_cleanup()
    sys.exit(0 if success else 1)