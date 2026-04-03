# -*- coding: utf-8 -*-
"""
Startup Window

Independent window for startup/home mode with its own size management.
"""
import json
import os
import logging
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QSplitter,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QKeyEvent

from app.data.workspace import Workspace
from app.ui.dialog.left_panel_dialog import LeftPanelDialog
from app.ui.window.startup.project_list_widget import ProjectListWidget

logger = logging.getLogger(__name__)


class StartupWindow(LeftPanelDialog):
    """
    Independent window for startup/home mode.

    This window displays the project list and project info,
    allowing users to browse and manage projects.
    """

    enter_edit_mode = Signal(str)  # Emits project name when entering edit mode

    def __init__(self, workspace: Workspace):
        super(StartupWindow, self).__init__(
            parent=None,
            left_panel_width=250,
            workspace=workspace,
            defer_server_status=True,
        )
        self.workspace = workspace

        # Store pending prompt to be set in agent panel after entering edit mode
        self._pending_prompt = None

        # Window size storage
        self._window_sizes = {}
        self._load_window_sizes()

        self._startup_ui_ready = False
        self._pending_project_refresh = False
        self._startup_stages_cancelled = False
        self._project_list_signals_connected = False
        self.project_list = None

        self.settings_clicked.connect(self._on_settings_clicked)
        self.server_status_clicked.connect(self._on_server_status_clicked)

        self._setup_shell_layout()
        self._apply_styles()

        width, height = self._get_window_size()
        self.resize(width, height)
        self.setWindowState(Qt.WindowNoState)
        screen = self.screen().availableGeometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)

        QTimer.singleShot(0, self._startup_stage_install_project_list)
    
    def _load_window_sizes(self):
        """Load stored window sizes from file."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._window_sizes = json.load(f)
            else:
                # Default size for startup window
                self._window_sizes = {
                    "startup": {"width": 800, "height": 600}
                }
        except Exception as e:
            logger.error(f"Error loading window sizes: {e}")
            # Default sizes if loading fails
            self._window_sizes = {
                "startup": {"width": 800, "height": 600}
            }
    
    def _save_window_sizes(self):
        """Save current window size to file."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")
            
            # Load existing sizes to preserve edit window size
            existing_sizes = {}
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_sizes = json.load(f)
            
            # Update startup window size
            existing_sizes["startup"] = {
                "width": self.width(),
                "height": self.height()
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_sizes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving window sizes: {e}")
    
    def _get_window_size(self):
        """Get the stored size for startup window."""
        # Startup window now uses larger 1600x900 size
        # This ensures consistent startup experience
        return 1600, 900
    
    def closeEvent(self, event):
        """Handle close event to save current window size."""
        self._startup_stages_cancelled = True
        self._save_window_sizes()
        from PySide6.QtWidgets import QApplication

        QApplication.instance().quit()
        event.accept()

    def reject(self):
        """Handle close button click (from MacTitleBar)."""
        self._startup_stages_cancelled = True
        self._save_window_sizes()
        from PySide6.QtWidgets import QApplication

        QApplication.instance().quit()
        super().reject()

    def _clear_left_content(self):
        while self.left_content_layout.count():
            item = self.left_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()

    def _build_left_panel_shell(self) -> QWidget:
        """Mirror ProjectListWidget splitter geometry (header / list / toolbar)."""
        root = QWidget()
        root.setObjectName("startup_left_panel_shell")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)
        splitter.setObjectName("startup_left_shell_splitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet(
            "QFrame { background-color: rgba(45, 45, 48, 0.55); border-radius: 4px; }"
        )
        splitter.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background-color: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background-color: transparent; }"
        )
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(8, 8, 8, 8)
        inner_lay.setSpacing(4)
        for _ in range(5):
            row = QFrame()
            row.setFixedHeight(48)
            row.setStyleSheet(
                "QFrame { background-color: rgba(60, 63, 65, 0.45); border-radius: 6px; }"
            )
            inner_lay.addWidget(row)
        inner_lay.addStretch()
        scroll.setWidget(inner)
        splitter.addWidget(scroll)

        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(
            "QFrame { background-color: transparent; "
            "border-top: 1px solid rgba(60, 63, 65, 0.5); }"
        )
        splitter.addWidget(toolbar)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        layout.addWidget(splitter, 1)
        return root

    def _setup_shell_layout(self):
        """Shell matching final layout; heavy widgets load in later stages."""
        self._clear_left_content()
        self.left_content_layout.setContentsMargins(0, 0, 0, 0)
        self.left_content_layout.setSpacing(0)
        self.left_content_layout.addWidget(self._build_left_panel_shell(), 1)

        self.set_right_title("Filmeto")

        while self.right_work_layout.count():
            item = self.right_work_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()

        self.right_work_layout.setContentsMargins(0, 0, 0, 0)
        self.right_work_layout.setSpacing(0)

        from app.ui.window.startup.project_startup_widget import ProjectStartupWidget

        self.startup_widget = ProjectStartupWidget(
            self,
            self.workspace,
            None,
            defer_components=True,
        )
        self.startup_widget.enter_edit_mode.connect(self._on_edit_project_from_widget)
        self.set_right_work_widget(self.startup_widget)

    def _connect_project_list_signals(self):
        if self._project_list_signals_connected or self.project_list is None:
            return
        self._project_list_signals_connected = True
        self.project_list.project_selected.connect(self._on_project_selected_in_list)
        self.project_list.project_edit.connect(self.startup_widget._on_edit_project)
        self.project_list.project_created.connect(self._on_project_created_in_list)

    def _startup_stage_install_project_list(self):
        if self._startup_stages_cancelled:
            return
        self.project_list = ProjectListWidget(self.workspace, defer_projects_load=True)

        self._clear_left_content()
        self.left_content_layout.setContentsMargins(0, 0, 0, 0)
        self.left_content_layout.setSpacing(0)
        self.left_content_layout.addWidget(self.project_list, 1)

        self._connect_project_list_signals()
        QTimer.singleShot(0, self._startup_stage_load_projects)

    def _startup_stage_load_projects(self):
        if self._startup_stages_cancelled:
            return
        self.project_list.refresh()
        QTimer.singleShot(0, self._startup_stage_server_status)

    def _startup_stage_server_status(self):
        if self._startup_stages_cancelled:
            return
        self.attach_server_status_widget()
        QTimer.singleShot(0, self._startup_stage_work_area)

    def _startup_stage_work_area(self):
        if self._startup_stages_cancelled:
            return
        self.startup_widget.attach_work_area_components()
        selected = self.project_list.get_selected_project()
        if selected:
            self.startup_widget.set_project(selected)
        self._apply_styles()
        QTimer.singleShot(0, self._startup_stage_finalize)

    def _startup_stage_finalize(self):
        if self._startup_stages_cancelled:
            return
        self._startup_ui_ready = True
        if self._pending_project_refresh:
            self._pending_project_refresh = False
            self._do_refresh_projects()
    
    def _apply_styles(self):
        """Apply styles to the widget."""
        self.setStyleSheet("""
            QWidget#startup_right_container {
                background-color: #2b2b2b;
            }
            QWidget#startup_prompt_container {
                background-color: #2b2b2b;
            }
            QWidget#startup_chat_skeleton,
            QWidget#startup_panel_skeleton,
            QWidget#startup_sidebar_skeleton,
            QWidget#project_startup_widget {
                background-color: #2b2b2b;
            }
        """)
    
    def _on_project_selected_in_list(self, project_name: str):
        """Handle project selection from the list."""
        # Update the ProjectStartupWidget to show the selected project
        self.startup_widget.set_project(project_name)

    def _on_project_created_in_list(self, project_name: str):
        """Handle new project creation."""
        # Update the ProjectStartupWidget to show the new project
        self.startup_widget.set_project(project_name)

    def _on_edit_project(self, project_name: str):
        """Handle edit project request."""
        # Switch to the project and enter edit mode
        self.workspace.switch_project(project_name)
        self.enter_edit_mode.emit(project_name)
    
    def _on_edit_project_from_widget(self, project_name: str):
        """Handle edit project request from the startup widget."""
        # Switch to the project and enter edit mode
        self.workspace.switch_project(project_name)
        self.enter_edit_mode.emit(project_name)

    def _on_settings_clicked(self):
        """Handle settings button click."""
        from app.ui.settings import SettingsDialog

        settings_dialog = SettingsDialog(self.workspace, self)
        settings_dialog.exec()

    def _on_server_status_clicked(self):
        """Handle server status button click."""
        from app.ui.server_status import ServerListDialog
        from PySide6.QtCore import QCoreApplication, QEvent

        # Create and show server management dialog
        server_dialog = ServerListDialog(self.workspace, self)
        # Connect to refresh server status widget when servers are modified
        if self.server_status_widget:
            server_dialog.servers_modified.connect(self.server_status_widget.force_refresh)
        logger.info(
            "StartupWindow opening ServerListDialog parent_enabled=%s active_modal=%s",
            self.isEnabled(),
            type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
        )
        try:
            server_dialog.exec()
        finally:
            # The ServerListDialog (via CustomDialog) already handles parent window restoration.
            # We just need to ensure any pending events are processed.
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QCoreApplication.processEvents()

            active_modal = QApplication.activeModalWidget()
            if active_modal:
                top_levels = [
                    f"{type(w).__name__}(visible={w.isVisible()},enabled={w.isEnabled()},modal={w.isModal()})"
                    for w in QApplication.topLevelWidgets()
                ]
                logger.warning(
                    "StartupWindow detected lingering active_modal=%s top_levels=%s",
                    type(active_modal).__name__,
                    top_levels,
                )
            logger.info(
                "StartupWindow closed ServerListDialog parent_enabled=%s active_modal=%s focus_widget=%s",
                self.isEnabled(),
                type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
                type(QApplication.focusWidget()).__name__ if QApplication.focusWidget() else "None",
            )
            # Log modal snapshots for debugging (optional)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._log_modal_snapshot_0ms)
            QTimer.singleShot(100, self._log_modal_snapshot_100ms)
            QTimer.singleShot(500, self._log_modal_snapshot_500ms)

    def _log_modal_snapshot_0ms(self):
        self._log_modal_snapshot("0ms")

    def _log_modal_snapshot_100ms(self):
        self._log_modal_snapshot("100ms")

    def _log_modal_snapshot_500ms(self):
        self._log_modal_snapshot("500ms")

    def _log_modal_snapshot(self, tag: str):
        try:
            active_modal = QApplication.activeModalWidget()
            active_window = QApplication.activeWindow()
            focus_widget = QApplication.focusWidget()
            top_levels = [
                f"{type(w).__name__}(visible={w.isVisible()},enabled={w.isEnabled()},modal={w.isModal()},obj={w.objectName()})"
                for w in QApplication.topLevelWidgets()
            ]
            logger.info(
                "StartupWindow modal snapshot %s active_modal=%s active_window=%s focus_widget=%s top_levels=%s",
                tag,
                type(active_modal).__name__ if active_modal else "None",
                type(active_window).__name__ if active_window else "None",
                type(focus_widget).__name__ if focus_widget else "None",
                top_levels,
            )
        except Exception as e:
            logger.debug(f"StartupWindow modal snapshot failed ({tag}): {e}")
    
    def refresh_projects(self):
        """Refresh the project list."""
        if not self._startup_ui_ready:
            self._pending_project_refresh = True
            return
        self._do_refresh_projects()

    def _do_refresh_projects(self):
        self.project_list.refresh()
        selected_project = self.project_list.get_selected_project()
        if selected_project:
            self.startup_widget.set_project(selected_project)

    def get_selected_project(self) -> str:
        """Get the currently selected project name."""
        if self.project_list is None:
            return ""
        name = self.project_list.get_selected_project()
        return name or ""
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts."""
        # Let the startup widget handle its own keyboard events
        super().keyPressEvent(event)

