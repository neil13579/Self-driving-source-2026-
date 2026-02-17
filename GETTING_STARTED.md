# 🚀 Getting Started - 10 Minute Overview

Welcome! This system lets you see what CARLA vehicles perceive in real-time. Here's what you need to know.

---

## What You Have

```
You have a CARLA autopilot system that shows you:
  1. Camera feed with bounding boxes
  2. LIDAR point cloud
  3. RADAR with velocity tracking
  4. Real-time statistics

All updating 30 times per second!
```

---

## The 3-Step Startup

### Step 1: Start CARLA (5 seconds)
**Windows**: Open your file explorer, go to `C:\Users\YOUR_NAME\Documents\CARLA_0.9.13\`  
**Double-click**: `CarlaUE4.exe`

Wait until you see the CARLA simulator window with a driving scene.

### Step 2: Start Server (2 minutes)
**Open PowerShell/command prompt**:
```bash
cd C:\Users\YOUR_NAME\Documents\Carla_SEAL
python monitor_server.py
```

You should see:
```
[INIT-16] WebSocket server ready
```

**Leave this window open!** The server keeps running here.

### Step 3: Open Dashboard (seconds)
**In file explorer**, go to same folder and **double-click**: `dashboard.html`

Your browser opens and shows **4 panels**:
- Top-left: **Camera** (with colored boxes)
- Top-right: **LIDAR** (3D point cloud)
- Bottom-left: **RADAR** (moving targets)
- Bottom-right: **Stats** (numbers)

---

## Video Guide (Mental Model)

Imagine you're in a self-driving car:

**Top-left panel (Camera)**:
```
┌─────────────────────────┐
│  Ahead: Vehicle ▭▭▭▭▭ │
│         45 km/h (GREEN) │
│                         │
│  Left:  Sign ▭▭▭       │
│         (CYAN)          │
└─────────────────────────┘
```
Shows: Everything the car's camera sees, with colored boxes

**Top-right panel (LIDAR)**:
```
┌─────────────────────────┐
│    (Red dots here)      │
│   (Orange there)        │
│ (Blue further back)     │
│                         │
│ Range circles: 0-150m   │
└─────────────────────────┘
```
Shows: 3D environment as seen by laser scanner  
Red = close | Blue = far away

**Bottom-left panel (RADAR)**:
```
┌─────────────────────────┐
│     ⊙──→  45m speed     │
│         (vehicle arrow) │
│                         │
│     ⊙─→   20m slow      │
│        (pedestrian)     │
└─────────────────────────┘
```
Shows: Moving targets with arrows showing direction

**Bottom-right panel (Stats)**:
```
FPS: 28.5
Vehicles: 4
Pedestrians: 1
Status: 🟢 Connected
```
Shows: System health and detection count

---

## What's Happening Behind the Scenes

```
CARLA Simulator
    ↓ (Cameras, sensors)
Python Perception Engine
    ↓ (AI models detect objects)
WebSocket Server
    ↓ (Sends data to browser)
Your Browser Dashboard
    ↓ (Renders visualizations)
4 Real-Time Panels ← YOU'RE HERE! 👀
```

---

## How to Interpret What You're Seeing

### Camera Panel (Top-Left)
- **Green boxes** = Vehicles, shows speed (45 km/h)
- **Red boxes** = People walking
- **Cyan boxes** = Traffic signs
- **Orange boxes** = Traffic lights

### LIDAR Panel (Top-Right)
- **Red/Orange dots** = Nearby objects (0-50m away)
- **Yellow/Green dots** = Medium distance (50-100m)
- **Blue dots** = Far away (100-150m)
- **Concentric circles** = 20-30m distance markers

### RADAR Panel (Bottom-Left)
- **Orange circle + arrow** = Vehicle moving (arrow shows direction)
- **Magenta circle + arrow** = Pedestrian moving
- **Distance labels** = "45m", "23m" from ego vehicle
- **Center green crosshair** = Your vehicle (ego)

### Stats Panel (Bottom-Right)
- **FPS** = Frames per second (target: 25+)
- **Vehicle/Pedestrian counts** = How many detected
- **Status** = 🟢 Connected (green) or 🔴 Offline (red)

---

## Example: Vehicle Approaching

Watch what changes:

**Time 1** (Far away):
- Camera: Small green box (far away)
- LIDAR: Blue dots (far)
- RADAR: Small distance "100m"
- Stats: Vehicle detected, FPS: 28

**Time 2** (Closer):
- Camera: Larger green box + "32 km/h"
- LIDAR: Yellow dots (closer color)
- RADAR: Larger circle, arrow bigger "50m"
- Stats: Vehicle speed shows 32

**Time 3** (Very close):
- Camera: Large green box + "45 km/h"
- LIDAR: Red dots (very close)
- RADAR: Huge circle + arrow "20m"
- Stats: Speed: 45 km/h

**What this means**: You're seeing the vehicle get closer! 🚗📍📍📍

---

## Common Questions

### Q: "Nothing shows up"
**A**: Check [INIT-16] in server console. If not there, server didn't start properly.
1. Stop server (Ctrl+C)
2. Restart: `python monitor_server.py`
3. Refresh browser (Ctrl+R)

### Q: "Dashboard loads but is blank"
**A**: Either no data or connection lost.
1. Check: Is Status showing 🟢 or 🔴?
2. If 🔴: Refresh page (Ctrl+R)
3. If still blank: Restart server + browser

### Q: "FPS is very low (< 10)"
**A**: Your system is struggling. Close other apps:
1. Close Chrome tabs (except dashboard)
2. Close other applications
3. Refresh dashboard (Ctrl+R)

### Q: "I see colored boxes but they don't move"
**A**: Server might not be streaming live frames.
1. Check server console for [PROC-N] messages
2. If missing: Restart CARLA (might have paused)
3. Restart server

### Q: "The system stopped working"
**A**: See **SERVER_STABILITY_DEBUG.md** in your folder

---

## Optional: Understanding the Numbers

### In Camera Feed
- **45 km/h** = Vehicle speed (kilometers per hour)
- **Vehicle0** = Object ID (0, 1, 2, etc.)

### In RADAR
- **45m** = Distance from your car
- **Vector arrow** = Direction moving

### In Stats
- **FPS: 28.5** = 28.5 frames per second (target: 20+)
- **Latency: 45ms** = Data takes 45 milliseconds to arrive
- **Vehicles: 4** = 4 vehicles detected in scene

---

## Things to Try

### 1. Drive Around the Scene
In CARLA window:
- Use arrow keys or WASD to control vehicle
- Watch how visualizations update!

### 2. Watch Pedestrians Cross
- Pedestrians sometimes cross in front
- See red boxes appear in camera
- See them on RADAR with movement

### 3. Multiple Vehicles
- Drive near other traffic
- Count how many in Stats panel
- See them in camera and RADAR simultaneously

### 4. Check LIDAR Depth
- Drive past objects (parked cars, buildings)
- LIDAR color changes red → blue as you move closer/farther

---

## Keyboard Shortcuts

### In Browser Dashboard
- **Ctrl+R** = Refresh (if something weird happens)
- **F12** = Open developer console (if curious)

### In CARLA Simulator
- **Space** = Pause/unpause the simulation
- **V** = Change camera view
- **Arrow keys** = Drive your vehicle
- **W, A, S, D** = Steer

### In Server Console
- **Ctrl+C** = Stop server (gracefully shuts down)

---

## File Organization

Everything is in one folder:
```
Carla_SEAL/
├── unified_perception_server.py  ← The brain (run this)
├── dashboard.html                ← The display (open this)
├── monitor_server.py             ← Safer server launcher
├── README.md                     ← Full documentation
└── [Other guides]
```

---

## Troubleshooting Quick Map

| Problem | Likely Cause | Quick Fix |
|---|---|---|
| Blank dashboard | No data | Refresh (Ctrl+R) |
| Red Status | Connection lost | Restart server |
| Boxes don't move | Paused CARLA | Press Space in CARLA |
| Very low FPS | System busy | Close other apps |
| Server won't start | CARLA offline | Start CARLA first |

---

## What You Should See (After 30 seconds)

✅ Dashboard loaded  
✅ Status: 🟢 Connected  
✅ FPS: 20+ (updating)  
✅ Camera shows a street scene  
✅ LIDAR shows colored point cloud  
✅ RADAR shows some circles/arrows  
✅ All updating smoothly in real-time  

**If you see all of these: You're all set!** 🎉

---

## Next Steps

1. **Keep it running**: Leave server and CARLA running, explore dashboard
2. **Read QUICKSTART.md**: More detailed info
3. **Check QUICK_REFERENCE_CARD.md**: Commands and tips
4. **Use TROUBLESHOOTING_FLOWCHART.md**: If something breaks

---

## That's It!

You now have a **real-time perception system** showing:
- 📷 What the camera sees
- 📡 What the LIDAR maps
- 🎯 Where targets are moving
- 📊 System health

Enjoy exploring your autonomous driving perception system! 🚗✨

---

**Questions?** Check the guides in your folder!  
**Something broken?** See **TROUBLESHOOTING_FLOWCHART.md**  
**Want more info?** Read **README.md**

