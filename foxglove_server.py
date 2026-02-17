#!/usr/bin/env python3
"""
Foxglove WebSocket Server for CARLA Data Visualization
Streams sensor data (camera, LIDAR, RADAR) in Foxglove-compatible format
"""

import carla
import asyncio
import json
from foxglove_websocket import FoxgloveWebSocketServer
from foxglove_websocket.msg import Image, Pose, PointCloud2
import numpy as np
import base64
import cv2
import time
from datetime import datetime
from collections import defaultdict

# Configuration
CARLA_HOST = 'localhost'
CARLA_PORT = 2000
FOXGLOVE_WS_PORT = 8766
FOXGLOVE_HTM_PORT = 8001

# Image dimensions
IM_WIDTH = 640
IM_HEIGHT = 480

# Global data buffer
sensor_data = {
    'camera_rgb': None,
    'camera_depth': None,
    'lidar_points': [],
    'radar_points': [],
    'ego_pose': {'x': 0, 'y': 0, 'z': 0, 'roll': 0, 'pitch': 0, 'yaw': 0},
    'timestamp': 0,
    'actors': []
}


frame_count = 0

# ============================================================================
# SENSOR CALLBACKS
# ============================================================================

def rgb_callback(image):
    """RGB camera callback"""
    array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
    array = np.reshape(array, (image.height, image.width, 4))
    sensor_data['camera_rgb'] = array[:, :, :3]
    sensor_data['timestamp'] = image.timestamp

def depth_callback(image):
    """Depth camera callback"""
    array = np.frombuffer(image.raw_data, dtype=np.dtype("float32"))
    # Depth images are single channel (height, width), not (height, width, 4)
    array = np.reshape(array, (image.height, image.width))
    sensor_data['camera_depth'] = array

def lidar_callback(data):
    """LIDAR callback - converts to point cloud"""
    points = np.frombuffer(data.raw_data, dtype=np.dtype('f4'))
    points = np.reshape(points, (int(points.shape[0] / 4), 4))
    # Keep only XYZ coordinates
    sensor_data['lidar_points'] = points[:, :3].tolist()

def radar_callback(data):
    """RADAR callback"""
    points = np.frombuffer(data.raw_data, dtype=np.dtype('f4'))
    points = np.reshape(points, (int(points.shape[0] / 4), 4))
    
    # Convert spherical coordinates to Cartesian
    cart_points = []
    for p in points:
        depth = p[3]
        azi = p[1]
        x = depth * np.cos(azi)
        y = depth * np.sin(azi)
        cart_points.append([x, y, 0])  # RADAR is 2D (XY)
    
    sensor_data['radar_points'] = cart_points

# ============================================================================
# FOXGLOVE MESSAGE BUILDERS
# ============================================================================

def build_camera_message(timestamp):
    """Build Foxglove-compatible camera message"""
    if sensor_data['camera_rgb'] is None:
        return None
    
    _, buffer = cv2.imencode('.jpg', sensor_data['camera_rgb'])
    image_b64 = base64.b64encode(buffer).decode('utf-8')
    
    return {
        'topic': '/camera/rgb',
        'timestamp': timestamp,
        'message': {
            'timestamp': timestamp,
            'frame_id': 'camera',
            'height': IM_HEIGHT,
            'width': IM_WIDTH,
            'encoding': 'jpeg',
            'data': image_b64
        }
    }

def build_lidar_message(timestamp):
    """Build Foxglove-compatible LIDAR point cloud message"""
    if not sensor_data['lidar_points']:
        return None
    
    points = np.array(sensor_data['lidar_points'], dtype=np.float32)
    
    return {
        'topic': '/lidar/points',
        'timestamp': timestamp,
        'message': {
            'timestamp': timestamp,
            'frame_id': 'lidar',
            'fields': [
                {'name': 'x', 'offset': 0, 'datatype': 7},    # 7 = FLOAT32
                {'name': 'y', 'offset': 4, 'datatype': 7},
                {'name': 'z', 'offset': 8, 'datatype': 7}
            ],
            'point_step': 12,  # 3 floats * 4 bytes
            'row_step': len(points) * 12,
            'height': 1,
            'width': len(points),
            'is_dense': True,
            'data': base64.b64encode(points.tobytes()).decode('utf-8')
        }
    }

def build_radar_message(timestamp):
    """Build Foxglove-compatible RADAR markers"""
    if not sensor_data['radar_points']:
        return None
    
    markers = []
    for i, point in enumerate(sensor_data['radar_points']):
        markers.append({
            'id': i,
            'ns': 'radar',
            'type': 2,  # Sphere
            'action': 0,  # Add/modify
            'pose': {
                'position': {'x': point[0], 'y': point[1], 'z': 0.5},
                'orientation': {'x': 0, 'y': 0, 'z': 0, 'w': 1}
            },
            'scale': {'x': 0.3, 'y': 0.3, 'z': 0.3},
            'color': {'r': 1.0, 'g': 0.0, 'b': 1.0, 'a': 1.0}  # Magenta
        })
    
    return {
        'topic': '/radar/markers',
        'timestamp': timestamp,
        'message': {
            'header': {
                'seq': 0,
                'stamp': timestamp,
                'frame_id': 'base_link'
            },
            'markers': markers
        }
    }

def build_ego_pose_message(timestamp, ego_transform):
    """Build ego vehicle pose message"""
    loc = ego_transform.location
    rot = ego_transform.rotation
    
    # Convert Euler angles to quaternion
    yaw = np.radians(rot.yaw)
    pitch = np.radians(rot.pitch)
    roll = np.radians(rot.roll)
    
    # Simple conversion (not ideal, but works for visualization)
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    
    return {
        'topic': '/ego_pose',
        'timestamp': timestamp,
        'message': {
            'header': {
                'seq': 0,
                'stamp': timestamp,
                'frame_id': 'world'
            },
            'pose': {
                'position': {'x': loc.x, 'y': loc.y, 'z': loc.z},
                'orientation': {'x': qx, 'y': qy, 'z': qz, 'w': qw}
            }
        }
    }

def build_vehicles_message(timestamp, ego_vehicle, actors):
    """Build message with all visible vehicle poses"""
    markers = []
    
    # Add ego vehicle
    ego_loc = ego_vehicle.get_location()
    ego_rot = ego_vehicle.get_transform().rotation
    markers.append({
        'id': -1,
        'ns': 'vehicles',
        'type': 1,  # Cube
        'action': 0,
        'pose': {
            'position': {'x': ego_loc.x, 'y': ego_loc.y, 'z': ego_loc.z},
            'orientation': {'x': 0, 'y': 0, 'z': 0, 'w': 1}
        },
        'scale': {'x': 2.0, 'y': 1.0, 'z': 1.5},
        'color': {'r': 1.0, 'g': 1.0, 'b': 0.0, 'a': 0.8}  # Yellow for ego
    })
    
    # Add other vehicles
    for i, actor in enumerate(actors):
        if 'vehicle' in actor.type_id:
            try:
                loc = actor.get_location()
                dist = ego_vehicle.get_location().distance(loc)
                
                if dist < 100:  # Only show nearby vehicles
                    markers.append({
                        'id': i,
                        'ns': 'vehicles',
                        'type': 1,
                        'action': 0,
                        'pose': {
                            'position': {'x': loc.x, 'y': loc.y, 'z': loc.z},
                            'orientation': {'x': 0, 'y': 0, 'z': 0, 'w': 1}
                        },
                        'scale': {'x': 2.0, 'y': 1.0, 'z': 1.5},
                        'color': {'r': 0.0, 'g': 0.0, 'b': 1.0, 'a': 0.8}  # Blue for NPCs
                    })
            except:
                pass
    
    return {
        'topic': '/vehicles/markers',
        'timestamp': timestamp,
        'message': {
            'header': {
                'seq': 0,
                'stamp': timestamp,
                'frame_id': 'world'
            },
            'markers': markers
        }
    }

# ============================================================================

# FOXGLOVE-SDK SERVER
async def run_foxglove_server(ego_vehicle, world):
    server = FoxgloveWebSocketServer(port=FOXGLOVE_WS_PORT)
    print(f"\n🚀 Starting Foxglove WebSocket on ws://localhost:{FOXGLOVE_WS_PORT}")
    print(f"📱 Open: http://localhost:{FOXGLOVE_HTM_PORT}/foxglove.html")
    print("=" * 60)

    # Register topics
    server.add_topic(
        topic="/camera/rgb",
        encoding="json",
        schema=Image.__schema__,
    )
    server.add_topic(
        topic="/lidar/points",
        encoding="json",
        schema=PointCloud2.__schema__,
    )
    server.add_topic(
        topic="/ego_pose",
        encoding="json",
        schema=Pose.__schema__,
    )
    # Add more topics as needed

    async def publish_loop():
        global frame_count
        actors = world.get_actors()
        while True:
            timestamp = int(time.time() * 1000)
            # Camera
            cam_msg = build_camera_message(timestamp)
            if cam_msg:
                await server.send_message("/camera/rgb", cam_msg['message'])
            # LIDAR
            lidar_msg = build_lidar_message(timestamp)
            if lidar_msg:
                await server.send_message("/lidar/points", lidar_msg['message'])
            # Ego Pose
            ego_pose_msg = build_ego_pose_message(timestamp, ego_vehicle.get_transform())
            if ego_pose_msg:
                await server.send_message("/ego_pose", ego_pose_msg['message'])
            # Add more publishers as needed
            frame_count += 1
            if frame_count % 20 == 0:
                print(f"📡 Foxglove: Sent frame {frame_count}")
            await asyncio.sleep(0.05)

    await asyncio.gather(server.start(), publish_loop())

# ============================================================================
# MAIN
# ============================================================================


async def main():
    # Connect to CARLA
    print("🔗 Connecting to CARLA...")
    client = carla.Client(CARLA_HOST, CARLA_PORT)
    client.set_timeout(10.0)
    world = client.get_world()
    bp_lib = world.get_blueprint_library()

    # Spawn or get ego vehicle
    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        print("❌ No spawn points!")
        return

    ego_bp = bp_lib.find('vehicle.tesla.model3')
    ego_vehicle = world.spawn_actor(ego_bp, spawn_points[0])
    ego_vehicle.set_simulate_physics(True)
    ego_vehicle.set_autopilot(True)
    print(f"✅ Ego vehicle spawned")

    # Setup sensors
    # RGB Camera
    cam_bp = bp_lib.find('sensor.camera.rgb')
    cam_bp.set_attribute('image_size_x', str(IM_WIDTH))
    cam_bp.set_attribute('image_size_y', str(IM_HEIGHT))
    cam_bp.set_attribute('fov', '90')
    sensor_rgb = world.spawn_actor(cam_bp, carla.Transform(carla.Location(x=1.5, z=2.4)), attach_to=ego_vehicle)
    sensor_rgb.listen(rgb_callback)
    print("✅ RGB Camera attached")

    # Depth Camera
    depth_bp = bp_lib.find('sensor.camera.depth')
    depth_bp.set_attribute('image_size_x', str(IM_WIDTH))
    depth_bp.set_attribute('image_size_y', str(IM_HEIGHT))
    depth_bp.set_attribute('fov', '90')
    sensor_depth = world.spawn_actor(depth_bp, carla.Transform(carla.Location(x=1.5, z=2.4)), attach_to=ego_vehicle)
    sensor_depth.listen(depth_callback)
    print("✅ Depth Camera attached")

    # LIDAR
    lidar_bp = bp_lib.find('sensor.lidar.ray_cast')
    lidar_bp.set_attribute('range', '50')
    sensor_lidar = world.spawn_actor(lidar_bp, carla.Transform(carla.Location(x=0, z=2.4)), attach_to=ego_vehicle)
    sensor_lidar.listen(lidar_callback)
    print("✅ LIDAR attached")

    # RADAR
    radar_bp = bp_lib.find('sensor.other.radar')
    sensor_radar = world.spawn_actor(radar_bp, carla.Transform(carla.Location(x=1.5, z=1.0)), attach_to=ego_vehicle)
    sensor_radar.listen(radar_callback)
    print("✅ RADAR attached")

    # Start Foxglove SDK server
    await run_foxglove_server(ego_vehicle, world)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except ConnectionRefusedError:
        print("\n❌ Cannot connect to CARLA on localhost:2000")
        print("Make sure CARLA is running: CarlaUE4.exe -windowed -carla-port=2000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
