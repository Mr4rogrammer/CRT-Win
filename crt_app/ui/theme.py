"""Modern flat dark theme (QSS) for the CRT Signal Scanner app."""

MODERN_DARK_QSS = """
* {
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog, QWidget {
    background-color: #1e2229;
    color: #e6e6e6;
}

QLabel {
    color: #c9ced6;
    background: transparent;
}

QLineEdit, QSpinBox {
    background-color: #2a2f3a;
    border: 1px solid #3a4150;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f0f0f0;
    selection-background-color: #4c8bf5;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #4c8bf5;
}

QPushButton {
    background-color: #3a4150;
    color: #f0f0f0;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #4a5265;
}
QPushButton:pressed {
    background-color: #2f3542;
}
QPushButton:disabled {
    background-color: #2a2e36;
    color: #6b7280;
}

QPushButton#primaryButton, QPushButton#connectButton {
    background-color: #4c8bf5;
    color: #ffffff;
}
QPushButton#primaryButton:hover, QPushButton#connectButton:hover {
    background-color: #3d7ce0;
}
QPushButton#primaryButton:pressed, QPushButton#connectButton:pressed {
    background-color: #2f68c9;
}

QPushButton#dangerButton {
    background-color: #3a4150;
    color: #f28b82;
}
QPushButton#dangerButton:hover {
    background-color: #c0392b;
    color: #ffffff;
}

QCheckBox {
    color: #c9ced6;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4a5265;
    background: #2a2f3a;
}
QCheckBox::indicator:checked {
    background-color: #4c8bf5;
    border: 1px solid #4c8bf5;
}

QTabWidget::pane {
    border: 1px solid #2f3542;
    border-radius: 8px;
    top: -1px;
    background: #20252c;
}
QTabBar::tab {
    background: transparent;
    color: #9aa1ac;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #20252c;
    color: #ffffff;
    font-weight: 600;
    border-bottom: 2px solid #4c8bf5;
}
QTabBar::tab:hover:!selected {
    color: #d0d4da;
}

QTableWidget {
    background-color: #20252c;
    alternate-background-color: #242933;
    gridline-color: #2f3542;
    border: 1px solid #2f3542;
    border-radius: 8px;
    color: #e6e6e6;
    selection-background-color: #34415c;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 6px;
}
QHeaderView::section {
    background-color: #262b34;
    color: #9aa1ac;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #3a4150;
    font-weight: 600;
}
QTableCornerButton::section {
    background-color: #262b34;
    border: none;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background: #1e2229;
    border: none;
    width: 10px;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #3a4150;
    border-radius: 5px;
    min-height: 20px;
    min-width: 20px;
}
QScrollBar::handle:hover {
    background: #4a5265;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

QListWidget {
    background-color: #20252c;
    border: 1px solid #2f3542;
    border-radius: 8px;
    color: #e6e6e6;
    padding: 4px;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #2a2f3a;
}
QListWidget::item:selected {
    background-color: #34415c;
}

QMessageBox {
    background-color: #1e2229;
}

QToolTip {
    background-color: #2a2f3a;
    color: #f0f0f0;
    border: 1px solid #4a5265;
    padding: 4px 8px;
    border-radius: 4px;
}
"""
