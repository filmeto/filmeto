"""
Agent Chat History Listener module.

Integrates with AgentChatSignals to automatically listen and save messages.
"""

import logging
from typing import Optional

from agent.chat.history.agent_chat_history_service import AgentChatHistoryService
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.agent_chat_message import AgentMessage

logger = logging.getLogger(__name__)


class AgentChatHistoryListener:
    """
    Listens to AgentChatSignals and automatically saves messages to history.

    Connects to the agent_message_send signal and persists messages
    to the history storage system.
    """

    def __init__(
        self,
        workspace_path: str,
        project_name: str,
        signals: Optional[AgentChatSignals] = None
    ):
        """
        Initialize the history listener.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            signals: Optional AgentChatSignals instance. If None, will connect to the first available.
        """
        self.workspace_path = workspace_path
        self.project_name = project_name
        self._signals = signals
        self._connected = False

    def connect(self, signals: Optional[AgentChatSignals] = None):
        """
        Connect to the AgentChatSignals.

        Args:
            signals: Optional AgentChatSignals instance. If provided, overrides the instance passed to __init__.
        """
        if signals is not None:
            self._signals = signals
        elif self._signals is None:
            logger.warning("No AgentChatSignals instance provided to connect")
            return

        self._signals.connect(self._on_message_send)
        self._connected = True
        logger.debug(f"HistoryListener connected for project {self.project_name}")

    def disconnect(self):
        """Disconnect from the AgentChatSignals."""
        if self._signals and self._connected:
            self._signals.disconnect(self._on_message_send)
            self._connected = False
            logger.debug(f"HistoryListener disconnected for project {self.project_name}")

    def _on_message_send(self, sender, message: AgentMessage):
        """
        Handle incoming message signal and save to history.

        Args:
            sender: The signal sender (typically the AgentChatSignals instance)
            message: The AgentMessage to save
        """
        try:
            # Skip system messages if needed
            if message.message_type.value == "system":
                # Optional: Filter out certain system messages
                pass

            # Save message to history
            file_path = AgentChatHistoryService.add_message(
                self.workspace_path,
                self.project_name,
                message,
                append_content=True  # Append content for same message_id
            )

            logger.debug(f"Saved message {message.message_id} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save message to history: {e}", exc_info=True)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
