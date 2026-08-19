@echo off
REM Launches MetaTrader 5 (if not already running) and then starts the
REM CRT Signal Scanner app. Use this instead of running the .exe directly
REM if you want MT5 to auto-start alongside it.
REM
REM SETUP (one-time):
REM   1. Edit MT5_PATH below to match your MT5 install location.
REM      Common default: "C:\Program Files\MetaTrader 5\terminal64.exe"
REM      To find yours: right-click your MT5 desktop/start-menu shortcut ->
REM      Properties -> copy the "Target" path.
REM   2. Edit APP_PATH below to point at CRT_Signal_Scanner.exe
REM      (the one built by build_exe.bat, usually in the "dist" folder).

set MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
set APP_PATH=%~dp0dist\CRT_Signal_Scanner.exe

echo Checking if MetaTrader 5 is already running...
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I "terminal64.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo MT5 is already running.
) else (
    echo Starting MetaTrader 5...
    start "" "%MT5_PATH%"
    REM Give MT5 a few seconds to fully load and log in before the app
    REM tries to connect to it.
    timeout /t 8 /nobreak >NUL
)

echo Starting CRT Signal Scanner...
start "" "%APP_PATH%"
