"""Widget for displaying tool call content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextEdit
from PySide6.QtCore import Qt

from agent.chat.structure_content import ToolCallContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ToolCallContentWidget(BaseStructuredContentWidget):
    """Widget for displaying tool call content."""

    def __init__(self, content: ToolCallContent, parent=None):
        """Initialize tool call widget."""
        super().__init__(structure_content=content, parent=parent)

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 193, 7, 0.1);
                border: 1px solid rgba(255, 193, 7, 0.4);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(6)

        # Header with tool name
        tool_name = self.structure_content.tool_name or "Unknown Tool"
        header_label = QLabel(f"🔧 Calling Tool: {tool_name}", container)
        header_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_label.setAlignment(Qt.AlignLeft)
        container_layout.addWidget(header_label)

        # Status indicator
        tool_status = self.structure_content.tool_status or "started"
        status_colors = {
            "started": "#ffc107",
            "running": "#2196f3",
            "completed": "#4caf50",
            "failed": "#f44336",
        }
        status_color = status_colors.get(tool_status, "#ffc107")

        status_label = QLabel(f"Status: {tool_status}", container)
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {status_color};
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
                background-color: {status_color}20;
                border-radius: 3px;
            }}
        """)
        status_label.setAlignment(Qt.AlignLeft)
        container_layout.addWidget(status_label)

        # Tool input parameters
        if self.structure_content.tool_input:
            input_label = QLabel("Parameters:", container)
            input_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(input_label)

            # Format input as JSON-like string
            input_text = QTextEdit(container)
            input_text.setReadOnly(True)
            input_text.setMaximumHeight(100)
            input_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    border: 1px solid #3c3c3c;
                    border-radius: 4px;
                    padding: 6px;
                }
            """)

            # Format the input nicely
            import json
            try:
                formatted_input = json.dumps(self.structure_content.tool_input, indent=2)
            except (TypeError, ValueError):
                formatted_input = str(self.structure_content.tool_input)

            input_text.setPlainText(formatted_input)
            container_layout.addWidget(input_text)

        layout.addWidget(container)

    def update_content(self, structure_content: ToolCallContent):
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
            "tool_name": self.structure_content.tool_name,
            "tool_input": self.structure_content.tool_input,
            "tool_status": self.structure_content.tool_status,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "tool_name" in state and hasattr(self.structure_content, 'tool_name'):
            self.structure_content.tool_name = state["tool_name"]
        if "tool_input" in state and hasattr(self.structure_content, 'tool_input'):
            self.structure_content.tool_input = state["tool_input"]
        if "tool_status" in state and hasattr(self.structure_content, 'tool_status'):
            self.structure_content.tool_status = state["tool_status"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
