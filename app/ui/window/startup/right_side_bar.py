"""
Right Side Bar for Startup Window

This module implements a right sidebar for the startup window that allows switching
between different views like members list and panels.
"""
from PySide6.QtWidgets import QPushButton, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget


class StartupWindowRightSideBar(BaseWidget):
    """Right sidebar with buttons for panel switching in startup window."""

    # Signal emitted when button is clicked (panel_name)
    button_clicked = Signal(str)

    def __init__(self, workspace: Workspace, parent):
        super(StartupWindowRightSideBar, self).__init__(workspace)
        self.setObjectName("startup_window_right_bar")
        self.parent = parent
        self.setFixedWidth(40)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 10, 0, 10)
        self.layout.setSpacing(20)

        # Map panel names to buttons for easy access
        self.button_map = {}

        # Members button
        self.members_button = QPushButton("\ue89e", self)  # User icon
        self.members_button.setFixedSize(30, 30)
        self.members_button.setCheckable(True)
        self.members_button.setToolTip("Members")  # Add tooltip for clarity
        self.members_button.clicked.connect(lambda: self._on_button_clicked('members'))
        self.layout.addWidget(self.members_button, alignment=Qt.AlignCenter)
        self.button_map['members'] = self.members_button

        # Screen Play button
        self.screenplay_button = QPushButton("\ue993", self)  # Text icon
        self.screenplay_button.setFixedSize(30, 30)
        self.screenplay_button.setCheckable(True)
        self.screenplay_button.setToolTip("Screen Play")  # Add tooltip for clarity
        self.screenplay_button.clicked.connect(lambda: self._on_button_clicked('screenplay'))
        self.layout.addWidget(self.screenplay_button, alignment=Qt.AlignCenter)
        self.button_map['screenplay'] = self.screenplay_button

        # Plan button
        self.plan_button = QPushButton("\ue8a5", self)  # Plan/Task icon
        self.plan_button.setFixedSize(30, 30)
        self.plan_button.setCheckable(True)
        self.plan_button.setToolTip("Plan Management")  # Add tooltip for clarity
        self.plan_button.clicked.connect(lambda: self._on_button_clicked('plan'))
        self.layout.addWidget(self.plan_button, alignment=Qt.AlignCenter)
        self.button_map['plan'] = self.plan_button

        self.layout.addStretch(0)

        # Track current selected button
        self.current_selected_button = None

        # Set initial selection to members
        self.set_selected_button('members', emit_signal=True)

    def _on_button_clicked(self, panel_name: str):
        """Handle button click and update selected state."""
        # Set the clicked button as checked
        self.set_selected_button(panel_name, emit_signal=True)
        # Emit signal for panel switching
        self.button_clicked.emit(panel_name)

    def set_selected_button(self, panel_name: str, emit_signal: bool = False):
        """
        Set the selected button state.

        Args:
            panel_name: Name of the panel to select
            emit_signal: Whether to emit the button clicked signal
        """
        # Uncheck previous button if exists
        if self.current_selected_button:
            self.current_selected_button.setChecked(False)

        # Check the new button
        if panel_name in self.button_map:
            button = self.button_map[panel_name]
            button.setChecked(True)
            self.current_selected_button = button

            # Emit the signal to trigger panel switching if requested
            if emit_signal:
                self.button_clicked.emit(panel_name)