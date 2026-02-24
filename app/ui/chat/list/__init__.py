"""Agent chat list component package.

This package provides a virtualized chat list widget using QML for
hardware-accelerated 60 FPS rendering with Qt Quick.

The QML implementation offers:
- Dynamic heights with automatic layout
- Pixel-perfect smooth scrolling
- Built-in virtualization for 100k+ messages
- Component-based message delegates
- Declarative animations

Architecture:
- Storage layer: Returns raw messages as stored (no merging)
- MessageBuilder: Handles ALL grouping and merging logic for consistency
- HistoryManager: Coordinates loading and delegates to MessageBuilder

Modules:
- agent_chat_list_items: Data classes
- agent_chat_list_model: QML-compatible Qt model
- agent_chat_list_widget: QML-based widget (refactored with components)

Components:
- handlers: QML and stream event handlers
- managers: History, skill, metadata, and scroll managers
- builders: Message construction utilities
"""

from app.ui.chat.list.agent_chat_list_items import (
    ChatListItem,
    LoadState,
)

# QML-based implementation
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget

# Refactored components (available for direct use if needed)
from app.ui.chat.list.handlers import QmlHandler, StreamEventHandler
from app.ui.chat.list.managers import (
    HistoryManager,
    SkillManager,
    MetadataResolver,
    ScrollManager,
)
from app.ui.chat.list.builders import MessageBuilder

__all__ = [
    # Data classes
    "ChatListItem",
    "LoadState",
    # QML-based
    "QmlAgentChatListModel",
    "QmlAgentChatListWidget",
    # Components (for advanced usage)
    "QmlHandler",
    "StreamEventHandler",
    "HistoryManager",
    "SkillManager",
    "MetadataResolver",
    "ScrollManager",
    "MessageBuilder",
]
