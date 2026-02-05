"""Compatibility wrapper for the virtualized chat list."""

from app.ui.chat.list.agent_chat_list import AgentChatListWidget


class AgentChatHistoryWidget(AgentChatListWidget):
    """Deprecated: use AgentChatListWidget instead."""

    pass
