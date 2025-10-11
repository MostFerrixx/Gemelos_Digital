# -*- coding: utf-8 -*-
"""
WorkOrder Real-Time Dashboard.

Displays the state of all WorkOrders in a real-time, sortable table.
Built with PyQt6 for performance and native look-and-feel.
"""

import sys
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
from PyQt6.QtGui import QFont

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

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row_data = self._data[index.row()]
            column_key = COLUMN_HEADERS[index.column()][1]
            return row_data.get(column_key, "")

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
        id_to_row_map = {wo['id']: i for i, wo in enumerate(self._data)}

        new_rows_data = []

        # Process updates for existing items first
        for wo_update in updates:
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

        # Buffer for high-frequency delta updates
        self._delta_buffer = []

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

        # Setup update throttling timer
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(67)  # ~15 FPS
        self.update_timer.timeout.connect(self.process_buffered_updates)
        self.update_timer.start()

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
        """
        Handles messages received from the simulation.
        Routes messages to the correct handler or buffers them.
        """
        msg_type = message.get("type")

        if msg_type in ("full_state", "FULL_STATE_SNAPSHOT"):
            # For full updates, clear buffer and apply immediately
            self._delta_buffer.clear()
            self.model.setData(message.get("data", []))
            self.table_view.resizeColumnsToContents()
        elif msg_type == "delta":
            # For delta updates, add to buffer to be processed by the timer
            updates = message.get("data", [])
            if updates:
                self._delta_buffer.extend(updates)

    def process_buffered_updates(self):
        """
        Process the accumulated delta updates in the buffer.
        This is called by the QTimer to throttle UI refreshes.
        """
        if not self._delta_buffer:
            return

        # Process all buffered updates in one go
        self.model.updateData(self._delta_buffer)

        # Clear the buffer
        self._delta_buffer.clear()

    def seek_simulation_time(self, value):
        """
        Sends a SEEK_TIME message to the simulation engine.
        """
        # The slider value might need scaling depending on the simulation's total time
        # For now, we'll send the raw value.
        timestamp = float(value)
        self.time_label.setText(f"Time: {timestamp:.2f}s")

        if self.queue_to_sim:
            message = {
                'type': 'SEEK_TIME',
                'timestamp': timestamp
            }
            self.queue_to_sim.put(message)

    def closeEvent(self, event):
        """
        Handle the window close event to clean up the listener thread.
        """
        if hasattr(self, 'thread') and self.thread.isRunning():
            # Send a sentinel value to stop the listener loop
            if self.queue_from_sim:
                self.queue_from_sim.put(None)
            self.thread.quit()
            self.thread.wait()
        event.accept()


def launch_dashboard_process(queue_from_sim, queue_to_sim):
    """
    Entry point for the dashboard process.
    Initializes and runs the PyQt6 application.
    """
    app = QApplication(sys.argv)
    dashboard = WorkOrderDashboard(queue_from_sim, queue_to_sim)
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