**EgoSEAL: ES-EKF State Estimation and Localisation**

This README explains the `ego_SEAL.py` module in this workspace. The module is a compact, importable implementation of an Error-State Extended Kalman Filter (ES-EKF) adapted from the `es_ekf.py` starter script.

**Purpose**: Provide a small, self-contained estimator that can run offline on dataset pickles or attach to CARLA sensor actors at runtime to buffer data and perform batch or online estimation.

**Files of interest**:
- `ego_SEAL.py`: The module that implements a lightweight `Quaternion`, the ES-EKF logic, CARLA-safe sensor callbacks, and an `EgoSEAL` class.
- `es_ekf.py`: The original course script. `ego_SEAL.py` is based on it but reorganised for reuse.

**Key differences vs `es_ekf.py`**
- **Modularity**: `es_ekf.py` is a standalone script (loads data, plots, saves submissions). `ego_SEAL.py` is a module designed to be imported or used as a library.
- **CARLA integration**: `ego_SEAL.py` contains `EgoSEAL` with `attach_listeners` / `detach_listeners` and callbacks that accept CARLA messages or simple dicts. `es_ekf.py` operates only on offline pickle data.
- **Robust message parsing**: Callbacks in `EgoSEAL` accept CARLA objects or dictionaries and use `try/except` to avoid raising from malformed messages.
- **Timestamp handling**: `ego_SEAL.py` automatically converts timestamps that look like milliseconds to seconds (if values > 1e6). `es_ekf.py` assumes the provided timestamps are directly usable (ms in dataset).
- **Quaternion helper**: `ego_SEAL.py` includes a minimal `Quaternion` implementation (axis-angle constructor, `to_mat`, `to_euler`, `quat_mult_right`) so the file has no external dependency on the `rotations` module.
- **Initialisation**: `es_ekf.py` uses the provided ground truth for initial pose/velocity; `ego_SEAL.py` initializes at origin unless GNSS or lidar first samples are present.
- **Covariance init**: Slightly different defaults (`ego_SEAL.py` uses `p_cov[0] = eye(9) * 0.01`), and `ego_SEAL.py` exposes sensor variance parameters via constructor.
- **LIDAR calibration**: Both apply the same transform, but `ego_SEAL.py` does this inside `estimate_from_data` and builds buffers rather than modifying dataset objects in-place.
- **No plotting**: `ego_SEAL.py` does not include plotting or submission code — it focuses on the estimator API.

**Why you saw the CARLA assertion (duplicate stream ID)**
- The CARLA server requires that each active streaming client (sensor.listen) registers a unique stream token. If `listen()` is called twice for the same actor without stopping the previous listener, the server can detect duplicate clients for the same stream id and assert.
- Typical causes:
  - Calling `attach_listeners` repeatedly without stopping previous listeners.
  - Re-running Python code (or reloading modules) while a previous client is still connected.
  - Attaching the same actor multiple times from different code paths.

Fixes applied and recommended usage:
- `EgoSEAL` now tracks attached actors in `self._attached_sensors` and avoids calling `listen()` again for the same actor. If a different actor is attached to the same channel, the previous actor is stopped first.
- Call `seal.detach_listeners()` on shutdown to cleanly stop listening and release streams.

**API: important parts of `ego_SEAL.py`**
- `class EgoSEAL(var_imu_f=0.01, var_imu_w=0.01, var_gnss=10.0, var_lidar=1.0)`
  - Constructor sets noise variances and allocates buffers. Thread-safe with a `Lock` for callback concurrency.
- `EgoSEAL.imu_callback(msg)`
  - Accepts a CARLA IMU message or a dict `{ 't': ..., 'accel': array, 'gyro': array }` and appends it to the IMU buffer.
- `EgoSEAL.gnss_callback(msg)` and `EgoSEAL.lidar_callback(msg)`
  - Same idea for GNSS and LIDAR. They append `t` and `pos` to respective buffers.
- `EgoSEAL.attach_listeners(ego_vehicle=None, imu=None, gnss=None, lidar=None)`
  - Attach CARLA sensor actors to the estimator. If CARLA is unavailable this is a no-op.
  - The method avoids duplicate `listen()` calls and will stop previously attached actors when replacing them.
- `EgoSEAL.detach_listeners()`
  - Stop and clear all attached CARLA sensor listeners (call before exiting to avoid hanging streams).
- `EgoSEAL.estimate()`
  - Run the batch ES-EKF on buffered data and return `(p_est, v_est, q_est, p_cov)` arrays (same format as `es_ekf.py`).
- `estimate_from_data(pickle_path)`
  - Convenience to load a dataset pickle (pt3_data-style), transform the lidar data to IMU frame, populate a new `EgoSEAL` instance, and run `estimate()`.

**Usage examples**

- Offline (run on dataset pickle):
  - From Python: 
    ```python
    from ego_SEAL import estimate_from_data
    p_est, v_est, q_est, p_cov = estimate_from_data('data/pt3_data.pkl')
    ```

- Live with CARLA sensors (pseudo):
  - Attach after spawning sensors (run in your spawn script):
    ```python
    from ego_SEAL import EgoSEAL

    seal = EgoSEAL()
    seal.attach_listeners(imu=imu_actor, gnss=gnss_actor, lidar=lidar_actor)

    # run later (batch estimate on buffered data)
    p_est, v_est, q_est, p_cov = seal.estimate()

    # on shutdown
    seal.detach_listeners()
    ```

  - If your application reconfigures sensors at runtime, call `detach_listeners()` first or rely on `attach_listeners()` which will stop any previous actor it replaces.

**Troubleshooting & tips**
- If you see the CARLA assertion about duplicate stream IDs again:
  - Ensure `detach_listeners()` is called before your program exits or before reattaching sensors.
  - Make sure no other process or earlier script instance still has active listeners connected to the CARLA server.
  - If debugging in an interactive session (REPL / notebook), explicitly call `seal.detach_listeners()` before re-running attachment code.
- Timestamp units: the estimator tries to detect ms vs s. If your sensors produce timestamps in different units, verify they are consistent. The code converts arrays that look like milliseconds (values > 1e6) to seconds.
- If you need ground-truth initialization like `es_ekf.py`, set `p_est[0]`, `v_est[0]`, `q_est[0]` manually before calling `estimate()`.

**Limitations and future work**
- `ego_SEAL.py` is intended as a light compatibility wrapper for the course EKF. It does not implement smoothing, outlier rejection, or a full online EKF with time-synchronous measurement handling beyond matching exact timestamps.
- You may want to adapt the measurement matching logic if your sensors have different timestamp rates or latencies (e.g., nearest-neighbour matching, interpolation, or time-sync).

**File location**: `ego_SEAL.py` is in the project root. The README is at the same location: `README.md`.

If you want, I can:
- Add a small example `run_seal.py` that demonstrates attaching to fake/dummy sensors and performing a run.
- Update `ego_spawn.py` to call `detach_listeners()` on cleanup and ensure `attach_listeners()` is called only once.
 - Add a small example `run_seal.py` that demonstrates attaching to fake/dummy sensors and performing a run.
 - Update `ego_spawn.py` to call `detach_listeners()` on cleanup and ensure `attach_listeners()` is called only once.

**Integrated `ego_spawn.py` Workflow**

After embedding `ego_SEAL` into `ego_spawn.py`, the project now supports a single-file workflow where sensor attachment, buffering and the ES-EKF estimation run inside the same process. This avoids CARLA stream duplication errors and makes it straightforward to run the simulator and estimator together.

- **How it runs**: Start CARLA and run `ego_spawn.py`. The script spawns the ego vehicle and sensors, attaches listeners that append measurements to an `EgoSEAL` instance, and enters a main loop that updates the spectator. When you stop the script with Ctrl+C, it will run `seal.estimate()` on the buffered data and save results to `seal_estimates.npz` before detaching listeners and destroying actors.
- **Default save location**: `seal_estimates.npz` in the same working directory.

**New helper: `plot_seal.py`**

I added `plot_seal.py` to visualize saved estimation outputs. Usage:

```
python .\plot_seal.py --file seal_estimates.npz
```

Or save the figure directly:

```
python .\plot_seal.py --file seal_estimates.npz --out trajectory.png
```

`plot_seal.py` creates a 3D trajectory plot and position component plots (Easting, Northing, Up).

**Input / Output Data Format**

- **Primary estimator output**: `seal_estimates.npz` — a NumPy archive saved by `ego_spawn.py` after running the estimator. Expected arrays inside:
  - `p_est`: float array, shape `(N, 3)` — estimated position in meters (Easting, Northing, Up) for N samples.
  - `v_est`: float array, shape `(N, 3)` — estimated velocity in m/s.
  - `q_est`: float array, shape `(N, 4)` — orientation quaternions in (w, x, y, z) order for each sample.
  - `p_cov`: float array, shape `(N, 9, 9)` — covariance matrix for the estimator error-state at each sample. The layout matches `[pos(3), vel(3), ori_axis_angle(3)]` producing a 9×9 block; top-left 3×3 is position covariance.
  - Optional timestamp arrays (preferred if present): any of `t`, `time`, `timestamps`, `timestamps_utc`, `gnss_t`, `imu_t`. These should be 1D arrays of length `N` (seconds since epoch or relative seconds). If present and length matches `p_est`, `plot_seal.py` will use them for the x-axis; otherwise the script falls back to a sample index axis `0..N-1`.

- **Diagnostic buffers**: When `ego_spawn.py` runs, it also saves raw buffers for diagnostics if estimation fails or on demand. Typical filenames:
  - `seal_buffers.npz` — contains the raw measurement buffers collected during the run, such as `imu_t`, `imu_accel`, `imu_gyro`, `gnss_t`, `gnss_pos`, and possibly `lidar_*` arrays depending on your configuration.
  - `seal_buffers_on_error.npz` — same as above but saved when estimation fails; helpful for offline debugging.

Notes about units and ordering:
- Positions are in meters in the simulator/world frame used by CARLA (Easting/Northing/Up).
- Quaternions are stored as `(w, x, y, z)` and `plot_seal.py` converts these to Euler angles (roll, pitch, yaw) for plotting.
- `p_cov` follows the error-state ordering used by the estimator (position, velocity, orientation-as-small-axis-angle). Use care if you re-order states or change measurement models.
**Files (current state)**
- `ego_spawn.py`: Single-file runtime that now embeds the estimator (`EgoSEAL`, `Quaternion`, helpers). Spawns sensors, attaches listeners, runs main loop, and executes estimation on shutdown.
- `plot_seal.py`: Small plotting helper to inspect `seal_estimates.npz`.
- `ego_SEAL.py`: Commented-out copy; preserved for later restoration if you want the estimator as a separate module.

**Significance of the recent changes**
- **Single process integration**: Embedding the estimator in `ego_spawn.py` eliminates cross-process listener re-registration and the CARLA duplicate-stream assertion. It also simplifies data flow: measurements buffer directly into the estimator in the same memory space.
- **Graceful cleanup**: The script now calls `seal.detach_listeners()` in the cleanup `finally` block and catches errors from `client.stop_recorder()` — ensuring sensor streams are stopped before actors are destroyed.
- **On-demand estimation**: The estimator is invoked automatically on Ctrl+C (main loop exit) and its outputs are saved as an `.npz` archive for analysis. This provides a simple, reproducible pipeline.
- **Plotting utility**: `plot_seal.py` provides a quick way to inspect and validate results without modifying the simulator script.

**What `seal_plots.png` shows (panel-by-panel explanation)**

When you run `plot_seal.py --out seal_plots.png` the generated figure contains multiple panels that help you inspect estimator performance. The default layout is a 2×2 grid; interpretations below refer to those panels.

- **Upper-left — 3D Trajectory**:
  - What it is: A 3D rendering of the estimated path (`p_est[:,0]`, `p_est[:,1]`, `p_est[:,2]`).
  - How to read it: Use it to check overall path shape and gross consistency with expected route. Large drifts or sudden jumps indicate sensor faults, timestamp mismatches, or mis-calibration.

- **Upper-right — Position Components vs Time (Easting / Northing / Up)**:
  - What it is: Three time-series showing each positional axis across samples/time.
  - Uncertainty shading: If `p_cov` is provided, the script plots +/-3σ shading for each component based on sqrt of the diagonal of the top-left 3×3 covariance block at each timestep. This shows an approximate confidence envelope for each axis.
  - How to read it: Check whether the trajectory lies mostly inside the shaded regions (reasonable) and whether the covariance grows or shrinks over time (expected behavior when sensors provide/lose information). If the covariance is unnaturally small or zero, the filter may be overconfident or mis-initialised.

- **Lower-left — Orientation (Euler angles) vs Time**:
  - What it is: Roll, Pitch, and Yaw plotted as Euler angles (radians) converted from `q_est` quaternions.
  - Uncertainty shading: If orientation covariance is available in `p_cov`, the script approximates orientation stddevs from the last 3×3 block (axis-angle covariance) and draws +/-3σ shading. This is an approximation that assumes small-angle perturbations.
  - Caveats: Euler angles wrap (−π..π); sudden jumps can be due to wrapping, not physical rotation. Use quaternions or unwrap the angle for analyses that require continuity.

- **Lower-right — Position Magnitude vs Time**:
  - What it is: The Euclidean norm of position (`||p_est||`) across samples. Useful for quick checks of scale and for verifying that position stays near expected ranges.

Interpretation tips:
- If the estimator diverges (position drifts unbounded) and covariance remains small, suspect incorrect sensor variances or a bug in measurement updates.
- If covariance grows rapidly then measurement updates are not arriving or are being ignored (e.g., timestamp mismatches, missing GNSS updates). Check `seal_buffers.npz` to confirm message rates.
- Orientation bounds computed from the axis-angle covariance are approximate. For precise orientation uncertainty propagation you should transform the full quaternion covariance using a proper Jacobian.

If you want, I can also update `plot_seal.py` to:
- Show timestamps as human-readable datetimes when epoch seconds are present.
- Add roll/pitch/yaw unwrapping to avoid visual jumps.
- Add per-sensor rate/time-coverage diagnostics in a small extra panel.

**How to run the integrated workflow (quick)**

1. Start CARLA server.
2. From project folder run:

```
python .\ego_spawn.py
```

3. When ready to stop and run estimation, press Ctrl+C in the terminal running `ego_spawn.py`. The script will:
- Run the ES-EKF on buffered data.
- Save `seal_estimates.npz`.
- Detach listeners and destroy actors.

4. Visualize results:

```
python .\plot_seal.py --file seal_estimates.npz
```

**If you prefer separate-process workflow**

If you need to run the estimator in a different process (for offline analysis or to avoid long-running simulator runs), I can add code to `ego_spawn.py` to dump raw sensor buffers (timestamps and measurements) to a pickle file on-demand or on shutdown. Then you can run `estimate_from_data()` in a separate script that loads that pickle and produces the `.npz` results.

---
If you'd like, I can now:
- Add periodic estimation inside `ego_spawn.py` (e.g., run estimator every N seconds and write snapshots).
- Add raw-buffer saving for a separate-process workflow.
- Add plotting customization (show covariance bounds, orientation plots, etc.).

---
Generated: Documentation for `ego_SEAL.py` and troubleshooting guidance for CARLA streaming assertions.
