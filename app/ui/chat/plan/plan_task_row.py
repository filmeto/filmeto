"""Plan task row widget for displaying a single plan task."""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt

from app.ui.components.avatar_widget import AvatarWidget
from agent.plan.plan_models import PlanTask
from utils.i18n_utils import tr

from .plan_status_icon import StatusIconWidget


class PlanTaskRow(QFrame):
    """Row widget for a single plan task."""

    def __init__(
        self,
        task: PlanTask,
        crew_member,
        status_label: str,
        status_color: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("plan_task_row")
        self.setStyleSheet("""
            QFrame#plan_task_row {
                background-color: #2b2d30;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        status_icon = StatusIconWidget(status_label, status_color, size=14, parent=self)
        top_row.addWidget(status_icon, 0, Qt.AlignVCenter)

        task_text = task.name or task.description or tr("Untitled Task")
        task_label = QLabel(task_text, self)
        task_label.setStyleSheet("color: #e1e1e1; font-size: 12px;")
        from PySide6.QtWidgets import QSizePolicy
        task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        task_label.setToolTip(task.description or task_text)
        top_row.addWidget(task_label, 1)
        layout.addLayout(top_row)

        crew_row = QHBoxLayout()
        crew_row.setContentsMargins(0, 0, 0, 0)
        crew_row.setSpacing(6)

        if crew_member:
            avatar_icon = crew_member.config.icon
            avatar_color = crew_member.config.color
            crew_name = crew_member.config.name
        else:
            avatar_icon = "A"
            avatar_color = "#5c5f66"
            crew_name = task.title or tr("Unknown")

        avatar = AvatarWidget(icon=avatar_icon, color=avatar_color, size=16, shape="rounded_rect", parent=self)
        crew_row.addWidget(avatar, 0, Qt.AlignVCenter)

        crew_label = QLabel(crew_name, self)
        crew_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        crew_row.addWidget(crew_label, 0, Qt.AlignVCenter)
        crew_row.addStretch()
        layout.addLayout(crew_row)
