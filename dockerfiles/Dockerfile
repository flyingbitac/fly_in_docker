FROM osrf/ros:noetic-desktop-full

ARG PROXY_HOST=""

# Setup your sources.list and keys
RUN rm /etc/apt/sources.list.d/ros* && \
    apt-get update && \
    apt-get install curl -y && \
    curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add - && \
    sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list' && \
    rm -rf /var/lib/apt/lists/*

# allow ssh access
RUN apt-get update && \
    apt-get install -y \
        passwd \
        openssl \
        openssh-server && \
    rm -rf /var/lib/apt/lists/*

RUN echo 'root:letmein' | chpasswd && \
    echo "Port 2222" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

# install MAVROS and dependencies
RUN apt-get update && \
    apt-get install -y \
        ros-noetic-mavros \
        ros-noetic-mavros-extras \
        ros-noetic-mavros-msgs \
        ros-noetic-cv-bridge \
        build-essential \
        python3-pip \
        python3-catkin-tools \
        python3-rosinstall-generator \
        git \
        # for realsense installation
        curl \
        # for ifconfig
        net-tools \
        wget \
        apt-transport-https && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/ws

# install geographiclib datasets
RUN wget http://gh-proxy.com/https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh -O /root/ws/install_geographiclib_datasets.sh && \
    export http_proxy=$PROXY_HOST && \
    export https_proxy=$PROXY_HOST && \
    bash /root/ws/install_geographiclib_datasets.sh && \
    export http_proxy="" && \
    export https_proxy="" && \
    rm /root/ws/install_geographiclib_datasets.sh

# install PX4-Autopilot
RUN git config --global http.proxy $PROXY_HOST && \
    git config --global https.proxy $PROXY_HOST && \
    git clone https://github.com/PX4/PX4-Autopilot.git --recursive -b v1.15.4 /root/ws/PX4-Autopilot && \
    git config --global --unset http.proxy && \
    git config --global --unset https.proxy

RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    bash /root/ws/PX4-Autopilot/Tools/setup/ubuntu.sh --no-nuttx && \
    rm -rf /var/lib/apt/lists/* && \
    pip config unset global.index-url && \
    pip install -U pip && \
    python3 -m pip cache purge

WORKDIR /root/ws/PX4-Autopilot

# prebuild for gazebo simulation
RUN DONT_RUN=1 make px4_sitl_default gazebo-classic

WORKDIR /root/ws/

RUN echo "source /opt/ros/noetic/setup.bash" >> /root/.bashrc

ENV PX4_PATH=/root/ws/PX4-Autopilot

# install Realsense SDK and ROS wrapper
RUN mkdir -p /etc/apt/keyrings && \
    curl -sSf https://librealsense.intel.com/Debian/librealsense.pgp | tee /etc/apt/keyrings/librealsense.pgp > /dev/null && \
    echo "deb [signed-by=/etc/apt/keyrings/librealsense.pgp] https://librealsense.intel.com/Debian/apt-repo `lsb_release -cs` main" | tee /etc/apt/sources.list.d/librealsense.list && \
    apt-get update && \
    apt-get install -y \
        # for lsusb
        usbutils \
        librealsense2-dkms \
        librealsense2-utils \
        librealsense2-dev \
        librealsense2-dbg \
        ros-noetic-realsense2-camera && \
    rm -rf /var/lib/apt/lists/* && \
    pip install pyrealsense2 && \
    python3 -m pip cache purge

# following https://github.com/IntelRealSense/realsense-ros/issues/1408
COPY 99-realsense-libusb.rules /etc/udev/rules.d/99-realsense-libusb.rules

# install dependencies for inference
RUN pip install -q torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cpu && \
    pip install -q -U -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
        onnxruntime \
        line_profiler \
        flatbuffers \
        packaging \
        protobuf \
        sympy \
        matplotlib \
        opencv-python && \
    python3 -m pip cache purge

# install casadi
RUN pip install -q -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple casadi==3.7.0 && \
    python3 -m pip cache purge

# install acados: https://docs.acados.org/installation/index.html#linux-mac, https://docs.acados.org/python_interface/index.html#installation
RUN git config --global http.proxy $PROXY_HOST && \
    git config --global https.proxy $PROXY_HOST && \
    git clone https://github.com/acados/acados.git --recursive -b v0.5.0 /root/ws/acados && \
    git config --global --unset http.proxy && \
    git config --global --unset https.proxy

RUN mkdir -p /root/ws/acados/build && \
    cd /root/ws/acados/build && \
    cmake -DACADOS_WITH_QPOASES=ON .. && \
    make install -j8 && \
    pip install -e /root/ws/acados/interfaces/acados_template -q -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    python3 -m pip cache purge && \
    echo "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:\"/root/ws/acados/lib\"" >> /root/.bashrc && \
    echo "export ACADOS_SOURCE_DIR=\"/root/ws/acados/\"" >> /root/.bashrc

COPY t_renderer /root/ws/acados/bin/t_renderer

RUN chmod +x /root/ws/acados/bin/t_renderer

# prebuild the vrpn packages for optitrack
RUN git config --global http.proxy $PROXY_HOST && \
    git config --global https.proxy $PROXY_HOST && \
    git clone https://github.com/flyingbitac/offboard_vrpn_pkgs.git --recursive /root/ws/offboard_vrpn_pkgs/src && \
    git config --global --unset http.proxy && \
    git config --global --unset https.proxy

WORKDIR /root/ws/offboard_vrpn_pkgs

# install dependencies for vrpn packages and build the workspace
# netbase is required for vrpn
RUN apt-get update && \
    apt-get install -y libtool netbase && \
    rm -rf /var/lib/apt/lists/* && \
    export http_proxy=$PROXY_HOST && \
    export https_proxy=$PROXY_HOST && \
    catkin config --extend /opt/ros/noetic && \
    cd /root/ws/offboard_vrpn_pkgs && \
    catkin build && \
    export http_proxy="" && \
    export https_proxy="" && \
    echo "source /root/ws/offboard_vrpn_pkgs/devel/setup.bash" >> /root/.bashrc

WORKDIR /root/ws/

EXPOSE 2222 11311

ENTRYPOINT service ssh restart && bash