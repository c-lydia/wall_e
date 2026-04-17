.. _getting_started:

===============
Getting Started
===============

Quick Start Guide
=================

Prerequisites
-------------

- Docker and Docker Compose
- Git

Initial Setup
=============

1. Clone the repository:

.. code-block:: bash

   git clone https://github.com/c-lydia/wall_e.git
   cd wall_e/micro_ros_ws

2. Start the Docker Compose environment:

.. code-block:: bash

   docker compose up -d

3. Enter the workspace container and build host packages:

.. code-block:: bash

   docker compose exec workspace bash
   cd /micro_ros_ws
   source /opt/ros/humble/setup.bash
   colcon build
   source /micro_ros_ws/install/setup.bash

4. Launch the integrated stack:

.. code-block:: bash

   ros2 launch wall_e_description wall_e.launch.py

If GUI authorization fails on the host (X11), run on host before launching GUI apps:

.. code-block:: bash

   xhost +si:localuser:root

Building the ESP32 Firmware
==============================

.. code-block:: bash

   ros2 run micro_ros_setup configure_firmware.sh esp32_controller -t udp -i 192.168.1.2 -p 8888
   ros2 run micro_ros_setup build_firmware.sh
   ros2 run micro_ros_setup flash_firmware.sh

Next Steps
==========

- Read the :doc:`firmware/esp32_controller` documentation
- Explore the :doc:`architecture` overview
- Check :doc:`troubleshooting` for common issues
