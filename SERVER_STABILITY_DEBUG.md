# 🔍 Server Stability Debugging Guide

## "Server Stopped By Itself" - Root Cause Analysis

### Why it Happens

Your server has 3 main threads:
1. **Main Thread** - Keeps server alive (sleeps)
2. **WebSocket Thread** - Broadcasts data to browser
3. **Processing Thread** - Gets frames from CARLA and processes them

If ANY of these threads crash silently, the server might appear to stop.

---

## Step 1: Identify What Stopped

Run this to see detailed console output:

```bash
python monitor_server.py
```

**Watch the console carefully.** Look for any of these:

### Sign 1: Red Error Messages
```
[ERROR-1] Failed to connect to CARLA
[PROC-ERROR] Processing error: ...
[BROADCAST-ERROR] Broadcast failed: ...
[SERVER-ERROR] ...
```

### Sign 2: Last Message Before Stop
```
[PROC-30] FPS: 25.3 | WS Clients: 1
[BROADCAST-OK-30] Message sent successfully
[END] Server stopped              ← This means clean exit
```
vs
```
[PROC-60] FPS: 28.1 | WS Clients: 1
[EXPECTED NEXT MESSAGE MISSING]  ← Server crashed!
```

### Sign 3: Yellow Warnings (Non-fatal)
```
[NULL-FRAME-60] Received null image
[BROADCAST-ERROR-60] Broadcast failed: ...
[NO-CLIENTS-60] No WS clients connected
```

---

## Step 2: Common Causes & Solutions

### Cause 1: CARLA Disconnected

**Symptoms:**
```
[NULL-FRAME-30] Received null image
[NULL-FRAME-31] Received null image
[PROC-ERROR] ...
```

**Solution:**
1. Make sure CARLA is **still running** when you start server
2. In another terminal, verify CARLA:
   ```bash
   python check_system.py
   ```
3. Should see:
   ```
   ✓ CARLA Server: Running
   ✓ Port 2000: Open
   ```

### Cause 2: Python Module Missing

**Symptoms:**
```
ModuleNotFoundError: No module named 'tensorflow'
ImportError: No module named 'websockets'
```

**Solution:**
```bash
# Install missing packages
pip install tensorflow==2.10.0
pip install websockets
pip install opencv-python
pip install numpy
```

### Cause 3: Memory Exhaustion

**Symptoms:**
- Server runs fine for 5-10 minutes, then stops
- No error messages
- System is very slow

**Solution:**
1. Free up RAM before starting:
   ```bash
   taskkill /F /IM python.exe  # Close other Python apps
   taskkill /F /IM chrome.exe  # Close Chrome (if open)
   ```
2. Or reduce frame rate in server:
   ```python
   time.sleep(0.066)  # ~15 FPS instead of 30
   ```

### Cause 4: Browser Disconnected

**Symptoms:**
```
[NO-CLIENTS-60] No WS clients connected (waiting...)
[PROC-ERROR] ...
```

**Solution:**
1. Browser might have crashed
2. Refresh browser: **Ctrl+R**
3. Or reopen dashboard.html

### Cause 5: CARLA Timeout

**Symptoms:**
- Server starts but gets stuck
- No [PROC-N] messages appear
- No [BROADCAST-OK-N] messages

**Solution:**
```bash
# Restart CARLA completely
# 1. Close CARLA window
# 2. Close Python server (Ctrl+C)
# 3. Wait 5 seconds
# 4. Start fresh
python monitor_server.py
```

---

## Step 3: Enhanced Error Logging

To see MORE detailed logs, edit [unified_perception_server.py](unified_perception_server.py) and change line ~30 from:

```python
logging_level = logging.INFO  # Current
```

to:

```python
logging_level = logging.DEBUG  # More detailed
```

Then restart server:
```bash
python monitor_server.py
```

You'll now see:
```
[DEBUG] [FRAME-1] Processed frame with 3 detections
[DEBUG] [ENCODE-1] RGB encoded: 45KB
[DEBUG] [MESSAGE-1] Message size: 850KB
```

---

## Step 4: Check Thread Health

Add this diagnostic script to see if threads are running:

Create file: `check_threads.py`
```python
import subprocess
import time

while True:
    # Check if unified_perception_server process exists
    result = subprocess.run(
        'tasklist | find "python.exe"',
        shell=True, 
        capture_output=True, 
        text=True
    )
    
    if 'python' in result.stdout:
        print("✓ Server process is running")
    else:
        print("✗ Server process crashed!")
        break
    
    time.sleep(5)
```

Run in another terminal:
```bash
python check_threads.py
```

---

## Step 5: Prevent Auto-Stop Issues

### Solution A: Use monitor_server.py
```bash
python monitor_server.py
```
This script **automatically restarts** the server if it crashes.

### Solution B: Add Recovery Code
Edit `unified_perception_server.py` line ~1082, change:

```python
# Current code (in process_frames function)
except Exception as e:
    logger.error(f"[PROC-ERROR] Processing error: {str(e)[:100]}")
    time.sleep(0.1)
```

to:

```python
# Enhanced code with recovery
except KeyboardInterrupt:
    logger.info("[PROC-INTERRUPT] Manual stop signal received")
    break
except Exception as e:
    logger.error(f"[PROC-ERROR] Processing error: {str(e)[:100]}")
    logger.error(f"[PROC-STACK] {traceback.format_exc()}")  # Show full error
    time.sleep(0.1)
```

---

## Step 6: Real-Time Monitoring Dashboard

Create file: `monitor_dashboard.py`
```python
#!/usr/bin/env python3
import subprocess
import time
import os
from datetime import datetime

def get_memory_usage():
    try:
        result = subprocess.run(
            'tasklist /v | find "python.exe"',
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except:
        return "Unknown"

def get_process_status():
    try:
        result = subprocess.run(
            'tasklist | find "python.exe"',
            shell=True,
            capture_output=True,
            text=True
        )
        return "✓ Running" if "python" in result.stdout else "✗ Stopped"
    except:
        return "? Unknown"

# Auto-restart if stopped
last_status = None
while True:
    status = get_process_status()
    memory = get_memory_usage()
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    print(f"\r[{timestamp}] Server: {status} | Memory: {memory[:50]:<50}", end="", flush=True)
    
    if status == "✗ Stopped" and last_status == "✓ Running":
        print("\n[CRASH DETECTED] Restarting...")
        subprocess.Popen(["python", "monitor_server.py"])
        time.sleep(5)
    
    last_status = status
    time.sleep(2)
```

Run it:
```bash
python monitor_dashboard.py
```

---

## Step 7: Server Crash Log Analysis

After server stops, check for crash log:

```bash
# On Windows
type diagnostics_log.csv | find "ERROR"

# On Mac/Linux
grep "ERROR" diagnostics_log.csv
```

Look for patterns like:
```
ERROR | CARLA disconnection
ERROR | WebSocket crash
ERROR | Out of memory
ERROR | Timeout
```

---

## Step 8: Stress Test the Server

Create file: `stress_test.py`
```python
#!/usr/bin/env python3
import asyncio
import websockets
import json
import time

async def test_connection():
    """Stress test WebSocket with multiple connections"""
    connections = []
    
    try:
        # Create 5 simultaneous connections
        for i in range(5):
            ws = await websockets.connect('ws://localhost:8765')
            connections.append(ws)
            print(f"✓ Connection {i+1} established")
        
        # Keep connections open for 60 seconds
        print("✓ All connections active, monitoring for 60 seconds...")
        for i in range(60):
            try:
                # Try to receive data from first connection
                data = await asyncio.wait_for(
                    connections[0].recv(),
                    timeout=2.0
                )
                print(f"[{i+1}s] ✓ Data received, size: {len(data)} bytes")
            except asyncio.TimeoutError:
                print(f"[{i+1}s] ⚠ No data (timeout)")
            except Exception as e:
                print(f"[{i+1}s] ✗ Error: {str(e)[:50]}")
                break
            
            await asyncio.sleep(1)
        
        print("✓ Stress test completed successfully")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
    
    finally:
        for ws in connections:
            await ws.close()

# Run stress test
asyncio.run(test_connection())
```

Run it (while server is running):
```bash
python stress_test.py
```

---

## Troubleshooting Checklist

Before reporting an issue, verify:

- [ ] CARLA is **running** (not paused)
- [ ] CARLA is **connected** (check_system.py shows ✓)
- [ ] Server **started** without [ERROR] messages
- [ ] Dashboard **connected** (green status in top-right)
- [ ] No other Python servers running on port 8765
- [ ] At least **2GB free RAM**
- [ ] Python **3.9+** installed (check: `python --version`)
- [ ] All dependencies **installed** (pip list | grep tensorflow/websockets)

---

## What to Report

If server keeps stopping, provide:

1. **Console output** from when it stops:
   ```
   [Copy last 10 lines before server stopped]
   ```

2. **Error messages** (if any):
   ```
   [Copy any RED text]
   ```

3. **System info**:
   ```bash
   python check_system.py
   ```

4. **Memory before/after**:
   ```
   Before starting: [X]GB free
   During server: [Y]GB free
   Server still running? YES / NO
   ```

5. **Duration before crash**:
   ```
   Server lasted: [X] minutes
   ```

---

## Quick Fixes (Try These First)

### Fix 1: Restart Everything
```bash
# Close server (Ctrl+C)
# Close CARLA
# Close browser
# Wait 10 seconds
# Restart all three
python monitor_server.py
```

### Fix 2: Clear Temp Files
```bash
# Remove old caches
del __pycache__ /s
del *.pyc /s

# Restart
python monitor_server.py
```

### Fix 3: Use Minimal Mode
```bash
# Reduce complexity
# Edit unified_perception_server.py
# Change FPS from 30 to 15:
time.sleep(0.066)  # ~15 FPS
```

---

## Server Reliability Scoring

| Daily Uptime | Reliability | Action |
|---|---|---|
| 4+ hours | ✓ Good | Normal use |
| 1-4 hours | ⚠ Acceptable | Monitor closely |
| < 1 hour | ✗ Poor | Debug immediately |
| Crashes on start | ✗ Critical | Check dependencies |

---

**Your goal: Identify the LAST message in console before server stops.** That message holds the key! 🔑

