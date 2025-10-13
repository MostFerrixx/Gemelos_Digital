# -*- coding: utf-8 -*-
"""
IPC Protocols - Event Sourcing Definitions for PyQt6 Dashboard

Defines the event-based communication contract between the ReplayEngine and the
WorkOrderDashboard. This module implements Phase 1 of the Event Sourcing
architecture refactor.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

# --- Event Catalog ---

class EventType(Enum):
    """
    Defines the complete catalog of event types for the event-driven architecture.
    This enum is the single source of truth for all possible events in the system.
    """
    # === LIFECYCLE EVENTS ===
    SIMULATION_START = "simulation_start"
    SIMULATION_END = "simulation_end"
    REPLAY_START = "replay_start"
    REPLAY_END = "replay_end"

    # === STATE MANAGEMENT EVENTS ===
    STATE_RESET = "state_reset"
    STATE_SNAPSHOT = "state_snapshot"

    # === WORKORDER EVENTS (GRANULAR) ===
    WO_CREATED = "wo_created"
    WO_STATUS_CHANGED = "wo_status_changed"
    WO_ASSIGNED = "wo_assigned"
    WO_UNASSIGNED = "wo_unassigned"
    WO_PROGRESS_UPDATED = "wo_progress_updated"
    WO_COMPLETED = "wo_completed"
    WO_CANCELLED = "wo_cancelled"

    # === OPERATOR EVENTS ===
    OPERATOR_STATUS_CHANGED = "operator_status_changed"
    OPERATOR_POSITION_UPDATED = "operator_position_updated"
    OPERATOR_TASK_STARTED = "operator_task_started"
    OPERATOR_TASK_COMPLETED = "operator_task_completed"

    # === TIME EVENTS ===
    TIME_TICK = "time_tick"
    TIME_SEEK = "time_seek"

    # === METRICS EVENTS ===
    METRICS_UPDATED = "metrics_updated"

    # === CONTROL EVENTS ===
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_RESUMED = "playback_resumed"
    PLAYBACK_SPEED_CHANGED = "playback_speed_changed"


# --- Base Event Structure ---

@dataclass(frozen=True)
class BaseEvent:
    """
    Abstract base class for all events.
    Contains fields common to all events that do not have default values.
    """
    timestamp: float
    type: EventType = field(init=False)


# --- Specific Event Dataclasses ---

# === State Management Events ===

@dataclass(frozen=True)
class StateResetEvent(BaseEvent):
    """
    Emitted to signal that the dashboard must clear its entire local state.
    This is the first step in a time-seek operation.
    """
    reason: str
    target_time: Optional[float] = None
    version: str = "v1"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        object.__setattr__(self, 'type', EventType.STATE_RESET)


@dataclass(frozen=True)
class StateSnapshotEvent(BaseEvent):
    """
    Emitted after a STATE_RESET, containing a complete snapshot of the system state.
    """
    work_orders: List[Dict[str, Any]]
    operators: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    version: str = "v1"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        object.__setattr__(self, 'type', EventType.STATE_SNAPSHOT)


# === WorkOrder Events ===

@dataclass(frozen=True)
class WorkOrderStatusChangedEvent(BaseEvent):
    """
    Emitted when a WorkOrder transitions between statuses.
    """
    wo_id: str
    old_status: str
    new_status: str
    agent_id: Optional[str] = None
    version: str = "v1"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        object.__setattr__(self, 'type', EventType.WO_STATUS_CHANGED)


@dataclass(frozen=True)
class WorkOrderAssignedEvent(BaseEvent):
    """
    Emitted specifically when a WorkOrder is assigned to an agent.
    """
    wo_id: str
    agent_id: str
    timestamp_assigned: float
    version: str = "v1"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        object.__setattr__(self, 'type', EventType.WO_ASSIGNED)


@dataclass(frozen=True)
class WorkOrderProgressUpdatedEvent(BaseEvent):
    """
    Emitted when the progress of a WorkOrder changes.
    """
    wo_id: str
    cantidad_restante: int
    volumen_restante: float
    progress_percentage: float
    version: str = "v1"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        object.__setattr__(self, 'type', EventType.WO_PROGRESS_UPDATED)


@dataclass(frozen=True)
class TimeTickEvent(BaseEvent):
    """
    Periodic time update event for dashboard synchronization.
    """
    elapsed_time: float
    total_duration: float
    version: str = "v1"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        object.__setattr__(self, 'type', EventType.TIME_TICK)