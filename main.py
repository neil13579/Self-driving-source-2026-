import carla
import random
import time
import numpy as np
import cv2
import asyncio
import websockets
import json
import base64
import math
import tensorflow as tf
from filterpy.kalman import MerweScaledSigmaPoints
from filterpy.kalman import UnscentedKalmanFilter as UKF
from filterpy.common import Q_discrete_white_noise

# --- Configuration ---
HOST = 'localhost'
PORT = 2000
WS_PORT = 8765
IM_WIDTH = 640
IM_HEIGHT = 480
# Track the vehicle immediately in front of us
TARGET_ID = None 

# --- TensorFlow Segmentation Pipeline ---
# Maps CARLA class IDs to CityScapes Palette
def build_tf_segmentation_mapper():
    # Palette (Road=Purple, Car=Blue, Pedestrian=Red, etc.)
    palette = tf.constant([
        [0, 0, 0], [128, 64, 128], [244, 35, 232], [70, 70, 70], [102, 102, 156],
        [190, 153, 153], [153, 153, 153], [250, 170, 30], [220, 220, 0], 
        [107, 142, 35], [152, 251, 152], [70, 130, 180], [220, 20, 60]
    ], dtype=tf.int32)
    
    @tf.function
    def process_sem_seg(image_tensor):
        # CARLA encodes tag in the Red channel
        tag_ids = image_tensor[:, :, 2] 
        tag_ids = tf.clip_by_value(tag_ids, 0, 12)
        colored_image = tf.gather(palette, tag_ids)
        return tf.cast(colored_image, tf.uint8)
    
    return process_sem_seg

tf_processor = build_tf_segmentation_mapper()

# --- UKF Setup (Sensor Fusion) ---
def fx(x, dt):
    # Constant Velocity Model: state [x, y, vx, vy]
    F = np.array([[1, 0, dt, 0],
                  [0, 1, 0, dt],
                  [0, 0, 1, 0],
                  [0, 0, 0, 1]])
    return np.dot(F, x)

def hx(x):
    # Measurement function: sensors return [x, y]
    return np.array([x[0], x[1]])

# Initialize UKF
points = MerweScaledSigmaPoints(n=4, alpha=.1, beta=2., kappa=-1)
ukf = UKF(dim_x=4, dim_z=2, fx=fx, hx=hx, dt=0.05, points=points)
ukf.x = np.array([0., 0., 0., 0.])
ukf.P *= 0.2
ukf.R = np.diag([0.5, 0.5]) # Sensor noise covariance
ukf.Q = Q_discrete_white_noise(dim=2, dt=0.05, var=0.01, block_size=2)

# --- Global State ---
data_buffer = {
    'rgb': None,
    'seg': None,
    'lidar': [],
    'radar': [],
    'ukf': [0, 0]
}

# --- 3D to 2D Projection Utils ---
def build_projection_matrix(w, h, fov):
    focal = w / (2.0 * np.tan(fov * np.pi / 360.0))
    K = np.identity(3)
    K[0, 0] = K[1, 1] = focal
    K[0, 2] = w / 2.0
    K[1, 2] = h / 2.0
    return K

def get_image_point(loc, K, w2c):
    # Calculate 2D projection of 3D coordinate
    point = np.array([loc.x, loc.y, loc.z, 1])
    # transform to camera coordinates
    point_camera = np.dot(w2c, point)
    
    # New we must change from UE4's coordinate system to an "standard"
    # (x, y ,z) -> (y, -z, x)
    # and we remove the fourth component also
    point_camera = [point_camera[1], -point_camera[2], point_camera[0]]
    
    # now project 3D->2D using the camera matrix
    point_img = np.dot(K, point_camera)
    
    # normalize
    point_img[0] /= point_img[2]
    point_img[1] /= point_img[2]
    
    return point_img[0], point_img[1]

# --- Sensor Callbacks ---
def rgb_callback(image):
    array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
    array = np.reshape(array, (image.height, image.width, 4))
    data_buffer['rgb'] = array[:, :, :3]

def seg_callback(image):
    array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
    array = np.reshape(array, (image.height, image.width, 4))
    # Process via TensorFlow
    tensor = tf.convert_to_tensor(array)
    colored = tf_processor(tensor)
    data_buffer['seg'] = colored.numpy()

def lidar_callback(data):
    # Get points relative to Ego
    points = np.frombuffer(data.raw_data, dtype=np.dtype('f4'))
    points = np.reshape(points, (int(points.shape[0] / 4), 4))
    # Filter points for visualization (downsample)
    data_buffer['lidar'] = points[::10, :2] 

    # UKF Step: If we are tracking a target, fuse Lidar points near it
    # Ideally, you use a clustering algo here. For demo, we just feed the center of points.
    if len(points) > 0:
        center = np.mean(points[:, :2], axis=0)
        # Only update UKF if measurements are reasonable (simple gating)
        if abs(center[0]) < 50: 
            ukf.predict()
            ukf.update(center)
            data_buffer['ukf'] = ukf.x[:2].tolist()

def radar_callback(data):
    points = np.frombuffer(data.raw_data, dtype=np.dtype('f4'))
    points = np.reshape(points, (int(points.shape[0] / 4), 4))
    # Radar Data: [vel, azimuth, altitude, depth]
    # Convert to XY for visualization
    cart_points = []
    for p in points:
        depth = p[3]
        azi = p[1]
        x = depth * np.cos(azi)
        y = depth * np.sin(azi)
        cart_points.append([x, y])
    data_buffer['radar'] = np.array(cart_points)

# --- Main Loop ---
async def main():
    client = carla.Client(HOST, PORT)
    client.set_timeout(10.0)
    world = client.get_world()
    bp_lib = world.get_blueprint_library()
    
    # 1. Setup Traffic
    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        print("ERROR: No spawn points available in map!")
        return
    
    ego_bp = bp_lib.find('vehicle.tesla.model3')
    if ego_bp is None:
        print("ERROR: Tesla Model 3 blueprint not found!")
        return
    
    # Spawn ego vehicle with proper physics
    ego_vehicle = world.spawn_actor(ego_bp, spawn_points[0])
    if ego_vehicle is None:
        print("ERROR: Failed to spawn ego vehicle!")
        return
    
    # Ensure physics is enabled
    ego_vehicle.set_simulate_physics(True)
    
    # Initialize Traffic Manager properly
    try:
        # Try port 8000, if fails try 8001
        traffic_manager = client.get_trafficmanager()
        traffic_manager.set_global_distance_to_leading_vehicle(2.0)
        ego_vehicle.set_autopilot(True)
        print(f"✅ Traffic Manager initialized")
    except Exception as tm_error:
        print(f"⚠️  Traffic Manager init failed: {tm_error}")
        print("   Continuing without autopilot...")
        # Continue without autopilot rather than crashing
    
    print(f"✅ Ego vehicle spawned at {spawn_points[0].location}")
    
    actors = []
    # Spawn NPCs
    for i in range(10):
        bp = random.choice(bp_lib.filter('vehicle'))
        t = random.choice(spawn_points)
        npc = world.try_spawn_actor(bp, t)
        if npc:
            npc.set_autopilot(True)
            actors.append(npc)
    
    # Spawn Walkers
    walker_bp = bp_lib.filter("walker.pedestrian.*")[0]
    for i in range(5):
        t = carla.Transform(world.get_random_location_from_navigation())
        w = world.try_spawn_actor(walker_bp, t)
        if w: actors.append(w)

    # 2. Setup Sensors
    # Camera RGB
    cam_bp = bp_lib.find('sensor.camera.rgb')
    cam_bp.set_attribute('image_size_x', str(IM_WIDTH))
    cam_bp.set_attribute('image_size_y', str(IM_HEIGHT))
    cam_bp.set_attribute('fov', '90')
    sensor_rgb = world.spawn_actor(cam_bp, carla.Transform(carla.Location(x=1.5, z=2.4)), attach_to=ego_vehicle)
    sensor_rgb.listen(rgb_callback)
    print("✅ RGB Camera attached")

    # Camera Seg (U-Net Input)
    seg_bp = bp_lib.find('sensor.camera.semantic_segmentation')
    seg_bp.set_attribute('image_size_x', str(IM_WIDTH))
    seg_bp.set_attribute('image_size_y', str(IM_HEIGHT))
    seg_bp.set_attribute('fov', '90')
    sensor_seg = world.spawn_actor(seg_bp, carla.Transform(carla.Location(x=1.5, z=2.4)), attach_to=ego_vehicle)
    sensor_seg.listen(seg_callback)
    print("✅ Segmentation Camera attached")

    # Lidar
    lidar_bp = bp_lib.find('sensor.lidar.ray_cast')
    lidar_bp.set_attribute('range', '50')
    sensor_lidar = world.spawn_actor(lidar_bp, carla.Transform(carla.Location(x=0, z=2.4)), attach_to=ego_vehicle)
    sensor_lidar.listen(lidar_callback)
    print("✅ LIDAR attached")

    # Radar
    radar_bp = bp_lib.find('sensor.other.radar')
    sensor_radar = world.spawn_actor(radar_bp, carla.Transform(carla.Location(x=1.5, z=1.0)), attach_to=ego_vehicle)
    sensor_radar.listen(radar_callback)
    print("✅ RADAR attached")

    print("Simulation Running. Connect Browser to localhost:8765")
    
    # Matrix for Projection
    K = build_projection_matrix(IM_WIDTH, IM_HEIGHT, 90.0)

    # 3. WebSocket Handler
    ws_frame_count = 0
    
    async def ws_handler(*args):
        # Support both websockets handler signatures (websocket, path) and single-arg connection
        nonlocal ws_frame_count
        if len(args) == 1:
            websocket = args[0]
            path = None
        else:
            websocket, path = args

        try:
            remote = getattr(websocket, 'remote_address', None)
            print(f"✅ WebSocket client connected from {remote}")
            while True:
                if data_buffer['rgb'] is not None and data_buffer['seg'] is not None:
                    ws_frame_count += 1
                    
                    # Encode Images
                    _, img_enc = cv2.imencode('.jpg', data_buffer['rgb'])
                    rgb_b64 = base64.b64encode(img_enc).decode('utf-8')
                    
                    _, seg_enc = cv2.imencode('.jpg', data_buffer['seg'])
                    seg_b64 = base64.b64encode(seg_enc).decode('utf-8')

                    # Calculate Bounding Boxes
                    world_2_camera = np.array(sensor_rgb.get_transform().get_inverse_matrix())
                    boxes = []
                    
                    for npc in actors:
                        # Filter only visible
                        dist = npc.get_location().distance(ego_vehicle.get_location())
                        if dist < 50:
                            pos = npc.get_transform().location
                            # Simple 1-point box for demo (centroid)
                            u, v = get_image_point(pos, K, world_2_camera)
                            if 0 <= u <= IM_WIDTH and 0 <= v <= IM_HEIGHT:
                                boxes.append({
                                    'id': npc.id, 
                                    'u': u, 'v': v, 
                                    'dist': round(dist, 2)
                                })

                    # Prepare Payload
                    payload = {
                        'rgb': rgb_b64,
                        'seg': seg_b64,
                        'ukf': data_buffer['ukf'],
                        'boxes': boxes,
                        'lidar': data_buffer['lidar'].tolist() if len(data_buffer['lidar']) > 0 else [],
                        'radar': data_buffer['radar'].tolist() if len(data_buffer['radar']) > 0 else []
                    }
                    
                    await websocket.send(json.dumps(payload))
                    
                    if ws_frame_count % 20 == 0:
                        print(f"📊 WebSocket: Sent {ws_frame_count} frames, {len(boxes)} actors visible")
                    
                    await asyncio.sleep(0.05) # ~20 FPS
                else:
                    await asyncio.sleep(0.05)
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            import traceback
            traceback.print_exc()

    # Start WebSocket Server
    try:
        print(f"\n🚀 Starting WebSocket server on ws://localhost:{WS_PORT}")
        print("📱 Open http://localhost/ in your browser to view visualization")
        print("=" * 60)
        
        server = await websockets.serve(ws_handler, "localhost", WS_PORT)
        print("✅ WebSocket server ready! Waiting for connections...")
        
        await server.wait_closed()
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup (important!)
        print("\n🛑 Cleaning up...")
        try:
            ego_vehicle.destroy()
            sensor_rgb.destroy()
            sensor_seg.destroy()
            sensor_lidar.destroy()
            sensor_radar.destroy()
            for a in actors: 
                try:
                    a.destroy()
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("🎮 CARLA UKF Perception System")
    print("=" * 60)
    print("Connecting to CARLA at localhost:2000...")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping by user request...")
    except ConnectionRefusedError:
        print("\n\n❌ ERROR: Cannot connect to CARLA!")
        print("Make sure CARLA simulator is running:")
        print("  CarlaUE4.exe -windowed -carla-port=2000")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()