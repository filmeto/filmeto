from PySide6.QtWidgets import QDialog, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt, QPoint, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from .mac_button import MacTitleBar
from ..styles import DIALOG_STYLE


class LeftPanelDialog(QDialog):
    """左侧面板对话框，无顶部标题栏，分为左边栏和右边工作区"""

    # 设置按钮点击信号
    settings_clicked = Signal()
    # 服务器状态按钮点击信号
    server_status_clicked = Signal()

    def __init__(self, parent=None, left_panel_width=200, show_right_title_bar=True, workspace=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_QuitOnClose, False)  # Don't quit app when dialog closes

        # Store workspace for server status widget
        self._workspace = workspace

        # 应用全局对话框样式
        self.setStyleSheet(DIALOG_STYLE)

        # 主布局 - 水平布局，分为左右两部分
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左边栏容器
        self.left_panel = QFrame()
        self.left_panel.setObjectName("LeftPanelDialogLeftPanel")
        self.left_panel.setFixedWidth(left_panel_width)
        # 样式已移至全局样式表 DIALOG_STYLE

        # 左边栏布局 - 垂直布局
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Mac风格的窗口控制按钮组 - 放置在左边栏左上角
        self.mac_control_buttons = MacTitleBar(self)
        self.mac_control_buttons.set_for_dialog()
        self.mac_control_buttons.show_navigation_buttons(False)
        left_layout.addWidget(self.mac_control_buttons)

        # 左边栏内容区域容器（供子类扩展）
        self.left_content_container = QWidget()
        self.left_content_container.setObjectName("LeftPanelDialogLeftContent")
        self.left_content_layout = QVBoxLayout(self.left_content_container)
        self.left_content_layout.setContentsMargins(8, 8, 8, 8)
        self.left_content_layout.setSpacing(8)
        left_layout.addWidget(self.left_content_container)

        # 添加弹性空间，将内容推到顶部
        left_layout.addStretch()

        main_layout.addWidget(self.left_panel)

        # 右边工作区容器
        self.right_work_area = QFrame()
        self.right_work_area.setObjectName("LeftPanelDialogRightWorkArea")
        # 样式已移至全局样式表 DIALOG_STYLE

        # 右边工作区主布局
        right_main_layout = QVBoxLayout(self.right_work_area)
        right_main_layout.setContentsMargins(0, 0, 0, 0)
        right_main_layout.setSpacing(0)

        # 右边顶部标题条（与左边栏配色一致，无缝衔接）
        self._show_right_title_bar = show_right_title_bar
        if show_right_title_bar:
            self.right_title_bar = QFrame()
            self.right_title_bar.setObjectName("LeftPanelDialogRightTitleBar")
            self.right_title_bar.setFixedHeight(40)  # 与 Mac 控制按钮高度一致

            # 标题条布局
            title_bar_layout = QHBoxLayout(self.right_title_bar)
            title_bar_layout.setContentsMargins(16, 0, 12, 0)

            # 标题标签
            self.right_title_label = QLabel()
            self.right_title_label.setObjectName("LeftPanelDialogRightTitleLabel")
            title_bar_layout.addWidget(self.right_title_label)
            title_bar_layout.addStretch()

            # Server status button (if workspace is provided)
            self.server_status_widget = None
            if self._workspace:
                from app.ui.server_status import ServerStatusWidget
                self.server_status_widget = ServerStatusWidget(self._workspace)
                self.server_status_widget.show_status_dialog.connect(self._on_server_status_clicked)
                title_bar_layout.addWidget(self.server_status_widget.status_button)

            # 设置按钮
            self.settings_button = QPushButton("\ue60f")  # settings icon
            self.settings_button.setObjectName("LeftPanelDialogSettingsButton")
            self.settings_button.setFixedSize(32, 32)
            self.settings_button.setCursor(Qt.PointingHandCursor)
            self.settings_button.clicked.connect(self._on_settings_clicked)
            title_bar_layout.addWidget(self.settings_button)

            right_main_layout.addWidget(self.right_title_bar)
        else:
            self.right_title_bar = None
            self.right_title_label = None
            self.settings_button = None
            self.server_status_widget = None

        # 右边工作区内容容器
        self.right_work_container = QWidget()
        self.right_work_container.setObjectName("LeftPanelDialogRightWorkContainer")
        self.right_work_layout = QVBoxLayout(self.right_work_container)
        self.right_work_layout.setContentsMargins(20, 20, 20, 20)
        self.right_work_layout.setSpacing(10)

        right_main_layout.addWidget(self.right_work_container)

        main_layout.addWidget(self.right_work_area)

        # 启用鼠标跟踪，用于窗口拖拽
        self.setMouseTracking(True)
        self.drag_position = QPoint()
        self.drag_enabled = True

    def _on_settings_clicked(self):
        """设置按钮点击处理"""
        self.settings_clicked.emit()

    def _on_server_status_clicked(self):
        """服务器状态按钮点击处理"""
        self.server_status_clicked.emit()
    
    def mousePressEvent(self, event: QMouseEvent):
        """处理鼠标按下事件，用于窗口拖拽"""
        if event.button() == Qt.LeftButton and self.drag_enabled:
            # 检查点击位置是否在MacTitleBar的按钮区域内
            click_pos = event.position().toPoint()
            mac_buttons_rect = self.mac_control_buttons.geometry()

            # 如果点击在MacTitleBar区域内，检查是否点击在按钮上
            if mac_buttons_rect.contains(click_pos):
                # 检查是否点击在具体的按钮上
                mac_buttons = self.mac_control_buttons.findChildren(QWidget)
                clicked_on_button = False
                for button in mac_buttons:
                    # 将按钮的全局坐标转换为相对于对话框的坐标
                    button_global_pos = button.mapTo(self, QPoint(0, 0))
                    button_rect = button.geometry()
                    button_rect.moveTopLeft(button_global_pos)
                    if button_rect.contains(click_pos):
                        clicked_on_button = True
                        break

                # 如果点击在按钮上，不处理拖拽，让按钮处理点击事件
                if clicked_on_button:
                    super().mousePressEvent(event)
                    return

            # 其他区域允许拖拽（包括左边栏和右边标题条）
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return

        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """处理鼠标移动事件，用于窗口拖拽"""
        if event.buttons() == Qt.LeftButton and not self.drag_position.isNull() and self.drag_enabled:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            return
        
        super().mouseMoveEvent(event)
    
    def set_left_panel_width(self, width: int):
        """设置左边栏宽度"""
        self.left_panel.setFixedWidth(width)
    
    def set_left_content_layout(self, layout):
        """设置左边栏内容布局"""
        # 清除现有的布局项
        while self.left_content_layout.count():
            item = self.left_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()
        
        # 添加新布局
        self.left_content_layout.addLayout(layout)
    
    def set_left_content_widget(self, widget):
        """设置左边栏内容控件"""
        # 清除现有的布局项
        while self.left_content_layout.count():
            item = self.left_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()
        
        # 添加控件
        self.left_content_layout.addWidget(widget)
    
    def add_left_content_widget(self, widget):
        """添加控件到左边栏内容区域"""
        self.left_content_layout.addWidget(widget)
    
    def add_left_content_layout(self, layout):
        """添加布局到左边栏内容区域"""
        self.left_content_layout.addLayout(layout)
    
    def set_right_work_layout(self, layout):
        """设置右边工作区布局"""
        # 清除现有的布局项
        while self.right_work_layout.count():
            item = self.right_work_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()
        
        # 添加新布局
        self.right_work_layout.addLayout(layout)
    
    def set_right_work_widget(self, widget):
        """设置右边工作区控件"""
        # 清除现有的布局项
        while self.right_work_layout.count():
            item = self.right_work_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()
        
        # 添加控件
        self.right_work_layout.addWidget(widget)
    
    def add_right_work_widget(self, widget):
        """添加控件到右边工作区"""
        self.right_work_layout.addWidget(widget)
    
    def add_right_work_layout(self, layout):
        """添加布局到右边工作区"""
        self.right_work_layout.addLayout(layout)
    
    def set_drag_enabled(self, enabled: bool):
        """设置是否允许拖拽窗口"""
        self.drag_enabled = enabled

    def set_right_title(self, title: str):
        """设置右边标题条的标题文本"""
        if self.right_title_label:
            self.right_title_label.setText(title)

    def reject(self):
        """Override reject to properly restore parent window state"""
        # Clear focus first
        self.clearFocus()
        # Release mouse grab
        self.releaseMouse()
        # Call parent reject
        super().reject()
        # Restore parent window activation
        self._restore_parent_window()

    def done(self, result):
        """Override done to properly restore parent window state"""
        # Clear focus first
        self.clearFocus()
        # Release mouse grab
        self.releaseMouse()
        # Call parent done
        super().done(result)
        # Restore parent window activation
        self._restore_parent_window()

    def _restore_parent_window(self):
        """Restore parent window activation and focus"""
        parent = self.parentWidget()
        if parent:
            parent.setEnabled(True)
            self._do_activate_parent(parent)
        else:
            active = QApplication.activeWindow()
            if active:
                self._do_activate_parent(active)

    def _do_activate_parent(self, parent):
        """Actually activate the parent window."""
        try:
            if not self.isHidden():
                self.setWindowModality(Qt.NonModal)

            if parent and not parent.isHidden():
                parent.setEnabled(True)
                parent.activateWindow()
                parent.raise_()
                parent.setFocus()
        except RuntimeError:
            pass

