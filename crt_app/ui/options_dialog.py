"""'More Options' panel: auto-refresh interval, timeframe, reject threshold,
and the destructive Reset App action - moved out of the main toolbar to keep
it clean and focused on Symbol/Add/Refresh.

Implemented as a QDockWidget fixed to the right edge of the main window (not
a floating top-level dialog) so it stays docked in place, resizes with the
window, and can't be dragged/floated away."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
)


class OptionsDialog(QDockWidget):
    """Houses all secondary settings: auto-refresh toggle/interval, candle
    timeframe, reject threshold %, and the Reset App button. The main window
    owns the actual widgets/state; this panel just presents them together
    and wires the same callbacks the toolbar used to use directly."""

    def __init__(
        self,
        auto_refresh_checked: bool,
        interval_minutes: int,
        threshold_pct: int,
        timeframe: str,
        timeframe_choices,
        parent=None,
    ):
        super().__init__("More Options", parent)
        self.setObjectName("optionsDock")
        # Fixed to the right side: no floating, no closing via drag, no moving.
        self.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)

        container = QWidget()
        container.setObjectName("optionsDockContent")
        layout = QVBoxLayout(container)

        form = QFormLayout()
        form.setSpacing(10)

        self.auto_refresh_checkbox = QCheckBox("Enabled")
        self.auto_refresh_checkbox.setChecked(auto_refresh_checked)
        form.addRow("Auto-refresh:", self.auto_refresh_checkbox)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(interval_minutes)
        self.interval_spin.setSuffix(" min")
        form.addRow("Refresh every:", self.interval_spin)

        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(list(timeframe_choices))
        if timeframe in timeframe_choices:
            self.timeframe_combo.setCurrentText(timeframe)
        self.timeframe_combo.setToolTip(
            "Candle timeframe used for C1/C2/C3 (e.g. D1 = daily, H4 = 4-hour, H1 = 1-hour)."
        )
        form.addRow("Timeframe:", self.timeframe_combo)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 99)
        self.threshold_spin.setValue(threshold_pct)
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.setToolTip(
            "How far into C1's range (from the swept side) C2 must stay compressed. "
            "50% = midpoint. Lower = stricter, higher = more lenient."
        )
        form.addRow("Reject Threshold:", self.threshold_spin)

        layout.addLayout(form)

        layout.addSpacing(12)
        danger_row = QHBoxLayout()
        self.reset_app_btn = QPushButton("Reset App")
        self.reset_app_btn.setObjectName("dangerButton")
        self.reset_app_btn.setToolTip(
            "Deletes ALL local data: watched pairs, settings, and signal history. Cannot be undone."
        )
        danger_row.addWidget(self.reset_app_btn)
        danger_row.addStretch()
        layout.addLayout(danger_row)

        layout.addSpacing(12)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        buttons.button(QDialogButtonBox.Close).setText("Hide")
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.close)
        layout.addWidget(buttons)

        layout.addStretch()

        self.setWidget(container)
        self.setMinimumWidth(300)
        self.setMaximumWidth(420)
