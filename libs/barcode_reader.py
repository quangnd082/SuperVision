from pyzbar.pyzbar import decode, Decoded, Rect, ZBarSymbol
from pylibdmtx.pylibdmtx import decode as dmtx
import cv2
import json
from collections import namedtuple

# from pyzxing import BarCodeReader

# zxing_reader = BarCodeReader()

# def read_barcode_by_zxing(mat):
#     res = zxing_reader.decode_array(mat)
#     return res

# list_symbols = sorted(ZBarSymbol.__members__.keys())

# s = ZBarSymbol.CODE39

def is_color_image(mat):
    if len(mat.shape) == 3:
        return True
    else:
        return False

def read_barcode(mat):
    if is_color_image(mat):
        gray = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
        res = decode(gray)
    else:
        res = decode(mat)
    return res

def read_barcode_(path):
    mat = cv2.imread(path)
    return read_barcode(mat)

def read_matrixcode(mat):
    if is_color_image(mat):
        gray = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
        res = dmtx(gray, max_count=1)
    else:
        res = dmtx(mat, max_count=1)
    return res

def read_matrixcode_(path):
    mat = cv2.imread(path)
    return read_matrixcode(mat)

if __name__ == "__main__":
    # from argparse import ArgumentParser
    # parse = ArgumentParser(description="Barcode Reader")
    # parse.add_argument('input')

    # args = parse.parse_args()

    # path = args.input
    # code = read_matrixcode_(path)

    path = "barcode.bmp"
    mat = cv2.imread(path)

    ret = read_barcode(mat)
    print("ZBAR: ", ret)

    # ret = read_barcode_by_zxing(mat)
    # print("ZXING: ", ret)
