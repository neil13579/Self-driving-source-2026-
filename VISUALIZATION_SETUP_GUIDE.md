# 🔧 CARLA Visualization Troubleshooting & Setup Guide

## ✅ FIXES APPLIED

### 1. **HTML Visualization Enhanced** (`index.html`)
- ✅ Added detailed console logging for WebSocket connection
- ✅ Made ego vehicle **2x larger** and **bright yellow** with white border for visibility
- ✅ Added grid reference lines for spatial orientation
- ✅ Added direction indicator arrow pointing forward
- ✅ Improved error handling for image loading
- ✅ Better structured data validation and drawing order

### 2. **main.py Improvements**
- ✅ Added ego vehicle physics enablement: `set_simulate_physics(True)`
- ✅ Added spawn point validation
- ✅ Added sensor attachment validation with detailed logging
- ✅ Added WebSocket frame counting and periodic status updates
- ✅ Added detailed error messages and exception handling
- ✅ Improved cleanup routine

### 3. **HTTP Server Created** (`serve_web.py`)
- ✅ New simple HTTP server to properly serve HTML/JS files
- ✅ Fixes CORS issues when opening HTML directly
- ✅ Better logging of HTTP requests

---

## 🚀 HOW TO RUN

### Step 1: Start CARLA Simulator
```bash
CarlaUE4.exe -windowed -carla-port=2000
```
(Make sure it's listening on localhost:2000)

### Step 2: Start the Perception Server (Terminal 1)
```bash
cd c:\Users\Priyanshu Verma\OneDrive\Documents\Carla_SEAL
python main.py
```

**Expected output:**
```
============================================================
🎮 CARLA UKF Perception System
============================================================
Connecting to CARLA at localhost:2000...

✅ Ego vehicle spawned at (x, y, z)
✅ RGB Camera attached
✅ Segmentation Camera attached
✅ LIDAR attached
✅ RADAR attached

🚀 Starting WebSocket server on ws://localhost:8765
📱 Open http://localhost/ in your browser to view visualization
============================================================
✅ WebSocket server ready! Waiting for connections...
```

### Step 3: Start HTTP Server (Terminal 2)
```bash
cd c:\Users\Priyanshu Verma\OneDrive\Documents\Carla_SEAL
python serve_web.py
```

**Expected output:**
```
============================================================
🌐 HTTP Server Started
============================================================
📍 URL: http://localhost:8000
📄 Serving files from: c:\Users\Priyanshu Verma\OneDrive\Documents\Carla_SEAL
...
```

### Step 4: Open Browser
```
Navigate to: http://localhost:8000/index.html
```

---

## 🔍 WHAT YOU SHOULD SEE

### Dashboard with 4 Panels:
1. **RGB Camera + Boxes** - Live camera feed with green bounding boxes around actors
2. **TensorFlow Segmentation** - Semantic segmentation mask
3. **Sensor Fusion (Lidar+Radar+UKF)** - Top-down view with:
   - 🟨 **Yellow Rectangle** = Your Ego Vehicle (center-bottom)
   - ⚪ **White Arrow** = Direction you're facing
   - 🔵 **Cyan Dots** = LIDAR points (front)
   - 🟣 **Magenta Circles** = RADAR detections
   - 🟢 **Green Circle** = UKF Tracking Estimate
4. **Stats Panel** - Shows connection status and actor count

---

## 🐛 DEBUGGING CHECKLIST

### Browser Console (Press F12)
```javascript
// You should see:
✅ WebSocket Connected!
📊 Message #1 received
✅ RGB image loaded
✅ Segmentation image loaded
✅ Ego vehicle drawn at (320, 430)
✅ Drew 50 LIDAR points
✅ Drew 5 RADAR points
```

### If Connection Shows But No Ego Vehicle:

**Check 1: WebSocket Messages**
- Open Browser DevTools (F12)
- Go to Console tab
- Look for "Message #X received" messages
- If you see this, data IS flowing

**Check 2: Canvas Drawing**
- In console, check for "Ego vehicle drawn at (X, Y)"
- The coordinates should be roughly (320, 430)

**Check 3: Data Structure**
- In console, check for "Missing image data" warnings
- This would indicate RGB or segmentation data is missing

### If WebSocket Won't Connect:

**Check 1: Port 8765 is free**
```powershell
netstat -ano | findstr :8765
```
If something is using it, kill it:
```powershell
taskkill /PID <PID_NUMBER> /F
```

**Check 2: Firewall**
- Windows Defender Firewall might block Python WebSocket
- Allow python.exe through firewall, or disable for localhost

**Check 3: main.py is running**
- See console output from main.py
- Should show "WebSocket server ready!" message

---

## 📊 EXPECTED SENSOR DATA

### RGB Camera
- Resolution: 640x480
- Refreshed every 50ms (20 FPS)
- Should show road, sky, traffic

### LIDAR
- Range: 50 meters
- Should see cyan dots scattered around
- More dense closer to ego vehicle

### Radar 
- Should show magenta circles
- Usually only detects moving vehicles
- More sparse than LIDAR

### Segmentation
- 13 classes (road, car, pedestrian, etc.)
- Color-coded output from TensorFlow

---

## 🎯 COMMON ISSUES & FIXES

| Issue | Solution |
|-------|----------|
| **Connection shows but no data** | Check CARLA is running, check ports 2000, 8765, 8000 |
| **Ego vehicle not visible** | Check console for "Ego vehicle drawn at X, Y" - should see yellow rect |
| **Images not loading** | Check browser console for image load errors, clear cache (Ctrl+F5) |
| **LIDAR/Radar points not visible** | Check sensor data in console: "Drew X points" |
| **Port already in use** | Use `netstat -ano \| findstr :PORT` to find and kill |
| **White screen** | Open DevTools (F12), check Console tab for errors |

---

## 📋 SYSTEM REQUIREMENTS

- Python 3.8+
- CARLA 0.9.13+
- websockets library: `pip install websockets`
- OpenCV: `pip install opencv-python`
- TensorFlow: `pip install tensorflow`

Check with:
```bash
python verify_components.py
```

---

## 📞 ADVANCED DEBUGGING

### Enable maximum logging:
Edit `main.py` and uncomment debug lines, or add:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check WebSocket traffic (external tool):
```bash
wscat -c ws://localhost:8765
```

### Monitor network:
```powershell
netstat -ab | findstr python
```

---

## ✨ Next Steps

If everything is working:
1. Ego vehicle should appear as **yellow rectangle at bottom-center**
2. As you drive around CARLA, it should move through the scene
3. LIDAR should light up with cyan dots
4. RADAR should show magenta circles for vehicles ahead
5. Bounding boxes should appear in RGB cam for tracked objects

**Happy debugging! 🚀**
