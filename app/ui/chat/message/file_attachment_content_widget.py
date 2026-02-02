"""Widget for displaying file attachment content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt

from agent.chat.content import FileAttachmentContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class FileAttachmentContentWidget(BaseStructuredContentWidget):
    """Widget for displaying file attachment content."""

    def __init__(self, content: FileAttachmentContent, parent=None):
        """Initialize file attachment widget."""
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
                background-color: rgba(96, 125, 139, 0.1);
                border: 1px solid rgba(96, 125, 139, 0.3);
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

        # File icon based on mime type
        icon = self._get_file_icon()
        icon_label = QLabel(icon, container)
        icon_label.setStyleSheet("font-size: 24px;")
        header_row.addWidget(icon_label)

        # File info column
        info_column = QVBoxLayout()
        info_column.setSpacing(2)

        # Filename
        filename = self.structure_content.filename or "Unknown File"
        filename_label = QLabel(filename, container)
        filename_label.setStyleSheet("""
            QLabel {
                color: #e1e1e1;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        filename_label.setWordWrap(True)
        info_column.addWidget(filename_label)

        # File metadata row
        metadata_row = QHBoxLayout()
        metadata_row.setSpacing(12)

        # File size
        if self.structure_content.file_size:
            size_text = self._format_file_size(self.structure_content.file_size)
            size_label = QLabel(f"📦 {size_text}", container)
            size_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 10px;
                }
            """)
            metadata_row.addWidget(size_label)

        # Mime type
        if self.structure_content.mime_type:
            mime_label = QLabel(f"📄 {self.structure_content.mime_type}", container)
            mime_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 10px;
                }
            """)
            metadata_row.addWidget(mime_label)

        metadata_row.addStretch()
        info_column.addLayout(metadata_row)
        header_row.addLayout(info_column)
        header_row.addStretch()

        container_layout.addLayout(header_row)

        # Action buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        # Download button
        download_button = QPushButton("⬇️ Download", container)
        download_button.setStyleSheet("""
            QPushButton {
                background-color: #607d8b;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #78909c;
            }
        """)
        download_button.clicked.connect(self._download_file)
        button_row.addWidget(download_button)

        # Open button (if has path)
        if self.structure_content.file_path:
            open_button = QPushButton("📂 Open", container)
            open_button.setStyleSheet("""
                QPushButton {
                    background-color: #4a90d9;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #5aa0ff;
                }
            """)
            open_button.clicked.connect(self._open_file)
            button_row.addWidget(open_button)

        button_row.addStretch()
        container_layout.addLayout(button_row)

        layout.addWidget(container)

    def _get_file_icon(self) -> str:
        """Get file icon based on mime type."""
        mime = self.structure_content.mime_type or ""
        filename = self.structure_content.filename or ""

        # Image files
        if mime.startswith("image/") or filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg")):
            return "🖼️"
        # Video files
        elif mime.startswith("video/") or filename.lower().endswith((".mp4", ".avi", ".mkv", ".mov", ".wmv")):
            return "🎬"
        # Audio files
        elif mime.startswith("audio/") or filename.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".m4a")):
            return "🎵"
        # PDF
        elif mime == "application/pdf" or filename.lower().endswith(".pdf"):
            return "📕"
        # Archive files
        elif mime in ("application/zip", "application/x-tar", "application/x-rar-compressed") or filename.lower().endswith((".zip", ".tar", ".rar", ".7z")):
            return "📦"
        # Code files
        elif filename.lower().endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs")):
            return "📜"
        # Text files
        elif mime.startswith("text/") or filename.lower().endswith((".txt", ".md", ".rst")):
            return "📄"
        # Default
        else:
            return "📎"

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _download_file(self):
        """Handle file download."""
        print(f"Download file: {self.structure_content.filename}")
        # In a real implementation, this would trigger a download

    def _open_file(self):
        """Handle file open."""
        import os
        import subprocess
        import platform

        file_path = self.structure_content.file_path
        if file_path and os.path.exists(file_path):
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            elif platform.system() == "Windows":
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(["xdg-open", file_path])

    def update_content(self, structure_content: FileAttachmentContent):
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
            "filename": self.structure_content.filename,
            "file_path": self.structure_content.file_path,
            "file_size": self.structure_content.file_size,
            "mime_type": self.structure_content.mime_type,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        for key in ["filename", "file_path", "file_size", "mime_type"]:
            if key in state and hasattr(self.structure_content, key):
                setattr(self.structure_content, key, state[key])

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
