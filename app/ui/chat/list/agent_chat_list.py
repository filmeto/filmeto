"""Agent chat list component using QListView for virtualized rendering.

This module provides backward compatibility by re-exporting all classes
from the split modules. The actual implementation is now in:
- agent_chat_list_items: Data classes and helpers
- agent_chat_list_model: Qt model for chat items
- agent_chat_list_delegate: Qt delegate for rendering
- agent_chat_list_view: Custom QListView with smooth scrolling
- agent_chat_list_widget: Main widget with all logic

Optimized to leverage FastMessageHistoryService capabilities:
- Message grouping by message_id for unified display
- Page-based initial loading with unique message count
- Efficient pagination using line offsets
- Smart polling using active log count only
- Virtualized widget management for performance
- Cached history instance for reduced overhead
"""

# Import all classes from the split modules for backward compatibility
from app.ui.chat.list.agent_chat_list_items import (
    ChatListItem,
    MessageGroup,
    LoadState,
)
from app.ui.chat.list.agent_chat_list_model import AgentChatListModel
from app.ui.chat.list.agent_chat_list_delegate import AgentChatListDelegate
from app.ui.chat.list.agent_chat_list_view import AgentChatListView
from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget

__all__ = [
    "ChatListItem",
    "MessageGroup",
    "LoadState",
    "AgentChatListModel",
    "AgentChatListDelegate",
    "AgentChatListView",
    "AgentChatListWidget",
]
