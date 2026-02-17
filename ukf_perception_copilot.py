"""
CARLA Perception Stack with UKF
"""

import carla
import numpy as np
import time
import json
import asyncio
import websockets
import struct
from collections import deque
from scipy.linalg import cholesky
from datetime import datetime
import threading
import queue
import os
import base64
import http.server
import socketserver


HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CARLA Perception Web Viz</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; }
        #container { width: 100vw; height: 100vh; }
        #info { position: absolute; top: 10px; left: 10px; color: white; background: rgba(0,0,0,0.5); padding: 10px; }
    </style>
</head>
<body>
    <div id="container"></div>
    <div id="info">
        <div>Lidar Points: <span id="pointCount">0</span></div>
        <div>Radar Detections: <span id="radarCount">0</span></div>
        <div>GPS: <span id="gps">N/A</span></div>
        <div>Pose: <span id="pose">N/A</span></div>
    </div>

    <script>
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer();
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.getElementById('container').appendChild(renderer.domElement);

        // LiDAR point cloud
        const geometry = new THREE.BufferGeometry();
        const material = new THREE.PointsMaterial({ color: 0xffffff, size: 0.1 });
        const points = new THREE.Points(geometry, material);
        scene.add(points);

        // Radar detections container
        const radarGroup = new THREE.Group();
        scene.add(radarGroup);

        camera.position.z = 50;

        const controls = { mouseX: 0, mouseY: 0 };
        document.addEventListener('mousemove', (event) => {
            controls.mouseX = (event.clientX / window.innerWidth) * 2 - 1;
            controls.mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
        });

        const ws = new WebSocket('ws://localhost:8765');
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'lidar') {
                updatePointCloud(msg.data);
            } else if (msg.type === 'radar') {
                updateRadarDetections(msg.detections);
            } else if (msg.type === 'gps') {
                document.getElementById('gps').textContent = `${msg.latitude.toFixed(6)}, ${msg.longitude.toFixed(6)}`;
            } else if (msg.type === 'pose') {
                const p = msg.position;
                document.getElementById('pose').textContent = `${p.x.toFixed(2)}, ${p.y.toFixed(2)}, ${p.z.toFixed(2)}`;
            }
        };

        function updatePointCloud(data) {
            const binary = atob(data);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            const positions = new Float32Array(bytes.buffer);
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 4));
            geometry.attributes.position.needsUpdate = true;
            document.getElementById('pointCount').textContent = positions.length / 4;
        }

        function updateRadarDetections(detections) {
            // Clear previous radar objects
            while (radarGroup.children.length > 0) {
                radarGroup.removeChild(radarGroup.children[0]);
            }

            // Create markers for each detection
            for (let i = 0; i < detections.length; i++) {
                const det = detections[i];
                
                // Create sphere for detection
                const geometry = new THREE.SphereGeometry(0.3, 8, 8);
                const material = new THREE.MeshBasicMaterial({ 
                    color: 0xff6600,  // Orange for radar
                    emissive: 0xff6600,
                    wireframe: false
                });
                const mesh = new THREE.Mesh(geometry, material);
                mesh.position.set(det.x, det.y, det.z);
                radarGroup.add(mesh);

                // Create velocity vector line
                const direction = new THREE.Vector3(det.vel_x, det.vel_y, 0).normalize();
                const velocity_length = 2;
                const points = [
                    new THREE.Vector3(det.x, det.y, det.z),
                    new THREE.Vector3(
                        det.x + direction.x * velocity_length,
                        det.y + direction.y * velocity_length,
                        det.z
                    )
                ];
                const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
                const lineMaterial = new THREE.LineBasicMaterial({ color: 0xff3300 });
                const line = new THREE.Line(lineGeometry, lineMaterial);
                radarGroup.add(line);
            }

            document.getElementById('radarCount').textContent = detections.length;
        }

        function animate() {
            requestAnimationFrame(animate);
            camera.position.x += (controls.mouseX * 10 - camera.position.x) * 0.05;
            camera.position.y += (controls.mouseY * 10 - camera.position.y) * 0.05;
            camera.lookAt(scene.position);
            renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>
"""


class UnscentedKalmanFilter:
    """Unscented Kalman Filter for sensor fusion"""
    
    def __init__(self, dim_x=10, dim_z=6):
        self.dim_x = dim_x
        self.dim_z = dim_z
        
        self.x = np.zeros(dim_x)
        self.P = np.eye(dim_x) * 10.0
        
        self.Q = np.eye(dim_x)
        self.Q[0:3, 0:3] *= 0.1
        self.Q[3:6, 3:6] *= 0.5
        self.Q[6:9, 6:9] *= 0.01
        self.Q[9, 9] *= 0.05
        
        self.R = np.eye(dim_z)
        self.R[0:3, 0:3] *= 2.0
        self.R[3:6, 3:6] *= 0.5
        
        self.alpha = 0.001
        self.beta = 2.0
        self.kappa = 0.0
        self.lambda_ = self.alpha**2 * (self.dim_x + self.kappa) - self.dim_x
        
        self.Wm, self.Wc = self._calculate_weights()
        
    def _calculate_weights(self):
        n = self.dim_x
        lambda_ = self.lambda_
        
        Wm = np.zeros(2 * n + 1)
        Wc = np.zeros(2 * n + 1)
        
        Wm[0] = lambda_ / (n + lambda_)
        Wc[0] = lambda_ / (n + lambda_) + (1 - self.alpha**2 + self.beta)
        
        for i in range(1, 2 * n + 1):
            Wm[i] = 1.0 / (2 * (n + lambda_))
            Wc[i] = 1.0 / (2 * (n + lambda_))
            
        return Wm, Wc
    
    def _generate_sigma_points(self):
        n = self.dim_x
        lambda_ = self.lambda_
        
        sigma_points = np.zeros((2 * n + 1, n))
        sigma_points[0] = self.x
        
        try:
            U = cholesky((n + lambda_) * self.P)
        except np.linalg.LinAlgError:
            U = np.linalg.cholesky((n + lambda_) * (self.P + np.eye(n) * 1e-6))
        
        for i in range(n):
            sigma_points[i + 1] = self.x + U[i]
            sigma_points[n + i + 1] = self.x - U[i]
            
        return sigma_points
    
    def _state_transition(self, x, dt):
        x_new = x.copy()
        x_new[0] += x[3] * dt
        x_new[1] += x[4] * dt
        x_new[2] += x[5] * dt
        x_new[8] += x[9] * dt
        x_new[8] = np.arctan2(np.sin(x_new[8]), np.cos(x_new[8]))
        return x_new
    
    def _measurement_function(self, x):
        return x[[0, 1, 2, 3, 4, 5]]
    
    def predict(self, dt):
        sigma_points = self._generate_sigma_points()
        sigma_points_pred = np.array([self._state_transition(sp, dt) for sp in sigma_points])
        
        self.x = np.sum(self.Wm[:, np.newaxis] * sigma_points_pred, axis=0)
        
        diff = sigma_points_pred - self.x
        self.P = self.Q.copy()
        for i in range(len(self.Wc)):
            self.P += self.Wc[i] * np.outer(diff[i], diff[i])
    
    def update(self, z, R=None):
        if R is None:
            R = self.R
            
        sigma_points = self._generate_sigma_points()
        sigma_points_meas = np.array([self._measurement_function(sp) for sp in sigma_points])
        
        z_pred = np.sum(self.Wm[:, np.newaxis] * sigma_points_meas, axis=0)
        
        diff_z = sigma_points_meas - z_pred
        Pzz = R.copy()
        for i in range(len(self.Wc)):
            Pzz += self.Wc[i] * np.outer(diff_z[i], diff_z[i])
        
        diff_x = sigma_points - self.x
        Pxz = np.zeros((self.dim_x, self.dim_z))
        for i in range(len(self.Wc)):
            Pxz += self.Wc[i] * np.outer(diff_x[i], diff_z[i])
        
        K = Pxz @ np.linalg.inv(Pzz)
        
        innovation = z - z_pred
        self.x += K @ innovation
        self.P -= K @ Pzz @ K.T


class DataWebSocketServer:
    """Simple WebSocket server for data transmission"""
    
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        
    async def register_client(self, websocket):
        self.clients.add(websocket)
        print(f"✅ Web client connected! Total: {len(self.clients)}")
        
    async def unregister_client(self, websocket):
        self.clients.discard(websocket)
        print(f"Client disconnected. Total: {len(self.clients)}")
    
    async def handle_client(self, websocket):
        """Handle client connection"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                pass  # Handle incoming if needed
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def send_message(self, message):
        """Send message to all clients"""
        if not self.clients:
            return
        
        msg_json = json.dumps(message)
        
        # Send to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(msg_json)
            except:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    async def start(self):
        """Start server"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"🌐 WebSocket: ws://localhost:{self.port}")
            await asyncio.Future()


class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode())
        else:
            self.send_error(404)


def start_http_server(port=9090):
    with socketserver.TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        print(f"🌐 HTTP Server: http://localhost:{port}")
        httpd.serve_forever()


class PerceptionStack:
    """Main perception stack"""
    
    def __init__(self):
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.client = None
        self.world = None
        self.vehicle = None
        self.sensors = {}
        
        self.carla_host = self.config['carla']['host']
        self.carla_port = self.config['carla']['port']
        
        self.ukf = UnscentedKalmanFilter()
        self.last_time = time.time()
        
        self.data_ws = DataWebSocketServer(
            host=self.config['websocket']['host'], 
            port=self.config['websocket']['port']
        )
        self.loop = None
        
        self.gps_origin = None
        self.data_count = {'lidar': 0, 'radar': 0, 'gps': 0, 'imu': 0}
        
    def connect_to_carla(self):
        """Connect to CARLA"""
        try:
            self.client = carla.Client(self.carla_host, self.carla_port)
            self.client.set_timeout(30.0)
            self.world = self.client.get_world()
            print(f'✅ Connected to CARLA: {self.client.get_server_version()}')
            return True
        except Exception as e:
            print(f'❌ CARLA connection failed: {e}')
            return False
    
    def spawn_vehicle(self):
        """Spawn vehicle with camera following"""
        blueprint_library = self.world.get_blueprint_library()
        
        vehicle_blueprints = blueprint_library.filter('vehicle.tesla.model3')
        if not vehicle_blueprints:
            vehicle_bp = blueprint_library.filter('vehicle.*')[0]
        else:
            vehicle_bp = vehicle_blueprints[0]
        
        spawn_points = self.world.get_map().get_spawn_points()
        if not spawn_points:
            print("❌ No spawn points!")
            return False
        
        # Try multiple spawn points
        for i in range(min(5, len(spawn_points))):
            try:
                spawn_point = spawn_points[i]
                self.vehicle = self.world.spawn_actor(vehicle_bp, spawn_point)
                print(f'✅ Vehicle spawned at point {i}')
                break
            except Exception as e:
                if i == 4:
                    print(f"❌ Failed to spawn: {e}")
                    return False
        
        self.vehicle.set_autopilot(True)
        print('✅ Autopilot enabled')
        
        # Position camera
        time.sleep(0.5)
        spectator = self.world.get_spectator()
        transform = self.vehicle.get_transform()
        spectator.set_transform(carla.Transform(
            transform.location + carla.Location(x=-8, z=4),
            carla.Rotation(pitch=-15, yaw=transform.rotation.yaw)
        ))
        print('✅ Camera positioned')
        
        return True
    
    def setup_sensors(self):
        """Setup sensors"""
        bp_lib = self.world.get_blueprint_library()
        
        # LiDAR
        lidar_bp = bp_lib.find('sensor.lidar.ray_cast')
        lidar_bp.set_attribute('channels', '32')
        lidar_bp.set_attribute('points_per_second', '280000')
        lidar_bp.set_attribute('rotation_frequency', '10')
        lidar_bp.set_attribute('range', '50')
        lidar_transform = carla.Transform(carla.Location(z=2.4))
        self.sensors['lidar'] = self.world.spawn_actor(
            lidar_bp, lidar_transform, attach_to=self.vehicle
        )
        self.sensors['lidar'].listen(self.lidar_callback)
        
        # Radar
        radar_bp = bp_lib.find('sensor.other.radar')
        radar_bp.set_attribute('horizontal_fov', '30')
        radar_bp.set_attribute('range', '100')
        radar_transform = carla.Transform(carla.Location(x=2.0, z=1.0))
        self.sensors['radar'] = self.world.spawn_actor(
            radar_bp, radar_transform, attach_to=self.vehicle
        )
        self.sensors['radar'].listen(self.radar_callback)
        
        # GPS
        gps_bp = bp_lib.find('sensor.other.gnss')
        gps_transform = carla.Transform()
        self.sensors['gps'] = self.world.spawn_actor(
            gps_bp, gps_transform, attach_to=self.vehicle
        )
        self.sensors['gps'].listen(self.gps_callback)
        
        # IMU
        imu_bp = bp_lib.find('sensor.other.imu')
        imu_transform = carla.Transform()
        self.sensors['imu'] = self.world.spawn_actor(
            imu_bp, imu_transform, attach_to=self.vehicle
        )
        self.sensors['imu'].listen(self.imu_callback)
        
        print('✅ All sensors active')
    
    def lidar_callback(self, lidar_data):
        """Process LiDAR"""
        try:
            self.data_count['lidar'] += 1
        
            # DEBUG: Print every 10 frames
            if self.data_count['lidar'] % 10 == 0:
                print(f"🔵 LiDAR callback #{self.data_count['lidar']}")
                print(f"   Raw data size: {len(lidar_data.raw_data)} bytes")
        
            points = np.frombuffer(lidar_data.raw_data, dtype=np.float32)
            points = points.reshape(-1, 4)
        
            # DEBUG: Check points
            if self.data_count['lidar'] % 10 == 0:
                print(f"   Points parsed: {len(points)}")
        
            # Downsample
            points = points[::5]
        
            # Send to web viz
            if self.loop:
                message = {
                    'type': 'lidar',
                    'data': base64.b64encode(points.tobytes()).decode('ascii')
                }
                asyncio.run_coroutine_threadsafe(
                    self.data_ws.send_message(message),
                    self.loop
                )
                
        except Exception as e:
            print(f"❌ LiDAR error: {e}")
            import traceback
            traceback.print_exc()
    
    def radar_callback(self, radar_data):
        """Process Radar"""
        self.data_count['radar'] += 1
        
        try:
            detections = []
            velocities = []
            
            # Extract all detections
            for detection in radar_data:
                # CARLA radar returns: velocity, altitude (vertical angle), azimuth (horizontal angle)
                # Convert to Cartesian coordinates
                velocity = detection.velocity
                altitude = detection.altitude  # Angle in radians, vertical
                azimuth = detection.azimuth    # Angle in radians, horizontal
                depth = detection.depth        # Range in meters
                
                # Convert polar to Cartesian with proper handling
                x = depth * np.cos(altitude) * np.sin(azimuth)
                y = depth * np.cos(altitude) * np.cos(azimuth)
                z = depth * np.sin(altitude)
                
                # Velocity components
                vel_x = velocity * np.sin(azimuth)
                vel_y = velocity * np.cos(azimuth)
                vel_z = velocity * np.sin(altitude)
                
                detections.append({
                    'x': float(x),
                    'y': float(y),
                    'z': float(z),
                    'vel_x': float(vel_x),
                    'vel_y': float(vel_y),
                    'vel_z': float(vel_z),
                    'velocity': float(velocity),
                    'depth': float(depth)
                })
                
                velocities.append(velocity)
            
            # Send radar detections to web viz
            if self.loop and detections:
                message = {
                    'type': 'radar',
                    'detections': detections,
                    'count': len(detections)
                }
                asyncio.run_coroutine_threadsafe(
                    self.data_ws.send_message(message),
                    self.loop
                )
            
            # Update UKF with average velocity
            if velocities:
                avg_velocity = np.mean(velocities)
                self.update_ukf_with_radar(avg_velocity)
                
        except Exception as e:
            print(f"❌ Radar error: {e}")
            import traceback
            traceback.print_exc()
    
    def gps_callback(self, gps_data):
        """Process GPS"""
        try:
            self.data_count['gps'] += 1
            
            if self.gps_origin is None:
                self.gps_origin = (gps_data.latitude, gps_data.longitude, gps_data.altitude)
                print(f"📍 GPS origin: {self.gps_origin}")
            
            # Send to web viz
            if self.loop:
                message = {
                    'type': 'gps',
                    'latitude': gps_data.latitude,
                    'longitude': gps_data.longitude,
                    'altitude': gps_data.altitude
                }
                asyncio.run_coroutine_threadsafe(
                    self.data_ws.send_message(message),
                    self.loop
                )
            
            self.update_ukf_with_gps(gps_data)
            
        except Exception as e:
            print(f"GPS error: {e}")
    
    def imu_callback(self, imu_data):
        """Process IMU"""
        self.data_count['imu'] += 1
        
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        if 0 < dt < 1.0:
            self.ukf.predict(dt)
            self.ukf.x[9] = imu_data.gyroscope.z
    
    def update_ukf_with_gps(self, gps_data):
        """Update UKF with GPS"""
        if self.gps_origin is None:
            return
        
        x = (gps_data.longitude - self.gps_origin[1]) * 111320.0 * np.cos(np.radians(self.gps_origin[0]))
        y = (gps_data.latitude - self.gps_origin[0]) * 110540.0
        z = gps_data.altitude - self.gps_origin[2]
        
        measurement = np.array([x, y, z, self.ukf.x[3], self.ukf.x[4], self.ukf.x[5]])
        
        R_gps = np.eye(6)
        R_gps[0:3, 0:3] *= 2.0
        R_gps[3:6, 3:6] *= 10.0
        
        self.ukf.update(measurement, R=R_gps)
        self.publish_fused_state()
    
    def update_ukf_with_radar(self, velocity):
        """Update UKF with radar"""
        measurement = np.array([
            self.ukf.x[0], self.ukf.x[1], self.ukf.x[2],
            velocity, 0.0, 0.0
        ])
        
        R_radar = np.eye(6)
        R_radar[0:3, 0:3] *= 100.0
        R_radar[3:6, 3:6] *= 0.5
        
        self.ukf.update(measurement, R=R_radar)
    
    def publish_fused_state(self):
        """Publish fused pose"""
        try:
            # Send to web viz
            if self.loop:
                message = {
                    'type': 'pose',
                    'position': {
                        'x': float(self.ukf.x[0]),
                        'y': float(self.ukf.x[1]),
                        'z': float(self.ukf.x[2])
                    }
                }
                asyncio.run_coroutine_threadsafe(
                    self.data_ws.send_message(message),
                    self.loop
                )
                
        except Exception as e:
            print(f"Pose error: {e}")
    
    def update_spectator(self):
        """Update camera"""
        if self.vehicle:
            spectator = self.world.get_spectator()
            transform = self.vehicle.get_transform()
            spectator.set_transform(carla.Transform(
                transform.location + carla.Location(x=-8, z=4),
                carla.Rotation(pitch=-15, yaw=transform.rotation.yaw)
            ))
    
    def cleanup(self):
        """Cleanup"""
        print("\n🧹 Cleaning up...")
        for sensor in self.sensors.values():
            if sensor:
                sensor.destroy()
        if self.vehicle:
            self.vehicle.destroy()
        print("✅ Cleanup done")


async def run_data_ws(perception):
    """Run data WebSocket server"""
    await perception.data_ws.start()


def main():
    """Main"""
    print("=" * 60)
    print("🚗 CARLA Perception Stack with Web Viz")
    print("=" * 60)
    
    perception = PerceptionStack()
    
    print("\n[1/4] Connecting to CARLA...")
    if not perception.connect_to_carla():
        print("\n❌ Start CARLA first: CarlaUE4.exe")
        return
    
    print("[2/4] Spawning vehicle...")
    if not perception.spawn_vehicle():
        return
    
    time.sleep(1)
    
    print("[3/4] Setting up sensors...")
    perception.setup_sensors()
    
    print("[4/4] Starting servers...")
    
    # Start WebSocket server in thread
    def run_server():
        perception.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(perception.loop)
        perception.loop.run_until_complete(run_data_ws(perception))
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Start HTTP server in thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ SYSTEM READY!")
    print("=" * 60)
    print("🌐 Web Viz: http://localhost:9090")
    print("🌐 WebSocket: ws://localhost:8765")
    print("\n⌨️  Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    try:
        while True:
            perception.update_spectator()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n")
        perception.cleanup()


if __name__ == '__main__':
    main()