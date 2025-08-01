import sys

from PySide6.QtWidgets import (
QWidget, QLineEdit, QApplication, QMessageBox, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import os
import glob
import requests

id = '10006646'
key = 'c66af4c46b1b1895c1aee8fa94f2d8a7'
url = f'https://cn.apihz.cn/api/tianqi/tqyb.php'

import json

with open('../files/Citys3465个/ChinaCitys.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

class weather_APP(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('简易天气查询')
        self.setFixedSize(400, 300)
        layout_main = QVBoxLayout()
        layout = QHBoxLayout()
        layout_info = QVBoxLayout()
        layout_icon = QHBoxLayout()

        self.folder_path = f'../files/weatherlogo/new_ico/'

        self.province = QComboBox()
        self.province.addItem('--省份--')
        self.city = QComboBox()
        self.area = QComboBox()

        self.button = QPushButton('查询')
        self.button_signal = True

        layout.addWidget(self.province)
        layout.addWidget(self.city)
        self.city.addItem('--市区-')
        layout.addWidget(self.area)
        self.area.addItem('--区域--')
        layout.addWidget(self.button)

        self.weather_icon_1 = QLabel('当前天气')
        # self.weather_icon_1.setPixmap(self.pixmap_1)
        self.weather_icon_3 = QLabel('--------->')
        self.weather_icon_2 = QLabel('未来天气')
        # self.weather_icon_2.setPixmap(self.pixmap_2)
        layout_icon.addWidget(self.weather_icon_1)
        layout_icon.addWidget(self.weather_icon_3)
        layout_icon.addWidget(self.weather_icon_2)

        self.city_label = QLabel("城市: ")
        self.temp_label = QLabel("温度: ")
        self.weather_label = QLabel("天气: ")
        self.humidity_label = QLabel("湿度: ")
        self.wind_label = QLabel("风速: ")
        self.city_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weather_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.humidity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wind_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_info.addWidget(self.city_label)
        layout_info.addWidget(self.temp_label)
        layout_info.addWidget(self.weather_label)
        layout_info.addWidget(self.humidity_label)
        layout_info.addWidget(self.wind_label)

        layout_main.addLayout(layout)
        layout_main.addLayout(layout_icon)
        layout_main.addLayout(layout_info)

        self.setLayout(layout_main)

        self.province_return()
        self.png_files = self.list_png_files(self.folder_path)
        self.province.currentTextChanged.connect(self.city_return)
        self.city.currentTextChanged.connect(self.area_return)
        self.button.clicked.connect(self.weather_info_return)

    def list_png_files(self, directory):
        # 使用glob.glob()函数匹配指定目录下的所有PNG文件
        png_files = glob.glob(os.path.join(directory, "*.png"))
        return png_files

    def weather_info_return(self):
        sheng = self.province.currentText()
        city = self.city.currentText()
        area = self.area.currentText()
        if self.area.currentText() != '--区域--':
            url_total = url + f'?id={id}&key={key}&sheng={sheng}&place={area}'
        elif self.city.currentText() != '--市区-':
            url_total = url + f'?id={id}&key={key}&sheng={sheng}&place={city}'
        else:
            self.button_signal = None

        try:
            response = requests.get(url_total)
            data = response.json()
            self.city_label.setText(f"城市: {data['place']}")
            self.temp_label.setText(f"温度: {data['temperature']}℃")
            self.weather_label.setText(f"天气: {data['weather1']}转{data['weather2']}")
            self.humidity_label.setText(f"湿度: {data['humidity']}%")
            self.wind_label.setText(f"风速: {data['windScale']}（{data['windSpeed']}m/s")
            for png_file in self.png_files:
                if data['weather1'] == os.path.splitext(os.path.basename(png_file))[0]:
                    self.weather_icon_1.setPixmap(QPixmap(png_file))
                if data['weather2'] == os.path.splitext(os.path.basename(png_file))[0]:
                    self.weather_icon_2.setPixmap(QPixmap(png_file))
        except Exception:
            self.show_dialog()

    def province_return(self):
        for province in data:
            self.province.addItem(province["province"])

    def city_return(self):
        self.city.clear()
        self.city.addItem('--市区-')
        city_list = []
        for province in data:
            if province["province"] == self.province.currentText():
                for city in province["citys"]:
                    city_list.append(city["city"])
        self.city.addItems(city_list)

    def area_return(self):
        self.area.clear()
        self.area.addItem('--区域--')
        area_list = []
        for province in data:
            if province["province"] == self.province.currentText():
                for city in province["citys"]:
                    if city["city"] == self.city.currentText():
                        for area in city["areas"]:
                            area_list.append(area["area"])
        self.area.addItems(area_list)

    def show_dialog(self):
        dialog = QMessageBox.information(
            self,
            "提示框",
            "请求失败，请检查错误",
            QMessageBox.StandardButton.Ok
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = weather_APP()
    window.show()
    sys.exit(app.exec())