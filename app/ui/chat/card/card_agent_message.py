"""Agent message card widget for displaying agent messages in chat."""

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from agent.chat.agent_chat_message import AgentMessage, StructureContent
from app.ui.chat.card.card_base import BaseMessageCard


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
