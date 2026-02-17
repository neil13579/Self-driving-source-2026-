#!/bin/bash

# CARLA SEAL Unified Visualization - Quick Start Script for Linux/Mac
# This script will:
# 1. Check for Python
# 2. Install/verify required packages
# 3. Start the visualization server

echo ""
echo "========================================"
echo "CARLA SEAL Unified Visualization"
echo "Quick Start Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7+ using:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

echo "[+] Python found"
python3 --version

echo ""
echo "[*] Checking/Installing required packages..."
echo ""

# Install required packages
echo "[*] Installing Flask..."
pip3 install flask --quiet
if [ $? -ne 0 ]; then
    echo "[-] Error installing Flask"
    exit 1
fi
echo "[+] Flask installed"

echo "[*] Installing Flask-CORS..."
pip3 install flask-cors --quiet
if [ $? -ne 0 ]; then
    echo "[-] Error installing Flask-CORS"
    exit 1
fi
echo "[+] Flask-CORS installed"

echo ""
echo "[+] All dependencies installed successfully!"
echo ""

# Check if visualization files exist
if [ ! -f "unified_visualization.html" ]; then
    echo "ERROR: unified_visualization.html not found!"
    echo "Please make sure all files are in the current directory"
    exit 1
fi

if [ ! -f "unified_server_simple.py" ]; then
    echo "ERROR: unified_server_simple.py not found!"
    echo "Please make sure all files are in the current directory"
    exit 1
fi

echo "[+] Visualization files found"
echo ""
echo "========================================"
echo "Starting CARLA SEAL Visualization Server"
echo "========================================"
echo ""
echo "Opening on: http://localhost:5000"
echo ""
echo "Controls:"
echo "  - Left Click + Drag: Rotate"
echo "  - Right Click + Drag: Pan"
echo "  - Scroll: Zoom"
echo "  - R: Reset View"
echo "  - L: Toggle LiDAR"
echo "  - D: Toggle RADAR"
echo "  - B: Toggle BBox"
echo "  - S: Toggle Segmentation"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python3 unified_server_simple.py
