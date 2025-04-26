import os
import sys
import re
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, 
                           QLineEdit, QLabel, QProgressBar, QMessageBox, QFileDialog,
                           QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
                           QFrame, QSizePolicy, QStyledItemDelegate, QApplication,
                           QProgressDialog, QDialog, QCheckBox, QTextBrowser, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer, QPropertyAnimation, QEasingCurve, QSize, QPoint, QRectF, QDateTime
from PyQt6.QtGui import QDesktopServices, QIcon, QPalette, QColor, QFont, QPainter, QPainterPath

from network.web_scraper import WebScraper
from parser.html_parser import HtmlParser
from utils.config import Config
from utils.logger import Logger

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.start_time = None
        self.last_bytes = 0
        self.last_time = None
        self._is_cancelled = False
        
    def run(self):
        try:
            # 检查URL是否有效
            if not self.url or not self.url.startswith(('http://', 'https://')):
                self.error_signal.emit(f"无效的下载链接: {self.url}")
                return
                
            # 检查保存路径
            save_dir = os.path.dirname(self.save_path)
            if not os.path.exists(save_dir):
                try:
                    os.makedirs(save_dir)
                except Exception as e:
                    self.error_signal.emit(f"创建目录失败: {str(e)}")
                    return
            
            # 检查目录可写
            if not os.access(save_dir, os.W_OK):
                self.error_signal.emit(f"目录无写入权限: {save_dir}")
                return
                
            scraper = WebScraper()
            success = scraper.download_file(self.url, self.save_path, self.progress_signal)
            
            if self._is_cancelled:
                # 如果下载被取消，删除部分下载的文件
                if os.path.exists(self.save_path):
                    try:
                        os.remove(self.save_path)
                    except:
                        pass
                return
                
            if success:
                self.finished_signal.emit(self.save_path)
            else:
                self.error_signal.emit("下载失败")
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(f"下载错误: {str(e)}")
                
    def cancel(self):
        self._is_cancelled = True

class SearchThread(QThread):
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)  # 添加进度信号
    
    def __init__(self, search_term):
        super().__init__()
        self.search_term = search_term
        self._is_cancelled = False
        
    def run(self):
        try:
            self.progress_signal.emit("正在连接搜索服务...")
            scraper = WebScraper()
            self.progress_signal.emit("正在搜索游戏...")
            html = scraper.search_game(self.search_term)
            self.progress_signal.emit("正在解析搜索结果...")
            parser = HtmlParser()
            results = parser.parse_search_results(html)
            if not self._is_cancelled:
                self.result_signal.emit(results)
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(f"搜索错误: {str(e)}")
                
    def cancel(self):
        self._is_cancelled = True

class FunctionButton(QPushButton):
    """顶部功能按钮样式"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 120px;
                height: 35px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class SearchButton(QPushButton):
    """搜索按钮样式"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
                height: 32px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class TableButton(QPushButton):
    """表格中的操作按钮样式"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 取消原来的样式表设置，完全使用paintEvent绘制
        self.setStyleSheet("")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(50, 24)  # 设置固定大小
        # 确保样式不被覆盖
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
    def paintEvent(self, event):
        # 自定义绘制确保四角都是圆角
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 抗锯齿
        
        # 创建圆角矩形路径
        path = QPainterPath()
        rect = self.rect()
        rectf = QRectF(rect)
        path.addRoundedRect(rectf, 4, 4)  # 使用4px的圆角
        
        # 根据按钮状态选择颜色
        if not self.isEnabled():
            color = QColor("#9E9E9E")  # 禁用状态使用灰色
        elif self.isDown():
            color = QColor("#0D47A1")
        elif self.underMouse():
            color = QColor("#1976D2")
        else:
            color = QColor("#2196F3")
        
        # 绘制背景
        painter.fillPath(path, color)
        
        # 绘制文本
        painter.setPen(QColor("white"))
        # 使用drawText的完整参数，指定绘制文本的绝对位置
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        
        # 计算文本位置，确保居中
        text_rect = painter.fontMetrics().boundingRect(self.text())
        x = (rect.width() - text_rect.width()) / 2
        y = (rect.height() + text_rect.height()) / 2 - 2  # 微调垂直位置
        
        painter.drawText(int(x), int(y), self.text())
        
    def setEnabled(self, enabled):
        """重写setEnabled方法以更新鼠标指针"""
        super().setEnabled(enabled)
        if enabled:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)

class ButtonContainer(QWidget):
    """表格按钮容器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 32)  # 调整容器尺寸
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # 确保没有边距
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 设置背景为透明，避免影响按钮样式
        self.setStyleSheet("background-color: transparent;")

    def addButton(self, button):
        self.layout.addWidget(button)

class ButtonDelegate(QStyledItemDelegate):
    """自定义代理来处理表格中的按钮"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.button_clicked = pyqtSignal(int)

    def createEditor(self, parent, option, index):
        button = TableButton(parent)
        return button

    def setEditorData(self, editor, index):
        editor.setText(index.data())

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class AnimatedProgressBar(QProgressBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._last_value = 0
        
    def setValue(self, value):
        if value != self._last_value:
            self._animation.setStartValue(self._last_value)
            self._animation.setEndValue(value)
            self._animation.start()
            self._last_value = value

# 添加一个新的翻译线程类，专门处理翻译过程，允许通过信号更新UI
class TranslateThread(QThread):
    progress_signal = pyqtSignal(str)  # 用于更新进度消息
    result_signal = pyqtSignal(str)    # 返回翻译结果
    error_signal = pyqtSignal(str)     # 返回错误信息
    finished_signal = pyqtSignal(bool) # 标记是否成功完成
    
    def __init__(self, chinese_name):
        super().__init__()
        self.chinese_name = chinese_name
        self._is_cancelled = False
        
    def run(self):
        try:
            self.progress_signal.emit(f"正在准备翻译游戏名称...")
            scraper = WebScraper()
            
            self.progress_signal.emit(f"正在查询中文游戏名对应的英文名...")
            # 注册一个回调函数，允许WebScraper报告进度
            english_name = scraper.get_english_game_name(
                self.chinese_name, 
                progress_callback=lambda msg: self.progress_signal.emit(msg)
            )
            
            if self._is_cancelled:
                self.finished_signal.emit(False)
                return
                
            if english_name:
                self.result_signal.emit(english_name)
                self.finished_signal.emit(True)
            else:
                self.error_signal.emit(f"未能找到 \"{self.chinese_name}\" 的英文名称")
                self.finished_signal.emit(False)
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(f"翻译过程中出错: {str(e)}")
                self.finished_signal.emit(False)
    
    def cancel(self):
        self._is_cancelled = True

# 添加协议对话框类
class AgreementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("重要声明")
        self.setMinimumSize(600, 400)
        self.setModal(True)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 添加文本浏览器显示协议内容
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)  # 允许打开外部链接
        
        # 设置协议内容
        agreement_text = """
        <h2 style='text-align:center;'>重要声明</h2>
        
        <p style='color:#0D47A1; font-weight:bold; font-size:14px;'>所有修改器均由风灵月影大佬制作，本人是基于学习技术才创作此软件，仅用于学习交流。</p>
        
        <p><b>交流群：</b>1029326088</p>
        <p><b>作者哔哩哔哩：</b><a href='https://space.bilibili.com/41173761?spm_id_from=333.337.0.0'>https://space.bilibili.com/41173761</a></p>
        
        <hr>
        
        <p><b>1. 本工具仅为技术演示用途，不提供任何破解/盗版资源</b></p>
        <p><b>2. 所有修改器资源均来自第三方公开网络，本软件不存储、不修改、不验证文件合法性</b></p>
        <p><b>3. 仅单机使用修改器，联机会导致游戏账号封禁或设备风险，请严格遵守游戏用户协议</b></p>
        <p style='color:red; font-size:16px; font-weight:bold;'>4. 本软件完全免费！本软件完全免费！本软件完全免费！</p>
        """
        
        self.text_browser.setHtml(agreement_text)
        # 监控文本浏览器的滚动位置变化
        self.text_browser.verticalScrollBar().valueChanged.connect(self.check_scroll_position)
        layout.addWidget(self.text_browser)
        
        # 滚动到顶部并初始化已阅读状态
        self.text_browser.verticalScrollBar().setValue(0)
        self.has_scrolled_to_bottom = False
        
        # 添加提示标签
        self.scroll_hint = QLabel("请滚动阅读至底部才能勾选同意")
        self.scroll_hint.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.scroll_hint)
        
        # 添加复选框
        checkbox_container = QHBoxLayout()
        self.agreement_checkbox = QCheckBox("我已阅读并同意上述声明")
        self.agreement_checkbox.setMinimumHeight(30)  # 增加高度使更容易点击
        self.agreement_checkbox.setEnabled(False)  # 初始状态下禁用
        # 使用clicked信号替代stateChanged信号，响应更直接
        self.agreement_checkbox.clicked.connect(self.update_button_state)
        checkbox_container.addWidget(self.agreement_checkbox)
        checkbox_container.addStretch()
        layout.addLayout(checkbox_container)
        
        # 添加按钮区域
        button_layout = QHBoxLayout()
        
        self.agree_button = QPushButton("同意并继续")
        self.agree_button.setEnabled(False)  # 初始禁用
        self.agree_button.clicked.connect(self.accept)
        
        self.exit_button = QPushButton("退出")
        self.exit_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.agree_button)
        button_layout.addWidget(self.exit_button)
        
        layout.addLayout(button_layout)
        
        # 应用样式
        self.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #ccc;
                padding: 10px;
                background-color: #f9f9f9;
                font-size: 11pt;
            }
            QPushButton {
                padding: 8px 16px;
                min-width: 100px;
                font-size: 11pt;
            }
            QCheckBox {
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 10px;
                font-size: 11pt;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
    
    def check_scroll_position(self, value):
        """检查文本浏览器的滚动位置，确定用户是否已滚动到底部"""
        scrollbar = self.text_browser.verticalScrollBar()
        # 如果滚动条接近底部（留出一点余量）
        if value >= scrollbar.maximum() - 5:  
            if not self.has_scrolled_to_bottom:
                self.has_scrolled_to_bottom = True
                self.agreement_checkbox.setEnabled(True)
                self.scroll_hint.setText("现在您可以勾选同意继续使用")
                self.scroll_hint.setStyleSheet("color: green; font-weight: bold;")
    
    def update_button_state(self, checked):
        """当复选框被点击时更新按钮状态"""
        # 再次验证是否已滚动到底部
        if not self.has_scrolled_to_bottom:
            self.agreement_checkbox.setChecked(False)
            self.agree_button.setEnabled(False)
            QMessageBox.warning(self, "提示", "请先阅读完整协议（滚动到底部）")
            return
            
        self.agree_button.setEnabled(checked)

class StatusOverlay(QWidget):
    """全局状态覆盖层，显示加载指示器和消息"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置为透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 创建加载指示文本
        self.status_label = QLabel("加载中...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(33, 150, 243, 0.8);
                border-radius: 10px;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # 添加到布局
        layout.addWidget(self.status_label)
        
        # 初始化为隐藏状态
        self.setVisible(False)
        
        # 创建渐变动画
        self.opacity_effect = QGraphicsOpacityEffect(self.status_label)
        self.status_label.setGraphicsEffect(self.opacity_effect)
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(500)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 创建闪烁动画计时器
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._update_blink)
        self.dots_count = 0
        
    def showMessage(self, message):
        """显示消息和加载动画"""
        self.status_label.setText(message)
        self.setVisible(True)
        self.opacity_animation.start()
        
        # 开始闪烁动画
        self.dots_count = 0
        self.blink_timer.start(500)  # 每500毫秒更新一次
        
    def hideMessage(self):
        """隐藏消息"""
        self.blink_timer.stop()
        self.setVisible(False)
        
    def _update_blink(self):
        """更新闪烁动画效果"""
        self.dots_count = (self.dots_count % 3) + 1
        dots = "." * self.dots_count
        base_message = self.status_label.text().rstrip(".").strip()
        self.status_label.setText(f"{base_message} {dots}")
        
    def paintEvent(self, event):
        """绘制半透明背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0, 50))  # 半透明黑色
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("风灵月影修改器下载器")
        self.setMinimumSize(1000, 700)
        self.download_thread = None
        self.search_thread = None
        self.config = Config()
        self.logger = Logger()
        self.trainer_links = []
        
        # 设置图标路径
        self.icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")
        
        # 设置窗口图标
        self.setWindowIcon(QIcon(os.path.join(self.icon_path, "app_icon.jpg")))
        
        # 初始化下载相关变量
        self.download_start_time = None
        self.download_speed = "0 KB/s"
        self.download_size = "0 MB"
        self.download_elapsed = "00:00:00"
        
        # 检查是否首次运行，显示协议
        if self.check_first_run():
            self.show_agreement_dialog()
        
        self.init_ui()
        self.apply_styles()
        
    def check_first_run(self):
        """检查是否是首次运行程序"""
        # 检查环境变量
        if os.environ.get('FLYYING_SKIP_DISCLAIMER') == '1':
            return False
            
        # 检查配置目录中的标记
        config_dir = os.path.join(os.path.expanduser("~"), "Documents", "FLYYING")
        config_flag_file = os.path.join(config_dir, ".agreement_accepted")
        if os.path.exists(config_flag_file):
            return False
            
        # 检查应用程序目录中的标记
        agreement_flag_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            ".agreement_accepted"
        )
        return not os.path.exists(agreement_flag_file)
    
    def show_agreement_dialog(self):
        """显示协议对话框，如果用户不同意则退出程序"""
        dialog = AgreementDialog(self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # 用户同意，创建标记文件
            # 1. 在应用程序目录中创建标记
            agreement_flag_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                ".agreement_accepted"
            )
            try:
                with open(agreement_flag_file, 'w') as f:
                    f.write("agreement accepted")
            except Exception as e:
                self.logger.error(f"无法创建程序目录协议接受标记文件: {e}")
                
            # 2. 在配置目录中创建标记
            try:
                config_dir = os.path.join(os.path.expanduser("~"), "Documents", "FLYYING")
                os.makedirs(config_dir, exist_ok=True)
                config_flag_file = os.path.join(config_dir, ".agreement_accepted")
                with open(config_flag_file, 'w') as f:
                    f.write("agreement accepted")
            except Exception as e:
                self.logger.error(f"无法创建配置目录协议接受标记文件: {e}")
                
            # 3. 设置环境变量
            os.environ['FLYYING_SKIP_DISCLAIMER'] = '1'
        else:
            # 用户不同意，退出程序
            sys.exit(0)
        
    def apply_styles(self):
        # 设置全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
            QLabel {
                color: #333;
            }
            QStatusBar {
                background-color: #f8f9fa;
                color: #666;
            }
        """)
        
    def init_ui(self):
        # 创建主窗口布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建顶部工具栏
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建搜索框和按钮
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)  # 设置搜索框和按钮之间的间距
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入游戏名称")
        self.search_input.setMinimumWidth(300)
        self.search_input.returnPressed.connect(self.search_game)
        
        self.search_btn = SearchButton("搜索")
        self.search_btn.setIcon(QIcon(os.path.join(self.icon_path, "search.png")))
        self.search_btn.clicked.connect(self.search_game)
        self.search_btn.setMinimumWidth(100)  # 设置最小宽度
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        
        # 创建官网链接按钮
        self.official_site_btn = FunctionButton("访问风灵月影官网")
        self.official_site_btn.setIcon(QIcon(os.path.join(self.icon_path, "website.png")))
        self.official_site_btn.clicked.connect(self.open_official_site)
        self.official_site_btn.setMinimumWidth(180)  # 设置最小宽度
        
        toolbar_layout.addLayout(search_layout)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.official_site_btn)
        
        # 添加搜索警示标语
        search_tips_layout = QVBoxLayout()
        
        # 英文搜索提示 - 使用HTML格式使其更加突出
        english_tip = QLabel("<b style='color:#1976D2;'>首选用<span style='color:#0D47A1;font-size:14px;'>英文游戏名称</span>进行搜索，以获得最精准的结果。中文搜索可能搜索不到。</b>")
        english_tip.setStyleSheet("padding: 5px; background-color: #E3F2FD; border-radius: 4px;")
        
        # 版权提示
        copyright_tip = QLabel("⚠ 提示：本工具仅提供信息索引服务，下载内容版权归属原作者，严禁用于商业用途")
        copyright_tip.setStyleSheet("color: #757575; padding: 3px;")
        
        search_tips_layout.addWidget(english_tip)
        search_tips_layout.addWidget(copyright_tip)
        
        # 创建搜索结果表格标题
        results_title = QLabel("搜索结果")
        results_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        
        # 创建搜索结果表格
        results_frame = QFrame()
        results_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        results_layout = QVBoxLayout(results_frame)
        
        results_layout.addWidget(results_title)
        
        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["游戏名称", "发布日期", "操作"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(2, 70)  # 设置操作列足够宽度
        self.results_table.horizontalHeader().setStretchLastSection(False)
        self.results_table.horizontalHeader().setSectionsClickable(False)
        self.results_table.verticalHeader().setDefaultSectionSize(40)
        self.results_table.setShowGrid(True)
        self.results_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
        """)
        results_layout.addWidget(self.results_table)
        
        # 创建版本选择表格
        versions_frame = QFrame()
        versions_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        versions_layout = QVBoxLayout(versions_frame)
        
        versions_label = QLabel("可用修改器版本")
        versions_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        versions_layout.addWidget(versions_label)
        
        self.versions_table = QTableWidget(0, 4)
        self.versions_table.setHorizontalHeaderLabels(["文件名", "添加日期", "文件大小", "操作"])
        self.versions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.versions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.versions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.versions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.versions_table.setColumnWidth(3, 70)  # 设置操作列足够宽度
        self.versions_table.horizontalHeader().setStretchLastSection(False)
        self.versions_table.horizontalHeader().setSectionsClickable(False)
        self.versions_table.verticalHeader().setDefaultSectionSize(40)
        self.versions_table.setShowGrid(True)
        self.versions_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
        """)
        versions_layout.addWidget(self.versions_table)
        
        # 创建下载区域
        download_frame = QFrame()
        download_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        download_layout = QVBoxLayout(download_frame)
        
        download_header = QHBoxLayout()
        self.download_label = QLabel("下载进度:")
        self.download_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.download_path_btn = FunctionButton("选择下载路径")
        self.download_path_btn.setIcon(QIcon(os.path.join(self.icon_path, "folder.png")))
        self.download_path_btn.clicked.connect(self.select_download_path)
        self.download_path_btn.setMinimumWidth(150)  # 设置最小宽度
        download_header.addWidget(self.download_label)
        download_header.addStretch()
        download_header.addWidget(self.download_path_btn)
        
        # 添加下载信息显示
        download_info_layout = QHBoxLayout()
        self.speed_label = QLabel("速度: 0 KB/s")
        self.size_label = QLabel("大小: 0 MB")
        self.time_label = QLabel("时间: 00:00:00")
        
        download_info_layout.addWidget(self.speed_label)
        download_info_layout.addWidget(self.size_label)
        download_info_layout.addWidget(self.time_label)
        download_info_layout.addStretch()
        
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% (%v/%m)")
        
        download_layout.addLayout(download_header)
        download_layout.addLayout(download_info_layout)
        download_layout.addWidget(self.progress_bar)
        
        # 将所有组件添加到主布局
        main_layout.addWidget(toolbar)
        
        # 添加搜索警示标语（直接放在工具栏下方）
        main_layout.addLayout(search_tips_layout)
        
        main_layout.addWidget(results_frame)
        # 交换下载区域和版本区域的顺序
        main_layout.addWidget(versions_frame)
        main_layout.addWidget(download_frame)
        
        # 设置中央窗口部件
        self.setCentralWidget(central_widget)
        
        # 创建状态覆盖层
        self.status_overlay = StatusOverlay(self)
        
        # 设置状态栏
        self.statusBar().showMessage("准备就绪")
        
        # 设置默认下载路径
        self.download_path = self.config.get_download_path()
        
    def resizeEvent(self, event):
        """重写大小调整事件，确保覆盖层覆盖整个窗口"""
        super().resizeEvent(event)
        if hasattr(self, 'status_overlay'):
            self.status_overlay.setGeometry(self.rect())
        
    def _contains_chinese(self, text):
        """检查字符串是否包含中文字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def search_game(self):
        search_term_original = self.search_input.text().strip()
        if not search_term_original:
            QMessageBox.warning(self, "警告", "请输入游戏名称")
            return
        
        search_term_to_use = search_term_original
        
        # 检查是否需要翻译
        if self._contains_chinese(search_term_original):
            # 创建并显示翻译进度对话框
            self.progress_dialog = QProgressDialog("正在准备翻译游戏名称...", "取消", 0, 100, self)
            self.progress_dialog.setWindowTitle("正在翻译游戏名")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)  # 模态对话框
            self.progress_dialog.setMinimumDuration(500)  # 至少显示500ms
            self.progress_dialog.setAutoClose(False)  # 不自动关闭
            self.progress_dialog.setAutoReset(False)  # 不自动重置
            
            # 设置进度条无确定范围（因为无法准确知道翻译需要多少步骤）
            self.progress_dialog.setRange(0, 0) 
            self.progress_dialog.setValue(-1)
            
            # 设置取消按钮连接
            cancel_button = self.progress_dialog.findChild(QPushButton)
            if cancel_button:
                cancel_button.setText("取消")  # 显式设置为中文
                
            # 创建翻译线程
            self.translate_thread = TranslateThread(search_term_original)
            
            # 连接信号
            self.translate_thread.progress_signal.connect(self.update_translate_progress)
            self.translate_thread.result_signal.connect(self.on_translate_success)
            self.translate_thread.error_signal.connect(self.on_translate_error)
            self.translate_thread.finished_signal.connect(self.on_translate_finished)
            
            # 连接取消按钮
            self.progress_dialog.canceled.connect(self.translate_thread.cancel)
            
            # 启动线程
            self.translate_thread.start()
            
            # 显示进度对话框（这不会阻塞，因为QProgressDialog会自己处理事件循环）
            self.progress_dialog.exec()
            
            # 注意: 执行到这里时，对话框已关闭，但线程可能仍在运行
            # 实际的搜索将在 on_translate_success 或 on_translate_error 中进行
            return
        
        # 非中文搜索，直接使用原始输入
        self.statusBar().showMessage(f"正在搜索: {search_term_to_use}...")
        self._perform_search(search_term_to_use)
    
    def update_translate_progress(self, message):
        """更新翻译进度对话框的信息"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog.isVisible():
            self.progress_dialog.setLabelText(message)
    
    def on_translate_success(self, english_name):
        """翻译成功的回调"""
        # 保存结果，稍后在对话框关闭后使用
        self.translated_name = english_name
    
    def on_translate_error(self, error_message):
        """翻译失败的回调"""
        self.translate_error = error_message
    
    def on_translate_finished(self, success):
        """翻译线程完成的回调"""
        # 确保进度对话框关闭
        if hasattr(self, 'progress_dialog') and self.progress_dialog.isVisible():
            self.progress_dialog.close()
        
        # 获取原始搜索词
        original_term = self.search_input.text().strip()
        
        if success and hasattr(self, 'translated_name'):
            # 成功情况：显示成功信息并启动搜索
            english_name = self.translated_name
            self.statusBar().showMessage(f"翻译成功: {english_name}, 正在搜索...")
            
            # 显示翻译成功的提示（可选）
            # QMessageBox.information(self, "翻译成功", f"已将 \"{original_term}\" 翻译为 \"{english_name}\"")
            
            # 执行搜索
            self._perform_search(english_name)
        else:
            # 失败情况：显示错误提示并询问用户是否继续
            error_msg = getattr(self, 'translate_error', "未知错误")
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("翻译失败")
            msg_box.setText(f"未能找到 \"{original_term}\" 的英文名称。")
            msg_box.setInformativeText("您想使用原始中文继续搜索，还是取消搜索?")
            msg_box.setDetailedText(f"错误详情: {error_msg}")
            
            # 添加三个按钮：使用中文搜索、直接取消、手动输入英文
            search_cn_btn = msg_box.addButton("使用中文搜索", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg_box.addButton("取消搜索", QMessageBox.ButtonRole.RejectRole) 
            msg_box.addButton("手动输入英文", QMessageBox.ButtonRole.ActionRole)
            
            msg_box.setDefaultButton(search_cn_btn)
            msg_box.exec()
            
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == search_cn_btn:
                # 用户选择使用中文搜索
                self.statusBar().showMessage(f"使用原始中文搜索: {original_term}...")
                self._perform_search(original_term)
            elif clicked_button == cancel_btn:
                # 用户选择取消搜索
                self.statusBar().showMessage("搜索已取消")
            else:
                # 用户选择手动输入英文
                self.statusBar().showMessage("请手动输入游戏的英文名称")
                # 保持焦点在搜索框上，便于用户立即输入
                self.search_input.setFocus()
                self.search_input.selectAll()
    
    def _perform_search(self, search_term):
        """执行实际的搜索操作，从原始search_game方法中提取的逻辑"""
        # 显示状态指示
        if hasattr(self, 'status_overlay'):
            self.status_overlay.showMessage("搜索中")
            
        # 创建搜索线程
        self.search_thread = SearchThread(search_term)
        
        # 连接信号
        self.search_thread.result_signal.connect(self.display_search_results)
        self.search_thread.result_signal.connect(lambda: self.status_overlay.hideMessage() if hasattr(self, 'status_overlay') else None)
        self.search_thread.error_signal.connect(self.show_error)
        self.search_thread.error_signal.connect(lambda: self.status_overlay.hideMessage() if hasattr(self, 'status_overlay') else None)
        self.search_thread.progress_signal.connect(lambda msg: self.status_overlay.showMessage(msg) if hasattr(self, 'status_overlay') else None)
        
        # 启动线程
        self.search_thread.start()
    
    def display_search_results(self, results):
        # 隐藏状态指示器
        if hasattr(self, 'status_overlay'):
            self.status_overlay.hideMessage()
        
        self.results_table.setRowCount(0)  # 清空表格
        
        if not results:
            self.statusBar().showMessage("没有找到结果")
            return
            
        for i, result in enumerate(results):
            self.results_table.insertRow(i)
            self.results_table.setItem(i, 0, QTableWidgetItem(result["title"]))
            self.results_table.setItem(i, 1, QTableWidgetItem(result["date"]))
            
            # 创建按钮
            view_btn = TableButton("查看")
            view_btn.clicked.connect(lambda checked, url=result["url"]: self.view_trainer_page(url))
            
            # 使用按钮容器
            btn_container = ButtonContainer()
            btn_container.addButton(view_btn)
            
            self.results_table.setCellWidget(i, 2, btn_container)
            
        self.statusBar().showMessage(f"找到 {len(results)} 个结果")
        
    def view_trainer_page(self, url):
        # 显示状态指示
        if hasattr(self, 'status_overlay'):
            self.status_overlay.showMessage("加载修改器页面")
            
        # 使用线程获取页面内容
        class TrainerPageThread(QThread):
            result_signal = pyqtSignal(str)
            error_signal = pyqtSignal(str)
            
            def __init__(self, url):
                super().__init__()
                self.url = url
                
            def run(self):
                try:
                    scraper = WebScraper()
                    html = scraper.get_trainer_page(self.url)
                    self.result_signal.emit(html)
                except Exception as e:
                    self.error_signal.emit(str(e))
        
        # 创建并启动线程
        self.trainer_thread = TrainerPageThread(url)
        self.trainer_thread.result_signal.connect(self.process_trainer_page)
        self.trainer_thread.error_signal.connect(self.show_trainer_error)
        self.trainer_thread.error_signal.connect(lambda: self.status_overlay.hideMessage() if hasattr(self, 'status_overlay') else None)
        
        # 启动线程
        self.trainer_thread.start()
        
    def process_trainer_page(self, html):
        """处理获取到的修改器页面内容"""
        # 隐藏状态指示器
        if hasattr(self, 'status_overlay'):
            self.status_overlay.hideMessage()
            
        try:
            parser = HtmlParser()
            versions = parser.parse_trainer_versions(html)
            
            self.display_trainer_versions(versions)
            self.statusBar().showMessage(f"加载完成，找到 {len(versions)} 个版本")
        except Exception as e:
            self.show_error(f"解析修改器页面失败: {str(e)}")
    
    def show_trainer_error(self, error_message):
        """显示修改器页面加载错误"""
        self.statusBar().showMessage(f"错误: {error_message}")
        self.logger.error(error_message)
        QMessageBox.critical(self, "错误", f"加载修改器页面失败: {error_message}")

    def display_trainer_versions(self, versions):
        # 创建调试日志
        print(f"解析到 {len(versions)} 个下载版本:")
        for ver in versions:
            print(f"  - 文件名: {ver['filename']}")
            print(f"    日期: {ver['date']}")
            print(f"    大小: {ver['size']}")
            print(f"    下载URL: {ver['download_url']}")
            if 'file_type' in ver:
                print(f"    文件类型: {ver['file_type']}")
        
        self.versions_table.setRowCount(0)  # 清空表格
        self.trainer_links = []
        self.trainer_versions = versions  # 保存完整的版本信息以便后续使用
        self.download_buttons = []  # 保存所有下载按钮的引用
        
        # 添加说明文字
        if not hasattr(self, 'versions_info_label'):
            self.versions_info_label = QLabel("部分修改器有自动更新版本和独立版本，均出自风大之手")
            self.versions_info_label.setStyleSheet("""
                QLabel {
                    color: #FF6D00;
                    font-weight: bold;
                    font-style: italic;
                    padding: 5px;
                    background-color: rgba(255, 248, 225, 0.7);
                    border-radius: 4px;
                    border: 1px solid #FFE0B2;
                }
            """)
            # 在表格上方添加说明
            layout = self.versions_table.parentWidget().layout()
            if layout:
                # 获取表格在布局中的索引
                for i in range(layout.count()):
                    if layout.itemAt(i).widget() == self.versions_table:
                        # 在表格前插入标签
                        layout.insertWidget(i, self.versions_info_label)
                        break
        else:
            # 确保标签可见
            self.versions_info_label.setVisible(True)
        
        for i, version in enumerate(versions):
            self.versions_table.insertRow(i)
            self.versions_table.setItem(i, 0, QTableWidgetItem(version["filename"]))
            self.versions_table.setItem(i, 1, QTableWidgetItem(version["date"]))
            self.versions_table.setItem(i, 2, QTableWidgetItem(version["size"]))
            
            # 创建按钮
            download_btn = TableButton("下载")
            download_btn.clicked.connect(lambda checked, url=version["download_url"], index=i, btn=download_btn: 
                                         self.download_trainer(url, index, btn))
            self.download_buttons.append(download_btn)
            
            # 使用按钮容器
            btn_container = ButtonContainer()
            btn_container.addButton(download_btn)
            
            self.versions_table.setCellWidget(i, 3, btn_container)
            
            self.trainer_links.append(version["download_url"])
            
    def download_trainer(self, url, version_index=None, download_button=None):
        # 显示状态指示
        if hasattr(self, 'status_overlay'):
            self.status_overlay.showMessage("准备下载")
            
        # 禁用点击的下载按钮
        if download_button:
            download_button.setEnabled(False)
            download_button.setText("下载中")
            
        # 显示一个下载准备中的小提示（可选）
        self.statusBar().showMessage("正在准备下载...")
        
        if not self.download_path:
            self.download_path = os.path.expanduser('~/Downloads')
            self.config.set_download_path(self.download_path)
            
        if not os.path.exists(self.download_path):
            try:
                os.makedirs(self.download_path)
            except Exception as e:
                self.show_error(f"创建下载目录失败: {str(e)}")
                # 尝试使用默认下载路径
                self.download_path = os.path.expanduser('~/Downloads')
                try:
                    if not os.path.exists(self.download_path):
                        os.makedirs(self.download_path)
                except Exception as e2:
                    self.show_error(f"无法创建默认下载目录: {str(e2)}")
                    return
        
        # 查找对应的版本信息，获取正确的文件名
        filename = "trainer.zip"  # 默认文件名
        file_type = ""  # 默认文件类型
        
        # 首先尝试从传入的版本索引获取详细信息
        if version_index is not None and hasattr(self, 'trainer_versions') and 0 <= version_index < len(self.trainer_versions):
            version = self.trainer_versions[version_index]
            filename = version["filename"]
            if 'file_type' in version:
                file_type = version["file_type"]
        else:
            # 如果没有传入版本索引或找不到对应版本，从表格中查找
            for row in range(self.versions_table.rowCount()):
                button_container = self.versions_table.cellWidget(row, 3)
                # 检查是否是ButtonContainer对象，并获取内部的下载按钮
                if button_container and isinstance(button_container, ButtonContainer):
                    # 假设第一个按钮是下载按钮
                    for i in range(button_container.layout.count()):
                        download_button = button_container.layout.itemAt(i).widget()
                        if download_button and hasattr(download_button, 'clicked'):
                            # 获取对应行的文件名
                            filename_item = self.versions_table.item(row, 0)
                            if filename_item and filename_item.text():
                                filename = filename_item.text()
                                # 尝试找到对应的版本信息获取文件类型
                                if hasattr(self, 'trainer_versions') and row < len(self.trainer_versions):
                                    if 'file_type' in self.trainer_versions[row]:
                                        file_type = self.trainer_versions[row]['file_type']
                                break
        
        # 确保文件名有正确的扩展名
        if file_type:
            # 使用解析器提供的文件类型
            if not filename.lower().endswith(f".{file_type}"):
                filename = f"{filename}.{file_type}"
        else:
            # 回退到旧的判断逻辑
            if "LatestVersion" in filename or ".exe" in filename.lower() or url.endswith(".exe"):
                # 确保EXE文件有正确的扩展名
                if not filename.lower().endswith('.exe'):
                    filename += '.exe'
            else:
                # 非EXE文件默认使用ZIP扩展名
                if not (filename.lower().endswith('.zip') or filename.lower().endswith('.rar') or filename.lower().endswith('.7z')):
                    filename += '.zip'
        
        # 清理文件名中的非法字符
        filename = self._sanitize_filename(filename)
        
        save_path = os.path.join(self.download_path, filename)
        
        # 检查文件是否已存在
        if os.path.exists(save_path):
            reply = QMessageBox.question(
                self, 
                "文件已存在", 
                f"文件 {filename} 已存在，是否覆盖?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                # 尝试创建一个新的文件名
                base_name, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(save_path):
                    new_filename = f"{base_name}_{counter}{ext}"
                    save_path = os.path.join(self.download_path, new_filename)
                    counter += 1
                filename = os.path.basename(save_path)
        
        # 重置下载信息
        self.download_start_time = None
        self.download_speed = "0 KB/s"
        self.download_size = "0 MB"
        self.download_elapsed = "00:00:00"
        self.speed_label.setText(f"速度: {self.download_speed}")
        self.size_label.setText(f"大小: {self.download_size}")
        self.time_label.setText(f"时间: {self.download_elapsed}")
        
        self.statusBar().showMessage(f"开始下载: {filename}")
        self.progress_bar.setValue(0)
        
        # 如果正在进行下载，先取消
        if self.download_thread and self.download_thread.isRunning():
            try:
                self.download_thread.cancel()
                self.download_thread.wait(1000)  # 等待最多1秒
            except:
                pass
                
        self.download_thread = DownloadThread(url, save_path)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.show_error)
        self.download_thread.error_signal.connect(lambda: self.status_overlay.hideMessage() if hasattr(self, 'status_overlay') else None)
        self.download_thread.start()
        
        # 隐藏状态指示器（下载开始后通过进度条显示状态）
        if hasattr(self, 'status_overlay'):
            self.status_overlay.hideMessage()
        
        # 添加取消下载按钮
        if not hasattr(self, 'cancel_download_btn'):
            self.cancel_download_btn = QPushButton("取消下载")
            self.cancel_download_btn.clicked.connect(self.cancel_download)
            self.cancel_download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
                QPushButton:pressed {
                    background-color: #b71c1c;
                }
            """)
        
        # 在下载信息布局中添加取消按钮
        layout = self.speed_label.parent().layout()
        if layout and self.cancel_download_btn not in [layout.itemAt(i).widget() for i in range(layout.count()) if layout.itemAt(i).widget()]:
            layout.addWidget(self.cancel_download_btn)
        
    def update_progress(self, value, speed_info):
        # 确保 value 是整数
        if isinstance(value, int):
             if value == -1:
                 # 总大小未知，只更新速度，不更新进度条数值
                 self.progress_bar.setFormat(f"已下载: {self.progress_bar.value() * self.progress_bar.maximum() / 100 / (1024*1024):.2f} MB - {speed_info}") # 假设最大值代表总大小
             else:
                 self.progress_bar.setValue(value)
                 self.progress_bar.setFormat("%p% - " + speed_info) # 标准格式显示百分比和速度
        else:
             # 如果传入的不是整数，记录一个警告或错误
             self.logger.warning(f"收到非整数进度值: {value}")
             # 或者设置一个默认值
             # self.progress_bar.setValue(0)

        # 更新下载信息
        if self.download_start_time is None:
            self.download_start_time = QDateTime.currentDateTime()
        
        # 计算已用时间
        elapsed = QDateTime.currentDateTime().toMSecsSinceEpoch() - self.download_start_time.toMSecsSinceEpoch()
        seconds = elapsed // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        self.download_elapsed = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # 更新显示
        self.speed_label.setText(f"速度: {speed_info}")
        self.time_label.setText(f"时间: {self.download_elapsed}")
        
    def download_finished(self, save_path):
        # 隐藏状态指示器
        if hasattr(self, 'status_overlay'):
            self.status_overlay.hideMessage()
        
        self.progress_bar.setValue(100)
        self.statusBar().showMessage(f"下载完成: {save_path}")
        
        # 从下载信息布局中移除取消按钮
        if hasattr(self, 'cancel_download_btn'):
            layout = self.speed_label.parent().layout()
            if layout:
                layout.removeWidget(self.cancel_download_btn)
                self.cancel_download_btn.hide()
        
        # 重置下载信息
        self.download_start_time = None
        self.download_speed = "0 KB/s"
        self.download_size = "0 MB"
        self.download_elapsed = "00:00:00"
        self.speed_label.setText(f"速度: {self.download_speed}")
        self.size_label.setText(f"大小: {self.download_size}")
        self.time_label.setText(f"时间: {self.download_elapsed}")
        
        reply = QMessageBox.question(
            self, 
            "下载完成", 
            f"文件已保存到: {save_path}\n是否打开文件所在文件夹?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 打开文件所在文件夹
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(save_path)))
            
        # 重新启用所有下载按钮
        if hasattr(self, 'download_buttons'):
            for btn in self.download_buttons:
                btn.setEnabled(True)
                btn.setText("下载")
        
    def select_download_path(self):
        folder = QFileDialog.getExistingDirectory(self, "选择下载文件夹", self.download_path)
        if folder:
            self.download_path = folder
            self.config.set_download_path(folder)
            self.statusBar().showMessage(f"下载路径已更改: {folder}")
            
    def open_official_site(self):
        QDesktopServices.openUrl(QUrl("https://flingtrainer.com/"))
        
    def show_error(self, message):
        self.statusBar().showMessage(f"错误: {message}")
        self.logger.error(message)
        QMessageBox.critical(self, "错误", message)
        
        # 重新启用所有下载按钮
        if hasattr(self, 'download_buttons'):
            for btn in self.download_buttons:
                btn.setEnabled(True)
                btn.setText("下载")

    def _sanitize_filename(self, filename):
        """清理文件名中的非法字符"""
        # Windows系统不允许文件名包含这些字符: \ / : * ? " < > |
        invalid_chars = r'[\\/:\*\?"<>\|]'
        return re.sub(invalid_chars, '_', filename)

    def cancel_download(self):
        """取消当前下载"""
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self, 
                "取消下载", 
                "确定要取消当前下载吗?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.statusBar().showMessage("正在取消下载...")
                self.download_thread.cancel()
                
                # 从下载信息布局中移除取消按钮
                if hasattr(self, 'cancel_download_btn'):
                    layout = self.speed_label.parent().layout()
                    if layout:
                        layout.removeWidget(self.cancel_download_btn)
                        self.cancel_download_btn.hide()
                
                self.statusBar().showMessage("下载已取消")