@echo off
setlocal
cd /d "%~dp0"
title PUBG Control Launcher

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Chua tim thay moi truong ao .venv. Dang khoi tao...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Khong the tao moi truong Python. Vui long kiem tra Python tren he thong.
        pause
        exit /b 1
    )
    echo [INFO] Dang cai dat cac goi phu thuoc...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo [INFO] Dang khoi dong PUBG Control...
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Ung dung da dung lai voi loi.
    pause
    exit /b 1
)
endlocal
