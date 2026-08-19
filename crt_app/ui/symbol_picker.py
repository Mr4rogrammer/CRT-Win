"""Dialog for browsing all symbols available in the connected MT5 terminal
and picking which ones to add to (or remove from) the watch list."""
from typing import List, Set

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QDialogButtonBox,
)


class SymbolPickerDialog(QDialog):
    """Shows every symbol the broker offers with a checkbox next to each one.
    Symbols already in the watch list start checked. Type in the search box
    to filter (e.g. "USD", "XAU", "GBP")."""

    def __init__(self, all_symbols: List[str], current_pairs: Set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browse & Select Pairs")
        self.resize(420, 560)
        self._all_symbols = sorted(all_symbols)
        self._current_pairs = set(current_pairs)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"{len(self._all_symbols)} symbols available from your broker."))

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter (e.g. USD, XAU, GBP)...")
        self.search_box.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_box)

        quick_row = QHBoxLayout()
        select_all_btn = QPushButton("Check All Visible")
        select_all_btn.clicked.connect(lambda: self._set_all_visible_checked(True))
        clear_btn = QPushButton("Uncheck All Visible")
        clear_btn.clicked.connect(lambda: self._set_all_visible_checked(False))
        quick_row.addWidget(select_all_btn)
        quick_row.addWidget(clear_btn)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self._populate_list()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_list(self):
        self.list_widget.clear()
        for symbol in self._all_symbols:
            item = QListWidgetItem(symbol)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if symbol in self._current_pairs else Qt.Unchecked)
            self.list_widget.addItem(item)

    def _apply_filter(self, text: str):
        text = text.strip().upper()
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item.setHidden(text not in item.text().upper())

    def _set_all_visible_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if not item.isHidden():
                item.setCheckState(state)

    def selected_symbols(self) -> Set[str]:
        """Returns the set of symbols that ended up checked when OK was pressed."""
        selected = set()
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item.checkState() == Qt.Checked:
                selected.add(item.text())
        return selected
