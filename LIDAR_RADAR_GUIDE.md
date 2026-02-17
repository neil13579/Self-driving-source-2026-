# LiDAR and Radar Visualization Guide

## Overview
The CARLA Perception System now includes professional LiDAR point cloud and Radar detection visualizations on the web dashboard.

## Features

### 🌐 LiDAR Point Cloud Visualization
- **Real-time 2D Bird's Eye View** of LiDAR point cloud
- **Color-coded points** showing 3D spatial distribution
- **Grid overlay** for distance reference
- **Range visualization** (50m max range)
- **32 channels** with downsampling for web streaming

#### How it works:
1. LiDAR sensor captures 3D points (x, y, z, intensity)
2. Points are projected to 2D bird's eye view
3. Grid lines show 10m increments
4. Green circle at center = ego vehicle
5. Blue points = LiDAR detections
6. Real-time point count displayed

### 📡 Radar Detection Visualization
- **Real-time 2D Bird's Eye View** of radar detections
- **Velocity-based color coding:**
  - 🟢 Green = Stationary (< 5 m/s)
  - 🟡 Yellow = Moving (5-15 m/s)
  - 🔴 Red = Fast moving (> 15 m/s)
- **Velocity vectors** showing direction and speed
- **Range visualization** (100m max range)

#### How it works:
1. Radar sensor detects objects with depth, azimuth, altitude, velocity
2. Convert spherical to Cartesian coordinates
3. Color by velocity magnitude
4. Draw velocity vectors as lines
5. Orange circle = ego vehicle
6. Real-time detection count displayed

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│                  📷 RGB Camera                               │
│              ☁️ LiDAR Point Cloud                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│        🎨 Semantic Segmentation                             │
│            📡 Radar Detection                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│        🎯 Object Detection        │    📊 Statistics        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                📋 Current Detections                        │
└─────────────────────────────────────────────────────────────┘
```

## Technical Implementation

### Backend (ukf_perception.py)
- **LiDAR Callback** (Line 1417):
  - Processes raw point cloud data
  - Stores latest points in `self.latest_lidar_points`
  - Downsamples by factor of 5 for web transfer
  - Updates LiDAR point count in stats

- **Radar Callback** (Line 1447):
  - Converts spherical to Cartesian coordinates
  - Stores detections in `self.latest_radar_objects`
  - Extracts velocity information
  - Updates for UKF sensor fusion

- **Frame Data API** (get_frame_data):
  - Encodes LiDAR points as hex string
  - Encodes Radar objects as hex string
  - Includes with JSON response

### Frontend (carla_web.html)
- **Canvas Rendering**:
  - `drawLidarPointCloud()`: 2D projection of point cloud
  - `drawRadarDetections()`: Velocity-colored detection visualization
  
- **Data Decoding**:
  - Hex string → Uint8Array → Float32Array
  - Real-time canvas updates (100ms interval)

## Performance Specs

| Sensor | Resolution | Max Range | Update Rate | Web FPS |
|--------|-----------|-----------|------------|---------|
| LiDAR | 32 channels | 50m | 10 Hz | 10 FPS |
| Radar | - | 100m | Variable | 10 FPS |

## Real-World Applications

1. **Autonomous Driving Development**
   - Test object detection in 3D space
   - Validate sensor fusion algorithms
   - Simulate realistic traffic scenarios

2. **Sensor Testing**
   - Visualize sensor blind spots
   - Detect sensor interference
   - Validate coordinate transformations

3. **Algorithm Development**
   - Test tracking algorithms on real sensors
   - Validate collision detection
   - Develop path planning with multiple sensors

## Troubleshooting

### LiDAR Not Showing
- Check if LiDAR sensor is properly attached to vehicle
- Verify sensor callback is being called (check console logs)
- Ensure vehicle is spawned correctly

### Radar Not Showing
- Verify radar is in front of vehicle (x: 2.0m forward)
- Check radar detection range settings
- Look for velocity data in raw detections

### Canvas Not Rendering
- Check browser console for JavaScript errors
- Verify canvas IDs match: `lidarCanvas`, `radarCanvas`
- Test with different browser (Chrome/Firefox recommended)

### Slow Updates
- Reduce LiDAR/Radar polling frequency
- Increase downsampling factor
- Check network latency to server

## Configuration

### Adjust Downsampling
Edit `lidar_callback()` in ukf_perception.py:
```python
points_ds = points[::5]  # Change 5 to higher for more downsampling
```

### Change Visualization Scale
Edit canvas drawing functions in carla_web.html:
```javascript
const pixelsPerMeter = 1 / metersPerPixel;  // Adjust for zoom
```

### Adjust Radar Velocity Thresholds
Edit `drawRadarDetections()` in carla_web.html:
```javascript
if (vel > 5) color = '#FFFF00';   // Yellow threshold
if (vel > 15) color = '#FF0000';  // Red threshold
```

## API Endpoints

### GET `/api/frame`
Returns complete frame data including:
```json
{
  "rgb": "base64_jpeg",
  "segmentation": "base64_jpeg",
  "bbox": "base64_jpeg",
  "lidarPoints": "hex_string",
  "radarObjects": "hex_string",
  "detections": [...],
  "stats": {...}
}
```

## Future Enhancements

- [ ] 3D WebGL visualization for point clouds
- [ ] Radar RCS (Radar Cross Section) display
- [ ] LiDAR intensity heatmap
- [ ] Multi-object radar tracking overlay
- [ ] Sensor fusion visualization (combined view)
- [ ] Recording and playback of sensor data
