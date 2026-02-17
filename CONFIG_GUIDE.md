# CARLA Perception System Configuration Guide

## System Parameters

### Camera Settings
```python
# In setup_sensors():
camera_bp.set_attribute('image_size_x', '256')  # Width
camera_bp.set_attribute('image_size_y', '256')  # Height
camera_bp.set_attribute('fov', '90')             # Field of view in degrees
```

### LiDAR Settings
```python
# In setup_sensors():
lidar_bp.set_attribute('channels', '32')              # Number of laser channels
lidar_bp.set_attribute('points_per_second', '280000') # Point generation rate
lidar_bp.set_attribute('rotation_frequency', '10')    # Rotation speed (Hz)
lidar_bp.set_attribute('range', '50')                 # Maximum range (meters)
```

### Radar Settings
```python
# In setup_sensors():
radar_bp.set_attribute('horizontal_fov', '30')  # Horizontal field of view
radar_bp.set_attribute('range', '100')          # Detection range (meters)
```

### UKF Parameters
```python
# In UnscentedKalmanFilter.__init__():
self.alpha = 0.001      # Spread of sigma points
self.beta = 2.0         # Optimal for Gaussian distribution
self.kappa = 0.0        # Secondary scaling parameter
```

### Vision Pipeline Parameters
```python
# In BoundingBoxDetector.extract_bboxes():
min_area = 100  # Minimum area threshold for detections

# In BoundingBoxDetector.non_max_suppression():
iou_threshold = 0.5  # IoU threshold for NMS

# In ObjectTracker.__init__():
max_age = 5  # Maximum frames to keep track without updates
```

### Web Server Settings
```python
# In main():
app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
# host='0.0.0.0' - Listen on all interfaces
# port=5000 - Flask server port
# debug=False - Disable debug mode for production
# threaded=True - Enable multi-threading

# WebSocket server
DataWebSocketServer(host='0.0.0.0', port=8765)
```

## Sensor Fusion Covariance Matrices

### Process Noise (Q Matrix)
```python
# Controls how much state can change between updates
self.Q[0:3, 0:3] *= 0.1    # Position noise
self.Q[3:6, 3:6] *= 0.5    # Velocity noise
self.Q[6:9, 6:9] *= 0.01   # Acceleration noise
self.Q[9, 9] *= 0.05       # Angular velocity noise
```

### Measurement Noise (R Matrix)
```python
# Controls trust in measurements
self.R[0:3, 0:3] *= 2.0    # Position measurement noise
self.R[3:6, 3:6] *= 0.5    # Velocity measurement noise
```

### GPS-specific Noise
```python
R_gps[0:3, 0:3] *= 2.0     # Position accuracy (meters)
R_gps[3:6, 3:6] *= 10.0    # Velocity accuracy (m/s)
```

### Radar-specific Noise
```python
R_radar[0:3, 0:3] *= 100.0  # Position uncertainty
R_radar[3:6, 3:6] *= 0.5    # Velocity certainty
```

## Performance Tuning

### Increase Detection Accuracy
```python
# Option 1: Stricter non-max suppression
iou_threshold = 0.3  # More aggressive filtering

# Option 2: Higher minimum area
min_area = 200  # Filter small detections

# Option 3: Better U-Net model
self.unet = UNet(input_shape=(512, 512, 3), num_classes=13)  # Larger input
```

### Improve Frame Rate
```python
# Option 1: Reduce image resolution
camera_bp.set_attribute('image_size_x', '128')
camera_bp.set_attribute('image_size_y', '128')

# Option 2: Reduce LiDAR points
lidar_bp.set_attribute('points_per_second', '100000')

# Option 3: Skip frames in processing
# Process every Nth frame in camera_callback
if self.data_count['camera'] % 2 == 0:  # Process every 2nd frame
    # ... prediction code
```

### Reduce Memory Usage
```python
# Option 1: Reduce tracking history
self.fps_history = deque(maxlen=10)  # Down from 30

# Option 2: Smaller U-Net
self.unet = UNet(input_shape=(128, 128, 3), num_classes=13)

# Option 3: Reduce sensor output
lidar_points = points[::10]  # Downsample more aggressively
```

## Object Detection Classes

CARLA Semantic Segmentation Classes:
```python
CARLA_COLORS = {
    0: (0, 0, 0),        # Unlabeled
    1: (128, 64, 128),   # Road
    2: (244, 35, 232),   # Sidewalk
    3: (70, 70, 70),     # Building
    4: (102, 102, 156),  # Wall
    5: (190, 153, 153),  # Fence
    6: (153, 153, 153),  # Pole
    7: (250, 170, 30),   # Traffic light
    8: (220, 220, 0),    # Traffic sign
    9: (107, 142, 35),   # Vegetation
    10: (152, 251, 152), # Terrain
    11: (70, 130, 180),  # Sky
    12: (220, 20, 60),   # Person
    13: (0, 0, 142),     # Vehicle
}
```

Detection Classes (detected):
```python
self.classes_to_detect = {
    13: 'Vehicle',
    12: 'Person',
    7: 'Traffic Light',
    8: 'Traffic Sign'
}
```

## Data Rate Configuration

### Current Configuration
- **Camera**: 30 FPS @ 256×256
- **LiDAR**: 10 Hz, 280k points/sec
- **Radar**: 10 Hz, 30° FOV
- **GPS**: 1 Hz
- **IMU**: 10 Hz

### Low-Latency Configuration
```python
# Reduce all sampling rates for real-time processing
lidar_bp.set_attribute('rotation_frequency', '20')  # 20 Hz
lidar_bp.set_attribute('points_per_second', '100000')  # 100k points
radar_bp.set_attribute('range', '50')  # Shorter range
```

### High-Accuracy Configuration
```python
# Increase sampling for accuracy
lidar_bp.set_attribute('rotation_frequency', '5')  # 5 Hz but denser
lidar_bp.set_attribute('points_per_second', '500000')  # 500k points
camera_bp.set_attribute('image_size_x', '512')
camera_bp.set_attribute('image_size_y', '512')
```

## Logger Configuration

### Enable Debug Logging
```python
# In camera_callback():
if self.data_count['camera'] % 10 == 0:
    print(f"📷 Frame {self.data_count['camera']}: "
          f"{len(self.current_detections)} objects detected")

# In lidar_callback():
if self.data_count['lidar'] % 10 == 0:
    print(f"🔵 LiDAR {self.data_count['lidar']}: "
          f"{self.stats['lidar_points']} points")
```

### Performance Metrics
```python
# Track processing time
import time
start = time.time()
# ... processing code
elapsed = time.time() - start
print(f"Processing time: {elapsed*1000:.2f}ms")
```

## Network Configuration

### Local Network Access
```python
# Allow access from other machines on network
app.run(host='0.0.0.0', port=5000)  # Accept all interfaces
# Then access from other machine: http://<server-ip>:5000
```

### Firewall Rules (Windows)
```powershell
# Add Flask server to firewall
netsh advfirewall firewall add rule name="Flask-5000" dir=in action=allow protocol=tcp localport=5000

# Add WebSocket to firewall
netsh advfirewall firewall add rule name="WebSocket-8765" dir=in action=allow protocol=tcp localport=8765
```

## Advanced Tuning

### Kalman Filter Tuning
```python
# For better position estimation
self.Q[0:3, 0:3] *= 0.05  # Trust motion model more
self.R[0:3, 0:3] *= 3.0   # Trust GPS less

# For better velocity estimation
self.Q[3:6, 3:6] *= 0.2   # Allow velocity changes
self.R[3:6, 3:6] *= 1.0   # Trust radar velocity
```

### Object Tracking Tuning
```python
# For faster moving objects
if iou > 0.2:  # Lower threshold for high-speed matches
    track['detection'] = best_det

# For crowded scenes
self.max_age = 2  # Forget tracks sooner
```

### Neural Network Tuning
```python
# Learning rate for re-training
optimizer=keras.optimizers.Adam(learning_rate=0.0001)

# Batch normalization momentum
layers.BatchNormalization(momentum=0.99)
```

## Debugging Checklist

- [ ] CARLA connected: Check console for "Connected to CARLA"
- [ ] Vehicle spawned: Check "Vehicle spawned at point X"
- [ ] Sensors active: Check "All sensors active"
- [ ] Web server running: Can access http://localhost:5000
- [ ] WebSocket working: Check browser console for connection
- [ ] Camera processing: FPS value updates
- [ ] Detections working: "Detected Objects" list updates
- [ ] Fusion working: UKF Fusion State values change

---

For more help, see QUICKSTART.md
