#!/usr/bin/env python3
"""
统一启动：从 /lidar_points + /odometry 生成三值二维栅格 /map。
- odom_to_tf_node：/odometry -> tf (lidar_init -> base_link)
- pointcloud_to_laserscan：/lidar_points -> /scan
- slam_toolbox：/scan + tf -> /map (nav_msgs/OccupancyGrid)
回放 bag 时建议 use_sim_time:=true。
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile


def generate_launch_description():
    pkg_share = get_package_share_directory('cloud_to_2d_slam')
    slam_toolbox_share = get_package_share_directory('slam_toolbox')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    odom_topic = LaunchConfiguration('odom_topic', default='/odometry')
    odom_frame = LaunchConfiguration('odom_frame', default='vita_lidar')
    pointcloud_topic = LaunchConfiguration('pointcloud_topic', default='/lidar_points')
    slam_params_file = LaunchConfiguration(
        'slam_params_file',
        default=os.path.join(pkg_share, 'config', 'slam_toolbox_params.yaml'),
    )
    pcl_params_file = LaunchConfiguration(
        'pcl_params_file',
        default=os.path.join(pkg_share, 'config', 'pointcloud_to_laserscan_params.yaml'),
    )

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time (set true when playing bag).',
    )
    declare_odom_topic = DeclareLaunchArgument(
        'odom_topic',
        default_value='/odometry',
        description='Odometry topic for tf (lidar_init->base_link). E.g. /odometry or /lidar_imu if same msg type.',
    )
    declare_odom_frame = DeclareLaunchArgument(
        'odom_frame',
        default_value='vita_lidar',
        description='Frame id for odom tf parent (must match slam_toolbox odom_frame).',
    )
    declare_pointcloud_topic = DeclareLaunchArgument(
        'pointcloud_topic',
        default_value='/lidar_points',
        description='PointCloud2 topic for 2D scan conversion.',
    )
    declare_slam_params = DeclareLaunchArgument(
        'slam_params_file',
        default_value=os.path.join(pkg_share, 'config', 'slam_toolbox_params.yaml'),
        description='Full path to slam_toolbox params YAML.',
    )
    declare_pcl_params = DeclareLaunchArgument(
        'pcl_params_file',
        default_value=os.path.join(pkg_share, 'config', 'pointcloud_to_laserscan_params.yaml'),
        description='Full path to pointcloud_to_laserscan params YAML.',
    )

    odom_to_tf_node = Node(
        package='cloud_to_2d_slam',
        executable='odom_to_tf_node',
        name='odom_to_tf_node',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time, 'odom_topic': odom_topic, 'odom_frame_id_override': odom_frame},
        ],
    )

    pointcloud_to_laserscan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan_node',
        output='screen',
        remappings=[
            ('cloud_in', pointcloud_topic),
        ],
        parameters=[
            ParameterFile(pcl_params_file, allow_substs=True),
            {'use_sim_time': use_sim_time},
        ],
    )

    slam_toolbox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_toolbox_share, 'launch', 'online_async_launch.py'),
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam_params_file': slam_params_file,
        }.items(),
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_odom_topic,
        declare_odom_frame,
        declare_pointcloud_topic,
        declare_slam_params,
        declare_pcl_params,
        odom_to_tf_node,
        pointcloud_to_laserscan_node,
        slam_toolbox_launch,
    ])
