# 从点云 + 里程计输出三值二维栅格地图（slam_toolbox）

在 ROS2 Humble 下，用 **slam_toolbox** 从 `/lidar_points`（PointCloud2，基于 lidar_init）和 `/odometry`（基于 lidar_init）生成 **三值二维栅格地图** `/map`（`nav_msgs/OccupancyGrid`：-1 未知 / 0 空闲 / 100 占用）。

## 依赖

- ROS2 Humble
- slam_toolbox
- pointcloud_to_laserscan

安装系统包：

```bash
sudo apt update
sudo apt install ros-humble-slam-toolbox ros-humble-pointcloud-to-laserscan
```

## 编译

在工作空间根目录（与 `cloud_to_2d_slam` 同级）执行：

```bash
cd /home/hzy/0.1cloud_to_2dscan
colcon build --packages-select cloud_to_2d_slam
source install/setup.bash
```

## 使用

1. **回放 bag**（建议先开一个终端，使用 `--clock`；若用 mcap 且需可靠 QoS，可加 `--qos-profile-overrides-path`）：

   ```bash
   # 示例：slam_building_2（mcap，-r 0.2 为 0.2 倍速；若机器不卡可改为 -r 0.5 或 -r 1.0 加快建图）
   cd "/home/hzy/0.1播放原始包/5floor/slam_building_2"
   ros2 bag play slam_building_2_0.mcap --qos-profile-overrides-path reliable_override.yaml --loop --clock -r 0.2
   ```

   若没有 `reliable_override.yaml`，可省略 `--qos-profile-overrides-path` 及其参数；或使用你自己的 .db3 路径：

   ```bash
   ros2 bag play /path/to/your.bag_0.db3 --clock
   ```

2. **启动本包的一键 launch**（会启动：odom→tf、点云→2D 扫描、slam_toolbox）：

   ```bash
   source install/setup.bash
   ros2 launch cloud_to_2d_slam cloud_to_2d_slam.launch.py use_sim_time:=true
   ```

   **可选：建图时实时把地图写入本地**（按间隔刷新 `map_latest.pgm` / `map_latest.yaml`）：

   ```bash
   source install/setup.bash
   ros2 launch cloud_to_2d_slam cloud_to_2d_slam.launch.py use_sim_time:=true save_map_to_disk:=true
   ```

   可调参数：`map_output_dir:=/path/to/dir`（保存目录，默认当前目录）、`map_file_prefix:=map_latest`、`map_update_interval_sec:=2.0`（每 2 秒写一次）。

3. **查看地图**：在 RViz2 中添加 `Map` 显示，Topic 选 `/map`。

---

### 保存三值栅格地图到本地（用于全局路径规划）

建图满意后，在**建图仍在运行**或**刚停掉**时保存。生成 **.pgm + .yaml** 即可被 Nav2、Move Base 等用于全局路径规划。

**方式一：slam_toolbox 自带服务（推荐）**

```bash
# 保存到当前终端所在目录，文件名为 my_map.pgm / my_map.yaml
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "name: {data: 'my_map'}"
```

**方式二：nav2 map_saver（需先安装 nav2）**

```bash
sudo apt install ros-humble-nav2-map-server
# 保存到当前目录，-f 后为文件名（不含扩展名）
ros2 run nav2_map_server map_saver_cli -f my_map
```

**输出文件说明**

| 文件 | 说明 |
|------|------|
| `my_map.pgm` | 栅格图像（灰度：白=空闲，黑=占用，灰=未知） |
| `my_map.yaml` | 元数据：`resolution`、`origin`、`occupied_threshold`、`free_threshold`，供 map_server 加载 |

**在全局路径规划中的用法**

- Nav2：在 `nav2_params.yaml` 里配置 `map_server` 的 `yaml_filename` 指向该 yaml，或 launch 时传入地图路径。
- 其他规划器：读取 yaml 得到分辨率与原点，再按 pgm 像素做代价或可通行性即可。

## 话题与坐标系约定

| 话题/TF        | 说明 |
|----------------|------|
| `/lidar_points` | 输入点云，`header.frame_id` 须与 slam 配置中 `odom_frame` 一致（当前默认 `vita_lidar`；可通过 launch 参数 `pointcloud_topic` 更换） |
| `/odometry`     | 输入里程计，`header.frame_id` 须为 `odom_frame`（如 `vita_lidar`），`child_frame_id` 须为 `base_frame`（如 `base_link`）；可通过 `odom_topic` 更换 |
| `/scan`         | 本包内部：由 pointcloud_to_laserscan 从点云生成，供 slam_toolbox 使用 |
| `/map`          | 本包输出：三值二维栅格（`nav_msgs/OccupancyGrid`） |
| TF `map` → `odom_frame` | 由 slam_toolbox 发布（如 map → vita_lidar） |
| TF `odom_frame` → `base_frame` | 由本包 `odom_to_tf_node` 根据里程计话题发布（如 vita_lidar → base_link） |

若你的 bag 里 `child_frame_id` 不是 `base_link`，可在 launch 中为 `odom_to_tf_node` 设置参数 `child_frame_id_override`（或 `odom_frame_id_override`）以保持一致。

### 与你现有话题的关系

- **本包只订阅**：`/lidar_points`、`/odometry`（话题名可通过 launch 参数改）。
- **本包会发布**：`/scan`、`/map`，以及 TF（`map`→odom_frame、odom_frame→base_frame，如 `vita_lidar`→`base_link`）。
- **不冲突**：你已有的 `/grid_map`（多为 `grid_map_msgs/GridMap`）与我们的 `/map`（`nav_msgs/OccupancyGrid`）是不同类型、不同用途，可并存。
- **未使用**：`/path`、`/imu_raw`、`/lidar_imu`、`/gnss/fix`、图像等本包未接；若希望用 `/lidar_imu` 当里程计，只要其类型为 `nav_msgs/Odometry` 且坐标系约定一致，可启动时加：`odom_topic:=/lidar_imu`。

## 可选调参

- **config/slam_toolbox_params.yaml**：栅格分辨率 `resolution`、激光范围 `min_laser_range`/`max_laser_range`、更新间隔 `map_update_interval` 等。
- **config/pointcloud_to_laserscan_params.yaml**：投影高度范围 `min_height`/`max_height`、`range_min`/`range_max`、角度范围等，请按雷达安装和场景调整。

## 目录结构

```
0.1cloud_to_2dscan/
├── README.md
└── cloud_to_2d_slam/           # ROS2 包
    ├── config/
    │   ├── slam_toolbox_params.yaml
    │   └── pointcloud_to_laserscan_params.yaml
    ├── launch/
    │   └── cloud_to_2d_slam.launch.py
    ├── cloud_to_2d_slam/
    │   ├── __init__.py
    │   └── odom_to_tf_node.py  # /odometry -> tf
    ├── package.xml
    ├── resource/
    ├── setup.cfg
    └── setup.py
```
