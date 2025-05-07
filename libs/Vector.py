import math
import cv2
import numpy as np
from Point import Point

class Vector:
    def __init__(self, x: Point, y: Point):
        self.x = y.point_x - x.point_x
        self.y = y.point_y - x.point_y
    
    def lenght(self):
        pass
    
    def angle(self, other):
        cos_angle = (self.x*other.x + self.y*other.y)/(math.sqrt(self.x**2 + self.y**2) * math.sqrt(other.x**2 + other.y**2))
        angle_radian = math.acos(cos_angle)
        angle_degree = math.degrees(angle_radian)
        cross = self.x*other.y - self.y*other.x
        return angle_degree if cross >= 0 else -angle_degree


if __name__ == '__main__':
    vector1 = Vector(Point(1, 2), Point(5, 6))
    vector2 = Vector(Point(-1,3), Point(4, 7))
    print(vector1.angle(vector2))
    