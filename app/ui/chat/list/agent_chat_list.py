"""Agent chat list component using QML for hardware-accelerated rendering.

This module provides backward compatibility by re-exporting all classes.
The QML-based implementation is now the default:
- qml_agent_chat_list_model: QML-compatible Qt model
- qml_agent_chat_list_widget: QML-based widget with 60 FPS rendering

Legacy QWidget implementation is available as a fallback:
- agent_chat_list_items: Data classes and helpers
- agent_chat_list_model: Legacy Qt model
- agent_chat_list_delegate: Qt delegate for rendering
- agent_chat_list_view: Custom QListView with smooth scrolling
- agent_chat_list_widget: Main QWidget implementation

QML Implementation Benefits:
- Dynamic heights with automatic layout
- Pixel-perfect smooth scrolling (60 FPS)
- Built-in virtualization for 100k+ messages
- Component-based message delegates
- Declarative animations
"""

# Data classes (shared by both implementations)
from app.ui.chat.list.agent_chat_list_items import (
    ChatListItem,
    MessageGroup,
    LoadState,
)

# QML-based implementation (default)
from app.ui.chat.list.qml_agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.qml_agent_chat_list_widget import QmlAgentChatListWidget

# Legacy QWidget implementation (fallback)
from app.ui.chat.list.agent_chat_list_model import AgentChatListModel
from app.ui.chat.list.agent_chat_list_delegate import AgentChatListDelegate
from app.ui.chat.list.agent_chat_list_view import AgentChatListView
from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget as LegacyAgentChatListWidget

# Use QML implementation by default
AgentChatListWidget = QmlAgentChatListWidget

__all__ = [
    # Data classes (shared)
    "ChatListItem",
    "MessageGroup",
    "LoadState",
    # QML-based (recommended, default)
    "QmlAgentChatListModel",
    "QmlAgentChatListWidget",
    "AgentChatListWidget",  # Points to QML version
    # Legacy QWidget (fallback)
    "AgentChatListModel",
    "LegacyAgentChatListWidget",
    "AgentChatListDelegate",
    "AgentChatListView",
]
