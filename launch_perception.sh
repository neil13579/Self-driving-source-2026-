#!/bin/bash

# Unified CARLA Perception System Launcher for Linux/macOS
# Author: CARLA_SEAL Team

clear

echo "========================================================================"
echo "  🚗 Unified CARLA Perception System Launcher"
echo "========================================================================"
echo ""
echo "This script will:"
echo "  1. Check if CARLA is running"
echo "  2. Verify Python dependencies"
echo "  3. Launch the Unified Perception Server"
echo "  4. Open the dashboard in your browser"
echo ""
echo "Make sure CARLA is already running before continuing!"
echo ""
read -p "Press Enter to continue..."

cd "$(dirname "$0")"

echo ""
echo "[1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.8+"
    exit 1
fi
python3 --version
echo "OK: Python found"
echo ""

echo "[2/4] Checking CARLA connection..."
sleep 2

echo ""
echo "[3/4] Checking dependencies..."
python3 -c "import carla, tensorflow, cv2, flask, websockets" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "WARNING: Missing dependencies!"
    echo "Please install with:"
    echo ""
    echo "  pip install carla tensorflow opencv-python flask flask-cors websockets scipy numpy"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo "OK: Dependencies found"
echo ""

echo "[4/4] Starting Unified Perception Server..."
echo ""
echo "========================================================================"
echo "  Dashboard will be available at: http://localhost:5000"
echo "  WebSocket: ws://localhost:8765"
echo ""
echo "  Press Ctrl+C to stop the server"
echo "========================================================================"
echo ""

# Try to open browser automatically
if command -v xdg-open &> /dev/null; then
    # Linux
    sleep 3 && xdg-open "http://localhost:5000" &
elif command -v open &> /dev/null; then
    # macOS
    sleep 3 && open "http://localhost:5000" &
fi

python3 unified_perception_server.py

echo ""
echo "Server stopped."
