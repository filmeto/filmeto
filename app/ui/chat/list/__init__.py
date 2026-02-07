"""Agent chat list component package.

This package provides a virtualized chat list widget with two implementations:
- QML-based (default): Hardware-accelerated 60 FPS rendering with Qt Quick
- QWidget-based: Traditional Qt Widgets implementation (fallback)

The QML implementation offers:
- Dynamic heights with automatic layout
- Pixel-perfect smooth scrolling
- Built-in virtualization for 100k+ messages
- Component-based message delegates
- Declarative animations

Modules:
- agent_chat_list_items: Data classes and helpers
- qml_agent_chat_list_model: QML-compatible Qt model
- qml_agent_chat_list_widget: QML-based widget (default)
- agent_chat_list_model: Legacy Qt model
- agent_chat_list_widget: Legacy QWidget implementation (fallback)
- agent_chat_list: Backward compatibility layer

To use the legacy QWidget implementation:
    from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget as LegacyChatListWidget
"""

from app.ui.chat.list.agent_chat_list_items import (
    ChatListItem,
    MessageGroup,
    LoadState,
)

# QML-based implementation (default)
from app.ui.chat.list.qml_agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.qml_agent_chat_list_widget import QmlAgentChatListWidget

# Legacy QWidget implementation (available as fallback)
from app.ui.chat.list.agent_chat_list_model import AgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget as LegacyAgentChatListWidget
from app.ui.chat.list.agent_chat_list_delegate import AgentChatListDelegate
from app.ui.chat.list.agent_chat_list_view import AgentChatListView

# Use QML implementation by default
AgentChatListWidget = QmlAgentChatListWidget

__all__ = [
    # Data classes
    "ChatListItem",
    "MessageGroup",
    "LoadState",
    # QML-based (recommended)
    "QmlAgentChatListModel",
    "QmlAgentChatListWidget",
    "AgentChatListWidget",  # Points to QML version
    # Legacy QWidget (fallback)
    "AgentChatListModel",
    "LegacyAgentChatListWidget",
    "AgentChatListDelegate",
    "AgentChatListView",
]
