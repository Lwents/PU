@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Chua co moi truong Python. Hay chay: python -m venv .venv
    pause
    exit /b 1
)
".venv\Scripts\python.exe" pu.py
if errorlevel 1 pause
