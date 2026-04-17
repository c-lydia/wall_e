import math

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu
from sensor_msgs.msg import Range
from std_msgs.msg import Float32

class OdometryNode(Node):
	def __init__(self):
		super().__init__('odometry_node')

		self.declare_parameter('odom_topic', '/odom')
		self.declare_parameter('odom_frame_id', 'odom')
		self.declare_parameter('base_frame_id', 'base_link')
		self.declare_parameter('publish_rate_hz', 30.0)
		self.declare_parameter('use_cmd_vel_linear', True)
		self.declare_parameter('use_imu_yaw', True)
		self.declare_parameter('use_imu_yaw_rate', True)
		self.declare_parameter('use_fusion_height', True)
		self.declare_parameter('use_fusion_vertical_velocity', True)
		self.declare_parameter('use_range_safety_scale', True)
		self.declare_parameter('range_safety_min_m', 0.20)
		self.declare_parameter('range_safety_max_m', 0.60)

		self.odom_topic = str(self.get_parameter('odom_topic').value)
		self.odom_frame_id = str(self.get_parameter('odom_frame_id').value)
		self.base_frame_id = str(self.get_parameter('base_frame_id').value)
		self.publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
		self.use_cmd_vel_linear = bool(self.get_parameter('use_cmd_vel_linear').value)
		self.use_imu_yaw = bool(self.get_parameter('use_imu_yaw').value)
		self.use_imu_yaw_rate = bool(self.get_parameter('use_imu_yaw_rate').value)
		self.use_fusion_height = bool(self.get_parameter('use_fusion_height').value)
		self.use_fusion_vertical_velocity = bool(self.get_parameter('use_fusion_vertical_velocity').value)
		self.use_range_safety_scale = bool(self.get_parameter('use_range_safety_scale').value)
		self.range_safety_min_m = float(self.get_parameter('range_safety_min_m').value)
		self.range_safety_max_m = float(self.get_parameter('range_safety_max_m').value)

		self._x_m = 0.0
		self._y_m = 0.0
		self._yaw_rad = 0.0
		self._z_m = 0.0

		self._latest_cmd = Twist()
		self._latest_imu_yaw = None
		self._latest_imu_wz = None
		self._latest_range_m = None
		self._latest_fusion_height_m = None
		self._latest_fusion_vz = None

		self._last_time = self.get_clock().now()

		self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_callback, 20)
		self.imu_sub = self.create_subscription(Imu, '/imu/filter', self.imu_callback, 20)
		self.range_sub = self.create_subscription(Range, '/range/filter', self.range_callback, 20)
		self.fusion_height_sub = self.create_subscription(Float32, '/fusion/height', self.fusion_height_callback, 20)
		self.fusion_vz_sub = self.create_subscription(Float32, '/fusion/vertical_velocity', self.fusion_vz_callback, 20)
		self.odom_pub = self.create_publisher(Odometry, self.odom_topic, 20)

		period = 1.0 / self.publish_rate_hz if self.publish_rate_hz > 0.0 else (1.0 / 30.0)
		self.timer = self.create_timer(period, self.timer_callback)

		self.get_logger().info('Localization odometry node started')

	@staticmethod
	def _quat_to_yaw_rad(x: float, y: float, z: float, w: float) -> float:
		siny_cosp = 2.0 * (w * z + x * y)
		cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
		return math.atan2(siny_cosp, cosy_cosp)

	@staticmethod
	def _yaw_to_quat(yaw_rad: float):
		half = yaw_rad * 0.5
		return (0.0, 0.0, math.sin(half), math.cos(half))

	@staticmethod
	def _wrap_angle_rad(angle: float) -> float:
		return math.atan2(math.sin(angle), math.cos(angle))

	@staticmethod
	def _clamp(value: float, min_value: float, max_value: float) -> float:
		return max(min_value, min(max_value, value))

	def _range_speed_scale(self) -> float:
		if not self.use_range_safety_scale or self._latest_range_m is None:
			return 1.0
		if not math.isfinite(self._latest_range_m):
			return 1.0

		if self._latest_range_m <= self.range_safety_min_m:
			return 0.0
		if self._latest_range_m >= self.range_safety_max_m:
			return 1.0

		span = self.range_safety_max_m - self.range_safety_min_m
		if span <= 1e-6:
			return 1.0
		return (self._latest_range_m - self.range_safety_min_m) / span

	def cmd_callback(self, msg: Twist):
		self._latest_cmd = msg

	def imu_callback(self, msg: Imu):
		q = msg.orientation
		self._latest_imu_yaw = self._quat_to_yaw_rad(q.x, q.y, q.z, q.w)
		self._latest_imu_wz = float(msg.angular_velocity.z)

	def range_callback(self, msg: Range):
		if math.isfinite(msg.range):
			self._latest_range_m = float(msg.range)

	def fusion_height_callback(self, msg: Float32):
		if math.isfinite(msg.data):
			self._latest_fusion_height_m = float(msg.data)

	def fusion_vz_callback(self, msg: Float32):
		if math.isfinite(msg.data):
			self._latest_fusion_vz = float(msg.data)

	def timer_callback(self):
		now = self.get_clock().now()
		dt = (now - self._last_time).nanoseconds * 1e-9
		self._last_time = now

		if dt <= 0.0:
			return

		vx = float(self._latest_cmd.linear.x) if self.use_cmd_vel_linear else 0.0
		wz_cmd = float(self._latest_cmd.angular.z)

		if self.use_imu_yaw and self._latest_imu_yaw is not None:
			self._yaw_rad = self._latest_imu_yaw
		else:
			wz_for_integrate = wz_cmd
			if self.use_imu_yaw_rate and self._latest_imu_wz is not None:
				wz_for_integrate = self._latest_imu_wz
			self._yaw_rad = self._wrap_angle_rad(self._yaw_rad + wz_for_integrate * dt)

		speed_scale = self._range_speed_scale()
		vx_eff = vx * speed_scale

		self._x_m += vx_eff * math.cos(self._yaw_rad) * dt
		self._y_m += vx_eff * math.sin(self._yaw_rad) * dt

		if self.use_fusion_height and self._latest_fusion_height_m is not None:
			self._z_m = self._latest_fusion_height_m

		qx, qy, qz, qw = self._yaw_to_quat(self._yaw_rad)

		odom = Odometry()
		odom.header.stamp = now.to_msg()
		odom.header.frame_id = self.odom_frame_id
		odom.child_frame_id = self.base_frame_id

		odom.pose.pose.position.x = self._x_m
		odom.pose.pose.position.y = self._y_m
		odom.pose.pose.position.z = self._z_m

		odom.pose.pose.orientation.x = qx
		odom.pose.pose.orientation.y = qy
		odom.pose.pose.orientation.z = qz
		odom.pose.pose.orientation.w = qw

		odom.twist.twist.linear.x = vx_eff
		odom.twist.twist.linear.z = self._latest_fusion_vz if (
			self.use_fusion_vertical_velocity and self._latest_fusion_vz is not None
		) else 0.0
		odom.twist.twist.angular.z = self._latest_imu_wz if (
			self.use_imu_yaw_rate and self._latest_imu_wz is not None
		) else wz_cmd

		# Conservative covariance because this is mixed sensor dead reckoning.
		odom.pose.covariance[0] = 0.25
		odom.pose.covariance[7] = 0.25
		odom.pose.covariance[14] = 0.30
		odom.pose.covariance[35] = 0.40
		odom.twist.covariance[0] = 0.30
		odom.twist.covariance[14] = 0.40
		odom.twist.covariance[35] = 0.35

		self.odom_pub.publish(odom)


def main(args=None):
	rclpy.init(args=args)
	node = OdometryNode()

	try:
		rclpy.spin(node)
	finally:
		node.destroy_node()
		if rclpy.ok():
			rclpy.shutdown()


if __name__ == '__main__':
	main()
