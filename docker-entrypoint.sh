#!/bin/bash
set -e

# Source the ROS setup
source /opt/ros/humble/setup.bash

# Install dependencies if src directory exists and has content
if [ -d /micro_ros_ws/src ] && [ "$(ls -A /micro_ros_ws/src)" ]; then
    echo "Installing dependencies..."
    rosdep install --from-paths /micro_ros_ws/src --ignore-src -y || true
fi

# Execute the command passed to the container
exec "$@"
