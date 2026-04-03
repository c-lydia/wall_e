========
Wall-E
========

**A Professional micro-ROS Workspace for ESP32 Robotics Development**

Welcome to Wall-E's comprehensive documentation. This project provides an integrated development environment combining ESP32 firmware, FreeRTOS, and ROS 2 Humble for advanced embedded robotics applications.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   getting_started
   firmware/esp32_controller
   architecture
   troubleshooting

Project Overview
================

Wall-E is a complete, production-ready workspace for developing intelligent embedded robot systems. It seamlessly integrates:

- **Modern Robotics**: Full ROS 2 Humble support on host systems
- **Embedded Systems**: FreeRTOS-based ESP32 controller firmware
- **Containerization**: Docker Compose for reproducible development environments
- **Professional Documentation**: Comprehensive guides covering all aspects of the system
- **Development Tools**: VS Code integration with IntelliSense and debugging


Core Capabilities
=================

Real-time Sensor Integration
------------------------------
- **IMU Sensor** (MPU6050): 6-axis inertial measurement via I2C
- **Range Sensor** (HC-SR04): Ultrasonic distance measurement with GPIO control
- **Configurable Publishing**: ROS 2 topics with sensor_msgs interface

Distributed Architecture
-------------------------
- **Host System**: ROS 2 development environment in Docker
- **Embedded Node**: FreeRTOS-based ESP32 running micro-ROS client
- **Network Communication**: Reliable UDP messaging through micro-ROS agent
- **Extensible Design**: Easy to add new sensors and publishers

Development Infrastructure
---------------------------
- **Docker Compose**: Multi-service orchestration (workspace + agent)
- **Build Tools**: colcon for packages, ESP-IDF for firmware
- **Source Control**: Git-based version management
- **Documentation**: Sphinx with professional PDF generation


Key Features & Benefits
=======================

✓ **Production Ready**: Complete Docker setup with tested configurations
✓ **Well Documented**: Comprehensive guides for setup, development, and troubleshooting
✓ **Extensible Architecture**: Modular design for adding custom sensors and behaviors
✓ **Professional Workflow**: Docker containers for reproducible development across machines
✓ **ROS 2 Integration**: Full compatibility with ROS 2 Humble ecosystem
✓ **Embedded Security**: FreeRTOS best practices with micro-ROS security features


Quick Start
===========

To get started with Wall-E:

1. Clone the repository and navigate to the workspace
2. Start the Docker containers: ``docker compose up --build``
3. Build packages in the workspace container: ``colcon build``
4. Build and flash the ESP32 firmware
5. Monitor the micro-ROS agent and ESP32 communication

For detailed instructions, see the **Getting Started** guide.


System Architecture
===================

Wall-E's architecture consists of:

- **Host System**: ROS 2 Humble development environment with visualization tools
- **Middleware**: micro-ROS agent for reliable UDP communication
- **Embedded Controller**: FreeRTOS-based ESP32 with sensor interface
- **Documentation**: Complete guides and API references

For a detailed technical overview, see the **Architecture** documentation.


Technical Stack
===============

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :align: center

   * - Component
     - Technology
   * - Host Robotics Framework
     - ROS 2 Humble (Ubuntu 20.04)
   * - Embedded OS
     - FreeRTOS + micro-ROS
   * - Microcontroller
     - ESP32 (Espressif Systems)
   * - Communication
     - UDP via micro-ROS agent
   * - Build System
     - colcon, ESP-IDF v5.0+
   * - Documentation
     - Sphinx with RTD theme
   * - Containerization
     - Docker & Docker Compose
   * - Version Control
     - Git


Support & Documentation
=======================

This documentation provides:

- :ref:`Getting Started Guide <getting_started>` - Setup and initial configuration
- :ref:`ESP32 Controller Documentation <firmware/esp32_controller>` - Hardware and firmware details
- :ref:`System Architecture <architecture>` - Design overview and data flow
- :ref:`Troubleshooting Guide <troubleshooting>` - Solutions to common issues

For additional information, see the project's GitHub repository.

