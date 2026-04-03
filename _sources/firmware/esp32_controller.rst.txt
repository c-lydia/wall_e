================
ESP32 Controller
================

The ESP32 controller is the main FreeRTOS application running on the ESP32, handling sensor I/O and micro-ROS communication.

Overview
========

The controller manages:

- **IMU (MPU6050)**: Accelerometer and gyroscope data via I2C
- **Ultrasonic Sensor (HC-SR04)**: Range/distance measurements  
- **micro-ROS Agent**: UDP communication with the host ROS 2 system

Hardware Configuration
======================

I2C (IMU)
---------

- **SCL (GPIO 22)**: Serial Clock
- **SDA (GPIO 21)**: Serial Data
- **Device Address**: 0x68 (MPU6050)
- **Frequency**: 100 kHz

Ultrasonic Sensor
-----------------

- **Trigger Pin**: GPIO 9
- **Echo Pin**: GPIO 10

Build and Flash
===============

Prerequisites
-------------

- ESP-IDF v5.0+
- micro-ROS firmware libraries
- FreeRTOS patched for micro-ROS

Build Command
-------------

.. code-block:: bash

   cd firmware/dev_ws
   idf.py build

Flash Command
-------------

.. code-block:: bash

   idf.py flash

Monitor Serial Output
---------------------

.. code-block:: bash

   idf.py monitor

Code Structure
==============

.. code-block:: text

   firmware/custom/esp32_controller/
   ├── app.c                 # Main application logic
   └── app-colcon.meta       # Build configuration

Main Functions
--------------

The controller implements several key functions for operation:

**app_main()** - Entry Point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

   void app_main(void) {
       ESP_LOGI(TAG, "Starting Wall-E ESP32 Controller");
       
       // Initialize WiFi
       wifi_init();
       
       // Initialize I2C for IMU
       i2c_master_init();
       
       // Initialize GPIO for ultrasonic
       ultrasonic_init();
       
       // Initialize micro-ROS
       rcl_allocator_t allocator = rcl_get_default_allocator();
       rclc_support_init(&support, 0, NULL, &allocator);
       
       // Create node
       rclc_node_init_default(&node, "esp32_node", "", &support);
       
       // Create publishers
       rclc_publisher_init_default(
           &imu_pub,
           &node,
           ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu),
           "/imu"
       );
       
       // Create timer for publishing at 10Hz
       rclc_timer_init_default(&timer, &support, RCL_MS_TO_NS(100), timer_callback);
       
       // Start executor
       rclc_executor_init(&executor, &support.context, 1, &allocator);
       rclc_executor_add_timer(&executor, &timer);
       
       ESP_LOGI(TAG, "Wall-E ESP32 Controller initialized successfully");
   }

**timer_callback()** - Sensor Publishing Loop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

   void timer_callback(rcl_timer_t *timer, int64_t last_call_time) {
       if (timer != NULL) {
           // Read IMU data
           mpu6050_accel_t accel;
           mpu6050_gyro_t gyro;
           mpu6050_read_accel(&accel);
           mpu6050_read_gyro(&gyro);
           
           // Publish IMU message
           sensor_msgs__msg__Imu imu_msg = {0};
           imu_msg.linear_acceleration.x = accel.x;
           imu_msg.linear_acceleration.y = accel.y;
           imu_msg.linear_acceleration.z = accel.z;
           imu_msg.angular_velocity.x = gyro.x;
           imu_msg.angular_velocity.y = gyro.y;
           imu_msg.angular_velocity.z = gyro.z;
           
           rcl_publish(&imu_pub, &imu_msg, NULL);
           
           // Read and publish ultrasonic range
           float distance_m = ultrasonic_read_distance_cm() / 100.0f;
           sensor_msgs__msg__Range range_msg = {0};
           range_msg.range = distance_m;
           range_msg.min_range = 0.02f;
           range_msg.max_range = 4.0f;
           
           rcl_publish(&range_pub, &range_msg, NULL);
       }
   }

**WiFi Initialization**
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

   void wifi_init(void) {
       tcpip_adapter_init();
       ESP_ERROR_CHECK(esp_event_loop_create_default());
       
       wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
       ESP_ERROR_CHECK(esp_wifi_init(&cfg));
       
       wifi_config_t wifi_config = {
           .sta = {
               .ssid = WIFI_SSID,
               .password = WIFI_PASS,
           },
       };
       
       ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
       ESP_ERROR_CHECK(esp_wifi_set_config(ESP_IF_WIFI_STA, &wifi_config));
       ESP_ERROR_CHECK(esp_wifi_start());
       
       ESP_LOGI(TAG, "WiFi initialized, connecting to SSID: %s", WIFI_SSID);
   }

**I2C Master Initialization**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

   void i2c_master_init(void) {
       const i2c_config_t i2c_config = {
           .mode = I2C_MODE_MASTER,
           .sda_io_num = I2C_MASTER_SDA_IO,  // GPIO 21
           .scl_io_num = I2C_MASTER_SCL_IO,  // GPIO 22
           .sda_pullup_en = GPIO_PULLUP_ENABLE,
           .scl_pullup_en = GPIO_PULLUP_ENABLE,
           .master.clk_speed = I2C_MASTER_FREQ_HZ,  // 100 kHz
       };
       
       ESP_ERROR_CHECK(i2c_param_config(I2C_MASTER_NUM, &i2c_config));
       ESP_ERROR_CHECK(i2c_driver_install(I2C_MASTER_NUM, i2c_config.mode, 0, 0, 0));
   }

Key Constants
~~~~~~~~~~~~~

.. code-block:: c

   // WiFi Configuration
   #define WIFI_SSID              "your_wifi_ssid"
   #define WIFI_PASS              "your_wifi_password"
   
   // I2C Configuration
   #define I2C_MASTER_NUM         0
   #define I2C_MASTER_SDA_IO      21
   #define I2C_MASTER_SCL_IO      22
   #define I2C_MASTER_FREQ_HZ     100000
   
   // GPIO Configuration  
   #define ULTRASONIC_TRIGGER_GPIO 9
   #define ULTRASONIC_ECHO_GPIO    10
   
   // micro-ROS Configuration
   #define RCL_MAX_NODES          1
   #define RCL_MAX_PUBLISHERS     2
   #define RCL_HISTORY_DEPTH      4

ROS Publishers
==============

.. table::
   :align: center

   ================== ============================== ================================
   Topic              Message Type                   Description
   ================== ============================== ================================
   ``/imu``           ``sensor_msgs::msg::Imu``      6-axis IMU data (accel + gyro)
   ``/range``         ``sensor_msgs::msg::Range``    Ultrasonic distance measurement
   ================== ============================== ================================

WiFi Configuration
===================

.. code-block:: c

   #define WIFI_SSID "your_wifi_ssid"
   #define WIFI_PASS "your_wifi_password"

.. warning::
   Update WiFi credentials in ``app.c`` before building. The placeholder values above are for documentation only.

Troubleshooting
===============

I2C Communication Fails
-----------------------

- Check pull-up resistors on SCL/SDA
- Verify I2C frequency (100 kHz default)
- Confirm MPU6050 address matches (0x68)

Ultrasonic Measurements Are Erratic
------------------------------------

- Ensure GPIO 9/10 are not used elsewhere
- Check sensor power supply (5V recommended)
- Verify echo pin is connected to an ADC-capable GPIO

micro-ROS Connection Issues
----------------------------

- Confirm WiFi SSID/password are correct
- Check micro-ROS agent is running (``docker compose up``)
- Verify UDP port 9999 is accessible
- Ensure ESP32 can reach the host machine on the network

Future Enhancements
===================

- [ ] Add magnetometer (compass) support
- [ ] Implement sensor fusion (Kalman filter)
- [ ] Add servo/motor control
- [ ] SD card logging for offline recording
