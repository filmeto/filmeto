"""Widget for displaying error content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel, QFrame, QTextEdit
from PySide6.QtCore import Qt

from agent.chat.structure_content import ErrorContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ErrorContentWidget(BaseStructuredContentWidget):
    """Widget for displaying error content."""

    def __init__(self, content: ErrorContent, parent=None):
        """Initialize error widget."""
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
                background-color: rgba(244, 67, 54, 0.15);
                border: 1px solid rgba(244, 67, 54, 0.5);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(8)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        # Error icon and title
        title_row = QLabel("❌ Error", container)
        title_row.setStyleSheet("""
            QLabel {
                color: #f44336;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        title_row.setAlignment(Qt.AlignLeft)
        header_layout.addWidget(title_row)

        # Error message (main text)
        error_message = self.structure_content.error_message or "An error occurred"
        error_label = QLabel(error_message, container)
        error_label.setWordWrap(True)
        error_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 13px;
                padding: 6px;
                background-color: rgba(244, 67, 54, 0.1);
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(error_label)

        container_layout.addLayout(header_layout)

        # Error type if available
        if self.structure_content.error_type:
            type_label = QLabel(f"Type: {self.structure_content.error_type}", container)
            type_label.setStyleSheet("""
                QLabel {
                    color: #ff8a80;
                    font-size: 11px;
                    font-style: italic;
                }
            """)
            type_label.setAlignment(Qt.AlignLeft)
            container_layout.addWidget(type_label)

        # Details if available
        if self.structure_content.details:
            details_header = QLabel("Details:", container)
            details_header.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(details_header)

            details_text = QTextEdit(container)
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(100)
            details_text.setPlainText(self.structure_content.details)
            details_text.setStyleSheet("""
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
            container_layout.addWidget(details_text)

        layout.addWidget(container)

    def update_content(self, structure_content: ErrorContent):
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
            "error_message": self.structure_content.error_message,
            "error_type": self.structure_content.error_type,
            "details": self.structure_content.details,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "error_message" in state and hasattr(self.structure_content, 'error_message'):
            self.structure_content.error_message = state["error_message"]
        if "error_type" in state and hasattr(self.structure_content, 'error_type'):
            self.structure_content.error_type = state["error_type"]
        if "details" in state and hasattr(self.structure_content, 'details'):
            self.structure_content.details = state["details"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
