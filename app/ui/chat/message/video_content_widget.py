"""Widget for displaying video content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from agent.chat.content import VideoContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class VideoContentWidget(BaseStructuredContentWidget):
    """Widget for displaying video content."""

    def __init__(self, content: VideoContent, parent=None):
        """Initialize video widget."""
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
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)

        # Video placeholder
        video_placeholder = QLabel(container)
        video_placeholder.setAlignment(Qt.AlignCenter)
        video_placeholder.setMinimumSize(300, 200)
        video_placeholder.setStyleSheet("""
            QLabel {
                background-color: #252526;
                border: 2px dashed #3c3c3c;
                border-radius: 6px;
                color: #a0a0a0;
                font-size: 24px;
            }
        """)

        # Show thumbnail if available, otherwise show placeholder
        if self.structure_content.thumbnail_url:
            video_placeholder.setText(f"🎬\n🖼️ Thumbnail: {self.structure_content.thumbnail_url[:30]}...")
        else:
            video_placeholder.setText("🎬\nVideo Content")

        container_layout.addWidget(video_placeholder)

        # Duration if available
        if self.structure_content.duration:
            duration_min = self.structure_content.duration // 60
            duration_sec = self.structure_content.duration % 60
            duration_label = QLabel(f"⏱️ Duration: {duration_min}:{duration_sec:02d}", container)
            duration_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                }
            """)
            container_layout.addWidget(duration_label)

        # URL display
        if self.structure_content.url:
            url_label = QLabel(f"URL: {self.structure_content.url}", container)
            url_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-size: 10px;
                }
            """)
            url_label.setWordWrap(True)
            url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            container_layout.addWidget(url_label)

        # Action buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        # Play button
        if self.structure_content.url:
            play_button = QPushButton("▶️ Play", container)
            play_button.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5cb860;
                }
            """)
            play_button.clicked.connect(self._play_video)
            button_row.addWidget(play_button)

        # Open in browser button
        if self.structure_content.url:
            open_button = QPushButton("🔗 Open", container)
            open_button.setStyleSheet("""
                QPushButton {
                    background-color: #4a90d9;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #5aa0ff;
                }
            """)
            open_button.clicked.connect(self._open_in_browser)
            button_row.addWidget(open_button)

        button_row.addStretch()
        container_layout.addLayout(button_row)

        layout.addWidget(container)

    def _play_video(self):
        """Play the video (opens in browser/external player)."""
        if self.structure_content.url:
            QDesktopServices.openUrl(QUrl(self.structure_content.url))

    def _open_in_browser(self):
        """Open the video URL in browser."""
        if self.structure_content.url:
            QDesktopServices.openUrl(QUrl(self.structure_content.url))

    def update_content(self, structure_content: VideoContent):
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
            "thumbnail_url": self.structure_content.thumbnail_url,
            "duration": self.structure_content.duration,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "url" in state and hasattr(self.structure_content, 'url'):
            self.structure_content.url = state["url"]
        if "thumbnail_url" in state and hasattr(self.structure_content, 'thumbnail_url'):
            self.structure_content.thumbnail_url = state["thumbnail_url"]
        if "duration" in state and hasattr(self.structure_content, 'duration'):
            self.structure_content.duration = state["duration"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
