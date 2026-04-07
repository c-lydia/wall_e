# Wall-E Concepts

This page explains the core ideas behind the Wall-E stack and how data moves through control, feedback, and firmware.

## 1. Layered Architecture

The system is organized into four roles:

- firmware: hardware I/O and actuation on ESP32
- feedback: filtering and fusion of raw sensor data
- localization: state estimation and motion representation
- control: command generation from operator input or autonomy logic

## 2. System Diagram

![Wall-E system architecture](docs/source/_static/wall_e_arch-dark.png)

## 3. Raw vs Filtered Signals

Raw data from `/imu/data` and `/range/data` can be noisy or jumpy. The host-side filtering stage improves stability:

- `imu_filter.py` applies attitude fusion and bias compensation.
- `ultrasonic_filter.py` applies range validation, median filtering, and EMA smoothing.

Filtered streams are then easier to use for odometry and control loops.

## 4. Fusion Without Kalman Complexity

The current `sensor_fusion.py` is a practical observer-style approach:

- prediction from IMU-derived motion terms
- correction from filtered range measurements

This keeps tuning simple and computational cost low while giving robust behavior for real-time operation.

## 5. Safety and Reliability Concepts

Firmware enforces hard safety constraints independently from host nodes:

- watchdog supervision to recover from stalls
- motor timeout to prevent runaway motion
- emergency stop topic to force immediate safe state
- WiFi provisioning and reconnect logic for operational recovery

The key design idea is that host-side filtering can fail or restart without removing firmware-side safety guarantees.

## 6. Where to Tune

Tune the pipeline at the right layer:

- firmware: motor/servo limits and hardware timing
- feedback: filter alpha, window size, jump thresholds, fusion gains
- localization/control: controller gains and kinematic assumptions

This separation reduces coupling and keeps debugging localized.
