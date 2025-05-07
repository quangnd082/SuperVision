

import socket
import random


class VsClient(socket.socket):
    def __init__(self):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)

    def connect_to_server(self, host, port):
        try:
            self.connect((host, port))
            return ""
        except socket.error as e:
            error = f"Error connecting to {host}:{port}: {e}"
            print(error)
            return error
    
    def movej(self, x, y, z, rx=0, ry=0, rz=0):
        """
        Send the movej command to the server.

        Args:
            x (float): The x-coordinate of the target position.
            y (float): The y-coordinate of the target position.
            z (float): The z-coordinate of the target position.
            rx (float, optional): The rotation around the x-axis. Defaults to 0.
            ry (float, optional): The rotation around the y-axis. Defaults to 0.
            rz (float, optional): The rotation around the z-axis. Defaults to 0.
        """
        command = f"movej({x},{y},{z},{rx},{ry},{rz})"
        self.send(command)

    def movej_(self, pose_name):
        """
        Move the robot to the specified joint position.

        Args:
            pose_name (str): The name of the pose to move to.

        Returns:
            None
        """
        command = f"movej({pose_name})"
        self.send(command)
    
    def get_pose(self):
        """
        Get the pose data from the server.

        Returns:
            tuple: A tuple containing the pose data in the format (x, y, z, rx, ry, rz).
        """
        # self.send("get_pose")
        # pose_str = self.recv_from_server()
        # pose_data = tuple(map(float, (pose_str.split(","))))

        pose_data = (random.randint(-100, 100), # x
                     random.randint(-100, 100), # y
                     random.randint(-100, 100), # z
                     random.random() * 3.14, # rx
                     random.random() * 3.14, # ry
                     random.random() * 3.14) # rz

        # pose_data = (

        # )
        
        return pose_data

    def send(self, data):
        self.sendall(data.encode())

    def recv_from_server(self, size=1024):
        return self.recv(size).decode()