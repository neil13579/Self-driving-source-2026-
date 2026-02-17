@echo off
REM Unified CARLA Perception System Launcher for Windows
REM Author: CARLA_SEAL Team

echo.
echo ========================================================================
echo   ^| Unified CARLA Perception System Launcher
echo ========================================================================
echo.
echo This script will:
echo   1. Check if CARLA is running
echo   2. Verify Python dependencies
echo   3. Launch the Unified Perception Server
echo   4. Open the dashboard in your browser
echo.
echo Make sure CARLA is already running before continuing!
echo.
pause

cd /d "%~dp0"

echo.
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)
echo OK: Python found
echo.

echo [2/4] Checking CARLA connection...
timeout /t 2 /nobreak >nul

echo.
echo [3/4] Checking dependencies...
python -c "import carla, tensorflow, cv2, flask, websockets" >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Missing dependencies!
    echo Please install with:
    echo.
    echo   pip install carla tensorflow opencv-python flask flask-cors websockets scipy numpy
    echo.
    pause
)
echo OK: Dependencies found
echo.

echo [4/4] Starting Unified Perception Server...
echo.
echo ========================================================================
echo   Dashboard will be available at: http://localhost:5000
echo   WebSocket: ws://localhost:8765
echo.
echo Press Ctrl+C to stop the server
echo ========================================================================
echo.

python unified_perception_server.py

echo.
echo Server stopped.
pause
