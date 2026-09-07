@echo off
setlocal
cd /d "%~dp0"
title PUBG Control (Chay An / Ep Xuong)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Chua tim thay moi truong ao .venv. Dang khoi tao...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo [INFO] Dang khoi dong PUBG Control o che do thu nho / ep xuong taskbar...
start "" /min ".venv\Scripts\python.exe" main.py --minimized
endlocal
