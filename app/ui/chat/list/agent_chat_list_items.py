"""Data classes and helper classes for agent chat list.

This module contains the data structures used by the agent chat list components:
- ChatListItem: Data class for a single chat message item
- MessageGroup: Helper class for grouping messages by message_id
- LoadState: Data class for tracking loading state
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agent import AgentMessage


@dataclass
class ChatListItem:
    """Data class representing a single chat message item in the list.

    Attributes:
        message_id: Unique identifier for this message
        sender_id: ID of the message sender
        sender_name: Display name of the sender
        is_user: Whether this is a user message
        user_content: Text content for user messages
        agent_message: Full agent message for non-user messages
        agent_color: Display color for the agent
        agent_icon: Display icon for the agent
        crew_member_metadata: Additional metadata about the crew member
    """
    message_id: str
    sender_id: str
    sender_name: str
    is_user: bool
    user_content: str = ""
    agent_message: Optional["AgentMessage"] = None
    agent_color: str = "#4a90e2"
    agent_icon: str = "🤖"
    crew_member_metadata: Dict[str, Any] = field(default_factory=dict)


class MessageGroup:
    """Helper class to group messages by message_id and combine content.

    When multiple log entries share the same message_id (e.g., a streaming
    response that was logged in chunks), this class groups them together
    and combines their content into a single message.
    """

    def __init__(self) -> None:
        """Initialize an empty message group."""
        self.messages: List[Dict[str, Any]] = []
        self.all_content: List[Dict[str, Any]] = []

    def add_message(self, msg_data: Dict[str, Any]) -> None:
        """Add a message to the group.

        Args:
            msg_data: Message data dictionary containing content and metadata
        """
        self.messages.append(msg_data)
        content_list = msg_data.get("content", [])
        if isinstance(content_list, list):
            self.all_content.extend(content_list)

    def get_combined_message(self) -> Optional[Dict[str, Any]]:
        """Get the combined message with all content items merged.

        Returns:
            A single message dictionary with combined content from all
            messages in the group, or None if the group is empty.
        """
        if not self.messages:
            return None

        # Use the first message as the base
        base_msg = dict(self.messages[0])

        # Combine all content items
        base_msg["content"] = self.all_content

        return base_msg


@dataclass
class LoadState:
    """Track the current loading state for efficient pagination.

    This dataclass maintains the state needed for efficient pagination
    when loading messages from history.

    Enhanced with GSN (Global Sequence Number) support for archive-aware
    message tracking. The GSN is maintained across all archives, allowing
    the UI to correctly fetch new messages even after archiving operations.

    Attributes:
        active_log_count: Number of lines in the active log file (legacy, kept for compatibility)
        unique_message_count: Number of unique messages currently in the model
        current_line_offset: Current line offset in the active log (legacy, kept for compatibility)
        last_seen_gsn: The last Global Sequence Number seen by the UI (primary tracking method)
        current_gsn: The current (latest) GSN in the system
        has_more_older: Whether there are more older messages available
        known_message_ids: Set of message IDs currently in the model (affected by prune)
        total_loaded_count: Total unique messages ever loaded (not affected by prune)
    """
    active_log_count: int = 0  # Number of lines in active log (legacy)
    unique_message_count: int = 0  # Number of unique messages in model
    current_line_offset: int = 0  # Current line offset in active log (legacy)
    last_seen_gsn: int = 0  # Last GSN seen by UI (primary tracking method)
    current_gsn: int = 0  # Current (latest) GSN in the system
    has_more_older: bool = True  # Whether there are more older messages
    known_message_ids: set = field(default_factory=set)  # Track message IDs in model (affected by prune)
    total_loaded_count: int = 0  # Total unique messages ever loaded (not affected by prune)
