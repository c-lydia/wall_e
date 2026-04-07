.. _concepts:

========
Concepts
========

This page describes the core system concepts used in Wall-E and how data flows through firmware, feedback, localization, and control.

Layered Roles
=============

The stack is organized into four responsibilities:

- **firmware**: hardware I/O, real-time safety, and actuator output on ESP32
- **feedback**: filtering and fusion of raw sensor streams
- **localization**: state estimation from fused signals
- **control**: converting operator/autonomy intent into actuator commands

Architecture Flow (Text Diagram)
================================

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

Main flow:

1. ``esp32_controller`` publishes raw ``/imu/data`` and ``/range/data``.
2. ``imu_filter`` and ``ultrasonic_filter`` clean those signals.
3. ``sensor_fusion`` combines filtered streams for stable state signals.
4. ``odometry`` and ``robot_control`` consume that state and generate commands.
5. Commands are transformed by ``inverse_kinematic`` and sent back to firmware.

Raw vs Filtered Signals
=======================

Raw sensors are noisy and may contain spikes or short dropouts.
The host feedback stage improves signal quality before localization or control:

- IMU path: bias-aware fusion in ``imu_filter.py``
- Range path: validity checks + median + EMA in ``ultrasonic_filter.py``

Fusion Strategy
===============

The current fusion approach prioritizes practical deployment over model-heavy complexity:

- prediction from IMU-derived motion trend
- correction from filtered range observations

This gives robust behavior with straightforward parameter tuning.

Safety Model
============

Safety remains firmware-local and independent from host nodes:

- watchdog supervision
- motor command timeout
- emergency stop topic handling
- WiFi provisioning + reconnect behavior

If host nodes are restarted, firmware safety constraints still apply.

Tuning Guidance
===============

Tune each layer separately for faster iteration:

- firmware layer: motor/servo limits, GPIO mapping, timing
- feedback layer: filter alpha, window size, jump gate, fusion gains
- localization/control layer: kinematic assumptions and controller gains

Related Reading
===============

- :doc:`architecture`
- :doc:`firmware/esp32_controller`
- :doc:`workflow_and_commands`
