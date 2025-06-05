# Docker Image and Utility for Onboard Computers

## Environment Details

Based on [osrf/ros:noetic-desktop-full](https://hub.docker.com/r/osrf/ros/tags)

- Ubuntu 20.04
- openssh-server
- ROS Noetic
  - ros-noetic-mavros
  - ros-noetic-mavros-extras
  - ros-noetic-mavros-msgs
  - ros-noetic-cv-bridge
  - ros-noetic-realsense2-camera
  - vrpn packages prebuilt for flight in optitrack
- PX4-Autopilot 1.15.4
- Gazebo 11
- [SITL with PX4 and Gazebo](https://docs.px4.io/v1.15/en/simulation/ros_interface.html#launching-gazebo-classic-with-ros-wrappers) prebuilt
- librealsense2
- Python 3.8.10
  - pyrealsense2
  - opencv-python
  - numpy
  - pandas
  - matplotlib
  - pytorch 2.4.1-cpu
  - torchvision 0.19.1-cpu
  - torchaudio 2.4.1-cpu
  - onnxruntime-cpu
  - casadi 3.7.0
  - acados 0.5.0

## Usage

```bash
# clone the repository
git clone https://github.com/flyingbitac/fly_in_docker.git
# pull the image
python fly_in_docker/docker.py pull
# or download the resources and build the image locally
python fly_in_docker/docker.py build
# start the container
python fly_in_docker/docker.py start --dir=/path/to/your/workspace # will be mounted at /root/ws/user_workspace
# enter the container
python fly_in_docker/docker.py enter
# stop the container
python fly_in_docker/docker.py stop
```

Connect through SSH to the container:

```bash
ssh root@<ip address of the host machine> -p 2222
# default password is 'letmein'
```