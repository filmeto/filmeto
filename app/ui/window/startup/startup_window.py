# -*- coding: utf-8 -*-
"""
Startup Window

Independent window for startup/home mode with its own size management.
Uses LeftPanelDialog layout: QML project list (left), ProjectStartupWidget (right).
"""
import json
import logging
import os

from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from app.data.workspace import Workspace
from app.ui.dialog.left_panel_dialog import LeftPanelDialog
from app.ui.window.startup.project_list_widget import ProjectListWidget
from app.ui.window.startup.project_startup_widget import ProjectStartupWidget

logger = logging.getLogger(__name__)


class StartupWindow(LeftPanelDialog):
    """
    Independent window for startup/home mode.

    This window displays the project list and project info,
    allowing users to browse and manage projects.
    """

    enter_edit_mode = Signal(str)  # Emits project name when entering edit mode

    def __init__(self, workspace: Workspace):
        super().__init__(parent=None, left_panel_width=250, workspace=workspace)
        self.workspace = workspace

        self._pending_prompt = None
        self._pending_startup_target = None

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

        self.set_right_title("Filmeto")

        selected_project = self.project_list.get_selected_project()
        self.startup_widget = ProjectStartupWidget(self, self.workspace, selected_project)
        self.startup_widget.enter_edit_mode.connect(self._on_edit_project_from_widget)

        self.set_right_work_widget(self.startup_widget)
        self.right_work_layout.setContentsMargins(0, 0, 0, 0)

        self._connect_signals()

    def _connect_signals(self):
        self.project_list.project_selected.connect(self._on_project_selected_in_list)
        self.project_list.project_edit.connect(self.startup_widget._on_edit_project)
        self.project_list.project_created.connect(self._on_project_created_in_list)
        self.settings_clicked.connect(self._on_settings_clicked)
        self.server_status_clicked.connect(self._on_server_status_clicked)

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
