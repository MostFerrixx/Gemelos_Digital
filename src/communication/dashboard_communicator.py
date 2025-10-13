# -*- coding: utf-8 -*-
"""
Dashboard Communicator - Robust communication with PyQt6 dashboard process.
"""

import time
import weakref
from typing import Optional, Dict, List, Any
import os
from dataclasses import is_dataclass, asdict

# --- FEATURE FLAG FOR EVENT SOURCING ARCHITECTURE ---
# REPLAY-VIEWER-FIX: Forcing Event Sourcing to True as this is the only supported mode for replay.
USE_EVENT_SOURCING = True
# ----------------------------------------------------

from .ipc_protocols import BaseEvent, EventType
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
    Supports both legacy state-pull and new event-sourcing models via a feature flag.
    """

    def __init__(self, data_provider=None, config: Optional[DashboardConfig] = None):
        """
        Initialize dashboard communicator.
        Args:
            data_provider: Interface for legacy data-pull mode. Not used if USE_EVENT_SOURCING is True.
            config: Configuration for process management.
        """
        if not USE_EVENT_SOURCING and data_provider is None:
            raise ValueError("data_provider is required when USE_EVENT_SOURCING is False.")

        self.data_provider = data_provider
        self.config = config or DashboardConfig()

        if USE_EVENT_SOURCING:
            print("[ARCH] DashboardCommunicator initialized in EVENT SOURCING mode.")
        else:
            print("[ARCH] DashboardCommunicator initialized in LEGACY (state-pull) mode.")

        self.lifecycle_manager = ProcessLifecycleManager(self.config)

        # Legacy state
        self._last_state_cache: Dict[str, Any] = {}
        self._initial_sync_completed = False
        self._simulation_ended_sent = False

        self._stats = {
            'messages_sent': 0,
            'events_sent': 0,
            'errors_count': 0,
            'last_update_time': 0.0
        }
        self._setup_lifecycle_callbacks()

    @property
    def is_dashboard_active(self) -> bool:
        return self.lifecycle_manager.is_process_active

    def start_dashboard(self) -> bool:
        if not USE_EVENT_SOURCING and not self._validate_data_provider():
            raise DataProviderError("Data provider validation failed for legacy mode.")

        try:
            dashboard_target = self._get_dashboard_target_function()
            success = self.lifecycle_manager.start_process(dashboard_target)
            if success:
                self._log("Dashboard process started successfully.")
                return True
            raise ProcessStartupError("Dashboard process failed to start.")
        except Exception as e:
            raise ProcessStartupError(f"Unexpected error starting dashboard: {e}")

    def shutdown_dashboard(self, force: bool = False) -> bool:
        if not self.is_dashboard_active:
            return True
        try:
            success = self.lifecycle_manager.shutdown_process(force=force)
            if success:
                self._log("Dashboard shutdown completed.")
                self._reset_communication_state()
            return success
        except Exception as e:
            self._log(f"Error during dashboard shutdown: {e}")
            return False

    def send_event(self, event: BaseEvent, block: bool = True) -> bool:
        """
        Sends a typed event to the dashboard (Event Sourcing mode).
        If block is True, it will wait for the dashboard to acknowledge the event.
        """
        if not USE_EVENT_SOURCING:
            self._log("Attempted to send an event while in legacy mode. Ignoring.")
            return False
        if not self.is_dashboard_active:
            return False
        try:
            message_dict = self._serialize_event(event)

            # Clear acknowledgment before sending
            if block:
                self.lifecycle_manager.clear_ack()

            success = self._send_message_with_retry(message_dict)
            
            if success:
                self._stats['events_sent'] += 1
                self._stats['messages_sent'] += 1
                self._stats['last_update_time'] = time.time()

                # Wait for dashboard to acknowledge processing
                if block:
                    if not self.lifecycle_manager.wait_for_ack(timeout=5.0):
                        self._log("Dashboard acknowledgment timeout!")
                        self._stats['errors_count'] += 1
                        return False
            return success
        except Exception as e:
            self._log(f"Error sending event {event.type.value}: {e}")
            return False

    def get_pending_message(self) -> Optional[Dict[str, Any]]:
        if not self.is_dashboard_active:
            return None
        return self.lifecycle_manager.get_message()

    def _serialize_event(self, event: BaseEvent) -> dict:
        """Serializes a dataclass event into a dict for IPC."""
        if not is_dataclass(event):
            raise TypeError("Can only serialize dataclass objects")

        event_data = asdict(event)

        payload = {
            'type': event.type.value,
            'timestamp': event_data.pop('timestamp'),
            'event_id': event_data.pop('event_id'),
            'data': event_data,
            'metadata': {
                'sent_timestamp': time.time()
            }
        }
        return payload

    def _send_message_with_retry(self, message_dict: dict, max_retries: int = 2, timeout: float = None) -> bool:
        if not self.lifecycle_manager.is_process_active:
            return False
        timeout = timeout or self.config.queue_timeout
        for _ in range(max_retries + 1):
            try:
                if self.lifecycle_manager.send_message(message_dict, timeout=timeout):
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        return False

    def _validate_data_provider(self) -> bool:
        if USE_EVENT_SOURCING:
            return True
        try:
            return (self.data_provider is not None and
                    hasattr(self.data_provider, 'has_valid_almacen') and
                    hasattr(self.data_provider, 'get_all_work_orders'))
        except Exception:
            return False

    def _get_dashboard_target_function(self):
        """Get dashboard target function with deferred import and validation"""
        import sys

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        src_dir = os.path.join(project_root, 'src')

        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        from subsystems.visualization.work_order_dashboard import launch_dashboard_process
        return launch_dashboard_process

    def _reset_communication_state(self) -> None:
        self._initial_sync_completed = False
        self._simulation_ended_sent = False

    def _log(self, message: str) -> None:
        if self.config.debug_logging:
            print(f"[{self.config.log_prefix}] {message}")

    # Stubs for legacy methods, not used in event sourcing mode
    def update_dashboard_state(self, force_full_sync: bool = False) -> bool:
        if USE_EVENT_SOURCING: return True
        # Legacy implementation would go here
        return False

    def force_temporal_sync(self) -> bool:
        if USE_EVENT_SOURCING: return True
        # Legacy implementation would go here
        return False

    def _setup_lifecycle_callbacks(self): pass
