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
        # Track GSN for each content item to enable smart deduplication
        self.content_gsn_map: Dict[str, int] = {}

    def add_message(self, msg_data: Dict[str, Any]) -> None:
        """Add a message to the group.

        Args:
            msg_data: Message data dictionary containing content and metadata
        """
        self.messages.append(msg_data)
        content_list = msg_data.get("content", [])

        # Get GSN for this message
        msg_gsn = msg_data.get("metadata", {}).get("gsn", 0)

        if isinstance(content_list, list):
            for content_item in content_list:
                if isinstance(content_item, dict):
                    content_id = content_item.get("content_id")
                    if content_id:
                        # Track the highest GSN for each content_id
                        if msg_gsn > self.content_gsn_map.get(content_id, 0):
                            self.content_gsn_map[content_id] = msg_gsn
                self.all_content.append(content_item)

    def get_combined_message(self) -> Optional[Dict[str, Any]]:
        """Get the combined message with all content items merged.

        Applies smart deduplication:
        1. For all content types: deduplicate by content_id
        2. For metadata content: additionally deduplicate by event_type, keeping
           only the latest version (highest GSN)

        Returns:
            A single message dictionary with combined content from all
            messages in the group, or None if the group is empty.
        """
        if not self.messages:
            return None

        # Use the first message as the base
        base_msg = dict(self.messages[0])

        # Smart deduplication
        seen_content_ids = set()
        # Track metadata event_types to their (content_id, gsn) for latest selection
        metadata_event_types: Dict[str, tuple[str, int]] = {}

        deduplicated_content = []

        for content_item in self.all_content:
            if not isinstance(content_item, dict):
                deduplicated_content.append(content_item)
                continue

            content_type = content_item.get("content_type", "")
            content_id = content_item.get("content_id", "")

            # For metadata content, apply special deduplication by event_type
            if content_type == "metadata" and content_id:
                # Get event_type from structured_content or metadata
                event_type = None
                if "structured_content" in content_item and isinstance(content_item["structured_content"], list) and len(content_item["structured_content"]) > 0:
                    first_content = content_item["structured_content"][0]
                    if isinstance(first_content, dict):
                        event_type = first_content.get("metadata", {}).get("event_type")

                if not event_type:
                    event_type = content_item.get("metadata", {}).get("event_type")

                if event_type:
                    # Get GSN for this content item
                    item_gsn = self.content_gsn_map.get(content_id, 0)

                    # Check if we've seen this event_type before
                    if event_type in metadata_event_types:
                        existing_id, existing_gsn = metadata_event_types[event_type]
                        if item_gsn > existing_gsn:
                            # This is a newer version, remove the old one
                            # Find and remove the old item from deduplicated_content
                            deduplicated_content = [
                                c for c in deduplicated_content
                                if not (isinstance(c, dict) and c.get("content_id") == existing_id)
                            ]
                            # Add the new one
                            deduplicated_content.append(content_item)
                            seen_content_ids.add(content_id)
                            metadata_event_types[event_type] = (content_id, item_gsn)
                        # else: keep the existing (newer) one, skip this older one
                        continue
                    else:
                        # First time seeing this event_type
                        metadata_event_types[event_type] = (content_id, item_gsn)

            # For non-metadata content, or metadata without event_type, use content_id deduplication
            if content_id:
                if content_id in seen_content_ids:
                    # Skip duplicate content_id
                    continue
                seen_content_ids.add(content_id)

            deduplicated_content.append(content_item)

        base_msg["content"] = deduplicated_content

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
        min_loaded_gsn: Minimum GSN among loaded messages (for loading older messages)
    """
    active_log_count: int = 0  # Number of lines in active log (legacy)
    unique_message_count: int = 0  # Number of unique messages in model
    current_line_offset: int = 0  # Current line offset in active log (legacy)
    last_seen_gsn: int = 0  # Last GSN seen by UI (primary tracking method)
    current_gsn: int = 0  # Current (latest) GSN in the system
    has_more_older: bool = True  # Whether there are more older messages
    known_message_ids: set = field(default_factory=set)  # Track message IDs in model (affected by prune)
    total_loaded_count: int = 0  # Total unique messages ever loaded (not affected by prune)
    min_loaded_gsn: int = 0  # Minimum GSN among loaded messages (for loading older)
