#!/usr/bin/env python3
"""
订阅 /map (nav_msgs/OccupancyGrid)，按固定间隔将当前地图写入本地 .pgm + .yaml，
实现“实时刷新”的本地地图，供全局路径规划加载。
"""

import os
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid


# 与 222.pgm / map_saver 一致：PGM 中 0=黑(障碍) 254=白(可通行) 205=灰(未知)，yaml negate: 0
OCCUPIED = 0
FREE = 254
UNKNOWN = 205


class MapToDiskNode(Node):
    def __init__(self):
        super().__init__('map_to_disk_node')
        self.declare_parameter('map_topic', '/map')
        self.declare_parameter('output_dir', '')
        self.declare_parameter('file_prefix', 'map_latest')
        self.declare_parameter('update_interval_sec', 2.0)
        self.declare_parameter('invert_for_display', False)
        self._output_dir = self.get_parameter('output_dir').get_parameter_value().string_value
        try:
            self._invert_for_display = self.get_parameter('invert_for_display').get_parameter_value().bool_value
        except Exception:
            self._invert_for_display = self.get_parameter('invert_for_display').get_parameter_value().string_value.lower() in ('1', 'true', 'yes')
        self._prefix = self.get_parameter('file_prefix').get_parameter_value().string_value
        try:
            self._interval_sec = self.get_parameter('update_interval_sec').get_parameter_value().double_value
        except Exception:
            self._interval_sec = float(self.get_parameter('update_interval_sec').get_parameter_value().string_value)
        self._last_write_ns = 0
        self._sub = self.create_subscription(
            OccupancyGrid,
            self.get_parameter('map_topic').get_parameter_value().string_value,
            self._map_cb,
            1,
        )

    def _map_cb(self, msg: OccupancyGrid):
        if msg.info.width == 0 or msg.info.height == 0:
            return
        now_ns = self.get_clock().now().nanoseconds
        if self._last_write_ns > 0 and (now_ns - self._last_write_ns) < self._interval_sec * 1e9:
            return
        self._last_write_ns = now_ns
        out_dir = self._output_dir if self._output_dir else os.getcwd()
        base = os.path.join(out_dir, self._prefix)
        yaml_path = base + '.yaml'
        pgm_path = base + '.pgm'
        try:
            self._write_pgm(pgm_path, msg)
            self._write_yaml(yaml_path, msg, os.path.basename(pgm_path))
            self.get_logger().info(f'Map written: {pgm_path}')
        except Exception as e:
            self.get_logger().error(f'Failed to write map: {e}')

    def _write_pgm(self, path: str, msg: OccupancyGrid):
        h, w = msg.info.height, msg.info.width
        n = h * w
        out = bytearray(n)
        # invert_for_display: 写入 255-value，使在“0=白”的查看器里显示为 黑=障碍、白=可通行
        inv = 255 if self._invert_for_display else 0
        for i in range(n):
            v = msg.data[i] if i < len(msg.data) else -1
            # ROS OccupancyGrid: 0=free, 100=occupied, -1=unknown -> PGM 0=黑(障碍) 254=白(可通行)
            raw = OCCUPIED if v == 100 else (FREE if v == 0 else UNKNOWN)
            out[i] = (255 - raw) if inv else raw
        with open(path, 'wb') as f:
            f.write(b'P5\n%d %d\n255\n' % (w, h))
            f.write(out)

    def _write_yaml(self, path: str, msg: OccupancyGrid, pgm_basename: str):
        o = msg.info.origin.position
        negate = 1 if self._invert_for_display else 0
        with open(path, 'w') as f:
            f.write(f'image: {pgm_basename}\n')
            f.write(f'resolution: {msg.info.resolution}\n')
            f.write(f'origin: [{o.x}, {o.y}, 0.0]\n')
            f.write(f'negate: {negate}\noccupied_threshold: 0.65\nfree_threshold: 0.196\n')


def main(args=None):
    rclpy.init(args=args)
    node = MapToDiskNode()
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
