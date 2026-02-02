"""Widget for displaying task list content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem, QCheckBox
from PySide6.QtCore import Qt

from agent.chat.content import TaskListContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class TaskListContentWidget(BaseStructuredContentWidget):
    """Widget for displaying task list content."""

    def __init__(self, content: TaskListContent, parent=None):
        """Initialize task list widget."""
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
                background-color: rgba(0, 150, 136, 0.1);
                border: 1px solid rgba(0, 150, 136, 0.3);
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

        icon_label = QLabel("✓", container)
        icon_label.setStyleSheet("font-size: 20px; color: #009688;")
        header_row.addWidget(icon_label)

        # Title
        list_title = self.structure_content.list_title or "Task List"
        title_label = QLabel(list_title, container)
        title_label.setStyleSheet("""
            QLabel {
                color: #009688;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_row.addWidget(title_label)
        header_row.addStretch()

        # Progress badge
        completed = self.structure_content.completed_count or 0
        total = self.structure_content.total_count or 0
        if total > 0:
            progress_percent = int((completed / total) * 100)
        else:
            progress_percent = 0

        progress_label = QLabel(f"{completed}/{total} ({progress_percent}%)", container)
        progress_label.setStyleSheet("""
            QLabel {
                color: #009688;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                background-color: rgba(0, 150, 136, 0.2);
                border-radius: 3px;
            }
        """)
        header_row.addWidget(progress_label)

        container_layout.addLayout(header_row)

        # Tasks list
        tasks = self.structure_content.tasks or []
        if tasks:
            for task in tasks:
                task_row = QHBoxLayout()
                task_row.setSpacing(8)

                # Checkbox
                is_checked = task.get("completed", False)
                checkbox = QCheckBox(container)
                checkbox.setChecked(is_checked)
                checkbox.setEnabled(False)  # Read-only
                checkbox.setStyleSheet(f"""
                    QCheckBox {{
                        color: {"#009688" if is_checked else "#a0a0a0"};
                    }}
                    QCheckBox::indicator {{
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid {"#009688" if is_checked else "#3c3c3c"};
                        background-color: {"#009688" if is_checked else "transparent"};
                    }}
                """)
                task_row.addWidget(checkbox)

                # Task text
                task_text = task.get("text", task.get("description", ""))
                task_label = QLabel(task_text, container)
                task_label.setWordWrap(True)
                task_label.setStyleSheet(f"""
                    QLabel {{
                        color: {"#009688" if is_checked else "#e1e1e1"};
                        font-size: 12px;
                        {"text-decoration: line-through;" if is_checked else ""}
                    }}
                """)
                task_row.addWidget(task_label, 1)

                container_layout.addLayout(task_row)
        else:
            # No tasks message
            no_tasks_label = QLabel("No tasks in this list", container)
            no_tasks_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-style: italic;
                }
            """)
            container_layout.addWidget(no_tasks_label)

        layout.addWidget(container)

    def update_content(self, structure_content: TaskListContent):
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
            "tasks": self.structure_content.tasks,
            "completed_count": self.structure_content.completed_count,
            "total_count": self.structure_content.total_count,
            "list_title": self.structure_content.list_title,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        for key in ["tasks", "completed_count", "total_count", "list_title"]:
            if key in state and hasattr(self.structure_content, key):
                setattr(self.structure_content, key, state[key])

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
