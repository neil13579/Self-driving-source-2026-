@echo off
REM Run component verification tool
REM This checks if everything is installed and configured correctly

echo.
echo ================================================
echo   CARLA Perception System - Component Check
echo ================================================
echo.
echo Checking Python packages, CARLA connection, ports, and files...
echo.

python verify_components.py

echo.
pause
