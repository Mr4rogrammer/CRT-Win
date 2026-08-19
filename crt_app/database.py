"""SQLite persistence layer: watched pairs, settings, and signal history."""
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import SignalResult

DB_DIR = Path.home() / ".crt_app"
DB_PATH = DB_DIR / "crt_app.db"

DEFAULT_SETTINGS = {
    "refresh_interval_minutes": "5",
    "auto_refresh_enabled": "1",
}


class Database:
    """Thin wrapper around sqlite3 for the CRT app's local storage."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    added_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    reason TEXT,
                    entry REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    risk_reward REAL,
                    c1_time TEXT,
                    c1_high REAL,
                    c1_low REAL,
                    c2_time TEXT,
                    c2_high REAL,
                    c2_low REAL,
                    c2_close REAL,
                    evaluated_at TEXT NOT NULL
                )
                """
            )
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

    # ---------- Settings ----------
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    # ---------- Watched pairs ----------
    def get_pairs(self) -> List[str]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT symbol FROM pairs ORDER BY added_at").fetchall()
            return [r["symbol"] for r in rows]

    def add_pair(self, symbol: str) -> bool:
        symbol = symbol.strip().upper()
        if not symbol:
            return False
        with closing(self._connect()) as conn, conn:
            try:
                conn.execute(
                    "INSERT INTO pairs (symbol, added_at) VALUES (?, ?)",
                    (symbol, datetime.now().isoformat(timespec="seconds")),
                )
                return True
            except sqlite3.IntegrityError:
                return False  # already exists

    def remove_pair(self, symbol: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM pairs WHERE symbol = ?", (symbol.strip().upper(),))

    # ---------- Signal history ----------
    def log_signal(self, result: SignalResult) -> None:
        c1, c2 = result.c1, result.c2
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO signal_history (
                    symbol, signal, reason, entry, stop_loss, take_profit, risk_reward,
                    c1_time, c1_high, c1_low, c2_time, c2_high, c2_low, c2_close, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.symbol,
                    result.signal,
                    result.reason,
                    result.entry,
                    result.stop_loss,
                    result.take_profit,
                    result.risk_reward,
                    c1.time.isoformat() if c1 else None,
                    c1.high if c1 else None,
                    c1.low if c1 else None,
                    c2.time.isoformat() if c2 else None,
                    c2.high if c2 else None,
                    c2.low if c2 else None,
                    c2.close if c2 else None,
                    (result.evaluated_at or datetime.now()).isoformat(timespec="seconds"),
                ),
            )

    def already_logged(self, symbol: str, signal: str, c2_time_iso: Optional[str]) -> bool:
        """Avoid re-logging the same setup on every auto-refresh poll."""
        if not c2_time_iso:
            return False
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT 1 FROM signal_history WHERE symbol=? AND signal=? AND c2_time=? LIMIT 1",
                (symbol.strip().upper(), signal, c2_time_iso),
            ).fetchone()
            return row is not None

    def get_history(self, symbol: Optional[str] = None, limit: int = 200) -> List[sqlite3.Row]:
        with closing(self._connect()) as conn:
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM signal_history WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                    (symbol.strip().upper(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM signal_history ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            return rows
