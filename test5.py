import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton,
    QMessageBox, QLabel
)
from datetime import datetime, timedelta

FILE_PATH = r'C:\Users\DTC\Desktop\Test3.txt'  # Đường dẫn file cần thao tác  # Đường dẫn file cần thao tác

class CodeCheckerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiểm tra mã S + Tên thiết bị")
        self.resize(500, 200)

        self.layout = QVBoxLayout()

        self.label1 = QLabel("Nhập mã (ví dụ: S123456789):")
        self.layout.addWidget(self.label1)
        self.line_edit_code = QLineEdit()
        self.layout.addWidget(self.line_edit_code)

        self.label2 = QLabel("Nhập tên thiết bị (ví dụ: SFG-ADC08011UQ):")
        self.layout.addWidget(self.label2)
        self.line_edit_device = QLineEdit()
        self.layout.addWidget(self.line_edit_device)

        self.check_button = QPushButton("Kiểm tra và ghi")
        self.check_button.clicked.connect(self.check_and_update)
        self.layout.addWidget(self.check_button)

        self.open_button = QPushButton("Mở file")
        self.open_button.clicked.connect(self.open_file)
        self.layout.addWidget(self.open_button)

        self.setLayout(self.layout)

    def check_and_update(self):
        input_code = self.line_edit_code.text().strip()
        input_device = self.line_edit_device.text().strip()

        if not input_code.startswith("S") or len(input_code) != 10:
            QMessageBox.warning(self, "Lỗi", "Mã không hợp lệ. Nhập dạng S123456789")
            return

        if not input_device:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thiết bị.")
            return

        full_check = f"{input_code} {input_device}"
        now = datetime.now()
        lines = []

        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, "r") as f:
                lines = f.readlines()

            # Kiểm tra trùng
            found = any(line.strip().startswith(full_check) for line in lines)
            if found:
                QMessageBox.information(self, "Thông báo", f"{full_check} đã tồn tại trong file.")
                return

            # Kiểm tra thời gian dòng đầu
            if lines:
                first_line = lines[0].strip()
                parts = first_line.strip().split()
                if len(parts) >= 4:
                    try:
                        first_time_str = f"{parts[-2]} {parts[-1]}"
                        first_time = datetime.strptime(first_time_str, "%Y/%m/%d %H:%M:%S")
                        delta = now - first_time
                        if delta >= timedelta(hours=24):
                            lines.pop(0)
                    except ValueError:
                        QMessageBox.critical(self, "Lỗi", f"Lỗi định dạng thời gian ở dòng đầu: {first_line}")
                        return
        else:
            # Tạo file mới nếu chưa có
            open(FILE_PATH, "w").close()

        # Ghi dòng mới
        # Ghi dòng mới
        timestamp = now.strftime('%Y/%m/%d %H:%M:%S')
        new_line_content = f"{input_code} {input_device} {timestamp}"

        if lines:  # Nếu file có nội dung → thêm xuống dòng
            new_line = f"\n{new_line_content}"
        else:
            new_line = new_line_content

        lines.append(new_line)

        with open(FILE_PATH, "w") as f:
            f.writelines(lines)

        QMessageBox.information(self, "Thành công", f"{full_check} đã được thêm vào file.")

    def open_file(self):
        if os.path.exists(FILE_PATH):
            os.startfile(FILE_PATH)  # Windows
        else:
            QMessageBox.warning(self, "Lỗi", "File không tồn tại.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CodeCheckerApp()
    window.show()
    sys.exit(app.exec_())
