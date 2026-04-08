from typing import List

import rclpy
from custom_interfaces.msg import Gamepad
from rclpy.node import Node
from sensor_msgs.msg import Joy

class GamepadNode(Node):
	def __init__(self) -> None:
		super().__init__("gamepad_node")

		self.declare_parameter("input_topic", "/joy")
		self.declare_parameter("output_topic", "/gamepad")
		self.declare_parameter("normalize_triggers", True)

		# Default mapping for common Xbox controller layouts on Linux.
		self.declare_parameter("axis_left_stick_x", 0)
		self.declare_parameter("axis_left_stick_y", 1)
		self.declare_parameter("axis_left_trigger", 2)
		self.declare_parameter("axis_right_stick_x", 3)
		self.declare_parameter("axis_right_stick_y", 4)
		self.declare_parameter("axis_right_trigger", 5)
		self.declare_parameter("axis_dpad_x", 6)
		self.declare_parameter("axis_dpad_y", 7)

		self.declare_parameter("button_a", 0)
		self.declare_parameter("button_b", 1)
		self.declare_parameter("button_x", 2)
		self.declare_parameter("button_y", 3)
		self.declare_parameter("button_lb", 4)
		self.declare_parameter("button_rb", 5)
		self.declare_parameter("button_back", 6)
		self.declare_parameter("button_start", 7)
		self.declare_parameter("button_home", 8)
		self.declare_parameter("button_left_stick_press", 9)
		self.declare_parameter("button_right_stick_press", 10)

		self._publisher = self.create_publisher(
			Gamepad,
			self.get_parameter("output_topic").value,
			10,
		)
		self._subscription = self.create_subscription(
			Joy,
			self.get_parameter("input_topic").value,
			self._joy_callback,
			10,
		)
		self.get_logger().info("gamepad_node started")

	def _axis(self, axes: List[float], param_name: str) -> float:
		index = int(self.get_parameter(param_name).value)
		if 0 <= index < len(axes):
			return float(axes[index])
		return 0.0

	def _button(self, buttons: List[int], param_name: str) -> bool:
		index = int(self.get_parameter(param_name).value)
		if 0 <= index < len(buttons):
			return bool(buttons[index])
		return False

	def _trigger_value(self, raw_value: float) -> float:
		normalize = bool(self.get_parameter("normalize_triggers").value)
		if normalize:
			return max(0.0, min(1.0, (raw_value + 1.0) / 2.0))
		return raw_value

	def _joy_callback(self, msg: Joy) -> None:
		out = Gamepad()
		out.header = msg.header

		out.left_stick_x = self._axis(msg.axes, "axis_left_stick_x")
		out.left_stick_y = self._axis(msg.axes, "axis_left_stick_y")
		out.right_stick_x = self._axis(msg.axes, "axis_right_stick_x")
		out.right_stick_y = self._axis(msg.axes, "axis_right_stick_y")

		out.left_trigger = self._trigger_value(
			self._axis(msg.axes, "axis_left_trigger")
		)
		out.right_trigger = self._trigger_value(
			self._axis(msg.axes, "axis_right_trigger")
		)

		out.dpad_x = int(self._axis(msg.axes, "axis_dpad_x"))
		out.dpad_y = int(self._axis(msg.axes, "axis_dpad_y"))

		out.a = self._button(msg.buttons, "button_a")
		out.b = self._button(msg.buttons, "button_b")
		out.x = self._button(msg.buttons, "button_x")
		out.y = self._button(msg.buttons, "button_y")

		out.lb = self._button(msg.buttons, "button_lb")
		out.rb = self._button(msg.buttons, "button_rb")
		out.back = self._button(msg.buttons, "button_back")
		out.start = self._button(msg.buttons, "button_start")
		out.home = self._button(msg.buttons, "button_home")

		out.left_stick_press = self._button(msg.buttons, "button_left_stick_press")
		out.right_stick_press = self._button(msg.buttons, "button_right_stick_press")

		self._publisher.publish(out)

def main(args=None) -> None:
	rclpy.init(args=args)
	node = GamepadNode()
	try:
		rclpy.spin(node)
	finally:
		node.destroy_node()
		rclpy.shutdown()


if __name__ == "__main__":
	main()
