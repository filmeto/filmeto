"""Widget for displaying image content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QPixmap, QDesktopServices

from agent.chat.content import ImageContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ImageContentWidget(BaseStructuredContentWidget):
    """Widget for displaying image content."""

    def __init__(self, content: ImageContent, parent=None):
        """Initialize image widget."""
        super().__init__(structure_content=content, parent=parent)
        self.image_label = None
        self.loaded_pixmap = None

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)

        # Alt text as title if available
        if self.structure_content.alt_text:
            alt_label = QLabel(self.structure_content.alt_text, container)
            alt_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-style: italic;
                }
            """)
            alt_label.setAlignment(Qt.AlignLeft)
            alt_label.setWordWrap(True)
            container_layout.addWidget(alt_label)

        # Image display
        self.image_label = QLabel(container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        self.image_label.setMinimumSize(200, 150)
        self.image_label.setMaximumSize(600, 400)

        # Try to load the image
        self._load_image()
        container_layout.addWidget(self.image_label)

        # Action buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        # Open in browser button (if URL)
        if self.structure_content.url:
            open_button = QPushButton("🔗 Open", container)
            open_button.setStyleSheet("""
                QPushButton {
                    background-color: #4a90d9;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #5aa0ff;
                }
            """)
            open_button.clicked.connect(self._open_in_browser)
            button_row.addWidget(open_button)

        # Download/save button
        save_button = QPushButton("💾 Save", container)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #5aa0ff;
            }
        """)
        save_button.clicked.connect(self._save_image)
        button_row.addWidget(save_button)

        button_row.addStretch()
        container_layout.addLayout(button_row)

        layout.addWidget(container)

    def _load_image(self):
        """Load the image from URL or display placeholder."""
        url = self.structure_content.url
        if url:
            # For now, show a placeholder with the URL
            # In a real implementation, you'd use QNetworkAccessManager to download
            self.image_label.setText(f"🖼️ Image\n{url[:50]}..." if len(url) > 50 else f"🖼️ Image\n{url}")
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #252526;
                    color: #a0a0a0;
                    border: 1px solid #3c3c3c;
                    border-radius: 4px;
                    font-size: 11px;
                }
            """)
        else:
            self.image_label.setText("🖼️ No Image URL")

    def _open_in_browser(self):
        """Open the image URL in browser."""
        if self.structure_content.url:
            QDesktopServices.openUrl(QUrl(self.structure_content.url))

    def _save_image(self):
        """Save the image to disk."""
        # Placeholder for save functionality
        print(f"Save image: {self.structure_content.url}")

    def update_content(self, structure_content: ImageContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content
        self._load_image()

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "url": self.structure_content.url,
            "alt_text": self.structure_content.alt_text,
            "width": self.structure_content.width,
            "height": self.structure_content.height,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "url" in state and hasattr(self.structure_content, 'url'):
            self.structure_content.url = state["url"]
        if "alt_text" in state and hasattr(self.structure_content, 'alt_text'):
            self.structure_content.alt_text = state["alt_text"]
        if "width" in state and hasattr(self.structure_content, 'width'):
            self.structure_content.width = state["width"]
        if "height" in state and hasattr(self.structure_content, 'height'):
            self.structure_content.height = state["height"]

        # Reload image
        self._load_image()
