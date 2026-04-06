#include <stdio.h>
#include <unistd.h>
#include <math.h>
#include <string.h>

#include "sdkconfig.h"

#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_err.h"
#include "esp_timer.h"
#include "rom/ets_sys.h"
#include "nvs_flash.h"

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/imu.h>
#include <sensor_msgs/msg/range.h>
#include <std_msgs/msg/float32_multi_array.h>
#include <std_msgs/msg/string.h>
#include <std_msgs/msg/bool.h>

#include "freertos/FreeRTOS.h"
#include "freertos/projdefs.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/portmacro.h"
#include "driver/i2c.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_task_wdt.h"
#include "esp_http_server.h"

#ifdef CONFIG_ESP_WIFI_SSID
#define WIFI_SSID CONFIG_ESP_WIFI_SSID
#else
#define WIFI_SSID ""
#endif

#ifdef CONFIG_ESP_WIFI_PASSWORD
#define WIFI_PASS CONFIG_ESP_WIFI_PASSWORD
#else
#define WIFI_PASS ""
#endif

#define NVS_NAMESPACE "wifi_creds"
#define NVS_SSID_KEY "ssid"
#define NVS_PASS_KEY "password"
#define WIFI_CREDS_MAX_LEN 64

static httpd_handle_t provisioning_server = NULL;
static char stored_ssid[64] = {0};
static char stored_pass[64] = {0};

static EventGroupHandle_t wifi_event_group;
#define WIFI_CONNECTED_BIT BIT0
static esp_netif_t *wifi_sta_netif = NULL;
static int wifi_initialized = 0;

#define RCCHECK(fn) do { \
    rcl_ret_t temp_rc = (fn); \
    if ((temp_rc != RCL_RET_OK)) { \
        printf("Failed status on line %d: %d. Aborting.\\n", __LINE__, (int)temp_rc); \
        vTaskDelete(NULL); \
    } \
} while (0)

#define RCSOFTCHECK(fn) do { \
    rcl_ret_t temp_rc = (fn); \
    if ((temp_rc != RCL_RET_OK)) { \
        printf("Failed status on line %d: %d. Continuing.\\n", __LINE__, (int)temp_rc); \
    } \
} while (0)

#define I2C_MASTER_SCL_IO 22 
#define I2C_MASTER_SDA_IO 21 
#define I2C_MASTER_NUM I2C_NUM_0
#define I2C_MASTER_FREQ_HZ 100000
#define MPU6050_ADDR 0x68

#define ULTRASONIC_TRIG_PIN 5
#define ULTRASONIC_ECHO_PIN 18

#define MPU6050_PWR_MGMT_1 0x6B
#define MPU6050_ACCEL_XOUT_H 0x3B
#define MPU6050_GYRO_XOUT_H 0x43

#define MOTOR_COUNT 4

#define MOTOR1_PWM  25
#define MOTOR1_DIR  26
#define MOTOR2_PWM  27
#define MOTOR2_DIR  14
#define MOTOR3_PWM  12
#define MOTOR3_DIR  13
#define MOTOR4_PWM  33
#define MOTOR4_DIR  32

#define LEDC_TIMER LEDC_TIMER_0
#define LEDC_FREQ 1000

static const int MOTOR_PWM_PIN[MOTOR_COUNT] = {
    MOTOR1_PWM,
    MOTOR2_PWM,
    MOTOR3_PWM,
    MOTOR4_PWM,
};

static const int MOTOR_DIR_PIN[MOTOR_COUNT] = {
    MOTOR1_DIR,
    MOTOR2_DIR,
    MOTOR3_DIR,
    MOTOR4_DIR,
};

rcl_publisher_t imu_pub;
rcl_publisher_t range_pub;
rcl_publisher_t status_pub;
rcl_subscription_t motor_sub;
rcl_subscription_t estop_sub;

static int64_t last_motor_cmd_time = 0;
#define MOTOR_TIMEOUT_MS 500
static float motor_targets[MOTOR_COUNT] = {0.0f};
static volatile int emergency_stop = 0;

sensor_msgs__msg__Imu imu_msg;
sensor_msgs__msg__Range range_msg;
std_msgs__msg__Float32MultiArray motor_msg;
std_msgs__msg__String status_msg;
std_msgs__msg__Bool estop_msg;

rclc_executor_t executor;

esp_err_t nvs_read_wifi_creds(char *ssid_out, char *pass_out) {
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) {
        printf("NVS open for read failed: 0x%02x\n", err);
        return err;
    }
    
    size_t ssid_len = WIFI_CREDS_MAX_LEN;
    size_t pass_len = WIFI_CREDS_MAX_LEN;
    
    err = nvs_get_str(handle, NVS_SSID_KEY, ssid_out, &ssid_len);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        printf("NVS SSID read error: 0x%02x\n", err);
        nvs_close(handle);
        return err;
    }
    
    err = nvs_get_str(handle, NVS_PASS_KEY, pass_out, &pass_len);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        printf("NVS password read error: 0x%02x\n", err);
        nvs_close(handle);
        return err;
    }
    
    nvs_close(handle);
    return ESP_OK;
}

esp_err_t nvs_write_wifi_creds(const char *ssid, const char *password) {
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        printf("NVS open for write failed: 0x%02x\n", err);
        return err;
    }
    
    err = nvs_set_str(handle, NVS_SSID_KEY, ssid);
    if (err != ESP_OK) {
        printf("NVS SSID write error: 0x%02x\n", err);
        nvs_close(handle);
        return err;
    }
    
    err = nvs_set_str(handle, NVS_PASS_KEY, password);
    if (err != ESP_OK) {
        printf("NVS password write error: 0x%02x\n", err);
        nvs_close(handle);
        return err;
    }
    
    err = nvs_commit(handle);
    nvs_close(handle);
    return err;
}

static esp_err_t get_handler(httpd_req_t *req) {
    const char* html_form = "<!DOCTYPE html><html><head><title>ESP32 WiFi Setup</title>"
        "<style>body{font-family:Arial;max-width:400px;margin:50px auto;padding:20px;}"
        "input{display:block;width:100%;padding:8px;margin:10px 0;box-sizing:border-box;}"
        "button{width:100%;padding:10px;margin-top:10px;background:#0066cc;color:white;border:none;cursor:pointer;border-radius:4px;}"
        "</style></head><body><h1>ESP32 Robot WiFi Setup</h1>"
        "<form id='form' method='post' action='/provision'>"
        "<input type='text' name='ssid' placeholder='WiFi SSID' required maxlength='32'>"
        "<input type='password' name='password' placeholder='WiFi Password' required maxlength='63'>"
        "<button type='submit'>Connect</button></form>"
        "<p style='color:#666;font-size:12px;margin-top:20px;'>"
        "Connect your device to ESP32-Setup network, then enter your WiFi credentials above.</p>"
        "</body></html>";
    
    httpd_resp_set_type(req, "text/html; charset=utf-8");
    httpd_resp_send(req, html_form, strlen(html_form));
    return ESP_OK;
}

static esp_err_t post_handler(httpd_req_t *req) {
    char buf[512] = {0};
    int ret = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (ret <= 0) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid request");
        return ESP_FAIL;
    }
    
    buf[ret] = '\0';
    printf("Received provisioning data (len=%d): %s\n", ret, buf);

    char ssid[64] = {0};
    char password[64] = {0};
    
    char *p = strstr(buf, "ssid=");
    if (p) {
        p += 5; 
        int i = 0;
        while (i < 63 && *p != '&' && *p != '\0') {
            ssid[i++] = *p++;
        }
        ssid[i] = '\0';
    }
    
    p = strstr(buf, "password=");
    if (p) {
        p += 9;
        int i = 0;
        while (i < 63 && *p != '&' && *p != '\0') {
            password[i++] = *p++;
        }
        password[i] = '\0';
    }
    
    if (strlen(ssid) > 0 && strlen(password) > 0) {
        printf("Provisioning WiFi: SSID='%s', Password='%s'\n", ssid, password);

        esp_err_t err = nvs_write_wifi_creds(ssid, password);
        if (err != ESP_OK) {
            const char* resp = "<html><body><h1>Error saving credentials</h1><p>NVS write failed. System will restart.</p></body></html>";
            httpd_resp_send(req, resp, strlen(resp));
            return ESP_FAIL;
        }

        strncpy(stored_ssid, ssid, sizeof(stored_ssid) - 1);
        strncpy(stored_pass, password, sizeof(stored_pass) - 1);

        const char* success = "<html><body><h1>WiFi Configured!</h1><p>Device will restart shortly. Reconnect to your WiFi network.</p></body></html>";
        httpd_resp_send(req, success, strlen(success));
        
        printf("Credentials saved to NVS. Shutting down provisioning server...\n");
 
        provisioning_server = NULL;
        return ESP_OK;
    } else {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Missing SSID or password");
        return ESP_FAIL;
    }
}

static void start_provisioning_server(void) {
    if (provisioning_server != NULL) {
        printf("Provisioning server already running\n");
        return;
    }
    
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_uri_handlers = 2;
    
    esp_err_t ret = httpd_start(&provisioning_server, &config);
    if (ret != ESP_OK) {
        printf("Failed to start provisioning server: 0x%02x\n", ret);
        provisioning_server = NULL;
        return;
    }
    
    httpd_uri_t get_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = get_handler,
        .user_ctx = NULL
    };
    
    httpd_uri_t post_uri = {
        .uri = "/provision",
        .method = HTTP_POST,
        .handler = post_handler,
        .user_ctx = NULL
    };
    
    httpd_register_uri_handler(provisioning_server, &get_uri);
    httpd_register_uri_handler(provisioning_server, &post_uri);
    
    printf("Provisioning server started on http://192.168.4.1/\n");
}

static void stop_provisioning_server(void) {
    if (provisioning_server != NULL) {
        httpd_stop(provisioning_server);
        provisioning_server = NULL;
        printf("Provisioning server stopped\n");
    }
}

static void start_softap(void) {
    printf("Starting SoftAP for WiFi provisioning...\n");

    esp_err_t err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        printf("Event loop creation failed: 0x%02x\n", err);
    }

    esp_netif_t *ap_netif = esp_netif_create_default_wifi_ap();
    if (ap_netif == NULL) {
        printf("Failed to create WiFi AP netif\n");
        return;
    }

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    wifi_config_t wifi_config = {
        .ap = {
            .ssid = "ESP32-Setup",
            .ssid_len = 11,
            .password = "",
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };
    
    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    esp_wifi_start();
    
    printf("SoftAP started: SSID='ESP32-Setup' (open)\n");
    printf("Users can connect and navigate to http://192.168.4.1/\n");
}

static void wifi_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
        printf("Retrying WiFi connection...\n");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
        printf("WiFi Connected! Got IP\n");
    }
}

void wifi_init(void) {
    if (wifi_initialized) {
        printf("WiFi already initialized, skipping duplicate init\n");
        return;
    }

    wifi_event_group = xEventGroupCreate();

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    err = esp_netif_init();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_ERROR_CHECK(err);
    }

    err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_ERROR_CHECK(err);
    }

    if (wifi_sta_netif == NULL) {
        wifi_sta_netif = esp_netif_create_default_wifi_sta();
        if (wifi_sta_netif == NULL) {
            printf("Failed to create default WiFi STA netif\n");
            vTaskDelete(NULL);
            return;
        }
    }
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    
    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL);
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = {0},
            .password = {0},
        },
    };

    if (strlen(stored_ssid) > 0) {
        strncpy((char*)wifi_config.sta.ssid, stored_ssid, 32);
        strncpy((char*)wifi_config.sta.password, stored_pass, 64);
    } else {
        strncpy((char*)wifi_config.sta.ssid, WIFI_SSID, 32);
        strncpy((char*)wifi_config.sta.password, WIFI_PASS, 64);
    }
   
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
    wifi_initialized = 1;

    printf("WiFi initialization complete\n");

    EventBits_t bits = xEventGroupWaitBits(
        wifi_event_group,
        WIFI_CONNECTED_BIT,
        pdFALSE,
        pdTRUE,
        pdMS_TO_TICKS(15000));

    if ((bits & WIFI_CONNECTED_BIT) == 0) {
        printf("WiFi connect timeout, continuing without network\n");
    }
}

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

void mpu6050_init(void) {
    mpu6050_write_byte(MPU6050_PWR_MGMT_1, 0x00);
    vTaskDelay(pdMS_TO_TICKS(100));
}

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

void motor_init(void) {
    for (int i = 0; i < MOTOR_COUNT; i++) {
        gpio_reset_pin(MOTOR_DIR_PIN[i]);
        gpio_set_direction(MOTOR_DIR_PIN[i], GPIO_MODE_OUTPUT);
        gpio_set_pull_mode(MOTOR_DIR_PIN[i], GPIO_PULLDOWN_ONLY);
        gpio_set_level(MOTOR_DIR_PIN[i], 0);

        ledc_channel_config_t ch = {
            .gpio_num = MOTOR_PWM_PIN[i],
            .speed_mode = 0,
            .channel = (ledc_channel_t) i,
            .intr_type = LEDC_INTR_DISABLE, 
            .timer_sel = LEDC_TIMER, 
            .duty = 0,
            .hpoint = 0
        };
        ledc_channel_config(&ch);
    }

    ledc_timer_config_t timer = {
        .speed_mode = 0, 
        .duty_resolution = LEDC_TIMER_8_BIT, 
        .timer_num = LEDC_TIMER,
        .freq_hz = LEDC_FREQ,
        .clk_cfg = LEDC_AUTO_CLK
    };
    ledc_timer_config(&timer);
    
    printf("Motors initialized (4x BLDC with PWM + GPIO direction)\n");
}

void set_motor(int id, float value) {
    if (id < 0 || id >= MOTOR_COUNT) {
        printf("Invalid motor ID: %d\n", id);
    
            if (emergency_stop) {
                value = 0.0f;
            }
        return;
    }

    if (fabsf(value) < 0.05f) {
        value = 0.0f;
    }

    if (value > 1.0f) {
        value = 1.0f;
    }

    if (value < -1.0f) {
        value = -1.0f;
    }

    float max_change = 0.1f;
    
    if (fabsf(value - motor_targets[id]) > max_change) {
        if (value > motor_targets[id]) {
            value = motor_targets[id] + max_change;
        } else {
            value = motor_targets[id] - max_change;
        }
    }
    
    motor_targets[id] = value;

    int dir;

    if (value > 0) {
        dir = 1;
    } else {
        dir = 0;
    }

    int pwm = (int)(fabsf(value) * 255.0f);
    
    gpio_set_level(MOTOR_DIR_PIN[id], dir);
    ledc_set_duty(0, (ledc_channel_t) id, pwm);
    ledc_update_duty(0, (ledc_channel_t) id);
}

void motor_callback(const void *msgin) {
    const std_msgs__msg__Float32MultiArray *cmd = (const std_msgs__msg__Float32MultiArray*) msgin;
    
    last_motor_cmd_time = esp_timer_get_time() / 1000;
    
    for (int i = 0; i < MOTOR_COUNT && i < cmd -> data.size; i++) {
        set_motor(i, cmd -> data.data[i]);
    }
    
    printf("Motor command received\n");
}

void estop_callback(const void *msgin) {
    const std_msgs__msg__Bool *estop_cmd = (const std_msgs__msg__Bool*) msgin;
    
    if (estop_cmd->data) {
        emergency_stop = 1;
        printf("!!! EMERGENCY STOP ACTIVATED !!!\n");
        
        for (int i = 0; i < MOTOR_COUNT; i++) {
            motor_targets[i] = 0.0f;
            gpio_set_level(MOTOR_DIR_PIN[i], 0);
            ledc_set_duty(0, (ledc_channel_t) i, 0);
            ledc_update_duty(0, (ledc_channel_t) i);
        }
    } else {
        emergency_stop = 0;
        printf("Emergency stop cleared\n");
    }
}

void timer_callback(rcl_timer_t * timer, int64_t last_call_time) {
    RCLC_UNUSED(last_call_time);
    
    if (timer != NULL) {
        int64_t current_time = esp_timer_get_time() / 1000;
        if (last_motor_cmd_time > 0 && (current_time - last_motor_cmd_time) > MOTOR_TIMEOUT_MS) {
            printf("Motor timeout! Stopping motors (no command for %lld ms)\n", 
                   current_time - last_motor_cmd_time);
            for (int i = 0; i < MOTOR_COUNT; i++) {
                set_motor(i, 0.0f);
            }
        }

        int16_t accel[3], gyro[3];

        mpu6050_read_data(accel, gyro);

        imu_msg.linear_acceleration.x = (accel[0] / 16384.0f) * 9.81f;
        imu_msg.linear_acceleration.y = (accel[1] / 16384.0f) * 9.81f;
        imu_msg.linear_acceleration.z = (accel[2] / 16384.0f) * 9.81f;
        
        imu_msg.angular_velocity.x = (gyro[0] / 131.0f) * (M_PI / 180.0f);
        imu_msg.angular_velocity.y = (gyro[1] / 131.0f) * (M_PI / 180.0f);
        imu_msg.angular_velocity.z = (gyro[2] / 131.0f) * (M_PI / 180.0f);

        RCSOFTCHECK(rcl_publish(&imu_pub, &imu_msg, NULL));

        float distance = ultrasonic_read_distance();

        if (distance > 0) {
            range_msg.range = distance;
            RCSOFTCHECK(rcl_publish(&range_pub, &range_msg, NULL));
        }
        
        char status_buf[64];
        
        int status_len = snprintf(status_buf, sizeof(status_buf),
            "Accel:%.2f,%.2f,%.2f|Gyro:%.2f,%.2f,%.2f|Range:%.2f|MotorTimeout:%lld",
            imu_msg.linear_acceleration.x,
            imu_msg.linear_acceleration.y,
            imu_msg.linear_acceleration.z,
            imu_msg.angular_velocity.x,
            imu_msg.angular_velocity.y,
            imu_msg.angular_velocity.z,
            distance > 0 ? (long long)distance : -1LL);
        
        status_msg.data.data = (uint8_t*) status_buf;
        status_msg.data.size = status_len;
        status_msg.data.capacity = status_len + 1;
        
        RCSOFTCHECK(rcl_publish(&status_pub, &status_msg, NULL));
        
        printf("IMU - Accel: %.2f, %.2f, %.2f | Gyro: %.2f, %.2f, %.2f | Range: %.2f\n",
               imu_msg.linear_acceleration.x,
               imu_msg.linear_acceleration.y,
               imu_msg.linear_acceleration.z,
               imu_msg.angular_velocity.x,
               imu_msg.angular_velocity.y,
               imu_msg.angular_velocity.z,
               distance > 0 ? distance : -1.0f);
    }
}

void appMain(void *arg) {
    (void)arg;
    printf("appMain start\n");

    esp_task_wdt_init(30, true);
    esp_task_wdt_add(NULL);
    printf("Watchdog timer initialized (30s timeout)\n");

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    if (err != ESP_OK) {
        printf("NVS init failed: 0x%02x\n", err);
    }
    
    nvs_read_wifi_creds(stored_ssid, stored_pass);
    
    if (strlen(stored_ssid) == 0 || strlen(stored_pass) == 0) {
        printf("No WiFi credentials stored. Starting provisioning mode...\n");

        ESP_ERROR_CHECK(esp_netif_init());
        ESP_ERROR_CHECK(esp_event_loop_create_default());

        start_softap();
        start_provisioning_server();

        printf("Waiting for WiFi provisioning (60s timeout)...\n");
        for (int i = 0; i < 60; i++) {
            if (provisioning_server == NULL) {
                printf("Credentials provisioned successfully!\n");
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
        
        stop_provisioning_server();

        printf("Restarting device to apply WiFi configuration...\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
        esp_restart();
    }
    
    wifi_init();

    i2c_master_init();
    printf("I2C initialized, checking sensor presence...\n");

    uint8_t test_data = 0;
    esp_err_t ret = mpu6050_read_bytes(MPU6050_PWR_MGMT_1, &test_data, 1);
    if (ret != ESP_OK) {
        printf("ERROR: MPU6050 not detected on I2C bus (address 0x%02x)\n", MPU6050_ADDR);
        printf("Check hardware connections and I2C wiring\n");
    } else {
        printf("MPU6050 detected on I2C bus\n");
    }
    
    mpu6050_init();
    ultrasonic_init();
    motor_init();
    
    rcl_allocator_t allocator = rcl_get_default_allocator();
    rclc_support_t support;

    rcl_init_options_t init_options = rcl_get_zero_initialized_init_options();
    RCCHECK(rcl_init_options_init(&init_options, allocator));
    RCCHECK(rclc_support_init_with_options(&support, 0, NULL, &init_options, &allocator));

    rcl_node_t node;
    RCCHECK(rclc_node_init_default(&node, "sensor_node", "", &support));

    RCCHECK(rclc_publisher_init_default(
        &imu_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu),
        "imu/data"
    ));

    RCCHECK(rclc_publisher_init_default(
        &range_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Range),
        "range/data"
    ));

    RCCHECK(rclc_subscription_init_default(
        &motor_sub, 
        &node, 
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
        "motor-cmd"
    ));
    
    RCCHECK(rclc_publisher_init_default(
        &status_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
        "firmware/status"
    ));

    RCCHECK(rclc_subscription_init_default(
        &estop_sub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
        "e-stop"
    ));

    sensor_msgs__msg__Imu__init(&imu_msg);
    sensor_msgs__msg__Range__init(&range_msg);
    std_msgs__msg__Float32MultiArray__init(&motor_msg);
    std_msgs__msg__String__init(&status_msg);
 
    imu_msg.header.frame_id.data = "imu_link";
    imu_msg.header.frame_id.size = strlen("imu_link");
    imu_msg.header.frame_id.capacity = strlen("imu_link") + 1;
    
    range_msg.header.frame_id.data = "ultrasonic_link";
    range_msg.header.frame_id.size = strlen("ultrasonic_link");
    range_msg.header.frame_id.capacity = strlen("ultrasonic_link") + 1;
    
    range_msg.radiation_type = sensor_msgs__msg__Range__ULTRASOUND;
    range_msg.field_of_view = 0.26;
    range_msg.min_range = 0.02; 
    range_msg.max_range = 4.0; 

    std_msgs__msg__Bool__init(&estop_msg);
    rcl_timer_t timer;
    const unsigned int timer_timeout = 100;
    RCCHECK(rclc_timer_init_default(
        &timer,
        &support,
        RCL_MS_TO_NS(timer_timeout),
        timer_callback));

    rclc_executor_t executor;
    RCCHECK(rclc_executor_init(&executor, &support.context, 3, &allocator));
    RCCHECK(rclc_executor_add_timer(&executor, &timer));
    RCCHECK(rclc_executor_add_subscription(&executor, &estop_sub, &estop_msg, estop_callback, ON_NEW_DATA));
    RCCHECK(rclc_executor_add_subscription(&executor, &motor_sub, &motor_msg, motor_callback, ON_NEW_DATA));

    printf("Sensor node started!\n");

    while(1) {
        esp_task_wdt_reset();
        
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));
        usleep(10000);
    }

    RCCHECK(rcl_publisher_fini(&imu_pub, &node));
    RCCHECK(rcl_publisher_fini(&range_pub, &node));
    RCCHECK(rcl_node_fini(&node));

    vTaskDelete(NULL);
}
