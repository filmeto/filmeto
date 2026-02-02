"""Widget for displaying text content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from agent.chat.content import TextContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


# Threshold for using collapsible widget (characters)
COLLAPSE_THRESHOLD = 300


class TextContentWidget(BaseStructuredContentWidget):
    """Widget for displaying text content."""

    def __init__(self, content: TextContent, parent=None):
        """Initialize text content widget."""
        super().__init__(structure_content=content, parent=parent)

        # Determine if we need collapsible widget
        text = self.structure_content.text or ""
        self._use_collapsible = len(text) > COLLAPSE_THRESHOLD

        # Remove default UI and create appropriate one
        self._create_appropriate_ui()

    def _setup_ui(self):
        """Set up UI - overridden to create appropriate UI based on content length."""
        pass  # Will be handled by _create_appropriate_ui

    def _create_appropriate_ui(self):
        """Create the appropriate UI based on content length."""
        # Clear any existing layout
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        if self._use_collapsible:
            # Use collapsible widget for long content
            from app.ui.chat.message.collapsible_text_content_widget import CollapsibleTextContentWidget
            self.collapsible_widget = CollapsibleTextContentWidget(
                self.structure_content,
                self,
                max_lines_collapsed=3,
                auto_collapse_threshold=COLLAPSE_THRESHOLD
            )
            layout.addWidget(self.collapsible_widget)

            # Connect to expand state changes
            if hasattr(self.collapsible_widget, 'expandStateChanged'):
                self.collapsible_widget.expandStateChanged.connect(self._on_expand_changed)

        else:
            # Simple widget for short content
            self._create_simple_ui(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

    def _create_simple_ui(self, layout):
        """Create simple UI for short content."""
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

        # Actual text content
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

    def _on_expand_changed(self, is_expanded: bool):
        """Handle expand state change from collapsible widget."""
        # Could emit custom signal or update parent about size change
        if self.parent():
            # Notify parent about potential size change
            self.updateGeometry()

    def update_content(self, structure_content: TextContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        old_text = self.structure_content.text or ""
        new_text = structure_content.text or ""

        self.structure_content = structure_content

        # Check if we need to switch between simple and collapsible UI
        was_collapsible = self._use_collapsible
        should_be_collapsible = len(new_text) > COLLAPSE_THRESHOLD

        if was_collapsible != should_be_collapsible:
            # Need to recreate UI
            self._use_collapsible = should_be_collapsible
            self._create_appropriate_ui()
        elif self._use_collapsible and hasattr(self, 'collapsible_widget'):
            # Update existing collapsible widget
            self.collapsible_widget.update_content(structure_content)
        else:
            # Update simple UI
            # Rebuild the simple UI
            if self.layout():
                while self.layout().count():
                    item = self.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            self._create_simple_ui(self.layout())

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        base_state = {
            "title": self.structure_content.title,
            "description": self.structure_content.description,
            "text": self.structure_content.text,
        }

        if self._use_collapsible and hasattr(self, 'collapsible_widget'):
            base_state.update({
                "is_expanded": self.collapsible_widget.is_expanded(),
                "is_auto_collapsed": self.collapsible_widget._auto_collapsed
            })

        return base_state

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
        if self._use_collapsible and hasattr(self, 'collapsible_widget'):
            self.collapsible_widget.update_content(self.structure_content)
            if "is_expanded" in state:
                self.collapsible_widget.set_expanded(state["is_expanded"])
        else:
            # Rebuild simple UI
            if self.layout():
                while self.layout().count():
                    item = self.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            self._create_simple_ui(self.layout())

    def set_expanded(self, expanded: bool):
        """
        Set the expand state (only works if using collapsible widget).

        Args:
            expanded: True to expand, False to collapse
        """
        if self._use_collapsible and hasattr(self, 'collapsible_widget'):
            self.collapsible_widget.set_expanded(expanded)

    def is_expanded(self) -> bool:
        """Check if content is expanded (only works if using collapsible widget)."""
        if self._use_collapsible and hasattr(self, 'collapsible_widget'):
            return self.collapsible_widget.is_expanded()
        return True  # Simple content is always "expanded"
