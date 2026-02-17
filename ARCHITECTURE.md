# System Architecture & Data Flow Diagrams

## High-Level System Architecture

```
╔════════════════════════════════════════════════════════════════════════════╗
║                         CARLA Perception System                            ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│                     CARLA Simulator (localhost:2000)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Camera(256×256) │ LiDAR(32ch) │ Radar(30°FOV) │ GPS │ IMU                  │
└──────────┬──────────────────────────────────┬──────────────────────────────┘
           │                                  │
           ▼                                  ▼
┌────────────────────────────────────┐  ┌─────────────────┐
│   Camera Processing Pipeline       │  │ Sensor Fusion   │
├────────────────────────────────────┤  ├─────────────────┤
│ 1. RGB Capture (256×256)           │  │ LiDAR           │
│ 2. Normalize (0-1)                 │  │ Radar           │
│ 3. U-Net Segmentation              │  │ GPS             │
│ 4. Semantic Mask (13 classes)      │  │ IMU             │
│ 5. Bounding Box Extraction         │  │ ↓               │
│ 6. Non-Max Suppression             │  │ UKF Filter      │
│ 7. Object Tracking                 │  │ ↓               │
│ 8. Visualization                   │  │ Fused Estimate  │
└──────────┬──────────────────────────┘  └────────┬────────┘
           │                                      │
           └──────────────────┬───────────────────┘
                              │
              ┌───────────────▼────────────┐
              │  Flask Web Server          │
              │  (port 5000)               │
              ├────────────────────────────┤
              │ REST API:                  │
              │ - GET /api/frame           │
              │ - GET /api/stats           │
              │ - POST /api/start          │
              │ - POST /api/stop           │
              └──────────┬─────────────────┘
                         │
        ┌────────────────┴─────────────────┐
        │                                  │
        ▼                                  ▼
    ┌─────────────┐            ┌──────────────────┐
    │  Dashboard  │            │ WebSocket        │
    │  (HTTP)     │            │ (ws://8765)      │
    │ - HTML5     │            │ - LiDAR stream   │
    │ - CSS Grid  │            │ - Radar stream   │
    │ - JS Fetch  │            │ - GPS updates    │
    │ - Live imgs │            │ - Pose estimates │
    └─────────────┘            └──────────────────┘
         │                            │
         └────────────┬───────────────┘
                      │
              ┌───────▼──────────┐
              │  Web Browser     │
              │  localhost:5000  │
              └──────────────────┘
```

## Vision Pipeline Detailed Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    VISION PROCESSING PIPELINE                                │
└──────────────────────────────────────────────────────────────────────────────┘

Input: CARLA Camera Frame (256×256×3 RGB)
   │
   ▼
┌─────────────────────────────────────┐
│ Normalization                        │
│ Array / 255.0 → [0, 1] range        │
│ Reshape: (H, W, 3) → (1, H, W, 3)  │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ U-Net Semantic Segmentation         │
│ Input: (1, 256, 256, 3)            │
│ Encoder:                            │
│   Conv → Conv → Pool (64ch)         │
│   Conv → Conv → Pool (128ch)        │
│   Conv → Conv → Pool (256ch)        │
│   Conv → Conv → Pool (512ch)        │
│ Bottleneck:                         │
│   Conv → Conv (1024ch)              │
│ Decoder:                            │
│   Upsample → Concat → Conv (512ch)  │
│   Upsample → Concat → Conv (256ch)  │
│   Upsample → Concat → Conv (128ch)  │
│   Upsample → Concat → Conv (64ch)   │
│ Output: (1, 256, 256, 13)          │
│ 13-class semantic segmentation      │
└─────────────────────────────────────┘
   │
   ▼ Prediction [0]: (256, 256, 13)
┌─────────────────────────────────────┐
│ Argmax & Class Mapping              │
│ predicted_mask = argmax(prediction) │
│ Shape: (256, 256)                   │
│ Values: 0-12 (class indices)        │
└─────────────────────────────────────┘
   │
   ├──────────┬──────────┬────────────┐
   │          │          │            │
   ▼          ▼          ▼            ▼
Vehicle   Person   Traffic L  Traffic S
(class13) (class12) (class7)  (class8)
   │          │          │            │
   └──────────┴──────────┴────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│ Connected Component Analysis        │
│ For each class:                     │
│   - Binary mask for class           │
│   - Label connected regions         │
│   - Calculate bounding box          │
│   - Compute area & confidence       │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│ Detection Generation                │
│ For each region:                    │
│ {                                   │
│   'class': 'Vehicle',              │
│   'bbox': [x1, y1, x2, y2],        │
│   'confidence': 0.92,               │
│   'area': 5000                      │
│ }                                   │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ Non-Max Suppression (per class)     │
│ Sort by confidence (descending)     │
│ For each detection:                 │
│   Keep if IoU < threshold (0.5)    │
│   With all kept detections          │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ Object Tracking                     │
│ Match with previous tracks:         │
│   - Same class                      │
│   - IoU-based matching              │
│   - Age management                  │
│ Output:                             │
│ [                                   │
│   {'id': 1, 'detection': {...}},   │
│   {'id': 2, 'detection': {...}},   │
│   ...                               │
│ ]                                   │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ Visualization & Encoding            │
│ Draw on RGB image:                  │
│   - Bounding boxes (class color)    │
│   - Labels + confidence             │
│ Encode to JPEG:                     │
│   - RGB → BGR (OpenCV)              │
│   - JPEG compress                   │
│   - Base64 encode                   │
└─────────────────────────────────────┘
   │
   ▼
Output: Base64-encoded JPEG image
        with bounding boxes
        ready for web display
```

## Sensor Fusion with UKF

```
┌──────────────────────────────────────────────────────────────────────────────┐
│              UNSCENTED KALMAN FILTER - SENSOR FUSION                         │
└──────────────────────────────────────────────────────────────────────────────┘

State Vector (10D):
┌────────────────────────────┐
│ x[0:3]   = Position (x,y,z)│
│ x[3:6]   = Velocity (vx,vy,vz)
│ x[6:9]   = Acceleration    │
│ x[9]     = Angular Velocity│
└────────────────────────────┘

Sensor Inputs:
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  LiDAR   │  │  Radar   │  │   GPS    │  │   IMU    │
├──────────┤  ├──────────┤  ├──────────┤  ├──────────┤
│Position  │  │Velocity  │  │Position  │  │Accel     │
│Point cnt │  │Detections│  │Altitude  │  │Gyro(z)   │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │            │             │            │
     └─────┬──────┴──────┬──────┴────────────┘
           │             │
           ▼             ▼
      ┌───────────────────────┐
      │ Sigma Point Generator │
      │ (2n+1 points where    │
      │  n=10 dimensions)     │
      └───────────────────────┘
           │
           ▼
      ┌───────────────────────┐
      │ State Prediction      │
      │ x_pred = f(x, dt)    │
      │ P_pred = Q matrix     │
      └───────────────────────┘
           │
           ▼
      ┌───────────────────────┐
      │ Measurement Update    │
      │ Kalman Gain Calc      │
      │ State Correction      │
      │ Covariance Update     │
      └───────────────────────┘
           │
           ▼
      Output: Fused State Estimate
      - Position uncertainty
      - Velocity certainty
      - Acceleration estimates
```

## Web Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🚗 CARLA Perception System                                                │
│  Real-time Sensor Fusion + Vision + Object Detection                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────┐  ┌──────────────────────────┐    │
│  │     VISION PIPELINE (Left)          │  │  STATISTICS (Right)      │    │
│  ├─────────────────────────────────────┤  ├──────────────────────────┤    │
│  │                                     │  │  📊 Statistics            │    │
│  │  ┌──────────┐  ┌──────────┐       │  │  ┌────────────────────┐   │    │
│  │  │ RGB Cam  │  │ BBoxes   │       │  │  │ FPS: 12.5 fps      │   │    │
│  │  │ Live ●   │  │ Objects:3│       │  │  │ Frames: 1234       │   │    │
│  │  │          │  │          │       │  │  │ LiDAR: 28000 pts   │   │    │
│  │  │          │  │ ◻●▪●◻    │       │  │  │ Tracks: 3          │   │    │
│  │  │ 256×256  │  │          │       │  │  └────────────────────┘   │    │
│  │  └──────────┘  └──────────┘       │  │                           │    │
│  │                                     │  │  🛰️ Sensor Data          │    │
│  │  ┌──────────┐  ┌──────────┐       │  │  ┌────────────────────┐   │    │
│  │  │ Segment  │  │ LiDAR    │       │  │  │ GPS: 42.123°N      │   │    │
│  │  │ FPS: 12.5│  │ Pts: 28k │       │  │  │     71.987°W       │   │    │
│  │  │          │  │          │       │  │  │ Alt: 10.5m         │   │    │
│  │  │ ████████ │  │ ·····    │       │  │  │ Radar: 5 objects   │   │    │
│  │  └──────────┘  └──────────┘       │  │  └────────────────────┘   │    │
│  │                                     │  │                           │    │
│  ├─────────────────────────────────────┤  │  🔮 UKF Fusion          │    │
│  │ 📋 DETECTIONS                       │  │  ┌────────────────────┐   │    │
│  ├─────────────────────────────────────┤  │  │ X: 50.2 m          │   │    │
│  │ • Vehicle #1        95%   [x1 y1]  │  │  │ Y: -10.5 m         │   │    │
│  │ • Person #2         87%   [x2 y2]  │  │  │ Z: 0.5 m           │   │    │
│  │ • Traffic Light #3  92%   [x3 y3]  │  │  │ Vel: 12.3 m/s      │   │    │
│  │                                     │  │  └────────────────────┘   │    │
│  │ ──────────────────────────────────  │  │                           │    │
│  │ 🎮 CONTROLS                         │  │  ┌────────────────────┐   │    │
│  │  [▶ Start]  [⏹ Stop]                │  │  │ ▶ Start  ⏹ Stop   │   │    │
│  │                                     │  │  └────────────────────┘   │    │
│  └─────────────────────────────────────┘  └──────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## API Communication Flow

```
┌─────────────────┐
│  Web Browser    │
│ http://5000     │
└────────┬────────┘
         │
    ┌────▼─────────────────┐
    │ JavaScript Fetch API │
    └────┬──────────────┬──────────┐
         │              │          │
         ▼              ▼          ▼
    ┌─────────────────────────────────────┐
    │     Flask Web Server (port 5000)    │
    └─┬───────────────────────────────┬───┘
      │                               │
      │ GET /api/frame              │ GET /api/stats
      │                               │
      ▼                               ▼
  ┌──────────────────────────────────────┐
  │  PerceptionStack.get_frame_data()   │
  │  ├─ Lock vision state                 │
  │  ├─ Get RGB image                     │
  │  ├─ Get segmentation image            │
  │  ├─ Get bounding boxes                │
  │  ├─ Get detections list               │
  │  └─ Get stats                         │
  └──────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────┐
  │  Image Encoding (Base64 JPEG)        │
  └──────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────┐
  │  JSON Response                        │
  │  {                                    │
  │    "rgb": "base64(...)",             │
  │    "segmentation": "base64(...)",    │
  │    "bbox": "base64(...)",            │
  │    "detections": [...],              │
  │    "stats": {...}                    │
  │  }                                    │
  └──────────────────────────────────────┘
      │
      ▼
  Browser JavaScript
  ├─ Decode base64 images
  ├─ Display in <img> tags
  ├─ Update statistics
  └─ Update detections list
```

## WebSocket Streaming Data

```
Browser (WebSocket Client) ←→ WebSocket Server (port 8765)

┌──────────────────────────────┐
│ DataWebSocketServer          │
├──────────────────────────────┤
│ Connected Clients: {client1, │
│                   client2,   │
│                   ...}       │
└──────────────────────────────┘

Message Types:
┌────────────────────────────┐
│ 1. LiDAR Stream            │
│    Type: "lidar"           │
│    Data: Float32 array     │
│    Size: ~1-10 MB          │
│    Rate: 1-10 Hz           │
└────────────────────────────┘

┌────────────────────────────┐
│ 2. Radar Stream            │
│    Type: "radar"           │
│    Data: Detection array   │
│    Count: 0-20 objects     │
│    Rate: 10 Hz             │
└────────────────────────────┘

┌────────────────────────────┐
│ 3. GPS Updates             │
│    Type: "gps"             │
│    Lat, Lon, Alt           │
│    Rate: 1 Hz              │
└────────────────────────────┘

┌────────────────────────────┐
│ 4. Fused Pose              │
│    Type: "pose"            │
│    X, Y, Z position        │
│    VX, VY, VZ velocity     │
│    Rate: 10 Hz             │
└────────────────────────────┘
```

## System Component Dependencies

```
ukf_perception.py
├── External Libraries
│   ├── carla (CARLA simulator)
│   ├── tensorflow (U-Net model)
│   ├── opencv (image processing)
│   ├── flask (web server)
│   ├── websockets (real-time communication)
│   ├── numpy (numerical computation)
│   └── scipy (scientific computing)
│
├── Internal Modules
│   ├── UNet
│   │   └── Requires: tensorflow.keras
│   │
│   ├── BoundingBoxDetector
│   │   └── Requires: scipy.ndimage, numpy
│   │
│   ├── ObjectTracker
│   │   └── Requires: numpy
│   │
│   ├── UnscentedKalmanFilter
│   │   └── Requires: scipy.linalg, numpy
│   │
│   ├── DataWebSocketServer
│   │   └── Requires: websockets, asyncio
│   │
│   ├── PerceptionStack
│   │   ├── Requires: carla, All above classes
│   │   └── Provides: Main orchestration
│   │
│   ├── Flask App
│   │   ├── Requires: flask, PerceptionStack
│   │   └── Provides: Web API & Dashboard
│   │
│   └── Main Loop
│       └── Orchestrates everything
│
└── Data Flow
    Camera Frames → U-Net → Detections → Tracking → Display
    Sensors → UKF → Fused Estimate → WebSocket
```

---

**Architecture Date**: February 7, 2026
**System Status**: Production Ready ✅
