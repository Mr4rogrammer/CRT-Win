"""PySide6 main window for the CRT signal app."""
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QSpinBox,
    QTabWidget,
    QMessageBox,
    QAbstractItemView,
    QStackedWidget,
)

from ..database import Database
from ..engine import analyze_symbols
from ..mt5_connector import MT5Connector, MT5_AVAILABLE

SIGNAL_COLORS = {
    "BUY": QColor("#1b7f3c"),
    "SELL": QColor("#c0392b"),
    "NO TRADE": QColor("#7f8c8d"),
    "ERROR": QColor("#e67e22"),
}

TABLE_COLUMNS = [
    "Symbol", "Signal", "Entry", "Stop Loss", "Take Profit",
    "R:R", "Reason", "Last Update",
]


class RefreshWorker(QObject):
    """Runs MT5 fetch + CRT evaluation off the UI thread."""
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, connector: MT5Connector, symbols):
        super().__init__()
        self.connector = connector
        self.symbols = symbols

    def run(self):
        try:
            if not self.connector.connected:
                self.connector.connect()
            results = analyze_symbols(self.connector, self.symbols)
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ConnectWorker(QObject):
    """Attempts to connect to the local MT5 terminal off the UI thread."""
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, connector: MT5Connector):
        super().__init__()
        self.connector = connector

    def run(self):
        try:
            self.connector.connect()
            self.succeeded.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRT Signal Scanner (MT5 - Daily)")
        self.resize(1100, 600)

        self.db = Database()
        self.connector = MT5Connector()
        self._thread: QThread | None = None
        self._worker: RefreshWorker | None = None
        self._connect_thread: QThread | None = None
        self._connect_worker: ConnectWorker | None = None

        self._build_ui()
        self._load_symbols_into_table()
        self._setup_auto_refresh_timer()

        # Start on the "not connected" page and try to connect automatically.
        self.stack.setCurrentWidget(self.connect_page)
        QTimer.singleShot(200, self._attempt_connect)

    # ---------------------------------------------------------- UI setup
    def _build_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.connect_page = self._build_connect_page()
        self.main_page = self._build_main_page()

        self.stack.addWidget(self.connect_page)
        self.stack.addWidget(self.main_page)

    def _build_connect_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()

        title = QLabel("Not Connected to MetaTrader 5")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.connect_message_label = QLabel(
            "Click Connect to try connecting to your local MT5 terminal."
        )
        self.connect_message_label.setAlignment(Qt.AlignCenter)
        self.connect_message_label.setWordWrap(True)
        self.connect_message_label.setStyleSheet("color: #7f8c8d; padding: 0 60px;")

        if not MT5_AVAILABLE:
            self.connect_message_label.setText(
                "The 'MetaTrader5' package is only available on Windows. Install it "
                "with 'pip install MetaTrader5' on your Windows machine and make sure "
                "the MetaTrader 5 terminal is installed and running."
            )
            self.connect_message_label.setStyleSheet("color: #e67e22; padding: 0 60px;")

        self.connect_btn = QPushButton("Connect to MT5")
        self.connect_btn.setFixedWidth(220)
        self.connect_btn.clicked.connect(self._attempt_connect)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.connect_btn)
        btn_row.addStretch()

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.connect_message_label)
        layout.addSpacing(20)
        layout.addLayout(btn_row)
        layout.addStretch()
        return page

    def _build_main_page(self) -> QWidget:
        central = QWidget()
        root = QVBoxLayout(central)

        # --- Top control bar ---
        top_bar = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g. EURUSD")
        self.symbol_input.returnPressed.connect(self._on_add_symbol)
        add_btn = QPushButton("Add Pair")
        add_btn.clicked.connect(self._on_add_symbol)

        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self.refresh_signals)

        self.auto_refresh_checkbox = QCheckBox("Auto-refresh every")
        auto_enabled = self.db.get_setting("auto_refresh_enabled", "1") == "1"
        self.auto_refresh_checkbox.setChecked(auto_enabled)
        self.auto_refresh_checkbox.stateChanged.connect(self._on_auto_refresh_toggled)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(int(self.db.get_setting("refresh_interval_minutes", "5")))
        self.interval_spin.setSuffix(" min")
        self.interval_spin.valueChanged.connect(self._on_interval_changed)

        top_bar.addWidget(QLabel("Symbol:"))
        top_bar.addWidget(self.symbol_input)
        top_bar.addWidget(add_btn)
        top_bar.addSpacing(20)
        top_bar.addWidget(self.refresh_btn)
        top_bar.addSpacing(20)
        top_bar.addWidget(self.auto_refresh_checkbox)
        top_bar.addWidget(self.interval_spin)
        top_bar.addStretch()
        root.addLayout(top_bar)

        # --- Status bar row ---
        self.status_label = QLabel("Not connected to MT5.")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        root.addWidget(self.status_label)

        # --- Tabs: Live signals / History ---
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # Live signals tab
        live_tab = QWidget()
        live_layout = QVBoxLayout(live_tab)
        self.table = QTableWidget(0, len(TABLE_COLUMNS) + 1)  # +1 for Remove button
        self.table.setHorizontalHeaderLabels(TABLE_COLUMNS + ["Remove"])
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        live_layout.addWidget(self.table)
        self.tabs.addTab(live_tab, "Live Signals")

        # History tab
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_controls = QHBoxLayout()
        refresh_history_btn = QPushButton("Reload History")
        refresh_history_btn.clicked.connect(self._load_history_into_table)
        history_controls.addWidget(refresh_history_btn)
        history_controls.addStretch()
        history_layout.addLayout(history_controls)

        self.history_table = QTableWidget(0, 9)
        self.history_table.setHorizontalHeaderLabels([
            "Symbol", "Signal", "Entry", "Stop Loss", "Take Profit",
            "R:R", "Reason", "Evaluated At", "C2 Close",
        ])
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        history_layout.addWidget(self.history_table)
        self.tabs.addTab(history_tab, "Signal History")

        self._load_history_into_table()
        return central

    def _setup_auto_refresh_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_signals)
        self._apply_timer_state()

    def _apply_timer_state(self):
        if self.auto_refresh_checkbox.isChecked():
            self.timer.start(self.interval_spin.value() * 60 * 1000)
        else:
            self.timer.stop()

    # ---------------------------------------------------------- Symbol management
    def _load_symbols_into_table(self):
        self.table.setRowCount(0)
        for symbol in self.db.get_pairs():
            self._add_symbol_row(symbol)

    def _add_symbol_row(self, symbol: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(symbol))
        for col in range(1, len(TABLE_COLUMNS)):
            self.table.setItem(row, col, QTableWidgetItem(""))
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda _, s=symbol: self._on_remove_symbol(s))
        self.table.setCellWidget(row, len(TABLE_COLUMNS), remove_btn)

    def _on_add_symbol(self):
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            return
        if self.db.add_pair(symbol):
            self._add_symbol_row(symbol)
            self.symbol_input.clear()
        else:
            QMessageBox.information(self, "Already added", f"{symbol} is already in your watch list.")

    def _on_remove_symbol(self, symbol: str):
        self.db.remove_pair(symbol)
        self._load_symbols_into_table()

    def _find_row_for_symbol(self, symbol: str):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == symbol:
                return row
        return None

    # ---------------------------------------------------------- Settings
    def _on_auto_refresh_toggled(self, _state):
        self.db.set_setting("auto_refresh_enabled", "1" if self.auto_refresh_checkbox.isChecked() else "0")
        self._apply_timer_state()

    def _on_interval_changed(self, value: int):
        self.db.set_setting("refresh_interval_minutes", str(value))
        self._apply_timer_state()

    # ---------------------------------------------------------- Connection
    def _attempt_connect(self):
        if self._connect_thread is not None and self._connect_thread.isRunning():
            return
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        self.connect_message_label.setText("Attempting to connect to MetaTrader 5...")
        self.connect_message_label.setStyleSheet("color: #2980b9; padding: 0 60px;")

        self._connect_thread = QThread(self)
        self._connect_worker = ConnectWorker(self.connector)
        self._connect_worker.moveToThread(self._connect_thread)
        self._connect_thread.started.connect(self._connect_worker.run)
        self._connect_worker.succeeded.connect(self._on_connect_succeeded)
        self._connect_worker.failed.connect(self._on_connect_failed)
        self._connect_worker.succeeded.connect(self._connect_thread.quit)
        self._connect_worker.failed.connect(self._connect_thread.quit)
        self._connect_thread.finished.connect(self._cleanup_connect_thread)
        self._connect_thread.start()

    def _cleanup_connect_thread(self):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect to MT5")
        self._connect_thread = None
        self._connect_worker = None

    def _on_connect_succeeded(self):
        self.stack.setCurrentWidget(self.main_page)
        self.status_label.setText("Connected to MT5.")
        self.status_label.setStyleSheet("color: #1b7f3c;")
        self.refresh_signals()

    def _on_connect_failed(self, message: str):
        self.connect_message_label.setText(message)
        self.connect_message_label.setStyleSheet("color: #c0392b; padding: 0 60px;")
        self.stack.setCurrentWidget(self.connect_page)

    # ---------------------------------------------------------- Refresh logic
    def refresh_signals(self):
        symbols = self.db.get_pairs()
        if not symbols:
            self.status_label.setText("Add at least one pair to scan.")
            return
        if self._thread is not None and self._thread.isRunning():
            return  # already refreshing

        self.refresh_btn.setEnabled(False)
        self.status_label.setText("Fetching daily candles from MT5...")
        self.status_label.setStyleSheet("color: #2980b9;")

        self._thread = QThread(self)
        self._worker = RefreshWorker(self.connector, symbols)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_refresh_finished)
        self._worker.failed.connect(self._on_refresh_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _cleanup_thread(self):
        self.refresh_btn.setEnabled(True)
        self._thread = None
        self._worker = None

    def _on_refresh_failed(self, message: str):
        self.status_label.setText(f"MT5 error: {message}")
        self.status_label.setStyleSheet("color: #c0392b;")
        # Connection was likely lost - send the user back to the connect page.
        self.connector.connected = False
        self._on_connect_failed(message)

    def _on_refresh_finished(self, results):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.setText(f"Connected. Last updated: {now_str}")
        self.status_label.setStyleSheet("color: #1b7f3c;")

        for result in results:
            row = self._find_row_for_symbol(result.symbol)
            if row is None:
                continue
            self._populate_row(row, result, now_str)

            if result.signal in ("BUY", "SELL"):
                c2_iso = result.c2.time.isoformat() if result.c2 else None
                if not self.db.already_logged(result.symbol, result.signal, c2_iso):
                    self.db.log_signal(result)

        self._load_history_into_table()

    def _populate_row(self, row: int, result, now_str: str):
        def set_cell(col, text, color=None):
            item = QTableWidgetItem(text)
            if color:
                item.setForeground(color)
            self.table.setItem(row, col, item)

        color = SIGNAL_COLORS.get(result.signal)
        set_cell(1, result.signal, color)
        set_cell(2, f"{result.entry:.5f}" if result.entry is not None else "-")
        set_cell(3, f"{result.stop_loss:.5f}" if result.stop_loss is not None else "-")
        set_cell(4, f"{result.take_profit:.5f}" if result.take_profit is not None else "-")
        set_cell(5, f"{result.risk_reward:.2f}" if result.risk_reward else "-")
        set_cell(6, result.reason or "")
        set_cell(7, now_str)

    def _load_history_into_table(self):
        rows = self.db.get_history(limit=200)
        self.history_table.setRowCount(0)
        for r in rows:
            row_idx = self.history_table.rowCount()
            self.history_table.insertRow(row_idx)
            values = [
                r["symbol"], r["signal"],
                f"{r['entry']:.5f}" if r["entry"] is not None else "-",
                f"{r['stop_loss']:.5f}" if r["stop_loss"] is not None else "-",
                f"{r['take_profit']:.5f}" if r["take_profit"] is not None else "-",
                f"{r['risk_reward']:.2f}" if r["risk_reward"] is not None else "-",
                r["reason"] or "",
                r["evaluated_at"],
                f"{r['c2_close']:.5f}" if r["c2_close"] is not None else "-",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                color = SIGNAL_COLORS.get(r["signal"])
                if color and col == 1:
                    item.setForeground(color)
                self.history_table.setItem(row_idx, col, item)

    def closeEvent(self, event):
        self.timer.stop()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        self.connector.shutdown()
        super().closeEvent(event)
