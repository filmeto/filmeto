"""Base message card widget with shared functionality."""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy
)

from agent.chat.agent_chat_message import StructureContent, ContentType
from app.ui.chat.message.button_widget import ButtonWidget
from app.ui.chat.message.code_block_widget import CodeBlockWidget
from app.ui.chat.message.link_widget import LinkWidget
from app.ui.chat.message.table_widget import TableWidget
from app.ui.chat.message.text_content_widget import TextContentWidget
from app.ui.chat.message.structure_content_widget import StructureContentWidget
from app.ui.components.avatar_widget import AvatarWidget
from app.ui.chat.message.thinking_content_widget import ThinkingContentWidget
from app.ui.chat.message.skill_content_widget import SkillContentWidget
from app.ui.chat.message.typing_content_widget import TypingContentWidget


class BaseMessageCard(QFrame):
    """Base class for message cards with shared functionality."""

    # Signals
    clicked = Signal(str)  # message_id
    reference_clicked = Signal(str, str)  # ref_type, ref_id

    def __init__(
        self,
        content: str,
        sender_name: str,
        icon: str,
        color: str,
        parent=None,
        alignment: Qt.AlignmentFlag = Qt.AlignLeft,
        background_color: str = "#2b2d30",
        text_color: str = "#e1e1e1",
        avatar_size: int = 42,
        structured_content: Optional[List[StructureContent]] = None
    ):
        """Initialize base message card."""
        super().__init__(parent)
        self.sender_name = sender_name
        self.icon = icon
        self.color = color
        self.alignment = alignment
        self.background_color = background_color
        self.text_color = text_color
        self.avatar_size = avatar_size
        self.structured_content_list = structured_content or []

        # For backward compatibility
        self._is_thinking = False
        self._is_complete = False

        self._setup_ui(content)

    def _setup_ui(self, content: str):
        """Set up UI."""
        self.setObjectName("base_message_card")
        self.setFrameShape(QFrame.NoFrame)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 8, 5, 8)
        main_layout.setSpacing(6)

        # Header row (avatar + name)
        header_row = QWidget(self)
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Avatar - using agent-specific color and icon
        self.avatar = AvatarWidget(
            icon=self.icon,
            color=self.color,
            size=self.avatar_size,
            shape="rounded_rect",  # Match the original style
            parent=header_row
        )
        header_layout.addWidget(self.avatar)

        # Name and role
        self.name_widget = QWidget(header_row)
        # Set maximum height to prevent header from being stretched when crew_title is added
        self.name_widget.setMaximumHeight(self.avatar_size)
        name_layout = QVBoxLayout(self.name_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)

        # Display name
        self.name_label = QLabel(self.sender_name, self.name_widget)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        name_layout.addWidget(self.name_label)

        # Add the name widget to the header layout
        header_layout.addWidget(self.name_widget)

        # Add stretch to push everything to the left for agent messages or to the right for user messages
        if self.alignment == Qt.AlignRight:
            # For user messages, we want avatar on the right, so we add stretch at the beginning
            header_layout.insertStretch(0, 1)
        else:
            # For agent messages, we want avatar on the left, so we add stretch at the end
            header_layout.addStretch()

        main_layout.addWidget(header_row)

        # Content area with padding to account for avatar width
        self.content_area = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setAlignment(self.alignment)
        avatar_width = self.avatar_size  # Same as avatar size
        # Add margins to content area to ensure spacing on both sides
        self.content_layout.setContentsMargins(avatar_width, 0, avatar_width, 0)  # Left and right margins same as avatar width
        self.content_layout.setSpacing(6)

        self.bubble_container = QFrame(self.content_area)
        self.bubble_container.setObjectName("message_bubble")
        self.bubble_container.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.bubble_layout = QVBoxLayout(self.bubble_container)
        self.bubble_layout.setContentsMargins(10, 8, 10, 8)
        self.bubble_layout.setSpacing(0)

        # Calculate initial available bubble width
        self._available_bubble_width_value = self._calculate_available_bubble_width()

        # Replace content_label with structure_content widget, passing available width
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

        # No need for separate structured container since it's handled by structure_content

        main_layout.addWidget(self.content_area)

        # Add structured content widgets
        for structure_content in self.structured_content_list:
            self.add_structure_content_widget(structure_content)

        # Apply card styling
        self._apply_style()

    def _apply_style(self):
        """Apply card styling."""
        self.setStyleSheet("""
            QFrame#base_message_card {
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
        # Return the cached value
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
        """Preferred width of structured content (skill, thinking, code, etc.) for bubble sizing."""
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

    def sizeHint(self):
        """Return the size hint for this widget."""
        # Use current size as size hint to prevent layout changes
        return self.size()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_bubble_width()


    def add_structure_content_widget(self, structure_content: StructureContent):
        """Add a widget for the given StructureContent based on its type."""
        widget = None

        # Map ContentType to appropriate widget class
        content_type = structure_content.content_type

        if content_type == ContentType.TEXT:
            widget = TextContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.THINKING:
            widget = ThinkingContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.TYPING:
            widget = TypingContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.CODE_BLOCK:
            widget = CodeBlockWidget(structure_content, self.structure_content)
        elif content_type == ContentType.TABLE:
            widget = TableWidget(structure_content, self.structure_content)
        elif content_type == ContentType.LINK:
            widget = LinkWidget(structure_content, self.structure_content)
        elif content_type == ContentType.BUTTON:
            widget = ButtonWidget(structure_content, self.structure_content)
        elif content_type == ContentType.SKILL:
            # Pass None initially so the widget can report natural width for bubble calculation
            widget = SkillContentWidget(structure_content, self.structure_content, available_width=None)
        elif content_type == ContentType.TOOL_CALL:
            from app.ui.chat.message.tool_call_content_widget import ToolCallContentWidget
            widget = ToolCallContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.TOOL_RESPONSE:
            from app.ui.chat.message.tool_response_content_widget import ToolResponseContentWidget
            widget = ToolResponseContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.PROGRESS:
            from app.ui.chat.message.progress_content_widget import ProgressContentWidget
            widget = ProgressContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.ERROR:
            from app.ui.chat.message.error_content_widget import ErrorContentWidget
            widget = ErrorContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.METADATA:
            from app.ui.chat.message.metadata_content_widget import MetadataContentWidget
            widget = MetadataContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.IMAGE:
            from app.ui.chat.message.image_content_widget import ImageContentWidget
            widget = ImageContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.VIDEO:
            from app.ui.chat.message.video_content_widget import VideoContentWidget
            widget = VideoContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.AUDIO:
            from app.ui.chat.message.audio_content_widget import AudioContentWidget
            widget = AudioContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.CHART:
            from app.ui.chat.message.chart_content_widget import ChartContentWidget
            widget = ChartContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.FORM:
            from app.ui.chat.message.form_content_widget import FormContentWidget
            widget = FormContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.FILE_ATTACHMENT:
            from app.ui.chat.message.file_attachment_content_widget import FileAttachmentContentWidget
            widget = FileAttachmentContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.PLAN:
            from app.ui.chat.message.plan_content_widget import PlanContentWidget
            widget = PlanContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.STEP:
            from app.ui.chat.message.step_content_widget import StepContentWidget
            widget = StepContentWidget(structure_content, self.structure_content)
        elif content_type == ContentType.TASK_LIST:
            from app.ui.chat.message.task_list_content_widget import TaskListContentWidget
            widget = TaskListContentWidget(structure_content, self.structure_content)
        else:
            # Default to text content for unrecognized types
            widget = TextContentWidget(structure_content, self.structure_content)

        if widget:
            self.structure_content.add_structured_content_widget(widget)
            # Trigger a width recalculation after adding structure content
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
        # The new structure doesn't have a thinking indicator, so we'll just ignore this for now
        pass

    def set_complete(self, is_complete: bool):
        """Set completion state (placeholder for backward compatibility)."""
        self._is_complete = is_complete
        # The new structure doesn't have a completion state, so we'll just ignore this for now
        pass

    def set_error(self, error_message: str):
        """Set error state."""
        # Show error in content
        error_content = f"❌ Error: {error_message}"
        self.set_content(error_content)
        self.structure_content.get_content_label().setStyleSheet(f"""
            QLabel#message_content {{
                color: #e74c3c;
                font-size: 13px;
            }}
        """)

    def add_structured_content(self, structured: StructureContent):
        """Add structured content widget (alias for backward compatibility)."""
        self.add_structure_content_widget(structured)

    def clear_structured_content(self):
        """Clear all structured content."""
        self.structure_content.clear_structured_content()

    def remove_typing_indicator(self):
        """Remove the typing indicator widget if present."""
        self.structure_content.remove_typing_indicator()

    def has_typing_indicator(self) -> bool:
        """Check if this card has a typing indicator."""
        return self.structure_content.has_typing_indicator()
