import cv2
import numpy as np
import glob
import pickle

from collections import namedtuple
from scipy.spatial.transform import Rotation as R

from PyQt5.QtCore import pyqtSignal, QObject


RESULTCORNERS = namedtuple("Corners", ["src", "dst", "corners"])
RESULTCALIB = namedtuple("Calib", ["camera_matrix", "dist_coeffs", "mean_error"])
RESULTPOSE = namedtuple("Pose", ["pose", "x", "y", "z", "rx", "ry", "rz"])


class CalibUtils(QObject):
    infoSignal = pyqtSignal(str)
    errorSignal = pyqtSignal(str)
    stepSignal = pyqtSignal()
    startSignal = pyqtSignal()
    finishedSignal = pyqtSignal()

    def __init__(self, board_size=(6, 8), square_size=4, type="EyeToHand"):
        '''
        @board_size: (6, 8) # size of checker board 6 rows, 8 cols
        @square_size: 4 # real square size (mm)
        '''
        super().__init__()
        self._camera_matrix = None
        self._dist_coeffs = None
        self._mapx = None
        self._mapy = None
        self._roi = None
        self._square_size = square_size
        self._board_size = board_size
        self._t_camera_to_gripper = None
        self._type = type

    @classmethod
    def create(cls, board_size=(6, 8), square_size=4):
        return cls(board_size, square_size)

    def get_paths(self, image_dir):
        paths = []
        [paths.extend(glob.glob(f"{image_dir}/{ext}")) for ext in ["*.bmp", "*.png", "*.jpg"]]
        return paths
    
    def save(self, path):
        data = {
            "mtx": self._camera_matrix,
            "dist": self._dist_coeffs,
            "mapx": self._mapx,
            "mapy": self._mapy,
            "roi": self._roi,
            "board_size": self._board_size,
            "square_size": self._square_size,
            "t_camera_to_gripper": self._t_camera_to_gripper
        }
        with open(path, "wb") as file:
            pickle.dump(data, file)

    def load(self, path):
        try:
            with open(path, "rb") as file:
                data = pickle.load(file)
                self._camera_matrix = data["mtx"]
                self._dist_coeffs = data["dist"]
                self._mapx = data["mapx"]
                self._mapy = data["mapy"]
                self._roi = data["roi"]
                self._board_size = data["board_size"]
                self._square_size = data["square_size"]
                self._t_camera_to_gripper = data["t_camera_to_gripper"]
        except Exception as ex:
            return(str(ex))

    def find_corners(self, mat):
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        gray = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, self._board_size, None)
        if ret:
            corners2 = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)

            output = mat.copy()
            cv2.drawChessboardCorners(output, self._board_size, corners2, ret)

            return RESULTCORNERS(src=mat, dst=output, corners=corners2)
        
        return RESULTCORNERS(src=mat, dst=mat, corners=None)
    
    def remap_and_crop(self, mat):
        if self._mapx is None or self._mapy is None:
            return mat
        
        mat_undistort = cv2.remap(mat, self._mapx, self._mapy, cv2.INTER_LINEAR)

        x, y, w, h = self._roi
        mat_undistort_crop = mat_undistort[y:y+h, x:x+w]
        
        return mat_undistort_crop
    
    def compute_reprojection_error(self, objpoints, imgpoints, rvecs, tvecs, mtx, dist):
        mean_error = 0
        for i in range(len(objpoints)):
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
            mean_error += error
        print( "total error: {}".format(mean_error/len(objpoints)))
        return mean_error

    def create_objp(self):
        objp = np.zeros((self._board_size[0] * self._board_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self._board_size[0], 0:self._board_size[1]].T.reshape(-1, 2)
        objp *= self._square_size
        return objp
    
    def get_camera_pose(self, mat):
        objp = self.create_objp()
        result = self.find_corners(mat)
        
        if result.corners is not None:
            _, rvec, tvec = cv2.solvePnP(objp, result.corners, self._camera_matrix, self._dist_coeffs)
            
            rx, ry, rz = tuple(map(float, rvec))
            tx, ty, tz = tuple(map(float, tvec))

            return (tx, ty, tz, rx, ry, rz)

    def to_homogeneous_matrix(self, rvec, tvec):
        R, _ = cv2.Rodrigues(rvec)  # Chuyển đổi từ vector quay sang ma trận xoay
        T_camera = np.eye(4)
        T_camera[:3, :3] = R
        T_camera[:3, 3] = tvec.ravel()
        return T_camera

    def find_camera_matrix_and_dist_coeffs(self, checkerboard_dir):
        self.startSignal.emit()
        # Chuẩn bị các điểm thế giới 3D (tọa độ góc checkerboard trong không gian thực)
        objp = self.create_objp()

        # Lưu các điểm ảnh và điểm thực
        objpoints = []  # Các điểm thực (world coordinates)
        imgpoints = []  # Các điểm ảnh (image coordinates)

        # Đọc và tìm góc checkerboard trong các ảnh hiệu chỉnh
        paths = self.get_paths(checkerboard_dir)

        if len(paths) < 15:
            msg = "Num of images must be greater than or equal to 15\nPlease take more images."
            self.errorSignal.emit(msg)
            return
             
        for fname in paths:
            img = cv2.imread(fname)
            result = self.find_corners(img)

            if result.corners is not None:
                objpoints.append(objp)
                imgpoints.append(result.corners)
                self.infoSignal.emit(f"Run {fname} : OK")
            else:
                self.infoSignal.emit(f"Run {fname} : NG")
            
            self.stepSignal.emit()

        if len(imgpoints) < 15:
            msg = "Some images not found corners(total images pass < 15)\nPlease take more images."
            self.errorSignal.emit(msg)
            return

        # Hiệu chỉnh camera
        self.infoSignal.emit(f"Wait for computing...")

        image_size = img.shape[:2][::-1]

        ret, self._camera_matrix, self._dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, image_size, None, None
        )

        new_camera_matrix, self._roi = cv2.getOptimalNewCameraMatrix(self._camera_matrix, self._dist_coeffs, image_size, 1, image_size)
        self._mapx, self._mapy = cv2.initUndistortRectifyMap(self._camera_matrix, self._dist_coeffs, None, new_camera_matrix, image_size, cv2.CV_32FC1)

        mean_error = self.compute_reprojection_error(objpoints, imgpoints, rvecs, tvecs, self._camera_matrix, self._dist_coeffs)

        print("Camera Matrix:\n", self._camera_matrix)
        print("Distortion Coefficients:\n", self._dist_coeffs)

        self.stepSignal.emit()
        self.infoSignal.emit(f"Finished")
        self.finishedSignal.emit()
        return RESULTCALIB(camera_matrix=self._camera_matrix, dist_coeffs=self._dist_coeffs, mean_error=mean_error)

    @staticmethod
    def r_to_euler(r):
        rotation = R.from_matrix(r)
        euler_angles = rotation.as_euler('xyz', degrees=True)  # Hoặc 'zyx', tùy thứ tự trục
        return euler_angles
    
    @staticmethod
    def deg2rad(self, d):
        return (d/180) * np.pi
    
    @staticmethod
    def rad2deg(self, r):
        return (r/np.pi) * 180

    @staticmethod
    def create_rotation_matrix(rx, ry, rz):
        rot_matrix, _ = cv2.Rodrigues(np.array([[rx], [ry], [rz]]))
        return rot_matrix
    
    @staticmethod
    def create_translation_matrix(tx, ty, tz):
        return np.array([[tx], [ty], [tz]])
    
    def calibration_handeye(self, poses):
        """
        Performs hand-eye calibration using the given poses.

        Args:
            poses (dict): A dictionary containing camera and robot poses.
                The camera poses should be stored under the key "camera",
                and the robot poses should be stored under the key "robot".

        Returns:
            numpy.ndarray: The transformation matrix from camera to gripper.
                This matrix represents the hand-eye calibration result.
                It can be interpreted as either eye-to-hand or eye-in-hand
                depending on the convention used.

        """
        camera_poses = poses["camera"]
        robot_poses = poses["robot"]

        list_r_gripper_to_base = []
        list_t_gripper_to_base = []

        list_r_target_to_camera = []
        list_t_target_to_camera = []

        for i in range(len(camera_poses)):
            r_gripper_to_base = self.create_rotation_matrix(*robot_poses[i][3:])
            t_gripper_to_base = self.create_translation_matrix(*robot_poses[i][:3])

            r_target_to_camera = self.create_rotation_matrix(*camera_poses[i][3:])
            t_target_to_camera = self.create_translation_matrix(*camera_poses[i][:3])

            list_r_gripper_to_base.append(r_gripper_to_base)
            list_t_gripper_to_base.append(t_gripper_to_base)

            list_r_target_to_camera.append(r_target_to_camera)
            list_t_target_to_camera.append(t_target_to_camera)


        R_cam_to_gripper, t_cam_to_gripper = cv2.calibrateHandEye(
            list_r_gripper_to_base, list_t_gripper_to_base,
            list_r_target_to_camera, list_t_target_to_camera
        )

        T_cam_to_gripper = np.eye(4)
        T_cam_to_gripper[:3, :3] = R_cam_to_gripper
        T_cam_to_gripper[:3, 3] = t_cam_to_gripper.ravel()

        self._t_camera_to_gripper = T_cam_to_gripper

        return T_cam_to_gripper
    
    def convert_to_gripper_coord(self, im_pos, z_depth=1.):
        """
        Converts the position in the image to the corresponding gripper pose.

        Args:
            im_pos (tuple): The position (x, y) in the image.
            z_depth (float, optional): The depth of the object. Defaults to 1..

        Returns:
            numpy.ndarray: The position in the base gripper coord system.
        """
        x, y = im_pos

        im_coord = np.array([x, y, 1])

        camera_coord = z_depth * np.dot(np.linalg.inv(self._camera_matrix), im_coord)

        camera_pose = np.append(camera_coord, 1)

        gripper_coord = np.dot(self._t_camera_to_gripper, camera_pose)[:3]

        return gripper_coord
    
    def convert_to_base_coord(self, robot_pose, im_pos, z_depth=1.):
        """
        Converts the image position to the base coordinate system.

        Parameters:
        - robot_pose (numpy.ndarray): The pose of the robot in the base coordinate system.
        - im_pos (numpy.ndarray): The image position in the image coordinate system.
        - z_depth (float): The depth of object in the camera coordinate system.

        Returns:
        - numpy.ndarray: The position in the base coordinate coord system.
        """
        gripper_coord = self.convert_to_gripper_coord(im_pos, z_depth)
        gripper_pose = np.append(gripper_coord, 1)
        base_coord = np.dot(robot_pose, gripper_pose)[:3]
        return base_coord
    
    @property
    def t_camera_to_gripper(self):
        return self._t_camera_to_gripper
    
    def __rep__(self):
        return f"CalibUtils(board_size={self._board_size}, square_size={self._square_size})"


if __name__ == "__main__":
    CalibUtils.find_camera_matrix_and_dist_coeffs()
