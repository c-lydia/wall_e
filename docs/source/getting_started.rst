.. _getting_started:

===============
Getting Started
===============

Quick Start Guide
=================

Prerequisites
-------------

- Docker and Docker Compose
- ESP-IDF v5.0+ (for ESP32 firmware)
- Git

Initial Setup
=============

1. Clone the repository:

.. code-block:: bash

   git clone https://github.com/c-lydia/wall_e.git
   cd wall_e/micro_ros_ws

2. Start the Docker Compose environment:

.. code-block:: bash

   docker compose up

3. Build your ROS 2 packages:

.. code-block:: bash

   # In the workspace container
   colcon build

Building the ESP32 Firmware
==============================

.. code-block:: bash

   cd firmware/dev_ws
   idf.py build
   idf.py flash
   idf.py monitor

Next Steps
==========

- Read the :doc:`firmware/esp32_controller` documentation
- Explore the :doc:`architecture` overview
- Check :doc:`troubleshooting` for common issues
