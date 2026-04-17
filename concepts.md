# Wall-E Concepts

This page explains the core ideas behind the Wall-E stack and how data moves through control, feedback, and firmware.

## Layered Architecture

The system is organized into four roles:

- firmware: hardware I/O and actuation on ESP32
- feedback: filtering and fusion of raw sensor data
- localization: state estimation and motion representation
- control: command generation from operator input or autonomy logic

## Launch Resilience and Dependency Strategy

Recent launch behavior emphasizes fault tolerance during startup:

- Robot description generation is done through the Python xacro API rather than shelling out to a `xacro` binary.
- Gazebo integration is optional in launch; when `gazebo_ros` is missing, the stack can still start for non-simulation use.
- Runtime package availability is treated as an image concern (Dockerfile includes xacro/RViz/Gazebo ROS packages for fresh containers).

This reduces failures caused by PATH differences or minimal container images.

## Robot Description and TF Completeness

The robot model defines four wheel links as continuous joints. In minimal visualization flows, only the driven front joints may receive live joint states.

To keep the TF tree complete for RViz:

- rear wheel static transforms are published when `joint_state_publisher` is disabled
- those static publishers are disabled automatically when `joint_state_publisher` is enabled

Result:

- RViz can resolve all wheel frames in default launch mode
- no duplicate transform source appears when full joint-state publishing is enabled

## System Diagram

![Wall-E system architecture](docs/source/_static/wall_e_arch-dark.png)

Current command and state loop:

- `/gamepad` from `gamepad_node`
- `/cmd_vel` and `/servo_cmd` from `robot_control_node`
- `/motor_cmd` from `inverse_kinematic_node`
- `/odom` from `odometry_node`

Control topology in `robot_control_node`:

- outer loop: position error (`range`, `heading`) to speed setpoint via P/PD
- inner loop: PI over speed error using odometry/IMU feedback
- speed setpoints are clamped and rate-limited before PI tracking
- parallel actuator path: gamepad axis to `/servo_cmd` angle mapping with configurable min/max/default

## Raw vs Filtered Signals

Raw data from `/imu/data` and `/range/data` can be noisy or jumpy. The host-side filtering stage improves stability:

- `imu_filter.py` applies attitude fusion and bias compensation.
- `ultrasonic_filter.py` applies range validation, median filtering, and EMA smoothing.

Filtered streams are then easier to use for odometry and control loops.

## Fusion Without Kalman Complexity

The current `sensor_fusion.py` is a practical observer-style approach:

- prediction from IMU-derived motion terms
- correction from filtered range measurements

This keeps tuning simple and computational cost low while giving robust behavior for real-time operation.

For this ground robot, `/fusion/height` is best interpreted as a local fused vertical/clearance signal, not global altitude.

## Odometry for Ground Robot

Current odometry is command-plus-sensor dead reckoning:

- translational integration from `/cmd_vel`
- heading from IMU yaw (with fallback integration)
- optional use of range/fusion channels for safety and vertical terms

It is practical for control and monitoring, but it will drift without wheel encoders.

## Safety and Reliability Concepts

Firmware enforces hard safety constraints independently from host nodes:

- watchdog supervision to recover from stalls
- motor timeout to prevent runaway motion
- emergency stop topic to force immediate safe state
- WiFi provisioning and reconnect logic for operational recovery

The key design idea is that host-side filtering can fail or restart without removing firmware-side safety guarantees.

## Where to Tune

Tune the pipeline at the right layer:

- firmware: motor/servo limits and hardware timing
- feedback: filter alpha, window size, jump thresholds, fusion gains
- localization/control: controller gains and kinematic assumptions

This separation reduces coupling and keeps debugging localized.

## Runtime Fault Interpretation

When debugging from serial logs, treat these messages as distinct fault classes:

- `Ultrasonic timeout(wait high)`:
  - Trigger pulse was sent, but ECHO never rose.
  - Typical causes are electrical (wiring, level shifting, power, shared ground), not filter math.

- `Starting ROS node setup...` followed by reset:
  - Startup entered middleware initialization but did not complete cleanly.
  - This path is sensitive to watchdog management and transport readiness.

- `NVS open for read failed: 0x1102`:
  - No stored WiFi credentials yet in NVS namespace.
  - This is expected before first successful provisioning write.

Practical design point:

- Keep early sensor checks before ROS startup so hardware faults are visible even if middleware setup blocks or restarts.
