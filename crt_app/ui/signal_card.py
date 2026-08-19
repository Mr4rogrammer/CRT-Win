"""A single collapsible "card" row for the Live Signals list.

Collapsed: shows Symbol, Signal badge, a one-line reason preview, and a
Remove button - compact so many pairs fit on screen at once.
Expanded (via the toggle arrow): reveals Entry / Stop-loss / Take-profit /
R:R / full reason / last-update details underneath.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QSizePolicy,
)

SIGNAL_COLORS = {
    "BUY": "#3ddc84",
    "SELL": "#ff6b6b",
    "NO TRADE": "#9aa1ac",
    "ERROR": "#f0ad4e",
    "": "#9aa1ac",
}

# Sort priority: BUY first, then SELL, then NO TRADE, then ERROR/unknown last.
SIGNAL_SORT_PRIORITY = {"BUY": 0, "SELL": 1, "NO TRADE": 2, "ERROR": 3, "": 4}


def _elide(text: str, max_len: int = 90) -> str:
    text = text or ""
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


class SignalCard(QFrame):
    """One expandable/collapsible row representing a single watched symbol."""

    remove_clicked = Signal(str)  # emits the symbol

    def __init__(self, symbol: str, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.signal = ""
        self._expanded = False
        self.setObjectName("signalCard")
        self.setFrameShape(QFrame.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---------- Header (always visible, collapsed summary) ----------
        header = QWidget()
        header.setObjectName("signalCardHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(10)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("\u25B8")  # ▸ collapsed
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFixedWidth(26)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setToolTip("Expand for Entry/SL/TP/R:R details")
        self.toggle_btn.clicked.connect(self._on_toggle)
        header_layout.addWidget(self.toggle_btn)

        self.symbol_label = QLabel(symbol)
        self.symbol_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        self.symbol_label.setFixedWidth(90)
        header_layout.addWidget(self.symbol_label)

        self.signal_badge = QLabel("\u2013")  # –
        self.signal_badge.setAlignment(Qt.AlignCenter)
        self.signal_badge.setFixedWidth(90)
        self.signal_badge.setFixedHeight(24)
        self._style_badge("")
        header_layout.addWidget(self.signal_badge)

        self.reason_preview = QLabel("Not yet evaluated.")
        self.reason_preview.setStyleSheet("color: #9aa1ac;")
        self.reason_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header_layout.addWidget(self.reason_preview, 1)

        self.last_update_label = QLabel("")
        self.last_update_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.last_update_label.setFixedWidth(130)
        self.last_update_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(self.last_update_label)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("dangerButton")
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.symbol))
        header_layout.addWidget(self.remove_btn)

        outer.addWidget(header)

        # ---------- Detail panel (hidden until expanded) ----------
        self.detail = QWidget()
        self.detail.setObjectName("signalCardDetail")
        grid = QGridLayout(self.detail)
        grid.setContentsMargins(48, 4, 16, 12)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(4)

        def make_field(row, col, label_text):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
            val = QLabel("-")
            val.setStyleSheet("font-size: 13px;")
            grid.addWidget(lbl, row, col)
            grid.addWidget(val, row + 1, col)
            return val

        self.entry_value = make_field(0, 0, "Entry")
        self.sl_value = make_field(0, 1, "Stop Loss")
        self.tp_value = make_field(0, 2, "Take Profit")
        self.rr_value = make_field(0, 3, "R:R")

        reason_lbl = QLabel("Reason")
        reason_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
        grid.addWidget(reason_lbl, 2, 0, 1, 4)
        self.reason_full = QLabel("")
        self.reason_full.setWordWrap(True)
        self.reason_full.setStyleSheet("font-size: 13px;")
        grid.addWidget(self.reason_full, 3, 0, 1, 4)

        self.detail.setVisible(False)
        outer.addWidget(self.detail)

    def _style_badge(self, signal: str):
        color = SIGNAL_COLORS.get(signal, "#9aa1ac")
        self.signal_badge.setStyleSheet(
            f"color: {color}; font-weight: 700; padding: 2px 6px;"
        )

    def _on_toggle(self):
        self._expanded = self.toggle_btn.isChecked()
        self.toggle_btn.setText("\u25BE" if self._expanded else "\u25B8")  # ▾ / ▸
        self.detail.setVisible(self._expanded)

    def set_expanded(self, expanded: bool):
        self.toggle_btn.setChecked(expanded)
        self._on_toggle()

    def update_result(self, result, now_str: str):
        """Refresh the card's displayed data from a SignalResult."""
        self.signal = result.signal or ""
        self.signal_badge.setText(self.signal or "-")
        self._style_badge(self.signal)

        self.reason_preview.setText(_elide(result.reason or ""))
        self.reason_full.setText(result.reason or "")

        self.entry_value.setText(f"{result.entry:.5f}" if result.entry is not None else "-")
        self.sl_value.setText(f"{result.stop_loss:.5f}" if result.stop_loss is not None else "-")
        self.tp_value.setText(f"{result.take_profit:.5f}" if result.take_profit is not None else "-")
        self.rr_value.setText(f"{result.risk_reward:.2f}" if result.risk_reward else "-")

        self.last_update_label.setText(now_str)

    def sort_key(self):
        return (SIGNAL_SORT_PRIORITY.get(self.signal, 4), self.symbol)
