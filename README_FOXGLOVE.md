# 🎮 CARLA Foxglove WebSocket Integration

A complete real-time visualization system for CARLA autonomous driving simulator using Foxglove.

## ⚡ Quick Start (30 seconds)

### Windows Users:
```bash
# Just run this one file!
START_FOXGLOVE.bat
```

### Manual:
```bash
# Terminal 1: Start CARLA
CarlaUE4.exe -windowed -carla-port=2000

# Terminal 2: Start Foxglove server
python foxglove_server.py

# Terminal 3: Start HTTP server & open browser
python start_foxglove.py
```

## 📺 View Your Data

Once running, open your browser to **one of these**:

### Local 3D Viewer (Recommended):
```
http://localhost:8001/foxglove_viewer.html
```
✅ Real-time 3D point clouds  
✅ Interactive orbit/pan/zoom controls  
✅ Multiple view modes (Ego, Top-Down, Follow)  
✅ Toggle sensors on/off  

### or Foxglove Web (Professional):
```
https://app.foxglove.dev/
→ Connection: ws://localhost:8766
```
✅ Advanced multi-panel layouts  
✅ Data recording (MCAP format)  
✅ Time series plotting  
✅ Professional UI  

## 📊 What You'll See

- 🟨 **Yellow cube** = Your ego vehicle
- 🔵 **Blue cubes** = Other vehicles
- ☁️ **Cyan points** = LIDAR point cloud
- 💜 **Magenta dots** = RADAR detections
- 📷 **Camera feed** = RGB camera view

## 📁 What Was Created

| File | Purpose |
|------|---------|
| `foxglove_server.py` | WebSocket server (streams sensor data) |
| `foxglove.html` | Gateway page with options |
| `foxglove_viewer.html` | Custom 3D viewer (Three.js) |
| `start_foxglove.py` | HTTP server + browser opener |
| `START_FOXGLOVE.bat` | Windows one-click launcher |
| `FOXGLOVE_GUIDE.md` | Complete setup guide |
| `FOXGLOVE_SETUP_SUMMARY.md` | Detailed overview |
| `foxglove_cheatsheet.py` | Quick reference (run to view) |

## 🎮 Controls

### Mouse:
- **Left Click + Drag** = Rotate camera
- **Right Click + Drag** = Pan
- **Scroll** = Zoom
- **Space** = Reset view

### Keyboard:
- **V** = Cycle view modes
- **C** = Toggle camera
- **L** = Toggle LIDAR
- **R** = Toggle RADAR
- **G** = Toggle grid

### View Modes:
1. **Orbit** - Free rotation (default)
2. **Ego** - First-person from vehicle
3. **Top-Down** - Bird's eye view
4. **Follow** - Camera follows from behind

## 📡 Data Topics Streamed

| Topic | Type | Update Rate |
|-------|------|-------------|
| `/camera/rgb` | JPEG Image | 20 Hz |
| `/lidar/points` | Point Cloud | 20 Hz |
| `/radar/markers` | 3D Markers | 20 Hz |
| `/ego_pose` | Position + Rotation | 20 Hz |
| `/vehicles/markers` | Vehicle Poses | 20 Hz |

## 🔍 Before You Start

**Make sure you have:**
- ✅ CARLA simulator installed
- ✅ Python 3.8+
- ✅ Required packages: `websockets`, `numpy`, `opencv-python`, `tensorflow`

**Check dependencies:**
```bash
python verify_components.py
```

**Install missing packages:**
```bash
pip install -r requirements.txt
```

## 🚀 Architecture

```
CARLA Simulator
  ↓ (Sensor data)
  ↓
foxglove_server.py (WebSocket)
  ↓ (JSON messages over ws://localhost:8766)
  ↓
Browser Visualization
  ├→ Local 3D Viewer (foxglove_viewer.html)
  └→ Foxglove Web (app.foxglove.dev)
```

## 🐛 Troubleshooting

### Nothing appears?
```bash
# Check CARLA is running
netstat -ano | findstr :2000

# Check server is running
netstat -ano | findstr :8766

# Check HTTP server is running
netstat -ano | findstr :8001
```

### Port already in use?
```bash
# Find what's using the port
netstat -ano | findstr :8766

# Kill it
taskkill /PID <PID_NUMBER> /F
```

### No point cloud visible?
- ✅ Check "☁️ LIDAR Points" is enabled
- ✅ Zoom out (use scroll wheel)
- ✅ Wait 2-3 seconds for sensors to warm up

### Camera feed not showing?
- ✅ Check "📷 Camera Feed" is enabled
- ✅ Wait for camera to initialize (1-2 seconds)
- ✅ Check browser console (F12) for errors

## 📖 Full Documentation

For detailed setup instructions and advanced configuration, see:
- **`FOXGLOVE_GUIDE.md`** - Complete setup guide
- **`FOXGLOVE_SETUP_SUMMARY.md`** - Detailed overview
- **`foxglove_cheatsheet.py`** - Quick reference (run it!)

```bash
python foxglove_cheatsheet.py
```

## 💡 Pro Tips

1. **Use both viewers:**
   - Local Viewer for quick debugging
   - Foxglove Web for professional analysis

2. **Record sessions:**
   - In Foxglove Web, click record
   - Download MCAP file for offline analysis
   - Great for presentations!

3. **Custom layouts:**
   - Save your favorite view configurations in Foxglove Web
   - Share layouts with team members

4. **Performance tuning:**
   - Reduce point cloud density for better performance
   - Lower camera resolution in CARLA
   - Disable sensors you don't need

5. **Keyboard shortcuts:**
   - Press `?` in Foxglove Web for more help
   - Space resets camera in Local Viewer

## 🎓 Next Steps

1. ✅ Get it running with `START_FOXGLOVE.bat`
2. ✅ Explore the 3D viewer with mouse controls
3. ✅ Try different view modes (dropdown)
4. ✅ Toggle sensors on/off
5. ✅ Connect to Foxglove Web for advanced features
6. ✅ Read guides for customization

## 📞 Support

### Common Issues:

| Problem | Solution |
|---------|----------|
| Can't connect | Check CARLA running on :2000 |
| Port conflict | Kill process: `taskkill /PID X /F` |
| No data | Wait 2-3 sec, check console output |
| Slow performance | Reduce point cloud, lower update rate |
| Camera not showing | Enable camera checkbox, wait for init |

### Debug Mode:

```bash
# Run server with more logging
python -u foxglove_server.py

# Check browser console
Press F12 → Console tab
```

## 🚗 Real-World Usage

This setup is perfect for:
- ✅ **Real-time perception debugging** - See what your car sees
- ✅ **Algorithm testing** - Visualize LIDAR/RADAR processing
- ✅ **Educational demos** - Show autonomous driving concepts
- ✅ **Research** - Record and analyze sensor data
- ✅ **Presentations** - Professional visualization

## 📊 Performance

### Current Configuration:
- Update rate: **20 Hz** (50ms latency)
- Point cloud: **~50,000 points/frame**
- Camera: **640x480 JPEG**
- Network: **WebSocket on localhost**

### Estimated Performance:
- **FPS**: 20-30 (depending on GPU)
- **Memory**: 500-800 MB for all components
- **CPU**: 10-15% (CARLA), 5-10% (server)

## 🎉 You're Ready!

Everything is set up. Just run:

```bash
START_FOXGLOVE.bat
```

Or manually start the three components and visit:
```
http://localhost:8001/foxglove_viewer.html
```

**Happy visualizing! 🚗✨**

---

<details>
<summary><b>Advanced Configuration</b></summary>

### Change WebSocket Port:
Edit `foxglove_server.py`:
```python
FOXGLOVE_WS_PORT = 8766  # Change this
```

### Change Update Rate:
Edit `foxglove_server.py`:
```python
await asyncio.sleep(0.05)  # 20 Hz (current)
await asyncio.sleep(0.033) # ~30 Hz (faster)
```

### Reduce Point Cloud Density:
Edit `foxglove_server.py` in `lidar_callback`:
```python
# Skip every 2nd point
sensor_data['lidar_points'] = points[::2, :3].tolist()
```

### Add Custom Sensors:
Follow the pattern in `foxglove_server.py` and add new callbacks.

</details>

---

**Created:** February 2026  
**Version:** 1.0  
**Compatibility:** CARLA 0.9.13+, Python 3.8+
