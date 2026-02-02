"""Widget for displaying link content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt

from agent.chat.content import LinkContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class LinkWidget(BaseStructuredContentWidget):
    """Widget for displaying link content."""

    def __init__(self, content: LinkContent, parent=None):
        """Initialize link widget."""
        super().__init__(structure_content=content, parent=parent)

    def _setup_ui(self):
        """Set up UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(74, 144, 217, 0.15);
                border: 1px solid rgba(74, 144, 217, 0.4);
                border-radius: 6px;
                padding: 4px;
            }
        """)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(8, 6, 8, 6)
        container_layout.setSpacing(8)

        # Link icon
        icon_label = QLabel("🔗", container)
        container_layout.addWidget(icon_label)

        # Get link info from LinkContent attributes
        url = self.structure_content.url or ""
        link_title = self.structure_content.link_title or url
        description = self.structure_content.description or ""

        # Link title label
        title_label = QLabel(link_title, container)
        title_label.setStyleSheet("""
            QLabel {
                color: #4a90d9;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        title_label.setWordWrap(True)
        container_layout.addWidget(title_label)

        # Description if available
        if description:
            desc_label = QLabel(f" - {description}", container)
            desc_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                }
            """)
            desc_label.setWordWrap(True)
            container_layout.addWidget(desc_label)

        container_layout.addStretch()

        # Open button
        open_button = QPushButton("Open", container)
        open_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5aa0ff;
            }
            QPushButton:pressed {
                background-color: #3a80c9;
            }
        """)
        open_button.clicked.connect(lambda: self._handle_link_click(url))
        container_layout.addWidget(open_button)

        layout.addWidget(container)

    def _handle_link_click(self, url: str):
        """Handle link click and emit reference clicked signal."""
        self.open_link(url)

        # Find the parent AgentMessageCard and emit the reference clicked signal
        parent = self.parent()
        while parent:
            if hasattr(parent, 'reference_clicked'):
                parent.reference_clicked.emit('link', url)
                break
            parent = parent.parent()

    def open_link(self, url: str):
        """Open the link in browser."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))

    def update_content(self, structure_content: LinkContent):
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
            "url": self.structure_content.url,
            "link_title": self.structure_content.link_title,
            "description": self.structure_content.description,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "url" in state and hasattr(self.structure_content, 'url'):
            self.structure_content.url = state["url"]
        if "link_title" in state and hasattr(self.structure_content, 'link_title'):
            self.structure_content.link_title = state["link_title"]
        if "description" in state and hasattr(self.structure_content, 'description'):
            self.structure_content.description = state["description"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
