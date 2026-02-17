# 🎮 Foxglove WebSocket Integration Summary

## ✅ What Was Created

I've set up a complete **Foxglove WebSocket server** for real-time visualization of CARLA sensor data in your browser.

---

## 📁 New Files

### Core Components:

1. **`foxglove_server.py`** ⭐
   - WebSocket server converting CARLA data to Foxglove format
   - Streams: Camera, LIDAR, RADAR, Ego Pose, Vehicles
   - Port: `ws://localhost:8766`
   - Update rate: 20 Hz

2. **`foxglove.html`** 
   - Gateway page with connection options
   - Link to official Foxglove Web or local viewer
   - Shows available data topics

3. **`foxglove_viewer.html`** ⭐
   - Custom 3D visualization using Three.js
   - Interactive controls (orbit, pan, zoom)
   - Multiple view modes (Orbit, Ego, Top-Down, Follow)
   - Real-time point cloud rendering

### Helper Scripts:

4. **`start_foxglove.py`**
   - HTTP server to serve HTML files
   - Automatically opens browser

5. **`START_FOXGLOVE.bat`** (Windows)
   - One-click start for both servers
   - Checks CARLA is running

### Documentation:

6. **`FOXGLOVE_GUIDE.md`**
   - Complete setup and usage guide
   - Architecture explanation
   - Troubleshooting tips

---

## 🚀 How to Run

### **Easiest Way (Windows):**
```bash
START_FOXGLOVE.bat
```

### **Manual Way:**

**Terminal 1 - Start CARLA:**
```bash
CarlaUE4.exe -windowed -carla-port=2000
```

**Terminal 2 - Start Foxglove Server:**
```bash
python foxglove_server.py
```

**Terminal 3 - Start HTTP Server:**
```bash
python start_foxglove.py
```

Or use the batch file which does all of this automatically.

---

## 💻 Access Points

Once running, you have **TWO visualization options**:

### Option 1: Local 3D Viewer (Recommended)
```
URL: http://localhost:8001/foxglove_viewer.html
```
✅ Full 3D scene with LIDAR point clouds  
✅ Interactive camera controls  
✅ Real-time data streaming  
✅ Multiple view modes  

**Mouse Controls:**
- Left drag = Rotate
- Right drag = Pan
- Scroll = Zoom
- Space = Reset

---

### Option 2: Official Foxglove Web
```
URL: https://app.foxglove.dev/
Connection: ws://localhost:8766
```
✅ Professional visualization tool  
✅ Multiple synchronized panels  
✅ Custom layouts  
✅ Time series plotting  
✅ Data recording  

**Connection Steps:**
1. Go to https://app.foxglove.dev/
2. Click "Open Connection"
3. Select "WebSocket"
4. Enter: `ws://localhost:8766`
5. Click Connect

---

## 📊 Data Streams (Topics)

The WebSocket server broadcasts these topics:

| Topic | Type | Data | Updates |
|-------|------|------|---------|
| `/camera/rgb` | Image | JPEG (640x480) | 20 Hz |
| `/lidar/points` | PointCloud | 3D XYZ points | 20 Hz |
| `/radar/markers` | Markers | 3D positions | 20 Hz |
| `/ego_pose` | Pose | Position + Rotation | 20 Hz |
| `/vehicles/markers` | MarkerArray | All visible vehicles | 20 Hz |

---

## 🎨 Visual Elements

### In 3D Viewer:

- 🟨 **Yellow cube** = Your ego vehicle
- 🔵 **Blue cubes** = Other vehicles  
- 💜 **Magenta spheres** = RADAR detections
- 🔵 **Cyan points** = LIDAR point cloud
- 📐 **Grid** = Reference plane

### Colors Correspond To:
```
Real sensor data → Same color in visualization
```

---

## 🔧 Technical Details

### Architecture:

```
CARLA Simulator (localhost:2000)
    ↓ (Sensor callbacks)
    ↓
foxglove_server.py
    ├→ RGB camera callback
    ├→ Depth camera callback
    ├→ LIDAR callback
    ├→ RADAR callback
    └→ Vehicle poses
    ↓ (Converts to Foxglove format)
    ↓
WebSocket Server (localhost:8766)
    ↓ (JSON over WebSocket)
    ↓
Browser Visualization
    ├→ https://app.foxglove.dev/ (Option A)
    └→ http://localhost:8001/foxglove_viewer.html (Option B)
```

### Message Format:

Each WebSocket message contains:
```json
{
  "messages": [
    {
      "topic": "/camera/rgb",
      "timestamp": 1675850401234,
      "message": { ... }
    },
    {
      "topic": "/lidar/points",
      "timestamp": 1675850401234,
      "message": { ... }
    }
  ],
  "timestamp": 1675850401234
}
```

---

## ✨ Features

### Local Viewer (3D):
- ✅ Real-time point cloud rendering
- ✅ Multiple view modes
- ✅ Toggle sensors on/off
- ✅ FPS counter and stats
- ✅ Camera feed display
- ✅ Interactive controls

### Foxglove Web:
- ✅ Professional UI
- ✅ Multiple panels
- ✅ Time series plots
- ✅ Message inspection
- ✅ Data recording (MCAP format)
- ✅ Customizable layouts

---

## 🎯 Common Tasks

### **View only LIDAR points:**
1. Uncheck "📷 Camera Feed" in Local Viewer
2. Uncheck "📡 RADAR Markers"
3. Keep "☁️ LIDAR Points" checked

### **Switch to first-person view:**
1. Select "Ego View" from dropdown

### **Get bird's eye view:**
1. Select "Top-Down" view mode

### **Record data for analysis:**
1. Use Foxglove Web
2. Click the record button
3. Drive around
4. Download MCAP file

### **Inspect raw sensor data:**
1. Open Foxglove Web
2. Click on messages in the debug panel
3. View raw JSON

---

## 🐛 Troubleshooting

### Nothing appears on screen?
- ✅ Check CARLA is running on localhost:2000
- ✅ Check foxglove_server.py is running (see console output)
- ✅ Wait 2-3 seconds for sensors to warm up
- ✅ Zoom out with scroll wheel

### Only camera visible, no point cloud?
- ✅ Make sure LIDAR checkbox is checked
- ✅ Try zooming out more
- ✅ Check LIDAR is being spawned (see console)

### Connection refused?
- ✅ Run: `python foxglove_server.py` in separate terminal
- ✅ Check port 8766 is free: `netstat -ano | findstr :8766`
- ✅ Verify CARLA is on localhost:2000

### Foxglove Web won't connect?
- ✅ Make sure WebSocket URL is: `ws://localhost:8766` (not http://)
- ✅ Check server is running
- ✅ Try: https://app.foxglove.dev/ (check for CORS issues)

---

## 📈 Performance Notes

### Current settings:
- Update rate: 20 Hz
- Point cloud: ~50,000 points per frame
- Camera: 640x480 JPEG

### To improve performance:
1. Reduce LIDAR point density (downsample in callback)
2. Lower update frequency (increase sleep time)
3. Disable camera feed in viewer

### To increase fidelity:
1. Increase point cloud resolution
2. Use higher resolution camera
3. Enable depth camera processing

---

## 🚗 Next Steps

1. **Run the demo:**
   ```bash
   START_FOXGLOVE.bat
   ```

2. **Explore the 3D viewer:**
   - Rotate with mouse
   - Try different view modes
   - Toggle sensors

3. **Try Foxglove Web:**
   - Advanced layouts
   - Multi-panel views
   - Data recording

4. **Customize:**
   - Edit `foxglove_viewer.html` for custom visualizations
   - Add more message types
   - Create special effects

---

## 📚 Additional Resources

- **Foxglove Documentation**: https://docs.foxglove.dev/
- **Three.js Documentation**: https://threejs.org/docs/
- **CARLA Sensor Documentation**: https://carla.readthedocs.io/en/latest/ref_sensors/

---

## 💡 Tips

1. **Use both viewers**: Local for quick checks, Foxglove Web for detailed analysis
2. **Save Foxglove layouts**: Create custom layouts for different scenarios
3. **Keyboard shortcuts**: Press `?` in Foxglove Web for help
4. **Time synchronization**: All sensors are synchronized to the same timestamp
5. **High-precision timing**: Timestamps are in milliseconds for accurate replay

---

## 🎉 You're All Set!

With this setup, you now have:
- ✅ Real-time sensor visualization
- ✅ Professional-grade UI
- ✅ Multiple viewing options
- ✅ Data recording capability
- ✅ Custom 3D viewer

**Happy driving and visualizing! 🚗✨**
