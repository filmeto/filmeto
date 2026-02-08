"""Agent chat list component package.

This package provides a QML-based virtualized chat list widget with:
- Hardware-accelerated 60 FPS rendering with Qt Quick
- Dynamic heights with automatic layout
- Pixel-perfect smooth scrolling
- Built-in virtualization for 100k+ messages
- Component-based message delegates
- Declarative animations

Modules:
- agent_chat_list_items: Data classes and helpers
- qml_agent_chat_list_model: QML-compatible Qt model
- qml_agent_chat_list_widget: QML-based widget
- agent_chat_list: Public API exports
"""

from app.ui.chat.list.agent_chat_list_items import (
    ChatListItem,
    MessageGroup,
    LoadState,
)

# QML-based implementation
from app.ui.chat.list.qml_agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.qml_agent_chat_list_widget import QmlAgentChatListWidget

# Public API
AgentChatListWidget = QmlAgentChatListWidget

__all__ = [
    # Data classes
    "ChatListItem",
    "MessageGroup",
    "LoadState",
    # QML-based implementation
    "QmlAgentChatListModel",
    "QmlAgentChatListWidget",
    "AgentChatListWidget",
]
