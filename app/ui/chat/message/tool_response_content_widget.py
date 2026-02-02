"""Widget for displaying tool response content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextEdit
from PySide6.QtCore import Qt

from agent.chat.content import ToolResponseContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ToolResponseContentWidget(BaseStructuredContentWidget):
    """Widget for displaying tool response content."""

    def __init__(self, content: ToolResponseContent, parent=None):
        """Initialize tool response widget."""
        super().__init__(structure_content=content, parent=parent)

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Determine status for styling
        tool_status = self.structure_content.tool_status or "completed"
        is_error = tool_status == "failed" or self.structure_content.error is not None

        # Create container frame
        container = QFrame(self)
        if is_error:
            container.setStyleSheet("""
                QFrame {
                    background-color: rgba(244, 67, 54, 0.1);
                    border: 1px solid rgba(244, 67, 54, 0.4);
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
        else:
            container.setStyleSheet("""
                QFrame {
                    background-color: rgba(76, 175, 80, 0.1);
                    border: 1px solid rgba(76, 175, 80, 0.4);
                    border-radius: 6px;
                    padding: 8px;
                }
            """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(6)

        # Header with tool name
        tool_name = self.structure_content.tool_name or "Tool"
        status_icon = "❌" if is_error else "✅"
        header_label = QLabel(f"{status_icon} Tool Response: {tool_name}", container)
        header_label.setStyleSheet("""
            QLabel {
                color: #4caf50;
                font-size: 13px;
                font-weight: bold;
            }
        """ if not is_error else """
            QLabel {
                color: #f44336;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_label.setAlignment(Qt.AlignLeft)
        container_layout.addWidget(header_label)

        # Status indicator
        status_label = QLabel(f"Status: {tool_status}", container)
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {'#f44336' if is_error else '#4caf50'};
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
                background-color: {'#f4433620' if is_error else '#4caf5020'};
                border-radius: 3px;
            }}
        """)
        status_label.setAlignment(Qt.AlignLeft)
        container_layout.addWidget(status_label)

        # Error message if present
        if self.structure_content.error:
            error_label = QLabel("Error:", container)
            error_label.setStyleSheet("""
                QLabel {
                    color: #f44336;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(error_label)

            error_text = QLabel(self.structure_content.error, container)
            error_text.setWordWrap(True)
            error_text.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-size: 12px;
                    padding: 4px;
                    background-color: #1e1e1e;
                    border-radius: 3px;
                }
            """)
            container_layout.addWidget(error_text)

        # Result if present
        if self.structure_content.result is not None:
            result_label = QLabel("Result:", container)
            result_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(result_label)

            # Check if result is large enough for a text edit
            result_str = str(self.structure_content.result)
            if len(result_str) > 100 or '\n' in result_str:
                result_text = QTextEdit(container)
                result_text.setReadOnly(True)
                result_text.setMaximumHeight(150)
                result_text.setStyleSheet("""
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

                # Format result nicely if it's a dict/list
                import json
                try:
                    formatted_result = json.dumps(self.structure_content.result, indent=2)
                except (TypeError, ValueError):
                    formatted_result = result_str

                result_text.setPlainText(formatted_result)
                container_layout.addWidget(result_text)
            else:
                # Short result as label
                result_value = QLabel(result_str, container)
                result_value.setWordWrap(True)
                result_value.setStyleSheet("""
                    QLabel {
                        color: #e1e1e1;
                        font-size: 12px;
                        padding: 4px;
                    }
                """)
                container_layout.addWidget(result_value)

        layout.addWidget(container)

    def update_content(self, structure_content: ToolResponseContent):
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
            "result": self.structure_content.result,
            "error": self.structure_content.error,
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
        if "result" in state and hasattr(self.structure_content, 'result'):
            self.structure_content.result = state["result"]
        if "error" in state and hasattr(self.structure_content, 'error'):
            self.structure_content.error = state["error"]
        if "tool_status" in state and hasattr(self.structure_content, 'tool_status'):
            self.structure_content.tool_status = state["tool_status"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
