import math

import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from sensor_msgs.msg import Range
from std_msgs.msg import Float32MultiArray

class RangeFilter(Node):
    def __init__(self):
        super().__init__('range_filter_node')

        self.declare_parameter('alpha', 0.35)
        self.declare_parameter('window_size', 3)
        self.declare_parameter('max_jump_m', 0.25)
        self.declare_parameter('publish_diagnostics', True)

        self.alpha = float(self.get_parameter('alpha').value)
        self.window_size = int(self.get_parameter('window_size').value)
        self.max_jump_m = float(self.get_parameter('max_jump_m').value)
        self.publish_diagnostics = bool(self.get_parameter('publish_diagnostics').value)

        if self.window_size < 1:
            self.window_size = 1
        if self.window_size % 2 == 0:
            self.window_size += 1

        self.range_sub = self.create_subscription(Range, '/range/data', self.range_callback, 10)
        self.range_filter_pub = self.create_publisher(Range, '/range/filter', 10)
        self.diag_pub = self.create_publisher(Float32MultiArray, '/range/filter/debug', 10)

        self.add_on_set_parameters_callback(self._on_parameter_update)

        self._buf = []
        self._filtered = None

    def _on_parameter_update(self, params):
        next_alpha = self.alpha
        next_window_size = self.window_size
        next_max_jump = self.max_jump_m
        next_publish_diag = self.publish_diagnostics

        for param in params:
            if param.name == 'alpha':
                next_alpha = float(param.value)
            elif param.name == 'window_size':
                next_window_size = int(param.value)
            elif param.name == 'max_jump_m':
                next_max_jump = float(param.value)
            elif param.name == 'publish_diagnostics':
                next_publish_diag = bool(param.value)

        if not (0.0 < next_alpha <= 1.0):
            return SetParametersResult(successful = False, reason = 'alpha must be in (0, 1]')
        
        if next_window_size < 1:
            return SetParametersResult(successful = False, reason = 'window_size must be >= 1')
        
        if next_max_jump <= 0.0:
            return SetParametersResult(successful = False, reason = 'max_jump_m must be > 0')

        self.alpha = next_alpha
        
        if next_window_size % 2 == 1:
            self.window_size = next_window_size
        else:
            self.window_size = next_window_size + 1
            
        self.max_jump_m = next_max_jump
        self.publish_diagnostics = next_publish_diag
        return SetParametersResult(successful = True)

    @staticmethod
    def _build_output(msg: Range) -> Range:
        range_filter_msg = Range()
        range_filter_msg.header
        range_filter_msg.radiation_type = msg.radiation_type
        range_filter_msg.field_of_view = msg.field_of_view
        range_filter_msg.min_range = msg.min_range
        range_filter_msg.max_range = msg.max_range
        return range_filter_msg

    @staticmethod
    def _is_valid_raw(raw: float, msg: Range) -> bool:
        if not math.isfinite(raw):
            return False
        if raw < msg.min_range:
            return False
        if raw > msg.max_range:
            return False
        return True

    def _reset_state(self):
        self._buf.clear()
        self._filtered = None

    def _append_raw(self, raw: float):
        self._buf.append(raw)
        
        if len(self._buf) > self.window_size:
            self._buf.pop(0)

    def _median_window(self) -> float:
        values = sorted(self._buf)
        mid = len(values) // 2
        
        if len(values) % 2 == 1:
            return values[mid]

        left = values[mid - 1]
        right = values[mid]
        return 0.5 * (left + right)

    def _passes_jump_gate(self, candidate: float) -> bool:
        if self._filtered is None:
            return True
        
        return abs(candidate - self._filtered) <= self.max_jump_m

    def _apply_ema(self, sample: float) -> float:
        if self._filtered is None:
            self._filtered = sample
        else:
            self._filtered = self.alpha * sample + (1.0 - self.alpha) * self._filtered
        return self._filtered

    def _publish_diag(self, raw: float, med: float, filt: float, accepted: bool):
        if not self.publish_diagnostics:
            return
        
        diag_msg = Float32MultiArray()
        accepted_flag = 0.0
        
        if accepted:
            accepted_flag = 1.0
            
        diag_msg.data = [float(raw), float(med), float(filt), accepted_flag]
        self.diag_pub.publish(diag_msg)

    def range_callback(self, msg: Range):
        range_filter_msg = self._build_output(msg)
        raw = msg.range

        if not self._is_valid_raw(raw, msg):
            self._reset_state()
            range_filter_msg.range = float("inf")
            self._publish_diag(raw, float("nan"), float("nan"), False)
            self.range_filter_pub.publish(range_filter_msg)
            return

        self._append_raw(raw)
        med = self._median_window()

        accepted = self._passes_jump_gate(med)
        
        if accepted:
            range_filter_msg.range = self._apply_ema(med)
        else:
            if self._filtered is not None:
                range_filter_msg.range = self._filtered
            else:
                range_filter_msg.range = med

        self._publish_diag(raw, med, range_filter_msg.range, accepted)
        self.range_filter_pub.publish(range_filter_msg)

def main():
    rclpy.init()
    range_filter = RangeFilter()
    
    try:
        rclpy.spin(range_filter)
    finally:
        range_filter.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
