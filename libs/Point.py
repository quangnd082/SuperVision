import math
import cv2
from abc import ABC, abstractmethod
import numpy as np


class Point:

    def __init__(self, x, y):
        self.__x = x
        self.__y = y

    def distance(self, other):
        distance_x = (self.__x - other.__x)**2
        distance_y = (self.__y - other.__y)**2
        return math.sqrt(distance_x + distance_y)
    
    @property
    def get_point(self):
        return self.__x, self.__y

    @property
    def point_x(self):
        return self.__x

    @property
    def point_y(self):
        return self.__y

class Shape(ABC):

    @abstractmethod
    def translate(self, dx, dy):
        pass

    @abstractmethod
    def get_perimeter(self):
        pass

    @abstractmethod
    def get_area(self):
        pass

    @abstractmethod
    def get_centroid(self):
        pass

class Triangle(Shape, ABC):
    def __init__(self, A: Point, B: Point, C: Point):
        self.__A = A
        self.__B = B
        self.__C = C

    @property
    def get_point(self):
        return ((self.__A.point_x, self.__A.point_y),
                (self.__B.point_x, self.__B.point_y),
                (self.__C.point_x, self.__C.point_y))

    def translate(self, dx, dy):
        self.__A = Point(self.__A.point_x + dx, self.__A.point_y + dy)
        self.__B = Point(self.__B.point_x + dx, self.__B.point_y + dy)
        self.__C = Point(self.__C.point_x + dx, self.__C.point_y + dy)

    def get_perimeter(self):
        return self.__A.distance(self.__B) + self.__B.distance(self.__C) + self.__C.distance(self.__A)

    def get_area(self):
        AB = self.__A.distance(self.__B)
        BC = self.__B.distance(self.__C)
        AC = self.__C.distance(self.__A)
        P = float((AB + BC + AC) / 2)
        return math.sqrt(P * (P - AB) * (P - BC) * (P - AC))

    def get_centroid(self):
        centroid_x = (self.__A.point_x + self.__B.point_x + self.__C.point_x) / 3
        centroid_y = (self.__A.point_y + self.__B.point_y + self.__C.point_y) / 3
        return centroid_x, centroid_y

class Rectangle(Shape, ABC):

    def __init__(self, top_left: Point, bottom_right: Point):
        self.__A = top_left
        self.__C = bottom_right
        self.__B = Point(bottom_right.point_x, top_left.point_y)
        self.__D = Point(top_left.point_x, bottom_right.point_y)

    @property
    def get_point(self):
        return ((self.__A.point_x, self.__A.point_y),
                (self.__B.point_x, self.__B.point_y),
                (self.__C.point_x, self.__C.point_y),
                (self.__D.point_x, self.__D.point_y))

    def translate(self, dx, dy):
        self.__A = Point(self.__A.point_x + dx, self.__A.point_y + dy)
        self.__B = Point(self.__B.point_x + dx, self.__B.point_y + dy)
        self.__C = Point(self.__C.point_x + dx, self.__C.point_y + dy)
        self.__D = Point(self.__D.point_x + dx, self.__D.point_y + dy)

    def get_perimeter(self):
        return (self.__A.distance(self.__B)
                + self.__B.distance(self.__C)
                + self.__C.distance(self.__D)
                + self.__D.distance(self.__A))

    def get_area(self):
        return self.__A.distance(self.__B) * self.__B.distance(self.__C)

    def get_centroid(self):
        return (self.__A.point_x + self.__C.point_x) / 2, (self.__A.point_y + self.__C.point_y) / 2

class Circle(Shape, ABC):

    def __init__(self, center: Point, radius: float):
        self.__A = center
        self.__rad = radius

    @property
    def get_point(self):
        return self.__A.point_x, self.__A.point_y

    def translate(self, dx, dy):
        self.__A = Point(self.__A.point_x + dx, self.__A.point_y + dy)

    def get_perimeter(self):
        return self.__rad * 2 * math.pi

    def get_area(self):
        return self.__rad * self.__rad * math.pi

    def get_centroid(self):
        return self.__A.point_x, self.__A.point_y

if __name__ == '__main__':
    img = np.zeros([500,500,3])
    point_1 = Point(3, 6)
    point_2 = Point(5, 6)
    point_3 = Point(70, 90)
    rec_1 = Rectangle(point_1, point_3)
    print(point_1.distance(point_2))
    # img_rec = cv2.rectangle(img, rec_1.get_point[0], rec_1.get_point[2], thickness=5, color=(0, 255, 0))
    # rec_1.translate(100, 200)
    # img_rec = cv2.rectangle(img, rec_1.get_point[0], rec_1.get_point[2], thickness=5, color=(0, 255, 0))
    # cv2.imshow('Trung', img_rec)
    # if cv2.waitKey(0) & 0xff == 27:
    #     cv2.destroyAllWindows()
