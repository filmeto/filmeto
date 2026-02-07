"""Widget for displaying plan content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget
from PySide6.QtCore import Qt

from agent.chat.content import PlanContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class PlanContentWidget(BaseStructuredContentWidget):
    """
    Widget for displaying plan content.

    Uses text-based progress display instead of progress bar for better performance.
    """

    def __init__(self, content: PlanContent, parent=None):
        """Initialize plan widget."""
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
                background-color: rgba(63, 81, 181, 0.1);
                border: 1px solid rgba(63, 81, 181, 0.3);
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

        icon_label = QLabel("📋", container)
        icon_label.setStyleSheet("font-size: 18px;")
        header_row.addWidget(icon_label)

        # Title
        plan_title = self.structure_content.plan_title or "Execution Plan"
        title_label = QLabel(plan_title, container)
        title_label.setStyleSheet("""
            QLabel {
                color: #3f51b5;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_row.addWidget(title_label)
        header_row.addStretch()

        # Status badge
        plan_status = self.structure_content.plan_status or "pending"
        status_colors = {
            "pending": ("#ffc107", "#ffc10720"),
            "in_progress": ("#2196f3", "#2196f320"),
            "completed": ("#4caf50", "#4caf5020"),
            "failed": ("#f44336", "#f4433620"),
        }
        status_color, status_bg = status_colors.get(plan_status, status_colors["pending"])
        status_label = QLabel(plan_status.replace("_", " ").title(), container)
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

        # Progress - text-based instead of progress bar
        current_step = self.structure_content.current_step or 0
        total_steps = self.structure_content.total_steps or 0
        if total_steps > 0:
            progress_percent = int((current_step / total_steps) * 100)
        else:
            progress_percent = 0

        # Text-based progress display
        progress_text = f"📊 Progress: {current_step}/{total_steps} steps ({progress_percent}%)"
        progress_label = QLabel(progress_text, container)
        progress_label.setStyleSheet("""
            QLabel {
                color: #3f51b5;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 8px;
                background-color: rgba(63, 81, 181, 0.1);
                border-radius: 4px;
            }
        """)
        progress_label.setAlignment(Qt.AlignLeft)
        container_layout.addWidget(progress_label)

        # Steps list
        steps = self.structure_content.steps or []
        if steps:
            steps_label = QLabel("Steps:", container)
            steps_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: bold;
                    margin-top: 4px;
                }
            """)
            container_layout.addWidget(steps_label)

            # Create steps widget directly without scroll area
            steps_widget = QWidget()
            steps_layout = QVBoxLayout(steps_widget)
            steps_layout.setContentsMargins(4, 4, 4, 4)
            steps_layout.setSpacing(4)

            for idx, step in enumerate(steps):
                step_num = step.get("step_number", idx + 1)
                step_desc = step.get("description", f"Step {step_num}")
                step_status = step.get("status", "pending")

                # Determine icon based on status
                status_icons = {
                    "pending": "⭕",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                }
                icon = status_icons.get(step_status, "⭕")

                step_label = QLabel(f"{icon} {step_num}. {step_desc}", steps_widget)
                step_label.setStyleSheet(f"""
                    QLabel {{
                        color: {"#4caf50" if step_status == "completed" else "#e1e1e1"};
                        font-size: 11px;
                        padding: 3px 6px;
                    }}
                """)
                step_label.setWordWrap(True)
                steps_layout.addWidget(step_label)

            # Add steps widget directly to container layout
            container_layout.addWidget(steps_widget)

        layout.addWidget(container)

    def update_content(self, structure_content: PlanContent):
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
            "plan_id": self.structure_content.plan_id,
            "plan_title": self.structure_content.plan_title,
            "steps": self.structure_content.steps,
            "current_step": self.structure_content.current_step,
            "total_steps": self.structure_content.total_steps,
            "plan_status": self.structure_content.plan_status,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        for key in ["plan_id", "plan_title", "steps", "current_step", "total_steps", "plan_status"]:
            if key in state and hasattr(self.structure_content, key):
                setattr(self.structure_content, key, state[key])

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
