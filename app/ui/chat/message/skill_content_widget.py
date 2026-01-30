"""
Skill content widget for displaying skill execution status.

This module provides a widget for displaying skill execution with support for
different states: start, progress, and end.
"""
from typing import Any, Dict

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget
from agent.chat.structure_content import SkillContent


class SkillContentWidget(BaseStructuredContentWidget):
    """
    Widget for displaying skill execution status with different states.

    Supports start, progress, and end states for skill execution.
    Uses text-based progress display instead of progress bar for better performance.
    """

    def __init__(self, structure_content: SkillContent, parent=None, available_width=None):
        """
        Initialize the skill content widget.

        Args:
            structure_content: The structure content to display
            parent: Parent widget
            available_width: Available width from parent container
        """
        super().__init__(structure_content, parent)
        self.available_width = available_width
        self.status = "starting"  # Track status separately
        self.status_message = ""
        self.result = ""

    def _setup_ui(self):
        """Set up the UI components."""
        self.setObjectName("skill_content_widget")

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        # Container frame
        self.container_frame = QFrame()
        self.container_frame.setObjectName("skill_container_frame")
        self.container_frame.setStyleSheet("""
            QFrame#skill_container_frame {
                border: 1px solid #4a90e2;
                border-radius: 6px;
                background-color: #2d2d2d;
            }
        """)

        # Frame layout
        self.frame_layout = QVBoxLayout(self.container_frame)
        self.frame_layout.setContentsMargins(10, 10, 10, 10)
        self.frame_layout.setSpacing(6)

        # Title label - use skill_name from SkillContent
        self.title_label = QLabel()
        self.title_label.setObjectName("skill_title_label")
        self.title_label.setStyleSheet("""
            QLabel#skill_title_label {
                color: #4a90e2;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        self.title_label.setAlignment(Qt.AlignLeft)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Status label
        self.status_label = QLabel()
        self.status_label.setObjectName("skill_status_label")
        self.status_label.setStyleSheet("""
            QLabel#skill_status_label {
                color: #ffffff;
                font-size: 13px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Progress label (text-based instead of progress bar)
        self.progress_label = QLabel()
        self.progress_label.setObjectName("skill_progress_label")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("""
            QLabel#skill_progress_label {
                color: #4a90e2;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.progress_label.setAlignment(Qt.AlignLeft)
        self.progress_label.setWordWrap(True)
        self.progress_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Description label (skill_description from SkillContent)
        self.description_label = QLabel()
        self.description_label.setObjectName("skill_description_label")
        self.description_label.setStyleSheet("""
            QLabel#skill_description_label {
                color: #a0a0a0;
                font-size: 11px;
                font-style: italic;
            }
        """)
        self.description_label.setAlignment(Qt.AlignLeft)
        self.description_label.setWordWrap(True)
        self.description_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Add widgets to frame layout
        self.frame_layout.addWidget(self.title_label)
        self.frame_layout.addWidget(self.status_label)
        self.frame_layout.addWidget(self.progress_label)
        self.frame_layout.addWidget(self.description_label)

        # Add frame to main layout
        self.main_layout.addWidget(self.container_frame)

        # Set initial maximum width
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._update_width)

    def _apply_initial_state(self):
        """Apply the initial state based on structure content."""
        # Extract skill info from SkillContent attributes
        skill_name = self.structure_content.skill_name or "Unknown Skill"
        skill_description = self.structure_content.skill_description or ""

        # Set title and description
        self.title_label.setText(f"🔧 Skill: {skill_name}")
        self.description_label.setText(skill_description)
        self.description_label.setVisible(bool(skill_description))

        # Check if there are parameters to display
        if self.structure_content.parameters:
            params_text = "Parameters: " + ", ".join(
                f"{p.get('name', '?')}={p.get('value', '?')}" for p in self.structure_content.parameters
            )
            params_label = QLabel(params_text)
            params_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-size: 11px;
                }
            """)
            params_label.setWordWrap(True)
            self.frame_layout.insertWidget(3, params_label)

        # Set initial status
        self.update_content(self.structure_content)

    def resizeEvent(self, event):
        """Handle resize events to update the widget's width."""
        super().resizeEvent(event)
        self._update_width()

    def _update_width(self):
        """Update the widget's width based on the parent's available width."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_available_bubble_width'):
                available_width = parent._available_bubble_width()
                self.container_frame.setMaximumWidth(available_width)
                break
            elif hasattr(parent, 'sizeHint') and hasattr(parent, 'width'):
                parent_width = parent.width()
                if parent_width > 0:
                    margins = self.main_layout.contentsMargins()
                    available_width = max(0, parent_width - margins.left() - margins.right())
                    self.container_frame.setMaximumWidth(available_width)
                    break
            parent = parent.parent()

    def update_content(self, structure_content: SkillContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        # SkillContent doesn't have status/message/result directly
        # Use metadata or default to "completed" for display
        self.title_label.setText(f"🔧 Skill: {structure_content.skill_name or 'Unknown Skill'}")

        # Use description for status message
        status_msg = structure_content.skill_description or "Skill execution"
        self.status_label.setText(status_msg)

        # Show text-based progress instead of progress bar
        self.progress_label.setVisible(True)
        self.progress_label.setText("✓ Completed")

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "skill_name": self.structure_content.skill_name,
            "skill_description": self.structure_content.skill_description,
            "status": self.status,
            "status_message": self.status_message,
            "progress_visible": self.progress_label.isVisible() if self.progress_label else False,
            "progress_text": self.progress_label.text() if self.progress_label and self.progress_label.isVisible() else None
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "skill_name" in state and hasattr(self.structure_content, 'skill_name'):
            self.structure_content.skill_name = state["skill_name"]
        if "skill_description" in state and hasattr(self.structure_content, 'skill_description'):
            self.structure_content.skill_description = state["skill_description"]

        # Update status display
        if "status" in state:
            self.status = state["status"]
        if "status_message" in state:
            self.status_message = state["status_message"]
            self.status_label.setText(self.status_message)

        if "progress_visible" in state and self.progress_label:
            self.progress_label.setVisible(state["progress_visible"])
        if "progress_text" in state and self.progress_label:
            self.progress_label.setText(state["progress_text"])

    def update_available_width(self, width: int):
        """Update the available width for this widget."""
        self.available_width = width
        if self.available_width is not None and self.container_frame:
            self.container_frame.setMaximumWidth(self.available_width)
