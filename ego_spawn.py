import carla
import argparse
import time
import math
import logging
import random
import subprocess
import platform
import os
import numpy as np
import threading

# --- Embedded ego_SEAL (ES-EKF) code ---
def angle_normalize(x):
    return ((x + np.pi) % (2 * np.pi)) - np.pi


def skew_symmetric(v):
    v = np.asarray(v).reshape(3)
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])


class Quaternion:
    """Minimal quaternion helper with the operations needed by the EKF code.

    Representation: a numpy array [w, x, y, z]
    """

    def __init__(self, w=1.0, x=0.0, y=0.0, z=0.0, euler=None, axis_angle=None):
        if euler is not None:
            cr = math.cos(euler[0] / 2.0)
            sr = math.sin(euler[0] / 2.0)
            cp = math.cos(euler[1] / 2.0)
            sp = math.sin(euler[1] / 2.0)
            cy = math.cos(euler[2] / 2.0)
            sy = math.sin(euler[2] / 2.0)
            w = cr * cp * cy + sr * sp * sy
            x = sr * cp * cy - cr * sp * sy
            y = cr * sp * cy + sr * cp * sy
            z = cr * cp * sy - sr * sp * cy
        elif axis_angle is not None:
            theta = np.linalg.norm(axis_angle)
            if theta < 1e-12:
                w, x, y, z = 1.0, 0.0, 0.0, 0.0
            else:
                axis = axis_angle / theta
                w = math.cos(theta / 2.0)
                s = math.sin(theta / 2.0)
                x, y, z = axis * s

        self.q = np.array([w, x, y, z], dtype=float)
        self.normalize()

    def to_numpy(self):
        return self.q.copy()

    def normalize(self):
        n = np.linalg.norm(self.q)
        if n > 0:
            self.q /= n

    @staticmethod
    def from_numpy(qarr):
        q = Quaternion()
        q.q = np.array(qarr, dtype=float)
        q.normalize()
        return q

    def to_mat(self):
        w, x, y, z = self.q
        R = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]
        ])
        return R

    def quat_mult_right(self, other_q):
        a = self.q
        b = np.asarray(other_q)
        w1, x1, y1, z1 = a
        w2, x2, y2, z2 = b
        w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
        x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        return np.array([w, x, y, z])

    def to_euler(self):
        w, x, y, z = self.q
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(t0, t1)
        t2 = +2.0 * (w * y - z * x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch = math.asin(t2)
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(t3, t4)
        return np.array([roll, pitch, yaw])


class EgoSEAL:
    def __init__(self, var_imu_f=0.01, var_imu_w=0.01, var_gnss=0.001, var_lidar=0.1, vel_ema_alpha=0.3):
        self.var_imu_f = var_imu_f
        self.var_imu_w = var_imu_w
        self.var_gnss = var_gnss  # Strongly trust GNSS measurements
        self.var_lidar = var_lidar  # Strongly trust LIDAR measurements
        # EMA alpha for velocity smoothing during online estimate
        self.vel_ema_alpha = vel_ema_alpha

        self.imu_ts = []
        self.imu_f = []
        self.imu_w = []

        self.gnss_ts = []
        self.gnss_pos = []

        self.lidar_ts = []
        self.lidar_pos = []

        self._lock = threading.Lock()
        self._attached_sensors = {'imu': None, 'gnss': None, 'lidar': None}

    def imu_callback(self, msg):
        with self._lock:
            try:
                if hasattr(msg, 'timestamp'):
                    t = msg.timestamp
                    accel = np.array([msg.accelerometer.x, msg.accelerometer.y, msg.accelerometer.z])
                    gyro = np.array([msg.gyroscope.x, msg.gyroscope.y, msg.gyroscope.z])
                elif isinstance(msg, dict):
                    t = msg.get('t')
                    accel = np.asarray(msg.get('accel'))
                    gyro = np.asarray(msg.get('gyro'))
                else:
                    t = getattr(msg, 't', time.time())
                    accel = np.asarray(getattr(msg, 'accel', getattr(msg, 'accelerometer', [0, 0, 0])))
                    gyro = np.asarray(getattr(msg, 'gyro', getattr(msg, 'gyroscope', [0, 0, 0])))
            except Exception:
                t = time.time()
                accel = np.zeros(3)
                gyro = np.zeros(3)

            self.imu_ts.append(t)
            self.imu_f.append(np.asarray(accel, dtype=float))
            self.imu_w.append(np.asarray(gyro, dtype=float))

    def gnss_callback(self, msg):
        with self._lock:
            try:
                if hasattr(msg, 'timestamp') and hasattr(msg, 'latitude'):
                    t = msg.timestamp
                    pos = np.array([msg.latitude, msg.longitude, msg.altitude])
                elif isinstance(msg, dict):
                    t = msg.get('t')
                    pos = np.asarray(msg.get('pos'))
                else:
                    t = getattr(msg, 't', time.time())
                    pos = np.asarray(getattr(msg, 'pos', [0, 0, 0]))
            except Exception:
                t = time.time()
                pos = np.zeros(3)

            self.gnss_ts.append(t)
            self.gnss_pos.append(pos)

    def lidar_callback(self, msg):
        with self._lock:
            try:
                if isinstance(msg, dict):
                    t = msg.get('t')
                    pos = np.asarray(msg.get('pos'))
                else:
                    t = getattr(msg, 't', time.time())
                    pos = np.asarray(getattr(msg, 'pos', [0, 0, 0]))
            except Exception:
                t = time.time()
                pos = np.zeros(3)

            self.lidar_ts.append(t)
            self.lidar_pos.append(pos)

    def attach_listeners(self, ego_vehicle=None, imu=None, gnss=None, lidar=None):
        try:
            if imu is not None:
                prev = self._attached_sensors.get('imu')
                if prev is not None and prev is not imu:
                    try:
                        prev.stop()
                    except Exception:
                        pass
                if self._attached_sensors.get('imu') is not imu:
                    imu.listen(lambda m: self.imu_callback(m))
                    self._attached_sensors['imu'] = imu

            if gnss is not None:
                prev = self._attached_sensors.get('gnss')
                if prev is not None and prev is not gnss:
                    try:
                        prev.stop()
                    except Exception:
                        pass
                if self._attached_sensors.get('gnss') is not gnss:
                    gnss.listen(lambda m: self.gnss_callback(m))
                    self._attached_sensors['gnss'] = gnss

            if lidar is not None:
                prev = self._attached_sensors.get('lidar')
                if prev is not None and prev is not lidar:
                    try:
                        prev.stop()
                    except Exception:
                        pass
                if self._attached_sensors.get('lidar') is not lidar:
                    lidar.listen(lambda m: self.lidar_callback(m))
                    self._attached_sensors['lidar'] = lidar
        except Exception:
            return

    def detach_listeners(self):
        for key, actor in list(self._attached_sensors.items()):
            if actor is not None:
                try:
                    actor.stop()
                except Exception:
                    pass
                self._attached_sensors[key] = None

    def estimate(self):
        with self._lock:
            imu_ts = np.array(self.imu_ts)
            imu_f = np.array(self.imu_f)
            imu_w = np.array(self.imu_w)
            gnss_ts = np.array(self.gnss_ts)
            gnss_pos = np.array(self.gnss_pos)
            lidar_ts = np.array(self.lidar_ts)
            lidar_pos = np.array(self.lidar_pos)

        if imu_ts.size == 0:
            raise RuntimeError('No IMU data buffered; cannot run estimator')

        N = imu_ts.shape[0]
        p_est = np.zeros([N, 3])
        v_est = np.zeros([N, 3])
        q_est = np.zeros([N, 4])
        p_cov = np.zeros([N, 9, 9])

        p0 = gnss_pos[0] if gnss_pos.size > 0 else (lidar_pos[0] if lidar_pos.size > 0 else np.zeros(3))
        # Initialize velocity to zero and let filter estimate it from measurements
        # Using ground truth velocity would bias the filter in simulation
        v0 = np.zeros(3)
        q0 = Quaternion().to_numpy()

        p_est[0] = p0
        v_est[0] = v0
        q_est[0] = q0
        # Normalize initial quaternion
        q_est[0] = q_est[0] / np.linalg.norm(q_est[0])
        # Initialize covariance with reasonable uncertainty
        p_cov[0] = np.eye(9) * 0.1

        l_jac = np.zeros([9, 6]); l_jac[3:, :] = np.eye(6)
        h_jac = np.zeros([3, 9]); h_jac[:, :3] = np.eye(3)
        g = np.array([0, 0, -9.81])

        gnss_i = 0
        lidar_i = 0

        if imu_ts.max() > 1e6:
            imu_ts = imu_ts * 1e-3
            gnss_ts = gnss_ts * 1e-3 if gnss_ts.size else gnss_ts
            lidar_ts = lidar_ts * 1e-3 if lidar_ts.size else lidar_ts

        for k in range(1, N):
            delta_t = imu_ts[k] - imu_ts[k - 1]
            if delta_t <= 0:
                delta_t = 1e-3

            rotation_matrix = Quaternion.from_numpy(q_est[k-1]).to_mat()

            p_est[k] = p_est[k-1] + delta_t * v_est[k-1] + (delta_t**2 / 2) * (rotation_matrix.dot(imu_f[k-1]) + g)
            v_est[k] = v_est[k-1] + delta_t * (rotation_matrix.dot(imu_f[k-1]) + g)
            q_est[k] = Quaternion(axis_angle=imu_w[k-1] * delta_t).quat_mult_right(q_est[k-1])
            # Normalize quaternion to prevent numerical drift
            q_est[k] = q_est[k] / np.linalg.norm(q_est[k])

            F = np.identity(9)
            Q = np.identity(6)
            F[:3, 3:6] = delta_t * np.identity(3)
            F[3:6, 6:] = -rotation_matrix.dot(skew_symmetric(imu_f[k-1]))
            Q[:3, :3] = self.var_imu_f * delta_t**2 * np.identity(3)
            Q[3:, 3:] = self.var_imu_w * delta_t**2 * np.identity(3)
            p_cov[k] = F.dot(p_cov[k-1]).dot(F.T) + l_jac.dot(Q).dot(l_jac.T)

            # Measurement synchronization with tolerance for timestamp matching
            if lidar_i < lidar_ts.shape[0] and abs(lidar_ts[lidar_i] - imu_ts[k]) < 1e-2:
                y_k = lidar_pos[lidar_i]
                p_est[k], v_est[k], q_est[k], p_cov[k] = measurement_update(self.var_lidar, p_cov[k], y_k, p_est[k], v_est[k], q_est[k])
                lidar_i += 1

            if gnss_i < gnss_ts.shape[0] and abs(gnss_ts[gnss_i] - imu_ts[k]) < 1e-2:
                y_k = gnss_pos[gnss_i]
                p_est[k], v_est[k], q_est[k], p_cov[k] = measurement_update(self.var_gnss, p_cov[k], y_k, p_est[k], v_est[k], q_est[k])
                gnss_i += 1

            # Apply EMA smoothing to velocity to reduce high-frequency spikes
            try:
                v_est[k] = self.vel_ema_alpha * v_est[k] + (1.0 - self.vel_ema_alpha) * v_est[k-1]
            except Exception:
                pass

        print(f"Filter Statistics:")
        print(f"Total measurements - GNSS: {gnss_i}, LIDAR: {lidar_i}")
        print(f"Final position: [{p_est[-1,0]:.2f}, {p_est[-1,1]:.2f}, {p_est[-1,2]:.2f}]")
        print(f"Final velocity: [{v_est[-1,0]:.2f}, {v_est[-1,1]:.2f}, {v_est[-1,2]:.2f}]")
        print(f"Sensor variances - IMU_F: {self.var_imu_f}, IMU_W: {self.var_imu_w}, GNSS: {self.var_gnss}, LIDAR: {self.var_lidar}\n")

        return p_est, v_est, q_est, p_cov


def measurement_update(sensor_var, p_cov_check, y_k, p_check, v_check, q_check):
    I = np.identity(3)
    R = I * sensor_var
    h_jac = np.zeros([3, 9]); h_jac[:, :3] = np.eye(3)
    K = p_cov_check.dot(h_jac.T).dot(np.linalg.inv(h_jac.dot(p_cov_check).dot(h_jac.T) + R))

    error = K.dot(y_k - p_check)

    p_del = error[:3]
    v_del = error[3:6]
    phi_del = error[6:]

    p_hat = p_check + p_del
    v_hat = v_check + v_del
    q_hat = Quaternion(euler=phi_del).quat_mult_right(q_check)

    p_cov_hat = (np.identity(9) - K.dot(h_jac)).dot(p_cov_check)
    return p_hat, v_hat, q_hat, p_cov_hat

# --- End embedded ego_SEAL ---


def cleanup_carla():
    """Try to cleanup any existing CARLA processes"""
    if platform.system() == "Windows":
        try:
            # Kill any existing carla processes
            subprocess.run(['taskkill', '/F', '/IM', 'CarlaUE4.exe'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            time.sleep(2)  # Give some time for cleanup
        except Exception as e:
            logging.warning(f"Failed to cleanup CARLA processes: {e}")

def try_connect_carla(client, max_retries=3, retry_delay=5):
    """Try to connect to CARLA with retries"""
    for attempt in range(max_retries):
        try:
            return client.get_world()
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"Connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise e

def main():
    argparser = argparse.ArgumentParser(
        description=__doc__)
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    args = argparser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    # Try to cleanup any existing CARLA processes first
    cleanup_carla()

    client = carla.Client(args.host, args.port)
    client.set_timeout(20.0)  # Increased timeout
    try:
        ego_vehicle = None
        ego_cam = None
        ego_col = None
        ego_lane = None
        ego_obs = None
        ego_gnss = None
        ego_imu = None
        seal = None

        # Try to connect to the world with retries
        try:
            logging.info("Attempting to connect to CARLA simulator...")
            world = try_connect_carla(client)
            logging.info("Successfully connected to CARLA simulator")
        except Exception as e:
            logging.error(f"Failed to connect to CARLA simulator after multiple attempts: {e}")
            logging.error("Make sure the CARLA simulator is running and accessible at {}:{}".format(args.host, args.port))
            logging.error("Try restarting the CARLA simulator and this script")
            return  # Exit the function if we can't connect

        # --------------
        # Start recording
        # --------------
        '''
        client.start_recorder('~/tutorial/recorder/recording01.log')
        '''

        # --------------
        # Spawn ego vehicle
        # --------------
    
        ego_bp = world.get_blueprint_library().find('vehicle.tesla.model3')
        ego_bp.set_attribute('role_name','ego')
        print('\nEgo role_name is set')
        ego_color = random.choice(ego_bp.get_attribute('color').recommended_values)
        ego_bp.set_attribute('color',ego_color)
        print('\nEgo color is set')

        spawn_points = world.get_map().get_spawn_points()
        number_of_spawn_points = len(spawn_points)

        if 0 < number_of_spawn_points:
            random.shuffle(spawn_points)
            ego_transform = spawn_points[0]
            ego_vehicle = world.spawn_actor(ego_bp,ego_transform)
            print('\nEgo is spawned')
        else: 
            logging.warning('Could not found any spawn points')
    

        # --------------
        # Add a RGB camera sensor to ego vehicle. 
        # --------------
    
        cam_bp = None
        cam_bp = world.get_blueprint_library().find('sensor.camera.rgb')
        cam_bp.set_attribute("image_size_x",str(1920))
        cam_bp.set_attribute("image_size_y",str(1080))
        cam_bp.set_attribute("fov",str(105))
        cam_location = carla.Location(2,0,1)
        cam_rotation = carla.Rotation(0,180,0)
        cam_transform = carla.Transform(cam_location,cam_rotation)
        ego_cam = world.spawn_actor(cam_bp,cam_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.Rigid)
        ego_cam.listen(lambda image: image.save_to_disk('~/tutorial/output/%.6d.jpg' % image.frame))
    

        # --------------
        # Add collision sensor to ego vehicle. 
        # --------------
    
        col_bp = world.get_blueprint_library().find('sensor.other.collision')
        col_location = carla.Location(0,0,0)
        col_rotation = carla.Rotation(0,0,0)
        col_transform = carla.Transform(col_location,col_rotation)
        ego_col = world.spawn_actor(col_bp,col_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.Rigid)
        def col_callback(colli):
            print("Collision detected:\n"+str(colli)+'\n')
        ego_col.listen(lambda colli: col_callback(colli))
    

        # --------------
        # Add Lane invasion sensor to ego vehicle. 
        # --------------
    
        lane_bp = world.get_blueprint_library().find('sensor.other.lane_invasion')
        lane_location = carla.Location(0,0,0)
        lane_rotation = carla.Rotation(0,0,0)
        lane_transform = carla.Transform(lane_location,lane_rotation)
        ego_lane = world.spawn_actor(lane_bp,lane_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.Rigid)
        def lane_callback(lane):
            print("Lane invasion detected:\n"+str(lane)+'\n')
        ego_lane.listen(lambda lane: lane_callback(lane))
    

        # --------------
        # Add Obstacle sensor to ego vehicle. 
        # --------------
        
        obs_bp = world.get_blueprint_library().find('sensor.other.obstacle')
        obs_bp.set_attribute("only_dynamics",str(True))
        obs_location = carla.Location(0,0,0)
        obs_rotation = carla.Rotation(0,0,0)
        obs_transform = carla.Transform(obs_location,obs_rotation)
        ego_obs = world.spawn_actor(obs_bp,obs_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.Rigid)
        def obs_callback(obs):
            print("Obstacle detected:\n"+str(obs)+'\n')
        ego_obs.listen(lambda obs: obs_callback(obs))
        

        # --------------
        # Add GNSS sensor to ego vehicle. 
        # --------------
    
        gnss_bp = world.get_blueprint_library().find('sensor.other.gnss')
        gnss_location = carla.Location(0,0,0)
        gnss_rotation = carla.Rotation(0,0,0)
        gnss_transform = carla.Transform(gnss_location,gnss_rotation)
        gnss_bp.set_attribute("sensor_tick",str(3.0))
        ego_gnss = world.spawn_actor(gnss_bp,gnss_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.Rigid)
        def gnss_callback(gnss):
            print("GNSS measure:\n"+str(gnss)+'\n')
        

        # --------------
        # Add IMU sensor to ego vehicle. 
        # --------------
        
        imu_bp = world.get_blueprint_library().find('sensor.other.imu')
        imu_location = carla.Location(0,0,0)
        imu_rotation = carla.Rotation(0,0,0)
        imu_transform = carla.Transform(imu_location,imu_rotation)
        imu_bp.set_attribute("sensor_tick",str(3.0))
        ego_imu = world.spawn_actor(imu_bp,imu_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.Rigid)
        def imu_callback(imu):
            print("IMU measure:\n"+str(imu)+'\n')
        # NOTE: do not call .listen() here for IMU/GNSS when the actor is
        # attached to `EgoSEAL` (seal.attach_listeners). The `EgoSEAL` instance
        # will call `.listen()` itself. Calling `.listen()` twice on the same
        # actor causes CARLA to attempt duplicate stream registration and can
        # trigger the server-side assertion about duplicate stream IDs.


        # --- State Estimation with embedded SEAL ---
        # Create SEAL estimator with tuned sensor variances and velocity smoothing
        seal = EgoSEAL(var_imu_f=0.01, var_imu_w=0.01, var_gnss=0.001, var_lidar=0.1, vel_ema_alpha=0.3)

        # Instead of calling `seal.attach_listeners()` which would call `.listen()`
        # internally, create a single listener wrapper per actor so we register
        # exactly one stream per actor and forward messages to both a debug
        # print and the `seal` callbacks.
        if ego_gnss is not None:
            def _gnss_wrapper(msg):
                try:
                    print("GNSS measure:\n" + str(msg) + '\n')
                except Exception:
                    pass
                try:
                    seal.gnss_callback(msg)
                except Exception:
                    pass

            ego_gnss.listen(_gnss_wrapper)
            seal._attached_sensors['gnss'] = ego_gnss

        if ego_imu is not None:
            def _imu_wrapper(msg):
                try:
                    print("IMU measure:\n" + str(msg) + '\n')
                except Exception:
                    pass
                try:
                    seal.imu_callback(msg)
                except Exception:
                    pass

            ego_imu.listen(_imu_wrapper)
            seal._attached_sensors['imu'] = ego_imu

        # If you have a lidar actor, attach similarly; otherwise leave None.

        # --------------
        # Place spectator in a third-person position behind the ego vehicle
        # --------------
        # Configuration: distance behind, height above vehicle and smoothing
        spectator = world.get_spectator()
        spectator_distance = 10.0  # meters behind the vehicle
        spectator_height = 4.0     # meters above the vehicle
        spectator_yaw_offset = 0.0 # degrees to offset yaw (rotate around vehicle)
        spectator_smooth_alpha = 0.12  # 0 = no movement (full smoothing), 1 = instant (snap)

        # initial placement (so spectator isn't at origin until loop runs)
        world_snapshot = world.wait_for_tick()
        t = ego_vehicle.get_transform()
        yaw_rad = math.radians(t.rotation.yaw + spectator_yaw_offset)
        init_loc = carla.Location(
            t.location.x - spectator_distance * math.cos(yaw_rad),
            t.location.y - spectator_distance * math.sin(yaw_rad),
            t.location.z + spectator_height
        )
        init_rot = carla.Rotation(pitch=-12.0, yaw=t.rotation.yaw, roll=0.0)
        spectator.set_transform(carla.Transform(init_loc, init_rot))
        

        # --------------
        # Enable autopilot for ego vehicle
        # --------------
        ego_vehicle.set_autopilot(True)

        # --------------
        # Spawn 30 vehicles with autopilot
        # --------------
        logging.info("Spawning 30 vehicles...")
        vehicles_list = []
        try:
            for i in range(30):
                # Get a random spawn point
                if len(spawn_points) > 1:
                    spawn_point = random.choice(spawn_points)
                    # Get a random vehicle blueprint
                    vehicle_bp = random.choice(world.get_blueprint_library().filter('vehicle'))
                    
                    # Set a random color if available
                    if vehicle_bp.has_attribute('color'):
                        color = random.choice(vehicle_bp.get_attribute('color').recommended_values)
                        vehicle_bp.set_attribute('color', color)
                    
                    # Spawn the vehicle
                    vehicle = world.spawn_actor(vehicle_bp, spawn_point)
                    
                    # Enable autopilot
                    vehicle.set_autopilot(True)
                    vehicles_list.append(vehicle)
                    
                    if (i + 1) % 10 == 0:
                        logging.info(f"Spawned {i + 1} vehicles")
            
            logging.info(f"Successfully spawned {len(vehicles_list)} vehicles")
        except Exception as e:
            logging.warning(f"Error spawning vehicles: {e}")

        # --------------
        # Spawn 30 pedestrians/actors
        # --------------
        logging.info("Spawning 30 pedestrians...")
        pedestrians_list = []
        try:
            walker_bp_library = world.get_blueprint_library().filter('walker.pedestrian.*')
            walker_controller_bp = world.get_blueprint_library().find('controller.ai.walker')
            
            for i in range(30):
                # Get a random spawn point
                if len(spawn_points) > 1:
                    spawn_point = random.choice(spawn_points)
                    
                    # Get a random pedestrian blueprint
                    walker_bp = random.choice(walker_bp_library)
                    
                    # Spawn the pedestrian
                    pedestrian = world.spawn_actor(walker_bp, spawn_point)
                    pedestrians_list.append(pedestrian)
                    
                    if (i + 1) % 10 == 0:
                        logging.info(f"Spawned {i + 1} pedestrians")
            
            logging.info(f"Successfully spawned {len(pedestrians_list)} pedestrians")
            
            # Spawn controllers for the pedestrians and start walking
            logging.info("Starting pedestrian AI controllers...")
            controller_list = []
            for pedestrian in pedestrians_list:
                controller = world.spawn_actor(walker_controller_bp, carla.Transform(), pedestrian)
                controller.start()
                # Set random target location
                controller.go_to_location(world.get_random_location_from_navigation())
                controller_list.append(controller)
            
            logging.info(f"Started {len(controller_list)} pedestrian controllers")
        except Exception as e:
            logging.warning(f"Error spawning pedestrians: {e}")

        # Store all spawned actors for cleanup
        all_spawned_actors = vehicles_list + pedestrians_list
        if 'controller_list' in locals():
            all_spawned_actors.extend(controller_list)

        # --------------
        # Game loop. Prevents the script from finishing.
        # --------------
        # Diagnostics log file for controls/speed/IMU
        diagnostics_path = os.path.join(os.getcwd(), 'diagnostics_log.csv')
        try:
            diagnostics_file = open(diagnostics_path, 'w', buffering=1)
            diagnostics_file.write('time,frame,throttle,brake,steer,speed,imu_ax,imu_ay,imu_az\n')
        except Exception as e:
            logging.warning(f'Could not open diagnostics log file: {e}')
            diagnostics_file = None
        def _lerp_angle(a, b, alpha):
            # shortest angular interpolation (degrees)
            diff = (b - a + 180.0) % 360.0 - 180.0
            return a + diff * alpha

        # --------------
        # Game loop. Update spectator every tick so it follows the ego vehicle
        # in a third-person perspective with light smoothing.
        # --------------
        try:
            while True:
                world_snapshot = world.wait_for_tick()

                # get current vehicle transform and compute desired spectator transform
                t = ego_vehicle.get_transform()
                yaw_rad = math.radians(t.rotation.yaw + spectator_yaw_offset)
                desired_loc = carla.Location(
                    t.location.x - spectator_distance * math.cos(yaw_rad),
                    t.location.y - spectator_distance * math.sin(yaw_rad),
                    t.location.z + spectator_height
                )
                desired_rot = carla.Rotation(pitch=-12.0, yaw=t.rotation.yaw, roll=0.0)

                # smoothing: lerp location and yaw from current spectator transform
                try:
                    current = spectator.get_transform()
                except Exception:
                    # spectator might not be accessible for a tick; skip smoothing then
                    spectator.set_transform(carla.Transform(desired_loc, desired_rot))
                    continue

                alpha = spectator_smooth_alpha
                new_loc = carla.Location(
                    current.location.x + (desired_loc.x - current.location.x) * alpha,
                    current.location.y + (desired_loc.y - current.location.y) * alpha,
                    current.location.z + (desired_loc.z - current.location.z) * alpha,
                )
                new_yaw = _lerp_angle(current.rotation.yaw, desired_rot.yaw, alpha)
                new_rot = carla.Rotation(pitch=desired_rot.pitch, yaw=new_yaw, roll=desired_rot.roll)

                # Per-tick diagnostics logging: control, speed, IMU
                try:
                    throttle = brake = steer = 0.0
                    try:
                        control = ego_vehicle.get_control()
                        throttle = control.throttle
                        brake = control.brake
                        steer = control.steer
                    except Exception:
                        pass
                    try:
                        vel = ego_vehicle.get_velocity()
                        speed = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                    except Exception:
                        speed = 0.0
                    imu_ax = imu_ay = imu_az = 0.0
                    try:
                        if 'seal' in locals() and seal is not None:
                            with seal._lock:
                                if len(seal.imu_f) > 0:
                                    a = np.asarray(seal.imu_f[-1], dtype=float)
                                    imu_ax, imu_ay, imu_az = a.tolist()
                    except Exception:
                        pass
                    if diagnostics_file is not None:
                        try:
                            diagnostics_file.write(f"{time.time()},{world_snapshot.frame},{throttle:.3f},{brake:.3f},{steer:.3f},{speed:.3f},{imu_ax:.4f},{imu_ay:.4f},{imu_az:.4f}\n")
                        except Exception:
                            pass
                except Exception:
                    pass
                spectator.set_transform(carla.Transform(new_loc, new_rot))
        except KeyboardInterrupt:
            logging.info('KeyboardInterrupt received: stopping main loop and running SEAL estimation (if available)')

        # After exiting the main loop (e.g., due to KeyboardInterrupt), run estimation
        if 'seal' in locals() and seal is not None:
            try:
                logging.info('Running SEAL.estimate() on buffered data...')
                # Log buffer sizes for diagnostics
                try:
                    imu_count = len(seal.imu_ts)
                    gnss_count = len(seal.gnss_ts)
                    lidar_count = len(seal.lidar_ts)
                except Exception:
                    imu_count = gnss_count = lidar_count = 0
                logging.info(f'SEAL buffers - IMU: {imu_count}, GNSS: {gnss_count}, LIDAR: {lidar_count}')

                # Dump raw buffers to a file for offline inspection (useful if estimate fails)
                try:
                    np.savez('seal_buffers.npz', imu_ts=np.array(seal.imu_ts), imu_f=np.array(seal.imu_f), imu_w=np.array(seal.imu_w), gnss_ts=np.array(seal.gnss_ts), gnss_pos=np.array(seal.gnss_pos), lidar_ts=np.array(seal.lidar_ts), lidar_pos=np.array(seal.lidar_pos))
                    logging.info('Raw SEAL buffers saved to seal_buffers.npz')
                except Exception as e:
                    logging.warning(f'Failed to save raw SEAL buffers: {e}')

                # Run estimator
                p_est, v_est, q_est, p_cov = seal.estimate()
                np.savez('seal_estimates.npz', p_est=p_est, v_est=v_est, q_est=q_est, p_cov=p_cov)
                logging.info('SEAL estimates saved to seal_estimates.npz')
            except Exception as e:
                logging.warning(f'Failed to run or save SEAL estimation: {e}')
                # Ensure raw buffers are saved for offline debugging
                try:
                    np.savez('seal_buffers_on_error.npz', imu_ts=np.array(seal.imu_ts), imu_f=np.array(seal.imu_f), imu_w=np.array(seal.imu_w), gnss_ts=np.array(seal.gnss_ts), gnss_pos=np.array(seal.gnss_pos), lidar_ts=np.array(seal.lidar_ts), lidar_pos=np.array(seal.lidar_pos))
                    logging.info('Raw SEAL buffers saved to seal_buffers_on_error.npz')
                except Exception:
                    pass

    finally:
        # --------------
        # Stop recording and destroy actors
        # --------------
        try:
            client.stop_recorder()
        except Exception:
            pass
        
        # Destroy all spawned vehicles and pedestrians
        logging.info("Cleaning up spawned actors...")
        try:
            if 'all_spawned_actors' in locals():
                for actor in all_spawned_actors:
                    try:
                        if actor.is_alive:
                            actor.destroy()
                    except Exception:
                        pass
            
            # Destroy controllers separately if they exist
            if 'controller_list' in locals():
                for controller in controller_list:
                    try:
                        if controller.is_alive:
                            controller.stop()
                            controller.destroy()
                    except Exception:
                        pass
        except Exception as e:
            logging.warning(f"Error cleaning up spawned actors: {e}")
        
        # Ensure SEAL detaches its listeners before actors are stopped/destroyed
        if 'seal' in locals() and seal is not None:
            try:
                seal.detach_listeners()
            except Exception:
                pass
        if ego_vehicle is not None:
            if ego_cam is not None:
                ego_cam.stop()
                ego_cam.destroy()
            if ego_col is not None:
                ego_col.stop()
                ego_col.destroy()
            if ego_lane is not None:
                ego_lane.stop()
                ego_lane.destroy()
            if ego_obs is not None:
                ego_obs.stop()
                ego_obs.destroy()
            if ego_gnss is not None:
                ego_gnss.stop()
                ego_gnss.destroy()
            if ego_imu is not None:
                ego_imu.stop()
                ego_imu.destroy()
            ego_vehicle.destroy()

if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\nDone with tutorial_ego.')
