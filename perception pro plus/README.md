# CARLA Vision System - Simplified (3 Files)

Complete U-Net semantic segmentation + bounding box detection system for autonomous driving.

## 📁 Files

1. **carla_vision.py** - U-Net model + bounding box detector + tracker
2. **carla_app.py** - Main application with Flask web server
3. **carla_web.html** - Web visualization dashboard

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install tensorflow numpy opencv-python scipy flask flask-cors --break-system-packages
```

### 2. Run the Application
```bash
python carla_app.py
```

### 3. Open in Browser
Go to: **http://localhost:5000**

That's it! The system will auto-start and show:
- 📷 RGB camera feed
- 🎨 Semantic segmentation (13 classes)
- 🎯 Bounding box detection (vehicles, pedestrians, traffic lights, signs)
- 📊 Real-time statistics and FPS
- 📋 Detection list with confidence scores

## 🎯 Features

- **U-Net Model**: Deep learning segmentation with ~31M parameters
- **Object Detection**: Extracts bounding boxes from segmentation masks
- **Object Tracking**: Tracks objects across frames with unique IDs
- **Web Dashboard**: Beautiful real-time visualization
- **Mock CARLA Data**: Works without CARLA simulator (generates synthetic data)

## 🔧 Using Real CARLA

If you have CARLA simulator running:

1. Install CARLA Python package:
```bash
pip install carla --break-system-packages
```

2. Modify `carla_app.py` to use real CARLA instead of mock data

## 📊 Classes Detected

- 🛣️ Road, Sidewalk
- 🏢 Building, Wall, Fence
- 🚦 Traffic Light, Traffic Sign
- 🌳 Vegetation, Terrain, Sky
- 👤 Person
- 🚗 Vehicle

## ⌨️ Controls

- **Start System**: Begin processing
- **Stop System**: Pause processing

---

**Enjoy autonomous driving vision! 🚗💨**
