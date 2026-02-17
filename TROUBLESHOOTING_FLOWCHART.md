# 🔧 Startup Troubleshooting Flowchart

## START: Running "python monitor_server.py"

```
                    Did the server start?
                           │
                ┌──────────┴──────────┐
               YES                   NO
                │                    │
                ▼                    ▼
        ┌──────────────┐    ┌─────────────────────┐
        │  Go to Flow  │    │ See CARLA/Deps Init │
        │      B       │    │    (Below)          │
        └──────────────┘    └─────────────────────┘
```

---

## Flow B: Server Running - Is Dashboard Connecting?

```
      Run: python monitor_server.py
                   │
                   ▼
      Is [INIT-16] showing in console?
           (WebSocket server ready)
                   │
        ┌──────────┴──────────┐
       YES                   NO
        │                    │
        ▼                    ▼
   Continue        ┌──────────────────────┐
   (Go to C)       │ Error before INIT-16 │
                   │ (See error messages) │
                   │                      │
                   │ [ERROR-1]: CARLA ──→ A1
                   │ [ERROR-2]: Traffic ─→ A2
                   │ [ERROR-3]: Sensors ─→ A3
                   └──────────────────────┘
```

---

## Flow C: Dashboard Connection

```
         Double-click: dashboard.html
                   │
                   ▼
      Does browser show the dashboard?
                   │
        ┌──────────┴──────────┐
       YES                   NO
        │                    │
        ▼                    ▼
   Go to Flow D     ┌─────────────────┐
              │    │ Browser issues   │
              │    │ Check console F12│
              │    │ (Ctrl+F12)       │
              │    │                  │
              │    │ Error messages:  │
              │    │ • Cannot connect │────→ Check: is port 8765 open?
              │    │ • SSL error      │────→ Use HTTP not HTTPS
              │    │ • CORS blocked   │────→ Wrong domain
              │    │ • File not found │────→ Use correct path
              │    └─────────────────┘
              │
              └──→ Refresh (Ctrl+R) and retry
```

---

## Flow D: Dashboard Loaded - Are Visualizations Working?

```
         Dashboard loads, now check visualizations
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    Camera Feed   LIDAR Points   RADAR Targets
        │              │              │
        │              │              │
   See boxes?     See points?    See circles?
        │              │              │
    ┌───┴───┐       ┌───┴───┐       ┌───┴───┐
   YES  NO        YES  NO        YES  NO
    │    │         │    │         │    │
    ▼    ▼         ▼    ▼         ▼    ▼
   Good D1       Good D2       Good D3 / D4
   │    │         │    │         │    │
   │    └────────┼────┼────────┼────┘
   │             │    │        │
   ▼             ▼    ▼        ▼
         See "Status: 🟢 Connected"?
                      │
           ┌──────────┴──────────┐
          YES                   NO
           │                    │
           ▼                    ▼
        ✓ GOOD!           ✗ DISCONNECTED
      System works        Go to Flow E
      (Monitoring)
```

---

## Flow D1: Camera Shows Boxes But Numbers Weird

```
    Boxes showing correctly?
            │
    ┌───────┴───────┐
   YES              NO
    │               │
    ▼               ▼
  Good!      Check detection format
          
        Missing object types?
        Wrong bounding boxes?
        Labels cut off?
                │
                ▼
        Edit dashboard.html
        drawDetections() function
        (Around line 300-400)
        
        Redraw box position:
        ctx.strokeRect(x, y, w, h)
```

---

## Flow D2: LIDAR Point Cloud Issues

```
        LIDAR showing points?
                │
    ┌───────────┴───────────┐
   YES                     NO
    │                      │
    ▼                      ▼
  Colors OK?       ┌──────────────────┐
    │              │ Empty LIDAR view │
    │ ┌────┴────┐  │                  │
    │ │          │  │ Check server log│
    │ │Red-Green │  │ for [LIDAR]:    │
    │ │-Blue     │  │                  │
    │ │showing?  │  │ [NULL-FRAME-60]?│
    │ │          │  │ → CARLA stopped │
    │ │ ┌──┴──┐  │  │                  │
    │ │ │     │  │  │ [PROC-ERROR]?   │
    │ │YES  NO  │  │ → Processing bug │
    │ │ │     │  │  │                  │
    │ │ ▼     ▼  │  └──────────────────┘
    │ │Good  Bad │
    │ │(OK)  (E) │           FIX: Restart
    │ └────┬────┘        CARLA + Server
    │      │
    └──────┘
       │
       ▼
    Continue monitoring
```

---

## Flow D3: RADAR Velocity Vectors

```
        RADAR showing targets?
                │
    ┌───────────┴───────────┐
   YES                     NO
    │                      │
    ▼                      ▼
  Arrows showing?   ┌──────────────────┐
    │               │ No targets in    │
    │ ┌────┴────┐   │ RADAR view       │
    │ │          │   │                  │
    │YES        NO  │ Possible causes: │
    │ │          │   │ 1. No vehicles   │
    │ │          │   │    near ego      │
    │ │ ▼        ▼   │ 2. RADAR sensor  │
    │ │Good     (E)  │    issue         │
    │ │(OK)         │ 3. Server filter  │
    │ │             │    too strict     │
    │ └────┬────┘   │                  │
    │      │        │Edit radar config │
    │      │        │in server code   │
    │      │        └──────────────────┘
    └──────┘
       │
       ▼
    Continue monitoring
    (or go to E if disconnected)
```

---

## Flow D4: Statistics Panel Update

```
        Stats showing numbers?
                │
    ┌───────────┴───────────┐
   YES                     NO
    │                      │
    ▼                      ▼
  FPS > 10?       ┌──────────────────┐
    │             │ Stats not        │
    │ ┌────┴────┐ │ updating         │
    │ │          │ │                  │
    │YES        NO│ Possible causes: │
    │ │          │ │ 1. Server slow   │
    │ │ ▼        ▼ │ 2. Data not      │
    │ │Good    Slow │    sent          │
    │ │(OK)    (W)  │ 3. Browser lag   │
    │ │             │                  │
    │ │FPS<5        │Refresh page:    │
    │ │then         │Ctrl+R           │
    │ │system       │                  │
    │ │overloaded   │If still 0 FPS:  │
    │ │Close other  │→ Go to Flow E    │
    │ │apps         └──────────────────┘
    │ │
    └─┴┘
       │
       ▼
    Continue monitoring
```

---

## Flow E: WebSocket Disconnection Fix

```
        Status shows: 🔴 Disconnected
                      or "Connecting..."
                      or offline
                      │
                      ▼
            Are you seeing in console:
            [BROADCAST-OK-N] messages?
                      │
           ┌──────────┴──────────┐
          YES                   NO
           │                    │
           ▼                    ▼
        Browser   ┌──────────────────────┐
        issue:    │ Server not sending   │
        • Refresh │ data = SERIOUS ISSUE │
        • F5      │                      │
        • Hard    │ Check last console   │
          reload  │ message:             │
        • Ctrl+   │                      │
          Shift+R │ [PROC-ERROR-N]?    │
                  │ → Processing crash  │
                  │                      │
                  │ [NULL-FRAME-N]?    │
                  │ → CARLA disconnect  │
                  │                      │
                  │ No message?          │
                  │ → Thread crash      │
                  │                      │
                  │ FIX: Restart        │
                  │ 1. Ctrl+C server    │
                  │ 2. Check CARLA      │
                  │ 3. Restart server   │
                  │ 4. Refresh browser  │
                  └──────────────────────┘
```

---

## CARLA/Dependencies Init Failures

```
Error at initialization?

┌─────────────────────────────────────────────────────┐
│ [ERROR-1] Failed to connect to CARLA                │
├─────────────────────────────────────────────────────┤
│ FIX:                                                │
│ 1. Is CARLA running?                               │
│    □ Start CarlaUE4.exe or CarlaUE4.sh             │
│    □ Wait 10 seconds for full load                 │
│ 2. Port 2000 open?                                 │
│    □ Run: python check_system.py                   │
│    □ Should show "✓ CARLA Server: Running"         │
│ 3. Firewall blocking?                              │
│    □ Check Windows Firewall settings               │
│    □ Try adding python.exe to Allow List           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ [ERROR-2] Failed to setup traffic                   │
├─────────────────────────────────────────────────────┤
│ FIX:                                                │
│ 1. CARLA crashed?                                  │
│    □ Check CARLA window - still open?              │
│ 2. Maps/assets corruption?                         │
│    □ Restart CARLA completely                      │
│    □ Load Town03 or Town05 maps                    │
│ 3. Retry:                                          │
│    □ Ctrl+C server                                 │
│    □ Close CARLA                                   │
│    □ Wait 5 seconds                                │
│    □ Start CARLA again                             │
│    □ Start server again                            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ [ERROR-3] Failed to setup sensors                   │
├─────────────────────────────────────────────────────┤
│ (or any TensorFlow/OpenCV import error)             │
│                                                     │
│ FIX:                                                │
│ 1. Check missing modules:                          │
│    □ python check_system.py                        │
│    □ Look for "✗" marks                            │
│ 2. Install missing packages:                       │
│    □ pip install tensorflow==2.10.0                │
│    □ pip install websockets                        │
│    □ pip install opencv-python                     │
│    □ pip install numpy                             │
│ 3. Restart server after install                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ ModuleNotFoundError: No module named 'X'            │
├─────────────────────────────────────────────────────┤
│ FIX:                                                │
│ pip install X                                      │
│                                                     │
│ Common missing modules:                            │
│ • tensorflow → pip install tensorflow==2.10.0      │
│ • cv2 → pip install opencv-python                  │
│ • websockets → pip install websockets              │
│ • numpy → pip install numpy                        │
│ • scipy → pip install scipy                        │
│ • carla → pip install carla==0.9.13                │
└─────────────────────────────────────────────────────┘
```

---

## Decision Tree Summary

```
Problem              Next Step              Reference
─────────────────────────────────────────────────────────
No CARLA connection    → Check port 2000         Flow A1
Server won't start     → Check imports           Flow A (Init)
Dashboard won't load   → Check console (F12)     Flow C
Camera empty           → Check [PROC-OK] message Flow D1
LIDAR empty            → Restart CARLA           Flow D2
RADAR empty            → Check CARLA traffic     Flow D3
Stats show 0 FPS       → Disconnect/reconnect    Flow D4
"Disconnected" status  → Restart server          Flow E
Server crashes         → Check console output    SERVER_STABILITY_DEBUG.md
Memory increasing      → Memory leak check       QUICK_REFERENCE.md
```

---

## Quick Emergency Restart

```
If ANYTHING is broken, try this sequence:

1. Server Terminal:
   └─ Press Ctrl+C (stop server)

2. Browser:
   └─ Close dashboard tab

3. CARLA Window:
   └─ Close CARLA completely (Alt+F4)

4. Wait 10 seconds

5. Restart CARLA:
   └─ Double-click CarlaUE4.exe or .sh
   └─ Wait for full load (5-10 seconds)

6. Restart Server:
   └─ Run: python monitor_server.py
   └─ Wait for [INIT-16] message

7. Open Dashboard:
   └─ Double-click dashboard.html
   └─ Watch for 🟢 Connected status

8. Success?
   └─ YES: Problem solved!
   └─ NO: Go to SERVER_STABILITY_DEBUG.md
```

---

## When All Else Fails

```
If flowchart doesn't solve it:

1. Gather information:
   └─ Console output
   └─ Last message before error
   └─ Error text (copy all red lines)
   └─ Python version (python --version)
   └─ System info (python check_system.py)

2. Check documentation:
   └─ README.md
   └─ SERVER_STABILITY_DEBUG.md
   └─ QUICK_REFERENCE_CARD.md

3. Additional debug:
   └─ Run verify_components.py
   └─ Clear cache: del __pycache__ /s
   └─ Reinstall deps: pip install -r requirements.txt

4. Last resort:
   └─ Fresh CARLA installation
   └─ Fresh Python environment
   └─ Contact tech support with details
```

---

**Keep this document handy for quick diagnosis!** 📋

