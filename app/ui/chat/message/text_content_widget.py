"""Widget for displaying text content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from agent.chat.structure_content import TextContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class TextContentWidget(BaseStructuredContentWidget):
    """Widget for displaying text content."""

    def __init__(self, content: TextContent, parent=None):
        """Initialize text content widget."""
        super().__init__(structure_content=content, parent=parent)

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Title if available
        if self.structure_content.title:
            title_label = QLabel(self.structure_content.title, self)
            title_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            layout.addWidget(title_label)

        # Description if available
        if self.structure_content.description:
            desc_label = QLabel(self.structure_content.description, self)
            desc_label.setStyleSheet("""
                QLabel {
                    color: #aaaaaa;
                    font-size: 11px;
                }
            """)
            layout.addWidget(desc_label)

        # Actual text content - use the 'text' attribute from TextContent
        text_label = QLabel(self.structure_content.text, self)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_label.setStyleSheet("""
            QLabel {
                color: #e1e1e1;
                font-size: 13px;
                padding-top: 4px;
            }
        """)
        layout.addWidget(text_label)

        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

    def update_content(self, structure_content: TextContent):
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
            "title": self.structure_content.title,
            "description": self.structure_content.description,
            "text": self.structure_content.text,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        title = state.get("title", "")
        description = state.get("description", "")
        text = state.get("text", "")

        # Update the structure content
        if hasattr(self.structure_content, 'title'):
            self.structure_content.title = title
        if hasattr(self.structure_content, 'description'):
            self.structure_content.description = description
        if hasattr(self.structure_content, 'text'):
            self.structure_content.text = text

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
