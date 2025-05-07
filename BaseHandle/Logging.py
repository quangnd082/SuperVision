import logging
import colorlog
import os
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal
import csv
import cv2
import numpy as np


class Logger(QObject):
    signalLog = pyqtSignal(str)

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(logging.DEBUG)

        # Tạo thư mục lưu log nếu chưa có
        os.makedirs('Log_Vision/Log_View', exist_ok=True)
        os.makedirs('Log_Vision/Log_CSV', exist_ok=True)
        os.makedirs('Log_Vision/Log_Image', exist_ok=True)

        # Biến lưu ngày hiện tại để kiểm tra thay đổi file log
        self.current_date = datetime.now().strftime('%Y_%m_%d')

        # Tạo các handler cho log
        self.__create_log_handlers()

    def __create_log_handlers(self):
        """Tạo các handler cho log mỗi ngày."""
        today = datetime.now().strftime('%Y_%m_%d')
        log_path = f'Log_Vision/Log_View/{today}.log'

        # Formatter có màu cho console
        self.__formatter_color = colorlog.ColoredFormatter(
            fmt='%(log_color)s %(asctime)s %(name)s - %(filename)s - %(levelname)s - %(message)s',
            datefmt='%Y/%m/%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red'  # Thay 'magenta' bằng 'bold_red'
            }
        )


        # Formatter không màu cho file log
        self.__formatter_no_color = logging.Formatter(
            fmt='%(asctime)s %(name)s - %(filename)s - %(levelname)s - %(message)s',
            datefmt='%Y/%m/%d %H:%M:%S'
        )

        # Xóa các handler cũ trước khi thêm mới
        self.__logger.handlers.clear()

        # File log dạng text
        log_handle = logging.FileHandler(log_path, encoding='utf-8')
        log_handle.setLevel(logging.DEBUG)
        log_handle.setFormatter(self.__formatter_no_color)
        self.__logger.addHandler(log_handle)

        # Hiển thị log ra console
        stream_handle = logging.StreamHandler()
        stream_handle.setLevel(logging.DEBUG)
        stream_handle.setFormatter(self.__formatter_color)
        self.__logger.addHandler(stream_handle)

    def __check_date_and_update_log(self):
        """Kiểm tra nếu ngày thay đổi thì tạo file log mới."""
        new_date = datetime.now().strftime('%Y_%m_%d')
        if new_date != self.current_date:
            self.current_date = new_date
            self.__create_log_handlers()

    def __emit_formatted_log(self, level, message):
        """Gửi tín hiệu log với format đầy đủ."""
        self.__check_date_and_update_log()

        # Tạo LogRecord
        record = logging.LogRecord(
            name=self.__logger.name,
            level=level,
            pathname=__file__,
            lineno=0,
            msg=message,
            args=None,
            exc_info=None
        )

        # Format log
        formatted_message = self.__formatter_no_color.format(record)

        # Gửi tín hiệu đã format
        self.signalLog.emit(formatted_message)

    def log_image(self, model_name, image, series_number=None, ret=None, capture=False, log_csv=False):
        """Lưu ảnh vào thư mục log, ghi log thông tin ảnh và lưu log vào file CSV."""
        self.__check_date_and_update_log()
        today_folder = datetime.now().strftime('%Y_%m_%d')
        date_str = datetime.now().strftime('%Y_%m_%d')
        time_str = datetime.now().strftime('%H_%M_%S')

        if capture:
            image_folder = f'ImageCapture/{today_folder}/{model_name}/{series_number}'
        else:
            if model_name == 'Source':
                image_folder = f'res/Database/Images/Source'
            elif model_name == 'Destination':
                image_folder = f'res/Database/Images/Destination'
            else:
                image_folder = f'Log_Vision/Log_Image/{today_folder}/{model_name}/{series_number}'

        os.makedirs(image_folder, exist_ok=True)

        image_path = os.path.join(image_folder, f'{ret}_{date_str}_{time_str}.jpg')
        try:
            if image is None:
                raise ValueError("Ảnh không hợp lệ (None). Không thể lưu.")
            success = cv2.imwrite(image_path, image)

            if not success:
                raise IOError("Lỗi khi lưu ảnh.")

            image_path_fixed = image_path.replace("\\", "/")
            log_message = f'Image logged at {image_path_fixed}'
            self.info(log_message)

            if log_csv == True:
                # ✅ Ghi log vào file CSV
                csv_folder = 'Log_Vision/Log_CSV'
                os.makedirs(csv_folder, exist_ok=True)
                csv_path = os.path.join(csv_folder, f'{date_str}.csv')
                csv_exists = os.path.isfile(csv_path)

                with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if not csv_exists:
                        writer.writerow(['Model', 'Series Number', 'Result', 'Time'])
                    writer.writerow([model_name, series_number, ret, time_str])

            return image_path_fixed
        except Exception as ex:
            self.error(ex)


    # Các hàm log với đầy đủ format
    def debug(self, message):
        self.__emit_formatted_log(logging.DEBUG, str(message))
        self.__logger.debug(message, stacklevel=2)

    def info(self, message):
        self.__emit_formatted_log(logging.INFO, str(message))
        self.__logger.info(message, stacklevel=2)

    def warning(self, message, exc=None):
        self.__emit_formatted_log(logging.WARNING, message)
        self.__logger.warning(message, stacklevel=2, exc_info=exc)

    def error(self, message, exc=None):
        self.__emit_formatted_log(logging.ERROR, message)
        self.__logger.error(message, stacklevel=2, exc_info=exc)

    def critical(self, message, exc=None):
        self.__emit_formatted_log(logging.CRITICAL, message)
        self.__logger.critical(message, stacklevel=2, exc_info=exc)


if __name__ == '__main__':
    logger_1 = Logger('Trung')

    try:
        logger_1.debug('Test debug message')
        logger_1.info('Test info message')
        logger_1.warning('Test warning message')
        logger_1.error('Test error message')

        # Giả lập lưu ảnh
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        logger_1.log_image(model_name="YOLOv9", image=image)

        # Gây lỗi để test critical
        result = 1 / 0

    except Exception as e:
        logger_1.critical(f'Exception occurred: {e}')
