"""Entry point for the CRT Signal Scanner desktop app.

Run with:  python main.py
Requires: PySide6, and on Windows: MetaTrader5 + a running/logged-in MT5 terminal.
"""
import sys

from PySide6.QtWidgets import QApplication

from crt_app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CRT Signal Scanner")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
