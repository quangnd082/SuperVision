from collections import Counter
import sys
import json
import cv2
import numpy as np
import threading
import time
import os
import copy
import re
import subprocess
import serial.tools.list_ports
from datetime import datetime
sys.path.append('libs')
sys.path.append('BaseHandle')
from ultralytics import YOLO
from types import SimpleNamespace
from libs import *
from libs.light_controller import LCPController, DCPController
from libs.IOController5 import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QActionGroup, QMessageBox, QFileDialog, QHeaderView, QTableWidgetItem, QTableWidget, QLabel
from PyQt5.QtCore import QThread, Qt, pyqtSignal, QStringListModel, QSettings, QByteArray, QTimer, QPointF
from PyQt5.QtGui import QIcon, QImage, QPixmap, QStandardItemModel, QStandardItem, QColor, QBrush
from res.Ui.mainwindow import Ui_MainWindow
from libs.canvas import Canvas, WindowCanvas
from libs.shape import Shape as MyShape
from cameras.open_camera import Camera
from cameras.webcam import Webcam
from cameras.hik import HIK
from cameras.soda import SODA
from cameras import get_camera_devices
from BaseHandle.server import Server
from BaseHandle.Logging import Logger
from BaseHandle.handle_file_json import HandleJsonPBA
from functools import partial
from constant import *
from sqlalchemy import create_engine, Column, Integer, String
import sqlite3
from PyQt5.QtWidgets import QPushButton
from sqlalchemy.orm import declarative_base, sessionmaker
from BaseHandle.connect_database import DatabaseManager
from BaseHandle.serial_receiver import SerialReceiver


class MainWindow(QMainWindow, Ui_MainWindow):
    showDstSignal = pyqtSignal(Canvas, np.ndarray)
    showEffect = pyqtSignal(int)
    hideEffect = pyqtSignal(int)
    showResultTable = pyqtSignal(QTableWidget, dict, str, str)
    showResultRate = pyqtSignal(str)
    showResultStatus = pyqtSignal(str)
    recheckSignal = pyqtSignal(str)
    setTextLabelSignal = pyqtSignal(QLabel, str)
    
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.camera = Camera()
        self.server = Server()
        self.scanner = SerialReceiver()
        self.send_data_com = SerialReceiver()
        self.light = None
        self.count_product_total = 0
        self.count_product_ok = 0
        self.count_product_ng = 0
        
        self.is_connect_server = False
        self.is_open_camera = False
        self.is_connect_io_controller = False
        self.is_connect_scanner = False
        self.is_connect_send_data = False 
        self.is_confirm_ret = True
        self.confirm_lock = threading.Lock()
        self.is_check_sn = False
        self.is_check_gen_id = False 
        self.is_sensor_on = False
        
        self.active_output = OutPorts.Out_3
        self.io_controller = None
        self.trigger_on = False
        self.handle_file_json = HandleJsonPBA()
        self.input_labels = [self.label_input_1, self.label_input_2, self.label_input_3, self.label_input_4,
                             self.label_input_5, self.label_input_6, self.label_input_7, self.label_input_8]
        
        self.main_logger = Logger('MainWindow')
        
        self.db = DatabaseManager(db_name=f'res/Database/{self.line_edit_database_path.text()}')
        self.log_table = self.db.create_table("users", Model=String, SeriesNumber= String, Source=String, Destination=String, 
                                    Return=String, Error=String)
        
        #Signal and Slots tab Auto
        self.but_start_auto.clicked.connect(self.on_click_but_start_auto)
        self.but_stop_auto.clicked.connect(self.on_click_but_stop_auto)
        self.but_reset_auto.clicked.connect(self.on_click_but_test_auto)
        self.showResultTable.connect(self.load_result_classes)
        self.recheckSignal.connect(self.recheck_result)
        self.setTextLabelSignal.connect(self.set_text_label)
        
        #Signal and Slots tab Teaching
        self.but_add.clicked.connect(self.on_click_but_add_model)
        self.but_del.clicked.connect(self.on_click_but_delete_model)
        self.but_save_teaching.clicked.connect(self.on_click_save_model)
        self.but_refresh_teaching.clicked.connect(self.refresh_ports)
        self.but_open_camera_teaching.clicked.connect(self.on_click_but_open_camera_teaching)
        self.but_open_camera_teaching.clicked.connect(self.on_click_but_close_camera_teaching)
        self.but_open_light.clicked.connect(self.on_click_but_open_light)
        self.spin_box_channel_value_0.valueChanged.connect(self.update_light_value)
        self.spin_box_channel_value_1.valueChanged.connect(self.update_light_value)
        self.spin_box_channel_value_2.valueChanged.connect(self.update_light_value)
        self.spin_box_channel_value_3.valueChanged.connect(self.update_light_value)
        self.but_out_1.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_1, checked))
        self.but_out_2.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_2, checked))
        self.but_out_3.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_3, checked))
        self.but_out_4.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_4, checked))
        self.but_out_5.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_5, checked))
        self.but_out_6.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_6, checked))
        self.but_out_7.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_7, checked))
        self.but_out_8.clicked.connect(lambda checked: self.on_click_but_out_all(OutPorts.Out_8, checked))
        self.but_connect_server.clicked.connect(self.on_click_but_connect_server)
        self.but_connect_server.clicked.connect(self.on_click_but_close_server)
        self.but_open_io_controller.clicked.connect(self.on_click_but_connect_io_controller)
        self.but_open_io_controller.clicked.connect(self.on_click_but_close_io_controller)
        self.but_connect_scanner.clicked.connect(self.on_click_but_connect_scanner)
        self.but_connect_scanner.clicked.connect(self.on_click_but_close_scanner)
        self.but_open_com_send_data.clicked.connect(self.on_click_but_open_com_send_data)
        self.but_open_com_send_data.clicked.connect(self.on_click_but_close_com_send_data)
        self.but_open_image_teaching.clicked.connect(self.on_click_but_open_image_teaching)
        self.but_start_camera_teaching.clicked.connect(self.on_click_but_start_camera_teaching)
        self.but_capture_teaching.clicked.connect(self.on_click_but_capture_teaching)
        self.combo_box_model_name_teaching.currentIndexChanged.connect(self.load_model_change_teaching)
        self.showDstSignal.connect(self.show_image)
        self.scanner.checkSignalScanner.connect(self.read_signal_scanner)
        # self.scanner.snFailed.connect(self.show_sn_failed)
        # self.scanner.snSuccess.connect(self.hide_sn_failed)
        self.showResultRate.connect(self.update_label_result)
        self.showResultStatus.connect(self.update_label_status)
        self.but_test_teaching.clicked.connect(self.on_click_but_test_teaching)
        
        #Signal and Slots Mainwindow
        self.server.server_logger.signalLog.connect(self.add_log)
        self.server.triggerOn.connect(self.set_trigger_on)
        self.camera.camera_logger.signalLog.connect(self.add_log)
        self.scanner.scanner_logger.signalLog.connect(self.add_log)
        self.main_logger.signalLog.connect(self.add_log)
        self.actionReset_Layout.triggered.connect(self.resetLayout)
        self.actionLight_mode.triggered.connect(partial(self.on_click_action_theme, path="res/Style/light_mode.qss"))
        self.actionDark_mode.triggered.connect(partial(self.on_click_action_theme, path="res/Style/dark_mode.qss"))
        self.actionAnime_mode.triggered.connect(partial(self.on_click_action_theme, path="res/Style/anime_mode.qss"))
        self.actionWood_mode.triggered.connect(partial(self.on_click_action_theme, path="res/Style/wood_mode.qss"))
        self.actionQuit.triggered.connect(self.close)
        self.showEffect.connect(self.show_effect)
        self.hideEffect.connect(self.hide_effect)
        
        #Signal and Slots tab Data
        self.table_widget_database.itemSelectionChanged.connect(self.get_selected_items)
        
        self.combo_box_classes_ai.currentIndexChanged.connect(
            lambda: self.load_classes_ai(
                self.table_widget_classes_ai_teaching,
                self.combo_box_classes_ai.currentText()
            )
        )
        
        self.but_load_database.clicked.connect(self.on_click_but_load_database)
        self.but_find_database.clicked.connect(self.on_click_but_find_database)
        
        self.init_main_window()
        self.init_ui_auto()
        self.init_ui_teaching()
        self.init_ui_data()
        self.init_ui_io_monitor()
        
        self.upload_model_ai()
        self.upload_feature_camera()
        self.refresh_ports()
        self.upload_model_names()
        self.load_model_change_teaching()
        self.load_classes_ai(self.table_widget_classes_ai_teaching, self.combo_box_classes_ai.currentText())
        self.loadSettings()
        self.connect_database()
        
        self.showMaximized()
    
    def init_main_window(self):
        self.setWindowIcon(QIcon("res/Style/icon.ico"))
        self.setWindowTitle('AI Vision') 
        
        
        self.image_dst = Canvas()
        self.image_bin = Canvas()
        
        self.layout_image_dst_canvas.addWidget(WindowCanvas(self.image_dst))
        self.layout_image_bin_canvas.addWidget(WindowCanvas(self.image_bin))
        
        self.action_group = QActionGroup(self)
        self.action_group.setExclusive(True)       
        self.action_group.addAction(self.actionLight_mode)
        self.action_group.addAction(self.actionDark_mode)
        self.action_group.addAction(self.actionAnime_mode)    
        self.action_group.addAction(self.actionWood_mode)    
        
        with open("res/Style/light_mode.qss", "r", encoding="utf-8") as file:
            app.setStyleSheet(file.read())
            
        self.statusBar().addPermanentWidget(self.progressBar)
        self.progressBar.setVisible(False)
        
        self.menuView.addAction(self.dockWidget_2.toggleViewAction())
        self.menuView.addAction(self.dockWidget_3.toggleViewAction())
        
        actions = self.menuView.actions()
        if actions:
            ui_action = actions[0]  # Action từ giao diện (ví dụ là action đầu)
            self.menuView.removeAction(ui_action)  # Xóa nó khỏi vị trí ban đầu
            self.menuView.addAction(ui_action)  # Thêm lại xuống cuối
 
        self.is_resetting = False
        
        self.log_model = QStandardItemModel()
        self.list_log_view.setModel(self.log_model)
        # self.list_log_view_2.setModel(self.log_model)
        
    def init_ui_auto(self):
        self.auto_canvas = Canvas()
        self.layout_auto_canvas.addWidget(WindowCanvas(self.auto_canvas))
        self.but_stop_auto.setDisabled(True)
        # self.msg_box_show_sn_failed = QMessageBox(self)

    def init_ui_teaching(self):
        self.is_open_camera = False
        self.is_showing_camera = False
        self.file_open_image = None
        self.teaching_canvas = Canvas()
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial_data)
        
        
        # =====================
        set_roi = QAction(QIcon("res/Style/icon.ico"), "Set Roi", self)
        self.teaching_canvas.contextMenu.addSeparator()
        self.teaching_canvas.contextMenu.addAction(set_roi)
        # ======================
        
        self.layout_teaching_canvas.addWidget(WindowCanvas(self.teaching_canvas))
        self.but_start_camera_teaching.setDisabled(True)
        self.but_open_camera_teaching.setProperty("status", "Open")
        self.but_start_camera_teaching.setProperty("status", "Open")
        self.but_open_light.setProperty("status", "Open")
        self.but_open_io_controller.setProperty("status", "Open")
        self.but_connect_server.setProperty("status", "Open")
        self.but_connect_scanner.setProperty("status", "Open")
        self.but_open_com_send_data.setProperty("status", "Open")
    
    def init_ui_data(self):
        self.file_path_database = None
        self.data_image_input_canvas = Canvas()
        self.data_image_output_canvas = Canvas()
        self.layout_image_input_canvas.addWidget(WindowCanvas(self.data_image_input_canvas))
        self.layout_image_output_canvas.addWidget(WindowCanvas(self.data_image_output_canvas))
        self.but_find_database.setDisabled(True)
        
        header = self.table_widget_database.verticalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
    
    def init_ui_io_monitor(self):
        self.input_labels = [self.label_input_1, self.label_input_2, self.label_input_3, self.label_input_4,
                            self.label_input_5, self.label_input_6, self.label_input_7, self.label_input_8]
        for label in self.input_labels:
            label.setStyleSheet("background-color: gray; color: white; padding: 5px;")
    
    def on_click_but_start_auto(self):
        self.combo_box_model_name_teaching.setCurrentIndex(self.combo_box_model_name_auto.currentIndex())
        
        model_name = f'Model/{self.combo_box_model_name_auto.currentText()}'
        
        self.config_auto = self.get_config_auto(model_name)
        
        self.on_click_but_connect_server()
        self.on_click_but_connect_scanner()
        self.on_click_but_open_com_send_data()
        self.on_click_but_connect_io_controller()
        self.on_click_but_open_camera_teaching()
        # self.ret_light, self.value = self.open_light_auto()
        
        # if not self.ret_light:
        #     self.on_click_but_close_camera_teaching()
        #     self.on_click_but_close_io_controller()
        #     self.on_click_but_close_server()
            
        #     return
        
        if not self.is_open_camera or not self.is_connect_server or not self.is_connect_scanner or not self.is_connect_io_controller or not self.is_connect_send_data:
            
            self.on_click_but_close_camera_teaching()
            self.on_click_but_close_io_controller()
            self.on_click_but_close_server()
            self.on_click_but_close_scanner()
            self.on_click_but_close_com_send_data()
            # self.close_light_teaching()
            
            return
        
        else:
            
            self.set_shapes(self.auto_canvas, self.config_auto.shapes)
            self.but_start_auto.setDisabled(True)
            self.but_stop_auto.setDisabled(False)
            
        self.start_process()
    
    def on_click_but_stop_auto(self):
        self.stop_process()
        self.set_disable_auto(False)
        self.on_click_but_close_server()
        self.on_click_but_close_io_controller()
        self.on_click_but_close_camera_teaching()
        self.on_click_but_close_scanner()
        self.on_click_but_close_com_send_data()
        
        # self.close_light_teaching()
        self.but_start_auto.setDisabled(False)
        self.but_stop_auto.setDisabled(True)
        
    def on_click_but_test_auto(self):
        self.count_product_total = 0
        self.count_product_ok = 0
        self.count_product_ng = 0
        
        self.label_ok.setText('0')
        self.label_ng.setText('0')
        self.label_total.setText('0')
        self.label_rate.setText('0')

    def on_click_but_add_model(self):
        name_model = self.combo_box_model_name_teaching.currentText()
        
        if name_model and self.combo_box_model_name_teaching.findText(name_model) == -1:
            reply = QMessageBox.question(self, 'Question', f'Bạn có muốn thêm mô hình {name_model} không',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            
            self.combo_box_model_name_teaching.addItem(name_model)
            self.combo_box_model_name_auto.addItem(name_model)
            self.combo_box_model_name_data.addItem(name_model)
            
            config = self.get_config_from_ui()
            config_dict = json.loads(json.dumps(config, default=lambda x: vars(x)))
            self.handle_file_json.add(name_model, config_dict)
            
            QMessageBox.information(self, 'Information', f'Mô hình {name_model} đã được thêm thành công',
                                    QMessageBox.StandardButton.Close)
            
            self.combo_box_model_name_teaching.clearEditText()
        elif name_model == '':
            QMessageBox.warning(self, 'Warning', f'Chưa nhập tên mô hình', QMessageBox.StandardButton.Close)
        else:
            QMessageBox.warning(self, 'Warning', f'Mô hình {name_model} đã tồn tại', QMessageBox.StandardButton.Close)

    def on_click_but_delete_model(self):
        name_model = self.combo_box_model_name_teaching.currentText()
        index_name_model = self.combo_box_model_name_teaching.findText(name_model)
        if index_name_model == -1:
            QMessageBox.warning(self, 'Warning', f'Mô hình {name_model} không tồn tại',
                                QMessageBox.StandardButton.Close)
            return
        elif name_model == 'Default':
            QMessageBox.warning(self, 'Warning', f'Mô hình {name_model} là mặc định, không thể xóa',
                                QMessageBox.StandardButton.Close)
            return
        reply = QMessageBox.question(self, 'Delete', f'Bạn có muốn xóa {name_model} không?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
        self.handle_file_json.delete(name_model)
        
        index = self.combo_box_model_name_teaching.currentIndex()
        self.combo_box_model_name_auto.removeItem(index)
        self.combo_box_model_name_teaching.removeItem(index)
        
        QMessageBox.information(self, 'Information', f'Mô hình {name_model} đã được xóa',
                                QMessageBox.StandardButton.Close)

    def on_click_save_model(self):
        name_model = self.combo_box_model_name_teaching.currentText()
        
        index_name_model = self.combo_box_model_name_teaching.findText(name_model)
        
        if index_name_model == -1:
            QMessageBox.warning(self, 'Warning', f'Mô hình {name_model} không tồn tại',
                                QMessageBox.StandardButton.Close)
            return
        
        config = self.get_config_from_ui()
        config_dict = json.loads(json.dumps(config, default=lambda x: vars(x)))
        
        reply = QMessageBox.question(self, 'Question', f'Bạn có muốn lưu mô hình {name_model} không',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        self.handle_file_json.save(name_model, config_dict)
        
        QMessageBox.information(self, 'Information', f'Mô hình {name_model} đã thay đổi thành công',
                                QMessageBox.StandardButton.Close)
         

    def on_click_but_open_camera_teaching(self):
        if self.but_open_camera_teaching.property("status") == "Open":
            self.open_camera_teaching()
            self.but_open_camera_teaching.setProperty("status", "Close")
            self.but_open_camera_teaching.setText('Close')
            
        self.style().unpolish(self.but_open_camera_teaching)
        self.style().polish(self.but_open_camera_teaching)
        self.style().unpolish(self.but_start_camera_teaching)
        self.style().polish(self.but_start_camera_teaching)
        
        self.but_open_camera_teaching.clicked.disconnect()
        self.but_open_camera_teaching.clicked.connect(self.on_click_but_close_camera_teaching)
            
    def on_click_but_close_camera_teaching(self):          
        if self.but_open_camera_teaching.property("status") == "Close":
            self.close_camera_teaching()
            self.but_open_camera_teaching.setText('Open')
            self.but_open_camera_teaching.setProperty("status", "Open")
            self.but_start_camera_teaching.setProperty("status", "Open")
            self.but_start_camera_teaching.setText('Start')
        
        self.style().unpolish(self.but_open_camera_teaching)
        self.style().polish(self.but_open_camera_teaching)
        self.style().unpolish(self.but_start_camera_teaching)
        self.style().polish(self.but_start_camera_teaching)
        
        self.but_open_camera_teaching.clicked.disconnect()
        self.but_open_camera_teaching.clicked.connect(self.on_click_but_open_camera_teaching)
        
    def on_click_but_start_camera_teaching(self):
        if self.but_start_camera_teaching.property("status") == "Open":
            self.but_start_camera_teaching.setProperty("status", "Close")
            self.but_start_camera_teaching.setText('Stop')
            self.start_camera_teaching()
        else:
            self.but_start_camera_teaching.setText('Start')
            self.but_start_camera_teaching.setProperty("status", "Open")
            self.stop_camera_teaching()
                
        self.style().unpolish(self.but_start_camera_teaching)
        self.style().polish(self.but_start_camera_teaching)
    
    def on_click_but_open_light(self):
        if self.but_open_light.property("status") == "Open":
            self.but_open_light.setProperty("status", "Close")
            self.but_open_light.setText('Close')
            self.open_light_teaching()
            
        elif self.but_open_light.property("status") == "Close":
            self.set_light_value()
            self.but_open_light.setText('Open')
            self.but_open_light.setProperty("status", "Open")
        
        self.style().unpolish(self.but_open_light)
        self.style().polish(self.but_open_light)
        
    def on_click_but_connect_io_controller(self):
        if self.but_open_io_controller.property("status") == "Open":
            self.but_open_io_controller.setProperty("status", "Close")
            self.but_open_io_controller.setText('Close')
            self.connect_io_controller()
            
        self.style().unpolish(self.but_open_io_controller)
        self.style().polish(self.but_open_io_controller)
        self.but_open_io_controller.clicked.disconnect()
        self.but_open_io_controller.clicked.connect(self.on_click_but_close_io_controller)
        
    def on_click_but_close_io_controller(self):        
        if self.but_open_io_controller.property("status") == "Close":
            self.but_open_io_controller.setText('Connect')
            self.but_open_io_controller.setProperty("status", "Open")
            self.close_io_controller()
            
        self.style().unpolish(self.but_open_io_controller)
        self.style().polish(self.but_open_io_controller)
        self.but_open_io_controller.clicked.disconnect()
        self.but_open_io_controller.clicked.connect(self.on_click_but_connect_io_controller)
        
    def on_click_but_connect_server(self):
        if self.but_connect_server.property("status") == "Open":
            self.but_connect_server.setProperty("status", "Close")
            self.but_connect_server.setText('Close')
            self.connect_server_teaching()
            
        self.style().unpolish(self.but_connect_server)
        self.style().polish(self.but_connect_server)
        
        self.but_connect_server.clicked.disconnect()
        self.but_connect_server.clicked.connect(self.on_click_but_close_server)
        
    def on_click_but_close_server(self):        
        if self.but_connect_server.property("status") == "Close":
            self.but_connect_server.setText('Open')
            self.but_connect_server.setProperty("status", "Open")
            self.close_server_teaching()
            
        self.style().unpolish(self.but_connect_server)
        self.style().polish(self.but_connect_server)
        
        self.but_connect_server.clicked.disconnect()
        self.but_connect_server.clicked.connect(self.on_click_but_connect_server)
    
    def on_click_but_save_teaching(self):
        pass
    
    def on_click_but_refresh_teaching(self):
        pass
        
    def on_click_but_open_image_teaching(self):
        if self.but_start_camera_teaching.property("status") == "Close":
            self.is_showing_camera = False
            self.but_start_camera_teaching.setProperty("status", "Open")
            self.but_start_camera_teaching.setText('Start')
            self.style().unpolish(self.but_start_camera_teaching)
            self.style().polish(self.but_start_camera_teaching)
        
        options = QFileDialog.Options()
        self.file_open_image, _ = QFileDialog.getOpenFileName(self, "Chọn Ảnh", "", 
                                                  "Images (*.png *.jpg *.jpeg *.bmp *.gif)", 
                                                  options=options)
        if self.file_open_image:
            self.teaching_canvas.load_pixmap(QPixmap(self.file_open_image))
    
    def on_click_but_capture_teaching(self):
        if self.is_showing_camera:
            # self.on_click_but_open_light()
            # time.sleep(self.spin_box_delay_controller.value() / 1000)
            self.file_open_image = self.mat.copy()
            
            self.main_logger.log_image(self.combo_box_model_name_teaching.currentText(), 
                                       self.file_open_image, capture=True)
            
            # self.on_click_but_open_light()
            return
        
        if self.is_open_camera:
            # self.on_click_but_open_light()
            # time.sleep(self.spin_box_delay_controller.value() / 1000)
            self.file_open_image = self.camera.get_frame()
            # self.on_click_but_open_light()
            self.main_logger.log_image(self.combo_box_model_name_teaching.currentText(), 
                                       self.file_open_image, capture=True)
            
            self.teaching_canvas.load_pixmap(QPixmap(self.file_open_image))
            return
    
    def on_click_but_out_all(self, port, state):
        if self.io_controller:
            if self.io_controller.is_open():
                self.io_controller.write_out(port, PortState.On if state else PortState.Off)
    
    def on_click_but_connect_scanner(self):
        if self.but_connect_scanner.property("status") == "Open":
            if not self.connect_scanner():
                return
            self.but_connect_scanner.setProperty("status", "Close")
            self.but_connect_scanner.setText('Close')

            
        self.style().unpolish(self.but_connect_scanner)
        self.style().polish(self.but_connect_scanner)
        
        self.but_connect_scanner.clicked.disconnect()
        self.but_connect_scanner.clicked.connect(self.on_click_but_close_scanner)
    
    def on_click_but_close_scanner(self):
        if self.but_connect_scanner.property("status") == "Close":
            self.but_connect_scanner.setText('Open')
            self.but_connect_scanner.setProperty("status", "Open")
            self.close_scanner()
            
        self.style().unpolish(self.but_connect_scanner)
        self.style().polish(self.but_connect_scanner)
        
        self.but_connect_scanner.clicked.disconnect()
        self.but_connect_scanner.clicked.connect(self.on_click_but_connect_scanner)
    
    # def on_click_but_connect_scanner(self):
    #     if not self.serial.is_connected():
    #         port = self.combo_box_com_controller_3.currentText()
    #         baudrate = int(self.combo_box_baudrate_controller_3.currentText())
    #         if self.serial.connect(port, baudrate):
    #             self.but_connect_scanner.setText("Disconnect")
    #             self.timer.start(100)  # đọc mỗi 100ms
    #             self.list_widget_gmes.addItem(f"[+] Đã kết nối {port} @ {baudrate}")
    #         else:
    #             self.list_widget_gmes.addItem("[!] Kết nối thất bại.")
    #     else:
    #         self.timer.stop()
    #         self.serial.disconnect()
    #         self.but_connect_scanner.setText("Connect")
    #         self.list_widget_gmes.addItem("[*] Đã ngắt kết nối.")
    
    def connect_scanner(self):
        port = self.combo_box_com_controller_3.currentText()
        baudrate = int(self.combo_box_baudrate_controller_3.currentText())
        if self.scanner.connect(port, baudrate):
            self.timer.start(100)  # đọc mỗi 100ms
            self.is_connect_scanner = True
            return True
        else:
            self.is_connect_scanner = False
            return False
    
    def close_scanner(self):
        self.timer.stop()
        self.scanner.disconnect()
        self.is_connect_scanner = False     
    
    def read_serial_data(self):
        try:
            data_sn = self.scanner.read_data()
            return data_sn
            
        except Exception as e:
            print(e)
    
    def on_click_but_test_teaching(self):
        if self.file_open_image:
            name_model = self.combo_box_model_ai.currentText()
            
            classes_ai = self.combo_box_classes_ai.currentText()
            
            model_ai = self.load_model(f'res/Model_AI/{name_model}')
            
            image = cv2.imread(self.file_open_image)
            
            shapes_box = self.get_shapes(self.teaching_canvas)
            
            name_model = self.combo_box_model_name_teaching.currentText()
            
            result = self.detect_objects(name_model, model_ai, classes_ai, image, shapes_box)
            
            self.load_result_classes(self.table_widget_classes_ai_teaching,
                                     result.label_counts, result.ret, result.error)
            
            self.show_image(self.teaching_canvas, result.output_image)
             
    def on_click_but_open_com_send_data(self):
        if self.but_open_com_send_data.property("status") == "Open":
            if not self.open_com_send_data():
                return
            self.but_open_com_send_data.setProperty("status", "Close")
            self.but_open_com_send_data.setText('Close')

            
        self.style().unpolish(self.but_open_com_send_data)
        self.style().polish(self.but_open_com_send_data)
        
        self.but_open_com_send_data.clicked.disconnect()
        self.but_open_com_send_data.clicked.connect(self.on_click_but_close_com_send_data)
    
    def on_click_but_close_com_send_data(self):
        if self.but_open_com_send_data.property("status") == "Close":
            self.but_open_com_send_data.setText('Open')
            self.but_open_com_send_data.setProperty("status", "Open")
            self.close_com_send_data()
            
        self.style().unpolish(self.but_open_com_send_data)
        self.style().polish(self.but_open_com_send_data)
        
        self.but_open_com_send_data.clicked.disconnect()
        self.but_open_com_send_data.clicked.connect(self.on_click_but_open_com_send_data)
    
    def open_com_send_data(self):
        port = self.combo_box_com_controller_4.currentText()
        baudrate = int(self.combo_box_baudrate_controller_4.currentText())
        if self.send_data_com.connect(port, baudrate):
            self.is_connect_send_data = True
            return True
        else:
            self.is_connect_send_data = False
            return False
       
    def close_com_send_data(self):
        self.send_data_com.disconnect()
        self.is_connect_send_data = False 
             
    def connect_database(self):
        self.file_path_database = os.path.join(os.getcwd(), 'res', 'Database', 'database.db')
        self.load_database(self.file_path_database)
        self.but_find_database.setDisabled(False)   
            
    def on_click_but_find_database(self):
        self.find_database()
    
    def on_click_but_load_database(self):
        self.load_database(self.file_path_database)
    
    def on_click_action_theme(self, path):
        with open(path, "r", encoding="utf-8") as file:
            app.setStyleSheet(file.read())
    
    def ndarray2pixmap(self, mat: np.ndarray):
        height, width, channel = mat.shape
        bytes_per_line = channel * width
        qimage = QImage(mat.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        return pixmap
    
    def pixmap2ndarray(self, pixmap: QPixmap) -> np.ndarray:
        image = pixmap.toImage()
        image = image.convertToFormat(QImage.Format_RGB888)
        width, height = image.width(), image.height()
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape(height, width, 3)

        return arr
    
    def load_model(self, model_path):
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
    
    def load_label(self, file_path):
        labels = set()
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # Bỏ qua dòng trống
                # Tách phần sau dấu gạch dưới đầu tiên
                parts = line.split("_", 1)
                if len(parts) > 1:
                    label_part = parts[1].split()[0]  # Lấy phần trước dấu cách nếu có
                    labels.add(label_part)
        return labels


    def is_inside_any_shape(self, x1, y1, x2, y2, shapes_dict):
        for key in shapes_dict:
            sx, sy, sw, sh = shapes_dict[key]
            sx2 = sx + sw
            sy2 = sy + sh
            if x1 >= sx and y1 >= sy and x2 <= sx2 and y2 <= sy2:
                return True
        return False

    
    def detect_objects(self, name_model, model_ai, classes_ai, image, shapes, seri_number=None): 
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            results = model_ai.predict(source=image, save=False, verbose=False)
            output_img = image.copy()

            detected_labels_in_position = set()
            detected_labels_out_of_position = set()
            label_counter = Counter()

            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                conf = box.conf[0].item()
                label = model_ai.names[cls_id]
                label_counter[label] += 1

                if self.is_inside_any_shape(x1, y1, x2, y2, shapes):
                    detected_labels_in_position.add(label)

                    color = (0, 255, 0)
                    cv2.rectangle(output_img, (x1, y1), (x2, y2), color, 12)
                    cv2.putText(output_img, f"{label} {conf:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 5, color, 15)
                else:
                    detected_labels_out_of_position.add(label)

                    color = (0, 0, 255)
                    cv2.rectangle(output_img, (x1, y1), (x2, y2), color, 12)
                    cv2.putText(output_img, f"{label} {conf:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 8, color, 20)

            # Load labels & counts từ file
            required_labels = set()
            required_counts = {}
            with open(f"res/Model_AI/{classes_ai}", "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        left, count = line.rsplit(" ", 1)
                        _, label = left.split("_", 1)
                        required_labels.add(label)
                        required_counts[label] = int(count)
                    except ValueError:
                        continue

            # Tạo label_counts dạng {"label": {"count": x, "status": "PASS"/"FAIL"}}
            label_counts_detailed = {}
            for label in required_labels:
                detected_count = label_counter.get(label, 0)
                expected_count = required_counts[label]

                if label in detected_labels_in_position and detected_count == expected_count:
                    status = "PASS"
                else:
                    status = "FAIL"

                label_counts_detailed[label] = {
                    "count": detected_count,
                    "status": status
                }

            # Xác định lỗi
            missing_labels = required_labels - (detected_labels_in_position | detected_labels_out_of_position)
            error = ''
            if missing_labels:
                error = 'Thiếu hàng'
            elif detected_labels_out_of_position & required_labels:
                error = 'Sai vị trí'

            # Nếu có bất kỳ label nào FAIL, kết quả là NG
            has_fail = any(info["status"] == "FAIL" for info in label_counts_detailed.values())
            if has_fail:
                font = cv2.FONT_HERSHEY_SIMPLEX
                text = "NG"
                color = (0, 0, 255)
                cv2.putText(output_img, text, (300, 500), font, 10, color, 15)

            # Vẽ current_time, name_model và seri_number (nếu có) ở góc phải phía trên - to gấp đôi
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 4  # GẤP ĐÔI
            font_thickness = 8  # GẤP ĐÔI
            text_color = (255, 255, 255)

            # Tính kích thước từng dòng text
            (current_time_width, current_time_height), _ = cv2.getTextSize(current_time, font, font_scale, font_thickness)
            (model_width, model_height), _ = cv2.getTextSize(name_model, font, font_scale, font_thickness)

            if seri_number:
                (seri_width, seri_height), _ = cv2.getTextSize(seri_number, font, font_scale, font_thickness)
            else:
                seri_width = seri_height = 0

            max_text_width = max(current_time_width, model_width, seri_width)
            x = output_img.shape[1] - max_text_width - 40  # Cách mép phải xa hơn để tránh đụng khung
            line_spacing = 30  # Khoảng cách giữa các dòng

            ##===============Viêt text ở trên==================##
            # # Vị trí các dòng
            # y_time = current_time_height + 40
            # y_model = y_time + model_height + line_spacing
            # y_seri = y_model + seri_height + line_spacing if seri_number else 0

            # # Tính vùng nền mờ
            # padding = 20
            # top_left = (x - padding, y_time - current_time_height - padding)
            # bottom_y = y_seri if seri_number else y_model
            # bottom_right = (x + max_text_width + padding, bottom_y + padding)
            # cv2.rectangle(output_img, top_left, bottom_right, (0, 0, 0), -1)
            
            ##===============Viêt text ở dưới==================##
            bottom_y = output_img.shape[0] - 40
            y_seri = bottom_y if seri_number else None
            y_model = y_seri - seri_height - line_spacing if seri_number else bottom_y
            y_time = y_model - model_height - line_spacing

            # Nền mờ phía sau text
            padding = 20
            top_left = (x - padding, y_time - current_time_height - padding)
            bottom_right = (x + max_text_width + padding, bottom_y + padding)
            cv2.rectangle(output_img, top_left, bottom_right, (0, 0, 0), -1)

            # Vẽ text
            cv2.putText(output_img, current_time, (x, y_time), font, font_scale, text_color, font_thickness)
            cv2.putText(output_img, name_model, (x, y_model), font, font_scale, text_color, font_thickness)
            if seri_number:
                cv2.putText(output_img, seri_number, (x, y_seri), font, font_scale, text_color, font_thickness)


            ret = StepResult.PASS_.value if not has_fail else StepResult.FAIL.value

            print(label_counts_detailed)

            return RESULT(
                model=name_model,
                seri=None,
                output_image=output_img,
                label_counts=label_counts_detailed,
                ret=ret,
                timecheck=current_time,
                error=error,
            )

        except Exception as e:
            return RESULT(
                model=name_model,
                seri=None,
                output_image=None,
                label_counts={},
                ret=None,
                timecheck=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                error=str(e),
            )
   
    # Dùng để bắt đầu live camera
    def start_camera(self, camera: Camera):
        self.b_start = True
        threading.Thread(target=self.loop_live_camera, args=(camera, ), daemon=True).start()
        
    # Dùng để dừng live camera
    def stop_camera(self):
        self.b_start = False

    # Vòng lặp để live
    def loop_live_camera(self, camera: Camera):
        while True:
            self.mat = camera.get_frame()
            if self.mat is not None:
                self.showDstSignal.emit(self.teaching_canvas, self.mat)
            if not self.is_showing_camera:
                break
            time.sleep(0.04)
            
    def set_canvas(self, canvas: Canvas, mat: np.ndarray):
        mat_rgb = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)
        pixmap = self.ndarray2pixmap(mat_rgb)
        canvas.load_pixmap(pixmap)
    
    def show_image(self, canvas, mat):
        self.set_canvas(canvas, mat)
        
    def thread_loop_teaching(self):
    #     step = STEP_READ_TRIGGER
        
    #     mat = None
    #     error = None
    #     result: RESULT = None
        
    #     self.showEffect.emit(50)
    #     model_ai = self.load_model(f'res/Model_AI/{self.combo_box_model_ai.CurrentText()}')
    #     self.hideEffect.emit(200)
        
    #     while True:
    #         try:
    #             if step == STEP_READ_TRIGGER:
    #                 if self.trigger_on:
    #                     self.main_logger.warning(STEP_READ_TRIGGER)
    #                     step = STEP_ON_LIGHTING
                        
    #             elif step == STEP_ON_LIGHTING:
    #                 self.main_logger.warning(STEP_ON_LIGHTING)
    #                 channel_0 = self.spin_box_channel_value_0
    #                 channel_1 = self.spin_box_channel_value_1
    #                 channel_2 = self.spin_box_channel_value_2
    #                 channel_3 = self.spin_box_channel_value_3
    #                 self.set_light_value(channel_0, channel_1, channel_2, channel_3)
    #                 step = STEP_PREPROCESS 
                    
    #             elif step == STEP_PREPROCESS:
    #                 self.main_logger.warning(STEP_PREPROCESS)
    #                 mat = self.camera.get_frame()
    #                 if mat is None:
    #                     raise Exception('Failed to get frame')              
    #                 step = STEP_OFF_LIGHTING
                    
    #             elif step == STEP_OFF_LIGHTING:
    #                 self.main_logger.warning(STEP_OFF_LIGHTING)
    #                 self.set_light_value()
    #                 step = STEP_VISION_DETECTION
                
    #             elif step == STEP_VISION_DETECTION:
    #                 self.main_logger.warning(STEP_VISION_DETECTION)
    #                 result = self.detect_objects(model_ai, mat)
    #                 step = STEP_OUTPUT
                
    #             elif step == STEP_OUTPUT:
    #                 self.main_logger.warning(STEP_OUTPUT)
    #                 self.showDstSignal.emit(self.teaching_canvas, result.output_image)
    #                 self.set_io_result(result.ret)            
    #                 step = STEP_RELEASE
                    
    #             elif step == STEP_RELEASE:
    #                 self.main_logger.warning(STEP_RELEASE)
    #                 mat = None
    #                 error = None
    #                 result = None
    #                 self.set_trigger_off()
    #                 step = STEP_READ_TRIGGER
                
    #             elif step == STEP_ERROR:
    #                 self.main_logger.warning(STEP_ERROR)
    #                 if error:
    #                     self.main_logger.error(error)
    #                     self.set_io_result(RESULT_FAIL)
    #                 step = STEP_RELEASE
            
    #         except Exception as ex:
    #             error = str(ex)
    #             step = STEP_ERROR 
            
    #         if not self.b_start:
    #             break
    
    #         time.sleep(0.01)
        pass
    
    def thread_loop_auto(self):
        step = Step.CHECK_SENSOR_ON.value
        
        mat = None
        error = None
        self.data_sn = None
        result: RESULT = None
        
        self.active_output = OutPorts.Out_3
        
        self.showEffect.emit(50)
        shapes_box = self.config_auto.shapes
        classes_ai = self.config_auto.model_ai.classes_name
        model_ai = self.load_model(f'res/Model_AI/{self.config_auto.model_ai.model_name}')
        self.load_classes_ai(self.table_widget_classes_ai_auto, classes_ai)
        self.hideEffect.emit(200)
        self.showResultStatus.emit(StepResult.WAIT_PRODUCT.value)
        self.set_io_result(StepResult.WAIT.value)
        self.set_disable_auto(True)
        
        delay_io = int(self.config_auto.hardware.io.delay)
        
        timing_results = {}
        
        while True:
            try:
                if step == Step.CHECK_SENSOR_ON.value:
                    if self.is_sensor_on:
                        step = Step.SCANNER.value
                        self.showResultStatus.emit(StepResult.WAIT_TRIGGER.value)
                    else:
                        self.data_sn = None
                        self.set_trigger_off()
                              
                elif step == Step.SCANNER.value:
                    if self.data_sn:
                        self.setTextLabelSignal.emit(self.label_scanner, self.data_sn)
                        step = Step.READ_TRIGGER.value
                    else:
                        self.set_trigger_off()
                    
                elif step == Step.READ_TRIGGER.value:
                    if self.trigger_on:
                        self.main_logger.warning(Step.READ_TRIGGER.value)
                        self.showResultStatus.emit(StepResult.WAIT.value)
                        step = Step.PREPROCESS.value 
                                        
                elif step == Step.ON_LIGHTING.value:
                    self.main_logger.warning(Step.ON_LIGHTING.value)
                    start = time.perf_counter()
                    self.set_light_value(self.value[0], self.value[1], self.value[2], self.value[3])
                    time.sleep(self.value[4] / 1000)
                    step = Step.PREPROCESS.value  
                    timing_results["on_light"] = (time.perf_counter() - start) * 1000    

                elif step == Step.PREPROCESS.value:
                    start = time.perf_counter()
                    self.main_logger.warning(Step.PREPROCESS.value)
                    mat = self.camera.get_frame()
                    if mat is None:
                        raise Exception('Failed to get frame')              
                    step = Step.VISION_DETECTION.value  
                    timing_results["grab_img"] = (time.perf_counter() - start) * 1000

                elif step == Step.OFF_LIGHTING.value:
                    start = time.perf_counter()
                    self.main_logger.warning(Step.OFF_LIGHTING.value)
                    self.set_light_value()
                    step = Step.VISION_DETECTION.value  
                    timing_results["off_light"] = (time.perf_counter() - start) * 1000

                elif step == Step.VISION_DETECTION.value:
                    start = time.perf_counter()
                    self.main_logger.warning(Step.VISION_DETECTION.value)
                    result = self.detect_objects(self.config_auto.name_model, model_ai, classes_ai, mat, shapes_box, self.data_sn)
                    result.seri = self.data_sn
                    self.showDstSignal.emit(self.auto_canvas, result.output_image)
                    timing_results["detect_objects"] = (time.perf_counter() - start) * 1000
                    step = Step.RECHECK_READ_TRIGGER.value  

                elif step == Step.RECHECK_READ_TRIGGER.value:
                    if result.ret == "PASS":
                        step = Step.OUTPUT.value  
                    else:
                        
                        self.recheckSignal.emit(result.ret)
                        step = Step.RECHECK_SCAN_GEN.value  

                    
                elif step == Step.RECHECK_SCAN_GEN.value:
                    if self.is_check_gen_id:
                        self.is_check_sn = False
                        step = Step.OUTPUT.value

                elif step == Step.OUTPUT.value:
                    self.main_logger.warning(Step.OUTPUT.value)
                    
                    result.ret = 'PASS' if self.is_confirm_ret else 'FAIL'
                    
                    self.showResultStatus.emit(result.ret)
                    self.set_io_result(result.ret)
                    self.showResultRate.emit(result.ret)
                    
                    step = Step.WRITE_LOG.value 

                elif step == Step.WRITE_LOG.value:
                    start = time.perf_counter()
                    
                    self.main_logger.warning(Step.WRITE_LOG.value)
                    
                    self.write_log_async(mat, result, self.data_sn)
                    
                    data_send_com = {
                        'Name model': self.config_auto.name_model,
                        'S/N': self.data_sn,
                    }
                    
                    json_str = json.dumps(data_send_com)
                    
                    self.send_data_com.send_data(json_str)
                    
                    self.showResultTable.emit(self.table_widget_classes_ai_auto, 
                                            result.label_counts, result.ret, result.error)
                    
                    timing_results["write_log"] = (time.perf_counter() - start) * 1000
                    
                    step = Step.RELEASE.value 

                elif step == Step.RELEASE.value:
                    self.main_logger.info(json.dumps(timing_results, indent=4))
                    self.main_logger.warning(Step.RELEASE.value)
                    mat = None
                    error = None
                    self.data_sn = None
                    with self.confirm_lock:
                        self.is_confirm_ret = True
                    result = None
                    self.is_check_gen_id = False
                    self.setTextLabelSignal.emit(self.label_scanner, '')
                    self.set_trigger_off()
                    step = Step.CHECK_SENSOR_OFF.value
                
                elif step == Step.CHECK_SENSOR_OFF.value:
                    if not self.is_sensor_on:
                        time.sleep(delay_io)
                        self.showResultStatus.emit(StepResult.WAIT_PRODUCT.value)
                        self.set_io_result(StepResult.WAIT.value)
                        step = Step.CHECK_SENSOR_ON.value
                    
                elif step == Step.ERROR.value:
                    self.main_logger.warning(Step.ERROR.value)
                    if error:
                        self.main_logger.error(error)
                        self.showResultStatus.emit(StepResult.FAIL.value)  
                        self.set_io_result(StepResult.FAIL.value)  
                        self.active_output = OutPorts.Out_2
                        self.db.add_entry(self.log_table, Model=self.combo_box_model_name_teaching.currentText(), 
                                        SeriesNumber='', 
                                        Source='', Destination='', 
                                        Return='', Error=error)
                    step = Step.RELEASE.value  

            
            except Exception as ex:
                error = str(ex)
                step = Step.ERROR.value 
            
            if not self.b_start:
                break
    
            time.sleep(0.01)
    def add_log(self, message):
        item = QStandardItem(message)

    # # Xác định màu dựa trên mức độ log
    #     if "DEBUG" in message:
    #         item.setBackground(QColor("#E0FFFF"))  # Nền xanh nhạt (Light Cyan)
    #         item.setForeground(QColor("#000000"))  # Chữ đen

    #     elif "INFO" in message:
    #         item.setBackground(QColor("#DFFFD6"))  # Nền xanh lá nhạt
    #         item.setForeground(QColor("#000000"))  # Chữ đen

    #     elif "WARNING" in message:
    #         item.setBackground(QColor("#FFFACD"))  # Nền vàng nhạt
    #         item.setForeground(QColor("#000000"))  # Chữ đen

    #     elif "ERROR" in message:
    #         item.setBackground(QColor("#FF6347"))  # Nền đỏ cam
    #         item.setForeground(QColor("#FFFFFF"))  # Chữ trắng

    #     elif "CRITICAL" in message:
    #         item.setBackground(QColor("#8B0000"))  # Nền đỏ đậm
    #         item.setForeground(QColor("#FFFFFF"))  # Chữ trắng

        self.log_model.appendRow(item)
        self.list_log_view.scrollToBottom()
        # self.list_log_view_2.scrollToBottom()
        
    def saveSettings(self):
        """Lưu trạng thái layout vào file settings.ini"""
        settings = QSettings("settings.ini", QSettings.IniFormat)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("combo_box_index", self.combo_box_model_name_teaching.currentIndex())
        settings.setValue("combo_box_index_auto", self.combo_box_model_name_auto.currentIndex())

    def loadSettings(self):
        settings = QSettings("settings.ini", QSettings.IniFormat)

        geometry = settings.value("geometry", QByteArray())
        windowState = settings.value("windowState", QByteArray())

        if isinstance(geometry, QByteArray) and not geometry.isEmpty():
            self.restoreGeometry(geometry)

        if isinstance(windowState, QByteArray) and not windowState.isEmpty():
            self.restoreState(windowState)
            
        self.combo_box_model_name_teaching.setCurrentIndex(int(settings.value("combo_box_index", 0)))
        self.combo_box_model_name_auto.setCurrentIndex(int(settings.value("combo_box_index_auto", 0)))

    def resetLayout(self):
        confirm = QMessageBox.question(self, "Reset Layout", 
                                       "Bạn có chắc chắn muốn đặt lại bố cục về mặc định không?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.is_resetting = True
            settings = QSettings("settings.ini", QSettings.IniFormat)
            settings.clear()  # Xóa tất cả dữ liệu đã lưu
            QMessageBox.information(self, "Thông báo", "Đã đặt lại bố cục. Ứng dụng sẽ khởi động lại.")
            self.restartApp()
    
    def upload_model_ai(self):
        model_dir = "res/Model_AI"
        model_names = [name for name in os.listdir(model_dir) if name.endswith((".pt", ".pth"))]
        classes_names = [name for name in os.listdir(model_dir) if name.endswith((".txt"))]
        self.combo_box_model_ai.clear()
        self.combo_box_model_ai.addItems(model_names)
        self.combo_box_classes_ai.clear()
        self.combo_box_classes_ai.addItems(classes_names)
        
    def upload_model_names(self):
        model_dir = "Model"
        model_names = [name for name in os.listdir(model_dir)]
        self.combo_box_model_name_teaching.clear()
        self.combo_box_model_name_teaching.addItems(model_names)
        self.combo_box_model_name_auto.clear()
        self.combo_box_model_name_auto.addItems(model_names)
        self.combo_box_model_name_data.addItems(model_names)
        
    def upload_feature_camera(self):
        feature_dir = "res/Camera"
        feature_names = [name for name in os.listdir(feature_dir) if name.endswith((".ini"))]
        self.combo_box_feature_camera.clear()
        self.combo_box_feature_camera.addItems(feature_names)
        
    def update_label_status(self, status):
        self.label_result.setText(status)
        self.label_result.setProperty("status", status)
        self.label_result.style().polish(self.label_result)

    def update_label_result(self, ret):
        self.count_product_total += 1
        if ret == "PASS":
            self.count_product_ok += 1
        else:
            self.count_product_ng += 1
        
        if self.count_product_total != 0:
            rate = round(self.count_product_ok / self.count_product_total, 2)
            
        self.label_ok.setText(str(self.count_product_ok))
        self.label_ng.setText(str(self.count_product_ng))
        self.label_total.setText(str(self.count_product_total))
        self.label_rate.setText(str(rate))
    
    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        
        self.combo_box_com_controller.clear()
        self.combo_box_com_controller_2.clear()
        self.combo_box_com_controller_3.clear()
        self.combo_box_com_controller_4.clear()
        self.combo_box_com_controller.addItems([port.device for port in ports])
        self.combo_box_com_controller_2.addItems([port.device for port in ports])
        self.combo_box_com_controller_3.addItems([port.device for port in ports])
        self.combo_box_com_controller_4.addItems([port.device for port in ports])
        
        self.combo_box_baudrate_controller.clear()
        self.combo_box_baudrate_controller_2.clear()
        self.combo_box_baudrate_controller_3.clear()
        self.combo_box_baudrate_controller_4.clear()
        self.combo_box_baudrate_controller.addItems(list(map(str, serial.Serial.BAUDRATES)))
        self.combo_box_baudrate_controller_2.addItems(list(map(str, serial.Serial.BAUDRATES)))
        self.combo_box_baudrate_controller_3.addItems(list(map(str, serial.Serial.BAUDRATES)))
        self.combo_box_baudrate_controller_4.addItems(list(map(str, serial.Serial.BAUDRATES)))
        
        devices = get_camera_devices()
        self.combo_box_id_camera.clear()
        self.combo_box_id_camera.addItems(list(devices.keys()))
        
    
    def get_config_from_ui(self):
        config = SimpleNamespace(
            name_model = self.combo_box_model_name_teaching.currentText(),
            
            shapes = self.get_shapes(self.teaching_canvas),
            
            model_ai=SimpleNamespace(
                model_name=self.combo_box_model_ai.currentText(),
                classes_name=self.combo_box_classes_ai.currentText(),
                threshold=self.line_edit_threshold.text(),
            ),            
            
            hardware=SimpleNamespace(
                server=SimpleNamespace(
                    ip=self.line_edit_ip_server.text(),
                    port=self.line_edit_port_server.text()
                ),

                camera=SimpleNamespace(
                    id=self.combo_box_id_camera.currentText(),
                    feature=self.combo_box_feature_camera.currentText(),
                    name=self.combo_box_name_camera.currentText()
                ),

                lighting=SimpleNamespace(
                    comport=self.combo_box_com_controller.currentText(),
                    baudrate=self.combo_box_baudrate_controller.currentText(),
                    channel_value_0=self.spin_box_channel_value_0.value(),
                    channel_value_1=self.spin_box_channel_value_1.value(),
                    channel_value_2=self.spin_box_channel_value_2.value(),
                    channel_value_3=self.spin_box_channel_value_3.value(),
                    controller=self.combo_box_light_controller.currentText(),
                    delay=self.spin_box_delay_controller.value()
                ),

                system=SimpleNamespace(
                    log_dir=self.line_edit_log_dir.text(),
                    log_size=self.spin_box_log_size.value(),
                    auto_start=self.check_box_auto_start.isChecked(),
                    database_path=self.line_edit_database_path.text()
                ),

                io=SimpleNamespace(
                    comport=self.combo_box_com_controller_2.currentText(),
                    baudrate=self.combo_box_baudrate_controller_2.currentText(),
                    delay=self.line_edit_time_delay_io.text()
                ),
                
                scanner=SimpleNamespace(
                    comport=self.combo_box_com_controller_3.currentText(),
                    baudrate=self.combo_box_baudrate_controller_3.currentText()
                ),
                
                send_data=SimpleNamespace(
                    comport=self.combo_box_com_controller_4.currentText(),
                    baudrate=self.combo_box_baudrate_controller_4.currentText()
                )
            )
        )

        return config
    
    def set_config_teaching(self, config):
        
        # self.combo_box_model_name_teaching.setCurrentText(config.get("name_model", ""))
        
        self.set_shapes(self.teaching_canvas, config.get("shapes", {}))
        
        model_ai = config.get("model_ai", {})
        self.combo_box_model_ai.setCurrentText(model_ai.get("model_name", ""))
        self.combo_box_classes_ai.setCurrentText(model_ai.get("classes_name", ""))
        self.line_edit_threshold.setText(model_ai.get("threshold", ""))
        
        hardware = config.get("hardware", {})

        # Cập nhật Server
        server_config = hardware.get("server", {})
        self.line_edit_ip_server.setText(server_config.get("ip", ""))
        self.line_edit_port_server.setText(server_config.get("port", ""))

        # Cập nhật Camera
        camera_config = hardware.get("camera", {})
        self.combo_box_id_camera.setCurrentText(camera_config.get("id", ""))
        self.combo_box_feature_camera.setCurrentText(camera_config.get("feature", ""))
        self.combo_box_name_camera.setCurrentText(camera_config.get("name", ""))

        # Cập nhật Lighting
        lighting_config = hardware.get("lighting", {})
        self.combo_box_com_controller.setCurrentText(lighting_config.get("comport", ""))
        self.combo_box_baudrate_controller.setCurrentText(lighting_config.get("baudrate", ""))
        self.spin_box_channel_value_0.setValue(lighting_config.get("channel_value_0", 0))
        self.spin_box_channel_value_1.setValue(lighting_config.get("channel_value_1", 0))
        self.spin_box_channel_value_2.setValue(lighting_config.get("channel_value_2", 0))
        self.spin_box_channel_value_3.setValue(lighting_config.get("channel_value_3", 0))
        self.combo_box_light_controller.setCurrentText(lighting_config.get("controller", ""))
        self.spin_box_delay_controller.setValue(lighting_config.get("delay", 0))

        # Cập nhật System
        system_config = hardware.get("system", {})
        self.line_edit_log_dir.setText(system_config.get("log_dir", ""))
        self.spin_box_log_size.setValue(system_config.get("log_size", 0))
        self.check_box_auto_start.setChecked(system_config.get("auto_start", False))
        self.line_edit_database_path.setText(system_config.get("database_path", ""))
        
        #Cập nhật IO/Controller
        io_config = hardware.get("io", {})
        self.combo_box_com_controller_2.setCurrentText(io_config.get("comport", ""))
        self.combo_box_baudrate_controller_2.setCurrentText(io_config.get("baudrate", ""))
        self.line_edit_time_delay_io.setText(io_config.get("delay", ""))
        
        #Cập nhật scanner
        scanner_config = hardware.get("scanner", {})
        self.combo_box_com_controller_3.setCurrentText(scanner_config.get("comport", ""))
        self.combo_box_baudrate_controller_3.setCurrentText(scanner_config.get("baudrate", ""))
        
        send_data_config = hardware.get("send_data", {})
        self.combo_box_com_controller_4.setCurrentText(send_data_config.get("comport", ""))
        self.combo_box_baudrate_controller_4.setCurrentText(send_data_config.get("baudrate", ""))
    
    
    def get_config_auto(self, model_name):
        config_data = self.handle_file_json.load(model_name)
        
        model_ai_config = config_data.get('model_ai', {})
        
        hardware = config_data.get("hardware", {})

        # Cấu hình Server
        server_config = hardware.get("server", {})

        # Cấu hình Camera
        camera_config = hardware.get("camera", {})

        # Cấu hình Lighting
        lighting_config = hardware.get("lighting", {})

        # Cấu hình System
        system_config = hardware.get("system", {})

        # Cấu hình IO/Controller
        io_config = hardware.get("io", {})
        
        scanner_config = hardware.get("scanner", {})
        
        send_data_config = hardware.get("send_data", {}) 

        config = SimpleNamespace(
            
            name_model = config_data.get("name_model", {}),
            
            shapes = config_data.get("shapes", {}),
            
            model_ai=SimpleNamespace(
                model_name=model_ai_config.get("model_name", ""),
                classes_name=model_ai_config.get("classes_name", ""),
                threshold=model_ai_config.get("threshold", ""),
            ),

            hardware=SimpleNamespace(  # Thêm hardware vào config
                server=SimpleNamespace(
                    ip=server_config.get("ip", ""),
                    port=server_config.get("port", "")
                ),
                
                camera=SimpleNamespace(
                    id=camera_config.get("id", ""),
                    feature=camera_config.get("feature", ""),
                    name=camera_config.get("name", "")
                ),
                
                lighting=SimpleNamespace(
                    comport=lighting_config.get("comport", ""),
                    baudrate=lighting_config.get("baudrate", ""),
                    channel_value_0=lighting_config.get("channel_value_0", 0),
                    channel_value_1=lighting_config.get("channel_value_1", 0),
                    channel_value_2=lighting_config.get("channel_value_2", 0),
                    channel_value_3=lighting_config.get("channel_value_3", 0),
                    controller=lighting_config.get("controller", ""),
                    delay=lighting_config.get("delay", 0),
                ),
                
                system=SimpleNamespace(
                    log_dir=system_config.get("log_dir", ""),
                    log_size=system_config.get("log_size", 0),
                    auto_start=system_config.get("auto_start", False),
                    database_path=system_config.get("database_path", "")
                ),
                
                io=SimpleNamespace(
                    comport=io_config.get("comport", ""),
                    baudrate=io_config.get("baudrate", ""),
                    delay=io_config.get("delay", "")
                ),
                
                scanner=SimpleNamespace(
                    comport=scanner_config.get("comport", ""),
                    baudrate=scanner_config.get("baudrate", "")
                ),
                
                send_data=SimpleNamespace(
                    comport=send_data_config.get("comport", ""),
                    baudrate=send_data_config.get("baudrate", "")
                )
            )
        )

        return config
     
    def load_model_change_teaching(self):
        name_model = self.combo_box_model_name_teaching.currentText()
        if name_model and self.combo_box_model_name_teaching.findText(name_model) == -1:
            QMessageBox.warning(self, 'Warning', 'Tên mô hình không đúng', QMessageBox.StandardButton.Close)
            return
        config = self.handle_file_json.load(file_path=f'Model/{name_model}')
        self.set_config_teaching(config)
        
    def open_camera_teaching(self):
        name_camera = self.combo_box_name_camera.currentText()
        id_camera=self.combo_box_id_camera.currentText()
        feature_camera=self.combo_box_feature_camera.currentText()
        success = self.camera.open_camera(name_camera, config={
            'id': id_camera,
            'feature': f'res/Camera/{feature_camera}'
        })
        if not success:
            return
        self.is_open_camera = True
        self.but_start_camera_teaching.setDisabled(False)
            
    
    def close_camera_teaching(self):
        self.camera.close_camera()
        self.is_open_camera = False
        self.is_showing_camera = False
        self.but_start_camera_teaching.setDisabled(True)
    
    def start_camera_teaching(self):
        try:
            self.is_showing_camera = True
            threading.Thread(target=self.loop_live_camera, args=(self.camera, ), daemon=True).start()
            # self.start_camera(self.camera)
            self.main_logger.info('Camera is starting')
        except Exception as ex:
            self.main_logger.error(f'Failed to show camera. Error{ex}')
    
    def stop_camera_teaching(self):
        try:
            self.is_showing_camera = False
            # self.stop_camera()
            self.main_logger.info('Camera was stoped')
        except Exception as ex:
            self.main_logger.error(f'Failed to stop camera. Error{ex}')
    
    def connect_server_teaching(self):
        ip = self.line_edit_ip_server.text()
        port = self.line_edit_port_server.text()
        self.server.start_server(ip, int(port))
        if not self.server.is_connected:
            return
        self.is_connect_server = True
    
    def close_server_teaching(self):
        self.server.stop_server()
        self.is_connect_server = False

    def open_light_auto(self):
        controller = self.config_auto.hardware.lighting.controller
        comport = self.config_auto.hardware.lighting.comport
        baudrate = self.config_auto.hardware.lighting.baudrate
        channel_0 = self.config_auto.hardware.lighting.channel_value_0
        channel_1 = self.config_auto.hardware.lighting.channel_value_1
        channel_2 = self.config_auto.hardware.lighting.channel_value_2
        channel_3 = self.config_auto.hardware.lighting.channel_value_3
        delay = self.config_auto.hardware.lighting.delay
        
        if controller == 'DCPController':
            self.light = DCPController(comport)
        else:
            self.light = LCPController(comport)
            
        self.light.light_logger.signalLog.connect(self.add_log)   
                 
        if not self.light.open():
            return False, []
        
        return True, [channel_0, channel_1, channel_2, channel_3, delay]
        
    def open_light_teaching(self):
        controller = self.combo_box_light_controller.currentText()
        comport = self.combo_box_com_controller.currentText()
        baudrate = self.combo_box_baudrate_controller.currentText()
        channel_0 = self.spin_box_channel_value_0.value()
        channel_1 = self.spin_box_channel_value_1.value()
        channel_2 = self.spin_box_channel_value_2.value()
        channel_3 = self.spin_box_channel_value_3.value()
        delay = self.spin_box_delay_controller.value()
            
        if controller == 'DCPController':
            self.light = DCPController(comport)
        else:
            self.light = LCPController(comport)
            
        self.light.light_logger.signalLog.connect(self.add_log)
                       
        if not self.light.open():
            return False
        
        self.set_light_value(channel_0, channel_1, channel_2, channel_3)
        time.sleep(delay / 1000)
        
        return True
    
    def set_light_value(self, channel_0=0, channel_1=0, channel_2=0, channel_3=0):
        self.light.set_light_value(0, channel_0)
        self.light.set_light_value(1, channel_1)
        self.light.set_light_value(2, channel_2)
        self.light.set_light_value(3, channel_3)
    
    def update_light_value(self):
        if hasattr(self, 'light') and self.but_open_light.property("status") == "Close":
            channel_0 = self.spin_box_channel_value_0.value()
            channel_1 = self.spin_box_channel_value_1.value()
            channel_2 = self.spin_box_channel_value_2.value()
            channel_3 = self.spin_box_channel_value_3.value()
            
            self.light.set_light_value(0, channel_0)
            self.light.set_light_value(1, channel_1)
            self.light.set_light_value(2, channel_2)
            self.light.set_light_value(3, channel_3)
    
    def connect_io_controller(self):
        com = self.combo_box_com_controller_2.currentText()
        
        baud = self.combo_box_baudrate_controller_2.currentText()
        
        self.io_controller = IOController(com=com, baud=int(baud))
        
        self.io_controller.io_logger.signalLog.connect(self.add_log)
        
        self.io_controller.inputSignalOnToOff.connect(self.on_to_off)
        
        self.io_controller.inputSignalOffToOn.connect(self.off_to_on)
        
        self.io_controller.checkSignalOn.connect(self.set_trigger_on)
        
        self.io_controller.checkSensorOn.connect(self.sensor_on)
        
        self.io_controller.checkSensorOff.connect(self.sensor_off)
        
        if self.io_controller.open():
            self.is_connect_io_controller = True
            
        else:
            self.is_connect_io_controller = False
    
    def close_io_controller(self):
        self.close_all_io_controller()
        self.set_trigger_off()
        self.set_io_result(StepResult.WAIT.value)
        self.showResultStatus.emit(StepResult.WAIT.value)
        self.io_controller.close()
    
    def close_all_io_controller(self):
        self.io_controller.write_out(OutPorts.Out_1, PortState.Off)
        self.io_controller.write_out(OutPorts.Out_3, PortState.Off)
        self.io_controller.write_out(OutPorts.Out_2, PortState.Off)
        self.io_controller.write_out(OutPorts.Out_4, PortState.Off)
        self.io_controller.write_out(OutPorts.Out_5, PortState.Off)
        self.io_controller.write_out(OutPorts.Out_6, PortState.Off)
        self.io_controller.write_out(OutPorts.Out_7, PortState.Off)
        self.io_controller.write_out(OutPorts.Out_8, PortState.Off)
    
    def set_io_result(self, ret):
        if ret == StepResult.PASS_.value:
            self.io_controller.write_out(OutPorts.Out_2, PortState.Off)
            time.sleep(0.02)
            self.io_controller.write_out(OutPorts.Out_3, PortState.Off)
            time.sleep(0.02)
            self.io_controller.write_out(OutPorts.Out_1, PortState.On)
            self.active_output = OutPorts.Out_1
            
        elif ret == StepResult.WAIT.value:
            self.io_controller.write_out(OutPorts.Out_1, PortState.Off)
            time.sleep(0.02)
            self.io_controller.write_out(OutPorts.Out_2, PortState.Off)
            time.sleep(0.02)
            self.io_controller.write_out(OutPorts.Out_3, PortState.On)
            self.active_output = OutPorts.Out_3
            
        else:
            self.io_controller.write_out(OutPorts.Out_1, PortState.Off)
            time.sleep(0.02)
            self.io_controller.write_out(OutPorts.Out_3, PortState.Off)
            time.sleep(0.02)
            self.io_controller.write_out(OutPorts.Out_2, PortState.On)
            self.active_output = OutPorts.Out_2
    
    def update_io_display(self, commands, states):
        self.plain_text_edit_io_monitoring.clear()

        lines = []  # Danh sách chứa từng hàng dữ liệu
        row = ""  # Lưu trạng thái trên một hàng
        
        for i, (cmd, state) in enumerate(zip(commands, states), start=1):
            row += f"{cmd}: {state.name}".ljust(20)  # Canh lề đẹp
            if i % 3 == 0:  # Mỗi hàng có 3 trạng thái
                lines.append(row)
                row = ""  # Reset hàng mới
        
        if row:  # Nếu còn dữ liệu chưa đủ 3 cột, thêm vào hàng cuối
            lines.append(row)
        
        self.plain_text_edit_io_monitoring.setPlainText("\n".join(lines))
        
    def on_to_off(self, commands):
        for cmd in commands:
            index = list(InPorts).index(InPorts[cmd])  # Lấy chỉ số từ enum InPorts
            self.input_labels[index].setStyleSheet("background-color: gray; color: white; padding: 5px;")

    def off_to_on(self, commands):
        for cmd in commands:
            index = list(InPorts).index(InPorts[cmd])  # Lấy chỉ số từ enum InPorts
            self.input_labels[index].setStyleSheet("background-color: green; color: white; padding: 5px;")  # Đổi màu thành đỏ
    
    def sensor_on(self):
        self.is_sensor_on = True
        print('sensor on')
    
    def sensor_off(self):
        self.is_sensor_on = False
        print('sensor off')
        
    def close_light_teaching(self): 
        if not self.light.close():
            return False
        return True
   
    def read_signal_scanner(self, code):
        if not self.is_check_sn:
            if code == "CheckOCDU":
                self.set_trigger_on()
                return
            
            if code is not None and code.startswith("S") and len(code) == 10:
                if self.find_series_number(code):
                    self.data_sn = code
                    self.hide_sn_failed()
                else:
                    self.show_sn_failed(check_repeat=True)
                return
                    
            else:
                self.show_sn_failed()
                return
        else:
            if not self.check_gen_id(code):
                self.show_message_scan_gen()
                self.is_check_gen_id = False
                return
            self.is_check_gen_id = True 
   
    def show_sn_failed(self, check_repeat=False):
        if hasattr(self, 'msg_box_show_sn_failed') and self.msg_box_show_sn_failed is not None:
            self.hide_sn_failed()

        self.msg_box_show_sn_failed = QMessageBox(self)
        self.msg_box_show_sn_failed.setIcon(QMessageBox.Warning)
        self.msg_box_show_sn_failed.setWindowTitle("Warning")
        if check_repeat:
            self.msg_box_show_sn_failed.setText("Mã S/N đã được sử dụng, vui lòng thực hiện lại")
        else:  
            self.msg_box_show_sn_failed.setText("Scan sai định dạng S/N, vui lòng thực hiện lại")
        self.msg_box_show_sn_failed.setStandardButtons(QMessageBox.Cancel)
        self.msg_box_show_sn_failed.show()

        # # Tự động đóng sau 3 giây
        # QTimer.singleShot(3000, self.hide_sn_failed)

    def hide_sn_failed(self):
        if hasattr(self, 'msg_box_show_sn_failed') and self.msg_box_show_sn_failed is not None:
            self.msg_box_show_sn_failed.close()
            self.msg_box_show_sn_failed = None
    
    def show_message_scan_gen(self):
        if hasattr(self, 'msg_box_show_scan_gen') and self.msg_box_show_scan_gen is not None:
            self.hide_message_scan_gen()

        self.msg_box_show_scan_gen = QMessageBox(self)
        self.msg_box_show_scan_gen.setIcon(QMessageBox.Warning)
        self.msg_box_show_scan_gen.setWindowTitle("Warning")
        self.msg_box_show_scan_gen.setText("Scan QR trên thẻ nhân viên để xác nhận")
        self.msg_box_show_scan_gen.show()
    
    def hide_message_scan_gen(self):
        if hasattr(self, 'msg_box_show_scan_gen') and self.msg_box_show_scan_gen is not None:
            self.msg_box_show_scan_gen.close()
            self.msg_box_show_scan_gen = None   
    
    def recheck_result(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Question')
        msg_box.setText('Kết quả là FAIL, bạn có muốn tiếp tục không?')

        ok_button = QPushButton('Xác nhận OK')
        ng_button = QPushButton('Xác nhận NG')
        ng_button.setStyleSheet("""
        QPushButton {
            background-color: red;
            color: white;
        }
        QPushButton:hover {
            background-color: darkred;
        }
        """)

        msg_box.addButton(ok_button, QMessageBox.YesRole)
        msg_box.addButton(ng_button, QMessageBox.NoRole)
        msg_box.setDefaultButton(ng_button)

        msg_box.exec_()

        if msg_box.clickedButton() == ok_button:
            self.is_confirm_ret = True
        else:
            self.is_confirm_ret = False
            
        self.is_check_sn = True
        self.show_message_scan_gen()

    def set_text_label(self, label: QLabel, text):
        label.setText(text)

    def check_gen_id(self, code):
        if code is not None and re.fullmatch(r'(0[8-9]|[1-9][0-9])\d{6}', code):
            self.hide_message_scan_gen()
            confirm = 'PASS' if self.is_confirm_ret else 'FAIL'
            self.main_logger.info(f'Gen: {code} xác nhận {confirm}')
            return True
        else:
            return False
    
    def set_trigger_on(self):
        self.trigger_on = True
    
    def set_trigger_off(self):
        self.trigger_on = False
    
    def start_process(self):
        time.sleep(0.2)
        self.b_start = True
        threading.Thread(target=self.thread_loop_auto, daemon=True).start()
    
    def stop_process(self):
        self.b_start = False
        
    def convert_path(self, relative_path):
        base_path = os.getcwd()
        absolute_path = os.path.join(base_path, relative_path.replace("/", "\\"))
        return absolute_path

    def get_selected_items(self):
        selected_row = self.table_widget_database.currentRow()  # Lấy hàng hiện tại đang được chọn

        if selected_row != -1:  # Kiểm tra có hàng nào được chọn không
            item_col2 = self.table_widget_database.item(selected_row, 2)  # Cột 2 (index 2)
            item_col3 = self.table_widget_database.item(selected_row, 3)  # Cột 3 (index 3)

            src = item_col2.text() if item_col2 else "None"
            dst = item_col3.text() if item_col3 else "None"
            if not src or not dst:
                return
            img_src = cv2.imread(src)
            img_dst = cv2.imread(dst)
            
            self.show_image(self.data_image_input_canvas, img_src)
            self.show_image(self.data_image_output_canvas, img_dst)
    
    def load_database(self, file_path=None):
        if not file_path:
            return

        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM users")  # Lấy dữ liệu từ bảng `users`
            rows = cursor.fetchall()  # Lấy tất cả kết quả
            columns = [desc[0] for desc in cursor.description]  # Lấy tên cột

            if "id" in columns:
                id_index = columns.index("id")  # Lấy vị trí của cột 'id'
                columns.pop(id_index)  # Xóa khỏi danh sách cột
                rows = [tuple(value for i, value in enumerate(row) if i != id_index) for row in rows]
                
            # Cập nhật tableWidget
            self.table_widget_database.setRowCount(len(rows))  # Số hàng
            self.table_widget_database.setColumnCount(len(columns))  # Số cột
            self.table_widget_database.setHorizontalHeaderLabels(columns)  # Đặt tên cột

            for row_idx, row_data in enumerate(rows):
                for col_idx, col_data in enumerate(row_data):
                    self.table_widget_database.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

            conn.close()  # Đóng kết nối

        except Exception as e:
            print(f"Lỗi khi load dữ liệu: {e}")
    
    def load_classes_ai(self, table: QTableWidget, file_path: str):
        file_path = f'res/Model_AI/{file_path}'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.lines_classes = f.read().splitlines()
                
            self.row_count = len(self.lines_classes)
               
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(["STT", "Label", "Số lượng", "Check", "Result", "Error"])
            table.setRowCount(self.row_count)

            for i, line in enumerate(self.lines_classes):
                try:
                    left, count = line.rsplit(" ", 1)
                    index, label = left.split("_", 1)
                    count = int(count)
                except ValueError:
                    print(f"⚠️ Dòng sai định dạng: {line}")
                    continue

                # STT
                item_index = QTableWidgetItem(index)
                item_index.setFlags(item_index.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 0, item_index)

                # Label
                item_label = QTableWidgetItem(label)
                item_label.setFlags(item_label.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 1, item_label)

                # Số lượng (editable)
                item_count = QTableWidgetItem(str(count))
                item_count.setFlags(item_count.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 2, item_count)

                item_check = QTableWidgetItem("")
                item_check.setFlags(item_check.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 3, item_check)

                # Return (có thể chỉnh sửa)
                item_return = QTableWidgetItem("")
                item_return.setFlags(item_return.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 4, item_return)
                
                item_error = QTableWidgetItem("")
                item_error.setFlags(item_error.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 5, item_error)
                
            # table.setSpan(0, 4, self.row_count, 1)
            table.setSpan(0, 5, self.row_count, 1)
            
        except Exception as e:
            print(f"❌ Lỗi khi đọc file: {e}")
    
    def load_result_classes(self, table, label_counts: dict, ret: str, error: str):
        labels = list(label_counts.keys())
        count_status_list = [(info["count"], info["status"]) for info in label_counts.values()]

        missing_materials = []  # Danh sách các vật liệu thiếu

        for i, line in enumerate(self.lines_classes):
            item_check = QTableWidgetItem(str(count_status_list[i][0]))
            item_check.setFlags(item_check.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 3, item_check)

            item_return = QTableWidgetItem(count_status_list[i][1])
            item_return.setFlags(item_return.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 4, item_return)

            item_error = QTableWidgetItem(error)
            item_error.setFlags(item_error.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 5, item_error)

            if count_status_list[i][1].upper() == "FAIL":
                item = table.item(i, 4)
                if item:
                    item.setBackground(QBrush(QColor("#FF3B30")))  # Màu đỏ nhạt phù hợp với nền tối
                    item.setForeground(QBrush(QColor("#FFFFFF")))  # Màu chữ trắng
                if item_return:  # Kiểm tra item_return để tránh lỗi
                    item_return.setForeground(QBrush(QColor("#FFFFFF")))  # Màu chữ trắng
                    item_return.setBackground(QBrush(QColor("#FF3B30")))  # Màu đỏ nhạt
                # Thêm vào danh sách vật liệu thiếu
                missing_materials.append(labels[i])
            else:
                item = table.item(i, 4)
                if item:
                    item.setBackground(QBrush(QColor("#34C759")))  # Màu xanh lá nhạt phù hợp với nền tối
                    item.setForeground(QBrush(QColor("#FFFFFF")))  # Màu chữ trắng
                if item_return:  # Kiểm tra item_return để tránh lỗi
                    item_return.setForeground(QBrush(QColor("#FFFFFF")))  # Màu chữ trắng
                    item_return.setBackground(QBrush(QColor("#34C759")))  # Màu xanh lá nhạt

        table.setSpan(0, 5, self.row_count, 1)

        # Nếu có vật liệu thiếu, hiện QMessageBox
        with self.confirm_lock:
            if not self.is_confirm_ret:
                if missing_materials:
                    QMessageBox.warning(
                        self, 
                        "Thiếu vật liệu", 
                        "Thiếu các vật liệu sau:\n- " + "\n- ".join(missing_materials) + 
                        "\n\nVui lòng kiểm tra lại và so sánh với WI."
                    )


    
    def set_disable_auto(self, ret):
        self.but_open_camera_teaching.setDisabled(ret)
        self.but_connect_server.setDisabled(ret)
        self.but_open_io_controller.setDisabled(ret)
        self.but_connect_scanner.setDisabled(ret)
        self.but_open_com_send_data.setDisabled(ret)
        
        self.combo_box_feature_camera.setDisabled(ret)
        self.combo_box_id_camera.setDisabled(ret)
        self.combo_box_name_camera.setDisabled(ret)
        self.combo_box_com_controller_2.setDisabled(ret)
        self.combo_box_com_controller_3.setDisabled(ret)
        self.combo_box_com_controller.setDisabled(ret)
        self.combo_box_com_controller_4.setDisabled(ret)
        self.combo_box_baudrate_controller.setDisabled(ret)
        self.combo_box_baudrate_controller_2.setDisabled(ret)
        self.combo_box_baudrate_controller_3.setDisabled(ret)
        self.combo_box_baudrate_controller_4.setDisabled(ret)
        self.combo_box_model_ai.setDisabled(ret)
        self.combo_box_classes_ai.setDisabled(ret)
        
        self.line_edit_ip_server.setDisabled(ret)
        self.line_edit_port_server.setDisabled(ret)
        self.line_edit_threshold.setDisabled(ret)
        self.line_edit_time_delay_io.setDisabled(ret)
    
    def write_log_async(self, mat, result, code):
        # Tạo bản sao độc lập để thread sử dụng
        mat_copy = copy.deepcopy(mat)
        result_copy = copy.deepcopy(result)
        code_copy = code

        def log_task():
            try:
                src_path = self.main_logger.log_image('Source',  mat_copy, code_copy, result_copy.ret)
                src_convert = self.convert_path(src_path)

                path_dst = self.combo_box_model_name_teaching.currentText()
                
                dst_path = self.main_logger.log_image(path_dst, result_copy.output_image, 
                                                      code_copy, result_copy.ret, log_csv=True)
                
                dst_convert = self.convert_path(dst_path)

                self.db.add_entry(self.log_table, Model=path_dst, SeriesNumber=result_copy.seri, 
                                Source=src_convert, Destination=dst_convert, 
                                Return=result_copy.ret, Error=result_copy.error)
            except Exception as e:
                self.main_logger.error(f"Error writing log: {e}")

        threading.Thread(target=log_task, daemon=True).start()
    
    def get_shapes(self, canvas: Canvas):
        shapes: list[MyShape] = canvas.shapes
        shape_config = {}
        
        for s in shapes:
            shape_config[s.label] = s.cvBox
        print(shape_config)
        return shape_config
    
    def set_shapes(self, canvas: Canvas, shape_config):
        canvas.clear()
        for label in shape_config:
            s = self.new_shape(label, shape_config[label])
            canvas.shapes.append(s)
            
    def new_shape(self, label, box):
        s = MyShape(label)
        x, y, w, h = box
        s.points = [
            QPointF(x, y),
            QPointF(x + w, y),
            QPointF(x + w, y + h),
            QPointF(x, y + h)            
        ]
        return s
     
    def find_database(self):
        try:
            conn = sqlite3.connect(self.file_path_database)
            cursor = conn.cursor()

            # Tạo câu truy vấn ban đầu
            query = "SELECT * FROM users WHERE Time BETWEEN ? AND ?"
            params = [
                self.date_time_from.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                self.date_time_to.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            ]

            # Lọc theo result
            result_filter = self.combo_box_result_data.currentText()
            if result_filter != "ALL":
                query += " AND Return = ?"
                params.append(result_filter)

            # Lọc theo model
            model_filter = self.combo_box_model_name_data.currentText().strip()
            if model_filter != "ALL":
                query += " AND Model = ?"
                params.append(model_filter)

            # Tìm theo keyword trong Source, Destination, Error
            keyword_filter = self.line_edit_keyword_data.text().strip()
            if keyword_filter:
                query += " AND ("
                keyword_conditions = []
                for column in ["SeriesNumber", "Source", "Destination", "Return", "Error"]:
                    keyword_conditions.append(f"{column} LIKE ?")
                    params.append(f"%{keyword_filter}%")
                query += " OR ".join(keyword_conditions) + ")"
                
            cursor.execute(query, params)
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]  

            if "id" in columns:
                id_index = columns.index("id")
                columns.pop(id_index)
                rows = [tuple(value for i, value in enumerate(row) if i != id_index) for row in rows]

            self.table_widget_database.setRowCount(len(rows))  # Số hàng
            self.table_widget_database.setColumnCount(len(columns))  # Số cột
            self.table_widget_database.setHorizontalHeaderLabels(columns)  # Đặt tên cột

            for row_idx, row_data in enumerate(rows):
                for col_idx, col_data in enumerate(row_data):
                    self.table_widget_database.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

            conn.close()

        except Exception as e:
            print(f"Lỗi khi tìm kiếm dữ liệu: {e}")
    
    def find_series_number(self, series_number):
        try:
            conn = sqlite3.connect(self.file_path_database)
            cursor = conn.cursor()

            # Tạo câu truy vấn để tìm SeriesNumber
            query = "SELECT * FROM users WHERE SeriesNumber = ?"
            cursor.execute(query, (series_number,))
            rows = cursor.fetchall()

            conn.close()

            # Nếu không tìm thấy bất kỳ dòng nào, trả về True (không có SeriesNumber)
            if not rows:
                return True
            else:
                return False  # Nếu có ít nhất một dòng có SeriesNumber, trả về False

        except Exception as e:
            print(f"Lỗi khi tìm kiếm SeriesNumber: {e}")
            return False
    
    def show_effect(self, dt=3):
        self.progressBar.setValue(0)
        # self.ui.progressBar.move((self.width() - self.ui.progressBar.width()) // 2, (self.height() - self.ui.progressBar.height()) // 2)
        self.progressBar.setVisible(True)
        for i in range(1, 100):
            QTimer.singleShot(dt*i, lambda value=i: self.progressBar.setValue(value))

    def hide_effect(self, timeout=500):
        QTimer.singleShot(10, partial(self.progressBar.setValue, 100))
        QTimer.singleShot(timeout, partial(self.progressBar.setVisible, False))
        
    def reload_qss(self):
        with open("res/Style/light_mode.qss", "r", encoding="utf-8") as file:
            app.setStyleSheet(file.read())
    
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Question', 'Are You want to quit?', 
                                     QMessageBox.Yes|QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.is_open_camera:
                self.close_camera_teaching()
            
            if self.is_connect_server:
                self.close_server_teaching()
                
            if self.io_controller:
                if self.io_controller.is_open():
                    self.close_all_io_controller()
                    self.set_io_result(StepResult.WAIT.value)
                    self.io_controller.close()
            
            if not self.is_resetting:
                self.saveSettings()
            else:
                self.restartApp()
            event.accept()
        else:
            event.ignore()
            
    def restartApp(self):
        python = sys.executable
        subprocess.Popen([python] + sys.argv)
        sys.exit(0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    
         
         