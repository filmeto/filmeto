"""Agent chat list component package.

This package provides a virtualized chat list widget using QListView
for efficient rendering of agent conversations.

The package is split into multiple modules:
- agent_chat_list_items: Data classes and helpers
- agent_chat_list_model: Qt model for chat items
- agent_chat_list_delegate: Qt delegate for rendering
- agent_chat_list_view: Custom QListView with smooth scrolling
- agent_chat_list_widget: Main widget with all logic
- agent_chat_list: Backward compatibility (imports from split files)
"""

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
