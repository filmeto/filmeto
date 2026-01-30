"""Widget for displaying step content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextEdit
from PySide6.QtCore import Qt

from agent.chat.structure_content import StepContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class StepContentWidget(BaseStructuredContentWidget):
    """Widget for displaying step content."""

    def __init__(self, content: StepContent, parent=None):
        """Initialize step widget."""
        super().__init__(structure_content=content, parent=parent)

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Determine status for styling
        step_status = self.structure_content.step_status or "pending"
        status_colors = {
            "pending": ("#ffc107", "#ffc10720", "⭕"),
            "in_progress": ("#2196f3", "#2196f320", "🔄"),
            "completed": ("#4caf50", "#4caf5020", "✅"),
            "failed": ("#f44336", "#f4433620", "❌"),
        }
        status_color, status_bg, status_icon = status_colors.get(step_status, status_colors["pending"])

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {status_bg};
                border: 1px solid {status_color}40;
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(6)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        # Status icon
        icon_label = QLabel(status_icon, container)
        icon_label.setStyleSheet("font-size: 18px;")
        header_row.addWidget(icon_label)

        # Step number and title
        step_number = self.structure_content.step_number or 0
        description = self.structure_content.description or f"Step {step_number}"
        title_label = QLabel(f"Step {step_number}: {description}", container)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {status_color};
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        title_label.setWordWrap(True)
        header_row.addWidget(title_label)
        header_row.addStretch()

        # Status badge
        status_label = QLabel(step_status.replace("_", " ").title(), container)
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {status_color};
                font-size: 10px;
                font-weight: bold;
                padding: 2px 8px;
                background-color: {status_bg};
                border-radius: 3px;
            }}
        """)
        header_row.addWidget(status_label)

        container_layout.addLayout(header_row)

        # Estimated duration if available
        if self.structure_content.estimated_duration:
            duration_min = self.structure_content.estimated_duration // 60
            duration_sec = self.structure_content.estimated_duration % 60
            if duration_min > 0:
                duration_text = f"⏱️ Est. {duration_min}m {duration_sec}s"
            else:
                duration_text = f"⏱️ Est. {duration_sec}s"
            duration_label = QLabel(duration_text, container)
            duration_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 10px;
                }
            """)
            container_layout.addWidget(duration_label)

        # Result if available (for completed steps)
        if self.structure_content.result is not None:
            result_header = QLabel("Result:", container)
            result_header.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(result_header)

            result_str = str(self.structure_content.result)
            if len(result_str) > 200:
                # Long result - use text edit
                result_text = QTextEdit(container)
                result_text.setReadOnly(True)
                result_text.setMaximumHeight(80)
                result_text.setPlainText(result_str)
                result_text.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e1e1e;
                        color: #d4d4d4;
                        font-family: 'Consolas', 'Courier New', monospace;
                        font-size: 11px;
                        border: 1px solid #3c3c3c;
                        border-radius: 4px;
                        padding: 6px;
                    }
                """)
                container_layout.addWidget(result_text)
            else:
                # Short result - use label
                result_label = QLabel(result_str, container)
                result_label.setWordWrap(True)
                result_label.setStyleSheet("""
                    QLabel {
                        color: #e1e1e1;
                        font-size: 11px;
                        padding: 4px;
                        background-color: #1e1e1e;
                        border-radius: 3px;
                    }
                """)
                container_layout.addWidget(result_label)

        # Error if available
        if self.structure_content.error:
            error_header = QLabel("Error:", container)
            error_header.setStyleSheet("""
                QLabel {
                    color: #f44336;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(error_header)

            error_label = QLabel(self.structure_content.error, container)
            error_label.setWordWrap(True)
            error_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-size: 11px;
                    padding: 4px;
                    background-color: rgba(244, 67, 54, 0.1);
                    border-radius: 3px;
                }
            """)
            container_layout.addWidget(error_label)

        layout.addWidget(container)

    def update_content(self, structure_content: StepContent):
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
            "step_id": self.structure_content.step_id,
            "step_number": self.structure_content.step_number,
            "description": self.structure_content.description,
            "step_status": self.structure_content.step_status,
            "result": self.structure_content.result,
            "error": self.structure_content.error,
            "estimated_duration": self.structure_content.estimated_duration,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        for key in ["step_id", "step_number", "description", "step_status", "result", "error", "estimated_duration"]:
            if key in state and hasattr(self.structure_content, key):
                setattr(self.structure_content, key, state[key])

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
