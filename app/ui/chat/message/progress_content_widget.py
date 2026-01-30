"""Widget for displaying progress content in chat messages."""

from typing import Any, Dict, Union
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar
from PySide6.QtCore import Qt

from agent.chat.structure_content import ProgressContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ProgressContentWidget(BaseStructuredContentWidget):
    """Widget for displaying progress content."""

    def __init__(self, content: ProgressContent, parent=None):
        """Initialize progress widget."""
        super().__init__(structure_content=content, parent=parent)
        self.progress_bar = None
        self.status_label = None

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(33, 150, 243, 0.1);
                border: 1px solid rgba(33, 150, 243, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(6)

        # Tool name or progress label
        progress_text = self.structure_content.progress or ""
        if isinstance(progress_text, (int, float)):
            progress_text = f"Progress: {progress_text}%"

        self.status_label = QLabel(progress_text, container)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #e1e1e1;
                font-size: 12px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setWordWrap(True)
        container_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar(container)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2196f3;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #2196f3;
                border-radius: 3px;
            }
        """)

        # Set progress value
        percentage = self.structure_content.percentage
        if percentage is not None:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"%p%")
        else:
            # Indeterminate progress
            self.progress_bar.setRange(0, 0)

        container_layout.addWidget(self.progress_bar)

        # Percentage text label
        if percentage is not None:
            percent_label = QLabel(f"{percentage}% complete", container)
            percent_label.setStyleSheet("""
                QLabel {
                    color: #2196f3;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            percent_label.setAlignment(Qt.AlignRight)
            container_layout.addWidget(percent_label)

        layout.addWidget(container)

    def update_content(self, structure_content: ProgressContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content

        # Update status text
        if self.status_label:
            progress_text = self.structure_content.progress or ""
            if isinstance(progress_text, (int, float)):
                progress_text = f"Progress: {progress_text}%"
            self.status_label.setText(progress_text)

        # Update progress bar
        if self.progress_bar:
            percentage = self.structure_content.percentage
            if percentage is not None:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(percentage)
            else:
                self.progress_bar.setRange(0, 0)  # Indeterminate

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "progress": self.structure_content.progress,
            "percentage": self.structure_content.percentage,
            "tool_name": self.structure_content.tool_name,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "progress" in state and hasattr(self.structure_content, 'progress'):
            self.structure_content.progress = state["progress"]
        if "percentage" in state and hasattr(self.structure_content, 'percentage'):
            self.structure_content.percentage = state["percentage"]
        if "tool_name" in state and hasattr(self.structure_content, 'tool_name'):
            self.structure_content.tool_name = state["tool_name"]

        # Update UI without rebuilding
        self.update_content(self.structure_content)
