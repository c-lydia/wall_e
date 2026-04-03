# Wall-E

A micro-ROS workspace for ESP32 development with ROS 2 Humble integration, featuring:

- **ESP32 Firmware:** FreeRTOS-based micro-ROS nodes
- **Host Agent:** micro-ROS agent running in Docker for ESP32 communication
- **ROS 2 Humble:** Native ROS 2 packages and visualization tools
- **Documentation:** Sphinx-based project documentation
- **Docker Compose:** Multi-container setup for reproducible builds

## Quick Start

### Prerequisites

- Docker and Docker Compose
- ESP-IDF v5.0+ (for ESP32 firmware)
- ROS 2 Humble (optional, for native host development)

### Build and Run

```bash
# Start all services (workspace + micro-ROS agent)
docker compose up

# In another terminal, build and flash ESP32
cd firmware/dev_ws
idf.py build flash monitor
```

The workspace container will:

1. Build your ROS 2 packages via colcon
2. Mount volumes for `src/`, `build/`, `install/`, and `docs/`
3. Provide an interactive bash shell for development

The micro-ROS agent listens on UDP port **9999** for ESP32 connections.

## Project Structure

```bash
micro_ros_ws/
├── src/                  # ROS 2 packages (colcon workspace)
├── firmware/
│   ├── custom/          # Custom ESP32 firmware applications
│   │   └── esp32_controller/    # Main sensor node (IMU + ultrasonic)
│   ├── dev_ws/          # ESP-IDF development workspace
│   └── mcu_ws/          # MCU-specific micro-ROS packages
├── docs/                # Sphinx documentation
├── Dockerfile           # Container image for ROS 2 workspace
├── docker-compose.yaml  # Multi-container orchestration
└── .gitignore          # Git ignore rules
```

## Documentation

Build and serve documentation inside the container:

```bash
cd /micro_ros_ws/docs
sphinx-build -b html source _build/html
```

## Services

| Service | Image | Purpose | Port |
|---------|-------|---------|------|
| **workspace** | Local build | Builds ROS 2 packages | - |
| **micro_ros_agent** | microros/micro-ros-agent:humble | ESP32 communication bridge | 9999 (UDP) |

## Development Workflow

1. **Add ROS 2 packages** to `src/` directory
2. **Workspace container builds automatically** via colcon
3. **Edit documentation** in `docs/source/` (mounted volume)
4. **ESP32 firmware** in `firmware/dev_ws/` uses ESP-IDF build system
5. **Host processes** on port 9999 are mapped to micro-ROS agent

## Notes

- **Port 9999:** micro-ROS agent UDP port (change in docker-compose.yaml if needed)
- **venv + Docker:** Use venv locally for Python tools, Docker for ROS 2 builds
- **Documentation tools:** Sphinx, myst-parser, RTD theme pre-installed

For more details, see:

- Restructured Text Documentation: [Documentation](docs/source/index.rst)
- HTML Documentation: [HTML Documentation](docs/build/index.html)
- PDF Documentation: [PDF Documentation](docs/build-pdf/wall-e.pdf)
