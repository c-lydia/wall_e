====================
WiFi Provisioning
====================

Quick Start
===========

1. Power on ESP32 with no stored WiFi credentials
2. Device starts SoftAP called ``ESP32-Setup`` (open network)
3. Connect your laptop/phone to ``ESP32-Setup`` WiFi
4. Open browser to ``http://192.168.4.1/``
5. Enter your WiFi SSID and password
6. Device saves credentials and restarts
7. Next boot: automatically connects to your configured WiFi

System Overview
===============

The provisioning system eliminates the need for:

- Hardcoded WiFi credentials in source code
- Manual menuconfig every build
- Terminal-based setup procedures
- Editing code for different WiFi networks

Instead, users provision via a simple web form on first boot.

How It Works
============

Boot Detection
--------------

.. code-block:: text

   PowerOn
     ↓
   NVS Init (read from flash)
     ↓
   Check SSID/Password in NVS
     ├─ EMPTY? → Start SoftAP + HTTP server
     └─ FOUND? → Connect to WiFi (normal operation)

The system checks if WiFi credentials exist in the NVS flash partition before attempting to connect. If empty, provisioning mode is activated.

SoftAP (Access Point Mode)
--------------------------

When credentials are missing, the device becomes a WiFi access point:

- **SSID**: ``ESP32-Setup``
- **Security**: Open (no password required)
- **IP Range**: ``192.168.4.0/24``
- **Gateway**: ``192.168.4.1`` (device IP)

Clients automatically receive an IP via DHCP.

HTTP Provisioning Server
------------------------

A lightweight HTTP server hosts a provisioning form:

**GET /** Returns HTML form with two inputs:
- WiFi SSID (text field, max 32 chars)
- WiFi Password (password field, max 63 chars)

**POST /provision** Accepts form submission with:
- ``ssid`` parameter: Network name
- ``password`` parameter: Network password

Server validates input and saves to NVS if successful.

NVS Storage
-----------

Credentials are stored persistently in the NVS (Non-Volatile Storage) partition:

- **Namespace**: ``"wifi_creds"``
- **SSID Key**: ``"ssid"``
- **Password Key**: ``"password"``
- **Persistence**: Survives power cycles, resets, and reboots

Once stored, credentials are automatically loaded on boot and used for normal WiFi station mode.

Fallback to Kconfig
-------------------

If NVS is empty or doesn't exist, the system falls back to compile-time defaults:

.. code-block:: c

   #ifdef CONFIG_ESP_WIFI_SSID
   #define WIFI_SSID CONFIG_ESP_WIFI_SSID
   #else
   #define WIFI_SSID ""
   #endif

This allows a default configuration while maintaining the provisioning system.

For End Users
=============

**First Time Setup**

1. Plug in device (ESP32 board)
2. Wait 10 seconds for boot to complete
3. On your phone/laptop, look for WiFi network ``ESP32-Setup``
4. Connect to it (no password needed)
5. Open web browser and navigate to ``http://192.168.4.1/``
6. Fill in your home WiFi name and password
7. Click "Connect"
8. Device will restart and connect to your WiFi
9. Done! Device is now ready to use

**Resetting Credentials**

To erase stored credentials and start provisioning again:

.. code-block:: bash

   # From host with device plugged in:
   cd /micro_ros_ws/firmware/freertos_apps/microros_esp32_extensions
   source /micro_ros_ws/firmware/toolchain/esp-idf/export.sh
   idf.py erase-flash      # Erases entire flash, including NVS
   idf.py flash            # Re-flashes firmware
   # Device boots with empty credentials → starts provisioning mode again

**Changing WiFi Networks**

Method 1 (Easiest): Erase and reflash (see above)

Method 2 (Advanced): Manually erase NVS partition only:

.. code-block:: bash

   idf.py erase-flash NVS  # Erases just the NVS partition
   # Device boots with empty credentials → starts provisioning mode again

For Developers
==============

Integration Points
------------------

The provisioning system is implemented in ``appMain()`` with these key functions:

**nvs_read_wifi_creds()**
   Reads stored SSID and password from NVS

**nvs_write_wifi_creds()**
   Writes SSID and password to NVS

**start_softap()**
   Initializes WiFi in AP mode with SSID ``ESP32-Setup``

**start_provisioning_server()**
   Launches HTTP server with GET and POST handlers

**stop_provisioning_server()**
   Cleanly shuts down HTTP server after provisioning

HTTP Handlers
~~~~~~~~~~~~~

**get_handler()**
   Serves HTML form for SSID/password input

**post_handler()**
   Parses form data, validates, writes to NVS, restarts device

Customization
~~~~~~~~~~~~~

Default SoftAP SSID (in ``start_softap()``):

.. code-block:: c

   .ssid = "ESP32-Setup",

Change this to customize the network name visible to users.

HTML form styling and layout (in ``get_handler()``):

.. code-block:: c

   const char* html_form = "<!DOCTYPE html>...";

Modify this string to customize the provisioning UI.

Post-provisioning timeout (in ``appMain()``):

.. code-block:: c

   for (int i = 0; i < 60; i++) {  // 60 seconds
       if (provisioning_server == NULL) break;
       vTaskDelay(pdMS_TO_TICKS(1000));
   }

Increase the loop count to allow more time for user input.

Testing Provisioning Manually
------------------------------

Simulate the provisioning flow without hardware:

1. Erase credentials to start provisioning mode
2. Monitor serial output to see SoftAP startup
3. Connect to ``ESP32-Setup`` with a mobile device
4. Open HTTP form in browser
5. Supply test credentials and verify POST data in logs
6. Confirm NVS write via ``nvs_read_wifi_creds()`` on next boot

Security Considerations
=======================

**Open Access Point**
   The SoftAP has no password to simplify first-time setup for non-technical users. Deploy this only in trusted networks (e.g., lab, personal use).

**Plaintext Credentials Over HTTP**
   Provisioning form is transmitted over plain HTTP (no HTTPS/TLS). For sensitive deployments, consider adding:
   - Basic authentication on GET /
   - HTTPS with self-signed certificate
   - Time-limited provisioning window (already implemented: 60s timeout)

**NVS Storage**
   Credentials are stored in flash without encryption. Access is controlled by file permissions on the NVS partition. For high-security applications:
   - Use ESP32 secure boot and flash encryption
   - Store encrypted credentials in partition

**Network Isolation**
   The SoftAP runs in open mode. Isolate the provisioning phase:
   - Keep provisioning timeout short (60 seconds default)
   - Disable SoftAP after credentials are saved
   - Use firewalls to restrict device access post-provisioning

Common Issues
=============

**No SoftAP visible on first boot**
   - Device only starts SoftAP if credentials are empty or missing
   - Check NVS earlier boot has stored credentials
   - Verify WiFi radio is functional

**Can't reach http://192.168.4.1/**
   - Ensure you're connected to the correct network: ``ESP32-Setup``
   - Try http://192.168.4.1:80/ explicitly
   - Check device IP: some phones assign different IPs (check Settings)

**Credentials saved but device won't connect**
   - Verify WiFi is 2.4 GHz (not 5 GHz)
   - Confirm no extra spaces in SSID or password
   - Check network uses WPA2, not legacy WEP or open

**Form submission hangs or times out**
   - Check device logs for POST handler errors
   - Ensure NVS partition has space (not full)
   - Try clearing all NVS and rebooting

API Reference
=============

.. code-block:: c

   // Read credentials from NVS
   esp_err_t nvs_read_wifi_creds(char *ssid_out, char *pass_out);
   // Parameters:
   //   ssid_out: pointer to buffer (64 bytes), receives stored SSID
   //   pass_out: pointer to buffer (64 bytes), receives stored password
   // Returns: ESP_OK on success, error code otherwise

.. code-block:: c

   // Write credentials to NVS
   esp_err_t nvs_write_wifi_creds(const char *ssid, const char *password);
   // Parameters:
   //   ssid: SSID to store (max 32 chars)
   //   password: password to store (max 63 chars)
   // Returns: ESP_OK on success, error code otherwise

.. code-block:: c

   // Start SoftAP for provisioning
   void start_softap(void);
   // Initializes WiFi in AP mode, starts SSID "ESP32-Setup"
   // Must be called before start_provisioning_server()

.. code-block:: c

   // Start HTTP provisioning server
   void start_provisioning_server(void);
   // Registers GET / and POST /provision handlers
   // Requires SoftAP to be running

.. code-block:: c

   // Stop HTTP provisioning server
   void stop_provisioning_server(void);
   // Cleanly shuts down httpd and frees resources
