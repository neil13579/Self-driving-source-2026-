# 🚀 Next Steps - Complete Verification & Testing Guide

## What's New

Your perception system now has:
- ✅ **Intelligent actor spawning** with collision avoidance
- ✅ **Mixed movement states** (50% moving vehicles, 50% stationary; 50% walking pedestrians, 50% idle)
- ✅ **Comprehensive diagnostic checkpoints** at every critical step
- ✅ **Component verification tool** to check system health
- ✅ **Real-time console monitor** with color-coded output
- ✅ **Detailed troubleshooting guide** for quick problem resolution

---

## Phase 1: Pre-Flight Check (5 minutes)

### Step 1.1: Verify All Components

Run the component checker to ensure everything is installed and configured:

```bash
python verify_components.py
```

**What to look for:**
- ✅ Python 3.7+
- ✅ All required packages (carla, tensorflow, opencv, flask, websockets)
- ✅ CARLA server running on localhost:2000
- ✅ Both ports free (5000 for Flask, 8765 for WebSocket)
- ✅ All required files present

**If something is ❌:**
- Missing packages: `pip install -r requirements.txt`
- CARLA not running: Start CARLA simulator
- Port in use: Kill process using that port

### Step 1.2: Check Configuration

Verify `config/general_config.json` has proper settings:

```json
{
  "carla_host": "localhost",
  "carla_port": 2000,
  "num_vehicles": 30,
  "num_pedestrians": 30,
  "ego_autopilot": true,
  "perception": {
    "enable_segmentation": true,
    "enable_detection": true
  }
}
```

---

## Phase 2: First Run (10 minutes)

### Step 2.1: Start Server with Colored Monitor

This monitors the server output and color-codes all diagnostic messages:

```bash
python monitor_server.py
```

**Console should show (in order):**

1. **Startup Phase** [INIT-1 to INIT-4]
   ```
   [INIT-1] Initializing CARLA integration...
   [INIT-2] ✓ Connected to CARLA on localhost:2000
   [CHECKPOINT 1] Starting traffic setup...
   ```
   - WAIT: System connecting to CARLA
   - Expected time: 3-5 seconds

2. **Actor Spawning Phase** [CHECKPOINT 3-10]
   ```
   [CHECKPOINT 3] Using XX spaced spawn points
   [CHECKPOINT 6] Spawning 30 vehicles (50% moving, 50% stationary)...
   [PROGRESS] Spawned 10 vehicles...
   [PROGRESS] Spawned 20 vehicles...
   [CHECKPOINT 7] Spawned XX moving vehicles + YY stationary
   ```
   - INFO: Shows collision statistics
   - Expected: 25-30 vehicles (some may fail due to collision detection)
   - Expected time: 5-10 seconds

3. **Sensor Phase** [INIT-5 to INIT-6]
   ```
   [INIT-5] Attaching sensors...
   [INIT-6] ✓ Sensors attached (Camera, LIDAR, RADAR)
   ```
   - Expected time: 1-2 seconds

4. **Model Phase** [INIT-7 to INIT-8]
   ```
   [INIT-7] Initializing perception pipeline...
   [INIT-8] ✓ U-Net and YOLO models loaded
   ```
   - INFO: Loading TensorFlow models
   - Expected time: 5-10 seconds (first load will be slower)

5. **WebSocket Phase** [INIT-9 to INIT-12]
   ```
   [INIT-9] Creating WebSocket event loop...
   [INIT-10] ✓ Event loop created
   [WS-READY] WebSocket server ready...
   [INIT-12] ✓ WebSocket server listening on ws://localhost:8765
   ```
   - Expected time: 1-2 seconds

6. **Processing/Flask Phase** [INIT-13 to INIT-16]
   ```
   [INIT-13] Starting frame processing thread...
   [PROC-START] Frame processing thread started
   =======================================================
     DASHBOARD: http://localhost:5000
     WebSocket: ws://localhost:8765
   =======================================================
   [INIT-16] Starting Flask server...
   ```
   - First frame processing: `[PROC-1]` with FPS
   - Expected time: 2-3 seconds

**Total startup:** 15-30 seconds until dashboard is ready

### Step 2.2: Open Dashboard in Browser

Once you see this line:
```
[INIT-16] Starting Flask server...
```

Open browser to: **http://localhost:5000**

### Step 2.3: Monitor Ongoing Operation

Watch the console for these patterns:

- **Frame Processing** (you should see this repeatedly):
  ```
  [PROC-30] 25 FPS | WS: 1 clients
  [FRAME-30] Vehicle: 4 | Pedestrian: 2 | Traffic: 1
  [BROADCAST-OK-30] Sent 1234 KB
  ```
  - Appears once per second
  - FPS should be 20-30
  - Shows active WebSocket clients

- **Browser Connection** (when dashboard loads):
  ```
  [WS-CONNECT] Client 1 connected | Total: 1
  [BROADCAST-OK-1] Sent to 1 client(s)
  ```
  - Appears once when you open dashboard
  - Should then show [BROADCAST-OK-N] every second

- **No WebSocket Clients** (problem indicator):
  ```
  [NO-CLIENTS-30] No clients connected yet
  ```
  - Means dashboard is open but JavaScript isn't connecting to WebSocket
  - Check browser console for errors (F12)

---

## Phase 3: Validation (5 minutes)

### Check 1: Dashboard Visual Elements

| Element | Expected | How to Verify |
|---------|----------|---------------|
| Title & Info | "CARLA Real-Time Perception Fusion System" | Appears at top |
| Live Feed | Video from camera updating | Should change frame-by-frame |
| Detection Boxes | Green (vehicles), Red (pedestrians) | Should see boxes around objects |
| LIDAR Points | Blue dots/cloud | Should shift as camera moves |
| RADAR Circles | Orange rings | Should show distance to objects |
| FPS Counter | 20-30 | Updates every second |
| Connection Status | "Connected" (green) | Shows WebSocket status |

### Check 2: Data Flow in Console

Look for continuous flow of:
```
[PROC-N] XX FPS | WS: 1 clients
[FRAME-N] Vehicle: X | Pedestrian: Y
[BROADCAST-OK-N] Sent XXXX KB
```

All three should appear in sequence, repeatedly.

### Check 3: CARLA Window

- Ego vehicle should be visible
- Other vehicles visible moving around (50% moving, 50% parked)
- Pedestrians walking around
- No excessive collisions (some OK due to detection)

### Check 4: Actor Movement Validation

In console, after actor spawning, look for:
```
[CHECKPOINT 7] Spawned 15 moving vehicles + 15 stationary
[CHECKPOINT 9] Spawned 15 walking pedestrians + 15 idle
```

Verify counts are approximately 50/50 for each category.

---

## Phase 4: Troubleshooting (if needed)

### Problem 1: Dashboard Won't Load (http://localhost:5000)

**Console Checks:**
1. Do you see `[INIT-16] Starting Flask server...`?
2. Do you see `[FLASK-HOME]` messages appearing?

**Solution:**
- If `[INIT-16]` exists → Flask is running
- If `[INIT-16]` missing → Flask crashed
  - Stop server (Ctrl+C)
  - Look for red [ERROR] messages above
  - Fix error, retry

### Problem 2: Dashboard Loads but No Video

**Console Checks:**
1. Do you see `[WS-CONNECT]` in console?
2. Do you see `[BROADCAST-OK-N]` messages?

**If [WS-CONNECT] exists + [BROADCAST-OK-N] exists:**
- Problem is browser JavaScript
- Open browser console (F12)
- Look for JavaScript errors
- Check if canvas element is present

**If [NO-CLIENTS-N] repeating instead:**
- JavaScript can't connect to WebSocket
- Browser console should show: `WebSocket connection failed`
- Try: Hard refresh (Ctrl+Shift+R)

### Problem 3: Low Frame Rate (FPS < 15)

**Solution:**
1. Disable debug output:
   - Edit `unified_perception_server.py`
   - Change `logging.basicConfig(level=logging.INFO)` to `logging.WARNING`
2. Run with minimal logging:
   ```bash
   set TF_ENABLE_ONEDNN_OPTS=0
   python monitor_server.py
   ```

### Problem 4: Cars Are Colliding During Spawn

**Check Console For:**
```
[CHECKPOINT 3] Using XX spaced spawn points (out of YY available)
[CHECKPOINT 7] Spawned xx vehicles (ZZ failed due to collision)
```

**Explanation:**
- Spacing factor automatically reduces spawn points to avoid collisions
- Some failures are normal and expected
- If < 20 vehicles spawned, increase `"num_vehicles": 50` in config

### Problem 5: WebSocket Disconnects Immediately

**Symptom:**
```
[WS-CONNECT] Client 1 connected | Total: 1
[WS-DISCONNECT] Client disconnected | Total: 0
```

**Cause:** Browser JavaScript error

**Fix:**
1. Open browser console (F12)
2. Look for JavaScript errors
3. Try different browser (Chrome/Firefox/Edge)

---

## Phase 5: Performance Tips

### To Get Maximum FPS:
1. Reduce vehicle count in config: `"num_vehicles": 15`
2. Disable non-essential sensors
3. Run on system with NVIDIA GPU (uses CUDA)

### To Get Maximum Sensor Data:
1. Increase resolution in U-Net model
2. Increase LIDAR point count
3. Less reduction in broadcast intervals

### To Reduce Network Load:
1. Reduce image compression (higher quality = slower)
2. Increase broadcast interval: `max(1, 30 // 10)` → `max(1, 30 // 30)`
3. Disable LIDAR visualization in dashboard

---

## Complete Verification Checklist

Once Phase 1-2 complete, go through this:

- [ ] **Component Verification**
  - [ ] All imports successful
  - [ ] CARLA connecting
  - [ ] Ports free
  - [ ] Files present

- [ ] **Startup Sequence** (check console)
  - [ ] [INIT-1] → [INIT-4] CARLA connected
  - [ ] [CHECKPOINT 6] → [CHECKPOINT 10] Actors spawned
  - [ ] [INIT-7] → [INIT-8] Models loaded
  - [ ] [INIT-9] → [INIT-12] WebSocket ready
  - [ ] [INIT-16] Flask started

- [ ] **Runtime Checking**
  - [ ] [PROC-N] appears every 1-2 seconds
  - [ ] [FRAME-N] shows detection counts
  - [ ] [BROADCAST-OK-N] confirms data sending
  - [ ] FPS reading shows 15+

- [ ] **Dashboard Validation**
  - [ ] Loads without errors at http://localhost:5000
  - [ ] Video feed visible and updating
  - [ ] Connection status shows "Connected"
  - [ ] Detection boxes visible (green/red)

- [ ] **Actor Validation** (in CARLA window)
  - [ ] Ego vehicle visible
  - [ ] 25-30 other vehicles visible
  - [ ] Some vehicles moving, some stationary
  - [ ] 20+ pedestrians visible

If all ✓ → **SYSTEM FULLY OPERATIONAL** 🎉

---

## Quick Reference Commands

```bash
# Component check
python verify_components.py

# Run with colored diagnostic output
python monitor_server.py

# Run without monitor
python unified_perception_server.py

# Open dashboard
# In browser: http://localhost:5000

# View WebSocket in browser console
# Press F12, go to Console tab, paste:
# const ws = new WebSocket('ws://localhost:8765');
# ws.onmessage = m => console.log(m.data.length, 'bytes');
```

---

## Getting Help

When you need help, provide:
1. **Console output** (copy first 20 lines after startup)
2. **Which phase fails** (startup, actor spawn, etc.)
3. **What you see in console** (checkpoint numbers)
4. **What you see in browser** (dashboard loaded? video feed?)
5. **Browser console errors** (F12, Console tab)

With these details, debugging is fast! 🔍

---

## Success Indicators

✅ **System is working if:**
- Console shows [INIT-16]
- Dashboard opens at http://localhost:5000
- [WS-CONNECT] appears in console
- [PROC-N] messages every 1-2 seconds
- [BROADCAST-OK-N] messages every 1-2 seconds
- Video is updating in dashboard
- FPS > 15

✅ **Actors spawned correctly if:**
- ~25-30 vehicles visible in CARLA
- ~20-25 pedestrians visible in CARLA
- Some vehicles are moving, some parked
- Some pedestrians walking, some idle
- No warning messages about collisions

---

Now you're ready! Start with `python verify_components.py` 🚀

