import os
import xacro
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():

    pkg_share = get_package_share_directory("wall_e_description")

    urdf_file   = os.path.join(pkg_share, "description", "robot.urdf.xacro")
    world_file  = os.path.join(pkg_share, "worlds", "indoor_room.world")
    rviz_config = os.path.join(pkg_share, "rviz",   "robot.rviz")

    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    use_rviz     = LaunchConfiguration("use_rviz",     default="true")
    use_gazebo = LaunchConfiguration("use_gazebo", default="true")
    use_gazebo_gui = LaunchConfiguration("use_gazebo_gui", default="false")
    use_joint_state_publisher = LaunchConfiguration("use_joint_state_publisher", default="false")
    use_control = LaunchConfiguration("use_control", default="true")
    use_feedback = LaunchConfiguration("use_feedback", default="true")
    use_localization = LaunchConfiguration("use_localization", default="true")

    robot_description = xacro.process_file(urdf_file).toxml()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {"robot_description": robot_description},
            {"use_sim_time": use_sim_time},
        ],
    )

    joint_state_publisher = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        name="joint_state_publisher",
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(use_joint_state_publisher),
    )

    rear_left_wheel_static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="rear_left_wheel_static_tf",
        arguments=[
            str(-0.07),
            str(0.085),
            str(-0.01),
            str(0.70710678),
            "0.0",
            "0.0",
            str(0.70710678),
            "base_link",
            "rear_left_wheel",
        ],
        condition=UnlessCondition(use_joint_state_publisher),
        output="screen",
    )

    rear_right_wheel_static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="rear_right_wheel_static_tf",
        arguments=[
            str(-0.07),
            str(-0.085),
            str(-0.01),
            str(0.70710678),
            "0.0",
            "0.0",
            str(0.70710678),
            "base_link",
            "rear_right_wheel",
        ],
        condition=UnlessCondition(use_joint_state_publisher),
        output="screen",
    )

    # Gazebo integration is optional and may be unavailable in minimal ROS images.
    try:
        gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory("gazebo_ros"),
                    "launch",
                    "gazebo.launch.py",
                )
            ),
            launch_arguments={
                "world": world_file,
                "gui": use_gazebo_gui,
                "verbose": "false",
            }.items(),
            condition=IfCondition(use_gazebo),
        )

        spawn_robot = Node(
            package="gazebo_ros",
            executable="spawn_entity.py",
            arguments=[
                "-topic", "robot_description",
                "-entity", "esp32_robot",
                "-x", "0.0",
                "-y", "0.0",
                "-z", "0.05",
            ],
            output="screen",
            condition=IfCondition(use_gazebo),
        )
    except PackageNotFoundError:
        gazebo = LogInfo(
            msg="gazebo_ros not found; launching without Gazebo. Install ros-humble-gazebo-ros-pkgs to enable simulation."
        )
        spawn_robot = LogInfo(msg="Skipping robot spawn because gazebo_ros is not installed.")

    # RViz
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config],
        # VS Code Snap can inject GTK/XDG vars that make rviz2 load incompatible snap libs.
        prefix=[
            "env -u GTK_EXE_PREFIX -u GTK_PATH -u LOCPATH -u XDG_DATA_DIRS "
            "-u XDG_DATA_HOME -u GIO_MODULE_DIR -u GTK_IM_MODULE_FILE "
            "-u GSETTINGS_SCHEMA_DIR"
        ],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(use_rviz),
        output="screen",
    )

    # Control package nodes
    gamepad_node = Node(
        package="control",
        executable="gamepad_node",
        name="gamepad_node",
        output="screen",
        condition=IfCondition(use_control),
    )

    robot_control_node = Node(
        package="control",
        executable="robot_control_node",
        name="robot_control_node",
        output="screen",
        condition=IfCondition(use_control),
    )

    # Feedback package nodes
    imu_filter_node = Node(
        package="feedback",
        executable="imu_filter_node",
        name="imu_filter_node",
        output="screen",
        condition=IfCondition(use_feedback),
    )

    range_filter_node = Node(
        package="feedback",
        executable="range_filter_node",
        name="range_filter_node",
        output="screen",
        condition=IfCondition(use_feedback),
    )

    sensor_fusion_node = Node(
        package="feedback",
        executable="sensor_fusion_node",
        name="sensor_fusion_node",
        output="screen",
        condition=IfCondition(use_feedback),
    )

    # Localization package nodes
    inverse_kinematic_node = Node(
        package="localization",
        executable="inverse_kinematic_node",
        name="inverse_kinematic_node",
        output="screen",
        condition=IfCondition(use_localization),
    )

    odometry_node = Node(
        package="localization",
        executable="odometry_node",
        name="odometry_node",
        output="screen",
        condition=IfCondition(use_localization),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use simulation clock",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Launch RViz",
            ),
            DeclareLaunchArgument(
                "use_gazebo",
                default_value="true",
                description="Launch Gazebo and spawn robot",
            ),
            DeclareLaunchArgument(
                "use_gazebo_gui",
                default_value="false",
                description="Launch Gazebo client GUI",
            ),
            DeclareLaunchArgument(
                "use_joint_state_publisher",
                default_value="false",
                description="Launch joint_state_publisher",
            ),
            DeclareLaunchArgument(
                "use_control",
                default_value="true",
                description="Launch control package nodes",
            ),
            DeclareLaunchArgument(
                "use_feedback",
                default_value="true",
                description="Launch feedback package nodes",
            ),
            DeclareLaunchArgument(
                "use_localization",
                default_value="true",
                description="Launch localization package nodes",
            ),
            robot_state_publisher,
            joint_state_publisher,
            rear_left_wheel_static_tf,
            rear_right_wheel_static_tf,
            gazebo,
            spawn_robot,
            rviz,
            gamepad_node,
            robot_control_node,
            imu_filter_node,
            range_filter_node,
            sensor_fusion_node,
            inverse_kinematic_node,
            odometry_node,
        ]
    )