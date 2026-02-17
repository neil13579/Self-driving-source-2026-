#!/usr/bin/env python3
"""plot_seal.py

Simple plotting helper for SEAL estimator outputs saved as `.npz` (e.g. `seal_estimates.npz`).

Usage:
  python plot_seal.py --file seal_estimates.npz

This script creates a 3D trajectory plot and a 3-panel position vs time plot.
"""
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt


def load_estimates(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f'File not found: {path}')
    data = np.load(path)
    # Expect arrays named p_est, v_est, q_est, p_cov
    p_est = data.get('p_est')
    v_est = data.get('v_est')
    q_est = data.get('q_est')
    p_cov = data.get('p_cov')
    return p_est, v_est, q_est, p_cov


def plot_trajectory(p_est, outpath=None):
    # Create a figure with trajectory and component plots + covariance/error bounds
    fig = plt.figure(figsize=(14, 8))

    # 3D trajectory
    ax_traj = fig.add_subplot(221, projection='3d')
    ax_traj.plot(p_est[:, 0], p_est[:, 1], p_est[:, 2], label='Estimated')
    ax_traj.set_xlabel('Easting [m]')
    ax_traj.set_ylabel('Northing [m]')
    ax_traj.set_zlabel('Up [m]')
    ax_traj.set_title('Estimated Trajectory')

    # Position components with +/- 3 sigma bounds (sigma must be supplied separately by caller)
    ax_pos = fig.add_subplot(222)
    t = np.arange(p_est.shape[0])
    ax_pos.plot(t, p_est[:, 0], label='Easting')
    ax_pos.plot(t, p_est[:, 1], label='Northing')
    ax_pos.plot(t, p_est[:, 2], label='Up')
    ax_pos.set_xlabel('Sample')
    ax_pos.set_ylabel('Meters')
    ax_pos.set_title('Position components')
    ax_pos.legend()

    # Position magnitude
    ax_mag = fig.add_subplot(223)
    ax_mag.plot(t, np.linalg.norm(p_est, axis=1))
    ax_mag.set_xlabel('Sample')
    ax_mag.set_ylabel('Range [m]')
    ax_mag.set_title('Position magnitude')

    fig.tight_layout()
    if outpath:
        fig.savefig(outpath, dpi=150)
        print(f'Plots saved to: {outpath}')
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='Plot SEAL estimator outputs stored in an .npz file')
    parser.add_argument('--file', '-f', default='seal_estimates.npz', help='Path to .npz file')
    parser.add_argument('--out', '-o', help='Optional output image file to save the plots')
    args = parser.parse_args()

    try:
        p_est, v_est, q_est, p_cov = load_estimates(args.file)
    except Exception as e:
        print(f'Error loading estimates: {e}')
        return

    if p_est is None:
        print('No `p_est` found in the provided file.')
        return

    # determine time axis: prefer timestamps saved in the .npz (e.g. 't','time','timestamps','gnss_t','imu_t')
    t = None
    try:
        _npz = np.load(args.file)
    except Exception:
        _npz = None

    if _npz is not None:
        for key in ('t', 'time', 'timestamps', 'timestamps_utc', 'gnss_t', 'imu_t'):
            if key in _npz:
                try:
                    cand = np.asarray(_npz[key]).reshape(-1)
                except Exception:
                    cand = None
                if cand is not None and cand.size == p_est.shape[0]:
                    t = cand
                    break
                else:
                    print(f"Found time array '{key}' but length {None if cand is None else cand.size} != p_est length {p_est.shape[0]}; ignoring it.")

    if t is None:
        # fallback to simple index-based axis
        t = np.arange(p_est.shape[0])

    # Compute position covariance std dev (sqrt of diagonal of top-left 3x3 block)
    p_cov_std = None
    if p_cov is not None:
        try:
            # p_cov is (N,9,9)
            p_cov_std = np.array([np.sqrt(np.diag(p_cov[i, :3, :3])) for i in range(p_cov.shape[0])])
        except Exception:
            p_cov_std = None

    # Convert quaternions (w,x,y,z) to Euler (roll,pitch,yaw)
    def quat_to_euler(q):
        w, x, y, z = q
        # roll
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + y * y)
        roll = np.arctan2(t0, t1)
        # pitch
        t2 = +2.0 * (w * y - z * x)
        t2 = np.clip(t2, -1.0, 1.0)
        pitch = np.arcsin(t2)
        # yaw
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        yaw = np.arctan2(t3, t4)
        return np.array([roll, pitch, yaw])

    eulers = np.array([quat_to_euler(q_est[i]) for i in range(q_est.shape[0])]) if q_est is not None else None

    # Orientation approx std from p_cov last 3x3 block (axis-angle covariance)
    orient_std = None
    if p_cov is not None:
        try:
            orient_std = np.array([np.sqrt(np.diag(p_cov[i, 6:, 6:])) for i in range(p_cov.shape[0])])
        except Exception:
            orient_std = None

    # Now assemble a more detailed figure including orientation & covariance bounds
    fig2 = plt.figure(figsize=(12, 9))
    ax3d = fig2.add_subplot(221, projection='3d')
    ax3d.plot(p_est[:, 0], p_est[:, 1], p_est[:, 2], label='Estimated')
    ax3d.set_title('Estimated Trajectory')

    ax_pos = fig2.add_subplot(222)
    ax_pos.plot(t, p_est[:, 0], label='Easting')
    ax_pos.plot(t, p_est[:, 1], label='Northing')
    ax_pos.plot(t, p_est[:, 2], label='Up')
    if p_cov_std is not None:
        # Plot +/- 3 sigma shading for each component
        for i, color in enumerate(['tab:blue', 'tab:orange', 'tab:green']):
            ax_pos.fill_between(t, p_est[:, i] - 3 * p_cov_std[:, i], p_est[:, i] + 3 * p_cov_std[:, i], color=color, alpha=0.12)
    ax_pos.set_title('Position components with +/-3 sigma')
    ax_pos.set_xlabel('Sample')
    ax_pos.set_ylabel('Meters')
    ax_pos.legend()

    ax_orient = fig2.add_subplot(223)
    if eulers is not None:
        ax_orient.plot(t, eulers[:, 0], label='Roll')
        ax_orient.plot(t, eulers[:, 1], label='Pitch')
        ax_orient.plot(t, eulers[:, 2], label='Yaw')
        if orient_std is not None:
            # Treat axis-angle std as approximate bounds for small angles (radians)
            for i, ls in enumerate(['--', '--', '--']):
                ax_orient.fill_between(t, eulers[:, i] - 3 * orient_std[:, i], eulers[:, i] + 3 * orient_std[:, i], alpha=0.12)
    ax_orient.set_title('Orientation (Euler) with approximate +/-3 sigma')
    ax_orient.set_xlabel('Sample')
    ax_orient.set_ylabel('Radians')
    ax_orient.legend()

    ax_mag = fig2.add_subplot(224)
    pos_magnitude = np.linalg.norm(p_est, axis=1)
    pos_magnitude_from_start = np.linalg.norm(p_est - p_est[0], axis=1)
    ax_mag.plot(t, pos_magnitude, label='Distance from origin', linewidth=2)
    ax_mag.plot(t, pos_magnitude_from_start, label='Drift from start', linewidth=2, linestyle='--')
    if p_cov is not None:
        try:
            # Plot uncertainty in position magnitude (simplified as max diagonal std)
            p_std_mag = np.array([np.sqrt(np.max(np.diag(p_cov[i, :3, :3]))) for i in range(p_cov.shape[0])])
            ax_mag.fill_between(t, pos_magnitude - 3*p_std_mag, pos_magnitude + 3*p_std_mag, alpha=0.1, label='±3σ bounds')
        except Exception:
            pass
    ax_mag.set_title('Position Magnitude')
    ax_mag.set_xlabel('Sample')
    ax_mag.set_ylabel('Distance [m]')
    ax_mag.legend()
    ax_mag.grid(True, alpha=0.3)

    fig2.tight_layout()
    if args.out:
        fig2.savefig(args.out, dpi=150)
        print(f'Plots saved to: {args.out}')
    else:
        plt.show()


if __name__ == '__main__':
    main()
