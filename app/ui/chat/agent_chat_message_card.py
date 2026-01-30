"""Agent message card widget for multi-agent chat display.

This module provides a card widget for displaying individual agent messages
with support for structured data and visual differentiation.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy
)

from agent.chat.agent_chat_message import AgentMessage, StructureContent, ContentType
from app.ui.chat.message.button_widget import ButtonWidget
from app.ui.chat.message.code_block_widget import CodeBlockWidget
from app.ui.chat.message.link_widget import LinkWidget
from app.ui.chat.message.table_widget import TableWidget
# Import specialized widgets from the message subpackage
from app.ui.chat.message.text_content_widget import TextContentWidget
from app.ui.chat.message.structure_content_widget import StructureContentWidget
from app.ui.components.avatar_widget import AvatarWidget
# Import all specialized content widgets
from app.ui.chat.message.thinking_content_widget import ThinkingContentWidget
from app.ui.chat.message.skill_content_widget import SkillContentWidget

if TYPE_CHECKING:
    pass


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


class AgentMessageCard(BaseMessageCard):
    """Card widget for displaying an agent message in the chat.

    Features:
    - Visual differentiation by agent
    - Structured content display (text, code, tables, links, buttons)
    - Collapsible for long content
    """

    def __init__(
        self,
        agent_message: AgentMessage,
        parent=None,
        agent_color: str = "#4a90e2",  # Default color
        agent_icon: str = "🤖",  # Default icon
        crew_member_metadata: Optional[Dict[str, Any]] = None  # Metadata for crew member
    ):
        """Initialize agent message card."""
        self.agent_message = agent_message
        self.agent_color = agent_color  # Store the agent-specific color
        self.agent_icon = agent_icon  # Store the agent-specific icon
        self.crew_member_metadata = crew_member_metadata  # Store crew member metadata

        # Extract text content from structured_content for BaseMessageCard
        text_content = agent_message.get_text_content()
        
        # Call parent constructor with agent-specific parameters
        super().__init__(
            content=text_content,
            sender_name=agent_message.sender_name or agent_message.sender_id,
            icon=self.agent_icon,
            color=self.agent_color,
            parent=parent,
            alignment=Qt.AlignLeft,
            background_color="#2b2d30",
            text_color="#e1e1e1",
            structured_content=agent_message.structured_content
        )

        # Add crew title if available
        self._add_crew_title()

    def _add_crew_title(self):
        """Add crew title to the name widget if available."""
        if not self.crew_member_metadata or 'crew_title' not in self.crew_member_metadata:
            return

        crew_title = self.crew_member_metadata['crew_title']

        # Create the colored block with text inside
        title_text = crew_title.replace('_', ' ').title()
        color_block_with_text = QLabel(title_text)
        color_block_with_text.setAlignment(Qt.AlignCenter)
        color_block_with_text.setStyleSheet(f"""
            QLabel {{
                background-color: {self.agent_color};
                color: white;
                font-size: 9px;
                font-weight: bold;
                border-radius: 3px;
                padding: 3px 8px;  /* Adjust padding for better appearance */
            }}
        """)

        # Adjust the width based on the text content
        font_metrics = color_block_with_text.fontMetrics()
        text_width = font_metrics.horizontalAdvance(title_text) + 16  # Add some extra space
        color_block_with_text.setFixedWidth(max(text_width, 60))  # Minimum width of 60

        # Add to the name layout - we now have a reference to name_widget
        name_layout = self.name_widget.layout()
        if name_layout:
            name_layout.addWidget(color_block_with_text)

    def update_from_agent_message(self, agent_message: AgentMessage):
        """Update the card from a new agent message."""
        # Update basic content from structured_content
        text_content = agent_message.get_text_content()
        self.structure_content.set_content(text_content)
        self._update_bubble_width()

        # Clear existing structured content
        self.clear_structured_content()

        # Add new structured content
        for structure_content in agent_message.structured_content:
            self.add_structure_content_widget(structure_content)

class UserMessageCard(BaseMessageCard):
    """Card widget for displaying user messages."""

    def __init__(self, content: str, parent=None):
        """Initialize user message card."""
        super().__init__(
            content=content,
            sender_name="You",
            icon="👤",
            color="#35373a",
            parent=parent,
            alignment=Qt.AlignRight,
            background_color="#35373a",
            text_color="#e1e1e1"
        )

        # Update the object name and styling for user messages
        self.setObjectName("user_message_card")
        self.setStyleSheet("""
            QFrame#user_message_card {
                background-color: transparent;
                margin: 2px 0px;
            }
        """)

        # Update name label styling for user messages
        self.name_label.setStyleSheet("""
            QLabel {
                color: #35373a;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        # Update bubble styling for user messages
        self.bubble_container.setStyleSheet(f"""
            QFrame#message_bubble {{
                background-color: {self.background_color};
                border-radius: 5px;
            }}
        """)
