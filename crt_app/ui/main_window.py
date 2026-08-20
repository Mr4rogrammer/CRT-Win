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
    QTabWidget,
    QMessageBox,
    QAbstractItemView,
    QStackedWidget,
    QScrollArea,
    QFrame,
)

from ..database import Database
from ..engine import analyze_symbols, analyze_symbol
from ..mt5_connector import MT5Connector, MT5_AVAILABLE, TIMEFRAME_MAP
from .symbol_picker import SymbolPickerDialog
from .signal_card import SignalCard, SIGNAL_SORT_PRIORITY
from .options_dialog import OptionsDialog

SIGNAL_COLORS = {
    "BUY": QColor("#3ddc84"),
    "SELL": QColor("#ff6b6b"),
    "NO TRADE": QColor("#9aa1ac"),
    "ERROR": QColor("#f0ad4e"),
}


class RefreshWorker(QObject):
    """Runs MT5 fetch + CRT evaluation off the UI thread."""
    finished = Signal(list)
    failed = Signal(str)
    progress = Signal(int, int, str)  # done_count, total_count, current_symbol

    def __init__(self, connector: MT5Connector, symbols, threshold_pct: float = 0.5, timeframe: str = "D1"):
        super().__init__()
        self.connector = connector
        self.symbols = symbols
        self.threshold_pct = threshold_pct
        self.timeframe = timeframe

    def run(self):
        try:
            if not self.connector.connected:
                self.connector.connect()
            results = []
            total = len(self.symbols)
            for i, symbol in enumerate(self.symbols):
                self.progress.emit(i, total, symbol)
                result = analyze_symbol(
                    self.connector, symbol,
                    threshold_pct=self.threshold_pct, timeframe=self.timeframe,
                )
                results.append(result)
            self.progress.emit(total, total, "")
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
        self.resize(1280, 720)
        self.setMinimumSize(900, 560)

        self.db = Database()
        self.connector = MT5Connector()
        self._thread: QThread | None = None
        self._worker: RefreshWorker | None = None
        self._connect_thread: QThread | None = None
        self._connect_worker: ConnectWorker | None = None

        self._build_ui()
        self._load_symbols_into_table()
        self._setup_auto_refresh_timer()
        self._build_options_dock()

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
        title.setStyleSheet("font-size: 22px; font-weight: 600; color: #f0f0f0;")

        self.connect_message_label = QLabel(
            "Click Connect to try connecting to your local MT5 terminal."
        )
        self.connect_message_label.setAlignment(Qt.AlignCenter)
        self.connect_message_label.setWordWrap(True)
        self.connect_message_label.setStyleSheet("color: #9aa1ac; padding: 0 60px;")

        if not MT5_AVAILABLE:
            self.connect_message_label.setText(
                "The 'MetaTrader5' package is only available on Windows. Install it "
                "with 'pip install MetaTrader5' on your Windows machine and make sure "
                "the MetaTrader 5 terminal is installed and running."
            )
            self.connect_message_label.setStyleSheet("color: #f0ad4e; padding: 0 60px;")

        self.connect_btn = QPushButton("Connect to MT5")
        self.connect_btn.setObjectName("connectButton")
        self.connect_btn.setFixedWidth(220)
        self.connect_btn.setFixedHeight(40)
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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # --- Top control bar ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g. EURUSD")
        self.symbol_input.returnPressed.connect(self._on_add_symbol)
        add_btn = QPushButton("Add Pair")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._on_add_symbol)
        browse_btn = QPushButton("Browse Pairs...")
        browse_btn.clicked.connect(self._on_browse_pairs)

        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.setObjectName("primaryButton")
        self.refresh_btn.clicked.connect(self.refresh_signals)

        self.options_btn = QPushButton("\u2699 More Options")
        self.options_btn.clicked.connect(self._on_open_options)

        top_bar.addWidget(QLabel("Symbol:"))
        top_bar.addWidget(self.symbol_input)
        top_bar.addWidget(add_btn)
        top_bar.addWidget(browse_btn)
        top_bar.addSpacing(20)
        top_bar.addWidget(self.refresh_btn)
        top_bar.addStretch()
        top_bar.addWidget(self.options_btn)

        root.addLayout(top_bar)

        # --- Status bar row ---
        self.status_label = QLabel("Not connected to MT5.")
        self.status_label.setStyleSheet("color: #9aa1ac;")
        root.addWidget(self.status_label)

        # --- Tabs: Live signals / History ---
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # Live signals tab - a scrollable list of expandable/collapsible SignalCards,
        # sorted BUY -> SELL -> NO TRADE -> ERROR.
        live_tab = QWidget()
        live_layout = QVBoxLayout(live_tab)
        live_layout.setContentsMargins(0, 0, 0, 0)

        controls_row = QHBoxLayout()
        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(lambda: self._set_all_cards_expanded(True))
        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(lambda: self._set_all_cards_expanded(False))
        controls_row.addWidget(expand_all_btn)
        controls_row.addWidget(collapse_all_btn)
        controls_row.addStretch()
        live_layout.addLayout(controls_row)

        self.signals_scroll = QScrollArea()
        self.signals_scroll.setWidgetResizable(True)
        self.signals_scroll.setFrameShape(QFrame.NoFrame)
        self.signals_container = QWidget()
        self.signals_container_layout = QVBoxLayout(self.signals_container)
        self.signals_container_layout.setContentsMargins(0, 0, 0, 0)
        self.signals_container_layout.setSpacing(6)
        self.signals_container_layout.addStretch()
        self.signals_scroll.setWidget(self.signals_container)
        live_layout.addWidget(self.signals_scroll)

        self.tabs.addTab(live_tab, "Live Signals")

        # symbol -> SignalCard
        self.signal_cards = {}

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
        self.history_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.history_table.setWordWrap(True)
        self.history_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        history_layout.addWidget(self.history_table)
        self.tabs.addTab(history_tab, "Signal History")

        self._load_history_into_table()
        return central

    def _setup_auto_refresh_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_signals)
        self._apply_timer_state()

    def _apply_timer_state(self):
        if self.db.get_setting("auto_refresh_enabled", "1") == "1":
            interval_min = int(self.db.get_setting("refresh_interval_minutes", "5"))
            self.timer.start(interval_min * 60 * 1000)
        else:
            self.timer.stop()

    # ---------------------------------------------------------- Symbol management
    def _load_symbols_into_table(self):
        # Remove existing cards.
        for card in list(self.signal_cards.values()):
            card.setParent(None)
        self.signal_cards = {}
        for symbol in self.db.get_pairs():
            self._add_symbol_row(symbol)
        self._resort_signal_cards()

    def _add_symbol_row(self, symbol: str):
        if symbol in self.signal_cards:
            return
        card = SignalCard(symbol)
        card.remove_clicked.connect(self._on_remove_symbol)
        # Insert before the trailing stretch (last item in the layout).
        insert_at = self.signals_container_layout.count() - 1
        self.signals_container_layout.insertWidget(insert_at, card)
        self.signal_cards[symbol] = card

    def _set_all_cards_expanded(self, expanded: bool):
        for card in self.signal_cards.values():
            card.set_expanded(expanded)

    def _resort_signal_cards(self):
        """Re-orders the cards in the layout: BUY first, then SELL, then
        NO TRADE, then ERROR/unknown last (alphabetical within each group)."""
        cards = sorted(self.signal_cards.values(), key=lambda c: c.sort_key())
        # Remove the trailing stretch temporarily, re-add widgets in order, restore stretch.
        while self.signals_container_layout.count():
            item = self.signals_container_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for card in cards:
            self.signals_container_layout.addWidget(card)
        self.signals_container_layout.addStretch()

    def _on_add_symbol(self):
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            return
        if self.db.add_pair(symbol):
            self._add_symbol_row(symbol)
            self._resort_signal_cards()
            self.symbol_input.clear()
        else:
            QMessageBox.information(self, "Already added", f"{symbol} is already in your watch list.")

    def _on_browse_pairs(self):
        if not self.connector.connected:
            QMessageBox.warning(
                self, "Not connected",
                "Connect to MT5 first so the full symbol list can be loaded from your broker.",
            )
            return
        try:
            all_symbols = self.connector.get_all_symbols()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Could not load symbols", str(exc))
            return

        current = set(self.db.get_pairs())
        dialog = SymbolPickerDialog(all_symbols, current, self)
        if dialog.exec() != SymbolPickerDialog.Accepted:
            return

        selected = dialog.selected_symbols()
        for symbol in selected - current:
            self.db.add_pair(symbol)
        for symbol in current - selected:
            self.db.remove_pair(symbol)
        self._load_symbols_into_table()

    def _on_remove_symbol(self, symbol: str):
        self.db.remove_pair(symbol)
        self._load_symbols_into_table()

    # ---------------------------------------------------------- Settings / Options dock
    def _build_options_dock(self):
        self.options_dock = OptionsDialog(
            auto_refresh_checked=self.db.get_setting("auto_refresh_enabled", "1") == "1",
            interval_minutes=int(self.db.get_setting("refresh_interval_minutes", "5")),
            threshold_pct=int(self.db.get_setting("threshold_pct", "50")),
            timeframe=self.db.get_setting("timeframe", "D1"),
            timeframe_choices=list(TIMEFRAME_MAP.keys()),
            parent=self,
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.options_dock)
        self.options_dock.hide()

        dialog = self.options_dock
        dialog.auto_refresh_checkbox.stateChanged.connect(
            lambda _s: self._on_auto_refresh_toggled(dialog.auto_refresh_checkbox.isChecked())
        )
        dialog.interval_spin.valueChanged.connect(self._on_interval_changed)
        dialog.threshold_spin.valueChanged.connect(self._on_threshold_changed)
        dialog.timeframe_combo.currentTextChanged.connect(self._on_timeframe_changed)
        dialog.reset_app_btn.clicked.connect(lambda: self._on_reset_app(dialog))

    def _on_open_options(self):
        self.options_dock.setVisible(not self.options_dock.isVisible())

    def _on_auto_refresh_toggled(self, checked: bool):
        self.db.set_setting("auto_refresh_enabled", "1" if checked else "0")
        self._apply_timer_state()
        self.refresh_signals()

    def _on_interval_changed(self, value: int):
        self.db.set_setting("refresh_interval_minutes", str(value))
        self._apply_timer_state()
        self.refresh_signals()

    def _on_threshold_changed(self, value: int):
        self.db.set_setting("threshold_pct", str(value))
        self.refresh_signals()

    def _on_timeframe_changed(self, value: str):
        self.db.set_setting("timeframe", value)
        self.refresh_signals()

    def _on_reset_app(self, dialog=None):
        confirm = QMessageBox.question(
            dialog or self,
            "Reset App?",
            "This will permanently delete ALL local data:\n\n"
            "  - Watched pairs\n"
            "  - Settings (refresh interval, threshold, etc.)\n"
            "  - Signal history\n\n"
            "This cannot be undone. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.timer.stop()
        self.db.reset_all()

        # Reload everything from the freshly-reset (empty/default) DB.
        self._load_symbols_into_table()
        self._load_history_into_table()

        if dialog is not None:
            dialog.auto_refresh_checkbox.blockSignals(True)
            dialog.auto_refresh_checkbox.setChecked(self.db.get_setting("auto_refresh_enabled", "1") == "1")
            dialog.auto_refresh_checkbox.blockSignals(False)

            dialog.interval_spin.blockSignals(True)
            dialog.interval_spin.setValue(int(self.db.get_setting("refresh_interval_minutes", "5")))
            dialog.interval_spin.blockSignals(False)

            dialog.threshold_spin.blockSignals(True)
            dialog.threshold_spin.setValue(int(self.db.get_setting("threshold_pct", "50")))
            dialog.threshold_spin.blockSignals(False)

            dialog.timeframe_combo.blockSignals(True)
            dialog.timeframe_combo.setCurrentText(self.db.get_setting("timeframe", "D1"))
            dialog.timeframe_combo.blockSignals(False)

        self.status_label.setText("App reset. Not connected to MT5.")
        self.status_label.setStyleSheet("color: #9aa1ac;")
        self._apply_timer_state()

        QMessageBox.information(dialog or self, "Reset Complete", "All local data has been cleared.")

    # ---------------------------------------------------------- Connection
    def _attempt_connect(self):
        if self._connect_thread is not None and self._connect_thread.isRunning():
            return
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        self.connect_message_label.setText("Attempting to connect to MetaTrader 5...")
        self.connect_message_label.setStyleSheet("color: #4c8bf5; padding: 0 60px;")

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
        self.status_label.setStyleSheet("color: #3ddc84;")
        self.refresh_signals()

    def _on_connect_failed(self, message: str):
        self.connect_message_label.setText(message)
        self.connect_message_label.setStyleSheet("color: #ff6b6b; padding: 0 60px;")
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
        self.status_label.setStyleSheet("color: #4c8bf5;")

        self._thread = QThread(self)
        threshold_fraction = int(self.db.get_setting("threshold_pct", "50")) / 100.0
        timeframe = self.db.get_setting("timeframe", "D1")
        self._worker = RefreshWorker(
            self.connector, symbols,
            threshold_pct=threshold_fraction, timeframe=timeframe,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_refresh_progress)
        self._worker.finished.connect(self._on_refresh_finished)
        self._worker.failed.connect(self._on_refresh_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_refresh_progress(self, done: int, total: int, symbol: str):
        if done >= total:
            self.status_label.setText(f"Processing {total} results...")
        else:
            self.status_label.setText(f"Fetching {symbol} ({done + 1}/{total})...")
        self.status_label.setStyleSheet("color: #4c8bf5;")

    def _cleanup_thread(self):
        self.refresh_btn.setEnabled(True)
        self._thread = None
        self._worker = None

    def _on_refresh_failed(self, message: str):
        self.status_label.setText(f"MT5 error: {message}")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        # Connection was likely lost - send the user back to the connect page.
        self.connector.connected = False
        self._on_connect_failed(message)

    def _on_refresh_finished(self, results):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.setText(f"Connected. Last updated: {now_str}")
        self.status_label.setStyleSheet("color: #3ddc84;")

        for result in results:
            card = self.signal_cards.get(result.symbol)
            if card is None:
                continue
            card.update_result(result, now_str)

            if result.signal in ("BUY", "SELL"):
                c2_iso = result.c2.time.isoformat() if result.c2 else None
                if not self.db.already_logged(result.symbol, result.signal, c2_iso):
                    self.db.log_signal(result)

        self._resort_signal_cards()
        self._load_history_into_table()

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
                if col == 6:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                self.history_table.setItem(row_idx, col, item)
            self.history_table.resizeRowToContents(row_idx)

    def closeEvent(self, event):
        self.timer.stop()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        self.connector.shutdown()
        super().closeEvent(event)
