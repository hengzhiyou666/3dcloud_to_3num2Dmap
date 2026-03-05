#!/usr/bin/env python3
"""
订阅 /odometry (nav_msgs/Odometry)，将 pose 发布为 tf：header.frame_id -> child_frame_id。
用于在回放 bag 时向 slam_toolbox 提供 odom_frame -> base_frame 的变换。
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


class OdomToTfNode(Node):
    def __init__(self):
        super().__init__('odom_to_tf_node')
        self.declare_parameter('odom_topic', '/odometry')
        self.declare_parameter('odom_frame_id_override', '')  # 空则使用 msg.header.frame_id
        self.declare_parameter('child_frame_id_override', '')  # 空则使用 msg.child_frame_id
        self._tf_broadcaster = TransformBroadcaster(self)
        odom_topic = self.get_parameter('odom_topic').get_parameter_value().string_value
        try:
            self.get_parameter('use_sim_time').get_parameter_value().bool_value
        except Exception:
            pass
        self._sub = self.create_subscription(
            Odometry,
            odom_topic,
            self._odom_cb,
            10,
        )
        self._logged_first = False

    def _odom_cb(self, msg: Odometry):
        if not self._logged_first:
            self._logged_first = True
            self.get_logger().info(
                f'Received first /odometry: frame_id={msg.header.frame_id}, child_frame_id={msg.child_frame_id}, publishing tf.'
            )
        t = TransformStamped()
        t.header = msg.header
        t.child_frame_id = msg.child_frame_id
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation

        odom_frame = self.get_parameter('odom_frame_id_override').get_parameter_value().string_value
        child_frame = self.get_parameter('child_frame_id_override').get_parameter_value().string_value
        if odom_frame:
            t.header.frame_id = odom_frame
        if child_frame:
            t.child_frame_id = child_frame

        self._tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = OdomToTfNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
