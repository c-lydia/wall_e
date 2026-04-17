.. _architecture:

============
Architecture
============


System Overview
===============

The micro_ros_ws system consists of firmware and host ROS 2 components with explicit feedback, localization, and control stages:

.. code-block:: text

   ROS 2
   ├─ control
   │  ├─ Gamepad
   │  └─ robot_control
   ├─ feedback
   │  ├─ imu_filter
   │  ├─ ultrasonic_filter
   │  └─ sensor_fusion
   └─ localization
      ├─ inverse_kinematic
      └─ odometry

   firmware
   └─ esp32_controller

Component Descriptions
======================

Host System (Docker)
--------------------

- **workspace container**: Builds and runs ROS 2 packages
- **micro_ros_agent**: Handles communication with ESP32
- **Volume mounts**: For persistent src/, build/, install/, docs/

ESP32 Firmware
--------------

- **FreeRTOS**: Real-time operating system
- **micro-ROS Client**: Lightweight ROS 2 client library
- **Sensor drivers**: I2C for IMU, GPIO for ultrasonic sensor

Communication Flow
==================

1. ``esp32_controller`` publishes raw IMU and range data via micro-ROS over UDP.
2. Host feedback nodes (``imu_filter`` and ``ultrasonic_filter``) clean raw streams.
3. ``sensor_fusion`` combines filtered streams into more stable state outputs.
4. ``odometry_node`` produces ``/odom`` from command and sensor streams.
5. ``robot_control_node`` publishes ``/cmd_vel`` from operator intent, safety logic, and cascaded control (P/PD outer loop, PI speed inner loop).
6. ``robot_control_node`` also publishes ``/servo_cmd`` (angle command in degrees) from configurable gamepad axis mapping.
7. ``inverse_kinematic_node`` converts ``/cmd_vel`` into ``/motor_cmd`` for firmware.

Data Types
==========

- ``sensor_msgs/msg/Imu``: 6-axis IMU data
- ``sensor_msgs/msg/Range``: Ultrasonic distance measurements

Primary Topic Paths
===================

- ``/imu/data`` -> ``/imu/filter``
- ``/range/data`` -> ``/range/filter``
- ``/imu/filter`` + ``/range/filter`` -> ``/fusion/height``
- ``/imu/filter`` + ``/range/filter`` -> ``/fusion/vertical_velocity``
- ``/gamepad`` -> ``/cmd_vel``
- ``/gamepad`` -> ``/servo_cmd``
- ``/cmd_vel`` + sensors -> ``/odom``
- ``/cmd_vel`` -> ``/motor_cmd``

Visualization and TF Notes
==========================

- Wheel links are part of robot description as continuous joints.
- In default minimal launch mode, rear wheel transforms are provided by static TF fallback.
- When ``joint_state_publisher`` is enabled, fallback static rear-wheel publishers are disabled.

This preserves a complete RViz RobotModel tree while preventing duplicate transform sources.
