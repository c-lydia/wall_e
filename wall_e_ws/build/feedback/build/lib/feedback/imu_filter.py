import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

KP_DEFAULT = 2.0
KI_DEFAULT = 0.05
CALIB_SAMPLES_DEFAULT = 200

class ImuFilter(Node):
    def __init__(self):
        super().__init__('imu_filter_node')

        self.imu_sub = self.create_subscription(Imu, '/imu/data', self.imu_callback, 10)
        self.imu_filter_pub = self.create_publisher(Imu, '/imu/filter', 10)

        self.declare_parameter('kp', KP_DEFAULT)
        self.declare_parameter('ki', KI_DEFAULT)
        
        self.declare_parameter('calibration_samples', CALIB_SAMPLES_DEFAULT)
        
        self.kp = float(self.get_parameter('kp').value)
        self.ki = float(self.get_parameter('ki').value)
        
        self.calibration_samples = int(self.get_parameter('calibration_samples').value)

        self._qx = 0.0
        self._qy = 0.0
        self._qz = 0.0
        self._qw = 1.0

        self._ex_int = 0.0
        self._ey_int = 0.0
        self._ez_int = 0.0

        self._bias_samples = 0
        self._bgx = 0.0
        self._bgy = 0.0
        self._bgz = 0.0

        self._prev_stamp = None

    @staticmethod
    def _stamp_to_seconds(msg: Imu) -> float:
        return float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9

    def _normalize_quaternion(self):
        norm = math.sqrt(self._qw * self._qw + self._qx * self._qx + self._qy * self._qy + self._qz * self._qz)
        
        if norm < 1e-9:
            self._qw = 1.0
            self._qx = 0.0
            self._qy = 0.0
            self._qz = 0.0
            return
        
        inv = 1.0 / norm
        self._qw *= inv
        self._qx *= inv
        self._qy *= inv
        self._qz *= inv

    def _compute_dt(self, msg: Imu) -> float:
        stamp_s = self._stamp_to_seconds(msg)
        
        if self._prev_stamp is None:
            dt = 0.01
        else:
            dt = stamp_s - self._prev_stamp
            
            if dt <= 0.0 or dt > 0.2:
                dt = 0.01
                
        self._prev_stamp = stamp_s
        return dt

    @staticmethod
    def _normalize_accel(ax: float, ay: float, az: float):
        accel_norm = math.sqrt(ax * ax + ay * ay + az * az)
        
        if accel_norm < 1e-6:
            return None

        norm_ax = ax / accel_norm
        norm_ay = ay / accel_norm
        norm_az = az / accel_norm
        return (norm_ax, norm_ay, norm_az)

    def _publish_passthrough(self, msg: Imu):
        out = Imu()
        out.header = msg.header
        
        out.orientation.x = self._qx
        out.orientation.y = self._qy
        out.orientation.z = self._qz
        out.orientation.w = self._qw
        out.orientation_covariance = msg.orientation_covariance
        
        out.angular_velocity = msg.angular_velocity
        out.angular_velocity_covariance = msg.angular_velocity_covariance
        
        out.linear_acceleration = msg.linear_acceleration
        out.linear_acceleration_covariance = msg.linear_acceleration_covariance
        
        self.imu_filter_pub.publish(out)

    def _calibrate_gyro_bias(self, gx: float, gy: float, gz: float):
        if self._bias_samples < self.calibration_samples:
            self._bgx += gx
            self._bgy += gy
            self._bgz += gz
            self._bias_samples += 1
            return False

        if self._bias_samples == self.calibration_samples:
            self._bgx /= float(self.calibration_samples)
            self._bgy /= float(self.calibration_samples)
            self._bgz /= float(self.calibration_samples)
            self._bias_samples += 1
            self.get_logger().info(
                f'Gyro bias calibrated: bx = {self._bgx:.4f}, by = {self._bgy:.4f}, bz = {self._bgz:.4f} rad/s'
            )
        return True

    def _estimate_gravity(self):
        vx = 2.0 * (self._qx * self._qz - self._qw * self._qy)
        vy = 2.0 * (self._qw * self._qx + self._qy * self._qz)
        vz = self._qw * self._qw - self._qx * self._qx - self._qy * self._qy + self._qz * self._qz
        return vx, vy, vz

    def _apply_correction(self, gx: float, gy: float, gz: float, ax: float, ay: float, az: float, dt: float):
        vx, vy, vz = self._estimate_gravity()

        ex = ay * vz - az * vy
        ey = az * vx - ax * vz
        ez = ax * vy - ay * vx

        if self.ki > 0.0:
            self._ex_int += ex * dt
            self._ey_int += ey * dt
            self._ez_int += ez * dt
        else:
            self._ex_int = 0.0
            self._ey_int = 0.0
            self._ez_int = 0.0

        gx += self.kp * ex + self.ki * self._ex_int
        gy += self.kp * ey + self.ki * self._ey_int
        gz += self.kp * ez + self.ki * self._ez_int
        return gx, gy, gz

    def _integrate_quaternion(self, gx: float, gy: float, gz: float, dt: float):
        half_dt = 0.5 * dt
        qw = self._qw
        qx = self._qx
        qy = self._qy
        qz = self._qz

        self._qw += (-qx * gx - qy * gy - qz * gz) * half_dt
        self._qx += (qw * gx + qy * gz - qz * gy) * half_dt
        self._qy += (qw * gy - qx * gz + qz * gx) * half_dt
        self._qz += (qw * gz + qx * gy - qy * gx) * half_dt
        self._normalize_quaternion()

    def _build_output(self, msg: Imu, gx: float, gy: float, gz: float) -> Imu:
        imu_filter_msg = Imu()
        imu_filter_msg.header = msg.header
        imu_filter_msg.orientation.x = self._qx
        imu_filter_msg.orientation.y = self._qy
        imu_filter_msg.orientation.z = self._qz
        imu_filter_msg.orientation.w = self._qw

        if msg.orientation_covariance[0] < 0.0:
            imu_filter_msg.orientation_covariance[0] = 0.05
            imu_filter_msg.orientation_covariance[4] = 0.05
            imu_filter_msg.orientation_covariance[8] = 0.15
        else:
            imu_filter_msg.orientation_covariance = msg.orientation_covariance

        imu_filter_msg.angular_velocity.x = gx
        imu_filter_msg.angular_velocity.y = gy
        imu_filter_msg.angular_velocity.z = gz
        imu_filter_msg.angular_velocity_covariance = msg.angular_velocity_covariance
        imu_filter_msg.linear_acceleration = msg.linear_acceleration
        imu_filter_msg.linear_acceleration_covariance = msg.linear_acceleration_covariance
        return imu_filter_msg

    def imu_callback(self, msg: Imu):
        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        az = msg.linear_acceleration.z
        gx = msg.angular_velocity.x
        gy = msg.angular_velocity.y
        gz = msg.angular_velocity.z

        dt = self._compute_dt(msg)

        accel = self._normalize_accel(ax, ay, az)
        
        if accel is None:
            return
        
        ax, ay, az = accel

        if not self._calibrate_gyro_bias(gx, gy, gz):
            self._publish_passthrough(msg)
            return

        gx -= self._bgx
        gy -= self._bgy
        gz -= self._bgz
        gx, gy, gz = self._apply_correction(gx, gy, gz, ax, ay, az, dt)
        self._integrate_quaternion(gx, gy, gz, dt)
        imu_filter_msg = self._build_output(msg, gx, gy, gz)
        self.imu_filter_pub.publish(imu_filter_msg)

def main():
    rclpy.init()
    imu_filter = ImuFilter()
    
    try:
        rclpy.spin(imu_filter)
    finally:
        imu_filter.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()