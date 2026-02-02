"""Widget for displaying code blocks in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from agent.chat.content import CodeBlockContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class CodeBlockWidget(BaseStructuredContentWidget):
    """Widget for displaying code blocks."""

    def __init__(self, content: CodeBlockContent, parent=None):
        """Initialize code block widget."""
        super().__init__(structure_content=content, parent=parent)
        self.code_text = None

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header row with language label and copy button
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        # Language label
        language = self.structure_content.language or "text"
        language_label = QLabel(language, self)
        language_label.setStyleSheet("""
            QLabel {
                background-color: #3c3c3c;
                color: #a0a0a0;
                font-size: 10px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 3px;
            }
        """)
        language_label.setMaximumWidth(language_label.fontMetrics().horizontalAdvance(language) + 20)
        header_row.addWidget(language_label)

        header_row.addStretch()

        # Copy button
        copy_button = QPushButton("📋 Copy", self)
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #a0a0a0;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
                color: #e0e0e0;
            }
        """)
        copy_button.clicked.connect(self._copy_code)
        header_row.addWidget(copy_button)

        layout.addLayout(header_row)

        # Code content - use the 'code' attribute from CodeBlockContent
        self.code_text = QTextEdit(self)
        self.code_text.setReadOnly(True)
        self.code_text.setPlainText(self.structure_content.code)
        self.code_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Fira Code', 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #3c3c3c;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4c4c4c;
            }
        """)
        layout.addWidget(self.code_text)

        # Filename label if available
        if self.structure_content.filename:
            filename_label = QLabel(f"📄 {self.structure_content.filename}", self)
            filename_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-size: 11px;
                    padding-top: 4px;
                }
            """)
            layout.addWidget(filename_label)

        self.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)

    def _copy_code(self):
        """Copy the code to clipboard."""
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.structure_content.code)

        # Optionally show feedback
        if self.code_text:
            self.code_text.setStyleSheet("""
                QTextEdit {
                    background-color: #2a2a2a;
                    color: #d4d4d4;
                    font-family: 'Fira Code', 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    border: 1px solid #7c4dff;
                    border-radius: 4px;
                    padding: 8px;
                }
            """)

            # Reset style after a short delay
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self.code_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    font-family: 'Fira Code', 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    border: none;
                    border-radius: 4px;
                    padding: 8px;
                }
            """))

    def update_content(self, structure_content: CodeBlockContent):
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
            "code": self.structure_content.code,
            "language": self.structure_content.language,
            "filename": self.structure_content.filename,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "code" in state and hasattr(self.structure_content, 'code'):
            self.structure_content.code = state["code"]
        if "language" in state and hasattr(self.structure_content, 'language'):
            self.structure_content.language = state["language"]
        if "filename" in state and hasattr(self.structure_content, 'filename'):
            self.structure_content.filename = state["filename"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
