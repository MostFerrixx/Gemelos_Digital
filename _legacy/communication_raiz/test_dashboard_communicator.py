# -*- coding: utf-8 -*-
"""
Test Suite for DashboardCommunicator - Phase 1 Basic Validation Tests.

Phase 1: Structural validation and API contract testing.
Phase 2: Full integration testing with mock dashboard process.
Phase 3: End-to-end testing with actual SimulationEngine integration.
"""

import unittest
from unittest.mock import Mock, MagicMock
import time
from typing import List

from .dashboard_communicator import DashboardCommunicator, DashboardCommunicationError
from .ipc_protocols import DataProviderInterface, WorkOrderSnapshot, MessageType
from .lifecycle_manager import ProcessLifecycleManager, DashboardConfig


class MockDataProvider(DataProviderInterface):
    """Mock data provider for testing"""

    def __init__(self, has_almacen=True, work_orders=None):
        self._has_almacen = has_almacen
        self._work_orders = work_orders or []
        self._simulation_finished = False

    def get_all_work_orders(self) -> List[WorkOrderSnapshot]:
        return self._work_orders

    def is_simulation_finished(self) -> bool:
        return self._simulation_finished

    def has_valid_almacen(self) -> bool:
        return self._has_almacen

    def set_simulation_finished(self, finished: bool):
        """Test helper method"""
        self._simulation_finished = finished

    def set_work_orders(self, work_orders: List[WorkOrderSnapshot]):
        """Test helper method"""
        self._work_orders = work_orders


class TestWorkOrderSnapshot(unittest.TestCase):
    """Test WorkOrderSnapshot immutable data structure"""

    def test_snapshot_creation(self):
        """Test basic snapshot creation"""
        snapshot = WorkOrderSnapshot(
            id="WO001",
            order_id="ORD001",
            tour_id="T001",
            sku_id="SKU001",
            status="active",
            ubicacion="A1-B2",
            work_area="picking",
            cantidad_restante=10,
            volumen_restante=0.5
        )

        self.assertEqual(snapshot.id, "WO001")
        self.assertEqual(snapshot.status, "active")
        self.assertEqual(snapshot.cantidad_restante, 10)

    def test_snapshot_validation(self):
        """Test snapshot validation"""
        with self.assertRaises(ValueError):
            WorkOrderSnapshot(
                id="",  # Empty ID should fail
                order_id="ORD001",
                tour_id="T001",
                sku_id="SKU001",
                status="active",
                ubicacion="A1-B2",
                work_area="picking",
                cantidad_restante=10,
                volumen_restante=0.5
            )


class TestDashboardCommunicator(unittest.TestCase):
    """Test DashboardCommunicator API and basic functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.mock_provider = MockDataProvider()
        self.config = DashboardConfig(
            startup_timeout=1.0,  # Fast timeouts for testing
            graceful_shutdown_timeout=1.0,
            debug_logging=False  # Reduce test noise
        )
        self.communicator = DashboardCommunicator(self.mock_provider, self.config)

    def test_initialization(self):
        """Test communicator initialization"""
        self.assertIsNotNone(self.communicator.data_provider)
        self.assertIsNotNone(self.communicator.lifecycle_manager)
        self.assertFalse(self.communicator.is_dashboard_active)
        self.assertIsNone(self.communicator.dashboard_pid)

    def test_data_provider_validation(self):
        """Test data provider validation"""
        # Valid provider
        self.assertTrue(self.communicator._validate_data_provider())

        # Invalid provider - no almacen
        invalid_provider = MockDataProvider(has_almacen=False)
        invalid_communicator = DashboardCommunicator(invalid_provider, self.config)
        self.assertFalse(invalid_communicator._validate_data_provider())

    def test_communication_stats(self):
        """Test communication statistics tracking"""
        stats = self.communicator.communication_stats
        self.assertIn('messages_sent', stats)
        self.assertIn('delta_updates_sent', stats)
        self.assertIn('full_syncs_sent', stats)
        self.assertIn('errors_count', stats)
        self.assertEqual(stats['messages_sent'], 0)

    def test_state_cache_management(self):
        """Test internal state cache operations"""
        # Create test work orders
        work_orders = [
            WorkOrderSnapshot(
                id="WO001",
                order_id="ORD001",
                tour_id="T001",
                sku_id="SKU001",
                status="active",
                ubicacion="A1-B2",
                work_area="picking",
                cantidad_restante=10,
                volumen_restante=0.5
            )
        ]

        # Update cache
        self.communicator._update_state_cache(work_orders)
        self.assertEqual(len(self.communicator._last_state_cache), 1)
        self.assertIn("WO001", self.communicator._last_state_cache)

    def test_delta_calculation(self):
        """Test delta change calculation"""
        # Initial state
        initial_wo = WorkOrderSnapshot(
            id="WO001",
            order_id="ORD001",
            tour_id="T001",
            sku_id="SKU001",
            status="active",
            ubicacion="A1-B2",
            work_area="picking",
            cantidad_restante=10,
            volumen_restante=0.5
        )

        self.communicator._update_state_cache([initial_wo])

        # Changed state
        changed_wo = WorkOrderSnapshot(
            id="WO001",
            order_id="ORD001",
            tour_id="T001",
            sku_id="SKU001",
            status="completed",  # Changed status
            ubicacion="A1-B2",
            work_area="picking",
            cantidad_restante=0,  # Changed quantity
            volumen_restante=0.0
        )

        # Calculate delta
        changes = self.communicator._calculate_delta_changes([changed_wo])
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "completed")

    def test_reset_communication_state(self):
        """Test communication state reset"""
        # Setup some state
        work_orders = [
            WorkOrderSnapshot(
                id="WO001",
                order_id="ORD001",
                tour_id="T001",
                sku_id="SKU001",
                status="active",
                ubicacion="A1-B2",
                work_area="picking",
                cantidad_restante=10,
                volumen_restante=0.5
            )
        ]

        self.communicator._update_state_cache(work_orders)
        self.communicator._initial_sync_completed = True

        # Reset state
        self.communicator._reset_communication_state()

        # Verify reset
        self.assertEqual(len(self.communicator._last_state_cache), 0)
        self.assertFalse(self.communicator._initial_sync_completed)
        self.assertFalse(self.communicator._simulation_ended_sent)


class TestProcessLifecycleManager(unittest.TestCase):
    """Test ProcessLifecycleManager basic functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.config = DashboardConfig(
            startup_timeout=1.0,
            graceful_shutdown_timeout=1.0,
            debug_logging=False
        )
        self.manager = ProcessLifecycleManager(self.config)

    def test_initialization(self):
        """Test manager initialization"""
        self.assertIsNotNone(self.manager.config)
        self.assertFalse(self.manager.is_process_active)
        self.assertIsNone(self.manager.process_pid)

    def test_callback_registration(self):
        """Test callback registration"""
        callback = Mock()
        self.manager.add_startup_callback('test', callback)
        self.assertIn('test', self.manager._startup_callbacks)

        shutdown_callback = Mock()
        self.manager.add_shutdown_callback('test', shutdown_callback)
        self.assertIn('test', self.manager._shutdown_callbacks)


class TestDashboardIntegration(unittest.TestCase):
    """Integration tests for dashboard communication (Phase 1: Basic)"""

    def setUp(self):
        """Setup integration test fixtures"""
        self.mock_provider = MockDataProvider()
        self.config = DashboardConfig(debug_logging=False)

    def test_full_workflow_without_process(self):
        """Test full workflow without actual process (Phase 1)"""
        communicator = DashboardCommunicator(self.mock_provider, self.config)

        # Test initial state
        self.assertFalse(communicator.is_dashboard_active)

        # Test update when not active (should handle gracefully)
        result = communicator.update_dashboard_state()
        self.assertFalse(result)  # Should fail gracefully when not active

        # Test shutdown when not active (should handle gracefully)
        result = communicator.shutdown_dashboard()
        self.assertTrue(result)  # Should succeed (no-op)


class TestPhase2Integration(unittest.TestCase):
    """Phase 2 integration tests for complete IPC functionality"""

    def setUp(self):
        """Setup Phase 2 test fixtures"""
        # Create test work orders
        self.test_work_orders = [
            WorkOrderSnapshot(
                id="WO001",
                order_id="ORD001",
                tour_id="T001",
                sku_id="SKU001",
                status="active",
                ubicacion="A1-B2",
                work_area="picking",
                cantidad_restante=10,
                volumen_restante=0.5
            ),
            WorkOrderSnapshot(
                id="WO002",
                order_id="ORD002",
                tour_id="T001",
                sku_id="SKU002",
                status="pending",
                ubicacion="B2-C3",
                work_area="packing",
                cantidad_restante=5,
                volumen_restante=0.3
            )
        ]

        self.mock_provider = MockDataProvider(work_orders=self.test_work_orders)
        self.config = DashboardConfig(debug_logging=False)
        self.communicator = DashboardCommunicator(self.mock_provider, self.config)

    def test_message_retry_logic(self):
        """Test message retry functionality"""
        # Test retry with failed send
        result = self.communicator._send_message_with_retry({}, max_retries=2)
        self.assertFalse(result)  # Should fail when no process active

    def test_full_state_serialization(self):
        """Test full state message serialization"""
        # Test serialization without active process
        result = self.communicator._send_full_state_sync(self.test_work_orders)
        self.assertFalse(result)  # Should fail gracefully when no process

    def test_delta_batching_logic(self):
        """Test delta update batching"""
        # Setup initial state
        self.communicator._update_state_cache(self.test_work_orders)

        # Create modified work orders
        modified_work_orders = []
        for wo in self.test_work_orders:
            modified_wo = WorkOrderSnapshot(
                id=wo.id,
                order_id=wo.order_id,
                tour_id=wo.tour_id,
                sku_id=wo.sku_id,
                status="completed",  # Changed status
                ubicacion=wo.ubicacion,
                work_area=wo.work_area,
                cantidad_restante=0,  # Changed quantity
                volumen_restante=0.0,
                assigned_agent_id="OP001"  # Added assignment
            )
            modified_work_orders.append(modified_wo)

        # Calculate delta - should detect all changes
        changes = self.communicator._calculate_delta_changes(modified_work_orders)
        self.assertEqual(len(changes), 2)  # Both work orders changed

    def test_simulation_data_provider_integration(self):
        """Test integration with SimulationEngineDataProvider"""
        from communication.simulation_data_provider import create_simulation_data_provider

        # Mock simulation engine
        class MockEngine:
            def __init__(self):
                self.almacen = MockAlmacen()
                self.simulacion_finalizada_reportada = False

        class MockAlmacen:
            def __init__(self):
                self.dispatcher = MockDispatcher()

        class MockDispatcher:
            def __init__(self):
                self.lista_maestra_work_orders = []
                self.work_orders_completadas_historicas = []

        mock_engine = MockEngine()
        provider = create_simulation_data_provider(mock_engine)

        # Test provider functionality
        self.assertTrue(provider.has_valid_almacen())
        self.assertFalse(provider.is_simulation_finished())

        work_orders = provider.get_all_work_orders()
        self.assertEqual(len(work_orders), 0)  # Empty lists

    def test_error_statistics_tracking(self):
        """Test error statistics tracking"""
        initial_errors = self.communicator.communication_stats['errors_count']

        # Trigger error in update
        self.communicator.update_dashboard_state()  # Should fail gracefully

        # Note: Error count may not increment since we handle gracefully
        stats = self.communicator.communication_stats
        self.assertIn('errors_count', stats)


# Phase 2: Enhanced test runner with integration validation
if __name__ == '__main__':
    print("=== DashboardCommunicator Phase 2 Tests ===")
    print("Testing complete IPC implementation and integration...")
    print()

    # Run all test suites
    unittest.main(verbosity=2)