from setuptools import find_packages, setup

package_name = 'cloud_to_2d_slam'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', [
            'config/slam_toolbox_params.yaml',
            'config/pointcloud_to_laserscan_params.yaml',
        ]),
        ('share/' + package_name + '/launch', ['launch/cloud_to_2d_slam.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@todo.todo',
    description='从点云+里程计用 slam_toolbox 输出三值二维栅格地图',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'odom_to_tf_node = cloud_to_2d_slam.odom_to_tf_node:main',
            'map_to_disk_node = cloud_to_2d_slam.map_to_disk_node:main',
        ],
    },
)
