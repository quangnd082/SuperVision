import cv2
import numpy as np
import random
import os
import time
from collections import namedtuple, deque

import ultralytics
from ultralytics import YOLO
from ultralytics.utils import ops
import openvino as ov
import torch
import yaml

from PIL import Image

# from prepare_data import preprocess_image

# import pycoral
# from pycoral.adapters import common
# from pycoral.adapters.detect import get_objects
# from pycoral.utils.dataset import read_label_file
# from pycoral.utils.edgetpu import make_interpreter
# from pycoral.utils.edgetpu import run_inference


# print("Ultralytics: ", ultralytics.__version__)
# print("Torch: ", torch.__version__)
# print("OpenVino: ", ov.__version__)
# print("OpenCV: ", cv2.__version__)
# print("Pycoral: ", pycoral.__version__)

from scipy import special

# DNNRESULT = namedtuple("DetResult", 
#                        ["class_index", "box", "mask", "conf", "rect"], 
#                        defaults=5*[None])

class DNNRESULT:
    def __init__(self, class_index=0, box=None, 
                 mask=None, conf=None, rect=None, imgsz=None) -> None:
        '''
        @class_index: class index of object
        @box: bounding box (x1, y1, x2, y2) of object
        @mask: polygon around object (segmention key point)
        @conf: confidence
        @rect: minAreaRect of mask
        @imgsz: tuple size (width, height) of image 
        '''
        self._class_index = class_index
        self._box = box
        self._mask = mask
        self._conf = conf
        self._rect = rect
        self._imgsz = imgsz
    
    @property
    def class_index(self):
        return self._class_index

    @property
    def box(self):
        return self._box

    @property
    def mask(self):
        return self._mask

    @property
    def conf(self):
        return self._conf
    
    @property
    def rect(self):
        return self._rect
    
    @property
    def imgsz(self):
        return self._imgsz
    
    @property
    def boxStr(self):
        '''
        return bndbox coordinates as yolo format
        '''
        im_w, im_h = self.imgsz
        x1, y1, x2, y2 = self.box

        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        w = x2 - x1
        h = y2 - y1

        cx /= im_w
        cy /= im_h
        w /= im_w
        h /= im_h

        line = f"{self.class_index} {round(cx, 5)} {round(cy, 5)} {round(w, 5)} {round(h, 5)}"
        return line
    
    @property
    def maskStr(self):
        '''
        return polygon coordinates as yolo format
        '''
        if self.mask is None:
            return ""
        
        im_w, im_h = self.imgsz
        line = f"{self.class_index}"

        for pos in self.mask:
            x, y = pos

            x /= im_w
            y /= im_h

            line += f" {round(x, 5)} {round(y, 5)}"
        return line

def plot_text(text, img:np.ndarray, org:tuple=None, color:tuple=None, line_thickness=5):
    """
    Helper function for drawing single min area rect on image
    Parameters:
        text : string
        img (np.ndarray): input image
    """
    color = color or (255, 255, 255)
    org = org or (10, 10)
    tl = line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1  # line/font thickness
    tf = max(tl -1, 1)
    
    cv2.putText(img, text, org, 0, tl / 3, color, tf, cv2.LINE_AA)
    return img
    pass

def plot_one_min_rect(rect, img:np.ndarray, color:tuple=None, line_thickness=5):
    """
    Helper function for drawing single min area rect on image
    Parameters:
        rect :result of cv2.minAreaRect
        img (np.ndarray): input image
    """
    color = color or (255, 255, 255)
    tl = line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1  # line/font thickness
    box = cv2.boxPoints(rect).astype(np.uint0)
    cv2.drawContours(img, [box], 0, color, tl)
    return img
    pass

def plot_one_box(box:np.ndarray = None, img:np.ndarray = None, color=None, mask:np.ndarray = None,
                label:str = None, line_thickness:int = 5):
        """
        Helper function for drawing single bounding box on image
        Parameters:
            x (np.ndarray): bounding box coordinates in format [x1, y1, x2, y2]
            img (no.ndarray): input image
            color (Tuple[int, int, int], *optional*, None): color in BGR format for drawing box, if not specified will be selected randomly
            mask (np.ndarray, *optional*, None): instance segmentation mask polygon in format [N, 2], where N - number of points in contour, if not provided, only box will be drawn
            label (str, *optonal*, None): box label string, if not provided will not be provided as drowing result
            line_thickness (int, *optional*, 5): thickness for box drawing lines
        """

        if box is None:
            return img
        
        # Plots one bounding box on image img
        tl = line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1  # line/font thickness
        fs = tl / 2.5
        if color is None:
            color = [random.randint(0, 255) for _ in range(3)]
        
        c1, c2 = (int(box[0]), int(box[1])), (int(box[2]), int(box[3]))
        cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
        if label:
            tf = max(tl - 1, 1)  # font thickness
            t_size = cv2.getTextSize(label, 0, fontScale=fs, thickness=tf)[0]

            if c1[1] > t_size[1] + 3:
                c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
                org = (c1[0], c1[1] -2)
            else:
                c2 = c1[0] + t_size[0], c1[1] + t_size[1] + 3
                org = (c1[0], c1[1] + t_size[1] + 2)

            cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
            text_color = (0, 0, 255 - color[2])
            cv2.putText(img, label, org, 0, fs, text_color, thickness=tf, lineType=cv2.LINE_AA)
        if mask is not None:
            image_with_mask = img.copy()
            cv2.fillPoly(image_with_mask, pts=[mask], color=color)
            img = cv2.addWeighted(img, 0.5, image_with_mask, 0.5, 1)
        return img

def plot_results(results, img:np.ndarray, label_map=None, colors=None, lw=5):
        """
        Helper function for drawing bounding boxes on image
        Parameters:
            results: list DNNRESULT("class_index", "box", "mask", "conf")
            source_image (np.ndarray): input image for drawing
            label_map; (Dict[int, str]): label_id to class name mapping
        Returns:

        """
        result:DNNRESULT = None
        for result in results:
            box = result.box
            mask = result.mask
            rect = result.rect
            cls_index = result.class_index
            conf = result.conf

            h, w = img.shape[:2]

            if label_map is not None:
                label = f'{label_map[cls_index]}, {conf:.2f}'
            else:
                label = f"{conf:.2f}"

            if colors is not None:
                color = colors[cls_index]
            else:
                random.seed(42)
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

            img = plot_one_box(box, img, 
                                mask=mask, 
                                label=label, 
                                color=color, line_thickness=lw)
            
            color = (0, 255, 255)
            # if mask is not None:
            #     plot_one_min_rect(rect, img, 
            #                     color=color, 
            #                     line_thickness=1)
        return img


# def softmax(x):
#     return np.exp(x)/sum(np.exp(x))

def load_labels(label_path:str):
    label_map = {}
    try:
        if label_path.endswith('.yaml'):
            with open(label_path, 'r', encoding="utf-8") as file:
                data = yaml.safe_load(file)
                label_map = data['names']

        elif label_path.endswith('.txt'):
            with open(label_path, 'r', encoding="utf-8") as file:
                lines = file.readlines()
                label_map = {}
                for i, line in enumerate(lines):
                    line = line.strip("\r\n").split(" ")
                    if len(line) > 1:
                        if line[0].isdigit():
                            label_map[int(line[0])] = " ".join(line[1:])
                        else:
                            label_map[i] = " ".join(line)    
                    else:
                        label_map[i] = " ".join(line)
    except:
        pass
    
    return label_map
    

class YoloInference():
    def __init__(self, model, label) -> None:
        self.model = YoloInference.load_model(model)
        self.label_map = load_labels(label)
        np.random.seed(0)
        self.color_map = np.random.uniform(0, 255, size=(len(self.label_map), 3))
    
    def load_model(model_path):
        start_time = time.perf_counter()
        try:
            model = YOLO(model_path)
            model.predict(np.zeros((640, 640, 3), dtype=np.uint8))
            end_time = time.perf_counter()
            msg = f"- Loading the network took {end_time-start_time:.2f} seconds."
            print(msg)
        except Exception as ex:
            print(str(ex))
            model = None
        return model 

    def detect(self, mat, conf=0.25, imgsz=640, approxy_contour=False, epsilon=0.001):
        t0 = time.time()
        result = self.model.predict(mat, conf=conf, imgsz=imgsz)[0]
        dt = time.time() - t0
        
        boxes = result.boxes
        masks = result.masks
        
        n_points = n_bndBox = n_class_index = n_conf = []

        if masks is not None:
            n_points = masks.xy

        if len(boxes):
            n_bndBox = boxes.xyxy.cpu().numpy().astype(np.uint0)
            n_class_index = list(map(int, boxes.cls))
            n_conf = list(map(float, boxes.conf))

        results = []
        for i in range(len(n_bndBox)):
            mask = n_points[i].astype(np.uint0) if masks is not None else None
            # 
            if approxy_contour and mask is not None:
                length = epsilon*cv2.arcLength(mask, True)
                mask = cv2.approxPolyDP(mask, length, True)
            # 
            rect = cv2.minAreaRect(mask) if mask is not None else None

            im_size = mat.shape[:2][::-1]

            results.append(DNNRESULT(
                class_index=n_class_index[i],
                box=n_bndBox[i],
                mask=mask,
                conf=n_conf[i],
                rect=rect,
                imgsz=im_size
            ))

        results = sorted(results, key=lambda x: x.conf, reverse=True)
        # 6 set on jig
        # if len(results) > 6:
        #     results = results[:6]
        return results
    
    def detect_multi(self, mats, conf=0.25, imgsz=640, 
                     approxy_contour=False, epsilon=0.001):
        t0 = time.time()
        results = self.model.predict(mats, conf=conf, imgsz=imgsz)
        dt = time.time() - t0
        
        _results = []
        for i, result in enumerate(results):
            boxes = result.boxes
            masks = result.masks
            
            n_points = n_bndBox = n_class_index = n_conf = []

            if masks is not None:
                n_points = masks.xy

            if len(boxes):
                n_bndBox = boxes.xyxy.cpu().numpy().astype(np.uint0)
                n_class_index = list(map(int, boxes.cls))
                n_conf = list(map(float, boxes.conf))

            _preds = []
            for i in range(len(n_bndBox)):
                mask = n_points[i].astype(np.uint0) if masks is not None else None
                # 
                if approxy_contour and mask is not None:
                    length = epsilon*cv2.arcLength(mask, True)
                    mask = cv2.approxPolyDP(mask, length, True)
                # 
                rect = cv2.minAreaRect(mask) if mask is not None else None

                im_size = mats[i].shape[:2][::-1]

                _preds.append(DNNRESULT(
                    class_index=n_class_index[i],
                    box=n_bndBox[i],
                    mask=mask,
                    conf=n_conf[i],
                    rect=rect,
                    imgsz=im_size
                ))
            
            _results.append(_preds)

        return _results

    def classify(self, mat, conf=0.2, imgsz=640):
        result = self.model.predict(mat, conf=conf, imgsz=imgsz)[0]
        probs = result.probs
        return DNNRESULT(
            class_index=probs.top1,
            conf=float(probs.top1conf)
        )
    
class OVInference():
    def __init__(self, model, label) -> None:
        self.model = OVInference.load_model(model)
        self.label_map = load_labels(label)
        np.random.seed(0)
        self.color_map = np.random.uniform(0, 255, size=(len(self.label_map), 3))

    def load_model(model_path, device_name='GPU'):
        dir_name = os.path.dirname(model_path)
        cache_path = f"{dir_name}/model_cache"
        os.makedirs(cache_path, exist_ok=True)
        # Enable caching for OpenVINO Runtime, and set LATECY performance mode
        config_dict = {"CACHE_DIR": cache_path,
                    ov.properties.hint.performance_mode(): ov.properties.hint.PerformanceMode.LATENCY}
        
        start_time = time.perf_counter()
        core = ov.Core()
        model = core.read_model(model=model_path)
        compiled_model = core.compile_model(model=model, device_name=device_name, config=config_dict)
        x = np.zeros((1, 3, 640, 640), dtype=np.uint8)
        x = torch.from_numpy(x)
        compiled_model(x)
        end_time = time.perf_counter()
        
        execution_devices = compiled_model.get_property("EXECUTION_DEVICES")
        performance_hint = compiled_model.get_property("PERFORMANCE_HINT")
        print('- excution devices: ', execution_devices)
        print('- performance hint: ', performance_hint)
        
        print(f"- Loading the network to the {device_name} device took {end_time-start_time:.2f} seconds.")
        return compiled_model
    
    def letterbox(img: np.ndarray, new_shape=(640, 640), color=(114, 114, 114), 
                  auto:bool = False, scale_fill:bool = False, scaleup:bool = False, stride:int = 32):
        """
        Resize image and padding for detection. Takes image as input,
        resizes image to fit into new shape with saving original aspect ratio and pads it to meet stride-multiple constraints

        Parameters:
        img (np.ndarray): image for preprocessing
        new_shape (Tuple(int, int)): image size after preprocessing in format [height, width]
        color (Tuple(int, int, int)): color for filling padded area
        auto (bool): use dynamic input size, only padding for stride constrins applied
        scale_fill (bool): scale image to fill new_shape
        scaleup (bool): allow scale image if it is lower then desired input size, can affect model accuracy
        stride (int): input padding stride
        Returns:
        img (np.ndarray): image after preprocessing
        ratio (Tuple(float, float)): hight and width scaling ratio
        padding_size (Tuple(int, int)): height and width padding size


        """
        # Resize and pad image while meeting stride-multiple constraints
        shape = img.shape[:2]  # current shape [height, width]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)

        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        if not scaleup:  # only scale down, do not scale up (for better test mAP)
            r = min(r, 1.0)

        # Compute padding
        ratio = r, r  # width, height ratios
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
        if auto:  # minimum rectangle
            dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
        elif scale_fill:  # stretch
            dw, dh = 0.0, 0.0
            new_unpad = (new_shape[1], new_shape[0])
            ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]  # width, height ratios

        dw /= 2  # divide padding into 2 sides
        dh /= 2

        if shape[::-1] != new_unpad:  # resize
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
        return img, ratio, (dw, dh)

    def preprocess_detect_image(img0: np.ndarray, input_size:tuple):
        """
        Preprocess image according to YOLOv8 input requirements.
        Takes image in np.array format, resizes it to specific size using letterbox resize and changes data layout from HWC to CHW.

        Parameters:
        img0 (np.ndarray): image for preprocessing
        input_size(tuple): height, width for image input
        Returns:
        img (np.ndarray): image after preprocessing
        """
        # resize
        img = OVInference.letterbox(img0, new_shape=input_size)[0]

        # Convert HWC to CHW
        img = img.transpose(2, 0, 1)
        img = np.ascontiguousarray(img)
        return img

    def image_to_tensor(image:np.ndarray):
        """
        Preprocess image according to YOLOv8 input requirements.
        Takes image in np.array format, resizes it to specific size using letterbox resize and changes data layout from HWC to CHW.

        Parameters:
        img (np.ndarray): image for preprocessing
        Returns:
        input_tensor (np.ndarray): input tensor in NCHW format with float32 values in [0, 1] range
        """
        input_tensor = image.astype(np.float32)  # uint8 to fp32
        input_tensor /= 255.0  # 0 - 255 to 0.0 - 1.0

        # add batch dimension
        if input_tensor.ndim == 3:
            input_tensor = np.expand_dims(input_tensor, 0)
        return input_tensor

    def postprocess(
            pred_boxes:np.ndarray,
            input_hw,
            nc:int,
            orig_img:np.ndarray,
            min_conf_threshold:float = 0.25,
            nms_iou_threshold:float = 0.7,
            agnosting_nms:bool = False,
            max_detections:int = 300,
            pred_masks:np.ndarray = None,
            retina_mask:bool = False
        ):
        """
        YOLOv8 model postprocessing function. Applied non maximum supression algorithm to detections and rescale boxes to original image size
        Parameters:
            pred_boxes (np.ndarray): model output prediction boxes
            input_hw (np.ndarray): preprocessed image
            orig_image (np.ndarray): image before preprocessing
            min_conf_threshold (float, *optional*, 0.25): minimal accepted confidence for object filtering
            nms_iou_threshold (float, *optional*, 0.45): minimal overlap score for removing objects duplicates in NMS
            agnostic_nms (bool, *optiona*, False): apply class agnostinc NMS approach or not
            max_detections (int, *optional*, 300):  maximum detections after NMS
            pred_masks (np.ndarray, *optional*, None): model ooutput prediction masks, if not provided only boxes will be postprocessed
            retina_mask (bool, *optional*, False): retina mask postprocessing instead of native decoding
        Returns:
        pred (List[Dict[str, np.ndarray]]): list of dictionary with det - detected boxes in format [x1, y1, x2, y2, score, label] and segment - segmentation polygons for each element in batch
        """
        nms_kwargs = {"agnostic": agnosting_nms, "max_det":max_detections}

        try:
            scale_segments = ops.scale_segments
        except AttributeError:
            scale_segments = ops.scale_coords

        # if pred_masks is not None:
        #     nms_kwargs["nm"] = 32
        preds = ops.non_max_suppression(
            torch.from_numpy(pred_boxes),
            min_conf_threshold,
            nms_iou_threshold,
            nc=nc,
            **nms_kwargs
        )
        results = []
        proto = torch.from_numpy(pred_masks) if pred_masks is not None else None

        for i, pred in enumerate(preds):
            shape = orig_img[i].shape if isinstance(orig_img, list) else orig_img.shape
            if not len(pred):
                results.append({"det": [], "segment": []})
                continue
            if proto is None:
                pred[:, :4] = ops.scale_boxes(input_hw, pred[:, :4], shape).round()
                results.append({"det": pred})
                continue
            if retina_mask:
                pred[:, :4] = ops.scale_boxes(input_hw, pred[:, :4], shape).round()
                masks = ops.process_mask_native(proto[i], pred[:, 6:], pred[:, :4], shape[:2])  # HWC
                segments = [scale_segments(input_hw, x, shape, normalize=False) for x in ops.masks2segments(masks)]
            else:
                masks = ops.process_mask(proto[i], pred[:, 6:], pred[:, :4], input_hw, upsample=True)
                pred[:, :4] = ops.scale_boxes(input_hw, pred[:, :4], shape).round()
                segments = [scale_segments(input_hw, x, shape, normalize=False) for x in ops.masks2segments(masks)]
            results.append({"det": pred[:, :6].numpy(), "segment": segments})
        return results

    def detect(self, mat, nc=1, conf=0.25, imgsz=640, approxy_contour=False, epsilon=0.001):
        # input_size = OVInference.get_input_size(model)
        preprocessed_image = OVInference.preprocess_detect_image(mat, imgsz)
        input_tensor = OVInference.image_to_tensor(preprocessed_image)
        result = self.model(input_tensor)
        boxes = result[0]

        num_outputs = len(self.model.outputs)
        masks = None
        if num_outputs > 1:
            masks = result[1]
        input_hw = input_tensor.shape[2:]
        detections = OVInference.postprocess(pred_boxes=boxes, input_hw=input_hw, 
                                            nc=nc, orig_img=mat, pred_masks=masks,
                                            min_conf_threshold=conf)[0]

        boxes = detections["det"]
        masks = detections.get("segment", None)

        results = []
        for i in range(len(boxes)):
            # 
            class_index = int(boxes[i][5])
            mask = None if masks is None else masks[i].astype(np.uint0)
            if class_index == PHONE_CLASS_INDEX:
                if approxy_contour and mask is not None:
                    length = epsilon*cv2.arcLength(mask, True)
                    mask = cv2.approxPolyDP(mask, length, True)
            # 
            rect = cv2.minAreaRect(mask) if mask is not None else None
            results.append(DNNRESULT(
                class_index=int(boxes[i][5]),
                box=boxes[i][:4],
                mask=mask,
                rect=rect,
                conf=float(boxes[i][4])
            ))

        results = sorted(results, key=lambda x: x.conf, reverse=True)
        # 6 set on jig
        # if len(results) > 6:
        #     results = results[:6]
        return results
    

    def get_input_size(model:ov.CompiledModel):
        s = model.input(0).get_shape()
        return (s[2], s[3]) 

    def classify(self, mat, conf=0.25, imgsz=640):
        # input_size = OVInference.get_input_size(model)
        input_tensor = OVInference.preprocess_classify_image(mat, imgsz)
        result_infer = self.model([input_tensor])[0][0]
        cls_index = int(np.argmax(result_infer))
        conf = result_infer[cls_index]
        return DNNRESULT(
            class_index=cls_index,
            conf=conf
        )
    
    def preprocess_classify_image(image, input_size=(224, 224), norm=True):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, input_size)
        if norm:
            x = OVInference.normalize(image)
            x = np.transpose(x , (2, 0, 1))
            tensor = np.expand_dims(x, 0)
            return tensor
        else:
            return image

    def normalize(image: np.ndarray) -> np.ndarray:
        """
        Normalize the image to the given mean and standard deviation
        for CityScapes models.
        """
        image = image.astype(np.float32)
        mean = (0.485, 0.456, 0.406)
        std = (0.229, 0.224, 0.225)
        image /= 255.0
        image -= mean
        image /= std
        return image


def test_classify(model_path, label_path, model:YoloInference):
    # path_to_model = r'E:\Github\yolov8-infer\Test open vino\pretrained\yolov8n-cls.pt'
    model = model(model_path, label_path)
    # camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    # camera.set(cv2.CAP_PROP_SETTINGS, 1)

    img_dir = r'E:\Github\yolov8-infer\Test open vino\images'
    paths = [os.path.join(img_dir, x) for x in os.listdir(img_dir)]
    
    cv2.namedWindow("Classification", cv2.WINDOW_FREERATIO)
    # while True:
    for path in paths:
        # ret, mat = camera.read()
        mat = cv2.imread(path)
        # if not ret:
        #     break
        result:DNNRESULT = model.classify(mat)
        
        cls_index = result.class_index
        conf = result.conf

        label = model.label_map[cls_index]
        text = f"{label}, score: {conf: .2f}"

        plot_text(text, mat, color=(255, 0, 0), line_thickness=1)

        cv2.imshow("Classification", mat)
        if cv2.waitKey() == 27:
            break

def test_detect_on_folder(model_path, label_path, img_dir, 
                          model=YoloInference, imgsz=640,
                          output_dir = ""):

    model = model(model_path, label_path)

    nc = len(model.label_map)
    colors = np.random.uniform(0, 255, size=(nc, 3))

    paths = [os.path.join(img_dir, x) for x in os.listdir(img_dir)]

    inference_times = deque()
    fps = 0.
    
    cv2.namedWindow("Segmention", cv2.WINDOW_FREERATIO)

    for p in paths:
        mat = cv2.imread(p)
        if mat is None:
            continue

        t0 = time.perf_counter()

        results = model.detect(mat, nc=nc, imgsz=imgsz, approxy_contour=True)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            for i, res in enumerate(results):
                x1, y1 , x2, y2 = res.box
                m = mat[y1 : y2, x1 : x2]

                base = os.path.splitext(os.path.basename(p))[0]
                s_path = os.path.join(output_dir, f"{base}_{i}.jpg")
                cv2.imwrite(s_path, m)
                print("saved %s" % s_path)

        dt = time.perf_counter() - t0
        inference_times.append(dt)

        if len(inference_times) > 200:
            inference_times.popleft()
        
        fps = 1 / np.mean(inference_times)

        res:DNNRESULT = None

        mat = plot_results(results, mat, label_map=model.label_map, colors=model.color_map)
        
        # for res in results:
        #     mask = res.mask
        #     if mask is not None:
        #         plot_one_min_rect(res.rect, mat, color=(255, 0, 0), line_thickness=1)

        plot_text(f"FPS: {fps:.2f}", mat, org=(20, 50), line_thickness=2)

        cv2.imshow("Segmention", mat)
        if cv2.waitKey(100) == 27:
            break

def test_detect_on_camera(model_path, label_path, model=YoloInference, imgsz=640):

    model = model(model_path, label_path)

    nc = len(model.label_map)
    colors = np.random.uniform(0, 255, size=(nc, 3))

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_SETTINGS, 1)

    inference_times = deque()
    fps = 0.
    
    cv2.namedWindow("Segmention", cv2.WINDOW_FREERATIO)
    while True:
        ret, mat = camera.read()
        if not ret:
            break

        t0 = time.perf_counter()

        results = model.detect(mat, nc=nc, imgsz=imgsz, approxy_contour=True)

        dt = time.perf_counter() - t0
        inference_times.append(dt)

        if len(inference_times) > 200:
            inference_times.popleft()
        
        fps = 1 / np.mean(inference_times)

        res:DNNRESULT = None

        mat = plot_results(results, mat, label_map=model.label_map, colors=colors)
        
        for res in results:
            mask = res.mask
            if mask is not None:
                plot_one_min_rect(res.rect, mat, color=(255, 0, 0), line_thickness=1)

        plot_text(f"FPS: {fps:.2f}", mat, org=(20, 50), line_thickness=2)

        cv2.imshow("Segmention", mat)
        if cv2.waitKey(1) == 27:
            break
if __name__ == "__main__":
    test_detect_on_camera(
        model_path=r"E:\Data\pretrained\yolov8\yolov8n-seg.pt",
        label_path=r"E:\Data\pretrained\yolov8\coco.yaml",
        model=YoloInference
    )
    # test_detect_on_folder(model_path=r"E:\Data\PhoneSet\8s_cam_and_phone_last.pt", 
    #             label_path='resources/static/yolo/cam_phone_labels.txt', 
    #             img_dir=r"E:\Data\PhoneSet\Images\EXAMPLE_17102023\2023-10-17\OK",
    #             model=YoloInference,
    #             imgsz=640)
    
    # test_detect_on_folder(model_path=r'E:\Download\PhoneSetImage\640x426_8n_best_openvino_model\640x426_8n_best.xml', 
    #             label_path=r'E:\Download\PhoneSetImage\labels.txt', 
    #             img_dir=r"E:\Download\PhoneSetImage\valid\images",
    #             model=OVInference,
    #             imgsz=640)
    pass
