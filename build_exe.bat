@echo off
REM Builds CRT_Signal_Scanner.exe on Windows using PyInstaller.
REM Run this ON WINDOWS after copying the project folder there.

echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Building CRT_Signal_Scanner.exe ...
pyinstaller --noconfirm --onefile --windowed ^
    --name CRT_Signal_Scanner ^
    --collect-all MetaTrader5 ^
    main.py

echo.
echo Done. Find your app at: dist\CRT_Signal_Scanner.exe
pause
