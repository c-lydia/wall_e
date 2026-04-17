FROM ros:humble-ros-base

# Install essential build tools
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libevdev-dev \
    python3-evdev \
    git \
    build-essential \
    cmake \
    ros-humble-xacro \
    ros-humble-joint-state-publisher \
    ros-humble-rviz2 \
    ros-humble-gazebo-ros-pkgs \
    && rm -rf /var/lib/apt/lists/*

# Install colcon and ROS development tools
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y python3 python3-pip && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 10

# Install documentation tools
RUN python3 -m pip install --no-cache-dir sphinx sphinx_rtd_theme myst-parser

# Create workspace
WORKDIR /micro_ros_ws

# Initialize rosdep if packages exist
RUN rosdep update || true

# Copy entrypoint
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
