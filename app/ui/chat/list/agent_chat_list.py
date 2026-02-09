"""Agent chat list component using QML for hardware-accelerated rendering.

This module provides backward compatibility by re-exporting the QML-based classes.

QML Implementation Benefits:
- Dynamic heights with automatic layout
- Pixel-perfect smooth scrolling (60 FPS)
- Built-in virtualization for 100k+ messages
- Component-based message delegates
- Declarative animations
"""

# Data classes
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
