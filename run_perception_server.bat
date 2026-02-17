@echo off
REM Run the perception server with colored diagnostic output
REM This is the main way to start the system

echo.
echo ================================================
echo   CARLA Perception Server with Diagnostics
echo ================================================
echo.
echo Starting server with color-coded console output...
echo.
echo Color Guide:
echo   BLUE       = [INIT-X] initialization stages
echo   CYAN       = [CHECKPOINT] actor spawning
echo   GREEN      = Frame processing [PROC/FRAME/ENCODE]
echo   BRIGHT GRN = WebSocket messages [BROADCAST/MESSAGE]
echo   MAGENTA    = WebSocket events [WS-]
echo   YELLOW     = Flask endpoints [FLASK-]
echo   RED BG     = ERROR messages
echo.
echo Once [INIT-16] appears, open: http://localhost:5000
echo.
echo Press Ctrl+C to stop server
echo.

python monitor_server.py

echo.
echo Server stopped. Press any key to close...
pause
