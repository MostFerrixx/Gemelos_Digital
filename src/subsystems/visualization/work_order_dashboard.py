# -*- coding: utf-8 -*-
"""
WorkOrder Real-Time Dashboard.

Displays the state of all WorkOrders in a real-time, sortable table.
Built with PyQt6 for performance and native look-and-feel.
"""

import sys
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
    'pending': QColor(255, 193, 7),      # Amber/Yellow
    'assigned': QColor(0, 123, 255),      # Blue
    'in_progress': QColor(255, 87, 34),   # Orange
    'completed': QColor(40, 167, 69),     # Green
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
        """Convert WorkOrderSnapshot to dictionary if needed."""
        if hasattr(data, '__dict__'):
            return {
                'id': data.id,
                'order_id': data.order_id,
                'tour_id': data.tour_id,
                'sku_id': data.sku_id,
                'status': data.status,
                'ubicacion': data.ubicacion,
                'work_area': data.work_area,
                'cantidad_restante': data.cantidad_restante,
                'volumen_restante': data.volumen_restante,
                'assigned_agent_id': data.assigned_agent_id,
                'timestamp': data.timestamp
            }
        return data

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row_data = self._convert_to_dict(self._data[index.row()])
            column_key = COLUMN_HEADERS[index.column()][1]
            return row_data.get(column_key, "")

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Color-code rows based on status
            row_data = self._convert_to_dict(self._data[index.row()])
            status = row_data.get('status', 'pending')
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
    def __init__(self, queue_from_sim=None, queue_to_sim=None):
        super().__init__()
        self.setWindowTitle("Digital Twin Warehouse - Dashboard v1.0")
        self.setGeometry(100, 100, 1600, 800)

        # Store communication queues
        self.queue_from_sim = queue_from_sim
        self.queue_to_sim = queue_to_sim

        # Local state rebuilt from events
        self._local_wo_state = {}  # Dict[wo_id, WorkOrderDict]
        self._is_rebuilding_state = False

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

    def handle_message(self, message):
        """Routes incoming events to the appropriate handler and logs performance."""
        start_time = time.time()
        event_type = message.get("type")

        sent_timestamp = message.get('metadata', {}).get('sent_timestamp')
        if sent_timestamp:
            latency_ms = (start_time - sent_timestamp) * 1000
            print(f"[PERF] event_type={event_type} latency_ms={latency_ms:.2f} timestamp={start_time}")

        if self._is_rebuilding_state and event_type not in ("state_reset", "state_snapshot"):
            return

        handlers = {
            "state_reset": self._handle_state_reset,
            "state_snapshot": self._handle_state_snapshot,
            "wo_status_changed": self._handle_wo_status_changed,
            "wo_assigned": self._handle_wo_assigned,
            "wo_progress_updated": self._handle_wo_progress_updated,
            "TIME_UPDATE": self._handle_time_update,
        }

        handler = handlers.get(event_type)
        if handler:
            handler(message)

    def _handle_state_reset(self, message):
        """Clears the local state in preparation for a snapshot."""
        print(f"[DASHBOARD] STATE RESET received. Reason: {message.get('data', {}).get('reason')}")
        self._is_rebuilding_state = True
        self._local_wo_state.clear()
        self.model.setData([])
        self.table_view.resizeColumnsToContents()

    def _handle_state_snapshot(self, message):
        """Rebuilds the local state from a snapshot."""
        print("[DASHBOARD] STATE SNAPSHOT received.")
        data = message.get('data', {})
        work_orders = data.get('work_orders', [])

        for wo in work_orders:
            self._local_wo_state[wo['id']] = wo

        self.model.setData(list(self._local_wo_state.values()))
        self.table_view.resizeColumnsToContents()
        self._is_rebuilding_state = False
        print(f"[DASHBOARD] State rebuilt with {len(work_orders)} work orders.")

        # Send SEEK_COMPLETE confirmation back to the engine
        if self.queue_to_sim:
            confirmation_msg = {
                'type': 'SEEK_COMPLETE',
                'timestamp': time.time(),
            }
            self.queue_to_sim.put(confirmation_msg)
            print(f"[DASHBOARD] SEEK_COMPLETE confirmation sent.")

    def _handle_wo_status_changed(self, message):
        """Handles a granular change to a WorkOrder's status."""
        data = message.get('data', {})
        wo_id = data.get('wo_id')
        if wo_id in self._local_wo_state:
            self._local_wo_state[wo_id]['status'] = data.get('new_status')
            self._update_view_for_wo(wo_id)

    def _handle_wo_assigned(self, message):
        """Handles a granular change to a WorkOrder's assignment."""
        data = message.get('data', {})
        wo_id = data.get('wo_id')
        if wo_id in self._local_wo_state:
            self._local_wo_state[wo_id]['assigned_agent_id'] = data.get('agent_id')
            self._update_view_for_wo(wo_id)

    def _handle_wo_progress_updated(self, message):
        """Handles a granular change to a WorkOrder's progress."""
        data = message.get('data', {})
        wo_id = data.get('wo_id')
        if wo_id in self._local_wo_state:
            self._local_wo_state[wo_id].update({
                'cantidad_restante': data.get('cantidad_restante'),
                'volumen_restante': data.get('volumen_restante'),
                'progress': data.get('progress_percentage'),
            })
            self._update_view_for_wo(wo_id)

    def _handle_time_update(self, message):
        """Updates the time slider and label."""
        timestamp = message.get('timestamp', 0.0)
        self.time_slider.blockSignals(True)
        self.time_slider.setValue(int(timestamp))
        self.time_slider.blockSignals(False)
        self.time_label.setText(f"Time: {timestamp:.2f}s")

    def _update_view_for_wo(self, wo_id: str):
        """Finds the row for a given WO_ID and emits dataChanged for it."""
        # This is a simplified approach. A real implementation would have a faster lookup.
        for row in range(self.model.rowCount()):
            if self.model._data[row]['id'] == wo_id:
                self.model.dataChanged.emit(self.model.index(row, 0), self.model.index(row, self.model.columnCount() - 1))
                return


    def seek_simulation_time(self, value):
        """
        Sends a SEEK_TIME message to the simulation engine.
        """
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


def launch_dashboard_process(data_queue, command_queue):
    """
    Entry point for the dashboard process.
    Initializes and runs the PyQt6 application.

    Args:
        data_queue: Queue for receiving data from simulation (queue_from_sim)
        command_queue: Queue for sending commands to simulation (queue_to_sim)
    """
    app = QApplication(sys.argv)
    dashboard = WorkOrderDashboard(data_queue, command_queue)
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
            "product": "Product B", "status": "pending", "assigned_agent_id": "None",
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