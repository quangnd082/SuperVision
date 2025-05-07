from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional


class Step(Enum):
    SCANNER = "STEP_SCANNER"
    READ_TRIGGER = "STEP_READ_TRIGGER"
    PREPROCESS = "STEP_PREPROCESS"
    ON_LIGHTING = "STEP_ON_LIGHTING"
    OFF_LIGHTING = "STEP_OFF_LIGHTING"
    VISION_DETECTION = "STEP_VISION_DETECTION"  # Đã sửa từ DETETION -> DETECTION
    VISION_CHECKING_LED = "STEP_VISION_CHECKING_LED"
    VISION_COMBINE = "STEP_VISION_COMBINE"
    OUTPUT = "STEP_OUTPUT"
    RECHECK_READ_TRIGGER = "STEP_RECHECK_READ_TRIGGER"
    RECHECK_HANDLE = "STEP_RECHECK_HANDLE"
    RECHECK_SCAN_GEN = "STEP_RECHECK_SCAN_GEN"
    WRITE_LOG = "STEP_WRITE_LOG"
    RELEASE = "STEP_RELEASE"
    ERROR = "STEP_ERROR"
    CHECK_SENSOR_ON = "STEP_CHECK_SENSOR_ON"
    CHECK_SENSOR_OFF = "STEP_CHECK_SENSOR_OFF"

class StepResult(Enum):
    WAIT_PRODUCT = "WAIT_PRODUCT"
    WAIT_TRIGGER = "WAIT_TRIGGER"
    WAIT = "WAIT"
    PASS_ = "PASS"
    FAIL = "FAIL"

@dataclass
class RESULT:
    model: Optional[Any] = None
    
    seri: Optional[Any] = None
    
    ret: Optional[Any] = None
    
    output_image: Optional[Any] = None
    
    label_counts: Optional[Any] = None
    
    timecheck: Optional[Any] = None
    
    error: Optional[Any] = None

