============
Architecture
============

System Overview
===============

The micro_ros_ws system consists of multiple interconnected components:

.. code-block:: text

   ┌─────────────────────────────────────────┐
   │         ROS 2 Humble (Host)             │
   │  - micro-ROS Agent (Port 9999 UDP)      │
   │  - Sensor subscribers                   │
   └────────────────▲─────────────────────────┘
                    │ UDP
   ┌────────────────▼─────────────────────────┐
   │          ESP32 + FreeRTOS                │
   │  - IMU (MPU6050) via I2C                 │
   │  - Ultrasonic Sensor (HC-SR04)           │
   │  - micro-ROS Client                      │
   └──────────────────────────────────────────┘

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
===================

1. ESP32 publishes sensor data to micro-ROS agent (UDP port 9999)
2. micro-ROS agent translates to ROS 2 topics
3. ROS 2 subscribers receive sensor messages
4. (Optionally) ROS 2 commands published back to ESP32

Data Types
==========

- ``sensor_msgs/msg/Imu``: 6-axis IMU data
- ``sensor_msgs/msg/Range``: Ultrasonic distance measurements
