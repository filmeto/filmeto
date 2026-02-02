"""
Thinking content widget for displaying agent thought processes in message bubbles.
This widget displays the agent's thinking process with a distinct visual style.
"""

from typing import Any, Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QFrame

from agent.chat.content import ThinkingContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ThinkingContentWidget(BaseStructuredContentWidget):
    """Widget to display agent thinking process with a distinct visual style."""

    def __init__(self, structure_content: ThinkingContent, parent=None):
        """
        Initialize the thinking content widget.

        Args:
            structure_content: ThinkingContent object containing thinking data
            parent: Parent widget
        """
        # If no structure_content is provided, create a default one for thinking
        if structure_content is None:
            from agent.chat.content import ThinkingContent
            structure_content = ThinkingContent(
                thought="",
                title="Thinking Process",
                description="Agent's thought process"
            )
        super().__init__(structure_content, parent)

    def _setup_ui(self):
        """Set up the UI for the thinking content widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Create a container frame for the thinking content
        thinking_frame = QFrame(self)
        thinking_frame.setObjectName("thinking_frame")
        thinking_frame.setStyleSheet("""
            QFrame#thinking_frame {
                background-color: rgba(124, 77, 255, 0.1);
                border: 1px solid rgba(124, 77, 255, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)

        # Layout for the thinking frame
        frame_layout = QVBoxLayout(thinking_frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(4)

        # Build header with step info if available
        header_text = "🤔 Thinking Process"
        if self.structure_content.step is not None:
            if self.structure_content.total_steps:
                header_text += f" (Step {self.structure_content.step}/{self.structure_content.total_steps})"
            else:
                header_text += f" (Step {self.structure_content.step})"

        # Add a header label for the thinking section
        header_label = QLabel(header_text, thinking_frame)
        header_label.setObjectName("thinking_header")
        header_label.setStyleSheet("""
            QLabel#thinking_header {
                color: #a0a0a0;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 4px;
            }
        """)
        header_label.setAlignment(Qt.AlignLeft)

        # Create the thinking content label
        self.thinking_label = QLabel("", thinking_frame)  # Will be set by update_content
        self.thinking_label.setObjectName("thinking_content")
        self.thinking_label.setWordWrap(True)
        self.thinking_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.thinking_label.setStyleSheet("""
            QLabel#thinking_content {
                color: #c0c0c0;
                font-size: 13px;
                font-style: italic;
            }
        """)

        # Add header and content to frame layout
        frame_layout.addWidget(header_label)
        frame_layout.addWidget(self.thinking_label)

        # Add the frame to the main layout
        layout.addWidget(thinking_frame)

        # Apply the initial content
        self.update_content(self.structure_content)

    def update_content(self, structure_content: ThinkingContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content
        # Extract the thinking content from the 'thought' attribute
        content = self.structure_content.thought or ""

        # Update header if step info changed
        if self.thinking_label:
            # Rebuild header with step info
            header_text = "🤔 Thinking Process"
            if self.structure_content.step is not None:
                if self.structure_content.total_steps:
                    header_text += f" (Step {self.structure_content.step}/{self.structure_content.total_steps})"
                else:
                    header_text += f" (Step {self.structure_content.step})"

            # Find and update header label
            header_label = self.findChild(QLabel, "thinking_header")
            if header_label:
                header_label.setText(header_text)

            self.thinking_label.setText(content)

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "thought": self.structure_content.thought,
            "step": self.structure_content.step,
            "total_steps": self.structure_content.total_steps,
            "title": self.structure_content.title,
            "description": self.structure_content.description
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "thought" in state and hasattr(self.structure_content, 'thought'):
            self.structure_content.thought = state["thought"]
        if "step" in state and hasattr(self.structure_content, 'step'):
            self.structure_content.step = state["step"]
        if "total_steps" in state and hasattr(self.structure_content, 'total_steps'):
            self.structure_content.total_steps = state["total_steps"]
        if "title" in state and hasattr(self.structure_content, 'title'):
            self.structure_content.title = state["title"]
        if "description" in state and hasattr(self.structure_content, 'description'):
            self.structure_content.description = state["description"]

        # Rebuild UI to reflect changes
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()

    def update_available_width(self, width: int):
        """Update the available width."""
        # Update the maximum width of the content label
        if self.thinking_label:
            self.thinking_label.setMaximumWidth(max(1, width - 20))  # Account for margins
