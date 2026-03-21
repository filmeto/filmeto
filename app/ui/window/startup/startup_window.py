# -*- coding: utf-8 -*-
"""
Startup Window

Independent window for startup/home mode with its own size management.
"""
import json
import os
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from app.data.workspace import Workspace
from app.ui.dialog.left_panel_dialog import LeftPanelDialog
from app.ui.window.startup.project_list_widget import ProjectListWidget
from app.ui.window.startup.project_info_widget import ProjectInfoWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget

logger = logging.getLogger(__name__)


class StartupWindow(LeftPanelDialog):
    """
    Independent window for startup/home mode.

    This window displays the project list and project info,
    allowing users to browse and manage projects.
    """

    enter_edit_mode = Signal(str)  # Emits project name when entering edit mode

    def __init__(self, workspace: Workspace):
        super(StartupWindow, self).__init__(parent=None, left_panel_width=250, workspace=workspace)
        self.workspace = workspace
        
        # Store pending prompt to be set in agent panel after entering edit mode
        self._pending_prompt = None
        
        # Window size storage
        self._window_sizes = {}
        self._load_window_sizes()
        
        # Set up the UI
        self._setup_ui()
        
        # Set initial window size (ensure not maximized)
        width, height = self._get_window_size()
        self.resize(width, height)
        
        # Ensure window is in normal state (not maximized)
        self.setWindowState(Qt.WindowNoState)
        
        # Center the window on screen
        screen = self.screen().availableGeometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)
    
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
        self._save_window_sizes()
        # Closing startup window should close the application
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
        event.accept()
    
    def _setup_ui(self):
        """Set up the UI with left panel and right work area."""
        # Left panel: Project list with header, scrollable list, and toolbar
        # The ProjectListWidget already has the correct layout structure:
        # - Header (top, fixed)
        # - Scrollable project list (middle, stretches)
        # - Toolbar (bottom, fixed)
        self.project_list = ProjectListWidget(self.workspace)

        # Clear the default left content layout and set up proper layout
        # Remove the default margins and spacing to let ProjectListWidget control its own layout
        while self.left_content_layout.count():
            item = self.left_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()

        # Set margins to 0 so ProjectListWidget fills the entire left panel
        self.left_content_layout.setContentsMargins(0, 0, 0, 0)
        self.left_content_layout.setSpacing(0)

        # Add project list widget, it will stretch vertically
        self.left_content_layout.addWidget(self.project_list, 1)

        # Set right title bar text
        self.set_right_title("Filmeto")

        # Right work area: Using ProjectStartupWidget which contains the tab functionality
        from app.ui.window.startup.project_startup_widget import ProjectStartupWidget
        # Initialize with the selected project from the project list
        selected_project = self.project_list.get_selected_project()
        self.startup_widget = ProjectStartupWidget(self, self.workspace, selected_project)

        # Connect the enter_edit_mode signal from the startup widget
        self.startup_widget.enter_edit_mode.connect(self._on_edit_project_from_widget)

        # Set the right work widget and adjust margins to 0 on the right
        self.set_right_work_widget(self.startup_widget)
        # Adjust the right work layout margins to have no margins
        self.right_work_layout.setContentsMargins(0, 0, 0, 0)  # Left, Top, Right, Bottom

        # Connect signals
        self._connect_signals()

        # Apply styles
        self._apply_styles()
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Project selection changes - update the ProjectStartupWidget to show the selected project
        self.project_list.project_selected.connect(self._on_project_selected_in_list)

        # Edit project (from list) - these will now be handled by the ProjectStartupWidget
        self.project_list.project_edit.connect(self.startup_widget._on_edit_project)

        # New project created - update the ProjectStartupWidget
        self.project_list.project_created.connect(self._on_project_created_in_list)

        # Settings button click
        self.settings_clicked.connect(self._on_settings_clicked)

        # Server status button click
        self.server_status_clicked.connect(self._on_server_status_clicked)
    
    def _apply_styles(self):
        """Apply styles to the widget."""
        self.setStyleSheet("""
            QWidget#startup_right_container {
                background-color: #2b2b2b;
            }
            QWidget#startup_prompt_container {
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
        from app.ui.settings import SettingsWidget

        # Create settings dialog
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Settings")
        settings_dialog.setMinimumSize(900, 700)
        settings_dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        # Create layout
        layout = QVBoxLayout(settings_dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create settings widget
        settings_widget = SettingsWidget(self.workspace)
        layout.addWidget(settings_widget)

        # Show dialog
        settings_dialog.exec()

    def _on_server_status_clicked(self):
        """Handle server status button click."""
        from app.ui.server_status import ServerListDialog

        # Create and show server management dialog
        server_dialog = ServerListDialog(self.workspace, self)
        # Connect to refresh server status widget when servers are modified
        if self.server_status_widget:
            server_dialog.servers_modified.connect(self.server_status_widget.force_refresh)
        server_dialog.exec()
    
    def refresh_projects(self):
        """Refresh the project list."""
        # Refresh the project list in the left panel
        self.project_list.refresh()

        # Also refresh the project info in the startup widget
        selected_project = self.project_list.get_selected_project()
        if selected_project:
            self.startup_widget.set_project(selected_project)

    def get_selected_project(self) -> str:
        """Get the currently selected project name."""
        # Get the selected project from the project list
        return self.project_list.get_selected_project()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts."""
        # Let the startup widget handle its own keyboard events
        super().keyPressEvent(event)

