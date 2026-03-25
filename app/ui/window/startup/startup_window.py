# -*- coding: utf-8 -*-
"""
Startup Window

Independent window for startup/home mode with its own size management.
Uses a startup-specific QML host for the left/right chrome/background.
"""
import json
import logging
import os

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal, QPoint, QUrl
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtQuickWidgets import QQuickWidget

from app.data.workspace import Workspace
from app.ui.dialog.mac_button import MacTitleBar
from app.ui.styles import DIALOG_STYLE
from app.ui.window.startup.project_list_widget import ProjectListWidget
from app.ui.window.startup.project_startup_widget import ProjectStartupWidget

logger = logging.getLogger(__name__)


class StartupWindow(QDialog):
    """
    Independent window for startup/home mode.

    This window displays the project list and project info,
    allowing users to browse and manage projects.
    """

    enter_edit_mode = Signal(str)  # Emits project name when entering edit mode

    def __init__(self, workspace: Workspace):
        super().__init__(parent=None)
        self.workspace = workspace

        self._pending_prompt = None
        self._pending_startup_target = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_QuitOnClose, False)  # Don't quit app when dialog closes
        self.setStyleSheet(DIALOG_STYLE)

        self.drag_position = QPoint()
        self.drag_enabled = True

        self._window_sizes = {}
        self._load_window_sizes()

        self._setup_ui()

        width, height = self._get_window_size()
        self.resize(width, height)
        self.setWindowState(Qt.WindowNoState)
        screen = self.screen().availableGeometry()
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)

    def _load_window_sizes(self):
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    self._window_sizes = json.load(f)
            else:
                self._window_sizes = {"startup": {"width": 1600, "height": 900}}
        except Exception as e:
            logger.error("Error loading window sizes: %s", e)
            self._window_sizes = {"startup": {"width": 1600, "height": 900}}

    def _save_window_sizes(self):
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")
            existing_sizes = {}
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    existing_sizes = json.load(f)
            existing_sizes["startup"] = {"width": self.width(), "height": self.height()}
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(existing_sizes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error saving window sizes: %s", e)

    def _get_window_size(self):
        stored = (self._window_sizes or {}).get("startup", {})
        return int(stored.get("width", 1600)), int(stored.get("height", 900))

    def closeEvent(self, event):
        self._save_window_sizes()
        QApplication.instance().quit()
        event.accept()

    def _setup_ui(self):
        # QML-backed host provides chrome/background; QWidget containers overlay content.
        host_root = QWidget(self)
        host_root.setObjectName("StartupWindowHostRoot")
        host_stack = QStackedLayout(host_root)
        host_stack.setContentsMargins(0, 0, 0, 0)
        host_stack.setStackingMode(QStackedLayout.StackAll)

        self._qml_host = QQuickWidget(host_root)
        self._qml_host.setObjectName("StartupWindowHostQml")
        self._qml_host.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._qml_host.setAttribute(Qt.WA_TranslucentBackground, True)
        self._qml_host.setClearColor(Qt.transparent)
        qml_root_dir = Path(__file__).resolve().parent.parent.parent / "qml"
        self._qml_host.engine().addImportPath(str(qml_root_dir))
        qml_path = qml_root_dir / "startup" / "StartupWindowHost.qml"
        self._qml_host.setSource(QUrl.fromLocalFile(str(qml_path)))
        host_stack.addWidget(self._qml_host)

        content_root = QWidget(host_root)
        content_root.setObjectName("StartupWindowContentRoot")
        host_stack.addWidget(content_root)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(host_root)

        content_layout = QHBoxLayout(content_root)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("LeftPanelDialogLeftPanel")
        self.left_panel.setFixedWidth(250)

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.mac_control_buttons = MacTitleBar(self)
        self.mac_control_buttons.set_for_dialog()
        self.mac_control_buttons.show_navigation_buttons(False)
        left_layout.addWidget(self.mac_control_buttons)

        self.left_content_container = QWidget()
        self.left_content_container.setObjectName("LeftPanelDialogLeftContent")
        self.left_content_layout = QVBoxLayout(self.left_content_container)
        self.left_content_layout.setContentsMargins(8, 8, 8, 8)
        self.left_content_layout.setSpacing(8)
        left_layout.addWidget(self.left_content_container)
        left_layout.addStretch()

        content_layout.addWidget(self.left_panel)

        self.right_work_area = QFrame()
        self.right_work_area.setObjectName("LeftPanelDialogRightWorkArea")

        right_main_layout = QVBoxLayout(self.right_work_area)
        right_main_layout.setContentsMargins(0, 0, 0, 0)
        right_main_layout.setSpacing(0)

        self.right_title_bar = QFrame()
        self.right_title_bar.setObjectName("LeftPanelDialogRightTitleBar")
        self.right_title_bar.setFixedHeight(40)

        title_bar_layout = QHBoxLayout(self.right_title_bar)
        title_bar_layout.setContentsMargins(16, 0, 12, 0)

        self.right_title_label = QLabel()
        self.right_title_label.setObjectName("LeftPanelDialogRightTitleLabel")
        title_bar_layout.addWidget(self.right_title_label)
        title_bar_layout.addStretch()

        self.server_status_widget = None
        if self.workspace:
            from app.ui.server_status import ServerStatusWidget

            self.server_status_widget = ServerStatusWidget(self.workspace)
            self.server_status_widget.show_status_dialog.connect(self._on_server_status_clicked)
            title_bar_layout.addWidget(self.server_status_widget.status_button)

        self.settings_button = QPushButton("\ue60f")
        self.settings_button.setObjectName("LeftPanelDialogSettingsButton")
        self.settings_button.setFixedSize(32, 32)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        title_bar_layout.addWidget(self.settings_button)

        right_main_layout.addWidget(self.right_title_bar)

        self.right_work_container = QWidget()
        self.right_work_container.setObjectName("LeftPanelDialogRightWorkContainer")
        self.right_work_layout = QVBoxLayout(self.right_work_container)
        self.right_work_layout.setContentsMargins(20, 20, 20, 20)
        self.right_work_layout.setSpacing(10)
        right_main_layout.addWidget(self.right_work_container)

        content_layout.addWidget(self.right_work_area)

        # Sync QML chrome sizing.
        root_obj = self._qml_host.rootObject()
        if root_obj is not None:
            try:
                root_obj.setProperty("leftPanelWidth", 250)
                root_obj.setProperty("rightTitleBarHeight", 40)
                root_obj.setProperty("showRightTitleBar", True)
            except Exception:
                pass

        # Left: project list
        self.project_list = ProjectListWidget(self.workspace)
        while self.left_content_layout.count():
            item = self.left_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()
        self.left_content_layout.setContentsMargins(0, 0, 0, 0)
        self.left_content_layout.setSpacing(0)
        self.left_content_layout.addWidget(self.project_list, 1)

        # Right: main startup widget
        self._set_right_title("Filmeto")
        selected_project = self.project_list.get_selected_project()
        self.startup_widget = ProjectStartupWidget(self, self.workspace, selected_project)
        self.startup_widget.enter_edit_mode.connect(self._on_edit_project_from_widget)
        self._set_right_work_widget(self.startup_widget)
        self.right_work_layout.setContentsMargins(0, 0, 0, 0)

        self._connect_signals()

    def _connect_signals(self):
        self.project_list.project_selected.connect(self._on_project_selected_in_list)
        self.project_list.project_edit.connect(self.startup_widget._on_edit_project)
        self.project_list.project_created.connect(self._on_project_created_in_list)
        # settings/server are handled by the title bar buttons in this window.

    def _on_project_selected_in_list(self, project_name: str):
        self.startup_widget.set_project(project_name)
        # Keep project info panel (if loaded) in sync
        try:
            panel = self.startup_widget.right_panel_switcher.get_panel("project_info")
            if panel and hasattr(panel, "set_project"):
                panel.set_project(project_name)
        except Exception:
            pass

    def _on_project_created_in_list(self, project_name: str):
        self.startup_widget.set_project(project_name)
        try:
            panel = self.startup_widget.right_panel_switcher.get_panel("project_info")
            if panel and hasattr(panel, "set_project"):
                panel.set_project(project_name)
        except Exception:
            pass

    def _on_edit_project_from_widget(self, project_name: str):
        self.workspace.switch_project(project_name)
        self.enter_edit_mode.emit(project_name)

    def _on_settings_clicked(self):
        from app.ui.settings import SettingsWidget

        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Settings")
        settings_dialog.setMinimumSize(900, 700)
        settings_dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        layout = QVBoxLayout(settings_dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        settings_widget = SettingsWidget(self.workspace)
        layout.addWidget(settings_widget)
        settings_dialog.exec()

    def _on_server_status_clicked(self):
        from app.ui.server_status import ServerListDialog

        server_dialog = ServerListDialog(self.workspace, self)
        server_dialog.servers_modified.connect(self.refresh_projects)
        if self.server_status_widget:
            server_dialog.servers_modified.connect(self.server_status_widget.force_refresh)
        server_dialog.exec()

    def refresh_projects(self):
        self.project_list.refresh()
        selected_project = self.project_list.get_selected_project()
        if selected_project:
            self.startup_widget.set_project(selected_project)

    def get_selected_project(self) -> str:
        return self.project_list.get_selected_project()

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)

    def _set_right_title(self, title: str):
        if self.right_title_label:
            self.right_title_label.setText(title)

    def _set_right_work_widget(self, widget: QWidget):
        while self.right_work_layout.count():
            item = self.right_work_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()
        self.right_work_layout.addWidget(widget)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.drag_enabled:
            click_pos = event.position().toPoint()
            mac_buttons_rect = self.mac_control_buttons.geometry()
            if mac_buttons_rect.contains(click_pos):
                mac_buttons = self.mac_control_buttons.findChildren(QWidget)
                for button in mac_buttons:
                    button_global_pos = button.mapTo(self, QPoint(0, 0))
                    button_rect = button.geometry()
                    button_rect.moveTopLeft(button_global_pos)
                    if button_rect.contains(click_pos):
                        super().mousePressEvent(event)
                        return
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and not self.drag_position.isNull() and self.drag_enabled:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)
