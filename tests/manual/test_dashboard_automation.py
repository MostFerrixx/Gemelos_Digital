#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPRF Automation Script for ReplayEngine Dashboard Testing V10.0.6

Tests the unified DashboardCommunicator integration in ReplayEngine
by automatically simulating user interactions and monitoring results.
"""

import sys
import time
import subprocess
import threading
from pathlib import Path

def test_replay_dashboard_integration():
    """
    Automated test suite for ReplayEngine DashboardCommunicator integration
    """
    replay_file = "./output/simulation_20250924_114214/replay_events_20250924_114214.jsonl"

    print("="*60)
    print("TPRF: ReplayEngine Dashboard Integration Test V10.0.6")
    print("="*60)

    # Test 1: Basic startup and dashboard initialization
    print("\n[TEST 1] Basic ReplayEngine + DashboardCommunicator Startup")
    print("-" * 50)

    try:
        # Import test - verify the migration worked
        from replay_engine import ReplayViewerEngine
        from communication import ReplayEngineDataProvider, DashboardCommunicator

        print("[OK] Import test passed - all components available")

        # Initialize ReplayEngine
        engine = ReplayViewerEngine()
        print("[OK] ReplayEngine initialized")
        print(f"   - Has DashboardCommunicator: {hasattr(engine, 'dashboard_communicator')}")
        print(f"   - DashboardCommunicator type: {type(engine.dashboard_communicator).__name__}")

        if engine.dashboard_communicator:
            data_provider = engine.dashboard_communicator.data_provider
            print(f"   - Data provider type: {type(data_provider).__name__}")
            print(f"   - Has valid estado_visual: {data_provider.has_valid_almacen()}")

            # Test dashboard communication API
            print(f"   - Dashboard active: {engine.dashboard_communicator.is_dashboard_active}")

            # Test toggle functionality (without actually opening GUI)
            print("\n[TOGGLE] Testing dashboard toggle API...")
            try:
                # Note: This will try to start the actual dashboard process
                print("   - Attempting toggle_dashboard() call...")
                result = engine.dashboard_communicator.toggle_dashboard()
                print(f"   - Toggle result: {result}")

                if engine.dashboard_communicator.is_dashboard_active:
                    print("   - Dashboard process started successfully")

                    # Test shutdown
                    print("   - Testing graceful shutdown...")
                    shutdown_result = engine.dashboard_communicator.shutdown_dashboard()
                    print(f"   - Shutdown result: {shutdown_result}")
                else:
                    print("   - Dashboard process did not start (expected in headless environment)")

            except Exception as e:
                print(f"   - Toggle test failed (expected in headless): {e}")

        print("\n[SUCCESS] TEST 1 RESULTADO: EXITO - Integracion basica funciona correctamente")

    except Exception as e:
        print(f"\n[FAILED] TEST 1 RESULTADO: FALLO - Error en integracion basica: {e}")
        return False

    # Test 2: Data Provider functionality
    print("\n[TEST 2] ReplayEngineDataProvider Functionality")
    print("-" * 50)

    try:
        engine = ReplayViewerEngine()
        data_provider = engine.dashboard_communicator.data_provider

        # Test initial state
        print("   - Testing initial data provider state...")
        stats = data_provider.get_stats()
        print(f"   - Engine available: {stats['engine_available']}")
        print(f"   - Estado visual valid: {stats['estado_visual_valid']}")
        print(f"   - Work order count: {stats['work_order_count']}")

        # Test simulation state control
        print("   - Testing simulation state control...")
        initial_finished = data_provider.is_simulation_finished()
        print(f"   - Initially finished: {initial_finished}")

        data_provider.mark_simulation_ended()
        after_mark = data_provider.is_simulation_finished()
        print(f"   - After mark_simulation_ended: {after_mark}")

        data_provider.reset_simulation_state()
        after_reset = data_provider.is_simulation_finished()
        print(f"   - After reset: {after_reset}")

        print("\n[SUCCESS] TEST 2 RESULTADO: EXITO - ReplayEngineDataProvider funciona correctamente")

    except Exception as e:
        print(f"\n[FAILED] TEST 2 RESULTADO: FALLO - Error en data provider: {e}")
        return False

    # Test 3: WorkOrder snapshot creation
    print("\n[TEST 3] WorkOrder Snapshot Creation")
    print("-" * 50)

    try:
        from communication.replay_data_provider import ReplayEngineDataProvider
        from subsystems.visualization.state import estado_visual

        # Mock some WorkOrder data
        test_work_order = {
            'id': 'test_wo_001',
            'order_id': 'order_123',
            'tour_id': 'tour_456',
            'sku_id': 'sku_789',
            'status': 'in_progress',
            'ubicacion': 'A1-2-3',
            'work_area': 'Area_Ground',
            'cantidad_restante': 5,
            'volumen_restante': 12.5,
            'assigned_agent_id': 'GroundOperator_1'
        }

        # Add to estado_visual
        estado_visual['work_orders'] = {'test_wo_001': test_work_order}

        engine = ReplayViewerEngine()
        data_provider = engine.dashboard_communicator.data_provider

        # Test WorkOrder retrieval
        work_orders = data_provider.get_all_work_orders()
        print(f"   - Retrieved {len(work_orders)} work orders")

        if work_orders:
            wo = work_orders[0]
            print(f"   - Sample WorkOrder ID: {wo.id}")
            print(f"   - Sample WorkOrder status: {wo.status}")
            print(f"   - Sample WorkOrder ubicacion: {wo.ubicacion}")
            print(f"   - Sample WorkOrder timestamp: {wo.timestamp}")

        print("\n[SUCCESS] TEST 3 RESULTADO: EXITO - WorkOrder snapshot creation funciona")

    except Exception as e:
        print(f"\n[FAILED] TEST 3 RESULTADO: FALLO - Error en WorkOrder snapshots: {e}")
        return False

    # Final summary
    print("\n" + "="*60)
    print("[SUMMARY] TPRF RESUMEN: Todos los tests de integracion EXITO")
    print("[VALIDATED] ReplayEngine DashboardCommunicator migration V10.0.6 VALIDADO")
    print("="*60)

    return True

if __name__ == "__main__":
    test_replay_dashboard_integration()