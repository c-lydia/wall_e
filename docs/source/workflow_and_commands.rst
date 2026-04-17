======================
Workflow and Commands
======================

This page collects the day-to-day commands for working in the Wall-E micro-ROS workspace.

Development Workflow
====================

1. Start the Docker workspace.
2. Enter the container and source ROS 2.
3. Create the firmware workspace if it does not exist.
4. Configure the ESP32 firmware for the app and transport.
5. Build the firmware.
6. Flash the board and monitor serial output.

Workspace Commands
===================

Start the containers:

.. code-block:: bash

   docker compose up -d

Enter the workspace container:

.. code-block:: bash

   docker compose exec workspace bash

Source the ROS environment inside the container:

.. code-block:: bash

   source /opt/ros/humble/setup.bash
   source install/setup.bash

Launch Commands
===============

Integrated launch:

.. code-block:: bash

   ros2 launch wall_e_description wall_e.launch.py

RViz-only mode (no Gazebo):

.. code-block:: bash

   ros2 launch wall_e_description wall_e.launch.py use_gazebo:=false use_rviz:=true

Enable joint_state_publisher explicitly:

.. code-block:: bash

   ros2 launch wall_e_description wall_e.launch.py use_joint_state_publisher:=true

If runtime packages are missing in an older running container, rebuild image:

.. code-block:: bash

   docker compose up --build -d

Firmware Commands
=================

Create the firmware workspace once, or again after a clean reset:

.. code-block:: bash

   ros2 run micro_ros_setup create_firmware_ws.sh freertos esp32

Configure the ESP32 app:

.. code-block:: bash

   ros2 run micro_ros_setup configure_firmware.sh esp32_controller \
     --transport udp \
     --ip 192.168.43.217 \
     --port 9999

Build the firmware:

.. code-block:: bash

   ros2 run micro_ros_setup build_firmware.sh

Flash the board:

.. code-block:: bash

   export ESPPORT=/dev/ttyUSB0
   ros2 run micro_ros_setup flash_firmware.sh

Useful Checks
=============

If configuration fails with a missing ``PLATFORM`` file, the firmware workspace has not been created yet.

Check that the custom app exists in the mounted firmware tree:

.. code-block:: bash

   ls firmware/custom/esp32_controller

If the serial port is not visible, confirm the device exists on the host and is passed into the container.

Notes
=====

- The ESP32 app source lives in ``firmware/custom/esp32_controller/app.c``.
- The workspace uses Docker for reproducible builds.
- The firmware creation step downloads and prepares the ESP-IDF toolchain, so it can take several minutes.
- Launch uses Python xacro processing for robot description generation.
- Rear wheel TF fallback is provided by launch when ``use_joint_state_publisher:=false``.

Host Runtime Commands
=====================

After building and sourcing:

.. code-block:: bash

   ros2 run control gamepad_node
   ros2 run control robot_control_node
   ros2 run localization odometry_node
   ros2 run localization inverse_kinematic_node

Topic checks:

.. code-block:: bash

   ros2 topic echo /gamepad
   ros2 topic echo /cmd_vel
   ros2 topic echo /servo_cmd
   ros2 topic echo /odom
   ros2 topic echo /motor_cmd

Operator Mapping (Default)
==========================

- Hold ``LB`` to enable motion commands.
- Move left stick Y for linear speed (internally ``-left_stick_y``).
- Move left stick X for angular speed.
- Hold ``A`` to engage hold/PI mode.
- Move right stick Y to drive servo angle output on ``/servo_cmd`` (default axis).