# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, List, Dict, Optional, Union
import argparse
import grp
import getpass
from textwrap import dedent

def get_hostname() -> str:
    """Get the hostname of the machine.

    Returns:
        The hostname of the machine.
    """
    return subprocess.run(
        ["hostname"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

def is_user_in_docker_group() -> bool:
    """
    Check if the current user is a member of the 'docker' group.

    Returns:
        True if the user is in the 'docker' group, False otherwise.
    """
    try:
        docker_grp = grp.getgrnam("docker")
    except KeyError:
        # 'docker' group does not exist on the system
        return False

    # Get list of group IDs the process belongs to
    user_gids = os.getgroups()
    # Also check membership by username in the group's member list
    username = getpass.getuser()

    return (docker_grp.gr_gid in user_gids) or (username in docker_grp.gr_mem)

class ContainerInterface:
    """A helper class for managing Isaac Lab containers."""

    def __init__(
        self,
        dir: Path,
        custom_model_paths: List[str],
        alibaba_acr: bool
    ):
        """Initialize the container interface with the given parameters.

        Args:
            dir: The directory to be mounted in the container.
        """
        self.dir = dir.resolve().expanduser()
        # set the context directory
        self.context_dir = Path(__file__).resolve().parent.joinpath("resources")
        self.dockerfile_dir = Path(__file__).resolve().parent.joinpath("dockerfiles").joinpath("Dockerfile")
        self.version = "deploy-v0.3"
        if alibaba_acr:
            self.repo_name = "crpi-jq3nu6qbricb9zcb.cn-beijing.personal.cr.aliyuncs.com/zxh_in_bitac/drones"
        else:
            self.repo_name = "deathhorn/onboard_env"
        self.digest = "sha256:70346dc9a0f22cb477da23819b38b195836de9871254c0b0e38514fcf845bdd0"
        if self.does_image_exist():
            self.image_id = self.get_image_id()
        self.image_name = f"{self.repo_name}:{self.version}"
        self.container_name = "onboard_env"
        self.host_name = get_hostname()
        
        assert is_user_in_docker_group(), dedent(f"""
            The current user is not in the 'docker' group. Please add the user to the 'docker' group and restart the terminal:
            `sudo usermod -a -G docker {getpass.getuser()}`
        """)
        
        self.runtime_resources_dir = Path(__file__).resolve().parent.joinpath("runtime_resources")
        self.mounted_volumes: List[Dict[str, Union[str, bool]]] = []
        self.mount_volume(source=self.dir, target=Path("/root/ws/workspace"))
        self.mount_volume(source=Path("/tmp/.X11-unix"), target=Path("/tmp/.X11-unix"))
        self.mount_volume(source=Path("~/.Xauthority").expanduser(), target=Path("/root/.Xauthority"))
        self.mount_volume(source=self.dir.joinpath("ros_log"), target=Path("/root/.ros/log"))
        # self.mount_volume(source=self.dir.joinpath("ros_outputs"), target=Path("/root/.ros/outputs"))
        self.mount_volume(source=self.runtime_resources_dir.joinpath("px4_setup.bash"), target=Path("/root/ws/px4_setup.bash"), read_only=True)

        # keep the environment variables from the current environment
        self.environ = os.environ
        self.custom_model_paths = custom_model_paths
    
    def get_image_id(self) -> str:
        """Get the image ID of the Docker image.

        Returns:
            The image ID of the Docker image.
        """
        result = subprocess.run(
            ["docker", "images", "--digests", "--format", "{{.Digest}},{{.ID}}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        image_id = ""
        for line in result.splitlines():
            digest, id = line.split(",")
            if digest == self.digest:
                image_id = id
                break
        if not image_id:
            raise RuntimeError(f"Image with digest {self.digest} not found. Please pull the image first.")
        return image_id
    
    def add_custom_drone_model(
        self,
        model_path
    ):
        model_path = Path(model_path).expanduser().resolve()
        container_px4_path = Path("/root/ws/PX4-Autopilot")
        files = os.listdir(model_path)
        romfs_file = ""
        model_mounted = False
        airframe_mounted = False
        for file in files:
            file_path = model_path.joinpath(file).resolve()
            if os.path.isdir(file_path):
                model_mounted = True
                target = container_px4_path.joinpath("Tools/simulation/gazebo-classic/sitl_gazebo-classic/models").joinpath(file)
                self.mount_volume(source=file_path, target=target, type="bind", read_only=True)
                print(f"Mounted custom drone model directory: {file_path} to {target}")
            elif not file.endswith(".yaml"):
                airframe_mounted = True
                romfs_file = file
                target = container_px4_path.joinpath("ROMFS/px4fmu_common/init.d-posix/airframes").joinpath(file)
                self.mount_volume(source=file_path, target=target, type="bind", read_only=True)
                print(f"Mounted custom drone model file: {file_path} to {target}")
        assert model_mounted, "Model directory mounting failed. Please check the model directory."
        assert airframe_mounted, "Airframe file mounting failed. Please check the model Airframe file."
        self.model_cmake_list.insert(-2, f"\t{romfs_file}\n")
        source = self.runtime_resources_dir.joinpath("model_CMakeLists_mount.txt")
        with open(source, "w") as f: f.writelines(self.model_cmake_list)
        mount_sources = [str(mount["source"]) for mount in self.mounted_volumes]
        if all(str(source) != mount_source for mount_source in mount_sources):
            target = container_px4_path.joinpath("ROMFS/px4fmu_common/init.d-posix/airframes/CMakeLists.txt")
            self.mount_volume(source=source, target=target, type="bind", read_only=True)

    def mount_volume(
        self,
        source: Path,
        target: Path,
        type: str = "bind",
        read_only: bool = False,
    ):
        """Mount a volume to the container.

        Args:
            source: The source path on the host machine.
            target: The target path in the container.
            type: The type of mount. Defaults to "bind".
            read_only: Whether the mount is read-only. Defaults to False.
        """
        self.mounted_volumes.append(
            {
                "source": str(source),
                "target": str(target),
                "type": type,
                "read_only": read_only,
            }
        )
    
    def mount_args(self):
        os.makedirs(self.dir.joinpath("ros_log"), exist_ok=True)
        # os.makedirs(self.dir.joinpath("ros_outputs"), exist_ok=True)
        mount_args = []
        for mount in self.mounted_volumes:
            mount_args.append("--mount")
            mount_args.append(f"type={mount['type']},source={mount['source']},target={mount['target']}")
            if mount["read_only"]:
                mount_args[-1] += ",readonly"
        return mount_args

    def is_container_running(self) -> bool:
        """Check if the container is running.

        Returns:
            True if the container is running, otherwise False.
        """
        status = subprocess.run(
            ["docker", "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        return status == "running"

    def does_image_exist(self) -> bool:
        """Check if the Docker image exists.

        Returns:
            True if the image exists, otherwise False.
        """
        result = subprocess.run(
            ["docker", "images", "--digests", "--format", "{{.Digest}}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        return self.digest in result.splitlines()
    
    def get_resources(self):
        """
        Download necessary resources to build the image if they do not exist.
        """
        if not os.path.exists(self.context_dir):
            os.makedirs(self.context_dir)
        commands = [
            [
                "wget",
                "https://github.com/acados/tera_renderer/releases/download/v0.0.34/t_renderer-v0.0.34-linux",
                "-O",
                str(self.context_dir.joinpath("t_renderer")),
            ],
            [
                "wget",
                "https://github.com/IntelRealSense/librealsense/blob/master/config/99-realsense-libusb.rules",
                "-O",
                str(self.context_dir.joinpath("99-realsense-libusb.rules")),
            ],
        ]
        for command in commands:
            if not os.path.exists(command[-1]):
                print(f"[INFO] Downloading resources with command: {' '.join(command)}")
                try:
                    subprocess.run(command, check=True, capture_output=True, text=True, cwd=self.context_dir)
                except subprocess.CalledProcessError as e:
                    command[1] = "http://gh-proxy.com/" + command[1]  # Fallback to HTTP proxy if download fails
                    print(f"[WARNING] Download failed with error: {e}. Retrying with proxy...")
                    subprocess.run(command, check=True, capture_output=True, text=True, cwd=self.context_dir)
            else:
                print(f"[INFO] Resource {command[-1]} already exists. Skipping download.")
    
    def build(self):
        # raise NotImplementedError("The build method is not implemented yet.")
        self.get_resources()
        command = [
            "docker",
            "build",
            "-t",
            self.image_name,
            "--network=host",
            str(self.context_dir),
            "-f",
            str(self.dockerfile_dir)
        ]
        http_proxy, https_proxy = self.environ.get("http_proxy", ""), self.environ.get("https_proxy", "")
        if len(http_proxy) > 0:
            command.append("--build-arg")
            command.append(f"PROXY_HOST={http_proxy}")
            print(f"[INFO] Using HTTP proxy {http_proxy} for building the image.")
        elif len(https_proxy) > 0:
            command.append("--build-arg")
            command.append(f"PROXY_HOST={https_proxy}")
            print(f"[INFO] Using HTTPS proxy {https_proxy} for building the image.")
        else:
            print("[WARNING] No proxy environment variables found. Building without proxy. The build may stuck or fail if the network is restricted.")
        subprocess.run(command, check=False, cwd=Path(__file__).resolve().parent)
    
    def pull(self):
        if self.does_image_exist():
            print(f"[INFO] The image '{self.image_name}' already exists. No need to pull it again.")
            return
        command = [ 
            "docker",
            "pull",
            self.image_name,
        ]
        subprocess.run(command, check=True, capture_output=False, text=True)

    def start(self):
        if not self.is_container_running():
            if not self.does_image_exist():
                raise RuntimeError(f"The image '{self.image_name}' does not exist. Please pull or build it first by `python docker.py pull/build`.")
            else:
                print(f"[INFO] The image '{self.image_name}' already exists. Starting the container...")

            with open(self.runtime_resources_dir.joinpath("model_CMakeLists.txt"), "r") as f:
                self.model_cmake_list = f.readlines()
            
            for model_path in self.custom_model_paths:
                self.add_custom_drone_model(model_path)
            # start the container
            command = [
                "docker",
                "run",
                "--rm",
                "-dit",
                "--name",
                self.container_name,
                "--hostname",
                self.host_name,
                *self.mount_args(),
                f"--env=DISPLAY={os.environ.get('DISPLAY', ':0')}",
                f"--env=ROS_HOSTNAME={self.host_name}",
                f"--env=ROS_MASTER_URI=http://{self.host_name}:11311",
                "--privileged", # for USB ports access
                "--network=host",
                self.image_id,
            ]
            subprocess.run(command, check=False)
        else:
            print(f"[INFO] The container '{self.container_name}' is already running.")

    def enter(self):
        """Enter the running container by executing a bash shell.

        Raises:
            RuntimeError: If the container is not running.
        """
        if self.is_container_running():
            print(f"[INFO] Entering the existing '{self.container_name}' container in a bash session...\n")
            subprocess.run([
                "docker",
                "exec",
                "--interactive",
                "--tty",
                f"--env=DISPLAY={os.environ.get('DISPLAY', ':0')}",
                f"{self.container_name}",
                "bash",
            ])
        else:
            raise RuntimeError(f"The container '{self.container_name}' is not running.")

    def stop(self):
        """Stop the running container using the Docker compose command.

        Raises:
            RuntimeError: If the container is not running.
        """
        if self.is_container_running():
            print(f"[INFO] Stopping the launched docker container '{self.container_name}'...\n")
            subprocess.run(
                ["docker", "stop", self.container_name],
                check=False,
                cwd=self.context_dir,
                env=self.environ,
            )
        else:
            raise RuntimeError(f"Can't stop container '{self.container_name}' as it is not running.")

def parse_cli_args() -> argparse.Namespace:
    """Parse command line arguments.

    This function creates a parser object and adds subparsers for each command. The function then parses the
    command line arguments and returns the parsed arguments.

    Returns:
        The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Utility for using Docker. Run `docker login --username=zxhomo crpi-jq3nu6qbricb9zcb.cn-beijing.personal.cr.aliyuncs.com` to login to the docker registry."
    )
    
    # We have to create separate parent parsers for common options to our subparsers
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "-d", "--dir",
        default=os.getcwd(),
        help=("The directory to be mounted in the container. "),
    )
    parent_parser.add_argument("-a", "--use_alibaba_acr", action="store_true", help="Whether to pull from Alibaba ACR service or docker hub.")
    parent_parser.add_argument("-c", "--custom_model_path", type=str, default=[], action="append", help="Path to a custom drone model directory.")

    # Actual command definition begins here
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start", help="Pull the docker image and create the container in detached mode.", parents=[parent_parser])
    subparsers.add_parser("enter", help="Begin a new bash process within an existing container.", parents=[parent_parser])
    subparsers.add_parser("stop", help="Stop the docker container and remove it.", parents=[parent_parser])
    subparsers.add_parser("pull", help="Pull the docker image from the registry.", parents=[parent_parser])
    subparsers.add_parser("build", help="Build the docker image from the Dockerfile.", parents=[parent_parser])

    # parse the arguments to determine the command
    args = parser.parse_args()

    return args

def main(args: argparse.Namespace):
    """Main function for the Docker utility."""
    # check if docker is installed
    if not shutil.which("docker"):
        raise RuntimeError("Docker is not installed! Please install Docker following https://docs.docker.com/engine/install/ubuntu/ and try again.")

    # creating container interface
    ci = ContainerInterface(dir=Path(args.dir).expanduser(), custom_model_paths=args.custom_model_path, alibaba_acr=args.use_alibaba_acr)

    if   args.command == "start": ci.start()
    elif args.command == "enter": ci.enter()
    elif args.command == "stop":  ci.stop()
    elif args.command == "pull":  ci.pull()
    elif args.command == "build": ci.build()
    else:
        raise RuntimeError(f"Invalid command provided: {args.command}. Please check the help message.")


if __name__ == "__main__":
    args_cli = parse_cli_args()
    main(args_cli)