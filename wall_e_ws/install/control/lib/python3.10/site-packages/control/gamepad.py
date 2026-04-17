from typing import Optional
import os
import fcntl
import rclpy
from rclpy.node import Node
from custom_interfaces.msg import Gamepad as gamepad_msg
from evdev import InputDevice, ecodes, list_devices, AbsInfo

class Gamepad(Node):
    def __init__(self) -> None:
        super().__init__("gamepad_node")

        self.declare_parameter("output_topic", "/gamepad")
        self.declare_parameter("device_name", "")
        self.declare_parameter("normalize_triggers", True)
        self.declare_parameter("poll_rate", 50.0)  # Hz

        self.normalize_triggers = bool(self.get_parameter("normalize_triggers").value)
        self.poll_rate = float(self.get_parameter("poll_rate").value)

        self._publisher = self.create_publisher(
            gamepad_msg,
            self.get_parameter("output_topic").value,
            10
        )

        requested_name = str(self.get_parameter("device_name").value).strip()
        self.device: Optional[InputDevice] = self._find_gamepad(requested_name or None)

        if not self.device:
            self.get_logger().error("No usable gamepad found. Make sure it is plugged in and /dev/input is mapped.")
            return

        self._set_device_nonblocking()

        self.get_logger().info(f"Using gamepad device: {self.device.path}")

        # Dictionary to track axes/buttons state
        self.axes = {}
        self.buttons = {}

        # Timer to poll events
        self.create_timer(1.0 / self.poll_rate, self._publish_state)

    def _set_device_nonblocking(self) -> None:
        """Configure device reads as non-blocking across evdev versions."""
        try:
            if hasattr(self.device, "set_nonblocking"):
                self.device.set_nonblocking(True)
                return

            flags = fcntl.fcntl(self.device.fd, fcntl.F_GETFL)
            fcntl.fcntl(self.device.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        except Exception as e:
            self.get_logger().warning(f"Could not set non-blocking mode explicitly: {e}")

    def _find_gamepad(self, name: Optional[str] = None) -> Optional[InputDevice]:
        """Auto-detect a usable input device, optionally by exact name."""
        available_paths = list_devices()
        self.get_logger().info(f"Detected {len(available_paths)} input device(s) under /dev/input")

        for dev_path in available_paths:
            try:
                dev = InputDevice(dev_path)
            except Exception:
                continue

            self.get_logger().info(f"Input device found: {dev.name} ({dev.path})")

            if name and dev.name == name:
                self.get_logger().info(f"Matched requested device_name: {dev.name} ({dev.path})")
                return dev

            capabilities = dev.capabilities(verbose=False)
            abs_caps = capabilities.get(ecodes.EV_ABS, [])
            key_caps = capabilities.get(ecodes.EV_KEY, [])

            abs_codes = {
                item[0] if isinstance(item, tuple) else item
                for item in abs_caps
            }
            key_codes = {
                item[0] if isinstance(item, tuple) else item
                for item in key_caps
            }

            has_axes = ecodes.ABS_X in abs_codes and ecodes.ABS_Y in abs_codes
            has_primary_button = ecodes.BTN_SOUTH in key_codes

            self.get_logger().info(
                f"Capabilities for {dev.name}: has_axes={has_axes}, has_primary_button={has_primary_button}"
            )

            if has_axes and has_primary_button:
                self.get_logger().info(f"Auto-detected gamepad candidate: {dev.name} ({dev.path})")
                return dev

        return None

    def _read_events(self):
        try:
            while True:
                event = self.device.read_one()
                if event is None:
                    break

                if event.type == ecodes.EV_ABS:
                    self.axes[event.code] = event.value
                elif event.type == ecodes.EV_KEY:
                    self.buttons[event.code] = event.value
        except Exception as e:
            self.get_logger().error(f"Error reading gamepad: {e}")

    def _normalize_trigger(self, value: int, absinfo: Optional[AbsInfo] = None) -> float:
        """Normalize trigger to 0..1 range"""
        if absinfo:
            min_val = absinfo.min
            max_val = absinfo.max
        else:
            min_val, max_val = 0, 255
        norm = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, norm)) if self.normalize_triggers else float(value)

    def _publish_state(self):
        """Publish current state as Gamepad message"""
        self._read_events()

        msg = gamepad_msg()

        # Map common Xbox layout
        msg.left_stick_x = self.axes.get(ecodes.ABS_X, 0) / 32768.0
        msg.left_stick_y = self.axes.get(ecodes.ABS_Y, 0) / 32768.0
        msg.right_stick_x = self.axes.get(ecodes.ABS_RX, 0) / 32768.0
        msg.right_stick_y = self.axes.get(ecodes.ABS_RY, 0) / 32768.0

        msg.left_trigger = self._normalize_trigger(self.axes.get(ecodes.ABS_Z, 0))
        msg.right_trigger = self._normalize_trigger(self.axes.get(ecodes.ABS_RZ, 0))

        msg.dpad_x = self.axes.get(ecodes.ABS_HAT0X, 0)
        msg.dpad_y = self.axes.get(ecodes.ABS_HAT0Y, 0)

        # Buttons mapping
        msg.a = bool(self.buttons.get(ecodes.BTN_SOUTH, 0))
        msg.b = bool(self.buttons.get(ecodes.BTN_EAST, 0))
        msg.x = bool(self.buttons.get(ecodes.BTN_NORTH, 0))
        msg.y = bool(self.buttons.get(ecodes.BTN_WEST, 0))
        msg.lb = bool(self.buttons.get(ecodes.BTN_TL, 0))
        msg.rb = bool(self.buttons.get(ecodes.BTN_TR, 0))
        msg.back = bool(self.buttons.get(ecodes.BTN_SELECT, 0))
        msg.start = bool(self.buttons.get(ecodes.BTN_START, 0))
        msg.home = bool(self.buttons.get(ecodes.BTN_MODE, 0))
        msg.left_stick_press = bool(self.buttons.get(ecodes.BTN_THUMBL, 0))
        msg.right_stick_press = bool(self.buttons.get(ecodes.BTN_THUMBR, 0))

        self._publisher.publish(msg)
        self.get_logger().info(f"Publishing Gamepad state: {msg}")

def main(args=None):
    rclpy.init(args=args)
    node = Gamepad()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()