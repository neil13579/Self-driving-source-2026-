# 🌐 Foxglove Integration Diagram

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     CARLA Simulator                             │
│              (localhost:2000)                                   │
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Camera  │  │ LIDAR   │  │ RADAR   │  │ IMU     │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │            │            │            │                 │
└───────┼────────────┼────────────┼────────────┼─────────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────────┐
│              foxglove_server.py (WebSocket Server)              │
│              (localhost:8766)                                   │
│                                                                  │
│  [Camera] ──┐                                                   │
│  [LIDAR]  ──┼──→ [Message Builder] ──→ [WebSocket Handler]    │
│  [RADAR]  ──┤                                                   │
│  [Pose]   ──┘                                                   │
│                                                                  │
│  Broadcasting:                                                  │
│    • /camera/rgb      (JPEG, 20Hz)                            │
│    • /lidar/points    (Point Cloud, 20Hz)                     │
│    • /radar/markers   (Markers, 20Hz)                         │
│    • /ego_pose        (Position+Rotation, 20Hz)               │
│    • /vehicles/markers (Vehicle positions, 20Hz)              │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ ws://localhost:8766
                       │ (JSON over WebSocket)
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
   ┌─────────────┐            ┌────────────────┐
   │ Local View  │            │ Foxglove Web   │
   └─────────────┘            └────────────────┘
```

## Data Flow

```
CARLA Sensors
      ↓
  Callbacks
      ↓
Data Buffer
      ↓
Message Builders (Convert to Foxglove format)
      ↓
WebSocket Server (ws://localhost:8766)
      ↓
Browser Clients
      ├─ Local Viewer (Three.js)
      └─ Foxglove Web (app.foxglove.dev)
```

## File Architecture

```
Carla_SEAL/
│
├─ foxglove_server.py ⭐ (Core WebSocket server)
│   ├─ Connects to CARLA on localhost:2000
│   ├─ Attaches sensors (Camera, LIDAR, RADAR)
│   ├─ Broadcasts on ws://localhost:8766
│   └─ Converts data to Foxglove format
│
├─ foxglove.html (Gateway page)
│   ├─ Explains available options
│   ├─ Links to Local Viewer
│   └─ Links to Foxglove Web
│
├─ foxglove_viewer.html ⭐ (Custom 3D visualization)
│   ├─ Three.js 3D engine
│   ├─ Real-time point cloud rendering
│   ├─ Interactive camera controls
│   ├─ Multiple view modes
│   └─ Sensor toggles
│
├─ start_foxglove.py (HTTP server)
│   ├─ Serves HTML files on localhost:8001
│   └─ Opens browser automatically
│
├─ START_FOXGLOVE.bat (Windows launcher)
│   ├─ One-click start
│   ├─ Starts Foxglove server
│   └─ Starts HTTP server
│
├─ Documentation/
│   ├─ README_FOXGLOVE.md (Quick start)
│   ├─ FOXGLOVE_GUIDE.md (Complete guide)
│   ├─ FOXGLOVE_SETUP_SUMMARY.md (Detailed overview)
│   └─ foxglove_cheatsheet.py (Quick reference)
│
└─ config/
    └─ config.json (Configuration)
```

## Process Overview

```
When you run START_FOXGLOVE.bat:

┌─────────────────────────────────────────┐
│ Window 1: Foxglove Server               │
│ (foxglove_server.py)                    │
│                                          │
│ • Connects to CARLA:2000                │
│ • Spawns ego vehicle                    │
│ • Attaches sensors                      │
│ • Listens on ws://localhost:8766        │
│ • Broadcasts sensor data (20 Hz)        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Window 2: HTTP Server + Browser         │
│ (start_foxglove.py)                     │
│                                          │
│ • Serves files on http://localhost:8001 │
│ • Opens browser to foxglove_viewer.html │
│ • Connects WebSocket to server          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Browser Window: Visualization           │
│ (foxglove_viewer.html)                  │
│                                          │
│ • Receives WebSocket messages (20 Hz)   │
│ • Renders 3D scene with Three.js       │
│ • Shows camera, LIDAR, RADAR, vehicles │
│ • Interactive controls                  │
│ • Real-time stats                       │
└─────────────────────────────────────────┘
```

## Network Ports

```
localhost:2000   ← CARLA Simulator
                  (server must be running)

localhost:8001   ← HTTP Server
                  (serves HTML files)

localhost:8766   ← Foxglove WebSocket
                  (sensor data broadcasting)

https://app.foxglove.dev/ ← Optional
                            (alternative viewer)
```

## Update Cycle

```
Every 50ms (20 Hz):

┌────────────────────────────────────┐
│ 1. Collect sensor data from CARLA  │
│    - RGB camera frame              │
│    - LIDAR points (~50k)           │
│    - RADAR detections              │
│    - Ego vehicle pose              │
│    - Actor positions               │
└────────────────────┬───────────────┘
                     ▼
┌────────────────────────────────────┐
│ 2. Build Foxglove messages         │
│    - Encode images (JPEG)          │
│    - Format point clouds           │
│    - Create markers                │
│    - Convert poses (quaternions)   │
└────────────────────┬───────────────┘
                     ▼
┌────────────────────────────────────┐
│ 3. Send via WebSocket              │
│    - JSON over ws://localhost:8766 │
│    - Broadcast to all clients      │
└────────────────────┬───────────────┘
                     ▼
┌────────────────────────────────────┐
│ 4. Browser receives & renders      │
│    - Decodes messages              │
│    - Updates point cloud           │
│    - Updates vehicle positions     │
│    - Refreshes textures            │
│    - Maintains at 20+ FPS          │
└────────────────────────────────────┘
```

## Control Flow

```
User Interaction
       ▼
Browser Input (Mouse/Keyboard)
       ▼
JavaScript Event Handler (foxglove_viewer.html)
       ▼
Update Three.js Scene
       ├─ Camera position/rotation
       ├─ Point cloud vertices
       ├─ Marker positions
       └─ Texture updates
       ▼
WebGL Render
       ▼
Screen Update (20+ FPS)
```

## Message Format (Example)

```json
{
  "messages": [
    {
      "topic": "/camera/rgb",
      "timestamp": 1675850401234,
      "message": {
        "height": 480,
        "width": 640,
        "encoding": "jpeg",
        "data": "base64_encoded_jpeg_data..."
      }
    },
    {
      "topic": "/lidar/points",
      "timestamp": 1675850401234,
      "message": {
        "width": 50000,
        "height": 1,
        "fields": [...],
        "data": "base64_encoded_point_data..."
      }
    },
    {
      "topic": "/ego_pose",
      "timestamp": 1675850401234,
      "message": {
        "pose": {
          "position": {"x": 100.5, "y": 50.2, "z": 1.0},
          "orientation": {"x": 0, "y": 0, "z": 0.707, "w": 0.707}
        }
      }
    }
  ],
  "timestamp": 1675850401234
}
```

## Hardware Requirements

```
Minimum:
├─ CPU: 4 cores @ 2GHz
├─ RAM: 8GB (CARLA 4GB + Server 1GB + Browser 2GB + OS 2GB)
├─ GPU: Any dedicated GPU (for CARLA rendering)
└─ Network: Localhost only (no network bandwidth needed)

Recommended:
├─ CPU: 8 cores @ 3GHz+
├─ RAM: 16GB
├─ GPU: NVIDIA GTX 1060+ or equivalent
└─ Storage: SSD for CARLA assets (50GB+)
```

## Color Legend

```
In 3D Viewer:

🟨 Yellow = Ego vehicle (your autonomous car)
🔵 Blue = Other vehicles (NPCs)
💜 Magenta = RADAR detections (spheres)
🔵 Cyan = LIDAR point cloud (small dots)
⚪ White = Grid/axes (reference)

In Controls:
✅ Checked = Visible in scene
❌ Unchecked = Hidden from scene
```

## View Modes Comparison

```
┌─────────────┬──────────────┬──────────────┬──────────────┐
│   ORBIT     │    EGO       │   TOP-DOWN   │    FOLLOW    │
├─────────────┼──────────────┼──────────────┼──────────────┤
│ Free camera │ Windshield   │ Bird's eye   │ Rear view    │
│ rotation    │ camera view  │ of scene     │ (chase cam)  │
└─────────────┴──────────────┴──────────────┴──────────────┘
```

## Latency Profile

```
CARLA Sensor → Callback: ~1ms
Callback → Message Build: ~5ms
Message Build → WebSocket Send: ~2ms
Network (localhost): <1ms
Browser Receive → Render: ~10ms
──────────────────────
Total Latency: ~20ms (very low!)

Visual Update: 20 Hz = 50ms per frame
→ New frame arrives while previous rendering
→ Smooth continuous updates
```

---

**This diagram shows the complete Foxglove integration system. Everything works together to give you real-time visualization of CARLA sensor data!** 🚗✨
