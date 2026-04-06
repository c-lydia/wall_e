#include <stdio.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "rom/ets_sys.h"

// MPU6050 I2C Configuration
#define I2C_MASTER_SCL_IO           22
#define I2C_MASTER_SDA_IO           21
#define I2C_MASTER_NUM              I2C_NUM_0
#define I2C_MASTER_FREQ_HZ          100000
#define MPU6050_ADDR                0x68

// Ultrasonic sensor pins - FIXED!
#define ULTRASONIC_TRIG_PIN         5
#define ULTRASONIC_ECHO_PIN         18

// MPU6050 Registers
#define MPU6050_PWR_MGMT_1          0x6B
#define MPU6050_ACCEL_XOUT_H        0x3B
#define MPU6050_GYRO_XOUT_H         0x43

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

// MPU6050 Write
esp_err_t mpu6050_write_byte(uint8_t reg_addr, uint8_t data) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (MPU6050_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg_addr, true);
    i2c_master_write_byte(cmd, data, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(1000));
    i2c_cmd_link_delete(cmd);
    return ret;
}

// MPU6050 Read
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
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(1000));
    i2c_cmd_link_delete(cmd);
    return ret;
}

// MPU6050 Init
void mpu6050_init(void) {
    mpu6050_write_byte(MPU6050_PWR_MGMT_1, 0x00);
    vTaskDelay(pdMS_TO_TICKS(100));
}

// MPU6050 Read Data
void mpu6050_read_data(int16_t *accel, int16_t *gyro) {
    uint8_t data[14];
    mpu6050_read_bytes(MPU6050_ACCEL_XOUT_H, data, 14);
    
    accel[0] = (int16_t)((data[0] << 8) | data[1]);
    accel[1] = (int16_t)((data[2] << 8) | data[3]);
    accel[2] = (int16_t)((data[4] << 8) | data[5]);
    
    gyro[0] = (int16_t)((data[8] << 8) | data[9]);
    gyro[1] = (int16_t)((data[10] << 8) | data[11]);
    gyro[2] = (int16_t)((data[12] << 8) | data[13]);
}

// Ultrasonic Init
void ultrasonic_init(void) {
    gpio_config_t io_conf = {};
    
    io_conf.intr_type = GPIO_INTR_DISABLE;
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pin_bit_mask = (1ULL << ULTRASONIC_TRIG_PIN);
    io_conf.pull_down_en = 0;
    io_conf.pull_up_en = 0;
    gpio_config(&io_conf);
    
    io_conf.mode = GPIO_MODE_INPUT;
    io_conf.pin_bit_mask = (1ULL << ULTRASONIC_ECHO_PIN);
    gpio_config(&io_conf);
}

// Ultrasonic Read
float ultrasonic_read_distance(void) {
    gpio_set_level(ULTRASONIC_TRIG_PIN, 0);
    ets_delay_us(2);
    gpio_set_level(ULTRASONIC_TRIG_PIN, 1);
    ets_delay_us(10);
    gpio_set_level(ULTRASONIC_TRIG_PIN, 0);
    
    int64_t start_time = esp_timer_get_time();
    while (gpio_get_level(ULTRASONIC_ECHO_PIN) == 0) {
        if ((esp_timer_get_time() - start_time) > 30000) {
            return -1.0;
        }
    }
    
    int64_t pulse_start = esp_timer_get_time();
    while (gpio_get_level(ULTRASONIC_ECHO_PIN) == 1) {
        if ((esp_timer_get_time() - pulse_start) > 30000) {
            return -1.0;
        }
    }
    int64_t pulse_end = esp_timer_get_time();
    
    long duration = pulse_end - pulse_start;
    return duration * 0.0001715;
}

void appMain(void *argument) {
    (void)argument;
    printf("\n=== ESP32 Sensor Test ===\n");
    
    i2c_master_init();
    printf("✓ I2C initialized\n");
    
    mpu6050_init();
    printf("✓ MPU6050 initialized\n");
    
    ultrasonic_init();
    printf("✓ Ultrasonic initialized\n\n");

    while (1) {
        int16_t accel[3], gyro[3];
        mpu6050_read_data(accel, gyro);

        float ax = (accel[0] / 16384.0f) * 9.81f;
        float ay = (accel[1] / 16384.0f) * 9.81f;
        float az = (accel[2] / 16384.0f) * 9.81f;

        float gx = (gyro[0] / 131.0f) * (M_PI / 180.0f);
        float gy = (gyro[1] / 131.0f) * (M_PI / 180.0f);
        float gz = (gyro[2] / 131.0f) * (M_PI / 180.0f);

        float distance = ultrasonic_read_distance();
        
        printf("Accel: %6.2f %6.2f %6.2f | Gyro: %6.3f %6.3f %6.3f | Dist: %.2fm\n",
               ax, ay, az, gx, gy, gz, distance);

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}