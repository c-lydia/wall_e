import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

TRACK_WIDTH = 1.0

class InverseKinematic(Node):
    def __init__(self):
        super().__init__('inverse_kinematic_node')
        self.declare_parameter('track_width', TRACK_WIDTH)
        self.declare_parameter('max_speed', 1.0)
        self.declare_parameter('wheel_order', ['front_left', 'front_right', 'rear_left', 'rear_right'])

        self.track_width = float(self.get_parameter('track_width').value)
        self.max_speed = float(self.get_parameter('max_speed').value)
        self.wheel_order = list(self.get_parameter('wheel_order').value)
        self.wheel_vel = [0.0, 0.0]
        
        self.cmd_vel_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.inverse_kinematic_pub = self.create_publisher(Float32MultiArray, '/motor_cmd', 10)
        
        self.timer = self.create_timer(0.01, self.timer_callback)
        
    def cmd_vel_callback(self, msg: Twist):
        linear_vel_x = msg.linear.x
        angular_vel_z = msg.angular.z 
        
        self.wheel_vel = self.inverse_kinematic(linear_vel_x, angular_vel_z)
        
    def inverse_kinematic(self, vx, wz):
        left_speed = vx - (wz * self.track_width) / 2.0
        right_speed = vx + (wz * self.track_width) / 2.0

        left_speed = max(-self.max_speed, min(self.max_speed, left_speed))
        right_speed = max(-self.max_speed, min(self.max_speed, right_speed))

        return [left_speed, right_speed]
    
    def timer_callback(self):
        left_speed, right_speed = self.wheel_vel

        side_map = {
            'left': left_speed,
            'right': right_speed,
        }

        motor_data = []
        
        for wheel_name in self.wheel_order:
            wheel_label = str(wheel_name).lower()
            
            if 'left' in wheel_label:
                motor_data.append(side_map['left'])
            elif 'right' in wheel_label:
                motor_data.append(side_map['right'])
            else:
                motor_data.append(0.0)

        motor_cmd = Float32MultiArray()
        motor_cmd.data = motor_data

        self.inverse_kinematic_pub.publish(motor_cmd)

        self.get_logger().debug(
            f'Publishing motor command: left={left_speed:.3f}, right={right_speed:.3f}, data={motor_cmd.data}'
        )

def main(args=None):
    rclpy.init(args=args)
    node = InverseKinematic()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()