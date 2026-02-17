# 🎮 CARLA Foxglove Integration Guide

**Foxglove** is a visualization platform for robotics and autonomous systems. This integration allows you to visualize CARLA sensor data in real-time using Foxglove's web interface.

---

## 📋 What's Included

### Files Created:

1. **`foxglove_server.py`** - WebSocket server that converts CARLA sensor data to Foxglove format
2. **`foxglove.html`** - Gateway page with options to connect to Foxglove
3. **`foxglove_viewer.html`** - Custom 3D viewer (alternative to official Foxglove Web)

---

## 🚀 Quick Start

### Step 1: Start CARLA
```bash
CarlaUE4.exe -windowed -carla-port=2000
```

### Step 2: Start Foxglove Server
```bash
python foxglove_server.py
```

**Expected output:**
```
✅ Ego vehicle spawned
✅ RGB Camera attached
✅ Depth Camera attached
✅ LIDAR attached
✅ RADAR attached

🚀 Starting Foxglove WebSocket on ws://localhost:8766
📱 Open: http://localhost:8001/foxglove.html
============================================================
✅ Foxglove server ready on port 8766!
```

### Step 3: Connect Visualization

**Option A: Local 3D Viewer (Recommended)**
```
Open: http://localhost:8001/foxglove_viewer.html
```

**Option B: Foxglove Web (Official Tool)**
1. Go to https://app.foxglove.dev/
2. Click "Open Connection" 
3. Select "WebSocket"
4. Enter: `ws://localhost:8766`
5. Click "Connect"

---

## 📊 Data Streams

The Foxglove server broadcasts data on these topics:

### `/camera/rgb`
- **Type**: Image (JPEG)
- **Rate**: ~20 Hz
- **Description**: RGB camera feed from ego vehicle

### `/lidar/points`
- **Type**: Point Cloud
- **Rate**: ~20 Hz
- **Description**: 3D point cloud from LIDAR sensor
- **Color in viewer**: Cyan

### `/radar/markers`
- **Type**: Markers
- **Rate**: ~20 Hz
- **Description**: RADAR detections as 3D markers
- **Color in viewer**: Magenta

### `/ego_pose`
- **Type**: PoseStamped
- **Rate**: ~20 Hz
- **Description**: Position and orientation of ego vehicle

### `/vehicles/markers`
- **Type**: MarkerArray
- **Rate**: ~20 Hz
- **Description**: Positions of all visible vehicles
- **Colors**: Yellow = Ego, Blue = NPCs

---

## 🎮 Local 3D Viewer Controls

### Mouse Controls:
- **Left Click + Drag**: Orbit camera around focus point
- **Right Click + Drag**: Pan camera
- **Scroll Wheel**: Zoom in/out
- **Space**: Reset camera to default position

### View Modes:
- **Orbit**: Free camera rotation around scene
- **Ego View**: First-person view from vehicle
- **Top-Down**: Bird's eye view of the scene
- **Follow**: Camera follows vehicle from behind

### Toggles:
- Camera Feed
- LIDAR Points
- RADAR Markers
- Vehicles
- Grid

---

## 🌐 Official Foxglove Web

Foxglove Web is a professional visualization tool with additional features:

### Features:
- ✅ Multiple synchronized views
- ✅ Custom layouts
- ✅ Time series plots
- ✅ Message inspection
- ✅ Data recording
- ✅ Advanced filtering

### Connection Steps:

1. **Navigate to**: https://app.foxglove.dev/

2. **Open Data Source**:
   - Click "Open Connection" button
   - Select "WebSocket" option

3. **Enter Connection Details**:
   ```
   URL: ws://localhost:8766
   ```

4. **Click Connect**

5. **Customize Layout**:
   - Drag panels to arrange
   - Add new panels for different visualizations
   - Save your layout

---

## 📋 Supported Visualizations

In Foxglove Web, you can add panels for:

- **3D Scene**: Full 3D visualization with all sensors
- **Camera**: Display camera feed
- **Point Cloud**: Visualize LIDAR data
- **Markers**: Show RADAR and vehicle positions
- **Plot**: Time series data
- **Text**: Raw message data

---

## 🔧 Architecture

```
CARLA Simulator
  ↓ (Sensors)
  ↓
foxglove_server.py
  ↓ (WebSocket)
  ↓
Browser (Visualization)
  ├─ Local Viewer (foxglove_viewer.html)
  └─ Foxglove Web (app.foxglove.dev)
```

### Data Pipeline:

1. **Sensor Callbacks** in CARLA collect:
   - RGB camera frames
   - Depth camera frames
   - LIDAR point cloud
   - RADAR detections

2. **Message Builders** convert to Foxglove format:
   - Images encoded as JPEG + Base64
   - Point clouds as BufferAttribute
   - Poses as quaternions

3. **WebSocket Server** broadcasts:
   - JSON-encoded messages
   - One message per client per update cycle
   - ~20 Hz update rate

4. **Browser Visualization**:
   - Receives messages via WebSocket
   - Renders with Three.js (local) or Foxglove (web)
   - Updates in real-time

---

## 🐛 Troubleshooting

### Connection Issues

**"Cannot connect to localhost:8766"**
- Verify `foxglove_server.py` is running
- Check firewall settings (allow Python)
- Try: `netstat -ano | findstr :8766`

**"WebSocket connection failed"**
- CARLA might not be running on port 2000
- Start CARLA: `CarlaUE4.exe -windowed -carla-port=2000`

### Visualization Issues

**"No point cloud visible"**
- Check LIDAR is spawned (see console output)
- Try clicking the LIDAR checkbox off/on in viewer
- Zoom out (may be too close)

**"Camera feed not showing"**
- Wait 1-2 seconds for first image to arrive
- Check browser console (F12) for errors
- Ensure `camera_rgb` callback is working

**"All black screen in local viewer"**
- Camera may be looking at ground
- Press Space to reset view
- Try "Top-Down" view mode

### Port Conflicts

If ports are already in use:

**Check what's using the port:**
```powershell
netstat -ano | findstr :8766
```

**Kill the process:**
```powershell
taskkill /PID <PID_NUMBER> /F
```

**Or use different ports** (edit `foxglove_server.py`):
```python
FOXGLOVE_WS_PORT = 8766  # Change this
FOXGLOVE_HTM_PORT = 8001  # Change this
```

---

## 📈 Performance Tuning

### Increase Update Rate:
In `foxglove_server.py`, change sleep duration:
```python
await asyncio.sleep(0.05)  # Currently 20 Hz
await asyncio.sleep(0.033)  # For ~30 Hz
```

### Reduce Point Cloud Resolution:
In LIDAR callback, downsample points:
```python
def lidar_callback(data):
    points = ...
    sensor_data['lidar_points'] = points[::2, :3].tolist()  # Skip every 2nd point
```

### Enable Depth of Field:
In `foxglove_server.py`, enable depth camera for 3D reconstruction

---

## 🎓 Advanced Usage

### Custom Message Types

To add custom messages, follow this pattern:

```python
def custom_callback(data):
    message = {
        'topic': '/custom/topic',
        'timestamp': timestamp,
        'message': {
            'header': {...},
            'data': {...}
        }
    }
    return message
```

### Recording Data

Foxglove Web supports recording sessions:
1. Click the record button
2. Drive your vehicle
3. Download the MCAP file
4. Play back anytime

### Time Sync

Foxglove automatically syncs timestamps across all messages, allowing you to replay at any speed.

---

## 💡 Tips & Tricks

1. **Sync multiple sensors**: All timestamps are aligned to microsecond precision
2. **Message inspection**: Click on any message in Foxglove to see raw data
3. **Custom layouts**: Save your favorite layout configurations
4. **Dark mode**: Foxglove automatically detects your system theme
5. **Keyboard shortcuts**: Press `?` in Foxglove Web for help

---

## 📞 Support

If you encounter issues:

1. Check the console output of `foxglove_server.py`
2. Open browser DevTools (F12) for JavaScript errors
3. Verify CARLA is running with: `CarlaUE4.exe -windowed -carla-port=2000`
4. Check network connectivity: `ping localhost`

---

## 🚗 Next Steps

- **Modify viewers**: Edit `foxglove_viewer.html` to add custom visualizations
- **Add more sensors**: Extend `foxglove_server.py` with additional sensors
- **Export data**: Record sessions in Foxglove Web for offline analysis
- **Integrate ML**: Add object detection overlays or predictions

---

**Happy visualizing! 🎉**
