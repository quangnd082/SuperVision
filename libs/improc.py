from collections import namedtuple
import cv2
import numpy as np
import time

import torch.utils
import torch.utils.data

from vision_dnn import YoloInference, DNNRESULT, plot_results, plot_one_box
from logger import Logger
improc_logger = Logger("improclog", "log/improclog.log", maxBytes=1e5)

from torchvision import transforms
import torch

from constant import *

from vae_model import vae_loss
from skimage.metrics import structural_similarity as ssim
from glob import glob
import os
from PIL import Image
from vae_model import ConvVAE
from resnet18_vae_model import ResnetVAE

RESULT = namedtuple("result", ["src", "dst", "ret", "annotations",
                               "timecheck", "error", "config"],
                    defaults=7*[None])


def bndbox_to_bbox(box):
    if box is None:
        return
    x, y, w, h = box
    return [x, y, x+w, y+h]

def bbox_to_rotatedrect(box):
    if box is None:
        return
    x1, y1, x2, y2 = box
    cx, cy = (x1+x2)/2, (y1+y2)/2
    w, h = x2-x1, y2-y1
    r = ((cx, cy), (float(w), float(h)), 0.)
    return r

def bndbox_to_rotatedrect(box):
    if box is None:
        return
    x, y, w, h = box
    cx, cy = x+w/2, y+h/2
    r = ((cx, cy), (float(w), float(h)), 0.)
    return r

def resize_image(mat, size=1280):
    return mat

def load_model(model_path, label_path):
    return YoloInference(model=model_path, label=label_path)

def process_check_doc(model: YoloInference, mat: np.ndarray, config: dict=None):
    time_check = time.strftime("%Y/%M/%d %H:%M:%S")
    
    try:
        results = model.detect(mat)
        #
        dst = mat.copy()
        
        annos = []
        
        r: DNNRESULT = None
        for r in results:
            annos.append(r.boxStr)
            box = r.box
            plot_one_box(box, dst, CV_GREEN)
        
        annos = "\n".join(annos)
                
        return RESULT(
            src=mat, dst=dst, 
            timecheck=time_check,
            ret = RESULT_PASS,
            config=config,
            annotations=annos
        )
        
    except Exception as ex:
        return RESULT(
            src=mat, dst=mat, 
            timecheck=time_check,
            ret = RESULT_FAIL,
            config=config,
            error=str(ex),
            annotations=""
        )
    

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from glob import glob

    model_doc: YoloInference = load_model("res/model/YOLO/best_doc.pt", "res/model/YOLO/classes_doc.txt")
    if model_doc.model is not None:
        print("Load model doc success")
    
    
    model_ngang: YoloInference = load_model("res/model/YOLO/best_ngang.pt", "res/model/YOLO/classes_ngang.txt")
    if model_ngang.model is not None:
        print("Load model ngang success")
        
    
    paths = glob(r"C:\Users\DTC\Desktop\PBA\Data\Data_ngang\Test\*.jpg")
    mat = cv2.imread(paths[0])
    
    label_map = model_ngang.label_map
    
    results = model_ngang.detect(mat)
    r: DNNRESULT = None
    for r in results:
        box = r.box
        plot_one_box(box, mat, CV_GREEN)
    cv2.namedWindow('Output', cv2.WINDOW_FREERATIO)    
    cv2.imshow("Output", mat)
    cv2.waitKey()
    






