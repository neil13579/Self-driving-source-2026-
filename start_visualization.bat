@echo off
REM CARLA SEAL Unified Visualization - Quick Start Script for Windows
REM This script will:
REM 1. Check for Python
REM 2. Install/verify required packages
REM 3. Start the visualization server

echo.
echo ========================================
echo CARLA SEAL Unified Visualization
echo Quick Start Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [+] Python found
python --version

echo.
echo [*] Checking/Installing required packages...
echo.

REM Install required packages
echo [*] Installing Flask...
pip install flask --quiet
if errorlevel 1 (
    echo [-] Error installing Flask
    pause
    exit /b 1
)
echo [+] Flask installed

echo [*] Installing Flask-CORS...
pip install flask-cors --quiet
if errorlevel 1 (
    echo [-] Error installing Flask-CORS
    pause
    exit /b 1
)
echo [+] Flask-CORS installed

echo.
echo [+] All dependencies installed successfully!
echo.

REM Check if visualization files exist
if not exist "unified_visualization.html" (
    echo ERROR: unified_visualization.html not found!
    echo Please make sure all files are in the current directory
    pause
    exit /b 1
)

if not exist "unified_server_simple.py" (
    echo ERROR: unified_server_simple.py not found!
    echo Please make sure all files are in the current directory
    pause
    exit /b 1
)

echo [+] Visualization files found
echo.
echo ========================================
echo Starting CARLA SEAL Visualization Server
echo ========================================
echo.
echo Opening on: http://localhost:5000
echo.
echo Controls:
echo  - Left Click + Drag: Rotate
echo  - Right Click + Drag: Pan  
echo  - Scroll: Zoom
echo  - R: Reset View
echo  - L: Toggle LiDAR
echo  - D: Toggle RADAR
echo  - B: Toggle BBox
echo  - S: Toggle Segmentation
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python unified_server_simple.py

pause
