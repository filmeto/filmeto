"""Widget for displaying button content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

from agent.chat.content import ButtonContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ButtonWidget(BaseStructuredContentWidget):
    """Widget for displaying button content."""

    def __init__(self, content: ButtonContent, parent=None):
        """Initialize button widget."""
        super().__init__(structure_content=content, parent=parent)
        self.action_button = None

    def _setup_ui(self):
        """Set up UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Get button info from ButtonContent attributes
        label = self.structure_content.label or "Button"
        action = self.structure_content.action or ""
        button_style = self.structure_content.button_style or "primary"
        disabled = self.structure_content.disabled or False

        # Determine button color based on style
        style_colors = {
            "primary": ("#4a90d9", "#5aa0ff", "#3a80c9"),
            "secondary": ("#6c757d", "#7a8690", "#5c6470"),
            "danger": ("#e74c3c", "#f05a4a", "#d63e2e"),
            "warning": ("#f39c12", "#ffa924", "#d68a0a"),
            "success": ("#27ae60", "#30be6f", "#229e52"),
        }
        bg_color, hover_color, press_color = style_colors.get(button_style, style_colors["primary"])

        # Create button
        self.action_button = QPushButton(label, self)
        self.action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {press_color};
            }}
            QPushButton:disabled {{
                background-color: #3c3c3c;
                color: #6c6c6c;
            }}
        """)
        self.action_button.setEnabled(not disabled)
        self.action_button.clicked.connect(lambda: self._handle_button_click(action, self.structure_content.payload))
        layout.addWidget(self.action_button)
        layout.addStretch()

        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

    def _handle_button_click(self, action: str, payload: Any):
        """Handle button click."""
        # Find the parent AgentMessageCard and emit the reference clicked signal
        parent = self.parent()
        while parent:
            if hasattr(parent, 'reference_clicked'):
                parent.reference_clicked.emit('button', action)
                break
            parent = parent.parent()

        print(f"Button clicked with action: {action}, payload: {payload}")

    def update_content(self, structure_content: ButtonContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content
        # Clear and re-layout the widget
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "label": self.structure_content.label,
            "action": self.structure_content.action,
            "button_style": self.structure_content.button_style,
            "disabled": self.structure_content.disabled,
            "payload": self.structure_content.payload,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "label" in state and hasattr(self.structure_content, 'label'):
            self.structure_content.label = state["label"]
        if "action" in state and hasattr(self.structure_content, 'action'):
            self.structure_content.action = state["action"]
        if "button_style" in state and hasattr(self.structure_content, 'button_style'):
            self.structure_content.button_style = state["button_style"]
        if "disabled" in state and hasattr(self.structure_content, 'disabled'):
            self.structure_content.disabled = state["disabled"]
        if "payload" in state and hasattr(self.structure_content, 'payload'):
            self.structure_content.payload = state["payload"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
