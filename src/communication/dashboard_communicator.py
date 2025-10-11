# -*- coding: utf-8 -*-
"""
Dashboard Communicator - Robust communication with PyQt6 dashboard process.

Extracted from SimulationEngine dashboard communication methods.
Provides clean API for dashboard lifecycle and data synchronization.

Based on audit findings from:
- simulation_engine.py:1185-1263 (toggle_order_dashboard)
- simulation_engine.py:1265-1314 (_enviar_estado_completo_inicial)
- simulation_engine.py:1316-1415 (_actualizar_dashboard_ordenes)
- simulation_engine.py:708-717 (process cleanup)

Migrated Methods:
- toggle_order_dashboard() -> toggle_dashboard()
- _enviar_estado_completo_inicial() -> _send_initial_full_state()
- _actualizar_dashboard_ordenes() -> update_dashboard_state()
- Cleanup logic -> shutdown_dashboard()
"""

import time
import weakref
from typing import Optional, Dict, List, Any

from .ipc_protocols import (
    DataProviderInterface,
    WorkOrderSnapshot,
    DashboardMessage,
    MessageType,
    ProtocolConstants
)
from .lifecycle_manager import (
    ProcessLifecycleManager,
    DashboardConfig,
    ProcessStartupError,
    ProcessShutdownError
)


# Exception hierarchy for dashboard communication
class DashboardCommunicationError(Exception):
    """Base exception for dashboard communication errors"""
    pass


class ProcessStartupError(DashboardCommunicationError):
    """Error starting dashboard process"""
    pass


class IPCTimeoutError(DashboardCommunicationError):
    """Timeout in IPC communication"""
    pass


class DataProviderError(DashboardCommunicationError):
    """Error accessing data from provider"""
    pass


class DashboardCommunicator:
    """
    Robust communication manager for PyQt6 dashboard process.

    Provides clean API for:
    - Process lifecycle management (start/stop)
    - Data synchronization (full state + delta updates)
    - Error handling and recovery
    - Resource cleanup

    Replaces scattered dashboard communication logic from SimulationEngine.
    """

    def __init__(self, data_provider: DataProviderInterface, config: Optional[DashboardConfig] = None):
        """
        Initialize dashboard communicator.

        Args:
            data_provider: Interface to get WorkOrder data
            config: Configuration for process management
        """
        self.data_provider = data_provider
        self.config = config or DashboardConfig()

        # Process lifecycle manager
        self.lifecycle_manager = ProcessLifecycleManager(self.config)

        # Communication state (based on audit of existing state management)
        self._last_state_cache: Dict[str, WorkOrderSnapshot] = {}
        self._initial_sync_completed = False
        self._simulation_ended_sent = False

        # Statistics and monitoring
        self._stats = {
            'messages_sent': 0,
            'delta_updates_sent': 0,
            'full_syncs_sent': 0,
            'errors_count': 0,
            'last_update_time': 0.0
        }

        # Setup lifecycle callbacks
        self._setup_lifecycle_callbacks()

    @property
    def is_dashboard_active(self) -> bool:
        """Check if dashboard process is active and communicating"""
        return self.lifecycle_manager.is_process_active

    @property
    def dashboard_pid(self) -> Optional[int]:
        """Get dashboard process PID if running"""
        return self.lifecycle_manager.process_pid

    @property
    def communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        return self._stats.copy()

    # PUBLIC API METHODS

    def toggle_dashboard(self) -> bool:
        """
        Toggle dashboard visibility - start if stopped, stop if running.

        Migrated from: simulation_engine.py:1185 (toggle_order_dashboard)

        Returns:
            bool: True if operation successful

        Raises:
            ProcessStartupError: If dashboard fails to start
            ProcessShutdownError: If dashboard fails to shutdown
        """
        if self.is_dashboard_active:
            # Dashboard is running - shut it down
            return self.shutdown_dashboard()
        else:
            # Dashboard is not running - start it
            return self.start_dashboard()

    def start_dashboard(self) -> bool:
        """
        Start dashboard process with data validation.

        Returns:
            bool: True if startup successful

        Raises:
            ProcessStartupError: If process fails to start
            DataProviderError: If data provider is invalid
        """
        # Validate data provider before starting process
        if not self._validate_data_provider():
            raise DataProviderError("Data provider validation failed - cannot start dashboard")

        try:
            # Import dashboard launch function (deferred import for startup validation)
            dashboard_target = self._get_dashboard_target_function()

            # Start process via lifecycle manager
            success = self.lifecycle_manager.start_process(dashboard_target)

            if success:
                self._log("Dashboard process started successfully")
                # Initial state sync will be handled by startup callback
                return True
            else:
                raise ProcessStartupError("Dashboard process failed to start")

        except ImportError as e:
            raise ProcessStartupError(f"Failed to import dashboard module: {e}")
        except Exception as e:
            raise ProcessStartupError(f"Unexpected error starting dashboard: {e}")

    def shutdown_dashboard(self, force: bool = False) -> bool:
        """
        Shutdown dashboard process gracefully.

        Migrated from: simulation_engine.py:1235-1263

        Args:
            force: Force immediate termination

        Returns:
            bool: True if shutdown successful
        """
        if not self.is_dashboard_active:
            self._log("Dashboard not running - shutdown not needed")
            return True

        try:
            success = self.lifecycle_manager.shutdown_process(force=force)

            if success:
                self._log("Dashboard shutdown completed")
                self._reset_communication_state()
            else:
                self._log("Dashboard shutdown had issues")

            return success

        except Exception as e:
            self._log(f"Error during dashboard shutdown: {e}")
            self._stats['errors_count'] += 1
            return False

    def update_dashboard_state(self, force_full_sync: bool = False) -> bool:
        """
        Update dashboard with current WorkOrder state using delta optimization.

        Migrated from: simulation_engine.py:1316 (_actualizar_dashboard_ordenes)

        Args:
            force_full_sync: If True, sends a full state sync instead of a delta.

        Returns:
            bool: True if update sent successfully
        """
        if not self.is_dashboard_active:
            self._log("Dashboard not active - skipping update")
            return False

        try:
            # Get current WorkOrder data
            current_work_orders = self._get_work_orders_safely()
            print(f"[DEBUG-DashboardCommunicator] update_dashboard_state: {len(current_work_orders) if current_work_orders else 0} WorkOrders")
            if not current_work_orders:
                self._log("No WorkOrder data available for update")
                return False

            # Send initial sync if not completed or a full sync is forced
            if not self._initial_sync_completed or force_full_sync:
                metadata = self._get_metadata_safely()
                return self._send_full_state_sync(current_work_orders, metadata=metadata)

            # Calculate and send delta updates
            return self._send_delta_updates(current_work_orders)

        except Exception as e:
            self._log(f"Error updating dashboard state: {e}")
            self._stats['errors_count'] += 1
            return False

    def get_pending_message(self) -> Optional[Dict[str, Any]]:
        """
        Check for and retrieve a pending message from the dashboard.
        This is non-blocking.
        """
        if not self.is_dashboard_active:
            return None
        return self.lifecycle_manager.get_message()

    def send_simulation_ended(self) -> bool:
        """
        Send simulation ended command to dashboard.

        Based on: simulation_engine.py:1220-1225

        Returns:
            bool: True if command sent successfully
        """
        if not self.is_dashboard_active:
            return False

        if self._simulation_ended_sent:
            self._log("Simulation ended already sent")
            return True

        try:
            message = DashboardMessage.command(ProtocolConstants.SIMULATION_ENDED)
            success = self.lifecycle_manager.send_message(message)

            if success:
                self._log("Simulation ended command sent")
                self._simulation_ended_sent = True

            return success

        except Exception as e:
            self._log(f"Error sending simulation ended: {e}")
            return False

    def force_temporal_sync(self) -> bool:
        """
        Force a complete temporal synchronization of WorkOrder states.
        
        This method is called when the replay scrubber changes time positions,
        ensuring the dashboard reflects the correct state at the selected time.
        
        Returns:
            bool: True if temporal sync sent successfully
        """
        if not self.is_dashboard_active:
            self._log("Dashboard not active - skipping temporal sync")
            return False

        try:
            # Get current WorkOrder data (should reflect the new temporal state)
            current_work_orders = self._get_work_orders_safely()
            if not current_work_orders:
                self._log("No WorkOrder data available for temporal sync")
                return False

            # Get metadata including current time
            metadata = self._get_metadata_safely()
            
            # Convert WorkOrderSnapshot objects to dictionaries for IPC
            converted_data = []
            for wo_snapshot in current_work_orders:
                wo_dict = {
                    'id': wo_snapshot.id,
                    'order_id': wo_snapshot.order_id,
                    'tour_id': wo_snapshot.tour_id,
                    'sku_id': wo_snapshot.sku_id,
                    'status': wo_snapshot.status,
                    'ubicacion': wo_snapshot.ubicacion,
                    'work_area': wo_snapshot.work_area,
                    'cantidad_restante': wo_snapshot.cantidad_restante,
                    'volumen_restante': wo_snapshot.volumen_restante,
                    'assigned_agent_id': wo_snapshot.assigned_agent_id,
                    'timestamp': wo_snapshot.timestamp
                }
                converted_data.append(wo_dict)
            
            # Send temporal sync message with current time
            current_time = metadata.get('current_time', 0.0)
            message_dict = {
                'type': 'temporal_sync',
                'timestamp': time.time(),
                'data': converted_data,
                'metadata': {
                    'target_time': current_time,
                    'sync_type': 'temporal',
                    'total_work_orders': len(converted_data)
                }
            }
            
            # Send via lifecycle manager with timeout handling
            success = self._send_message_with_retry(message_dict, max_retries=2)
            
            if success:
                self._log(f"Temporal sync completed: {len(current_work_orders)} WorkOrders synchronized")
                # Reset delta cache since we've sent a full state
                self._last_state_cache.clear()
            else:
                self._log("Failed to send temporal sync")

            return success

        except Exception as e:
            self._log(f"Error in temporal sync: {e}")
            self._stats['errors_count'] += 1
            return False

    # PRIVATE IMPLEMENTATION METHODS

    def _send_message_with_retry(self, message_dict: dict, max_retries: int = 2, timeout: float = None) -> bool:
        """
        Send message with retry logic and timeout handling.

        Phase 2: Complete implementation for robust IPC communication.

        Args:
            message_dict: Message dictionary to send
            max_retries: Maximum number of retry attempts
            timeout: Send timeout (uses config default if None)

        Returns:
            bool: True if message sent successfully
        """
        if not self.lifecycle_manager.is_process_active:
            self._log("Cannot send message - process not active")
            return False

        timeout = timeout or self.config.queue_timeout

        for attempt in range(max_retries + 1):
            try:
                # Use lifecycle manager's send_message with timeout
                success = self.lifecycle_manager.send_message(message_dict, timeout=timeout)

                if success:
                    if attempt > 0:
                        self._log(f"Message sent successfully on attempt {attempt + 1}")
                    return True
                else:
                    if attempt < max_retries:
                        self._log(f"Send failed, retrying ({attempt + 1}/{max_retries})")
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    else:
                        self._log(f"Message send failed after {max_retries + 1} attempts")

            except Exception as e:
                if attempt < max_retries:
                    self._log(f"Send error on attempt {attempt + 1}: {e}, retrying")
                    time.sleep(0.1 * (attempt + 1))
                else:
                    self._log(f"Message send failed with error: {e}")

        return False

    def _validate_data_provider(self) -> bool:
        """Validate that data provider can supply required data"""
        try:
            return (self.data_provider.has_valid_almacen() and
                    hasattr(self.data_provider, 'get_all_work_orders'))
        except Exception as e:
            self._log(f"Data provider validation error: {e}")
            return False

    def _get_dashboard_target_function(self):
        """Get dashboard target function with deferred import and validation"""
        import sys
        import os
        
        # Add current directory and src directory to Python path if not already there
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        src_dir = os.path.join(project_root, 'src')
        
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            
        try:
            # Try multiple import strategies
            launch_dashboard_process = None
            
            # Strategy 1: Import from subsystems.visualization (correct location)
            try:
                from subsystems.visualization.work_order_dashboard import launch_dashboard_process
                self._log("Dashboard target function imported successfully (strategy 1)")
            except ImportError:
                # Strategy 2: Direct import from src
                try:
                    from src.visualization.work_order_dashboard import launch_dashboard_process
                    self._log("Dashboard target function imported successfully (strategy 2)")
                except ImportError:
                    # Strategy 3: Import from visualization module
                    try:
                        from visualization.work_order_dashboard import launch_dashboard_process
                        self._log("Dashboard target function imported successfully (strategy 3)")
                    except ImportError:
                        raise ImportError("All import strategies failed")

            if not callable(launch_dashboard_process):
                raise ImportError("launch_dashboard_process is not callable")

            return launch_dashboard_process

        except ImportError as e:
            error_msg = f"Failed to import dashboard module: {e}"
            self._log(error_msg)
            self._log(f"Python path: {sys.path[:3]}...")  # Show first 3 paths
            self._log(f"Current working directory: {os.getcwd()}")
            self._log(f"Project root: {project_root}")
            self._log(f"SRC directory: {src_dir}")
            
            # Try to find the file manually
            dashboard_file_subsystems = os.path.join(src_dir, 'subsystems', 'visualization', 'work_order_dashboard.py')
            dashboard_file_src = os.path.join(src_dir, 'visualization', 'work_order_dashboard.py')
            
            if os.path.exists(dashboard_file_subsystems):
                self._log(f"Dashboard file exists at: {dashboard_file_subsystems}")
            elif os.path.exists(dashboard_file_src):
                self._log(f"Dashboard file exists at: {dashboard_file_src}")
            else:
                self._log(f"Dashboard file NOT found at: {dashboard_file_subsystems}")
                self._log(f"Dashboard file NOT found at: {dashboard_file_src}")

            raise ProcessStartupError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error importing dashboard function: {e}"
            self._log(error_msg)
            raise ProcessStartupError(error_msg) from e

    def _get_metadata_safely(self) -> Dict[str, Any]:
        """Get simulation metadata from data provider with error handling"""
        try:
            return self.data_provider.get_simulation_metadata()
        except Exception as e:
            self._log(f"Error getting metadata from provider: {e}")
            return {}

    def _get_work_orders_safely(self) -> Optional[List[WorkOrderSnapshot]]:
        """Get WorkOrders from data provider with error handling"""
        try:
            return self.data_provider.get_all_work_orders()
        except Exception as e:
            self._log(f"Error getting WorkOrders from provider: {e}")
            return None

    def _send_full_state_sync(self, work_orders: List[WorkOrderSnapshot], metadata: Optional[Dict] = None) -> bool:
        """
        Send complete WorkOrder state to dashboard.

        Migrated from: simulation_engine.py:1265 (_enviar_estado_completo_inicial)
        Complete Phase 2 implementation with proper message serialization.

        Args:
            work_orders: Complete list of WorkOrders
            metadata: Optional dictionary for extra data like max_time

        Returns:
            bool: True if sync sent successfully
        """
        try:
            # Phase 2: Create full state message with proper serialization
            # Convert WorkOrderSnapshots to dict format for IPC transmission
            full_state_data = []
            for wo in work_orders:
                wo_dict = {
                    "id": wo.id,
                    "order_id": wo.order_id,
                    "tour_id": wo.tour_id,
                    "sku_id": wo.sku_id,
                    "status": wo.status,
                    "ubicacion": wo.ubicacion,
                    "work_area": wo.work_area,
                    "cantidad_restante": wo.cantidad_restante,
                    "volumen_restante": wo.volumen_restante,
                    "assigned_agent_id": wo.assigned_agent_id,
                    "timestamp": wo.timestamp
                }
                full_state_data.append(wo_dict)

            # Create structured message (matching original format from simulation_engine.py:1297-1303)
            message_dict = {
                'type': 'full_state',
                'timestamp': time.time(),
                'data': full_state_data,
                'metadata': metadata or {}
            }

            # Send via lifecycle manager with timeout handling
            success = self._send_message_with_retry(message_dict, max_retries=2)

            if success:
                # Update cache and sync state
                self._update_state_cache(work_orders)
                self._initial_sync_completed = True
                self._stats['full_syncs_sent'] += 1
                self._stats['messages_sent'] += 1
                self._stats['last_update_time'] = time.time()

                self._log(f"Full state sync sent: {len(work_orders)} WorkOrders")
            else:
                self._log("Failed to send full state sync message")

            return success

        except Exception as e:
            self._log(f"Error in full state sync: {e}")
            self._stats['errors_count'] += 1
            return False

    def _send_delta_updates(self, current_work_orders: List[WorkOrderSnapshot]) -> bool:
        """
        Send only changed WorkOrders to dashboard.

        Migrated from: simulation_engine.py:1344-1398 (delta calculation logic)
        Complete Phase 2 implementation with proper serialization and batching.

        Args:
            current_work_orders: Current WorkOrder state

        Returns:
            bool: True if delta sent successfully
        """
        try:
            # Calculate changes from last state
            changed_work_orders = self._calculate_delta_changes(current_work_orders)

            if not changed_work_orders:
                # No changes - update cache and return success
                self._update_state_cache(current_work_orders)
                return True

            # Phase 2: Implement batching for large delta sets
            max_batch_size = ProtocolConstants.MAX_DELTA_BATCH_SIZE
            total_changes = len(changed_work_orders)

            # Process in batches if necessary
            for batch_start in range(0, total_changes, max_batch_size):
                batch_end = min(batch_start + max_batch_size, total_changes)
                batch = changed_work_orders[batch_start:batch_end]

                # Convert to dict format for IPC
                delta_data = []
                for wo in batch:
                    wo_dict = {
                        "id": wo.id,
                        "order_id": wo.order_id,
                        "tour_id": wo.tour_id,
                        "sku_id": wo.sku_id,
                        "status": wo.status,
                        "ubicacion": wo.ubicacion,
                        "work_area": wo.work_area,
                        "cantidad_restante": wo.cantidad_restante,
                        "volumen_restante": wo.volumen_restante,
                        "assigned_agent_id": wo.assigned_agent_id,
                        "timestamp": wo.timestamp
                    }
                    delta_data.append(wo_dict)

                # Create delta message (matching original format from simulation_engine.py:1384-1388)
                message_dict = {
                    'type': 'delta',
                    'timestamp': time.time(),
                    'data': delta_data,
                    'metadata': {
                        'batch_info': {
                            'current_batch': (batch_start // max_batch_size) + 1,
                            'total_batches': (total_changes + max_batch_size - 1) // max_batch_size,
                            'batch_size': len(batch)
                        }
                    }
                }

                # Send batch with retry logic
                success = self._send_message_with_retry(message_dict, max_retries=2)
                if not success:
                    self._log(f"Failed to send delta batch {batch_start//max_batch_size + 1}")
                    return False

            # Update cache with new state after successful transmission
            self._update_state_cache(current_work_orders)

            # Update statistics
            self._stats['delta_updates_sent'] += 1
            self._stats['messages_sent'] += 1
            self._stats['last_update_time'] = time.time()

            self._log(f"Delta update sent: {total_changes} changes in {(total_changes + max_batch_size - 1) // max_batch_size} batch(es)")
            return True

        except Exception as e:
            self._log(f"Error in delta update: {e}")
            self._stats['errors_count'] += 1
            return False

    def _calculate_delta_changes(self, current_work_orders: List[WorkOrderSnapshot]) -> List[WorkOrderSnapshot]:
        """
        Calculate WorkOrders that changed since last update.

        Based on: simulation_engine.py:1365-1375 (change detection logic)

        Args:
            current_work_orders: Current WorkOrder state

        Returns:
            List[WorkOrderSnapshot]: WorkOrders that changed
        """
        changed = []
        current_by_id = {wo.id: wo for wo in current_work_orders}

        for work_order_id, current_wo in current_by_id.items():
            last_wo = self._last_state_cache.get(work_order_id)

            # Check if new or changed (key fields from audit)
            if (last_wo is None or
                last_wo.status != current_wo.status or
                last_wo.cantidad_restante != current_wo.cantidad_restante or
                last_wo.assigned_agent_id != current_wo.assigned_agent_id or
                last_wo.volumen_restante != current_wo.volumen_restante):

                changed.append(current_wo)

        return changed

    def _update_state_cache(self, work_orders: List[WorkOrderSnapshot]) -> None:
        """Update internal state cache for delta calculation"""
        self._last_state_cache = {wo.id: wo for wo in work_orders}

    def _setup_lifecycle_callbacks(self) -> None:
        """Setup callbacks for process lifecycle events"""
        self.lifecycle_manager.add_startup_callback(
            'initial_sync',
            self._on_process_startup
        )
        self.lifecycle_manager.add_shutdown_callback(
            'cleanup_state',
            self._on_process_shutdown
        )

    def _on_process_startup(self, lifecycle_manager) -> None:
        """Callback for process startup - send initial data"""
        # Send initial full state if data available
        work_orders = self._get_work_orders_safely()
        if work_orders:
            self._send_full_state_sync(work_orders)

            # Check if simulation already ended
            if self.data_provider.is_simulation_finished():
                self.send_simulation_ended()

    def _on_process_shutdown(self, lifecycle_manager) -> None:
        """Callback for process shutdown - cleanup state"""
        self._reset_communication_state()

    def _reset_communication_state(self) -> None:
        """Reset communication state after shutdown"""
        self._last_state_cache.clear()
        self._initial_sync_completed = False
        self._simulation_ended_sent = False

    def _log(self, message: str) -> None:
        """Internal logging with consistent prefix"""
        if self.config.debug_logging:
            print(f"{self.config.log_prefix} {message}")


# Phase 1: Export main communication API
__all__ = [
    'DashboardCommunicator',
    'DashboardCommunicationError',
    'ProcessStartupError',
    'IPCTimeoutError',
    'DataProviderError'
]