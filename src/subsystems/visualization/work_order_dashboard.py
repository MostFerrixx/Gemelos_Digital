# -*- coding: utf-8 -*-
"""
WorkOrder Real-Time Dashboard.

Displays the state of all WorkOrders in a real-time, sortable table.
Built with PyQt6 for performance and native look-and-feel.
"""

import sys
import os
import time
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableView,
    QVBoxLayout,
    QWidget,
    QSlider,
    QLabel,
    QHBoxLayout,
)
from PyQt6.QtCore import (
    Qt,
    QAbstractTableModel,
    QSortFilterProxyModel,
    QModelIndex,
    QObject,
    QThread,
    pyqtSignal,
    QTimer,
)
from PyQt6.QtGui import QFont, QColor
from typing import Dict, Any

# Define the columns based on the reference image and requirements.
# Using a list of tuples: (Header Name, Internal Key)
COLUMN_HEADERS = [
    ("WO_ID", "id"),
    ("ORDER ID", "order_id"),
    ("TOUR ID", "tour_id"),
    ("SKU", "sku_id"),
    ("PRODUCT", "product"),
    ("STATUS", "status"),
    ("AGENT", "assigned_agent_id"),
    ("PRIORITY", "priority"),
    ("ITEMS", "items"),
    ("TOTAL QTY", "total_qty"),
    ("VOLUME", "volume"),
    ("LOCATION", "location"),
    ("STAGING", "staging"),
    ("WORK GROUP", "work_group"),
    ("WORK AREA", "work_area"),
    ("EXECUTIONS", "executions"),
    ("START TIME", "start_time"),
    ("PROGRESS", "progress"),
]

# Define status colors for visual differentiation
STATUS_COLORS = {
    'released': QColor(255, 193, 7),      # Amber/Yellow (estado inicial)
    'assigned': QColor(0, 123, 255),      # Blue (asignada a operario)
    'in_progress': QColor(255, 87, 34),   # Orange (en proceso de picking)
    'staged': QColor(40, 167, 69),        # Green (completada y en staging)
    # Legacy support (por si acaso)
    'pending': QColor(255, 193, 7),       # Amber/Yellow (deprecated)
    'completed': QColor(40, 167, 69),     # Green (deprecated)
}

class WorkOrderTableModel(QAbstractTableModel):
    """
    Data model for the WorkOrders table.
    Manages the data and provides it to the QTableView.
    """
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = data or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMN_HEADERS)

    def _convert_to_dict(self, data):
        """
        Convert WorkOrderSnapshot or dictionary to a standardized dictionary.
        This ensures all keys defined in COLUMN_HEADERS are present.
        """
        if not isinstance(data, dict):
            # If it's an object, convert it to a dictionary
            source_dict = {
                'id': getattr(data, 'id', ''),
                'order_id': getattr(data, 'order_id', ''),
                'tour_id': getattr(data, 'tour_id', ''),
                'sku_id': getattr(data, 'sku_id', ''),
                'product': getattr(data, 'product', ''),
                'status': getattr(data, 'status', 'released'),
                'assigned_agent_id': getattr(data, 'assigned_agent_id', None),
                'priority': getattr(data, 'priority', 9999),
                'items': getattr(data, 'items', 0),
                'total_qty': getattr(data, 'total_qty', getattr(data, 'cantidad_restante', 0)),
                'volume': getattr(data, 'volume', getattr(data, 'volumen_restante', 0.0)),
                'location': getattr(data, 'location', getattr(data, 'ubicacion', '')),
                'staging': getattr(data, 'staging', ''),
                'work_group': getattr(data, 'work_group', ''),
                'work_area': getattr(data, 'work_area', ''),
                'executions': getattr(data, 'executions', 0),
                'start_time': getattr(data, 'start_time', 0.0),
                'progress': getattr(data, 'progress', 0.0),
                'timestamp': getattr(data, 'timestamp', 0.0)
            }
        else:
            # If it's already a dictionary, use it directly
            source_dict = data

        # Ensure all expected keys are present, providing defaults if necessary
        # This handles both objects and dictionaries gracefully.
        return {
            key: source_dict.get(key, default)
            for default, key in [
                ('', 'id'), ('', 'order_id'), ('', 'tour_id'), ('', 'sku_id'),
                ('', 'product'), ('released', 'status'), (None, 'assigned_agent_id'),
                (9999, 'priority'), (0, 'items'), (0, 'total_qty'), (0.0, 'volume'),
                ('', 'location'), ('', 'staging'), ('', 'work_group'), ('', 'work_area'),
                (0, 'executions'), (0.0, 'start_time'), (0.0, 'progress')
            ]
        }

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row_data = self._convert_to_dict(self._data[index.row()])
            column_key = COLUMN_HEADERS[index.column()][1]
            value = row_data.get(column_key, "")
            return str(value)  # Convert all values to string for display

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Color-code rows based on status
            row_data = self._convert_to_dict(self._data[index.row()])
            status = row_data.get('status', 'released')
            if status in STATUS_COLORS:
                return STATUS_COLORS[status]

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COLUMN_HEADERS[section][0]
        return None

    def setData(self, data):
        """
        Set the entire dataset for the model.
        Used for full state updates.
        """
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def updateData(self, updates):
        """
        Update or add new data from a list of updates. This method is optimized
        for batch updates.
        """
        id_to_row_map = {self._convert_to_dict(wo)['id']: i for i, wo in enumerate(self._data)}

        new_rows_data = []

        # Process updates for existing items first
        for wo_update in updates:
            # Convert WorkOrderSnapshot to dictionary if needed
            wo_update = self._convert_to_dict(wo_update)

            wo_id = wo_update.get('id')
            if not wo_id:
                continue

            if wo_id in id_to_row_map:
                row = id_to_row_map[wo_id]
                self._data[row] = wo_update
                self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
            else:
                new_rows_data.append(wo_update)

        # Add all new items in a single batch
        if new_rows_data:
            first_row_to_insert = self.rowCount()
            last_row_to_insert = first_row_to_insert + len(new_rows_data) - 1

            self.beginInsertRows(QModelIndex(), first_row_to_insert, last_row_to_insert)
            self._data.extend(new_rows_data)
            self.endInsertRows()


class QueueListener(QObject):
    """
    A worker that listens on a multiprocessing.Queue in a separate thread.
    Emits a signal when a message is received.
    """
    message_received = pyqtSignal(dict)

    def __init__(self, queue_from_sim):
        super().__init__()
        self.queue_from_sim = queue_from_sim

    def run(self):
        """Continuously listen for messages from the queue."""
        while True:
            try:
                message = self.queue_from_sim.get()
                if message is None:  # Sentinel value to stop the thread
                    break
                self.message_received.emit(message)
            except Exception as e:
                # In a real app, you'd want more robust error logging
                print(f"Error in queue listener: {e}")


class WorkOrderDashboard(QMainWindow):
    """
    The main dashboard window.
    Contains the table view and handles UI setup.
    """
    def __init__(self, queue_from_sim=None, queue_to_sim=None, ack_event=None):
        super().__init__()
        self.setWindowTitle("Digital Twin Warehouse - Dashboard v1.0")
        self.setGeometry(100, 100, 1600, 800)

        # Store communication queues and sync event
        self.queue_from_sim = queue_from_sim
        self.queue_to_sim = queue_to_sim
        self.ack_event = ack_event

        # ===== NUEVO: Event Sourcing State Management =====
        # Local state rebuilt from events (Event Sourcing pattern)
        self._local_wo_state: Dict[str, Dict[str, Any]] = {}
        self._wo_id_to_row_map: Dict[str, int] = {}
        self._local_operator_state: Dict[str, Dict[str, Any]] = {}
        self._local_metrics: Dict[str, Any] = {}

        # Event processing state
        self._is_rebuilding_state: bool = False
        self._last_snapshot_time: float = 0.0

        # REPLAY-VIEWER-FIX: Forcing Event Sourcing to True as this is the only supported mode for replay.
        self._use_event_sourcing = True

        if self._use_event_sourcing:
            print("[DASHBOARD] Initialized in EVENT SOURCING mode")
        else:
            print("[DASHBOARD] Initialized in LEGACY mode")
        # ===== END NUEVO =====

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Table View
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        layout.addWidget(self.table_view)

        # Replay Scrubber UI
        scrubber_layout = QHBoxLayout()
        self.time_label = QLabel("Time: 0.00s")
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 1000) # Placeholder range
        scrubber_layout.addWidget(self.time_label)
        scrubber_layout.addWidget(self.time_slider)
        layout.addLayout(scrubber_layout)

        # Connect signals
        self.time_slider.valueChanged.connect(self.seek_simulation_time)

        # Set font
        font = QFont("Consolas", 10)
        self.table_view.setFont(font)
        self.table_view.horizontalHeader().setFont(font)

        # Data Model
        self.model = WorkOrderTableModel([])

        # Sorting Proxy Model
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.table_view.setModel(self.proxy_model)

        # Adjust column widths to content
        self.table_view.resizeColumnsToContents()

        # Start the queue listener thread if a queue is provided
        if self.queue_from_sim:
            self.setup_queue_listener()

    def setup_queue_listener(self):
        """
        Sets up and starts the QThread for listening to the IPC queue.
        """
        self.thread = QThread()
        self.listener = QueueListener(self.queue_from_sim)
        self.listener.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.listener.run)
        self.listener.message_received.connect(self.handle_message)

        # Start the thread
        self.thread.start()

    def handle_message(self, message: Dict[str, Any]):
        """
        Handle incoming messages from simulation.
        Supports both legacy mode and Event Sourcing mode.
        """
        if not message:
            return

        message_type = message.get("type")

        # ===== Event Sourcing Mode =====
        if self._use_event_sourcing:
            self._handle_event_sourcing_message(message_type, message)
        # ===== Legacy Mode =====
        else:
            self._handle_legacy_message(message_type, message)

        # Signal acknowledgment after processing is complete
        if self.ack_event:
            self.ack_event.set()

    def _handle_legacy_message(self, message_type: str, message: Dict[str, Any]):
        """Handle messages in legacy mode (existing behavior)."""
        # TODO: Mover aquí todo el código existente de handle_message()
        # Este método mantiene la funcionalidad actual sin cambios
        pass

    def _handle_event_sourcing_message(self, message_type: str, message: Dict[str, Any]):
        """
        Handle messages in Event Sourcing mode.
        Routes events to specific handlers.
        """
        # State Management Events
        if message_type == "state_reset":
            self._handle_state_reset(message)

        elif message_type == "state_snapshot":
            self._handle_state_snapshot(message)

        # WorkOrder Events (Granular)
        elif message_type == "wo_status_changed":
            self._handle_wo_status_changed(message)

        elif message_type == "wo_assigned":
            self._handle_wo_assigned(message)

        elif message_type == "wo_progress_updated":
            self._handle_wo_progress_updated(message)

        elif message_type == "wo_completed":
            self._handle_wo_completed(message)

        # NUEVO: Handle generic work order update for real-time data population
        elif message_type == "work_order_update":
            self._handle_wo_update(message)

        # Time Events
        elif message_type == "time_tick":
            self._handle_time_tick(message)

        elif message_type == "time_seek":
            self._handle_time_seek(message)

        # Metrics Events
        elif message_type == "metrics_updated":
            self._handle_metrics_updated(message)

        else:
            print(f"[DASHBOARD-WARNING] Unknown event type: {message_type}")

    def _handle_state_reset(self, message: Dict[str, Any]):
        """
        Handle STATE_RESET event - Clear all local state.
        This is the first step in the scrubber time-seek protocol.

        Protocol: SEEK_TIME -> STATE_RESET -> STATE_SNAPSHOT -> SEEK_COMPLETE
        """
        reason = message.get('data', {}).get('reason', 'unknown')
        target_time = message.get('data', {}).get('target_time', 0.0)

        print(f"[DASHBOARD] STATE RESET received - reason: {reason}, target_time: {target_time:.2f}s")

        # Set rebuilding flag to block incremental updates
        self._is_rebuilding_state = True

        # Clear all local state
        self._local_wo_state.clear()
        self._local_operator_state.clear()
        self._local_metrics.clear()

        # Clear UI table
        self.model.beginResetModel()
        self.model._data.clear()
        self.model.endResetModel()

        # Update status bar
        self.statusBar().showMessage(f"Rebuilding state at time {target_time:.2f}s...")

        print(f"[DASHBOARD] State cleared, awaiting STATE_SNAPSHOT...")

    def _handle_state_snapshot(self, message: Dict[str, Any]):
        """
        Handle STATE_SNAPSHOT event - Rebuild complete state from snapshot.
        This is the second step in the scrubber time-seek protocol.

        Protocol: SEEK_TIME -> STATE_RESET -> STATE_SNAPSHOT -> SEEK_COMPLETE
        """
        timestamp = message.get('timestamp', 0.0)
        data = message.get('data', {})

        work_orders = data.get('work_orders', [])
        operators = data.get('operators', [])
        metrics = data.get('metrics', {})

        print(f"[DASHBOARD] STATE SNAPSHOT received at time {timestamp:.2f}s")
        print(f"[DASHBOARD]   - WorkOrders: {len(work_orders)}")
        print(f"[DASHBOARD]   - Operators: {len(operators)}")
        print(f"[DASHBOARD]   - Metrics keys: {list(metrics.keys())}")

        # Rebuild local state from snapshot
        for wo in work_orders:
            wo_id = wo.get('id')
            if wo_id:
                self._local_wo_state[wo_id] = wo

        for op in operators:
            op_id = op.get('id')
            if op_id:
                self._local_operator_state[op_id] = op

        self._local_metrics = metrics
        self._last_snapshot_time = timestamp

        # Update UI table (batch update)
        self.model.beginResetModel()
        self.model._data = list(self._local_wo_state.values())
        self.model.endResetModel()

        # Rebuild the ID-to-row map for fast lookups
        self._rebuild_wo_id_map()

        # Update time slider if exists
        if hasattr(self, 'time_slider') and self.time_slider:
            self.time_slider.setValue(int(timestamp))

        # Clear rebuilding flag
        self._is_rebuilding_state = False

        # Update status bar
        completed_wos = sum(1 for wo in work_orders if wo.get('status') == 'staged')
        total_wos = len(work_orders)
        self.statusBar().showMessage(
            f"State rebuilt: {completed_wos}/{total_wos} WOs staged at t={timestamp:.1f}s"
        )

        print(f"[DASHBOARD] State rebuilt successfully: {len(work_orders)} WorkOrders")

        # Send SEEK_COMPLETE confirmation back to engine
        if self.queue_to_sim:
            self.queue_to_sim.put({
                'type': 'SEEK_COMPLETE',
                'timestamp': timestamp
            })
            print(f"[DASHBOARD] SEEK_COMPLETE confirmation sent")

    def _handle_wo_status_changed(self, message: Dict[str, Any]):
        """
        Handle WorkOrder status change event (granular update).
        Only updates the specific status field.
        """
        if self._is_rebuilding_state:
            return  # Skip during state rebuild

        data = message.get('data', {})
        wo_id = data.get('wo_id')
        old_status = data.get('old_status')
        new_status = data.get('new_status')

        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            # BUGFIX: Update the model's actual data source, not just the local cache.
            self.model._data[row]['status'] = new_status
            if wo_id in self._local_wo_state:
                self._local_wo_state[wo_id]['status'] = new_status

            # Emit dataChanged signal for the entire row to ensure UI update
            left_index = self.model.index(row, 0)
            right_index = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left_index, right_index)

            print(f"[DASHBOARD] WO {wo_id} status: {old_status} -> {new_status}")

    def _handle_wo_assigned(self, message: Dict[str, Any]):
        """
        Handle WorkOrder assignment event (granular update).
        """
        if self._is_rebuilding_state:
            return

        data = message.get('data', {})
        wo_id = data.get('wo_id')
        agent_id = data.get('agent_id')
        timestamp_assigned = data.get('timestamp_assigned', 0.0)

        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            # BUGFIX: Update the model's actual data source.
            self.model._data[row]['assigned_agent_id'] = agent_id
            self.model._data[row]['timestamp_assigned'] = timestamp_assigned
            if wo_id in self._local_wo_state:
                self._local_wo_state[wo_id]['assigned_agent_id'] = agent_id
                self._local_wo_state[wo_id]['timestamp_assigned'] = timestamp_assigned

            # Update UI by emitting dataChanged for the entire row
            left_index = self.model.index(row, 0)
            right_index = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left_index, right_index)

            print(f"[DASHBOARD] WO {wo_id} assigned to {agent_id}")

    def _handle_wo_progress_updated(self, message: Dict[str, Any]):
        """
        Handle WorkOrder progress update event (granular update).
        """
        if self._is_rebuilding_state:
            return

        data = message.get('data', {})
        wo_id = data.get('wo_id')

        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            # BUGFIX: Update the model's actual data source.
            self.model._data[row]['cantidad_restante'] = data.get('cantidad_restante')
            self.model._data[row]['volumen_restante'] = data.get('volumen_restante')
            self.model._data[row]['progress'] = data.get('progress_percentage', 0.0)
            if wo_id in self._local_wo_state:
                self._local_wo_state[wo_id]['cantidad_restante'] = data.get('cantidad_restante')
                self._local_wo_state[wo_id]['volumen_restante'] = data.get('volumen_restante')
                self._local_wo_state[wo_id]['progress'] = data.get('progress_percentage', 0.0)

            # Update UI (emit signal for entire row for simplicity)
            left_index = self.model.index(row, 0)
            right_index = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left_index, right_index)

    def _handle_wo_completed(self, message: Dict[str, Any]):
        """
        Handle WorkOrder completion event.
        """
        if self._is_rebuilding_state:
            return

        data = message.get('data', {})
        wo_id = data.get('wo_id')
        completion_time = data.get('completion_time', 0.0)

        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            # BUGFIX: Update the model's actual data source.
            self.model._data[row]['status'] = 'staged'
            self.model._data[row]['completion_time'] = completion_time
            self.model._data[row]['cantidad_restante'] = 0
            self.model._data[row]['volumen_restante'] = 0.0
            if wo_id in self._local_wo_state:
                self._local_wo_state[wo_id]['status'] = 'staged'
                self._local_wo_state[wo_id]['completion_time'] = completion_time
                self._local_wo_state[wo_id]['cantidad_restante'] = 0
                self._local_wo_state[wo_id]['volumen_restante'] = 0.0

            # Update UI
            left_index = self.model.index(row, 0)
            right_index = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left_index, right_index)

            print(f"[DASHBOARD] WO {wo_id} COMPLETED at t={completion_time:.2f}s")

    def _handle_wo_update(self, message: Dict[str, Any]):
        """
        Handle a generic WorkOrder update event.
        This is the main handler for real-time data updates during replay.
        """
        if self._is_rebuilding_state:
            return  # Skip during state rebuild

        # FIX: The event data is at the top level, not in a 'data' key.
        wo_data = message.copy()
        wo_id = wo_data.get('id')

        if not wo_id:
            return

        # Remove non-attribute keys before updating
        wo_data.pop('type', None)
        wo_data.pop('timestamp', None)

        row = self._find_row_by_wo_id(wo_id)
        if row >= 0:
            # Update the model's underlying data source for the specific row
            self.model._data[row].update(wo_data)
            
            # Update the local state cache as well
            if wo_id in self._local_wo_state:
                self._local_wo_state[wo_id].update(wo_data)

            # Emit dataChanged for the entire row to trigger a UI refresh
            left_index = self.model.index(row, 0)
            right_index = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left_index, right_index)


    def _handle_time_update(self, message):
        """Updates the time slider and label."""
        timestamp = message.get('timestamp', 0.0)
        self.time_slider.blockSignals(True)
        self.time_slider.setValue(int(timestamp))
        self.time_slider.blockSignals(False)
        self.time_label.setText(f"Time: {timestamp:.2f}s")

    def _find_row_by_wo_id(self, wo_id: str) -> int:
        """
        Find row index in table by WorkOrder ID using a cache.
        Returns -1 if not found.
        """
        return self._wo_id_to_row_map.get(wo_id, -1)

    def _rebuild_wo_id_map(self):
        """Rebuilds the dictionary mapping WorkOrder IDs to their row index."""
        print("[DASHBOARD-DEBUG] Rebuilding WO ID to row map...")
        self._wo_id_to_row_map = {
            wo.get('id'): i for i, wo in enumerate(self.model._data)
        }
        print(f"[DASHBOARD-DEBUG] Map rebuilt with {len(self._wo_id_to_row_map)} entries.")

    def _get_column_index(self, column_name: str) -> int:
        """
        Get column index by column name.
        Returns -1 if not found.
        """
        if not hasattr(self.model, 'headers'):
            return -1

        try:
            return self.model.headers.index(column_name)
        except (ValueError, AttributeError):
            return -1

    def _handle_time_tick(self, message: Dict[str, Any]):
        """Handle periodic time update event."""
        timestamp = message.get('timestamp', 0.0)

        if hasattr(self, 'time_slider') and self.time_slider:
            # Block signals to prevent triggering seek_simulation_time
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(int(timestamp))
            self.time_slider.blockSignals(False)

    def _handle_time_seek(self, message: Dict[str, Any]):
        """Handle time seek command (user interaction)."""
        target_time = message.get('data', {}).get('target_time', 0.0)
        print(f"[DASHBOARD] TIME_SEEK command received: {target_time:.2f}s")
        # STATE_RESET and STATE_SNAPSHOT will follow

    def _handle_metrics_updated(self, message: Dict[str, Any]):
        """Handle metrics update event."""
        if self._is_rebuilding_state:
            return

        metrics = message.get('data', {})
        self._local_metrics.update(metrics)

        # Update status bar with metrics
        completed = metrics.get('workorders_completadas', 0)
        total = metrics.get('total_wos', 0)
        time_sim = metrics.get('tiempo', 0.0)

        if total > 0:
            self.statusBar().showMessage(
                f"Progress: {completed}/{total} WOs | Time: {time_sim:.1f}s"
            )


    def seek_simulation_time(self, value):
        """
        Sends a SEEK_TIME message to the simulation engine.
        """
        # Prevent seeks during state rebuilding to avoid infinite loops
        if self._is_rebuilding_state:
            print(f"[DEBUG-Dashboard] Ignoring seek during state rebuild: {value}")
            return
            
        # The slider value might need scaling depending on the simulation's total time
        # For now, we'll send the raw value.
        timestamp = float(value)
        print(f"[DEBUG-Dashboard] seek_simulation_time called with value: {value}, timestamp: {timestamp}")
        print(f"[DEBUG-Dashboard] queue_to_sim status: {self.queue_to_sim is not None}")
        print(f"[DEBUG-Dashboard] queue_to_sim type: {type(self.queue_to_sim)}")
        self.time_label.setText(f"Time: {timestamp:.2f}s")

        if self.queue_to_sim:
            message = {
                'type': 'SEEK_TIME',
                'timestamp': timestamp
            }
            print(f"[DEBUG-Dashboard] Sending SEEK_TIME message: {message}")
            try:
                self.queue_to_sim.put(message)
                print(f"[DEBUG-Dashboard] SEEK_TIME message sent successfully")
            except Exception as e:
                print(f"[DEBUG-Dashboard] Error sending SEEK_TIME message: {e}")
        else:
            print(f"[DEBUG-Dashboard] queue_to_sim is None, cannot send SEEK_TIME message")

    def closeEvent(self, event):
        """
        Handle the window close event to clean up the listener thread.
        """
        if hasattr(self, 'thread') and isinstance(self.thread, QThread) and self.thread.isRunning():
            # Send a sentinel value to stop the listener loop
            if self.queue_from_sim:
                self.queue_from_sim.put(None)
            self.thread.quit()
            self.thread.wait()
        event.accept()


def launch_dashboard_process(data_queue, command_queue, ack_event):
    """
    Entry point for the dashboard process.
    Initializes and runs the PyQt6 application.

    Args:
        data_queue: Queue for receiving data from simulation (queue_from_sim)
        command_queue: Queue for sending commands to simulation (queue_to_sim)
        ack_event: Event to signal acknowledgment of message processing.
    """
    app = QApplication(sys.argv)
    dashboard = WorkOrderDashboard(data_queue, command_queue, ack_event)
    dashboard.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    # This block allows for standalone testing of the dashboard UI.
    # You can run this file directly to see the UI.
    # In production, `launch_dashboard_process` will be called by the main simulation.

    # Dummy data for testing
    test_data = [
        {
            "id": "WO_0001", "order_id": "ORD-001", "tour_id": "TOUR-A", "sku_id": "SKU001",
            "product": "Product A", "status": "assigned", "assigned_agent_id": "Agent_1",
            "priority": 9999, "items": 1, "total_qty": 10, "volume": 5.0, "location": "(1, 2)",
            "staging": "(3, 4)", "work_group": "wg_a", "work_area": "wa_a", "executions": 1,
            "start_time": 123.45, "progress": 0.5
        },
        {
            "id": "WO_0002", "order_id": "ORD-002", "tour_id": "TOUR-B", "sku_id": "SKU002",
            "product": "Product B", "status": "released", "assigned_agent_id": "None",
            "priority": 5000, "items": 2, "total_qty": 20, "volume": 10.0, "location": "(5, 6)",
            "staging": "(7, 8)", "work_group": "wg_b", "work_area": "wa_b", "executions": 0,
            "start_time": 0.0, "progress": 0.0
        },
    ]

    app = QApplication(sys.argv)
    dashboard = WorkOrderDashboard()
    dashboard.model.setData(test_data)  # Manually set data for testing
    dashboard.show()
    sys.exit(app.exec())