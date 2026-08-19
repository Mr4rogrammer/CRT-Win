@echo off
REM Double-click this file to run the CRT Signal Scanner directly from
REM source (no .exe build needed). Requires Python + dependencies already
REM installed (pip install -r requirements.txt).
REM
REM This keeps a console window open, so if the app fails to start you'll
REM see the actual Python error message instead of it silently doing nothing.

cd /d "%~dp0"
python main.py
pause
