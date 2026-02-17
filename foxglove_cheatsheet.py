#!/usr/bin/env python3
"""
Quick Reference - CARLA Foxglove Integration Cheat Sheet
"""

CHEATSHEET = """
╔═══════════════════════════════════════════════════════════════╗
║        CARLA FOXGLOVE INTEGRATION - QUICK REFERENCE          ║
╚═══════════════════════════════════════════════════════════════╝

┌─ STARTUP ─────────────────────────────────────────────────────┐
│                                                              │
│  Windows (Easiest):                                         │
│  $ START_FOXGLOVE.bat                                       │
│                                                              │
│  Manual:                                                    │
│  T1: CarlaUE4.exe -windowed -carla-port=2000              │
│  T2: python foxglove_server.py                              │
│  T3: python start_foxglove.py                               │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ ACCESS POINTS ────────────────────────────────────────────────┐
│                                                              │
│  Local 3D Viewer: http://localhost:8001/foxglove_viewer.html │
│  Gateway Page:    http://localhost:8001/foxglove.html       │
│  Foxglove Web:    https://app.foxglove.dev/                │
│  WebSocket:       ws://localhost:8766                       │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ DATA TOPICS ──────────────────────────────────────────────────┐
│                                                              │
│  /camera/rgb        → RGB Camera (JPEG, 640x480, 20 Hz)    │
│  /lidar/points      → Point Cloud (3D XYZ, 20 Hz)          │
│  /radar/markers     → RADAR Detections (3D, 20 Hz)         │
│  /ego_pose          → Vehicle Pose (Position + Rotation)    │
│  /vehicles/markers  → All Visible Vehicles (20 Hz)         │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ LOCAL VIEWER CONTROLS ────────────────────────────────────────┐
│                                                              │
│  MOUSE:                                                     │
│    Left Click + Drag    → Rotate camera                    │
│    Right Click + Drag   → Pan camera                       │
│    Scroll Wheel         → Zoom in/out                      │
│    Space Bar            → Reset to default view            │
│                                                              │
│  KEYBOARD:                                                  │
│    V → Cycle view modes                                    │
│    C → Toggle camera feed                                  │
│    L → Toggle LIDAR points                                 │
│    R → Toggle RADAR markers                                │
│    G → Toggle grid                                         │
│                                                              │
│  VIEW MODES:                                               │
│    Orbit    → Free camera rotation (default)              │
│    Ego      → First-person from vehicle                   │
│    Top-Down → Bird's eye view                             │
│    Follow   → Camera follows vehicle from behind           │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ FOXGLOVE WEB SETUP ───────────────────────────────────────────┐
│                                                              │
│  1. Go to: https://app.foxglove.dev/                       │
│  2. Click: "Open Connection"                                │
│  3. Select: "WebSocket"                                     │
│  4. Enter: ws://localhost:8766                             │
│  5. Click: "Connect"                                        │
│                                                              │
│  Pro Tips:                                                  │
│    • Record sessions for playback                          │
│    • Create custom multi-panel layouts                     │
│    • Toggle data visibility with checkboxes                │
│    • Inspect raw message data                              │
│    • Use keyboard shortcut "?" for help                    │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ TROUBLESHOOTING ──────────────────────────────────────────────┐
│                                                              │
│  No visualization:                                          │
│    → Check CARLA running: CarlaUE4.exe -windowed           │
│    → Check server running: python foxglove_server.py       │
│    → Wait 2-3 seconds for sensors to start                 │
│    → Try zooming out (Scroll wheel)                        │
│                                                              │
│  Connection refused:                                        │
│    → Port 8766 in use? netstat -ano | findstr :8766       │
│    → Kill process: taskkill /PID <PID> /F                │
│    → Or change port in foxglove_server.py                  │
│                                                              │
│  LIDAR not visible:                                        │
│    → Check "☁️ LIDAR Points" checkbox                      │
│    → Zoom out more (scroll wheel)                          │
│    → Verify LIDAR spawned in console output               │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ FILE STRUCTURE ───────────────────────────────────────────────┐
│                                                              │
│  foxglove_server.py          Main WebSocket server          │
│  foxglove.html               Gateway/menu page              │
│  foxglove_viewer.html        3D viewer (Three.js)          │
│  start_foxglove.py           HTTP server helper             │
│  START_FOXGLOVE.bat          Windows batch launcher         │
│  FOXGLOVE_GUIDE.md           Complete documentation        │
│  FOXGLOVE_SETUP_SUMMARY.md   Setup guide                   │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ COMMON TASKS ────────────────────────────────────────────────┐
│                                                              │
│  View only LIDAR:                                           │
│    → Uncheck camera, radar in Local Viewer                  │
│                                                              │
│  Record data:                                               │
│    → Use Foxglove Web → Click record button                 │
│    → File is MCAP format (universal robotics format)        │
│                                                              │
│  Switch view:                                               │
│    → Select from "View Mode" dropdown                       │
│                                                              │
│  Change update rate:                                        │
│    → Edit foxglove_server.py: sleep(0.05) → sleep(0.033)    │
│                                                              │
│  Reduce point cloud:                                        │
│    → In LIDAR callback: points[::2] to skip every 2nd       │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ PERFORMANCE ───────────────────────────────────────────────────┐
│                                                              │
│  Current Settings:                                          │
│    • Update rate: 20 Hz                                    │
│    • Point cloud: ~50,000 points/frame                     │
│    • Camera: 640x480 JPEG                                  │
│                                                              │
│  Optimization:                                              │
│    • Lower update rate: increase sleep(0.05)                │
│    • Reduce point density: downsample in callback           │
│    • Lower camera resolution in CARLA                       │
│    • Disable features (camera, radar) when not needed       │
│                                                              │
│  Better Quality:                                            │
│    • Increase point resolution in LIDAR                    │
│    • Use higher camera resolution                          │
│    • Reduce sleep time (20 Hz → 30 Hz)                     │
│    • Enable depth camera processing                        │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ ONE-LINER COMMANDS ──────────────────────────────────────────┐
│                                                              │
│  Start everything:              START_FOXGLOVE.bat          │
│  Just server:                   python foxglove_server.py   │
│  Just HTTP:                     python start_foxglove.py    │
│  Check CARLA:                   CarlaUE4.exe -windowed      │
│  Kill port 8766:                netstat -ano | findstr 8766 │
│  View Python version:            python --version            │
│  Test WebSocket:                 wscat -c ws://localhost:87... │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ KEYBOARD SHORTCUTS (Local Viewer) ────────────────────────────┐
│                                                              │
│  Space      → Reset camera to default                      │
│  C          → Toggle camera feed visibility                │
│  L          → Toggle LIDAR points visibility               │
│  R          → Toggle RADAR markers visibility              │
│  V          → Toggle vehicle markers visibility            │
│  G          → Toggle grid visibility                       │
│  Mouse      → Orbit/Pan/Zoom (see Controls section)       │
│                                                              │
└────────────────────────────────────────────────────────────────┘

┌─ COLOR SCHEME ───────────────────────────────────────────────┐
│                                                              │
│  🟨 Yellow Cube   = Ego Vehicle (your car)                 │
│  🔵 Blue Cubes    = Other Vehicles (NPCs)                  │
│  💜 Magenta Dots  = RADAR Detections                       │
│  🔵 Cyan Points   = LIDAR Point Cloud                      │
│  ⚪ White Grid    = Reference Ground Plane                 │
│                                                              │
└────────────────────────────────────────────────────────────────┘

TIPS:
  • Use Local Viewer for quick checks, Foxglove Web for analysis
  • All sensors are synchronized to the same timestamp
  • Point clouds can have 50k+ points - zoom out if too dense
  • LIDAR warmup takes 1-2 seconds - be patient on startup
  • Foxglove Web supports recording - great for offline analysis
  • Edit foxglove_viewer.html for custom visualizations

SUPPORT:
  • Check console output for errors
  • Open DevTools (F12) in browser for JS errors
  • Verify CARLA is running on localhost:2000
  • Read FOXGLOVE_GUIDE.md for detailed help

═════════════════════════════════════════════════════════════════
Version: 1.0 | Created: February 2026
═════════════════════════════════════════════════════════════════
"""

if __name__ == '__main__':
    print(CHEATSHEET)
