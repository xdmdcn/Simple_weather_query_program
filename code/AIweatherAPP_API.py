import sys
import os
import glob
import requests
import json
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QApplication, QMessageBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QMovie, QFont, QIcon

# 从外部文件加载城市数据
with open('../files/Citys3465个/ChinaCitys.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# API配置
id = '10006646'
key = 'c66af4c46b1b1895c1aee8fa94f2d8a7'
url = 'https://cn.apihz.cn/api/tianqi/tqyb.php'


class WeatherWorker(QThread):
    """
    后台工作线程，用于执行网络请求

    参数:
    query_list -- 查询参数列表，每个元素为元组(sheng, place)
    """
    finished = Signal(dict)  # 成功信号，传递天气数据
    error = Signal(str)  # 错误信号，传递错误信息
    progress = Signal(int)  # 进度更新信号

    def __init__(self, query_list):
        """
        初始化工作线程

        参数:
        query_list -- 查询参数列表，每个元素为元组(sheng, place)
        """
        super().__init__()
        self.query_list = query_list
        self.canceled = False  # 取消标志

    def run(self):
        """
        线程执行的主要方法，执行网络请求和数据处理
        """
        try:
            # 模拟进度更新
            for i in range(1, 101, 10):
                if self.canceled:
                    return
                self.progress.emit(i)
                time.sleep(0.05)

            last_error = None  # 记录最后一个错误

            # 依次尝试查询列表中的地点
            for sheng, place in self.query_list:
                try:
                    # 构建API URL
                    url_total = f"{url}?id={id}&key={key}&sheng={sheng}&place={place}"

                    # 发送网络请求，设置10秒超时
                    response = requests.get(url_total, timeout=10)
                    response.raise_for_status()  # 检查HTTP错误状态码

                    # 解析JSON响应
                    weather_data = response.json()

                    # 验证API返回的数据是否有效
                    if 'place' not in weather_data or 'temperature' not in weather_data:
                        raise ValueError("API返回无效数据")

                    # 添加时间戳
                    weather_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    weather_data['query_level'] = f"{sheng}/{place}"  # 记录查询成功的级别

                    # 发出完成信号
                    self.finished.emit(weather_data)
                    return

                except requests.exceptions.RequestException as e:
                    # 处理网络相关错误
                    last_error = f"查询 {place} 失败: {str(e)}"
                except ValueError as e:
                    # 处理JSON解析错误或无效数据
                    last_error = f"查询 {place} 失败: {str(e)}"
                except Exception as e:
                    # 处理其他未知错误
                    last_error = f"查询 {place} 失败: {str(e)}"

            # 所有查询都失败，发出错误信号
            if last_error:
                self.error.emit(last_error)

        finally:
            # 确保进度条到达100%
            self.progress.emit(100)

    def cancel(self):
        """取消正在进行的请求"""
        self.canceled = True


class WeatherApp(QWidget):
    """
    天气查询应用主窗口
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('多级天气查询系统')
        self.setFixedSize(500, 650)  # 增大窗口尺寸以容纳更多内容

        # 创建主布局
        self.layout_main = QVBoxLayout()
        self.setLayout(self.layout_main)

        # 设置应用样式
        self.set_app_style()

        # 初始化天气图标缓存
        self.folder_path = '../files/weatherlogo/new_ico/'
        self.weather_icons = self.preload_weather_icons()

        # 初始化天气数据缓存
        self.weather_cache = {}

        # 创建UI组件
        self.create_ui_components()

        # 填充省份数据
        self.province_return()

        # 连接信号与槽
        self.connect_signals()

        # 初始化工作线程
        self.worker = None

        # 显示欢迎消息
        self.show_welcome_message()

        self.last_request_time = 0  # 添加最后请求时间记录
        self.MIN_REQUEST_INTERVAL = 3  # 最小请求间隔(秒)

    def set_app_style(self):
        """
        设置应用样式表
        """
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f5f9;
                font-family: 'Microsoft YaHei';
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #a0a0a0;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:hover {
                border: 1px solid #4a9cff;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #4a9cff;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a8cff;
            }
            QPushButton:disabled {
                background-color: #a0c4ff;
            }
            QLabel {
                padding: 3px;
            }
            QProgressBar {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                text-align: center;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4a9cff;
                width: 10px;
            }
            #queryInfo {
                background-color: #e8f4ff;
                padding: 5px;
                border-radius: 4px;
                border: 1px solid #c0d8f0;
            }
        """)

    def create_ui_components(self):
        """创建所有UI组件"""
        # 创建省市区选择布局
        self.create_location_selection()

        # 创建查询按钮
        self.create_query_button()

        # 创建加载指示器
        self.create_loading_indicator()

        # 创建查询信息区域
        self.create_query_info()

        # 创建天气图标显示区域
        self.create_weather_icons()

        # 创建天气信息显示区域
        self.create_weather_info()

        # 创建附加信息区域
        self.create_additional_info()

        # 创建缓存管理区域
        self.create_cache_management()

    def create_location_selection(self):
        """创建位置选择组件"""
        # 位置选择布局
        location_layout = QVBoxLayout()

        # 省份选择
        province_layout = QHBoxLayout()
        province_layout.addWidget(QLabel("省份:"))
        self.province = QComboBox()
        self.province.setMinimumWidth(150)
        self.province.addItem('--省份--')
        province_layout.addWidget(self.province)
        location_layout.addLayout(province_layout)

        # 城市选择
        city_layout = QHBoxLayout()
        city_layout.addWidget(QLabel("城市:"))
        self.city = QComboBox()
        self.city.setMinimumWidth(150)
        self.city.addItem('--市区--')
        city_layout.addWidget(self.city)
        location_layout.addLayout(city_layout)

        # 区域选择
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel("区域:"))
        self.area = QComboBox()
        self.area.setMinimumWidth(150)
        self.area.addItem('--区域--')
        area_layout.addWidget(self.area)
        location_layout.addLayout(area_layout)

        # 添加说明标签
        info_label = QLabel("提示: 有些地区可能只支持到市级查询")
        info_label.setStyleSheet("color: #666666; font-size: 10pt; font-style: italic;")
        location_layout.addWidget(info_label)

        self.layout_main.addLayout(location_layout)

    def create_query_button(self):
        """创建查询按钮"""
        # 按钮布局
        button_layout = QHBoxLayout()

        # 查询按钮
        self.query_button = QPushButton('查询天气')
        self.query_button.setMinimumHeight(35)
        self.query_button.setIcon(QIcon.fromTheme("search"))

        # 取消按钮
        self.cancel_button = QPushButton('取消查询')
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setEnabled(False)  # 初始禁用
        self.cancel_button.setIcon(QIcon.fromTheme("cancel"))

        button_layout.addWidget(self.query_button)
        button_layout.addWidget(self.cancel_button)

        self.layout_main.addLayout(button_layout)

    def create_loading_indicator(self):
        """创建加载指示器"""
        # 进度条布局
        progress_layout = QHBoxLayout()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)  # 初始隐藏

        progress_layout.addWidget(self.progress_bar)

        self.layout_main.addLayout(progress_layout)

    def create_query_info(self):
        """创建查询信息区域"""
        # 查询信息布局
        query_info_layout = QHBoxLayout()

        # 查询级别标签
        self.query_level_label = QLabel("查询级别: ")
        self.query_level_label.setObjectName("queryInfo")

        # 查询策略标签
        self.query_strategy_label = QLabel("查询策略: ")
        self.query_strategy_label.setObjectName("queryInfo")

        query_info_layout.addWidget(self.query_level_label)
        query_info_layout.addWidget(self.query_strategy_label)

        self.layout_main.addLayout(query_info_layout)

    def create_weather_icons(self):
        """创建天气图标显示区域"""
        # 图标布局
        icon_layout = QHBoxLayout()

        # 当前天气图标
        self.weather_icon_1 = QLabel()
        self.weather_icon_1.setAlignment(Qt.AlignCenter)
        self.weather_icon_1.setMinimumSize(100, 100)
        self.weather_icon_1.setStyleSheet("background-color: white; border-radius: 8px;")

        # 分隔符
        self.weather_icon_3 = QLabel('→')
        self.weather_icon_3.setAlignment(Qt.AlignCenter)
        self.weather_icon_3.setFont(QFont("Arial", 24))

        # 未来天气图标
        self.weather_icon_2 = QLabel()
        self.weather_icon_2.setAlignment(Qt.AlignCenter)
        self.weather_icon_2.setMinimumSize(100, 100)
        self.weather_icon_2.setStyleSheet("background-color: white; border-radius: 8px;")

        # 添加到布局
        icon_layout.addStretch()
        icon_layout.addWidget(self.weather_icon_1)
        icon_layout.addWidget(self.weather_icon_3)
        icon_layout.addWidget(self.weather_icon_2)
        icon_layout.addStretch()

        self.layout_main.addLayout(icon_layout)

    def create_weather_info(self):
        """创建天气信息显示区域"""
        # 信息布局
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        # 创建信息标签
        self.city_label = self.create_info_label("城市: ")
        self.temp_label = self.create_info_label("温度: ")
        self.weather_label = self.create_info_label("天气: ")
        self.humidity_label = self.create_info_label("湿度: ")
        self.wind_label = self.create_info_label("风速: ")

        # 添加到布局
        info_layout.addLayout(self.create_info_row("城市:", self.city_label))
        info_layout.addLayout(self.create_info_row("温度:", self.temp_label))
        info_layout.addLayout(self.create_info_row("天气:", self.weather_label))
        info_layout.addLayout(self.create_info_row("湿度:", self.humidity_label))
        info_layout.addLayout(self.create_info_row("风速:", self.wind_label))

        self.layout_main.addLayout(info_layout)

    def create_info_label(self, text):
        """创建信息显示标签"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignLeft)
        label.setStyleSheet("font-weight: bold; color: #0055aa; font-size: 12pt;")
        return label

    def create_info_row(self, title, value_label):
        """创建信息行布局"""
        row_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        row_layout.addWidget(title_label)
        row_layout.addWidget(value_label)
        row_layout.addStretch()
        return row_layout

    def create_additional_info(self):
        """创建附加信息区域"""
        # 附加信息布局
        additional_layout = QVBoxLayout()

        # 更新时间标签
        self.update_time_label = QLabel("更新时间: ")
        self.update_time_label.setStyleSheet("color: #666666; font-size: 10pt;")

        # 数据来源标签
        self.source_label = QLabel("数据来源: 中国天气网")
        self.source_label.setStyleSheet("color: #666666; font-size: 10pt;")

        additional_layout.addWidget(self.update_time_label)
        additional_layout.addWidget(self.source_label)

        self.layout_main.addLayout(additional_layout)

    def create_cache_management(self):
        """创建缓存管理区域"""
        # 缓存布局
        cache_layout = QHBoxLayout()

        # 缓存状态标签
        self.cache_status = QLabel("缓存: 0 项")
        self.cache_status.setStyleSheet("color: #666666; font-size: 10pt;")

        # 清除缓存按钮
        self.clear_cache_button = QPushButton("清除缓存")
        self.clear_cache_button.setMaximumWidth(100)

        cache_layout.addWidget(self.cache_status)
        cache_layout.addStretch()
        cache_layout.addWidget(self.clear_cache_button)

        self.layout_main.addLayout(cache_layout)

    def preload_weather_icons(self):
        """预加载天气图标（优化版）"""
        icon_dict = {}
        try:
            png_files = glob.glob(os.path.join(self.folder_path, "*.png"))
            for png_file in png_files:
                key = os.path.splitext(os.path.basename(png_file))[0]

                # 优化：只加载小尺寸图标
                pixmap = QPixmap(png_file)
                if not pixmap.isNull():
                    # 缩放为实际需要的大小
                    icon_dict[key] = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e:
            print(f"加载天气图标时出错: {e}")
        return icon_dict

    def connect_signals(self):
        """连接所有信号与槽"""
        # 省市区选择信号
        self.province.currentTextChanged.connect(self.city_return)
        self.city.currentTextChanged.connect(self.area_return)

        # 按钮信号
        self.query_button.clicked.connect(self.weather_info_return)
        self.cancel_button.clicked.connect(self.cancel_query)
        self.clear_cache_button.clicked.connect(self.clear_cache)

    def weather_info_return(self):
        """处理天气查询请求"""

        # 添加频率限制检查
        current_time = time.time()
        if current_time - self.last_request_time < self.MIN_REQUEST_INTERVAL:
            self.show_dialog("请求过于频繁，请稍后再试")
            return

        # 获取选择的位置
        sheng = self.province.currentText()
        city = self.city.currentText()
        area = self.area.currentText()

        # 验证选择
        if sheng == '--省份--' or city == '--市区--':
            self.show_dialog("请至少选择省份和城市")
            return

        # 生成缓存键
        cache_key = f"{sheng}-{city}-{area}"

        # 检查缓存
        if cache_key in self.weather_cache:
            # 从缓存中获取数据
            cached_data = self.weather_cache[cache_key]

            # 检查缓存是否过期（10分钟内有效）
            cache_time = datetime.strptime(cached_data['timestamp'], "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - cache_time).total_seconds() < 600:
                self.display_weather(cached_data)
                self.update_time_label.setText(f"更新时间: {cached_data['timestamp']} (缓存)")
                self.query_level_label.setText(f"查询级别: {cached_data.get('query_level', '缓存')}")
                return

        # 创建查询列表（按优先级从高到低）
        query_list = []
        query_strategy = []

        # 1. 优先尝试县级查询
        if area != '--区域--':
            query_list.append((sheng, area))
            query_strategy.append(f"县级: {area}")

        # 2. 尝试市级查询
        if city != '--市区--':
            query_list.append((sheng, city))
            query_strategy.append(f"市级: {city}")

        # 3. 最后尝试省级查询（如果支持）
        query_list.append((sheng, sheng))
        query_strategy.append(f"省级: {sheng}")

        # 更新查询策略显示
        self.query_strategy_label.setText(f"查询策略: {' → '.join(query_strategy)}")

        # 禁用查询按钮，启用取消按钮
        self.query_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        # 显示加载指示器
        self.show_loading_indicator(True)

        # 创建并启动工作线程
        self.worker = WeatherWorker(query_list)

        # 连接工作线程信号
        self.worker.finished.connect(self.handle_weather_data)
        self.worker.error.connect(self.handle_error)
        self.worker.progress.connect(self.update_progress)

        # 确保线程结束后被清理
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.cleanup_after_query(cache_key))
        self.worker.error.connect(lambda: self.cleanup_after_query(cache_key))

        # 启动线程
        self.worker.start()
        self.last_request_time = current_time  # 更新最后请求时间

    def handle_weather_data(self, data):
        """
        处理成功获取的天气数据

        参数:
        data -- 从API获取的天气数据
        """
        # 获取缓存键
        sheng = self.province.currentText()
        city = self.city.currentText()
        area = self.area.currentText()
        cache_key = f"{sheng}-{city}-{area}"

        # 更新缓存
        self.weather_cache[cache_key] = data
        self.update_cache_status()

        # 显示天气信息
        self.display_weather(data)

        # 显示更新时间
        self.update_time_label.setText(f"更新时间: {data['timestamp']}")

        # 显示查询级别
        self.query_level_label.setText(f"查询级别: {data.get('query_level', '未知')}")

    def display_weather(self, data):
        """显示天气信息"""
        # 更新文本信息
        self.city_label.setText(f"{data['place']}")
        self.temp_label.setText(f"{data['temperature']}℃")
        self.weather_label.setText(f"{data['weather1']}转{data['weather2']}")
        self.humidity_label.setText(f"{data['humidity']}%")
        self.wind_label.setText(f"{data['windScale']}级 ({data['windSpeed']}m/s)")

        # 更新图标
        weather1 = data['weather1']
        weather2 = data['weather2']

        if weather1 in self.weather_icons:
            self.weather_icon_1.setPixmap(self.weather_icons[weather1].scaled(80, 80, Qt.KeepAspectRatio))
            self.weather_icon_1.setText("")
        else:
            self.weather_icon_1.setText(f"无{weather1}图标")

        if weather2 in self.weather_icons:
            self.weather_icon_2.setPixmap(self.weather_icons[weather2].scaled(80, 80, Qt.KeepAspectRatio))
            self.weather_icon_2.setText("")
        else:
            self.weather_icon_2.setText(f"无{weather2}图标")

    def handle_error(self, error_msg):
        """处理错误"""
        self.show_dialog(error_msg)
        self.query_level_label.setText("查询级别: 失败")

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"加载中... {value}%")

    def cleanup_after_query(self, cache_key):
        """查询结束后的清理工作"""

        if self.worker:
            try:
                if self.worker.isRunning():
                    self.worker.quit()
                    self.worker.wait(2000)  # 等待2秒
                self.worker.deleteLater()
            except Exception as e:
                print(f"清理线程时出错: {e}")
            finally:
                self.worker = None

        # 隐藏加载指示器
        self.show_loading_indicator(False)

        # 恢复按钮状态
        self.query_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 重置工作线程引用
        self.worker = None

    def cancel_query(self):
        """取消正在进行的查询"""
        if self.worker:
            self.worker.cancel()
            self.show_dialog("查询已取消")
            self.cleanup_after_query(None)
            self.query_level_label.setText("查询级别: 已取消")

    def clear_cache(self):
        """清除天气数据缓存"""
        self.weather_cache.clear()
        self.update_cache_status()
        self.show_dialog("已清除所有缓存数据")

    def update_cache_status(self):
        """更新缓存状态显示"""
        count = len(self.weather_cache)
        self.cache_status.setText(f"缓存: {count} 项")

    def show_loading_indicator(self, visible):
        """
        显示或隐藏加载指示器

        参数:
        visible -- 是否显示指示器
        """
        self.progress_bar.setVisible(visible)
        self.progress_bar.setValue(0)

    def province_return(self):
        """填充省份数据"""
        for province in data:
            self.province.addItem(province["province"])

    def city_return(self):
        """根据省份填充城市数据"""
        self.city.clear()
        self.city.addItem('--市区--')

        if self.province.currentText() == '--省份--':
            return

        city_list = []
        for province in data:
            if province["province"] == self.province.currentText():
                for city in province["citys"]:
                    city_list.append(city["city"])
        self.city.addItems(city_list)

    def area_return(self):
        """根据城市填充区域数据"""
        self.area.clear()
        self.area.addItem('--区域--')

        if self.city.currentText() == '--市区--':
            return

        area_list = []
        for province in data:
            if province["province"] == self.province.currentText():
                for city in province["citys"]:
                    if city["city"] == self.city.currentText():
                        for area in city["areas"]:
                            area_list.append(area["area"])
        self.area.addItems(area_list)

        # 如果没有区域数据，禁用区域选择
        if len(area_list) == 0:
            self.area.setEnabled(False)
            self.area.setToolTip("该城市没有县级区域数据")
        else:
            self.area.setEnabled(True)
            self.area.setToolTip("")

    def show_dialog(self, message):
        """
        显示消息对话框

        参数:
        message -- 要显示的消息内容
        """
        QMessageBox.information(
            self,
            "提示",
            message,
            QMessageBox.StandardButton.Ok
        )

    def show_welcome_message(self):
        """显示欢迎消息"""
        self.city_label.setText("欢迎使用天气查询")
        self.temp_label.setText("请选择地区并查询")
        self.weather_label.setText("获取最新天气信息")
        self.humidity_label.setText("")
        self.wind_label.setText("")
        self.update_time_label.setText("")
        self.query_level_label.setText("查询级别: 等待查询")
        self.query_strategy_label.setText("查询策略: 等待查询")
        self.update_cache_status()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec())