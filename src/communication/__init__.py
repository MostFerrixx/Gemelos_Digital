# -*- coding: utf-8 -*-
"""
Communication Package - Digital Twin Warehouse Simulator V11.0.0

Handles event-based communication with the PyQt6 dashboard process.
"""

# Core communication classes
from .dashboard_communicator import DashboardCommunicator
from .lifecycle_manager import ProcessLifecycleManager, DashboardConfig
from .ipc_protocols import (
    EventType,
    BaseEvent,
    StateResetEvent,
    StateSnapshotEvent,
    WorkOrderStatusChangedEvent,
    WorkOrderAssignedEvent,
    WorkOrderProgressUpdatedEvent,
)


# Exceptions
from .dashboard_communicator import (
    DashboardCommunicationError,
    ProcessStartupError,
    IPCTimeoutError
)

__version__ = "11.0.0"
__all__ = [
    # Main API
    'DashboardCommunicator',

    # Lifecycle management
    'ProcessLifecycleManager',
    'DashboardConfig',

    # IPC protocols (Event Sourcing)
    'EventType',
    'BaseEvent',
    'StateResetEvent',
    'StateSnapshotEvent',
    'WorkOrderStatusChangedEvent',
    'WorkOrderAssignedEvent',
    'WorkOrderProgressUpdatedEvent',



    # Exceptions
    'DashboardCommunicationError',
    'ProcessStartupError',
    'IPCTimeoutError'
]
