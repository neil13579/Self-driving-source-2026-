# LiDAR & Radar Visualization - Quick Start

## What's New ✨

Your dashboard now displays **real-time LiDAR point clouds** and **Radar detections** alongside the vision pipeline!

### New Visualizations:

1. **☁️ LiDAR Point Cloud** - Bird's eye view of 32-channel point cloud
2. **📡 Radar Detection** - Color-coded objects based on velocity

## How to Use

### 1. Start the System
```bash
python ukf_perception.py
```

### 2. Open Dashboard
Navigate to: **http://localhost:5000**

### 3. Click "Start System"
The dashboard will automatically display:
- ✅ RGB camera feed
- ✅ Semantic segmentation
- ✅ Object detection bounding boxes
- ✅ **LiDAR point cloud** (NEW!)
- ✅ **Radar detections** (NEW!)

## Dashboard Layout

```
Top Row:       [RGB Camera]  [LiDAR Cloud]
Middle Row:    [Segmentation]  [Radar]
Bottom:        [Detections]  [Statistics]
```

## LiDAR Visualization Guide

### What You See:
- **Green dot** at center = Your vehicle (ego)
- **Blue dots** = LiDAR point cloud points
- **Grid lines** = Distance markers (10m each)
- **Blue circle** = 50m sensor range

### Bird's Eye View:
```
         North (50m)
             ↑
     [ ][ ][ ]
West[ ][ X ][ ] East
     [ ][ ][ ]
             ↓
         South (50m)
         
X = Your vehicle
```

## Radar Visualization Guide

### Color Meanings:
- **🟢 Green** = Stationary objects (< 5 m/s)
- **🟡 Yellow** = Moving objects (5-15 m/s)  
- **🔴 Red** = Fast moving objects (> 15 m/s)

### Visual Elements:
- **Orange circle** at center = Your vehicle
- **Colored circles** = Detected objects
- **Lines extending** = Velocity vectors (direction & speed)
- **Circle outline** = 100m sensor range

### Example:
```
Green object detected 20m ahead, not moving
Yellow object detected 50m to the right, moving 10 m/s
Red object detected 30m behind, moving 25 m/s
```

## Performance Tips

1. **Optimize Downsampling**
   - Default: Every 5th point shown
   - Edit line 1433 in ukf_perception.py for faster/slower updates

2. **Canvas Smoothness**
   - Check browser: Chrome/Firefox recommended
   - Disable other browser tabs to reduce CPU load

3. **Network Speed**
   - Localhost connection = ~10 FPS
   - Remote connection = varies with network

## Data Flow

```
CARLA Simulator
    ↓
LiDAR Sensor (32 channels) → callback → store points
    ↓
Radar Sensor → callback → store detections
    ↓
Flask API (/api/frame) → encode as hex
    ↓
Browser Dashboard
    ↓
Canvas Rendering (JavaScript)
    ↓
Real-time Visualization
```

## Troubleshooting

**LiDAR shows no points?**
- Vehicle may not be spawned yet
- Wait 3-5 seconds for initialization
- Check browser console (F12) for errors

**Radar shows no objects?**
- No traffic nearby - click "Spawn" button to add vehicles
- Objects need to be detected (check Radar range settings)

**Canvas not updating?**
- Check browser console for JavaScript errors
- Verify `localhost:5000` is accessible
- Try refreshing page

**Frames slow/stuttering?**
- Reduce update frequency in Flask (default 100ms)
- Increase LiDAR downsampling (change `::5` to `::10`)

## Sensor Specifications

### LiDAR
- **Type**: 32-channel Ray Cast sensor
- **Range**: 50 meters
- **Update Rate**: 10 Hz
- **Points per Second**: 280,000
- **Channels**: 32
- **Position**: 0.5m forward, 2.4m up from vehicle center

### Radar
- **Type**: Doppler Radar
- **Range**: 100 meters
- **Horizontal FOV**: 30°
- **Update Rate**: Variable (depends on detections)
- **Data**: Position (x,y,z) + Velocity
- **Position**: 2.0m forward, 1.0m up from vehicle center

## Advanced Usage

### Access Raw Sensor Data
Edit ukf_perception.py to access:
```python
# LiDAR points (shape: N×4 where columns are x,y,z,intensity)
self.latest_lidar_points

# Radar objects (shape: N×4 where columns are x,y,z,velocity)
self.latest_radar_objects
```

### Customize Visualization
Edit `drawLidarPointCloud()` or `drawRadarDetections()` in carla_web.html to:
- Change colors
- Adjust grid size
- Modify range circles
- Add labels/annotations

### Record Sensor Data
The system automatically sends data to WebSocket server. See `data_ws` for capturing raw sensor feeds.

## Next Steps

1. **Add More Traffic** - Click spawn button for realistic scenarios
2. **Test Sensor Fusion** - UKF combines all 5 sensors for robust state estimation
3. **Develop Algorithms** - Use LiDAR/Radar for object tracking or collision detection
4. **Record Sessions** - Capture sensor data for offline analysis

## Need More Help?

Check these files:
- **LIDAR_RADAR_GUIDE.md** - Technical details
- **ARCHITECTURE.md** - System design
- **CONFIG_GUIDE.md** - Configuration options
- **QUICKSTART.md** - General getting started guide

---

**Happy Autonomous Driving Development! 🚗💨**
