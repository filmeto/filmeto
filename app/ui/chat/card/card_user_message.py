"""User message card widget for displaying user messages in chat."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy
)

from app.ui.components.avatar_widget import AvatarWidget
from app.ui.chat.message.structure_content_widget import StructureContentWidget


class UserMessageCard(QFrame):
    """Card widget for displaying user messages."""

    # Signals
    clicked = None  # User messages don't need click signals
    reference_clicked = None

    def __init__(self, content: str, parent=None):
        """Initialize user message card."""
        super().__init__(parent)

        # User message styling
        self.sender_name = "You"
        self.icon = "👤"
        self.color = "#35373a"
        self.alignment = Qt.AlignRight
        self.background_color = "#35373a"
        self.text_color = "#e1e1e1"
        self.avatar_size = 42
        self.structured_content_list = []

        # For backward compatibility
        self._is_thinking = False
        self._is_complete = False

        self._setup_ui(content)

    def _setup_ui(self, content: str):
        """Set up UI with name on the left of avatar."""
        self.setObjectName("user_message_card")
        self.setFrameShape(QFrame.NoFrame)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 8, 5, 8)
        main_layout.setSpacing(6)

        # Header row (name + avatar) - name on left for user messages
        header_row = QWidget(self)
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Name and role - added first (on the left)
        self.name_widget = QWidget(header_row)
        name_layout = QVBoxLayout(self.name_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)

        # Display name
        self.name_label = QLabel(self.sender_name, self.name_widget)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #35373a;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        name_layout.addWidget(self.name_label)

        # Add the name widget to the header layout first (left side)
        header_layout.addWidget(self.name_widget)

        # Avatar - added after name (on the right of name)
        self.avatar = AvatarWidget(
            icon=self.icon,
            color=self.color,
            size=self.avatar_size,
            shape="rounded_rect",
            parent=header_row
        )
        header_layout.addWidget(self.avatar)

        # Add stretch at the end to push everything to the right
        header_layout.addStretch()

        main_layout.addWidget(header_row)

        # Content area with padding to account for avatar width
        self.content_area = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setAlignment(self.alignment)
        avatar_width = self.avatar_size
        self.content_layout.setContentsMargins(avatar_width, 0, avatar_width, 0)
        self.content_layout.setSpacing(6)

        self.bubble_container = QFrame(self.content_area)
        self.bubble_container.setObjectName("message_bubble")
        self.bubble_container.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.bubble_layout = QVBoxLayout(self.bubble_container)
        self.bubble_layout.setContentsMargins(10, 8, 10, 8)
        self.bubble_layout.setSpacing(0)

        # Calculate initial available bubble width
        self._available_bubble_width_value = self._calculate_available_bubble_width()

        # Structure content widget
        self.structure_content = StructureContentWidget(content, self.bubble_container, self._available_bubble_width_value)
        self.structure_content.setStyleSheet(f"""
            QLabel#message_content {{
                background-color: {self.background_color};
                color: {self.text_color};
                font-size: 13px;
                border-radius: 5px;
            }}
        """)
        self.bubble_layout.addWidget(self.structure_content)
        self.content_layout.addWidget(self.bubble_container)

        main_layout.addWidget(self.content_area)

        # Apply card styling
        self._apply_style()

    def _apply_style(self):
        """Apply card styling."""
        self.setStyleSheet("""
            QFrame#user_message_card {
                background-color: transparent;
                margin: 2px 0px;
            }
        """)
        self.bubble_container.setStyleSheet(f"""
            QFrame#message_bubble {{
                background-color: {self.background_color};
                border-radius: 5px;
            }}
        """)

    def _calculate_available_bubble_width(self) -> int:
        total_width = max(0, self.width())
        max_width = max(0, total_width - (self.avatar_size * 2))
        if self.content_layout:
            margins = self.content_layout.contentsMargins()
            content_width = max(0, self.content_area.width() - margins.left() - margins.right())
            max_width = min(max_width, content_width)
        return max(80, max_width)

    def _available_bubble_width(self) -> int:
        return self._available_bubble_width_value

    def _calculate_text_width(self, max_text_width: int) -> int:
        text = self.structure_content.get_content() or ""
        if not text:
            return 0
        font_metrics = self.structure_content.get_content_label().fontMetrics()
        lines = text.splitlines() or [text]
        max_line_width = 0
        for line in lines:
            max_line_width = max(max_line_width, font_metrics.horizontalAdvance(line))
        return min(max_line_width, max_text_width)

    def _calculate_structured_content_width(self, max_width: int) -> int:
        return self.structure_content.get_structured_content_preferred_width(max_width)

    def _update_bubble_width(self):
        self._available_bubble_width_value = self._calculate_available_bubble_width()
        max_width = self._available_bubble_width_value
        padding = self.bubble_layout.contentsMargins().left() + self.bubble_layout.contentsMargins().right()
        max_content_width = max(0, max_width - padding)

        text_width = self._calculate_text_width(max_content_width)
        structured_width = self._calculate_structured_content_width(max_content_width)
        content_width = max(text_width, structured_width)
        bubble_width = min(max_width, content_width + padding)
        actual_content_width = max(0, bubble_width - padding)

        self.structure_content.get_content_label().setMaximumWidth(max_content_width)
        self.bubble_container.setFixedWidth(max(1, bubble_width))
        self.structure_content.setMaximumWidth(bubble_width)
        self.structure_content.update_available_width(actual_content_width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_bubble_width()

    def add_structure_content_widget(self, structure_content):
        """Add a widget for the given StructureContent based on its type."""
        from agent.chat.agent_chat_message import ContentType
        from app.ui.chat.message.text_content_widget import TextContentWidget

        widget = TextContentWidget(structure_content, self.structure_content)

        if widget:
            self.structure_content.add_structured_content_widget(widget)
            self._update_bubble_width()

    def set_content(self, content: str):
        """Set the content (replace)."""
        self.structure_content.set_content(content)
        self._update_bubble_width()

    def append_content(self, content: str):
        """Append content."""
        self.structure_content.append_content(content)
        self._update_bubble_width()

    def get_content(self) -> str:
        """Get current content."""
        return self.structure_content.get_content()

    def get_content_label(self):
        """Get the content label widget (for backward compatibility)."""
        return self.structure_content.get_content_label()

    def set_thinking(self, is_thinking: bool, thinking_text: str = ""):
        """Set thinking state (placeholder for backward compatibility)."""
        self._is_thinking = is_thinking
        pass

    def set_complete(self, is_complete: bool):
        """Set completion state (placeholder for backward compatibility)."""
        self._is_complete = is_complete
        pass

    def set_error(self, error_message: str):
        """Set error state."""
        error_content = f"❌ Error: {error_message}"
        self.set_content(error_content)
        self.structure_content.get_content_label().setStyleSheet("""
            QLabel#message_content {
                color: #e74c3c;
                font-size: 13px;
            }
        """)

    def add_structured_content(self, structured):
        """Add structured content widget (alias for backward compatibility)."""
        self.add_structure_content_widget(structured)

    def clear_structured_content(self):
        """Clear all structured content."""
        self.structure_content.clear_structured_content()
