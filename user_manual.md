# Wall-E User Manual

This guide explains how to set up, build, flash, and use the ESP32-based Wall-E controller.

## What This Project Does

The main firmware in `firmware/custom/esp32_controller` provides:

- Micro-ROS connectivity over WiFi
- IMU publishing on `imu/data`
- Ultrasonic range publishing on `range/data`
- Motor control on `/motor_cmd`
- Servo control on `/servo_cmd`
- Emergency stop handling on `/e_stop`
- Firmware status publishing on `firmware/status`

The host feedback stack in `wall_e_ws/src/feedback/feedback` can additionally provide:

- IMU filtered topic on `/imu/filter`
- Ultrasonic filtered topic on `/range/filter`
- Fused state outputs on `/fusion/height` and `/fusion/vertical_velocity`

If no WiFi credentials are stored, the device starts a provisioning access point so you can enter credentials from a browser.

## System Diagram

![Wall-E system architecture](docs/source/_static/wall_e_arch-dark.png)

Use this as the mental model for where each node belongs:

- Firmware node handles physical I/O and low-level actuator control.
- Feedback nodes perform filtering and fusion.
- Localization nodes estimate platform motion state.
- Control nodes compute and publish actuation commands.

## Requirements

- Docker and Docker Compose
- VS Code with the project opened
- An ESP32 board connected over USB if you want to flash real hardware
- A serial device such as `/dev/ttyUSB0` or the port exposed by your system

## First-Time Setup

1. Start the container stack from the repository root.

``` bash
docker compose up -d
```

1. Open a shell in the workspace container.

``` bash
docker exec -it micro_ros_workspace bash
```

1. Source the ROS environment if you are working with the host workspace.

``` bash
source /opt/ros/humble/setup.bash
source /micro_ros_ws/install/setup.bash
```

## Launch the Integrated Host Stack

From the workspace container, run:

``` bash
cd /micro_ros_ws
source /opt/ros/humble/setup.bash
source /micro_ros_ws/install/setup.bash
ros2 launch wall_e_description wall_e.launch.py
```

Useful launch toggles:

- RViz only (no Gazebo):

``` bash
ros2 launch wall_e_description wall_e.launch.py use_gazebo:=false use_rviz:=true
```

- Enable joint_state_publisher:

``` bash
ros2 launch wall_e_description wall_e.launch.py use_joint_state_publisher:=true
```

Notes:

- Rear wheel transforms are now published in default launch mode even when `joint_state_publisher` is disabled.
- Gazebo launch is optional and will be skipped if `gazebo_ros` is not installed.

## WiFi Provisioning

On first boot, the controller creates an open access point named `ESP32-Setup`.

1. Connect your phone or laptop to `ESP32-Setup`.
2. Open `http://192.168.4.1/` in a browser.
3. Enter your WiFi SSID and password.
4. Save the form and wait for the device to restart.

The credentials are stored in NVS flash and used on future boots.

## Build the Firmware

Inside the workspace container, configure and build the firmware app.

``` bash
ros2 run micro_ros_setup configure_firmware.sh esp32_controller -t udp -i 192.168.1.2 -p 8888
ros2 run micro_ros_setup build_firmware.sh
```

The generated firmware is expected under:

``` text
firmware/freertos_apps/microros_esp32_extensions/build/esp32_controller.bin
firmware/freertos_apps/microros_esp32_extensions/build/esp32_controller.elf
```

## Flash the Board

After building, flash the ESP32 from the container.

``` bash
ros2 run micro_ros_setup flash_firmware.sh
```

If your board is not on `/dev/ttyUSB0`, update the device mapping in `docker-compose.yaml`.

## Monitor Logs

To view ESP-IDF logs from the board:

``` bash
cd /micro_ros_ws/firmware/freertos_apps/microros_esp32_extensions
source /micro_ros_ws/firmware/toolchain/esp-idf/export.sh
idf.py -p /dev/ttyUSB0 monitor
```

## Run in Wokwi

Wokwi uses the compiled `.bin` and `.elf` files directly.

1. Build the firmware first.
2. Start the simulator from VS Code with `Wokwi: Start Simulator`.
3. Check the VS Code `Output` panel if you do not see logs.

## Command Topics

The controller listens to these ROS 2 topics:

- `/motor_cmd`: `std_msgs/msg/Float32MultiArray`, one value per motor
- `/servo_cmd`: `std_msgs/msg/Float32`, servo angle in degrees
- `/e_stop`: `std_msgs/msg/Bool`, true enables emergency stop

Published topics include:

- `imu/data`
- `range/data`
- `firmware/status`

### Topic Details

#### `/motor_cmd`

This topic drives the four motor outputs.

- Message type: `std_msgs/msg/Float32MultiArray`
- Data meaning: each array value maps to one motor channel in order
- Expected range: `-1.0` to `1.0`
- `1.0` means full forward
- `-1.0` means full reverse
- `0.0` means stop

Example array values:

- `[0.5, 0.5, 0.5, 0.5]` drives all four motors forward at half speed
- `[1.0, -1.0, 0.0, 0.0]` drives the first motor forward, second motor reverse, and stops the remaining two

The firmware also rate-limits motor changes, so sudden jumps are softened instead of being applied instantly.

#### `/servo_cmd`

This topic sets the servo target angle.

- Message type: `std_msgs/msg/Float32`
- Data meaning: desired servo angle in degrees
- Expected range: controlled by Kconfig settings, usually `0` to `180`
- Example: `90.0` moves the servo to the center position

The servo motion is rate-limited, so it moves toward the target at a controlled speed instead of jumping immediately.

#### `/e_stop`

This topic enables or clears emergency stop.

- Message type: `std_msgs/msg/Bool`
- `true` forces the motors to zero and sends the servo to its default angle
- `false` clears the emergency stop state

Use this when you need to force the robot into a safe state quickly.

### Published Data

#### `imu/data`

Contains accelerometer and gyro readings from the MPU6050.

- Linear acceleration is reported in meters per second squared
- Angular velocity is reported in radians per second

#### `range/data`

Contains ultrasonic distance measurements.

- Units: meters
- Only published when the sensor returns a valid reading

#### `firmware/status`

Contains a compact status string with the latest sensor values.

This is mainly useful for debugging and quick health checks.

## Motor and Servo Configuration

The controller uses Kconfig so you can tune hardware settings without editing source code.

Useful options in `firmware/custom/esp32_controller/Kconfig.projbuild` include:

- Motor PWM and direction GPIOs: choose which ESP32 pins control each motor driver
- Motor slew rate limit: controls how fast the motor command may change per second
- Servo PWM GPIO: selects the pin that generates the servo PWM signal
- Servo angle limits: defines the minimum and maximum angle the servo will accept
- Servo default angle: angle used at startup and as the emergency-stop position
- Servo max rate: sets how fast the servo may move toward a new target

### Parameter Reference

| Parameter | Default | What it does |
| --- | --- | --- |
| `ESP_MOTOR_MAX_SLEW_PER_S_X100` | `200` | Sets the motor slew rate in hundredths of normalized units per second. `200` means `2.00` units per second. Lower values make motion smoother but slower to respond. |
| `ESP_MOTOR1_PWM_GPIO` | `25` | PWM output for motor 1. |
| `ESP_MOTOR1_DIR_GPIO` | `26` | Direction output for motor 1. |
| `ESP_MOTOR2_PWM_GPIO` | `27` | PWM output for motor 2. |
| `ESP_MOTOR2_DIR_GPIO` | `14` | Direction output for motor 2. |
| `ESP_MOTOR3_PWM_GPIO` | `12` | PWM output for motor 3. |
| `ESP_MOTOR3_DIR_GPIO` | `13` | Direction output for motor 3. |
| `ESP_MOTOR4_PWM_GPIO` | `33` | PWM output for motor 4. |
| `ESP_MOTOR4_DIR_GPIO` | `32` | Direction output for motor 4. |
| `ESP_SERVO_PWM_GPIO` | `19` | PWM output used for the servo signal. |
| `ESP_SERVO_MIN_ANGLE_DEG` | `0` | Lowest servo angle accepted by the firmware. |
| `ESP_SERVO_MAX_ANGLE_DEG` | `180` | Highest servo angle accepted by the firmware. |
| `ESP_SERVO_DEFAULT_ANGLE_DEG` | `90` | Servo position used at startup and during emergency stop. |
| `ESP_SERVO_MAX_RATE_DEG_S` | `120` | Maximum speed the servo may move in degrees per second. |

Open `menuconfig` from the ESP-IDF project if you want to change these values.

### When to Change These Values

- Change motor GPIOs if your wiring uses different ESP32 pins.
- Lower motor slew rate if the platform jerks or draws too much current.
- Change servo GPIO if the servo signal wire is connected elsewhere.
- Narrow servo angle limits if your servo horn or mechanism cannot safely rotate through the full range.
- Lower servo max rate if the movement is too aggressive.

### Example Settings

- Smooth but responsive motor control: `ESP_MOTOR_MAX_SLEW_PER_S_X100 = 150`
- Slower servo movement for delicate mechanisms: `ESP_SERVO_MAX_RATE_DEG_S = 60`
- Centered startup servo position: `ESP_SERVO_DEFAULT_ANGLE_DEG = 90`

## Typical Control Flow

1. Boot the board.
2. Connect WiFi or provision it from the browser if needed.
3. Start host control stack (`gamepad_node`, `robot_control_node`, `inverse_kinematic_node`, `odometry_node`).
4. Verify command paths: `/gamepad` -> `/cmd_vel` -> `/motor_cmd` and `/gamepad` -> `/servo_cmd`.
5. Watch `imu/data`, `range/data`, `/odom`, and `firmware/status` for feedback.
6. Use `/e_stop` if you need to stop the robot immediately.

## Host Control Stack

- `gamepad_node` publishes `/gamepad`
- `robot_control_node` publishes `/cmd_vel` in manual mode (stick inputs) and cascaded closed-loop mode using `/range/filter`, `/imu/filter`, `/odom`.
- `robot_control_node` closed-loop details: outer loop is P/PD over position error (range/heading) to speed setpoint.
- `robot_control_node` closed-loop details: inner loop is PI over speed error with speed saturation and setpoint rate limiting.
- `robot_control_node` publishes `/servo_cmd` (`std_msgs/msg/Float32`, angle in degrees) from configurable gamepad axis mapping.
- `inverse_kinematic_node` maps `/cmd_vel` to four-wheel `/motor_cmd`
- `odometry_node` publishes `/odom` from available sensors and command flow

### Servo Mapping in `robot_control_node`

- Servo publish topic: `/servo_cmd`
- Servo message type: `std_msgs/msg/Float32`
- Default axis: `right_stick_y`
- Default mapping: normalized axis value `[-1, 1]` to angle range `[servo_min_angle_deg, servo_max_angle_deg]`
- Default behavior when drive enable is not held: publish `servo_default_angle_deg` (when `servo_only_when_enabled=true`)

Key parameters:

- `servo_enabled`
- `servo_axis`
- `servo_axis_invert`
- `servo_min_angle_deg`
- `servo_max_angle_deg`
- `servo_default_angle_deg`
- `servo_only_when_enabled`

### Gamepad Input Mapping

The current host control mapping is:

- Enable motion gate: `LB` (must be held, default `enable_button=lb`)
- Hold/PI mode button: `A` (default `pi_mode_button=a`)
- Manual linear command (`/cmd_vel.linear.x`): `-left_stick_y` with deadband and scaling by `max_linear_speed`
- Manual angular command (`/cmd_vel.angular.z`): `left_stick_x` with deadband and scaling by `max_angular_speed`
- Servo command (`/servo_cmd`): selected axis (default `right_stick_y`) mapped from `[-1, 1]` to `[servo_min_angle_deg, servo_max_angle_deg]`

Defaults and behavior notes:

- Servo axis inversion is enabled by default (`servo_axis_invert=true`)
- If `servo_only_when_enabled=true` and enable is not held, servo command falls back to `servo_default_angle_deg`
- Triggers and D-pad are published in `/gamepad`, but are not used by `robot_control_node` motion logic by default

### Control Loop Note

- PI is intentionally applied to speed tracking.
- Position regulation is done by P/PD in the outer loop.
- This avoids integral windup directly on position while keeping responsive speed control.

## Troubleshooting

- If `micro_ros_setup` is missing, source both ROS setup files.
- If flashing fails, check the USB device mapping and permissions.
- If WiFi does not connect, re-run provisioning and confirm the SSID/password.
- If motion feels jerky, lower the motor or servo rate limits in Kconfig.
- If the servo does not move, confirm the PWM GPIO matches your wiring and the topic message is a single floating point angle.
- If a motor spins the wrong way, swap the direction GPIO logic in hardware or adjust the motor wiring.
- If launch fails with `file not found: [Errno 2] No such file or directory: 'xacro'`, install xacro in the running container or rebuild from the latest Dockerfile image.
- If launch reports package missing for `rviz2` or `gazebo_ros`, rebuild containers so runtime ROS GUI/simulation dependencies are present.
- If RViz RobotModel shows missing transform for `rear_left_wheel` or `rear_right_wheel`, restart launch from updated sources; rear wheel TF fallback is provided by launch when `use_joint_state_publisher:=false`.

### Interpreting Current Debug Logs

- `NVS open for read failed: 0x1102`
  - Means no credentials are stored yet in namespace `wifi_creds`.
  - This is expected on first boot before successful provisioning.

- `Ultrasonic timeout(wait high)`
  - Trigger was sent but ECHO never went high.
  - Check hardware in order: shared GND, TRIG/ECHO wiring, sensor power, and ECHO level shifting to 3.3V-safe GPIO input.

- `Starting ROS node setup...` then immediate reboot
  - Startup entered micro-ROS initialization path but reset before completion.
  - Use monitor logs around watchdog messages (`WDT delete current task`, `WDT add current task`) to isolate failure stage.

### Verified Sensor Output Snapshot (From Real Device Logs)

- IMU values are publishing with corrected gyro terms after startup calibration.
- Ultrasonic was verified with pulse widths around `344-401 us`, corresponding to `~0.059-0.069 m`.
- If ultrasonic values disappear and timeouts return, treat it as hardware-edge detection loss, not a filter issue.

## Project Entry Points

- Main controller firmware: `firmware/custom/esp32_controller`
- Reference firmware variant: `firmware/freertos_apps/apps/esp32_controller`
