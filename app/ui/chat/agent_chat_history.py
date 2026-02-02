"""Chat history component for agent panel with multi-agent support.

This module provides a group-chat style presentation for multi-agent conversations,
with support for streaming content, structured data, and concurrent agent execution.
"""

import uuid
from typing import Dict, List, Any, TYPE_CHECKING
from PySide6.QtWidgets import (
    QVBoxLayout, QScrollArea, QWidget, QLabel
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QIcon, QFont, QPen

from agent import AgentMessage
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr

# Lazy imports - defer heavy imports until first use
if TYPE_CHECKING:
    from app.data.workspace import Workspace
    from agent.chat.conversation import Message
    from app.ui.chat.card import AgentMessageCard, UserMessageCard

class AgentChatHistoryWidget(BaseWidget):
    """Chat history component for displaying multi-agent conversation messages.

    Features:
    - Group-chat style presentation with multiple agent cards
    - Streaming content updates per agent
    - Structured content display (plans, tasks, media, references)
    - Concurrent agent execution visualization
    - Dynamic card updates during streaming
    """

    # Signals
    reference_clicked = Signal(str, str)  # ref_type, ref_id
    message_complete = Signal(str, str)  # message_id, agent_name

    def __init__(self, workspace: 'Workspace', parent=None):
        """Initialize the chat history widget."""
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        # Message tracking
        self.messages: List[QWidget] = []  # All message widgets
        self._message_cards: Dict[str, AgentMessageCard] = {}  # message_id -> card
        self._agent_current_cards: Dict[str, str] = {}  # agent_name -> current message_id
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._scroll_to_bottom)

        # Track if user is at the bottom of the chat
        self._user_at_bottom = True

        # Sub-agent metadata cache
        self._crew_member_metadata: Dict[str, Dict[str, Any]] = {}
        self._load_crew_member_metadata()

        # Connect to project switched signal to refresh metadata when project changes
        if self.workspace:
            try:
                self.workspace.connect_project_switched(self._on_project_switched)
            except AttributeError:
                # In case the workspace doesn't have this method
                pass

        self._setup_ui()

        # Load the most recent conversation if available
        self._load_recent_conversation()

    def refresh_crew_member_metadata(self):
        """Refresh crew member metadata when project changes."""
        self._load_crew_member_metadata()

    def _on_project_switched(self, project_name: str):
        """Handle project switched event."""
        print(f"Project switched to: {project_name}, refreshing crew member metadata")
        self.refresh_crew_member_metadata()

        # Reload the most recent conversation for the new project
        self._load_recent_conversation()

    def _load_recent_conversation(self):
        """Load the most recent conversation from the current project."""
        try:
            # Get the current project
            project = self.workspace.get_project()
            if not project:
                print("No project found, skipping conversation load")
                return

            # Get the conversation manager from the project
            conversation_manager = project.get_conversation_manager()

            # Get or create the default (most recent) conversation
            conversation = project.get_or_create_default_conversation()

            if conversation:
                print(f"Loading conversation: {conversation.title} ({len(conversation.messages)} messages)")

                # Clear existing messages
                self.clear()

                # Add messages to the chat history
                for message in conversation.messages:
                    # Map the message role to sender name
                    if message.role == "user":
                        sender = tr("User")  # Use translation for "User"
                    elif message.role == "system":
                        sender = tr("System")  # Use translation for "System"
                    elif message.role == "tool":
                        sender = tr("Tool")  # Use translation for "Tool"
                    else:  # assistant or other roles
                        # Use the metadata to get the agent name if available
                        # Check if this is a crew member message
                        if message.metadata and 'sender_name' in message.metadata:
                            sender = message.metadata['sender_name']
                        elif message.metadata and 'agent_name' in message.metadata:
                            sender = message.metadata['agent_name']
                        elif message.metadata and 'title' in message.metadata:
                            # Use the title from metadata as the sender
                            sender = message.metadata['title']
                        else:
                            # Default to Assistant if no specific agent info
                            sender = tr("Assistant")

                    # Add the message to the chat history
                    # For historical messages, we need to create the proper card with metadata
                    self._add_historical_message(sender, message)
            else:
                print("No conversation found, starting fresh")

        except Exception as e:
            logger.error(f"Error loading recent conversation: {e}", exc_info=True)

    def _add_historical_message(self, sender: str, message: 'Message'):
        """Add a historical message to the chat history with proper metadata."""
        if not message.content:
            return

        # Lazy import when first needed
        from app.ui.chat.card import AgentMessageCard, UserMessageCard
        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType

        # Determine if this is a user message
        is_user = message.role == "user"
        is_user_normalized = sender.lower() in [tr("用户").lower(), "用户", "user", tr("user").lower()]

        if is_user or is_user_normalized:
            card = UserMessageCard(message.content, self.messages_container)
        else:
            # Generate a message ID based on timestamp or use one from metadata if available
            message_id = message.metadata.get('message_id', f"hist_{message.timestamp}") if message.metadata else f"hist_{message.timestamp}"

            # Create an AgentMessage with structured_content
            from agent.chat.content import TextContent
            agent_message = ChatAgentMessage(
                message_type=MessageType.TEXT,
                sender_id=sender,
                sender_name=sender,
                message_id=message_id,
                structured_content=[TextContent(text=message.content)] if message.content else []
            )

            # Get the color and icon for this agent from metadata
            # Ensure metadata is loaded
            if not self._crew_member_metadata:
                self._load_crew_member_metadata()

            agent_color = "#4a90e2"  # Default color
            agent_icon = "🤖"  # Default icon

            # Normalize the sender to lowercase to match metadata keys
            normalized_sender = sender.lower()
            sender_crew_member = self._crew_member_metadata.get(normalized_sender)
            if sender_crew_member:
                agent_color = sender_crew_member.config.color
                agent_icon = sender_crew_member.config.icon
            else:
                # Check if there's color/icon info in the message metadata
                if message.metadata:
                    agent_color = message.metadata.get('color', agent_color)
                    agent_icon = message.metadata.get('icon', agent_icon)
                else:
                    print(f"Note: Sender '{normalized_sender}' not found in sub-agent metadata (this is normal for historical messages)")
                    agent_color = '#4a90e2'  # Default color
                    agent_icon = '🤖'  # Default icon

            # Use the same crew member object for metadata
            crew_member_obj = sender_crew_member

            # Convert crew member object to metadata format
            if crew_member_obj:
                crew_member_data = {
                    'name': crew_member_obj.config.name,
                    'description': crew_member_obj.config.description,
                    'color': crew_member_obj.config.color,
                    'icon': crew_member_obj.config.icon,
                    'soul': crew_member_obj.config.soul,
                    'skills': crew_member_obj.config.skills,
                    'model': crew_member_obj.config.model,
                    'temperature': crew_member_obj.config.temperature,
                    'max_steps': crew_member_obj.config.max_steps,
                    'config_path': crew_member_obj.config.config_path,
                    'crew_title': crew_member_obj.config.metadata.get('crew_title', normalized_sender)
                }
            else:
                # Use metadata from the message if available
                crew_member_data = message.metadata or {}

            card = AgentMessageCard(
                agent_message=agent_message,
                agent_color=agent_color,  # Pass the color to the card
                agent_icon=agent_icon,    # Pass the icon to the card
                crew_member_metadata=crew_member_data,  # Pass the crew member metadata
                parent=self.messages_container
            )

            self._message_cards[message_id] = card

        # Insert before the stretch spacer
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)
        self.messages.append(card)

        self._schedule_scroll()

        return card

    def _load_crew_member_metadata(self):
        """Load crew member objects including color configurations."""
        try:
            # Import here to avoid circular imports
            from agent.crew.crew_service import CrewService

            # Get the current project
            project = self.workspace.get_project()
            if project:
                # Initialize crew member service
                crew_member_service = CrewService()

                # Load crew members for the project
                crew_members = crew_member_service.get_project_crew_members(project)

                # Convert to a dictionary using crew member names as keys for easy lookup
                self._crew_member_metadata = {}
                for name, crew_member in crew_members.items():
                    # Use the crew member's actual name as the key (normalized to lowercase)
                    self._crew_member_metadata[crew_member.config.name.lower()] = crew_member

                print(f"Loaded crew members for project: {len(self._crew_member_metadata)} agents")
            else:
                print("No project found, clearing crew member metadata")
                self._crew_member_metadata = {}
        except Exception as e:
            print(f"Error loading crew members: {e}")
            self._crew_member_metadata = {}

    def _create_circular_icon(
        self,
        icon_char: str,
        size: int = 24,
        bg_color: QColor = None,
        icon_color: QColor = None,
        use_iconfont: bool = True
    ) -> QIcon:
        """Create a circular icon with an icon character."""
        if bg_color is None:
            bg_color = QColor("#4080ff")
        if icon_color is None:
            icon_color = QColor("#ffffff")
        
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = QPainterPath()
        rect.addEllipse(0, 0, size, size)
        painter.fillPath(rect, bg_color)
        
        if use_iconfont:
            font = QFont("iconfont", size // 2)
        else:
            font = QFont()
            font.setPointSize(size // 2)
            font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(icon_color))
        painter.drawText(0, 0, size, size, Qt.AlignCenter, icon_char)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _get_sender_info(self, sender: str):
        """Get sender information including icon and alignment."""
        # Normalize sender name for comparison
        normalized_sender = sender.lower()
        is_user = normalized_sender in [tr("用户").lower(), "用户", "user", tr("user").lower()]
        is_system = normalized_sender in [tr("系统").lower(), "系统", "system", tr("system").lower()]
        is_tool = normalized_sender in [tr("工具").lower(), "工具", "tool", tr("tool").lower()]
        is_assistant = normalized_sender in [tr("助手").lower(), "助手", "assistant", tr("assistant").lower()]

        if is_user:
            icon_char = "\ue6b3"
            bg_color = QColor("#35373a")
            alignment = Qt.AlignLeft
            use_iconfont = True
        elif is_system or is_tool:
            # System and tool messages use different styling
            icon_char = "⚙️"  # Gear icon for system/tool
            bg_color = QColor("#555555")
            alignment = Qt.AlignLeft
            use_iconfont = False
        else:
            # For crew members and assistants, we'll use their specific icons/colors later
            # So return generic values here, the AgentMessageCard will handle the specific styling
            icon_char = "A"
            bg_color = QColor("#3d3f4e")
            alignment = Qt.AlignLeft
            use_iconfont = False

        return is_user, icon_char, bg_color, alignment, use_iconfont

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)  # Match agent_prompt_widget margins
        layout.setSpacing(0)

        # Scroll area for chat messages
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #252525;
                border: none;  /* Remove border to match agent_prompt_widget style */
                border-radius: 0px;  /* Remove border radius */
            }
            QScrollBar:vertical {
                background-color: #2b2d30;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #505254;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #606264;
            }
        """)

        # Connect scroll bar value change to track user position
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)

        # Container widget for messages
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("""
            QWidget {
                background-color: #252525;
            }
        """)
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(5, 10, 5, 10)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)
    
    def _on_scroll_value_changed(self, value):
        """Track when user scrolls and whether they're at the bottom."""
        scrollbar = self.scroll_area.verticalScrollBar()
        # Calculate if user is at/near the bottom
        # If the difference between max value and current value is less than 50 pixels,
        # consider the user to be at/near the bottom
        scroll_diff = scrollbar.maximum() - value
        self._user_at_bottom = scroll_diff < 50

    def _scroll_to_bottom(self):
        """Scroll to bottom of chat only if user was previously at the bottom."""
        scrollbar = self.scroll_area.verticalScrollBar()

        # Only scroll to bottom if the user was already at the bottom
        if self._user_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
    
    def _schedule_scroll(self):
        """Schedule a scroll to bottom (debounced)."""
        self._scroll_timer.start(50)  # 50ms debounce
    
    # ========================================================================
    # Legacy API (for backward compatibility)
    # ========================================================================
    
    def append_message(self, sender: str, message: str, message_id: str = None) -> QWidget:
        """Append a message to the chat history (legacy API)."""
        if not message:
            return None

        # Lazy import when first needed
        from app.ui.chat.card import AgentMessageCard, UserMessageCard
        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType

        is_user, icon_char, bg_color, alignment, use_iconfont = self._get_sender_info(sender)

        # Create appropriate card
        if is_user:
            card = UserMessageCard(message, self.messages_container)
        else:
            # Generate message_id if not provided
            if not message_id:
                message_id = str(uuid.uuid4())

            # Create an AgentMessage with structured_content
            from agent.chat.content import TextContent
            agent_message = ChatAgentMessage(
                message_type=MessageType.TEXT,
                sender_id=sender,
                sender_name=sender,
                message_id=message_id,
                structured_content=[TextContent(text=message)] if message else []
            )

            # Get the color and icon for this agent from metadata
            # Ensure metadata is loaded
            if not self._crew_member_metadata:
                self._load_crew_member_metadata()

            agent_color = "#4a90e2"  # Default color
            agent_icon = "🤖"  # Default icon

            # Normalize the sender to lowercase to match metadata keys
            normalized_sender = sender.lower()
            sender_crew_member = self._crew_member_metadata.get(normalized_sender)
            if sender_crew_member:
                agent_color = sender_crew_member.config.color
                agent_icon = sender_crew_member.config.icon
            else:
                # For user messages, we typically don't want to use sub-agent colors
                # But if sender happens to match a sub-agent name, we'll use that color
                print(f"Note: Sender '{normalized_sender}' not found in sub-agent metadata (this is normal for user messages)")
                agent_color = '#4a90e2'  # Default color
                agent_icon = '🤖'  # Default icon

            # Use the same crew member object for metadata
            crew_member_obj = sender_crew_member

            # Convert crew member object to metadata format
            if crew_member_obj:
                crew_member_data = {
                    'name': crew_member_obj.config.name,
                    'description': crew_member_obj.config.description,
                    'color': crew_member_obj.config.color,
                    'icon': crew_member_obj.config.icon,
                    'soul': crew_member_obj.config.soul,
                    'skills': crew_member_obj.config.skills,
                    'model': crew_member_obj.config.model,
                    'temperature': crew_member_obj.config.temperature,
                    'max_steps': crew_member_obj.config.max_steps,
                    'config_path': crew_member_obj.config.config_path,
                    'crew_title': crew_member_obj.config.metadata.get('crew_title', normalized_sender)
                }
            else:
                crew_member_data = {}

            card = AgentMessageCard(
                agent_message=agent_message,
                agent_color=agent_color,  # Pass the color to the card
                agent_icon=agent_icon,    # Pass the icon to the card
                crew_member_metadata=crew_member_data,  # Pass the crew member metadata
                parent=self.messages_container
            )

            self._message_cards[message_id] = card

        # Insert before the stretch spacer
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)
        self.messages.append(card)

        self._schedule_scroll()

        return card
    
    def update_last_message(self, message: str):
        """Update the content of the last message (legacy API)."""
        if not self.messages:
            return

        # Lazy import when first needed
        from app.ui.chat.card import AgentMessageCard
        from agent.chat.content import TextContent
        from agent.chat.agent_chat_types import ContentType

        last_widget = self.messages[-1]
        if isinstance(last_widget, AgentMessageCard):
            # Update structured_content instead of content
            # Clear existing text content and add new one
            text_content = TextContent(text=message)
            # Remove existing TEXT content and add new one
            last_widget.agent_message.structured_content = [
                sc for sc in last_widget.agent_message.structured_content
                if sc.content_type != ContentType.TEXT
            ]
            last_widget.agent_message.structured_content.append(text_content)
            last_widget.set_content(message)
        else:
            # Old style widget
            for child in last_widget.findChildren(QLabel):
                if child.objectName() == "chat_content_label":
                    child.setText(message)
                    break

        self._schedule_scroll()
    
    def start_streaming_message(self, sender: str) -> str:
        """Start a new streaming message (legacy API)."""
        message_id = str(uuid.uuid4())
        self.append_message(sender, "...", message_id)
        return message_id
    
    def update_streaming_message(self, message_id: str, content: str):
        """Update a streaming message by ID (legacy API)."""
        card = self._message_cards.get(message_id)
        if card:
            # Update structured_content instead of content
            from agent.chat.content import TextContent
            from agent.chat.agent_chat_types import ContentType
            # Find existing TEXT content or create new one
            text_content = None
            for sc in card.agent_message.structured_content:
                if sc.content_type == ContentType.TEXT:
                    text_content = sc
                    break
            if text_content:
                # Update existing text content
                text_content.text = content
            else:
                # Add new text content
                card.agent_message.structured_content.append(TextContent(text=content))
            card.set_content(content)
        else:
            # Fallback to old method
            for widget in self.messages:
                if hasattr(widget, 'property') and widget.property("message_id") == message_id:
                    for child in widget.findChildren(QLabel):
                        if child.objectName() == "chat_content_label":
                            child.setText(content)
                            break
                    break

        self._schedule_scroll()
    
    # ========================================================================
    # Multi-Agent Streaming API
    # ========================================================================
    
    def add_user_message(self, content: str):
        """Add a user message card."""
        # Lazy import when first needed
        from app.ui.chat.card import UserMessageCard
        
        card = UserMessageCard(content, self.messages_container)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)
        self.messages.append(card)
        self._schedule_scroll()
        return card
    
    def get_or_create_agent_card(
        self,
        message_id: str,
        agent_name: str,
        title = None  # This parameter is kept for compatibility but not used
    ):
        """Get or create an agent message card."""
        if message_id in self._message_cards:
            return self._message_cards[message_id]

        # Lazy import when first needed
        from app.ui.chat.card import AgentMessageCard
        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType

        # Create an empty AgentMessage
        agent_message = ChatAgentMessage(
            message_type=MessageType.TEXT,
            sender_id=agent_name,
            sender_name=agent_name,
            message_id=message_id,
            structured_content=[]
        )

        # Get the color and icon for this agent from metadata
        # Ensure metadata is loaded
        if not self._crew_member_metadata:
            self._load_crew_member_metadata()

        agent_color = "#4a90e2"  # Default color
        agent_icon = "🤖"  # Default icon

        # Normalize the agent_name to lowercase to match metadata keys
        normalized_agent_name = agent_name.lower()
        agent_crew_member = self._crew_member_metadata.get(normalized_agent_name)
        if agent_crew_member:
            agent_color = agent_crew_member.config.color
            agent_icon = agent_crew_member.config.icon
        else:
            print(f"Warning: No metadata found for agent {normalized_agent_name}, available: {list(self._crew_member_metadata.keys())}")
            agent_color = '#4a90e2'  # Default color
            agent_icon = '🤖'  # Default icon

        # Use the same crew member object for metadata
        crew_member_obj = agent_crew_member

        # Convert crew member object to metadata format
        if crew_member_obj:
            crew_member_data = {
                'name': crew_member_obj.config.name,
                'description': crew_member_obj.config.description,
                'color': crew_member_obj.config.color,
                'icon': crew_member_obj.config.icon,
                'soul': crew_member_obj.config.soul,
                'skills': crew_member_obj.config.skills,
                'model': crew_member_obj.config.model,
                'temperature': crew_member_obj.config.temperature,
                'max_steps': crew_member_obj.config.max_steps,
                'config_path': crew_member_obj.config.config_path,
                'crew_title': crew_member_obj.config.metadata.get('crew_title', normalized_agent_name)
            }
        else:
            crew_member_data = {}

        card = AgentMessageCard(
            agent_message=agent_message,
            agent_color=agent_color,  # Pass the color to the card
            agent_icon=agent_icon,    # Pass the icon to the card
            crew_member_metadata=crew_member_data,  # Pass the crew member metadata
            parent=self.messages_container
        )

        # Connect signals
        card.reference_clicked.connect(self.reference_clicked.emit)

        # Add to layout
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)
        self.messages.append(card)
        self._message_cards[message_id] = card
        self._agent_current_cards[agent_name] = message_id

        self._schedule_scroll()
        return card
    
    def get_agent_current_card(self, agent_name: str):
        """Get the current active card for an agent."""
        message_id = self._agent_current_cards.get(agent_name)
        if message_id:
            return self._message_cards.get(message_id)
        return None
    
    def update_agent_card(
        self,
        message_id: str,
        content: str = None,
        append: bool = True,
        is_thinking: bool = False,
        thinking_text: str = "",
        is_complete: bool = False,
        structured_content=None,
        error: str = None,
    ):
        """Update an agent message card."""
        card = self._message_cards.get(message_id)
        if not card:
            return

        if content is not None:
            from agent.chat.content import TextContent
            from agent.chat.agent_chat_types import ContentType
            # Find existing TEXT content or create new one
            text_content = None
            for sc in card.agent_message.structured_content:
                if sc.content_type == ContentType.TEXT:
                    text_content = sc
                    break
            if text_content:
                # Update existing text content
                if append:
                    text_content.text = (text_content.text or "") + content
                else:
                    text_content.text = content
            else:
                # Add new text content
                card.agent_message.structured_content.append(TextContent(text=content))
            # Update the display
            final_content = text_content.text if text_content else content
            card.set_content(final_content)

        if structured_content is not None:
            from agent.chat.content import StructureContent

            items = (
                [structured_content]
                if isinstance(structured_content, StructureContent)
                else list(structured_content)
            )
            for sc in items:
                card.agent_message.structured_content.append(sc)
                card.add_structure_content_widget(sc)

        if error:
            from agent.chat.content import TextContent
            from agent.chat.agent_chat_types import ContentType
            error_text = f"❌ Error: {error}"
            # Remove existing TEXT content and add error
            card.agent_message.structured_content = [
                sc for sc in card.agent_message.structured_content
                if sc.content_type != ContentType.TEXT
            ]
            card.agent_message.structured_content.append(TextContent(text=error_text))
            card.set_content(error_text)

        self._schedule_scroll()

    async def handle_agent_message(self, message: AgentMessage):
        if message.sender_id == "user":
            return

        # Skip creating chat cards for system lifecycle events (handled by plan widget or unused)
        if getattr(message, "message_type", None):
            from agent.chat.agent_chat_types import MessageType
            if message.message_type == MessageType.SYSTEM and message.metadata.get("event_type") in (
                "crew_member_start", "producer_start", "mentioned_agent_start",
                "responding_agent_start", "plan_update", "plan_created",
            ):
                return

        message_id = (
            getattr(message, "message_id", None)
            or (message.metadata.get("message_id") if message.metadata else None)
        )
        if not message_id:
            message_id = str(uuid.uuid4())

        card = self.get_or_create_agent_card(
            message_id,
            message.sender_name,
            message.sender_name,
        )

        has_structure = bool(message.structured_content)
        if has_structure:
            for sc in message.structured_content:
                self.update_agent_card(message_id, structured_content=sc)
        # """Handle an AgentMessage directly. Uses StructureContent for display; no business data via metadata."""
        # from PySide6.QtWidgets import QApplication
        # QApplication.processEvents()

    @Slot(object, object)
    def handle_stream_event(self, event, session):
        """Handle a streaming event from the agent system."""
        # Handle different types of events based on event_type
        if event.event_type == "error":
            # Handle error events - data contains content and session_id
            error_content = event.data.get('content', 'Unknown error occurred')

            # Create a message ID for the error
            message_id = str(uuid.uuid4())

            # Create or update the card with the error content
            card = self.get_or_create_agent_card(
                message_id,
                "System",  # Error messages come from the system
                "System"
            )

            # Update the card with the error content
            from agent.chat.content import ErrorContent
            error_structure = ErrorContent(
                error_message=error_content
            )
            self.update_agent_card(
                message_id,
                structured_content=error_structure,
                error=error_content
            )
        elif event.event_type == "agent_response":
            # Handle agent response events - data comes from event.data
            content = event.data.get('content', '')
            sender_name = event.data.get('sender_name', 'Unknown')
            sender_id = event.data.get('sender_id', sender_name.lower())
            session_id = event.data.get('session_id', 'unknown')

            # Check if this is a user message that would cause duplication
            # If sender_id is "user", we need to avoid duplication
            if sender_id == "user":
                # Skip adding user messages that come through the agent system
                # since they're already added when the user submits them in the UI
                return

            # Create a unique message ID for this response
            message_id = event.data.get('message_id')
            if not message_id:
                message_id = f"response_{session_id}_{uuid.uuid4()}"
            append_content = event.data.get('append', True)

            # Create or update the card with the content
            card = self.get_or_create_agent_card(
                message_id,
                sender_name,  # This will be normalized in get_or_create_agent_card
                sender_name
            )

            # Update the card with structured_content
            from agent.chat.content import TextContent
            text_structure = TextContent(text=content)
            self.update_agent_card(
                message_id,
                structured_content=text_structure
            )
        elif event.event_type in ["skill_start", "skill_progress", "skill_end"]:
            # Handle skill events (start, progress, end)
            skill_name = event.data.get('skill_name', 'Unknown')
            sender_name = event.data.get('sender_name', 'Unknown')
            sender_id = event.data.get('sender_id', sender_name.lower())
            message_id = event.data.get('message_id', str(uuid.uuid4()))

            # Check if this is a user message that would cause duplication
            if sender_id == "user":
                # Skip adding user messages that come through the agent system
                return

            # Determine the status based on event type
            if event.event_type == "skill_start":
                status = "starting"
                message = f"Starting skill: {skill_name}"
                content = f"[Skill: {skill_name}] Starting execution..."
            elif event.event_type == "skill_progress":
                status = "in_progress"
                message = event.data.get('progress_text', 'Processing...')
                content = f"[Skill: {skill_name}] {message}"
            elif event.event_type == "skill_end":
                status = "completed"
                result = event.data.get('result', 'No result returned')
                message = result
                content = f"[Skill: {skill_name}] Completed. Result: {result}"
            else:
                status = "unknown"
                message = "Unknown skill status"
                content = f"[Skill: {skill_name}] {message}"

            # Get or create the card
            card = self.get_or_create_agent_card(
                message_id,
                sender_name,
                sender_name
            )

            # Create structured content for skill execution
            from agent.chat.content import SkillContent, ProgressContent
            # Use ProgressContent for skill execution status
            skill_content = ProgressContent(
                progress=content,
                percentage=None,
                tool_name=skill_name
            )

            # Update the card with the structured content
            self.update_agent_card(
                message_id,
                content=content,
                append=False,
                structured_content=skill_content
            )
        elif hasattr(event, 'content') and event.content:
            # Handle regular content events (fallback for other types)
            # Check if this is a user message that would cause duplication
            sender_id = getattr(event, 'sender_id', '')
            if hasattr(event, 'agent_name'):
                sender_id = getattr(event, 'agent_name', '').lower()

            if sender_id == "user":
                # Skip adding user messages that come through the agent system
                return

            # Check if this is a thinking message
            message_type = getattr(event, 'message_type', None)
            from agent.chat.agent_chat_types import MessageType, ContentType
            # Get or create the card
            card = self._message_cards.get(event.message_id)
            if not card:
                agent_name = getattr(event, 'agent_name', 'Unknown')
                card = self.get_or_create_agent_card(
                    event.message_id,
                    agent_name,
                    getattr(event, 'title', None)
                )

            if message_type == MessageType.THINKING:
                # Handle thinking content specially
                from agent.chat.content import ThinkingContent

                # Check if content is already a ThinkingContent object (new format)
                if isinstance(event.content, ThinkingContent):
                    thinking_structure = event.content
                else:
                    # Old format: content is a string
                    thinking_content = event.content
                    if thinking_content.startswith("🤔 Thinking: "):
                        thinking_content = thinking_content[len("🤔 Thinking: "):]

                    # Create StructureContent for thinking
                    thinking_structure = ThinkingContent(
                        thought=thinking_content,
                        title="Thinking Process",
                        description="Agent's thought process"
                    )

                # Add the thinking content using the standard method
                card.add_structure_content_widget(thinking_structure)
            else:
                # Handle regular content
                # Update the card with structured_content
                from agent.chat.content import TextContent
                text_structure = TextContent(text=event.content)
                self.update_agent_card(
                    event.message_id,
                    structured_content=text_structure
                )
    
    def sync_from_session(self, session):
        """Synchronize display from a stream session."""
        # For now, we'll just iterate through messages and update the cards
        # This method may need to be adapted depending on the session structure
        pass

    def clear(self):
        """Clear all messages from the chat history."""
        while self.messages:
            message_widget = self.messages.pop()
            message_widget.setParent(None)
            message_widget.deleteLater()

        self._message_cards.clear()
        self._agent_current_cards.clear()
