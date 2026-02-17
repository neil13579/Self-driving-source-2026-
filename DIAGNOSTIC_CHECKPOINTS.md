# 🔍 Diagnostic Checkpoint Guide

## Connection Troubleshooting - Read the Console Carefully!

The system now has detailed checkpoints at every critical step. Follow this guide to debug where the connection is being severed.

---

## Expected Console Output (In Order)

### Phase 1: Startup
```
[START] Unified Perception Server Startup
[INIT-1] Initializing CARLA integration...
[INIT-2] ✓ Connected to CARLA on localhost:2000
[CHECKPOINT 1] Starting traffic setup...
[CHECKPOINT 2] Found XX spawn points on map
[CHECKPOINT 3] Using YY spaced spawn points to avoid collisions
[CHECKPOINT 4] Spawning ego vehicle...
[CHECKPOINT 5] Ego vehicle spawned with autopilot
[CHECKPOINT 6] Spawning 30 vehicles (50% moving, 50% stationary)...
[PROGRESS] Spawned 10 vehicles...
[PROGRESS] Spawned 20 vehicles...
[CHECKPOINT 7] Spawned XX moving vehicles + YY stationary
[CHECKPOINT 8] Spawning 30 pedestrians (50% moving, 50% idle)...
[CHECKPOINT 9] Spawned XX walking pedestrians + YY idle
[CHECKPOINT 10] Traffic setup complete
[INIT-4] ✓ Traffic setup complete
[INIT-5] Attaching sensors to ego vehicle...
[INIT-6] ✓ Sensors attached (Camera, LIDAR, RADAR)
[INIT-7] Initializing perception pipeline...
[INIT-8] ✓ U-Net and YOLO models loaded
[INIT-9] Creating WebSocket event loop...
[INIT-10] ✓ Event loop created
[INIT-11] Starting WebSocket thread...
[WS-START] WebSocket event loop starting...
[WS-READY] WebSocket server ready, starting event loop...
[INIT-12] ✓ WebSocket server listening on ws://localhost:8765
[INIT-13] Starting frame processing thread...
[PROC-START] Frame processing thread started
[INIT-14] ✓ Frame processing thread started
=======================================================
  DASHBOARD: http://localhost:5000
  WebSocket: ws://localhost:8765
=======================================================
[INIT-16] Starting Flask server...
```

---

## Checkpoint Legend

### Startup Checkpoints
- **[INIT-1]** to **[INIT-4]**: CARLA connection and traffic setup
- **[INIT-5]** to **[INIT-6]**: Sensor attachment (Camera, LIDAR, RADAR)
- **[INIT-7]** to **[INIT-8]**: Model loading (U-Net, YOLO)
- **[INIT-9]** to **[INIT-10]**: WebSocket setup
- **[INIT-11]** to **[INIT-12]**: WebSocket thread start
- **[INIT-13]** to **[INIT-16]**: Processing thread and Flask startup

### Traffic Checkpoints
- **[CHECKPOINT 1-3]**: Spawn point analysis
- **[CHECKPOINT 4-5]**: Ego vehicle spawning
- **[CHECKPOINT 6-7]**: Vehicle spawning (50% moving, 50% stationary)
- **[CHECKPOINT 8-10]**: Pedestrian spawning (50% moving, 50% idle)
- **[PROGRESS]**: Incremental progress (every 10 actors)

### Runtime Checkpoints
- **[PROC-N]**: Running frame count with FPS and WS client count
- **[FRAME-N]**: Frame processed with detection count
- **[ENCODE-N]**: Image encoding size in KB
- **[MESSAGE-N]**: Full message size before sending
- **[BROADCAST-N]**: Broadcasting attempt
- **[BROADCAST-OK-N]**: Successful broadcast
- **[BROADCAST-ERROR-N]**: Broadcast failure
- **[NO-CLIENTS-N]**: No WebSocket clients connected yet
- **[NULL-FRAME-N]**: Camera returned null frame

### WebSocket Checkpoints
- **[WS-CONNECT]**: Client connected, total count
- **[WS-DISCONNECT]**: Client disconnected, total count
- **[WS-BROADCAST]**: Broadcasting to N clients
- **[WS-NO-CLIENTS]**: No clients to send to

### Flask Checkpoints
- **[FLASK-HOME]**: Dashboard page requested
- **[FLASK-FRAME]**: Frame API called
- **[FLASK-FRAME-OK]**: Frame returned
- **[FLASK-FRAME-EMPTY]**: No frame available
- **[FLASK-HEALTH]**: Health check API called

---

## Troubleshooting Matrix

### Problem: Dashboard won't load at localhost:5000

**Check Console For:**
- `[INIT-16]` present? → Flask should be running
- `[FLASK-HOME]` appearing? → Flask is receiving requests
- If missing → Flask crashed, check error before it

**Action:** Stop server, look for error messages in red/orange

---

### Problem: Dashboard loads but no video feed

**Check Console For:**
1. `[PROC-START]` present? → Frame processing running
2. `[FRAME-N]` appearing? → Frames being captured from CARLA
3. `[ENCODE-N]` appearing? → Images being encoded
4. `[MESSAGE-N]` appearing? → Messages being built
5. `[WS-CONNECT]` appearing? → WebSocket connected from browser
6. `[BROADCAST-OK-N]` appearing? → Data being sent to browser
7. `[NO-CLIENTS-N]` repeating? → Browser not connecting to WebSocket!

**If you see [NO-CLIENTS-N] repeatedly:**
- Browser JS is having trouble connecting to WebSocket
- Check browser console (F12 → Console tab)
- Look for WebSocket connection errors

**Action:**
```javascript
// Open browser console (F12) and paste:
const ws = new WebSocket('ws://localhost:8765');
ws.onopen = () => console.log('WebSocket connected!');
ws.onerror = (e) => console.log('WebSocket error:', e);
```

---

### Problem: Actors colliding with each other

**Check Console For:**
- `[CHECKPOINT 3]` value - should be spacing vehicles
- `[PROGRESS]` counts - if only 10/30 vehicles spawned, collisions prevented it
- Look for the actual spawn counts in `[CHECKPOINT 7]` and `[CHECKPOINT 9]`

**Expected Values:**
- Should spawn 25-30 vehicles (collision avoidance is working)
- Should spawn 25-28 pedestrians
- 50% of each should be moving, 50% stationary

**Action:** If vehicles < 20, collision detection is blocking spawns (working as intended)

---

### Problem: Low FPS (below 20)

**Check Console For:**
- FPS value in `[PROC-N]` messages
- `[BROADCAST-ERROR-N]` messages - if WebSocket is slow

**If FPS shows <20:**
- Reduce CPU load by disabling debug logging
- Or disable some sensors

**Action:** Add this environment variable:
```bash
set TF_ENABLE_ONEDNN_OPTS=0
python unified_perception_server.py
```

---

### Problem: WebSocket never connects from browser

**Check Console For:**
1. `[WS-START]` message? → WebSocket thread started
2. `[WS-READY]` message? → Server ready
3. `[WS-CONNECT]` appearing when you open browser? → Client tried to connect

**If [WS-CONNECT] never appears:**
- Open browser console (F12)
- Look for JavaScript errors
- Check if WebSocket URL is correct: `ws://localhost:8765`

**If [WS-CONNECT] appears immediately then [WS-DISCONNECT]:**
- Connection established but dropped immediately
- Likely a browser-side error
- Check browser console for errors

**Action:** Manually test with Python:
```python
import websockets
import asyncio

async def test():
    async with websockets.connect('ws://localhost:8765') as ws:
        await ws.send("test")
        msg = await ws.recv()
        print(f"Received: {msg}")

asyncio.run(test())
```

---

### Problem: CARLA not sending frames

**Check Console For:**
- `[PROC-N]` messages appearing? → Processing thread running
- `[FRAME-N]` appearing? → Frames being processed
- `[NULL-FRAME-N]` appearing repeatedly? → Camera not returning data

**If [NULL-FRAME-N] repeating:**
- Camera sensor not attached
- Or CARLA not sending data
- Check if `[INIT-6]` shows sensors attached

**Action:**
1. Restart CARLA
2. Make sure ego vehicle is visible in CARLA window
3. Verify camera is on ego vehicle

---

## Quick Diagnostic Checklist

Run through this to find the problem:

- [ ] Server starts without `[ERROR]` messages?
- [ ] All `[INIT-1]` through `[INIT-16]` checkpoints appear?
- [ ] Dashboard loads at `http://localhost:5000`?
- [ ] Browser console (F12) shows no red errors?
- [ ] `[WS-CONNECT]` appears in server console when browser opens?
- [ ] `[PROC-N]` and `[FRAME-N]` messages appearing regularly?
- [ ] `[BROADCAST-OK-N]` messages (not `[BROADCAST-ERROR-N]`)?
- [ ] Vehicles visible in CARLA window?
- [ ] About 25-30 vehicles spawned (not 30 - some collision failures OK)?
- [ ] About 25 pedestrians spawned?
- [ ] Video in dashboard updating periodically?
- [ ] FPS counter > 20?

If all checked ✓ → System working!

---

## Console Log Levels

To see MORE debug messages (very verbose):
```python
# In unified_perception_server.py, line ~31:
logging.basicConfig(level=logging.DEBUG)  # Change from INFO
```

To see LESS messages:
```python
logging.basicConfig(level=logging.WARNING)
```

---

## Sample Debug Session

When reporting issues, include this:

```
1. Server startup output (all [INIT] messages)
2. First 10 [PROC] messages
3. Do you see [WS-CONNECT] in console?
4. Do you see [FLASK-HOME] in console?
5. Browser console errors (F12)
6. Actual error messages (red text in console)
```

With those details, I can quickly identify the problem!

---

## Key Indicators

| What You See | Status | What To Do |
|-------------|--------|-----------|
| All [INIT] → [INIT-16] | ✅ Good | Continue to browser |
| [PROC-N] every second | ✅ Good | System running |
| [WS-CONNECT] | ✅ Good | Browser connected |
| [BROADCAST-OK-N] | ✅ Good | Data flowing |
| Video in dashboard | ✅ Good | **WORKING!** |
| Missing [INIT-X] | ❌ Error | Check red messages |
| [BROADCAST-ERROR-N] | ⚠️ Warning | WebSocket issue |
| [NO-CLIENTS-N] only | ⚠️ Warning | Browser not connected |
| No [PROC-N] | ❌ Error | Camera/processing issue |

---

**Remember:** Check the console output first - that's where all the clues are! 🔍

