"""Agent chat list component package.

This package provides a virtualized chat list widget using QML for
hardware-accelerated 60 FPS rendering with Qt Quick.

The QML implementation offers:
- Dynamic heights with automatic layout
- Pixel-perfect smooth scrolling
- Built-in virtualization for 100k+ messages
- Component-based message delegates
- Declarative animations

Modules:
- agent_chat_list_items: Data classes and helpers
- qml_agent_chat_list_model: QML-compatible Qt model
- qml_agent_chat_list_widget: QML-based widget
- agent_chat_list: Backward compatibility layer
"""

from app.ui.chat.list.agent_chat_list_items import (
    ChatListItem,
    MessageGroup,
    LoadState,
)

# QML-based implementation
from app.ui.chat.list.qml_agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.qml_agent_chat_list_widget import QmlAgentChatListWidget

# Use QML implementation
AgentChatListWidget = QmlAgentChatListWidget

__all__ = [
    # Data classes
    "ChatListItem",
    "MessageGroup",
    "LoadState",
    # QML-based
    "QmlAgentChatListModel",
    "QmlAgentChatListWidget",
    "AgentChatListWidget",  # Points to QML version
]
