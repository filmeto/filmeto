"""
Typing content widget for displaying agent typing indicator in message bubbles.
This widget displays three bouncing dots to indicate the agent is processing.
"""

from typing import Any, Dict
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QSizePolicy

from agent.chat.content import TypingContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class TypingContentWidget(BaseStructuredContentWidget):
    """Widget to display agent typing indicator with bouncing dots animation."""

    # Fixed width for the typing indicator
    FIXED_WIDTH = 40  # 3 dots of 8px + 4px spacing + margins

    def __init__(self, structure_content: TypingContent, parent=None):
        """
        Initialize the typing content widget.

        Args:
            structure_content: TypingContent object
            parent: Parent widget
        """
        # If no structure_content is provided, create a default one
        if structure_content is None:
            from agent.chat.content import TypingContent
            structure_content = TypingContent(
                title="Typing",
                description="Agent is typing"
            )
        super().__init__(structure_content, parent)

        # Animation state
        self._animation_step = 0
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animation)

        # Start the animation
        self._start_animation()

    def _setup_ui(self):
        """Set up the UI for the typing content widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Set fixed width and size policy for the widget
        self.setFixedWidth(self.FIXED_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Create a container for the typing indicator
        typing_frame = QFrame(self)
        typing_frame.setObjectName("typing_frame")
        typing_frame.setFixedWidth(self.FIXED_WIDTH)
        typing_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        typing_frame.setStyleSheet("""
            QFrame#typing_frame {
                background-color: transparent;
                border: none;
                padding: 4px 0px;
            }
        """)

        # Layout for the typing frame
        frame_layout = QHBoxLayout(typing_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(4)

        # Create three dots
        self.dots = []
        for i in range(3):
            dot = QLabel(typing_frame)
            dot.setObjectName(f"typing_dot_{i}")
            dot.setFixedSize(8, 8)
            dot.setStyleSheet("""
                QLabel {
                    background-color: #a0a0a0;
                    border-radius: 4px;
                }
            """)
            self.dots.append(dot)
            frame_layout.addWidget(dot)

        # Add the frame to the main layout
        layout.addWidget(typing_frame)

    def _start_animation(self):
        """Start the bouncing dots animation."""
        self._animation_step = 0
        self._animation_timer.start(150)  # Update every 150ms

    def _stop_animation(self):
        """Stop the bouncing dots animation."""
        self._animation_timer.stop()

    def _update_animation(self):
        """Update the animation frame."""
        # Dot opacity/brightness levels for bouncing effect
        opacity_levels = [
            ["#404040", "#404040", "#404040"],  # Start: all dim
            ["#808080", "#404040", "#404040"],  # Dot 1 rises
            ["#a0a0a0", "#808080", "#404040"],  # Dot 1 peak, Dot 2 rising
            ["#404040", "#a0a0a0", "#808080"],  # Dot 2 peak, Dot 3 rising
            ["#404040", "#404040", "#a0a0a0"],  # Dot 3 peak
            ["#404040", "#808080", "#a0a0a0"],  # Dot 3 falling, Dot 2 rising
            ["#808080", "#a0a0a0", "#404040"],  # Dot 2 peak, Dot 1 falling
            ["#a0a0a0", "#808080", "#404040"],  # Dot 1 peak, Dot 2 falling
        ]

        colors = opacity_levels[self._animation_step % len(opacity_levels)]

        for i, dot in enumerate(self.dots):
            dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {colors[i]};
                    border-radius: 4px;
                }}
            """)

        self._animation_step += 1

    def update_content(self, structure_content: TypingContent):
        """
        Update the widget with new structure content.
        For typing indicator, this doesn't change the visual but keeps consistency.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content
        # Typing indicator is always the same, no visual update needed

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "title": self.structure_content.title,
            "description": self.structure_content.description,
            "is_animating": self._animation_timer.isActive(),
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "title" in state:
            self.structure_content.title = state["title"]
        if "description" in state:
            self.structure_content.description = state["description"]

        # Rebuild UI to reflect changes
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()

        # Control animation based on state
        if state.get("is_animating", True):
            self._start_animation()
        else:
            self._stop_animation()

    def update_available_width(self, width: int):
        """Update the available width (typing indicator has fixed width)."""
        # Typing indicator has fixed width, no need to adjust
        pass

    def cleanup(self):
        """Clean up resources when widget is being destroyed."""
        self._stop_animation()
        super().cleanup()

    def start_typing(self):
        """Start the typing animation."""
        self._start_animation()

    def stop_typing(self):
        """Stop the typing animation."""
        self._stop_animation()

    def sizeHint(self):
        """Return the fixed size hint for the typing indicator."""
        return QSize(self.FIXED_WIDTH, 20)  # Height of 20 for the dots + margins
