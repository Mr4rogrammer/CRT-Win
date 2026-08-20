@echo off
REM Debug build: same as build_exe.bat but WITHOUT --windowed, so a console
REM window stays open and shows any error/traceback if the app fails to
REM start. Use this to diagnose "double-click does nothing" issues.
REM
REM Run this ON WINDOWS. After it finishes, run the exe from a Command
REM Prompt (not double-click) so you can read the output, e.g.:
REM   cd dist
REM   CRT_Signal_Scanner_debug.exe

echo Installing dependencies...
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo Building CRT_Signal_Scanner_debug.exe (console enabled) ...
python -m PyInstaller --noconfirm --onefile ^
    --name CRT_Signal_Scanner_debug ^
    --clean ^
    --collect-all MetaTrader5 ^
    --collect-all numpy ^
    main.py

echo.
echo Done. Now run it from a terminal to see errors:
echo   cd dist
echo   CRT_Signal_Scanner_debug.exe
pause
