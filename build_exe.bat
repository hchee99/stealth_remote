@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 was not found. Install Python and try again.
    if not defined CI pause
    exit /b 1
)

echo [1/3] Installing build dependencies...
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed

echo [2/3] Building StealthPlayer...
python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --name StealthPlayer ^
    --hidden-import PyQt5.QtWebEngineWidgets ^
    --hidden-import PyQt5.QtWebEngine ^
    claude_stealth.py
if errorlevel 1 goto :failed

echo [3/3] Creating the portable ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\StealthPlayer\*' -DestinationPath 'dist\StealthPlayer-windows-x64.zip' -Force"
if errorlevel 1 goto :failed

echo.
echo EXE: dist\StealthPlayer\StealthPlayer.exe
echo ZIP: dist\StealthPlayer-windows-x64.zip
exit /b 0

:failed
echo.
echo [ERROR] Build failed.
if not defined CI pause
exit /b 1
