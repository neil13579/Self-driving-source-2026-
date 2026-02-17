@echo off
REM ========================================
REM CARLA Foxglove Quick Start
REM ========================================

cd /d "%~dp0"

echo.
echo ========================================
echo  CARLA Foxglove Visualization
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found or not in PATH!
    pause
    exit /b 1
)

REM Check CARLA
echo Checking CARLA...
python -c "import socket; s = socket.socket(); s.connect(('localhost', 2000)); print('  ✓ CARLA is running')" >nul 2>&1

if errorlevel 1 (
    echo.
    echo ⚠️  WARNING: CARLA is NOT running!
    echo Please start CARLA first:
    echo   CarlaUE4.exe -windowed -carla-port=2000
    echo.
    pause
)

echo.
echo Starting Foxglove server...
echo.

REM Start the server in a new window
start "CARLA Foxglove Server" cmd /k python foxglove_server.py

REM Give it time to start
timeout /t 3 /nobreak >nul

echo.
echo Starting HTTP server and opening browser...
echo.

REM Start HTTP server (this one opens browser too)
python start_foxglove.py

echo.
echo Done!
