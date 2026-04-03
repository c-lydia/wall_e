#include <stdio.h>
#include <unistd.h>
#include <math.h>

#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/imu.h>
#include <sensor_msgs/msg/range.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c.h"
#include "driver/gpio.h"

#include <rmw_microros/rmw_microros.h>

// Error checking macros
#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){printf("Failed status on line %d: %d. Aborting.\n",__LINE__,(int)temp_rc);vTaskDelete(NULL);}}
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){printf("Failed status on line %d: %d. Continuing.\n",__LINE__,(int)temp_rc);}}

// MPU6050 I2C Configuration
#define I2C_MASTER_SCL_IO           22      // GPIO for I2C SCL
#define I2C_MASTER_SDA_IO           21      // GPIO for I2C SDA
#define I2C_MASTER_NUM              I2C_NUM_0
#define I2C_MASTER_FREQ_HZ          100000
#define MPU6050_ADDR                0x68

// Ultrasonic sensor pins
#define ULTRASONIC_TRIG_PIN         9
#define ULTRASONIC_ECHO_PIN         10

// MPU6050 Registers
#define MPU6050_PWR_MGMT_1          0x6B
#define MPU6050_ACCEL_XOUT_H        0x3B
#define MPU6050_GYRO_XOUT_H         0x43

#define WIFI_SSID "i_need_to_sleep"
#define WIFI_PASS "12345678"

// ROS publishers
rcl_publisher_t imu_pub;
rcl_publisher_t range_pub;

// ROS messages
sensor_msgs__msg__Imu imu_msg;
sensor_msgs__msg__Range range_msg;

static void wifi_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
        printf("Retrying WiFi connection...\n");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        printf("WiFi Connected! Got IP\n");
    }
}

void wifi_init(void) {
    nvs_flash_init();
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    
    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL);
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
        },
    };
   
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(ESP_IF_WIFI_STA, &wifi_config);
    esp_wifi_start();

    printf("WiFi initialization complete\n");

    // Wait until connected
    xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
}

// I2C Initialization
void i2c_master_init(void) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };

    i2c_param_config(I2C_MASTER_NUM, &conf);
    i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
}

// MPU6050 Write Register
esp_err_t mpu6050_write_byte(uint8_t reg_addr, uint8_t data) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (MPU6050_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg_addr, true);
    i2c_master_write_byte(cmd, data, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}

// MPU6050 Read Multiple Bytes
esp_err_t mpu6050_read_bytes(uint8_t reg_addr, uint8_t *data, size_t len) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (MPU6050_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg_addr, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (MPU6050_ADDR << 1) | I2C_MASTER_READ, true);

    if (len > 1) {
        i2c_master_read(cmd, data, len - 1, I2C_MASTER_ACK);
    }

    i2c_master_read_byte(cmd, data + len - 1, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}

// MPU6050 Initialize
void mpu6050_init(void) {
    // Wake up MPU6050
    mpu6050_write_byte(MPU6050_PWR_MGMT_1, 0x00);
    vTaskDelay(100 / portTICK_PERIOD_MS);
}

// Read MPU6050 Data
void mpu6050_read_data(int16_t *accel, int16_t *gyro) {
    uint8_t data[14];
    
    mpu6050_read_bytes(MPU6050_ACCEL_XOUT_H, data, 14);
    
    // Accelerometer
    accel[0] = (int16_t)((data[0] << 8) | data[1]);
    accel[1] = (int16_t)((data[2] << 8) | data[3]);
    accel[2] = (int16_t)((data[4] << 8) | data[5]);
    
    // Gyroscope
    gyro[0] = (int16_t)((data[8] << 8) | data[9]);
    gyro[1] = (int16_t)((data[10] << 8) | data[11]);
    gyro[2] = (int16_t)((data[12] << 8) | data[13]);
}

// Ultrasonic sensor initialization
void ultrasonic_init(void) {
    gpio_config_t io_conf = {};
    
    // Configure trigger pin as output
    io_conf.intr_type = GPIO_INTR_DISABLE;
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pin_bit_mask = (1ULL << ULTRASONIC_TRIG_PIN);
    io_conf.pull_down_en = 0;
    io_conf.pull_up_en = 0;
    gpio_config(&io_conf);
    
    // Configure echo pin as input
    io_conf.mode = GPIO_MODE_INPUT;
    io_conf.pin_bit_mask = (1ULL << ULTRASONIC_ECHO_PIN);
    gpio_config(&io_conf);
}

// Read ultrasonic distance
float ultrasonic_read_distance(void) {
    // Trigger pulse
    gpio_set_level(ULTRASONIC_TRIG_PIN, 0);
    ets_delay_us(2);
    gpio_set_level(ULTRASONIC_TRIG_PIN, 1);
    ets_delay_us(10);
    gpio_set_level(ULTRASONIC_TRIG_PIN, 0);
    
    // Wait for echo to go high
    int64_t start_time = esp_timer_get_time();

    while (gpio_get_level(ULTRASONIC_ECHO_PIN) == 0) {
        if ((esp_timer_get_time() - start_time) > 30000) { // 30ms timeout
            return -1.0;
        }
    }
    
    // Measure pulse duration
    int64_t pulse_start = esp_timer_get_time();

    while (gpio_get_level(ULTRASONIC_ECHO_PIN) == 1) {
        if ((esp_timer_get_time() - pulse_start) > 30000) {
            return -1.0;
        }
    }

    int64_t pulse_end = esp_timer_get_time();
    
    long duration = pulse_end - pulse_start;
    
    // Calculate distance in meters (speed of sound = 343 m/s)
    return duration * 0.0001715;
}

// Timer callback for publishing sensor data
void timer_callback(rcl_timer_t * timer, int64_t last_call_time) {
    RCLC_UNUSED(last_call_time);
    
    if (timer != NULL) {
        int16_t accel[3], gyro[3];
        
        // Read MPU6050
        mpu6050_read_data(accel, gyro);
        
        // Convert to SI units
        imu_msg.linear_acceleration.x = (accel[0] / 16384.0) * 9.81;
        imu_msg.linear_acceleration.y = (accel[1] / 16384.0) * 9.81;
        imu_msg.linear_acceleration.z = (accel[2] / 16384.0) * 9.81;
        
        imu_msg.angular_velocity.x = (gyro[0] / 131.0) * (M_PI / 180.0);
        imu_msg.angular_velocity.y = (gyro[1] / 131.0) * (M_PI / 180.0);
        imu_msg.angular_velocity.z = (gyro[2] / 131.0) * (M_PI / 180.0);
        
        // Publish IMU data
        RCSOFTCHECK(rcl_publish(&imu_pub, &imu_msg, NULL));
        
        // Read ultrasonic sensor
        float distance = ultrasonic_read_distance();

        if (distance > 0) {
            range_msg.range = distance;
            RCSOFTCHECK(rcl_publish(&range_pub, &range_msg, NULL));
        }
        
        printf("IMU - Accel: %.2f, %.2f, %.2f | Gyro: %.2f, %.2f, %.2f | Range: %.2f\n",
               imu_msg.linear_acceleration.x,
               imu_msg.linear_acceleration.y,
               imu_msg.linear_acceleration.z,
               imu_msg.angular_velocity.x,
               imu_msg.angular_velocity.y,
               imu_msg.angular_velocity.z,
               range_msg.range);
    }
}

void appMain(void * arg) {
    wifi_init(); 
    
    // Initialize hardware
    i2c_master_init();
    mpu6050_init();
    ultrasonic_init();
    
    rcl_allocator_t allocator = rcl_get_default_allocator();
    rclc_support_t support;

    rcl_init_options_t init_options = rcl_get_zero_initialized_init_options();
    RCCHECK(rcl_init_options_init(&init_options, allocator));
    RCCHECK(rclc_support_init_with_options(&support, 0, NULL, &init_options, &allocator));

    // Create node
    rcl_node_t node;
    RCCHECK(rclc_node_init_default(&node, "sensor_node", "", &support));

    // Create IMU publisher
    RCCHECK(rclc_publisher_init_default(
        &imu_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu),
        "imu/data"));

    // Create Range publisher
    RCCHECK(rclc_publisher_init_default(
        &range_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Range),
        "range/data"));

    // Initialize messages
    sensor_msgs__msg__Imu__init(&imu_msg);
    sensor_msgs__msg__Range__init(&range_msg);
    
    // Set frame IDs
    imu_msg.header.frame_id.data = "imu_link";
    imu_msg.header.frame_id.size = strlen("imu_link");
    imu_msg.header.frame_id.capacity = strlen("imu_link") + 1;
    
    range_msg.header.frame_id.data = "ultrasonic_link";
    range_msg.header.frame_id.size = strlen("ultrasonic_link");
    range_msg.header.frame_id.capacity = strlen("ultrasonic_link") + 1;
    
    range_msg.radiation_type = sensor_msgs__msg__Range__ULTRASOUND;
    range_msg.field_of_view = 0.26; // ~15 degrees in radians
    range_msg.min_range = 0.02;     // 2cm
    range_msg.max_range = 4.0;      // 4m

    // Create timer (100ms = 10Hz)
    rcl_timer_t timer;
    const unsigned int timer_timeout = 100;
    RCCHECK(rclc_timer_init_default(
        &timer,
        &support,
        RCL_MS_TO_NS(timer_timeout),
        timer_callback));

    // Create executor
    rclc_executor_t executor;
    RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
    RCCHECK(rclc_executor_add_timer(&executor, &timer));

    printf("Sensor node started!\n");

    // Main loop
    while(1) {
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));
        usleep(10000);
    }

    // Cleanup (won't reach here, but good practice)
    RCCHECK(rcl_publisher_fini(&imu_pub, &node));
    RCCHECK(rcl_publisher_fini(&range_pub, &node));
    RCCHECK(rcl_node_fini(&node));

    vTaskDelete(NULL);
}