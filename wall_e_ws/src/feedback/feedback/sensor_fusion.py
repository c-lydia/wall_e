import math

import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from sensor_msgs.msg import Imu
from sensor_msgs.msg import Range
from std_msgs.msg import Float32
from std_msgs.msg import Float32MultiArray

class SensorFusion(Node):
	def __init__(self):
		super().__init__('sensor_fusion_node')

		self.declare_parameter('gravity_m_s2', 9.81)
		self.declare_parameter('accel_bias_m_s2', 0.0)
		self.declare_parameter('range_correction_gain', 0.08)
		self.declare_parameter('velocity_damping', 0.02)
		self.declare_parameter('max_dt_s', 0.2)
		self.declare_parameter('publish_diagnostics', True)

		self.gravity_m_s2 = float(self.get_parameter('gravity_m_s2').value)
		self.accel_bias_m_s2 = float(self.get_parameter('accel_bias_m_s2').value)
		self.range_correction_gain = float(self.get_parameter('range_correction_gain').value)
		self.velocity_damping = float(self.get_parameter('velocity_damping').value)
		self.max_dt_s = float(self.get_parameter('max_dt_s').value)
		self.publish_diagnostics = bool(self.get_parameter('publish_diagnostics').value)

		self.add_on_set_parameters_callback(self._on_parameter_update)

		self.imu_sub = self.create_subscription(Imu, '/imu/filter', self.imu_callback, 20)
		self.range_sub = self.create_subscription(Range, '/range/filter', self.range_callback, 20)

		self.height_pub = self.create_publisher(Float32, '/fusion/height', 20)
		self.velocity_pub = self.create_publisher(Float32, '/fusion/vertical_velocity', 20)
		self.diag_pub = self.create_publisher(Float32MultiArray, '/fusion/debug', 20)

		self._height_m = 0.0
		self._velocity_m_s = 0.0
		self._last_time_s = None
		self._latest_range_m = None
		self._initialized_from_range = False

	def _on_parameter_update(self, params):
		next_gravity = self.gravity_m_s2
		next_bias = self.accel_bias_m_s2
		next_gain = self.range_correction_gain
		next_damping = self.velocity_damping
		next_max_dt = self.max_dt_s
		next_publish_diag = self.publish_diagnostics

		for param in params:
			if param.name == 'gravity_m_s2':
				next_gravity = float(param.value)
			elif param.name == 'accel_bias_m_s2':
				next_bias = float(param.value)
			elif param.name == 'range_correction_gain':
				next_gain = float(param.value)
			elif param.name == 'velocity_damping':
				next_damping = float(param.value)
			elif param.name == 'max_dt_s':
				next_max_dt = float(param.value)
			elif param.name == 'publish_diagnostics':
				next_publish_diag = bool(param.value)

		if next_gravity <= 0.0:
			return SetParametersResult(successful = False, reason = 'gravity_m_s2 must be > 0')

		if next_gain < 0.0 or next_gain > 1.0:
			return SetParametersResult(successful = False, reason = 'range_correction_gain must be in [0, 1]')

		if next_damping < 0.0 or next_damping > 1.0: 
			return SetParametersResult(successful = False, reason = 'velocity_damping must be in [0, 1]')

		if next_max_dt <= 0.0:
			return SetParametersResult(successful = False, reason = 'max_dt_s must be > 0')

		self.gravity_m_s2 = next_gravity
		self.accel_bias_m_s2 = next_bias
		self.range_correction_gain = next_gain
		self.velocity_damping = next_damping
		self.max_dt_s = next_max_dt
		self.publish_diagnostics = next_publish_diag
		return SetParametersResult(successful = True)

	@staticmethod
	def _stamp_to_seconds(sec: int, nanosec: int) -> float:
		return float(sec) + float(nanosec) * 1e-9

	def range_callback(self, msg: Range):
		if not math.isfinite(msg.range):
			return
		self._latest_range_m = msg.range
		if not self._initialized_from_range:
			self._height_m = msg.range
			self._velocity_m_s = 0.0
			self._initialized_from_range = True

	def _compute_dt(self, msg: Imu) -> float:
		now_s = self._stamp_to_seconds(msg.header.stamp.sec, msg.header.stamp.nanosec)
  
		if self._last_time_s is None:
			self._last_time_s = now_s
			return 0.0

		dt = now_s - self._last_time_s
		self._last_time_s = now_s

		if dt <= 0.0:
			return 0.0
		if dt > self.max_dt_s:
			return self.max_dt_s
		return dt

	def _predict_with_imu(self, imu_msg: Imu, dt: float):
		# Assumes sensor Z axis is aligned with vertical. For tilted mounting,
		# rotate accel into world frame before using this term.
		az_m_s2 = imu_msg.linear_acceleration.z
		az_linear = az_m_s2 - self.gravity_m_s2 - self.accel_bias_m_s2

		self._velocity_m_s = self._velocity_m_s + az_linear * dt
		self._velocity_m_s = self._velocity_m_s * (1.0 - self.velocity_damping)
		self._height_m = self._height_m + self._velocity_m_s * dt
		return az_linear

	def _correct_with_range(self):
		if self._latest_range_m is None:
			return 0.0

		innovation = self._latest_range_m - self._height_m
		correction = self.range_correction_gain * innovation
		self._height_m = self._height_m + correction
		return innovation

	def _publish_outputs(self, az_linear: float, innovation: float):
		height_msg = Float32()
		height_msg.data = float(self._height_m)
		self.height_pub.publish(height_msg)

		velocity_msg = Float32()
		velocity_msg.data = float(self._velocity_m_s)
		self.velocity_pub.publish(velocity_msg)

		if self.publish_diagnostics:
			diag = Float32MultiArray()
			range_value = float('nan')
   
			if self._latest_range_m is not None:
				range_value = float(self._latest_range_m)
    
			diag.data = [
				float(self._height_m),
				float(self._velocity_m_s),
				float(az_linear),
				range_value,
				float(innovation),
			]
   
			self.diag_pub.publish(diag)

	def imu_callback(self, msg: Imu):
		dt = self._compute_dt(msg)
  
		if dt <= 0.0:
			return

		if not self._initialized_from_range:
			if self._latest_range_m is not None:
				self._height_m = self._latest_range_m
				self._velocity_m_s = 0.0
				self._initialized_from_range = True
			else:
				return

		az_linear = self._predict_with_imu(msg, dt)
		innovation = self._correct_with_range()
		self._publish_outputs(az_linear, innovation)

def main():
	rclpy.init()
	sensor_fusion = SensorFusion()
 
	try:
		rclpy.spin(sensor_fusion)
	finally:
		sensor_fusion.destroy_node()
		rclpy.shutdown()


if __name__ == '__main__':
	main()
