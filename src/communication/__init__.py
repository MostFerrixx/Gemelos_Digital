# -*- coding: utf-8 -*-
"""
Communication Package - Digital Twin Warehouse Simulator V10.0.4

Extracted dashboard communication functionality from SimulationEngine.
Provides robust, testable communication with PyQt6 dashboard process.

Phase 1: Architecture skeleton and base classes.
"""

# Core communication classes
from .dashboard_communicator import DashboardCommunicator
from .lifecycle_manager import ProcessLifecycleManager, DashboardConfig
from .ipc_protocols import (
    WorkOrderSnapshot,
    DataProviderInterface,
    DashboardMessage,
    MessageType
)
from .simulation_data_provider import SimulationEngineDataProvider, create_simulation_data_provider

# Exceptions
from .dashboard_communicator import (
    DashboardCommunicationError,
    ProcessStartupError,
    IPCTimeoutError
)

__version__ = "10.0.4"
__all__ = [
    # Main API
    'DashboardCommunicator',

    # Lifecycle management
    'ProcessLifecycleManager',
    'DashboardConfig',

    # IPC protocols
    'WorkOrderSnapshot',
    'DataProviderInterface',
    'DashboardMessage',
    'MessageType',

    # Data providers
    'SimulationEngineDataProvider',
    'create_simulation_data_provider',

    # Exceptions
    'DashboardCommunicationError',
    'ProcessStartupError',
    'IPCTimeoutError'
]