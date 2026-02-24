"""Builder classes for constructing chat list items.

This package contains components that:
- Build QML model items from history data
- Handle message content merging
"""

from app.ui.chat.list.builders.message_builder import MessageBuilder

__all__ = [
    "MessageBuilder",
]
