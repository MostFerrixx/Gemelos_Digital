# -*- coding: utf-8 -*-
"""
IPC Protocols - Inter-Process Communication definitions and interfaces.

Defines the communication contract between SimulationEngine and dashboard process.
Extracted from SimulationEngine dashboard communication logic.

Based on audit findings:
- Delta update protocol from simulation_engine.py:1365-1390
- Message format from simulation_engine.py:1297-1303
- Full state sync protocol from simulation_engine.py:1265-1314
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import time


class MessageType(Enum):
    """Types of messages supported by dashboard IPC protocol"""
    FULL_STATE = "full_state"
    DELTA_UPDATE = "delta"
    COMMAND = "command"
    STATUS = "status"
    ERROR = "error"
    TEMPORAL_SYNC = "temporal_sync"


@dataclass(frozen=True)
class WorkOrderSnapshot:
    """
    Immutable snapshot of WorkOrder state for IPC transmission.

    Based on audit of simulation_engine.py:1283-1294 and 1350-1361
    Ensures thread-safe data transfer across process boundary.
    """
    # Core identifiers
    id: str
    order_id: str
    tour_id: str
    sku_id: str

    # Status and location
    status: str
    ubicacion: str
    work_area: str

    # Quantities
    cantidad_restante: int
    volumen_restante: float

    # Assignment
    assigned_agent_id: Optional[str] = None

    # Metadata for change detection
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """Validate required fields"""
        if not self.id:
            raise ValueError("WorkOrderSnapshot requires valid id")
        if not self.order_id:
            raise ValueError("WorkOrderSnapshot requires valid order_id")


@dataclass
class DashboardMessage:
    """
    Structured message for dashboard IPC communication.

    Based on protocol audit from simulation_engine.py:1297-1303, 1384-1388
    Supports full state sync and delta updates.
    """
    type: MessageType
    timestamp: float = field(default_factory=time.time)
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def full_state(cls, work_orders: List[WorkOrderSnapshot]) -> 'DashboardMessage':
        """Create full state synchronization message"""
        return cls(
            type=MessageType.FULL_STATE,
            data=work_orders,
            metadata={
                'total_work_orders': len(work_orders),
                'sync_type': 'initial'
            }
        )

    @classmethod
    def delta_update(cls, changed_work_orders: List[WorkOrderSnapshot]) -> 'DashboardMessage':
        """Create delta update message with only changed WorkOrders"""
        return cls(
            type=MessageType.DELTA_UPDATE,
            data=changed_work_orders,
            metadata={
                'delta_count': len(changed_work_orders),
                'update_type': 'incremental'
            }
        )

    @classmethod
    def command(cls, command_str: str, **kwargs) -> 'DashboardMessage':
        """Create command message for process control"""
        return cls(
            type=MessageType.COMMAND,
            data=command_str,
            metadata=kwargs
        )

    @classmethod
    def status(cls, status_str: str, **kwargs) -> 'DashboardMessage':
        """Create status update message"""
        return cls(
            type=MessageType.STATUS,
            data=status_str,
            metadata=kwargs
        )

    @classmethod
    def temporal_sync(cls, work_orders: List[WorkOrderSnapshot], target_time: float) -> 'DashboardMessage':
        """Create temporal synchronization message for replay scrubber"""
        return cls(
            type=MessageType.TEMPORAL_SYNC,
            data=work_orders,
            metadata={
                'target_time': target_time,
                'sync_type': 'temporal',
                'total_work_orders': len(work_orders)
            }
        )


class DataProviderInterface(ABC):
    """
    Abstract interface for providing WorkOrder data to DashboardCommunicator.

    Decouples dashboard communication from SimulationEngine internal structure.
    Based on audit of data access patterns in simulation_engine.py:1276-1278, 1340-1342
    """

    @abstractmethod
    def get_all_work_orders(self) -> List[WorkOrderSnapshot]:
        """
        Get complete list of WorkOrders (active + historical).

        Returns:
            List[WorkOrderSnapshot]: Immutable snapshots of all WorkOrders
        """
        pass

    @abstractmethod
    def is_simulation_finished(self) -> bool:
        """
        Check if simulation has completed.

        Returns:
            bool: True if simulation finished
        """
        pass

    @abstractmethod
    def has_valid_almacen(self) -> bool:
        """
        Check if almacen data is available and valid.

        Returns:
            bool: True if almacen is available for data extraction
        """
        pass

    def get_simulation_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the simulation (e.g., max_time).
        Default implementation returns an empty dict.
        """
        return {}


class DashboardProtocolValidator:
    """
    Validation utilities for dashboard communication protocol.

    Phase 1: Stub implementation for future protocol validation.
    """

    @staticmethod
    def validate_message(message: DashboardMessage) -> bool:
        """
        Validate message structure and content.

        Phase 1: Basic validation stub
        Future: Comprehensive protocol validation

        Args:
            message: Message to validate

        Returns:
            bool: True if message is valid
        """
        if not isinstance(message, DashboardMessage):
            return False

        if not isinstance(message.type, MessageType):
            return False

        # Future: Deep validation of data field based on message type
        return True

    @staticmethod
    def validate_work_order_snapshot(snapshot: WorkOrderSnapshot) -> bool:
        """
        Validate WorkOrderSnapshot structure.

        Args:
            snapshot: Snapshot to validate

        Returns:
            bool: True if snapshot is valid
        """
        try:
            # Basic validation - ensure required fields present
            return (
                bool(snapshot.id) and
                bool(snapshot.order_id) and
                isinstance(snapshot.cantidad_restante, int) and
                isinstance(snapshot.volumen_restante, (int, float))
            )
        except (AttributeError, TypeError):
            return False


# Protocol constants based on audit findings
class ProtocolConstants:
    """Constants for dashboard communication protocol"""

    # Command strings from simulation_engine.py audit
    EXIT_COMMAND = "__EXIT_COMMAND__"
    SIMULATION_ENDED = "__SIMULATION_ENDED__"

    # Queue settings
    DEFAULT_QUEUE_TIMEOUT = 1.0  # seconds
    MAX_QUEUE_SIZE = 1000

    # Message limits
    MAX_DELTA_BATCH_SIZE = 50  # Maximum WorkOrders per delta message
    MAX_MESSAGE_SIZE_BYTES = 1024 * 1024  # 1MB message size limit


# Phase 1: Export protocol definitions for use by other modules
__all__ = [
    'MessageType',
    'WorkOrderSnapshot',
    'DashboardMessage',
    'DataProviderInterface',
    'DashboardProtocolValidator',
    'ProtocolConstants'
]