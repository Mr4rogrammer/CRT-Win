@echo off
REM Builds CRT_Signal_Scanner.exe on Windows using PyInstaller.
REM Run this ON WINDOWS after copying the project folder there.

echo Installing dependencies...
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo Building CRT_Signal_Scanner.exe ...
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name CRT_Signal_Scanner ^
    --clean ^
    --collect-all MetaTrader5 ^
    --collect-all numpy ^
    main.py

echo.
echo Done. Find your app at: dist\CRT_Signal_Scanner.exe
pause
