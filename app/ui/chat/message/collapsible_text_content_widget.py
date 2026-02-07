"""
Collapsible text content widget for displaying large text content.

This widget provides:
- Auto-height content without scrolling
- Hidden expand/collapse (always expanded)
- Clean visual design
"""

from typing import Any, Dict
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSizePolicy
)

from agent.chat.content import TextContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class CollapsibleTextContentWidget(BaseStructuredContentWidget):
    """
    Widget for displaying text content with auto-height (no collapse).

    Features:
    - Always expanded state
    - Auto-height content (no scrolling)
    - Text selection and link support
    """

    # Signals
    expandStateChanged = Signal(bool)  # Emitted when expand/collapse state changes

    def __init__(self, structure_content: TextContent, parent=None,
                 max_lines_collapsed: int = 3, auto_collapse_threshold: int = 500):
        """
        Initialize the collapsible text content widget.

        Args:
            structure_content: TextContent object with text data
            parent: Parent widget
            max_lines_collapsed: Maximum lines to show when collapsed (unused now)
            auto_collapse_threshold: Auto-collapse threshold (unused now)
        """
        # Always expanded
        self._is_expanded = True
        self._auto_collapsed = False

        # Now call parent init (which will call _setup_ui)
        super().__init__(structure_content, parent)

    def _setup_ui(self):
        """Set up the UI with auto-height and no collapse."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Title if available (show as simple label, no collapse button)
        if self.structure_content.title:
            title_label = QLabel(self.structure_content.title)
            title_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 4px 8px;
                }
            """)
            layout.addWidget(title_label)

        # Content area with auto-height
        self.content_container = QWidget()
        self.content_container.setObjectName("collapsible_content_container")
        self.content_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.content_container.setStyleSheet("""
            QWidget#collapsible_content_container {
                background-color: transparent;
                border: none;
            }
        """)

        container_layout = QVBoxLayout(self.content_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Content label - direct display without scrolling
        self.content_label = QLabel()
        self.content_label.setObjectName("collapsible_text_content")
        self.content_label.setWordWrap(True)
        content_text = self.structure_content.text or ""
        self.content_label.setText(content_text)
        self.content_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )
        self.content_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.content_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.content_label.setStyleSheet("""
            QLabel#collapsible_text_content {
                color: #e1e1e1;
                font-size: 13px;
                padding: 8px;
                background-color: transparent;
            }
        """)

        # Add content label directly to container layout
        container_layout.addWidget(self.content_label)

        # Add container to main layout
        layout.addWidget(self.content_container)

        # No expand/collapse button - always expanded

    def _get_expand_icon(self) -> str:
        """Get the expand/collapse icon character (unused now)."""
        return ""

    def _update_expand_state(self):
        """Update the expand state (always expanded)."""
        # Always show full content with auto height
        self.content_container.setMaximumHeight(16777215)  # No max height (QWIDGETSIZE_MAX)
        self.content_container.setVisible(True)

    def _toggle_expand(self):
        """Toggle disabled (always expanded)."""
        pass  # Do nothing - always expanded

    def is_expanded(self) -> bool:
        """Check if the content is expanded (always True)."""
        return True

    def set_expanded(self, expanded: bool):
        """Set the expand state (ignored - always expanded)."""
        # Always expanded, ignore this
        self._is_expanded = True

    def update_content(self, structure_content: TextContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content

        # Update content label
        content_text = self.structure_content.text or ""
        self.content_label.setText(content_text)

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
            "is_expanded": True,
            "is_auto_collapsed": False
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "text" in state:
            self.structure_content.text = state["text"]
            self.content_label.setText(state["text"])

        if "title" in state and self.structure_content.title:
            self.structure_content.title = state["title"]

        if "description" in state:
            self.structure_content.description = state["description"]

    def update_available_width(self, width: int):
        """Update the available width for content."""
        # Update maximum width of content label
        if self.content_label:
            self.content_label.setMaximumWidth(max(1, width - 20))
