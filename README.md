# Docker Image and Utility for Onboard Computers

**TL;DR**: This repository contains [a Docker image](https://hub.docker.com/repository/docker/deathhorn/onboard_env/general) and [a container interface](docker.py) for simulation and hardware experiments of drones.

![Cover](cover.png)

The docker images provide a ready-to-use environment with pre-installed packages for drone **simulation and hardware offboard experiments**, for **both x64 and arm64** platforms. We recommend using this image for both simulation on workstations and real-world experiments, as it greatly **simplifies the setup process** and **ensures environment consistency** across different machines. The environment details can be found in the [Environment Details](#environment-details).

- [Docker Image and Utility for Onboard Computers](#docker-image-and-utility-for-onboard-computers)
  - [Usage](#usage)
    - [Basic Usage](#basic-usage)
      - [国内用户](#国内用户)
    - [Use prebuilt packages](#use-prebuilt-packages)
      - [VINS-Fusion](#vins-fusion)
      - [Fast-LIO2](#fast-lio2)
      - [SITL with gazebo and PX4 (for x64 image only)](#sitl-with-gazebo-and-px4-for-x64-image-only)
    - [Connect to the container via SSH](#connect-to-the-container-via-ssh)
    - [Simulation with Custom Drone Models](#simulation-with-custom-drone-models)
  - [Environment Details](#environment-details)
    - [Intel RealSense Depth Camera Support](#intel-realsense-depth-camera-support)
    - [LiDAR Support](#lidar-support)
    - [OptiTrack Motion Capture Support](#optitrack-motion-capture-support)
    - [Neural Network Inference Support](#neural-network-inference-support)

## Usage

### Basic Usage
Setting everything up:
```bash
# clone the repository
git clone https://github.com/flyingbitac/fly_in_docker.git
# then pull the prebuilt image
python fly_in_docker/docker.py pull
# or download the resources and build the image locally (not recommended)
python fly_in_docker/docker.py build
```

Work with the container:
```bash
# start the container
python fly_in_docker/docker.py start -d /path/to/your/workspace # will be mounted at /root/ws/workspace
# enter the container
python fly_in_docker/docker.py enter
# stop the container
python fly_in_docker/docker.py stop
```

#### 国内用户
对于国内用户，为了绕过 Docker Hub 的访问限制，可以使用阿里云的 ACR 服务。只需在拉取容器时添加 `-a` 或 `--use_alibaba_acr` 参数即可：
```bash
# 使用阿里云 ACR 服务拉取容器
python fly_in_docker/docker.py pull -a
```

此外，镜像构建的过程也需要从外部网站拉取许多依赖，因此建议使用代理来加速构建：
```bash
http_proxy=http://<proxy_address>:<proxy_port> python fly_in_docker/docker.py build
# or
https_proxy=http://<proxy_address>:<proxy_port> python fly_in_docker/docker.py build
```

### Use prebuilt packages
#### VINS-Fusion
```bash
source ~/ws/vins/devel/setup.bash
roslaunch vins up.launch
```
#### Fast-LIO2
Before using Fast-LIO2, please modify the IP, subnet mask, and gateway of the **HOST** OS ethernet to connect to the Livox LiDAR:
- **IP**: `192.168.1.5`
- **Subnet Mask**: `255.255.255.0`
- **Gateway**: `192.168.1.1`

Then run:
```bash
source ~/ws/livox_ws/devel/setup.bash
roslaunch fast_lio2 hardware_lidar_imu.launch ip:=192.168.1.1xx
```
#### SITL with gazebo and PX4 (for x64 image only)
```bash
source ~/ws/px4_setup.bash
export DISPLAY=:x # replace `:x` with your display number
roslaunch px4 mavros_posix_sitl.launch [gui:=false] # if you want gazebo to run in the headless mode
```

### Connect to the container via SSH
```bash
ssh root@<ip address of the host machine> -p 2222 # default password is 'letmein'
```

### Simulation with Custom Drone Models
To use custom drone models, you can specify the path to the model directory using the `-c` or `--custom_model_path` option when starting the container. The model directory should contain a valid PX4 drone model.

For example:
```bash
# start the container with custom drone models
python fly_in_docker/docker.py start \
  -d /path/to/your/workspace \
  -c /path/to/your/custom_model_1 \
  -c /path/to/your/custom_model_2

# enter the container
python fly_in_docker/docker.py enter

# then re-compile the PX4 firmware with the custom models
cd ~/ws/PX4-Autopilot && DONT_RUN=1 make px4_sitl_default gazebo

# setting up environment variables
source ~/ws/px4_setup.bash

# start the simulation with the custom model
roslaunch px4 mavros_posix_sitl.launch vehicle:=custom_model_1
```

## Environment Details
- **OS**: Ubuntu 20.04
- **ROS & MAVROS**: Noetic
- **PX4 Firmware**: v1.15.4
- **Python**: 3.8.10
- **Gazebo**: 11 (with PX4 SITL support) (**x64 image only**)

### Intel RealSense Depth Camera Support
- ros-noetic-cv-bridge
- ros-noetic-realsense2-camera
- librealsense2
- opencv-python
- pyrealsense2
- [vins-fusion](https://github.com/flyingbitac/VINS-Fusion)

### LiDAR Support
- [Livox-SDK2](https://github.com/Livox-SDK/Livox-SDK2)
- [livox_ros_driver2](https://github.com/flyingbitac/livox_ros_driver2)
- [Fast-LIO2](https://github.com/flyingbitac/FAST_LIO)
- [livox_laser_simulation](https://github.com/flyingbitac/livox_laser_simulation)

### OptiTrack Motion Capture Support
- [vrpn packages](https://github.com/flyingbitac/offboard_vrpn_pkgs) prebuilt

### Neural Network Inference Support
- pytorch 2.4.1-cpu
- torchvision 0.19.1-cpu
- torchaudio 2.4.1-cpu
- onnxruntime-cpu
