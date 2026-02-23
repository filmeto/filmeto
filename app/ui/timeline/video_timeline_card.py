import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QGraphicsDropShadowEffect, QSizePolicy, QPushButton, QScrollArea, QGridLayout,
    QMenu
)
from PySide6.QtGui import QPixmap, QColor, QPalette, QPainter, QFont, QAction
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint, QTimer, Property, QSize

logger = logging.getLogger(__name__)


class VideoTimelineCard(QFrame):
    """
    一个自定义 QFrame，通过边框高亮来显示悬停和选中状态。
    """

    def __init__(self, parent, content_text, snapshot:QPixmap, index):
        super().__init__(parent)
        self.parent = parent
        self.index = index
        # --- 基本配置 ---
        self.setFrameStyle(QFrame.NoFrame)  # Use CSS for all styling to avoid Qt's frame affecting size
        self.setLineWidth(0)  # Use CSS for borders
        # 设置初始大小 - keep the original visual size
        self.setFixedSize(90, 160)  # Use fixed size to prevent any fluctuations
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 启用鼠标跟踪
        self.setMouseTracking(True)

        # --- 内容 ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins so image fills the frame

        self.content_label = QLabel(content_text)
        # Enable transparency support and remove any borders from the label
        # Add border-radius to match the outer frame's rounded corners
        self.content_label.setStyleSheet("QLabel { background-color: transparent; border: none; border-radius: 8px; }")
        self.content_label.setScaledContents(True)  # Enable scaled contents for proper clipping
        # Make label transparent to mouse events so clicks pass through to parent card
        # This allows the parent container's eventFilter to handle card selection
        self.content_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        scaled_image = snapshot.scaled(QSize(90, 160), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.content_label.setPixmap(scaled_image)
        self.content_label.setAlignment(Qt.AlignCenter)
        self.content_label.setWordWrap(True)
        font = self.content_label.font()
        font.setPointSize(10)
        self.content_label.setFont(font)
        layout.addWidget(self.content_label)

        # 创建菜单按钮（默认隐藏）
        self.menu_button = QPushButton("⋮")
        self.menu_button.setFixedSize(20, 20)
        self.menu_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.7);
            }
        """)
        self.menu_button.hide()
        self.menu_button.clicked.connect(self.show_context_menu)
        # 使用绝对定位将按钮放在右上角
        self.menu_button.setParent(self)
        self.menu_button.move(self.width() - self.menu_button.width() - 5, 5)

        # --- 状态 ---
        self._is_hovered = False
        self._is_selected = False
        
        # 更新样式
        self._update_style()

    def is_hovered(self):
        return self._is_hovered

    def set_hovered(self, hovered):
        if self._is_hovered != hovered:
            self._is_hovered = hovered
            self._update_style()
            # 当鼠标悬停时显示菜单按钮，否则隐藏
            if hovered:
                self.menu_button.show()
            else:
                self.menu_button.hide()
    
    def is_selected(self):
        return self._is_selected
    
    def set_selected(self, selected):
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_style()
    
    def _update_style(self):
        """根据悬停和选中状态更新边框样式"""
        # To solve the size fluctuation problem, use a fixed border that provides
        # the different visual states without changing the widget's size.
        # The original approach used 1px/2px/3px borders which caused size changes.
        # This solution maintains the same 3px border but changes the visual weight
        # by adjusting the color contrast to simulate different border thicknesses.
        
        if self._is_selected:
            # Selected: bright blue border for maximum visual impact (equivalent to thick border)
            self.setStyleSheet("""
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #4080ff;
                    border-radius: 8px;
                }
            """)
        elif self._is_hovered:
            # Hover: medium blue border for moderate visual impact (equivalent to medium border)
            self.setStyleSheet("""
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #6a9eff;
                    border-radius: 8px;
                }
            """)
        else:
            # Default: light gray border for minimal visual impact (equivalent to thin border)
            self.setStyleSheet("""
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #a0a0a0;
                    border-radius: 8px;
                }
            """)

    def enterEvent(self, event):
        """当鼠标进入控件时触发"""
        super().enterEvent(event)
        self.set_hovered(True)

    def leaveEvent(self, event):
        """当鼠标离开控件时触发"""
        super().leaveEvent(event)
        self.set_hovered(False)

    def setContent(self, text):
        """设置显示的文本内容"""
        self.content_label.setText(text)

    def setImage(self,snapshot:QPixmap):
        scaled_image = snapshot.scaled(QSize(90, 160), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.content_label.setPixmap(scaled_image)

    def show_context_menu(self, event):
        """显示上下文菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #4080ff;
            }
        """)
        
        delete_action = QAction("Delete", self)
        clean_action = QAction("Clean", self)
        move_action = QAction("Move", self)
        
        menu.addAction(delete_action)
        menu.addAction(clean_action)
        menu.addAction(move_action)
        
        # 连接动作到处理函数
        delete_action.triggered.connect(self.delete_item)
        clean_action.triggered.connect(self.clean_item)
        move_action.triggered.connect(self.move_item)
        
        # 在按钮下方显示菜单
        button_pos = self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height()))
        menu.exec(button_pos)

    def delete_item(self):
        """删除项目"""
        logger.info(f"Deleting item at index {self.index}")
        # 实现删除逻辑

    def clean_item(self):
        """清理项目"""
        logger.info(f"Cleaning item at index {self.index}")
        # 实现清理逻辑

    def move_item(self):
        """移动项目"""
        logger.info(f"Moving item at index {self.index}")
        # 实现移动逻辑