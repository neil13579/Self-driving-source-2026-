@echo off
REM ========================================
REM CARLA Visualization - Main Quick Start
REM ========================================

cd /d "%~dp0"

echo.
echo ========================================
echo  CARLA Visualization System
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found or not in PATH!
    pause
    exit /b 1
)

echo  Checking system...
echo.

REM Run diagnostic
python diagnostic_viz.py

echo.
echo ========================================
echo Select what to start:
echo ========================================
echo  1 = Start Perception Server (main.py)
echo  2 = Start HTTP Web Server (serve_web.py)  
echo  3 = Start BOTH servers (recommended)
echo  4 = Exit
echo.

set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo Starting Perception Server...
    start "CARLA Perception" cmd /k python main.py
    goto done
)

if "%choice%"=="2" (
    echo.
    echo Starting HTTP Server...
    start "CARLA Web Server" cmd /k python serve_web.py
    goto done
)

if "%choice%"=="3" (
    echo.
    echo Starting both servers...
    start "CARLA Perception" cmd /k python main.py
    timeout /t 2 /nobreak >nul
    start "CARLA Web Server" cmd /k python serve_web.py
    echo.
    echo Both servers started!
    echo.
    echo Open browser: http://localhost:8000/index.html
    echo.
    pause
    goto done
)

if "%choice%"=="4" (
    goto done
)

echo Invalid choice!

:done
exit /b 0
