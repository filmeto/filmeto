"""Widget for displaying audio content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QSlider
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from agent.chat.content import AudioContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class AudioContentWidget(BaseStructuredContentWidget):
    """Widget for displaying audio content."""

    def __init__(self, content: AudioContent, parent=None):
        """Initialize audio widget."""
        super().__init__(structure_content=content, parent=parent)
        self.is_playing = False

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(156, 39, 176, 0.1);
                border: 1px solid rgba(156, 39, 176, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(6)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        # Audio icon
        icon_label = QLabel("🎵", container)
        icon_label.setStyleSheet("font-size: 20px;")
        header_row.addWidget(icon_label)

        # Title
        title_label = QLabel("Audio Content", container)
        title_label.setStyleSheet("""
            QLabel {
                color: #9c27b0;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_row.addWidget(title_label)
        header_row.addStretch()

        # Duration if available
        if self.structure_content.duration:
            duration_min = self.structure_content.duration // 60
            duration_sec = self.structure_content.duration % 60
            duration_label = QLabel(f"{duration_min}:{duration_sec:02d}", container)
            duration_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                }
            """)
            header_row.addWidget(duration_label)

        container_layout.addLayout(header_row)

        # URL display
        if self.structure_content.url:
            url_label = QLabel(self.structure_content.url, container)
            url_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-size: 10px;
                }
            """)
            url_label.setWordWrap(True)
            url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            container_layout.addWidget(url_label)

        # Progress bar (placeholder)
        progress_slider = QSlider(Qt.Horizontal, container)
        progress_slider.setRange(0, 100)
        progress_slider.setValue(0)
        progress_slider.setStyleSheet("""
            QSlider {
                background-color: #1e1e1e;
                border: none;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background-color: #3c3c3c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                background-color: #9c27b0;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        container_layout.addWidget(progress_slider)

        # Transcript if available
        if self.structure_content.transcript:
            transcript_header = QLabel("📝 Transcript:", container)
            transcript_header.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(transcript_header)

            transcript_label = QLabel(self.structure_content.transcript, container)
            transcript_label.setWordWrap(True)
            transcript_label.setStyleSheet("""
                QLabel {
                    color: #e1e1e1;
                    font-size: 11px;
                    padding: 6px;
                    background-color: #1e1e1e;
                    border-radius: 4px;
                }
            """)
            container_layout.addWidget(transcript_label)

        # Action buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        # Play button
        if self.structure_content.url:
            self.play_button = QPushButton("▶️ Play", container)
            self.play_button.setStyleSheet("""
                QPushButton {
                    background-color: #9c27b0;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ab30c0;
                }
            """)
            self.play_button.clicked.connect(self._toggle_play)
            button_row.addWidget(self.play_button)

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

    def _toggle_play(self):
        """Toggle play/pause (opens audio in external player)."""
        if self.structure_content.url:
            self.is_playing = not self.is_playing
            if self.is_playing:
                self.play_button.setText("⏸️ Pause")
                QDesktopServices.openUrl(QUrl(self.structure_content.url))
            else:
                self.play_button.setText("▶️ Play")

    def _open_in_browser(self):
        """Open the audio URL in browser."""
        if self.structure_content.url:
            QDesktopServices.openUrl(QUrl(self.structure_content.url))

    def update_content(self, structure_content: AudioContent):
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
            "transcript": self.structure_content.transcript,
            "is_playing": self.is_playing,
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
        if "transcript" in state and hasattr(self.structure_content, 'transcript'):
            self.structure_content.transcript = state["transcript"]
        if "is_playing" in state:
            self.is_playing = state["is_playing"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
