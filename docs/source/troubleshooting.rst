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

- Verify GPIO 5 (Trigger) and GPIO 18 (Echo) are connected
- Check power supply voltage (5V needed for HC-SR04)
- Ensure ECHO line is 3.3V-safe for ESP32 input (use divider/level shifter if sensor drives 5V)
- Ensure common ground between ESP32 and sensor
- Test with a simple GPIO toggle program first

**Problem**: `Ultrasonic timeout(wait high)` appears repeatedly

- Trigger pulses are being generated, but no ECHO rising edge is detected
- Re-check TRIG/ECHO wiring order and continuity
- Confirm sensor power stability under load
- Move a target to 5-20 cm in front of sensor to force a measurable echo

**Problem**: Device resets after `Starting ROS node setup...`

- Check serial output for watchdog markers around ROS init
- Verify middleware/transport configuration is valid before node startup
- Keep startup sensor diagnostics before ROS setup to separate hardware faults from middleware faults

**Problem**: `NVS open for read failed: 0x1102`

- No WiFi credentials are present yet in NVS namespace `wifi_creds`
- Provision credentials through SoftAP flow and reboot

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

Launch and Visualization Issues
-------------------------------

**Problem**: Launch fails with ``file not found: [Errno 2] No such file or directory: 'xacro'``

- Ensure xacro runtime is installed in the running container:

.. code-block:: bash

   apt-get update && apt-get install -y ros-humble-xacro

- For long-term consistency, rebuild the workspace image:

.. code-block:: bash

   docker compose up --build -d

**Problem**: ``Package not found`` for ``rviz2`` or ``gazebo_ros``

- The running container is missing runtime GUI/simulation packages.
- Rebuild using the latest Dockerfile so ROS runtime dependencies are present.

**Problem**: RViz RobotModel shows ``No transform from rear_left_wheel`` or ``rear_right_wheel``

- Rear wheels are continuous joints and may not have live joint states in minimal launch configurations.
- Current launch publishes rear-wheel static TF when ``joint_state_publisher`` is disabled.
- If issue persists, verify you are launching updated sources and restart launch.

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
