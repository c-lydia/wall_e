# Notes

## 1D Sensor Fusion (IMU + Ultrasonic)

Source: `sensor_fusion.py`

This is a lightweight 1D estimator (complementary-filter style) that combines:

- high-rate IMU acceleration updates
- low-rate ultrasonic distance corrections

State:

- $h_t$: estimated fused vertical/clearance state
- $v_t$: estimated vertical velocity

Prediction step (IMU):

1. Compute linear acceleration:
   $$a_{lin} = a_z - g - b_a$$
   where $g = 9.81$ and $b_a$ is accelerometer bias.
2. Integrate velocity with damping:
   $$v_t = (v_{t-1} + a_{lin} \Delta t) \cdot (1 - \gamma)$$
   where $\gamma$ is `velocity_damping`.
3. Integrate position:
   $$h_t = h_{t-1} + v_t \Delta t$$

Correction step (ultrasonic range):

1. Innovation:
   $$y = z_{range} - h_t$$
2. Position correction:
   $$h_t = h_t + K_{range} \cdot y$$

> Note: this implementation corrects height only (not velocity) on range updates.
> For this platform, interpret $h_t$ as a local fused vertical/clearance signal, not absolute world altitude.

## Planar Odometry (Ground Robot)

Source: `localization/odometry.py`

Planar state update:

$$x_t = x_{t-1} + v_x \cos(\psi_t)\Delta t$$
$$y_t = y_{t-1} + v_x \sin(\psi_t)\Delta t$$

Heading update:

- preferred: yaw from IMU quaternion
- fallback: integrate yaw rate

$$\psi_t = \psi_{t-1} + \omega_z\Delta t$$

This is suitable for closed-loop behavior and debugging, but long-run drift is expected without encoder feedback.

## Cascaded Robot Control (Position to Speed to Command)

Source: `control/robot_control.py`

Outer loop (position-to-speed, P/PD only):

$$v_{sp} = K_{p,r} e_r + K_{d,r} \dot{e}_r$$
$$\omega_{sp} = K_{p,\psi} e_\psi + K_{d,\psi} \dot{e}_\psi$$

Then apply:

- speed saturation: $v_{sp} \in [-v_{max}, v_{max}]$, $\omega_{sp} \in [-\omega_{max}, \omega_{max}]$
- setpoint rate limit: $\Delta v_{sp}/\Delta t$ and $\Delta\omega_{sp}/\Delta t$

Inner loop (speed PI):

$$u_v = K_{p,v}(v_{sp}-v) + K_{i,v}\int (v_{sp}-v)dt$$
$$u_\omega = K_{p,\omega}(\omega_{sp}-\omega) + K_{i,\omega}\int (\omega_{sp}-\omega)dt$$

This keeps PI action on speed tracking while avoiding direct integral action on position.

## Servo Command Mapping (Host Control)

Source: `control/robot_control.py`

`robot_control_node` publishes `/servo_cmd` as `std_msgs/msg/Float32` (degrees).

Axis-to-angle mapping:

1. Read selected axis `u` from gamepad (`u \in [-1, 1]`)
2. Optional inversion: $u' = -u$ if `servo_axis_invert=true`, else $u' = u$
3. Map to angle range $[\theta_{min}, \theta_{max}]$:

$$\theta = \theta_{min} + \frac{u' + 1}{2}(\theta_{max} - \theta_{min})$$

Operational behavior:

- If `servo_only_when_enabled=true` and drive enable is not pressed, controller publishes `servo_default_angle_deg`.
- If `servo_enabled=false`, no servo command is published by host control.

## Attitude Estimation (Mahony Filter)

Source: `imu_filter.py`

Orientation is represented by quaternion:
$$\mathbf{q} = [q_w, q_x, q_y, q_z]^T$$

Step 1: expected gravity in sensor frame
$$\hat{v}_x = 2(q_x q_z - q_w q_y)$$
$$\hat{v}_y = 2(q_w q_x + q_y q_z)$$
$$\hat{v}_z = q_w^2 - q_x^2 - q_y^2 + q_z^2$$

Step 2: error from measured acceleration
Using $\mathbf{e} = \mathbf{a} \times \hat{\mathbf{v}}$ with $\mathbf{a} = [a_x, a_y, a_z]^T$:
$$e_x = a_y \hat{v}_z - a_z \hat{v}_y$$
$$e_y = a_z \hat{v}_x - a_x \hat{v}_z$$
$$e_z = a_x \hat{v}_y - a_y \hat{v}_x$$

Step 3: PI correction of gyro rate
$$\mathbf{e}_{int} = \mathbf{e}_{int} + \mathbf{e} \Delta t$$
$$\mathbf{\omega}_{corr} = \mathbf{\omega}_{raw} + K_p \mathbf{e} + K_i \mathbf{e}_{int}$$

Step 4: quaternion integration (Euler)
$$q_w(t+\Delta t) = q_w(t) + \frac{\Delta t}{2} (-q_x \omega_x - q_y \omega_y - q_z \omega_z)$$
$$q_x(t+\Delta t) = q_x(t) + \frac{\Delta t}{2} (q_w \omega_x + q_y \omega_z - q_z \omega_y)$$
$$q_y(t+\Delta t) = q_y(t) + \frac{\Delta t}{2} (q_w \omega_y - q_x \omega_z + q_z \omega_x)$$
$$q_z(t+\Delta t) = q_z(t) + \frac{\Delta t}{2} (q_w \omega_z + q_x \omega_y - q_y \omega_x)$$

Normalize to unit quaternion:
$$\mathbf{q} = \frac{\mathbf{q}}{\sqrt{q_w^2 + q_x^2 + q_y^2 + q_z^2}}$$

## Non-Linear Range Filtering

Source: `range_filter.py`

Used to reject ultrasonic outliers before fusion.

Median filter:

- Given window $W = [w_1, w_2, ..., w_N]$ (odd $N$)
- Sort: $S = \text{sort}(W)$
- Median: $x_m = S[\frac{N+1}{2}]$

Jump gate:
$$\text{accept if } |x_m - y_{t-1}| \le J_{max}$$

EMA smoothing:

- If accepted:
  $$y_t = \alpha x_m + (1 - \alpha) y_{t-1}$$
- If rejected:
  $$y_t = y_{t-1}$$

## Hardware Conversions and Low-Level Math

Source: `app.c`

### Time-of-flight distance

Ultrasonic echo distance:
$$d = \frac{v_s t}{2}, \; v_s \approx 343 \text{ m/s}$$
$$d = \frac{343 \cdot (t \times 10^{-6})}{2} = t \times 1.715 \times 10^{-4} \text{ m}$$

Observed debug values (2026-04-10):

- `t = 344 us` gives:
   $$d \approx 344 \times 1.715 \times 10^{-4} = 0.0590\text{ m}$$
- `t = 401 us` gives:
   $$d \approx 401 \times 1.715 \times 10^{-4} = 0.0688\text{ m}$$

These match monitor output (`~0.059-0.069 m`).

If `Ultrasonic timeout(wait high)` repeats, no ECHO rising edge is being detected.
That indicates an input-electrical issue before any filtering stage.

### IMU register scaling

Acceleration (for $\pm 2g$):
$$a\,[\text{m/s}^2] = \left(\frac{\text{raw}}{16384.0}\right) \cdot 9.81$$

Gyroscope (for $\pm 250^\circ/\text{s}$):
$$\omega\,[\text{rad/s}] = \left(\frac{\text{raw}}{131.0}\right) \cdot \frac{\pi}{180}$$

### Gyro Bias Compensation at Boot

Firmware now computes a startup gyro bias from multiple stationary samples:

$$b_x = \frac{1}{N}\sum_{k=1}^{N} g_{x,k},\; b_y = \frac{1}{N}\sum_{k=1}^{N} g_{y,k},\; b_z = \frac{1}{N}\sum_{k=1}^{N} g_{z,k}$$

Corrected gyro raw values are then:

$$g'_{x} = g_x - b_x,\; g'_{y} = g_y - b_y,\; g'_{z} = g_z - b_z$$

This reduces static drift in angular velocity when the platform is still.

### Servo angle to PWM

Pulse width from angle $\theta \in [0, 180]$:
$$t_{pulse} = 500 + (2500 - 500) \cdot \frac{\theta}{180}$$

16-bit register value at 20 ms period:
$$\text{Duty} = \frac{t_{pulse}}{T_{period}}$$
$$\text{Register} = \left(\frac{t_{pulse}}{20000}\right) \cdot (2^{16} - 1)$$

## Robot Model Generation and TF Notes

### Xacro generation at launch

Host launch now builds URDF XML directly with Python xacro processing:

$$\text{robot\_description} = \text{xacro.process\_file}(\text{urdf\_file}).\text{toxml}()$$

This avoids dependence on a shell-resolved `xacro` executable path.

### Rear wheel RViz transform fallback

When `joint_state_publisher` is disabled, rear wheel continuous joints may have no joint-state source.
To keep RViz RobotModel complete, launch publishes rear wheel static transforms from `base_link`.

For `rear_left_wheel`:

$$\mathbf{t}_{rl} = [-0.07,\; 0.085,\; -0.01]^T$$

For `rear_right_wheel`:

$$\mathbf{t}_{rr} = [-0.07,\; -0.085,\; -0.01]^T$$

Wheel visual orientation uses a fixed $\frac{\pi}{2}$ roll, with quaternion:

$$q = [x, y, z, w] = [\sin(\pi/4),\; 0,\; 0,\; \cos(\pi/4)] \approx [0.7071,\; 0,\; 0,\; 0.7071]$$

These static publishers are conditionally disabled when `joint_state_publisher` is enabled.
