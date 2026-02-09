"""
Agent Chat History package.

Provides high-performance message history storage using log + index file structure.

Components:
- FastMessageHistoryService: Main service API for accessing history
- message_saved: Signal emitted when a message is successfully saved to storage
- MessageLogHistory: Low-level history manager
- MessageLogStorage: Storage engine with current/data.log + current/index.idx + history_* directories
- AgentChatHistoryListener: Auto-saves messages from signals
"""

from .agent_chat_history_service import FastMessageHistoryService, message_saved
from .agent_chat_storage import MessageLogHistory, MessageLogStorage, MessageLogArchive
from .agent_chat_history_listener import AgentChatHistoryListener

__all__ = [
    'FastMessageHistoryService',
    'message_saved',
    'MessageLogHistory',
    'MessageLogStorage',
    'MessageLogArchive',
    'AgentChatHistoryListener',
]
