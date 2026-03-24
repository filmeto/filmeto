import logging
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.dialog.dialog_view_model import (
    CustomDialogTitleBarViewModel,
    DialogTitleDragViewModel,
    MacWindowControlsViewModel,
)

from ..styles import DIALOG_STYLE, _darken_color, _lighten_color

logger = logging.getLogger(__name__)


class CustomTitleBar(QFrame):
    """Title bar: mac controls, optional nav, title + drag, toolbar (QWidget) — QML chrome."""

    back_clicked = Signal()
    forward_clicked = Signal()

    def __init__(self, parent, title=""):
        super().__init__(parent)
        self.setObjectName("CustomDialogTitleBar")
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.parent_dialog = parent

        self._mac = MacWindowControlsViewModel(parent, self)
        self._mac.set_dialog_mode(True)
        self._title_bridge = CustomDialogTitleBarViewModel(self)
        self._title_bridge.title = title
        self._title_bridge.back_clicked.connect(self.back_clicked.emit)
        self._title_bridge.forward_clicked.connect(self.forward_clicked.emit)
        self._drag = DialogTitleDragViewModel(parent, self)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 8, 0)
        row.setSpacing(0)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setClearColor(Qt.transparent)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setStyleSheet("background: transparent;")
        self._quick.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._quick.setFixedHeight(36)

        qml_dir = Path(__file__).resolve().parent.parent / "qml" / "dialog"
        self._quick.engine().addImportPath(str(qml_dir.parent))
        rc = self._quick.rootContext()
        rc.setContextProperty("chromeMacActions", self._mac)
        rc.setContextProperty("chromeTitleModel", self._title_bridge)
        rc.setContextProperty("chromeDragBridge", self._drag)

        self._quick.setSource(QUrl.fromLocalFile(str(qml_dir / "CustomDialogTitleBar.qml")))

        if self._quick.status() == QQuickWidget.Error:
            for err in self._quick.errors():
                logger.error("CustomDialogTitleBar QML: %s", err.toString())

        row.addWidget(self._quick, 1)

        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(8)
        row.addLayout(self.toolbar_layout)

        self.setMouseTracking(True)

    def set_title(self, title):
        self._title_bridge.title = title

    def show_navigation_buttons(self, show: bool = True):
        self._title_bridge.navVisible = show

    def set_navigation_enabled(self, back_enabled: bool, forward_enabled: bool):
        self._title_bridge.backEnabled = back_enabled
        self._title_bridge.forwardEnabled = forward_enabled
    


class CustomDialog(QDialog):
    """自定义无边框对话框"""

    # Forward navigation signals
    back_clicked = Signal()
    forward_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_QuitOnClose, False)  # Don't quit app when dialog closes

        # 应用全局对话框样式
        self.setStyleSheet(DIALOG_STYLE)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建自定义标题栏
        self.title_bar = CustomTitleBar(self)
        # Forward navigation signals from title bar
        self.title_bar.back_clicked.connect(self.back_clicked.emit)
        self.title_bar.forward_clicked.connect(self.forward_clicked.emit)
        main_layout.addWidget(self.title_bar)

        # 内容区域容器 - includes both content and button area
        self.content_container = QFrame()
        self.content_container.setObjectName("CustomDialogContentContainer")  # Add object name for CSS
        # 样式已移至全局样式表 DIALOG_STYLE

        # Main content layout that will contain both the content and button area
        self.main_content_layout = QVBoxLayout(self.content_container)
        self.main_content_layout.setContentsMargins(20, 15, 20, 15)  # Keep consistent margins
        self.main_content_layout.setSpacing(10)

        # Content area layout for user content
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 10)  # Add bottom margin for button area
        self.main_content_layout.addLayout(self.content_layout)

        # Bottom button area - now properly contained within content container
        self.button_area = QWidget()
        self.button_area.setObjectName("CustomDialogButtonArea")  # Add object name for CSS
        self.button_area_layout = QHBoxLayout(self.button_area)
        self.button_area_layout.setContentsMargins(0, 0, 0, 0)
        self.button_area_layout.setSpacing(10)
        # Align buttons to the right by adding a stretch at the end
        # Initially hide the button area until buttons are added
        self.button_area.hide()
        self.main_content_layout.addWidget(self.button_area)

        main_layout.addWidget(self.content_container)

        # 启用鼠标跟踪
        self.setMouseTracking(True)
        self.drag_position = QPoint()
    
    def mousePressEvent(self, event: QMouseEvent):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """处理鼠标移动事件"""
        if event.buttons() == Qt.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """处理鼠标释放事件"""
        self.drag_position = QPoint()
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        """处理关闭事件 - 确保清理资源"""
        # Clear focus to release any focus grabs
        self.clearFocus()
        # Release mouse grab if any
        self.releaseMouse()
        # Closing via window controls bypasses reject()/done(); explicitly
        # restore parent activation to avoid leaving UI input blocked.
        self._restore_parent_window()
        # Accept the close event
        event.accept()

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
        modal = QApplication.activeModalWidget()
        logger.info(
            "CustomDialog restore parent=%s modal=%s active=%s",
            type(parent).__name__ if parent else "None",
            type(modal).__name__ if modal else "None",
            type(QApplication.activeWindow()).__name__ if QApplication.activeWindow() else "None",
        )
        if parent:
            # Ensure parent is enabled immediately (was blocked by modal dialog)
            parent.setEnabled(True)
            # Activate parent window SYNCHRONOUSLY to ensure it's ready when exec() returns
            self._do_activate_parent(parent)
        else:
            active = QApplication.activeWindow()
            if active:
                self._do_activate_parent(active)

    def _do_activate_parent(self, parent):
        """Actually activate the parent window."""
        try:
            # Check if dialog is still valid before accessing it
            if not self.isHidden():
                # Clear modal state first (only if dialog still visible)
                self.setWindowModality(Qt.NonModal)

            if parent and not parent.isHidden():
                parent.setEnabled(True)
                parent.activateWindow()
                parent.raise_()
                parent.setFocus()
                logger.info(
                    "CustomDialog activated parent=%s parent_enabled=%s focus_widget=%s",
                    type(parent).__name__,
                    parent.isEnabled(),
                    type(QApplication.focusWidget()).__name__ if QApplication.focusWidget() else "None",
                )
        except RuntimeError:
            # Dialog may have been destroyed
            pass

    def set_title(self, title):
        """设置对话框标题"""
        self.title_bar.set_title(title)
    
    def show_navigation_buttons(self, show: bool = True):
        """Show or hide navigation buttons in title bar"""
        self.title_bar.show_navigation_buttons(show)
    
    def set_navigation_enabled(self, back_enabled: bool, forward_enabled: bool):
        """Enable or disable navigation buttons in title bar"""
        self.title_bar.set_navigation_enabled(back_enabled, forward_enabled)
    
    def setContentLayout(self, layout):
        """设置内容布局"""
        # 清除现有的布局项
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加新布局
        self.content_layout.addLayout(layout)
    
    def setContentWidget(self, widget):
        """设置内容控件"""
        # 清除现有的布局项
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加控件
        self.content_layout.addWidget(widget)

    def add_button(self, text, handler=None, role="default"):
        """
        Add a button to the standardized button area

        Args:
            text: Button text
            handler: Function to call when button is clicked
            role: Role of the button (e.g., 'accept', 'reject', 'default')
        """
        button = QPushButton(text)
        self._style_button(button, role)

        if handler:
            button.clicked.connect(handler)

        # Check if layout is currently empty (first button)
        is_first_button = self.button_area_layout.count() == 0

        # Add a stretch at the beginning for right-alignment if this is the first button
        if is_first_button:
            self.button_area_layout.insertStretch(0)  # Insert stretch at position 0
            self.button_area_layout.addWidget(button)  # Add button after the stretch
        else:
            # Not the first button, just add it (after the initial stretch)
            self.button_area_layout.addWidget(button)

        self.button_area.show()

        # Return the button so the caller can reference it if needed
        return button

    def add_button_row(self, buttons_config):
        """
        Add a row of buttons to the standardized button area

        Args:
            buttons_config: List of tuples (text, handler, role)
        """
        # Clear existing buttons in the button area
        self.clear_buttons()

        # Add a stretch at the beginning for right-alignment
        self.button_area_layout.insertStretch(0)

        # Add the buttons after the stretch
        for text, handler, role in buttons_config:
            # Create the button directly without calling add_button to avoid
            # redundantly showing the button area again
            button = QPushButton(text)
            self._style_button(button, role)

            if handler:
                button.clicked.connect(handler)

            self.button_area_layout.addWidget(button)

        # Show the button area after adding all buttons
        self.button_area.show()

    def clear_buttons(self):
        """Clear all buttons from the button area"""
        import warnings

        # Remove all widgets from the layout
        while self.button_area_layout.count():
            item = self.button_area_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                # Disconnect all signals to prevent callbacks to deleted widgets
                try:
                    if hasattr(widget, 'clicked'):
                        # Suppress RuntimeWarning when no connections exist
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", RuntimeWarning)
                            widget.clicked.disconnect()
                except (RuntimeError, TypeError):
                    pass
                # Use delayed deletion to avoid immediate destruction during signal handling
                widget.deleteLater()

        # Hide the button area after clearing
        self.button_area.hide()

    def _style_button(self, button, role):
        """Apply consistent button styling based on role"""
        # Default styling similar to ServerConfigDialog
        if role == "accept":
            color = "#4CAF50"  # Green for accept/save
        elif role == "reject":
            color = "#555555"  # Gray for cancel
        elif role == "danger":
            color = "#F44336"  # Red for dangerous actions
        else:
            color = "#4c5052"  # Default color

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color)};
            }}
        """)

    def _lighten_color(self, color: str) -> str:
        """Lighten a hex color"""
        return _lighten_color(color)

    def _darken_color(self, color: str) -> str:
        """Darken a hex color"""
        return _darken_color(color)