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