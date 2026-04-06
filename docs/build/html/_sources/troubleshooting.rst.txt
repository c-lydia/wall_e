.. _troubleshooting:

===============
Troubleshooting
===============


Common Issues and Solutions
============================

Docker Compose Issues
---------------------

**Problem**: Port 9999 already in use

.. code-block:: bash

   # Kill any existing micro-ROS processes
   killall -9 micro_ros_agent 2>/dev/null
   
   # Or change port in docker-compose.yaml
   nano docker-compose.yaml

**Problem**: Docker image build fails

.. code-block:: bash

   # Clean and rebuild
   docker compose down
   docker system prune -f
   docker compose build --no-cache
   docker compose up

ESP32 Firmware Issues
---------------------

**Problem**: I2C communication fails with MPU6050

- Verify pull-up resistors (4.7kΩ recommended) on SCL/SDA lines
- Check connections: GPIO 22 (SCL), GPIO 21 (SDA)
- Confirm I2C address: 0x68 (check with ``i2cdetect``)
- Reduce I2C frequency if needed

**Problem**: Ultrasonic sensor readings are incorrect

- Verify GPIO 9 (Trigger) and GPIO 10 (Echo) are connected
- Check power supply voltage (5V needed for HC-SR04)
- Ensure no interference from other GPIO operations
- Test with a simple GPIO toggle program first

**Problem**: ESP32 won't flash

.. code-block:: bash

   # Check USB connection
   ls -l /dev/ttyUSB*
   
   # Erase flash completely
   idf.py erase-flash
   
   # Try again
   idf.py flash

micro-ROS Connection Issues
----------------------------

**Problem**: ESP32 can't connect to WiFi

- Verify SSID and password in ``app.c``
- Check WiFi network is accessible from ESP32 location
- Enable serial monitor to see debug output:

.. code-block:: bash

   idf.py monitor

**Problem**: micro-ROS topics not appearing on host

- Verify micro-ROS agent is running:

.. code-block:: bash

   docker compose ps

- Check port 9999 is open:

.. code-block:: bash

   netstat -tuln | grep 9999

- Monitor agent logs:

.. code-block:: bash

   docker compose logs micro_ros_agent

- Verify ESP32 can reach host (test ping from ESP32)

ROS 2 Build Issues
------------------

**Problem**: Package dependencies not found

.. code-block:: bash

   # Inside workspace container
   rosdep update
   rosdep install --from-paths src --ignore-src -y

**Problem**: colcon build fails

.. code-block:: bash

   # Clean and rebuild
   rm -rf build install log
   colcon build

Documentation Build Issues
---------------------------

**Problem**: Sphinx documentation won't build

.. code-block:: bash

   # Inside workspace container
   cd docs
   sphinx-build -W -b html source _build/html

Using Debug Tools
==================

Serial Monitor (ESP32)
----------------------

.. code-block:: bash

   idf.py monitor -p /dev/ttyUSB0 -b 115200

ROS 2 Message Inspection
------------------------

.. code-block:: bash

   # In host ROS 2 environment
   ros2 topic list
   ros2 topic echo /imu/data
   ros2 topic echo /range/data

Getting Help
============

1. Check serial output from ESP32 for error messages
2. Review micro-ROS agent logs
3. Verify hardware connections with multimeter
4. Check ROS 2 node graph: ``rqt_graph``
