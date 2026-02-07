"""Widget for displaying text content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt

from agent.chat.content import TextContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class TextContentWidget(BaseStructuredContentWidget):
    """Widget for displaying text content with auto-height (no collapse)."""

    def __init__(self, content: TextContent, parent=None):
        """Initialize text content widget."""
        super().__init__(structure_content=content, parent=parent)

        # Always use simple UI with auto-height
        self._create_simple_ui()

    def _setup_ui(self):
        """Set up UI - overridden to create simple auto-height UI."""
        pass  # Will be handled by _create_simple_ui

    def _create_simple_ui(self):
        """Create simple UI with auto-height for all content."""
        # Clear any existing layout
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

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

        # Actual text content with auto-height
        text_label = QLabel(self.structure_content.text or "", self)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        text_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        text_label.setStyleSheet("""
            QLabel {
                color: #e1e1e1;
                font-size: 13px;
                padding-top: 4px;
            }
        """)
        layout.addWidget(text_label)

        self._text_label = text_label  # Store reference for updates

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

        # Update text label if it exists
        if hasattr(self, '_text_label') and self._text_label:
            self._text_label.setText(self.structure_content.text or "")
        else:
            # Recreate UI
            self._create_simple_ui()

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

        # Update UI
        if hasattr(self, '_text_label') and self._text_label:
            self._text_label.setText(self.structure_content.text or "")

    def is_expanded(self) -> bool:
        """Content is always expanded (no collapse)."""
        return True
