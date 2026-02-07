"""
Agent Chat History package.

Provides high-performance message history storage using message.log files.

Components:
- FastMessageHistoryService: Main service API for accessing history
- MessageLogHistory: Low-level history manager
- MessageLogStorage: Storage engine with message.log + history_*.log files
- AgentChatHistoryListener: Auto-saves messages from signals
"""

from .agent_chat_history_service import FastMessageHistoryService
from .agent_chat_storage import MessageLogHistory, MessageLogStorage, MessageLogArchive
from .agent_chat_history_listener import AgentChatHistoryListener

__all__ = [
    'FastMessageHistoryService',
    'MessageLogHistory',
    'MessageLogStorage',
    'MessageLogArchive',
    'AgentChatHistoryListener',
]
