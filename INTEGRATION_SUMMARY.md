# CARLA Perception System Integration - Summary

## Overview
Successfully combined **carla_app.py**, **carla_vision.py**, and **ukf_perception.py** into a unified, professional perception system with integrated vision pipeline and sensor fusion.

## What Was Combined

### 1. **U-Net Semantic Segmentation** (from carla_vision.py)
- Complete U-Net architecture implementation
- 13-class semantic segmentation for CARLA scenes
- Encoder-decoder with skip connections
- Integrated into main perception stack

### 2. **Bounding Box Detection** (from carla_vision.py)
- Object detection from segmentation masks
- Non-max suppression for filtering overlapping boxes
- Support for Vehicle, Person, Traffic Light, Traffic Sign classes
- IoU-based detection processing

### 3. **Object Tracking** (from carla_vision.py)
- Multi-object tracking across frames
- Age-based track management
- Class-aware matching

### 4. **Flask Web Server** (from carla_app.py)
- Replaced old HTTP server with Flask
- Professional web dashboard
- RESTful API endpoints

### 5. **UKF Sensor Fusion** (from ukf_perception.py)
- Unscented Kalman Filter for multi-sensor fusion
- LiDAR, Radar, GPS, and IMU integration
- 10-dimensional state space tracking

### 6. **WebSocket Communication**
- Real-time sensor data streaming
- GPS updates
- Fused pose estimates

## New Features

### Professional Web Dashboard
- **Responsive Grid Layout** - Adapts to different screen sizes
- **Real-time Vision Pipeline Display**:
  - RGB camera feed
  - Semantic segmentation overlay
  - Bounding box visualizations
  - LiDAR point cloud counter
  
- **Statistics Panel**:
  - FPS monitoring
  - Frame counter
  - LiDAR point tracking
  - Active object tracks
  
- **Sensor Data Display**:
  - GPS coordinates (latitude, longitude, altitude)
  - Radar detection count
  
- **UKF Fusion State**:
  - Position (X, Y, Z)
  - Velocity calculation
  
- **Object Detections List**:
  - Real-time detection list
  - Confidence scores
  - Bounding box coordinates
  - Color-coded by object class

### Enhanced Camera Integration
- RGB camera feed processed with U-Net
- Real-time segmentation prediction
- Bounding box extraction and visualization
- Object tracking integration

## File Structure

```
ukf_perception.py (Main integrated file)
├── U-Net Model
├── BoundingBoxDetector
├── ObjectTracker
├── UnscentedKalmanFilter
├── DataWebSocketServer
├── PerceptionStack (Enhanced with vision)
├── Flask App
└── Main execution loop

carla_web.html (Professional dashboard)
├── Responsive grid layout
├── Real-time image updates
├── Statistics display
├── Sensor data visualization
└── Object detection list
```

## API Endpoints

### Flask Routes
- `GET /` - Main dashboard HTML
- `POST /api/start` - Start processing
- `POST /api/stop` - Stop processing
- `GET /api/frame` - Get current frame data (RGB, segmentation, bbox, detections)
- `GET /api/stats` - Get current statistics

### WebSocket (ws://localhost:8765)
- **lidar** - Point cloud data
- **radar** - Radar detections
- **gps** - GPS coordinates
- **pose** - UKF fused pose estimate

## Running the System

```bash
python ukf_perception.py
```

Then open browser to: **http://localhost:5000**

### Requirements
- CARLA simulator running on localhost:2000
- Python packages:
  - carla
  - tensorflow
  - numpy
  - opencv-python (cv2)
  - flask
  - flask-cors
  - websockets
  - scipy

## Data Flow

```
CARLA Simulator
    ↓
Sensors (Camera, LiDAR, Radar, GPS, IMU)
    ↓
Perception Stack
├── Camera → U-Net → Segmentation → BBox Detection → Tracker
├── LiDAR → Point Cloud Processing
├── Radar → Detection Extraction
├── GPS → Coordinate Conversion
└── IMU → Angular Velocity
    ↓
UKF Sensor Fusion (Multi-modal integration)
    ↓
Flask REST API ← → Web Dashboard
    ↓
WebSocket Streaming ← → Real-time Updates
```

## Key Improvements

✅ **Unified Architecture** - All vision + sensor fusion in one system
✅ **Professional UI** - Modern, responsive dashboard with dark theme
✅ **Real-time Visualization** - Live segmentation, bboxes, and detections
✅ **Accurate Object Detection** - U-Net + tracking for robust detection
✅ **Multi-sensor Integration** - LiDAR, Radar, GPS, and IMU fusion
✅ **RESTful API** - Clean endpoints for frame and stats data
✅ **WebSocket Streaming** - Efficient real-time data transmission

## Statistics Tracked

- **Frame Count** - Total processed frames
- **FPS** - Real-time frames per second
- **LiDAR Points** - Point cloud size
- **Radar Detections** - Radar object count
- **Active Tracks** - Currently tracked objects
- **Total Detections** - Cumulative detections

## Color Legend

- **Road** - Teal (128, 64, 128)
- **Vehicle** - Dark Blue (0, 0, 142)
- **Person** - Red (220, 20, 60)
- **Traffic Light** - Orange (250, 170, 30)
- **Traffic Sign** - Yellow (220, 220, 0)
- **Sky** - Light Blue (70, 130, 180)
