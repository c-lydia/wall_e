# Notes

## 1D Sensor Fusion (IMU + Ultrasonic)

Source: `sensor_fusion.py`

This is a lightweight 1D estimator (complementary-filter style) that combines:

- high-rate IMU acceleration updates
- low-rate ultrasonic distance corrections

State:

- $h_t$: estimated height
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

### IMU register scaling

Acceleration (for $\pm 2g$):
$$a\,[\text{m/s}^2] = \left(\frac{\text{raw}}{16384.0}\right) \cdot 9.81$$

Gyroscope (for $\pm 250^\circ/\text{s}$):
$$\omega\,[\text{rad/s}] = \left(\frac{\text{raw}}{131.0}\right) \cdot \frac{\pi}{180}$$

### Servo angle to PWM

Pulse width from angle $\theta \in [0, 180]$:
$$t_{pulse} = 500 + (2500 - 500) \cdot \frac{\theta}{180}$$

16-bit register value at 20 ms period:
$$\text{Duty} = \frac{t_{pulse}}{T_{period}}$$
$$\text{Register} = \left(\frac{t_{pulse}}{20000}\right) \cdot (2^{16} - 1)$$