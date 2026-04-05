# -*- coding: utf-8 -*-
"""
Edit Window

Independent window for edit mode with its own size management.
"""
import json
import os
import logging
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QKeyEvent

from app.data.workspace import Workspace
from .edit_widget import EditWidget

logger = logging.getLogger(__name__)


class EditWindow(QMainWindow):
    """
    Independent window for edit mode.

    This window displays the project editing interface with timeline,
    canvas, and all editing tools.
    """

    go_home = Signal()  # Emitted when home button is clicked
    about_to_close = Signal()  # Emitted when window is about to close

    def __init__(self, workspace: Workspace, lazy_init: bool = False):
        super(EditWindow, self).__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.workspace = workspace
        self.project = workspace.get_project()
        self._lazy_init = lazy_init

        # Set main window reference to workspace for access to preview components
        self.workspace._main_window = self

        # Window size storage
        self._window_sizes = {}
        self._load_window_sizes()

        self._setup_ui()

        # Set initial window size (fullscreen/maximized)
        self.showMaximized()

    def _complete_lazy_init(self):
        """Progressively replace shell regions with real widgets (after first paint)."""
        if self._lazy_init and self.edit_widget:
            self.edit_widget.run_staged_load()

    def _load_window_sizes(self):
        """Load stored window sizes from file."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")

            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    self._window_sizes = json.load(f)
            else:
                # Default size for edit window
                self._window_sizes = {
                    "edit": {"width": 1600, "height": 900}
                }
        except Exception as e:
            logger.error(f"Error loading window sizes: {e}")
            # Default sizes if loading fails
            self._window_sizes = {
                "edit": {"width": 1600, "height": 900}
            }

    def _save_window_sizes(self):
        """Save current window size to file."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")

            # Load existing sizes to preserve startup window size
            existing_sizes = {}
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    existing_sizes = json.load(f)

            # Update edit window size
            existing_sizes["edit"] = {
                "width": self.width(),
                "height": self.height()
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(existing_sizes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving window sizes: {e}")

    def closeEvent(self, event):
        """Handle close event to save current window size."""
        self._save_window_sizes()
        # Emit signal before closing
        self.about_to_close.emit()
        # Clear workspace reference
        if hasattr(self.workspace, "_main_window") and self.workspace._main_window == self:
            self.workspace._main_window = None
        event.accept()

    def _setup_ui(self):
        """Full edit UI, or shell + staged attach when lazy_init."""
        central_widget = QWidget()
        central_widget.setObjectName("edit_window")

        layout = QVBoxLayout()
        layout.setObjectName("edit_window_layout")
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._lazy_init:
            self.edit_widget = EditWidget(
                self, self.workspace, defer_parts=True
            )
        else:
            self.edit_widget = EditWidget(
                self, self.workspace, defer_parts=False
            )
        self.edit_widget.go_home.connect(self.go_home.emit)
        layout.addWidget(self.edit_widget)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def get_workspace(self):
        """Get the workspace instance."""
        return self.workspace

    def get_project(self):
        """Get the current project instance."""
        return self.project

    # Properties for backward compatibility
    @property
    def top_bar(self):
        """Get the top bar (only available in edit mode)."""
        if self.edit_widget:
            return self.edit_widget.get_top_bar()
        return None

    @property
    def bottom_bar(self):
        """Get the bottom bar (only available in edit mode)."""
        if self.edit_widget:
            return self.edit_widget.get_bottom_bar()
        return None

    @property
    def h_layout(self):
        """Get the h_layout (only available in edit mode)."""
        if self.edit_widget:
            return self.edit_widget.get_h_layout()
        return None

    def keyPressEvent(self, event: QKeyEvent):
        """
        Handle global keyboard shortcuts.
        Spacebar toggles play/pause unless a text input is focused.
        """
        if event.key() == Qt.Key_Space:
            # Check if focus is on a text input widget
            focused_widget = self.focusWidget()

            # If focused widget is a text input, let it handle the spacebar
            if isinstance(focused_widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
                super().keyPressEvent(event)
                return

            # Handle spacebar in edit mode with bottom bar available
            if self.bottom_bar:
                # Toggle play/pause
                play_control = self.bottom_bar.play_control
                play_control.set_playing(not play_control.is_playing())
                event.accept()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
