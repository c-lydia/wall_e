import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from sensor_msgs.msg import Range
from std_msgs.msg import Float32
from custom_interfaces.msg import Gamepad

class RobotControl(Node):
    def __init__(self):
        super().__init__('robot_control_node')
        self._declare_parameters()
        self._load_parameters()
        self._setup_ros_io()
        self._init_runtime_state()

        timer_period = 1.0 / self.publish_rate_hz if self.publish_rate_hz > 0.0 else 0.05
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info('Robot control node started')

    def _declare_parameters(self):
        self.declare_parameter('max_linear_speed', 0.6)
        self.declare_parameter('max_angular_speed', 1.5)
        self.declare_parameter('deadband', 0.08)
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('range_stop_enabled', True)
        self.declare_parameter('min_clearance_m', 0.25)
        self.declare_parameter('enable_button', 'lb')
        self.declare_parameter('pi_mode_button', 'a')
        self.declare_parameter('range_pos_kp', 1.2)
        self.declare_parameter('range_pos_kd', 0.0)
        self.declare_parameter('yaw_pos_kp', 2.0)
        self.declare_parameter('yaw_pos_kd', 0.0)
        self.declare_parameter('linear_speed_kp', 1.0)
        self.declare_parameter('linear_speed_ki', 0.2)
        self.declare_parameter('angular_speed_kp', 1.0)
        self.declare_parameter('angular_speed_ki', 0.2)
        self.declare_parameter('max_linear_setpoint_rate', 1.2)
        self.declare_parameter('max_angular_setpoint_rate', 2.5)
        self.declare_parameter('integral_limit_linear', 0.8)
        self.declare_parameter('integral_limit_angular', 1.0)
        self.declare_parameter('use_odom_yaw', True)
        self.declare_parameter('servo_enabled', True)
        self.declare_parameter('servo_min_angle_deg', 0.0)
        self.declare_parameter('servo_max_angle_deg', 180.0)
        self.declare_parameter('servo_default_angle_deg', 90.0)
        self.declare_parameter('servo_axis', 'right_stick_y')
        self.declare_parameter('servo_axis_invert', True)
        self.declare_parameter('servo_only_when_enabled', True)

    def _load_parameters(self):
        self.max_linear_speed = float(self.get_parameter('max_linear_speed').value)
        self.max_angular_speed = float(self.get_parameter('max_angular_speed').value)
        self.deadband = float(self.get_parameter('deadband').value)
        self.publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        self.range_stop_enabled = bool(self.get_parameter('range_stop_enabled').value)
        self.min_clearance_m = float(self.get_parameter('min_clearance_m').value)
        self.enable_button = str(self.get_parameter('enable_button').value).strip()
        self.pi_mode_button = str(self.get_parameter('pi_mode_button').value).strip()
        self.range_pos_kp = float(self.get_parameter('range_pos_kp').value)
        self.range_pos_kd = float(self.get_parameter('range_pos_kd').value)
        self.yaw_pos_kp = float(self.get_parameter('yaw_pos_kp').value)
        self.yaw_pos_kd = float(self.get_parameter('yaw_pos_kd').value)
        self.linear_speed_kp = float(self.get_parameter('linear_speed_kp').value)
        self.linear_speed_ki = float(self.get_parameter('linear_speed_ki').value)
        self.angular_speed_kp = float(self.get_parameter('angular_speed_kp').value)
        self.angular_speed_ki = float(self.get_parameter('angular_speed_ki').value)
        self.max_linear_setpoint_rate = float(self.get_parameter('max_linear_setpoint_rate').value)
        self.max_angular_setpoint_rate = float(self.get_parameter('max_angular_setpoint_rate').value)
        self.integral_limit_linear = float(self.get_parameter('integral_limit_linear').value)
        self.integral_limit_angular = float(self.get_parameter('integral_limit_angular').value)
        self.use_odom_yaw = bool(self.get_parameter('use_odom_yaw').value)
        self.servo_enabled = bool(self.get_parameter('servo_enabled').value)
        self.servo_min_angle_deg = float(self.get_parameter('servo_min_angle_deg').value)
        self.servo_max_angle_deg = float(self.get_parameter('servo_max_angle_deg').value)
        self.servo_default_angle_deg = float(self.get_parameter('servo_default_angle_deg').value)
        self.servo_axis = str(self.get_parameter('servo_axis').value).strip()
        self.servo_axis_invert = bool(self.get_parameter('servo_axis_invert').value)
        self.servo_only_when_enabled = bool(self.get_parameter('servo_only_when_enabled').value)

        if self.servo_max_angle_deg < self.servo_min_angle_deg:
            self.servo_min_angle_deg, self.servo_max_angle_deg = self.servo_max_angle_deg, self.servo_min_angle_deg
        self.servo_default_angle_deg = self._clamp(
            self.servo_default_angle_deg,
            self.servo_min_angle_deg,
            self.servo_max_angle_deg,
        )

    def _setup_ros_io(self):
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.servo_pub = self.create_publisher(Float32, '/servo_cmd', 10)
        self.gamepad_sub = self.create_subscription(Gamepad, '/gamepad', self.gamepad_callback, 10)
        self.range_sub = self.create_subscription(Range, '/range/filter', self.range_callback, 10)
        self.imu_sub = self.create_subscription(Imu, '/imu/filter', self.imu_callback, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)

    def _init_runtime_state(self):
        self._latest_gamepad = None
        self._latest_range_m = None
        self._latest_yaw_rad = None
        self._latest_odom_yaw_rad = None
        self._latest_odom_vx = 0.0
        self._latest_odom_wz = 0.0
        self._latest_imu_wz = 0.0
        self._last_cmd = Twist()
        self._target_range_m = None
        self._target_yaw_rad = None
        self._linear_speed_integral = 0.0
        self._angular_speed_integral = 0.0
        self._range_error_prev = 0.0
        self._yaw_error_prev = 0.0
        self._linear_speed_setpoint = 0.0
        self._angular_speed_setpoint = 0.0
        self._pi_mode_active = False
        self._prev_pi_button = False
        self._last_timer_time = self.get_clock().now()
        self._last_servo_cmd_deg = self.servo_default_angle_deg

    @staticmethod
    def _apply_deadband(value: float, deadband: float) -> float:
        if abs(value) < deadband:
            return 0.0
        return value

    def _is_enable_pressed(self, msg: Gamepad) -> bool:
        return self._is_button_pressed(msg, self.enable_button)

    def _read_axis_value(self, msg: Gamepad, axis_name: str) -> float:
        if axis_name == 'left_stick_x':
            return float(msg.left_stick_x)
        if axis_name == 'left_stick_y':
            return float(msg.left_stick_y)
        if axis_name == 'right_stick_x':
            return float(msg.right_stick_x)
        if axis_name == 'right_stick_y':
            return float(msg.right_stick_y)
        return 0.0

    def _axis_to_servo_deg(self, axis_value: float) -> float:
        normalized = self._clamp(axis_value, -1.0, 1.0)
        if self.servo_axis_invert:
            normalized = -normalized
        span = self.servo_max_angle_deg - self.servo_min_angle_deg
        return self.servo_min_angle_deg + (normalized + 1.0) * 0.5 * span

    def _publish_servo_angle(self, angle_deg: float):
        msg = Float32()
        msg.data = float(self._clamp(angle_deg, self.servo_min_angle_deg, self.servo_max_angle_deg))
        self.servo_pub.publish(msg)
        self._last_servo_cmd_deg = msg.data

    def _update_servo_cmd(self, msg: Gamepad, control_enabled: bool):
        if not self.servo_enabled:
            return

        target_deg = self.servo_default_angle_deg
        if not self.servo_only_when_enabled or control_enabled:
            axis_value = self._read_axis_value(msg, self.servo_axis)
            target_deg = self._axis_to_servo_deg(axis_value)

        self._publish_servo_angle(target_deg)

    @staticmethod
    def _wrap_angle_rad(angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))

    @staticmethod
    def _quat_to_yaw_rad(x: float, y: float, z: float, w: float) -> float:
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        return math.atan2(siny_cosp, cosy_cosp)

    @staticmethod
    def _clamp(value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    def _is_button_pressed(self, msg: Gamepad, button_name: str) -> bool:
        if button_name == 'a':
            return bool(msg.a)
        if button_name == 'b':
            return bool(msg.b)
        if button_name == 'x':
            return bool(msg.x)
        if button_name == 'y':
            return bool(msg.y)
        if button_name == 'lb':
            return bool(msg.lb)
        if button_name == 'rb':
            return bool(msg.rb)
        if button_name == 'back':
            return bool(msg.back)
        if button_name == 'start':
            return bool(msg.start)
        if button_name == 'home':
            return bool(msg.home)
        if button_name == 'left_stick_press':
            return bool(msg.left_stick_press)
        if button_name == 'right_stick_press':
            return bool(msg.right_stick_press)
        return False

    def _reset_pi_state(self):
        self._reset_hold_controller_state()
        self._target_range_m = None
        self._target_yaw_rad = None
        self._pi_mode_active = False

    def _reset_hold_controller_state(self):
        self._linear_speed_integral = 0.0
        self._angular_speed_integral = 0.0
        self._range_error_prev = 0.0
        self._yaw_error_prev = 0.0
        self._linear_speed_setpoint = 0.0
        self._angular_speed_setpoint = 0.0

    def _get_heading_yaw(self):
        if self.use_odom_yaw and self._latest_odom_yaw_rad is not None:
            return self._latest_odom_yaw_rad
        return self._latest_yaw_rad

    def _should_hold_mode_button(self, msg: Gamepad) -> bool:
        return self._is_button_pressed(msg, self.pi_mode_button)

    def _prime_hold_targets(self):
        current_yaw = self._get_heading_yaw()
        if self._latest_range_m is None or current_yaw is None:
            return

        self._target_range_m = self._latest_range_m
        self._target_yaw_rad = current_yaw
        self._reset_hold_controller_state()
        self._pi_mode_active = True
        self.get_logger().info(
            f'PI mode engaged: target_range={self._target_range_m:.3f} m, target_yaw={self._target_yaw_rad:.3f} rad'
        )

    def _update_hold_mode_state(self, msg: Gamepad):
        hold_button_pressed = self._should_hold_mode_button(msg)
        pressed_on_this_cycle = hold_button_pressed and not self._prev_pi_button
        self._prev_pi_button = hold_button_pressed

        if not hold_button_pressed:
            if self._pi_mode_active:
                self._reset_pi_state()
            return

        if pressed_on_this_cycle:
            self._prime_hold_targets()

    def _compute_outer_speed_setpoints(self, dt: float):
        range_error = self._target_range_m - self._latest_range_m
        yaw_error = self._wrap_angle_rad(self._target_yaw_rad - self._get_heading_yaw())

        range_error_dot = (range_error - self._range_error_prev) / dt if dt > 1e-6 else 0.0
        yaw_error_dot = (yaw_error - self._yaw_error_prev) / dt if dt > 1e-6 else 0.0
        self._range_error_prev = range_error
        self._yaw_error_prev = yaw_error

        desired_linear_sp = self.range_pos_kp * range_error + self.range_pos_kd * range_error_dot
        desired_angular_sp = self.yaw_pos_kp * yaw_error + self.yaw_pos_kd * yaw_error_dot
        desired_linear_sp = self._clamp(desired_linear_sp, -self.max_linear_speed, self.max_linear_speed)
        desired_angular_sp = self._clamp(desired_angular_sp, -self.max_angular_speed, self.max_angular_speed)
        return desired_linear_sp, desired_angular_sp

    def _rate_limit_speed_setpoints(self, desired_linear_sp: float, desired_angular_sp: float, dt: float):
        max_dv = self.max_linear_setpoint_rate * dt
        max_dw = self.max_angular_setpoint_rate * dt
        self._linear_speed_setpoint += self._clamp(desired_linear_sp - self._linear_speed_setpoint, -max_dv, max_dv)
        self._angular_speed_setpoint += self._clamp(desired_angular_sp - self._angular_speed_setpoint, -max_dw, max_dw)

    def _compute_manual_cmd(self, msg: Gamepad) -> Twist:
        linear_input = self._apply_deadband(-float(msg.left_stick_y), self.deadband)
        angular_input = self._apply_deadband(float(msg.left_stick_x), self.deadband)

        cmd = Twist()
        cmd.linear.x = self._clamp(linear_input, -1.0, 1.0) * self.max_linear_speed
        cmd.angular.z = self._clamp(angular_input, -1.0, 1.0) * self.max_angular_speed
        return cmd

    def _get_control_dt(self) -> float:
        dt = (self.get_clock().now() - self._last_timer_time).nanoseconds * 1e-9
        return self._clamp(dt, 0.0, 0.2)

    def _build_cmd_from_mode(self, msg: Gamepad, dt: float) -> Twist:
        if self._pi_mode_active:
            return self._compute_hold_mode_cmd(dt)
        return self._compute_manual_cmd(msg)

    def _apply_range_stop_guard(self, cmd: Twist):
        if self._range_allows_motion():
            return
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.get_logger().warn(
            f'Range stop active: latest_range={self._latest_range_m:.3f} m < min_clearance_m={self.min_clearance_m:.3f} m'
        )

    def _on_control_disabled(self):
        self._reset_pi_state()
        self._last_cmd = Twist()

    def _compute_inner_speed_pi(self, dt: float):
        vx_meas = self._latest_odom_vx
        wz_meas = self._latest_odom_wz if self.use_odom_yaw else self._latest_imu_wz
        linear_speed_error = self._linear_speed_setpoint - vx_meas
        angular_speed_error = self._angular_speed_setpoint - wz_meas

        self._linear_speed_integral += linear_speed_error * dt
        self._angular_speed_integral += angular_speed_error * dt

        self._linear_speed_integral = self._clamp(
            self._linear_speed_integral,
            -self.integral_limit_linear,
            self.integral_limit_linear,
        )
        self._angular_speed_integral = self._clamp(
            self._angular_speed_integral,
            -self.integral_limit_angular,
            self.integral_limit_angular,
        )

        linear_cmd = (
            self.linear_speed_kp * linear_speed_error +
            self.linear_speed_ki * self._linear_speed_integral
        )
        angular_cmd = (
            self.angular_speed_kp * angular_speed_error +
            self.angular_speed_ki * self._angular_speed_integral
        )
        return linear_cmd, angular_cmd

    def _compute_hold_mode_cmd(self, dt: float) -> Twist:
        cmd = Twist()
        if not self._pi_mode_active:
            return cmd
        if self._target_range_m is None or self._target_yaw_rad is None:
            return cmd
        if self._latest_range_m is None or self._get_heading_yaw() is None:
            return cmd

        desired_linear_sp, desired_angular_sp = self._compute_outer_speed_setpoints(dt)
        self._rate_limit_speed_setpoints(desired_linear_sp, desired_angular_sp, dt)
        linear_cmd, angular_cmd = self._compute_inner_speed_pi(dt)

        cmd.linear.x = self._clamp(linear_cmd, -self.max_linear_speed, self.max_linear_speed)
        cmd.angular.z = self._clamp(angular_cmd, -self.max_angular_speed, self.max_angular_speed)
        return cmd

    def _range_allows_motion(self) -> bool:
        if not self.range_stop_enabled:
            return True
        if self._latest_range_m is None:
            return True
        if not math.isfinite(self._latest_range_m):
            return True
        return self._latest_range_m >= self.min_clearance_m

    def gamepad_callback(self, msg: Gamepad):
        self._latest_gamepad = msg
        self._update_hold_mode_state(msg)

        control_enabled = self._is_enable_pressed(msg)
        self._update_servo_cmd(msg, control_enabled)

        if not control_enabled:
            self._on_control_disabled()
            return

        dt = self._get_control_dt()
        cmd = self._build_cmd_from_mode(msg, dt)
        self._apply_range_stop_guard(cmd)

        self._last_cmd = cmd

    def range_callback(self, msg: Range):
        if math.isfinite(msg.range):
            self._latest_range_m = float(msg.range)

    def imu_callback(self, msg: Imu):
        q = msg.orientation
        self._latest_yaw_rad = self._quat_to_yaw_rad(q.x, q.y, q.z, q.w)
        self._latest_imu_wz = float(msg.angular_velocity.z)

    def odom_callback(self, msg: Odometry):
        q = msg.pose.pose.orientation
        self._latest_odom_yaw_rad = self._quat_to_yaw_rad(q.x, q.y, q.z, q.w)
        self._latest_odom_vx = float(msg.twist.twist.linear.x)
        self._latest_odom_wz = float(msg.twist.twist.angular.z)

    def timer_callback(self):
        self._last_timer_time = self.get_clock().now()
        self.cmd_vel_pub.publish(self._last_cmd)
        self.get_logger().debug(f'Publishing: {self._last_cmd}')

def main(args=None):
    rclpy.init(args=args)
    node = RobotControl()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
