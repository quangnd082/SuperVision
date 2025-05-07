import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout
from PyQt5.QtCore import Qt
from libs.IOController5 import *

class IOControllerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("I/O Controller GUI")
        self.setGeometry(100, 100, 400, 400)

        # Layout chính
        layout = QVBoxLayout()

        # Lưới hiển thị trạng thái InPorts
        grid = QGridLayout()
        self.input_labels = []  # Danh sách chứa 8 label theo chỉ số 0-7

        for i in range(8):  # Tạo 8 label
            label = QLabel(f"In_{i+1}")  # Đặt tên theo chỉ số
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background-color: gray; color: white; padding: 5px;")
            self.input_labels.append(label)
            grid.addWidget(label, i // 4, i % 4)

        layout.addLayout(grid)

        # Nút mở cổng COM
        self.btn_open = QPushButton("Open COM Port")
        self.btn_open.clicked.connect(self.open_com)
        layout.addWidget(self.btn_open)

        # Lưới nút Output
        self.output_buttons = {}
        output_grid = QGridLayout()
        for i, port in enumerate(OutPorts):
            btn = QPushButton(f"{port.name} OFF")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, p=port: self.toggle_output(p, checked))
            self.output_buttons[port.name] = btn
            output_grid.addWidget(btn, i // 4, i % 4)
        layout.addLayout(output_grid)

        self.setLayout(layout)

        # Khởi tạo bộ điều khiển I/O
        self.io_controller = IOController(com="COM8", baud=19200)
        self.io_controller.inputSignalOnToOff.connect(self.on_to_off)
        self.io_controller.inputSignalOffToOn.connect(self.off_to_on)

    def open_com(self):
        if self.io_controller.open():
            self.btn_open.setText("COM Port Opened")
            self.btn_open.setEnabled(False)

    def on_to_off(self, commands):
        for cmd in commands:
            index = list(InPorts).index(InPorts[cmd])  # Lấy chỉ số từ enum InPorts
            self.input_labels[index].setStyleSheet("background-color: gray; color: white; padding: 5px;")

    def off_to_on(self, commands):
        for cmd in commands:
            index = list(InPorts).index(InPorts[cmd])  # Lấy chỉ số từ enum InPorts
            self.input_labels[index].setStyleSheet("background-color: green; color: white; padding: 5px;")  # Đổi màu thành đỏ

    def toggle_output(self, port, checked):
        state = PortState.On if checked else PortState.Off
        self.io_controller.write_out(port, state)
        self.output_buttons[port.name].setText(f"{port.name} {'ON' if checked else 'OFF'}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IOControllerGUI()
    window.show()
    sys.exit(app.exec_())
