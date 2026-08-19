# CRT Signal Scanner

A Windows desktop app that connects to a locally running **MetaTrader 5**
terminal, pulls **daily candles**, applies the **CRT (Candle Range Theory)**
price-action reversal strategy, and shows you a clear BUY / SELL / NO TRADE
signal per symbol in a PySide6 GUI. Trades are **not** auto-placed — the app
only displays the signal for you to act on manually.

## Strategy: CRT (Candle Range Theory)

- **C1** — reference candle (2 daily candles ago). Defines the range
  `[C1.low, C1.high]` and its 50% midpoint.
- **C2** — the last completed daily candle. Must sweep exactly one side of
  C1's range and then close back past the **50% midpoint** of C1 (not just
  back inside the range — a stronger rejection):
  - Bearish (`SELL`): `C2.high > C1.high`, `C2.low >= C1.low`, and
    `C2.close < midpoint(C1)`.
  - Bullish (`BUY`): `C2.low < C1.low`, `C2.high <= C1.high`, and
    `C2.close > midpoint(C1)`.
  - Both sides swept, or close doesn't cross the midpoint back → `NO TRADE`.
- **C3** — today's live/forming candle — the entry candle. Entry = C3's
  opening price (stable, not a fluctuating live tick), stop-loss = just
  beyond C2's sweep wick, take-profit = the opposite side of C1's range.
  If price has already moved past the stop-loss or take-profit by the time
  the app checks (setup is stale), it reports `NO TRADE` instead of a signal.

See `crt_app/strategy.py` for the full implementation and `tests/test_strategy.py`
for the objective rule set validated with unit tests.

## Requirements

- **Windows** with **MetaTrader 5** terminal installed and **logged in** to
  your broker account (the app connects to the terminal already running
  locally — it does not need your login credentials).
- Python 3.10+

## Setup (on Windows)

```powershell
pip install -r requirements.txt
python main.py
```

## Building a standalone .exe (on Windows)

PyInstaller can only build for the OS it runs on, so you must run this step
**on Windows** (it cannot be produced from macOS/Linux):

```powershell
build_exe.bat
```

This installs dependencies + PyInstaller and produces a single-file
`dist\CRT_Signal_Scanner.exe` you can double-click to launch the app —
no need to keep Python installed separately after that (MT5 terminal still
required, of course).

## Using the app

1. Add currency pairs/symbols you want to scan (exact MT5 symbol name, e.g.
   `EURUSD`, `XAUUSD`) using the "Add Pair" box. Pairs persist in a local
   SQLite database (`~/.crt_app/crt_app.db`).
2. Click **Refresh Now**, or enable **Auto-refresh** with an interval
   (minutes) to periodically re-check MT5 for new signals.
3. The **Live Signals** tab shows the current signal, entry, stop-loss,
   take-profit, risk:reward, and reason for each symbol.
4. The **Signal History** tab logs every BUY/SELL signal that was generated
   (deduplicated per day) so you can review past setups.

## Project layout

```
main.py                     Entry point
crt_app/
  models.py                 Candle / SignalResult dataclasses
  strategy.py                CRT rule evaluation (pure logic, unit-tested)
  mt5_connector.py            MetaTrader5 wrapper (Windows-only)
  engine.py                    Glue: fetch candles -> run strategy
  database.py                   SQLite: watched pairs, settings, signal history
  ui/main_window.py             PySide6 GUI
tests/test_strategy.py       Unit tests for the CRT rules (no MT5 needed)
```

## Notes

- The `MetaTrader5` pip package only works on Windows and requires the MT5
  terminal to be installed and running locally. On other platforms the app
  still runs (UI, strategy, storage) but will report MT5 as unavailable.
- No orders are ever placed automatically — this app is a signal scanner only.
