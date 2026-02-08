"""
Agent Chat History Listener module.

Integrates with AgentChatSignals to automatically listen and save messages.

Uses FastMessageHistoryService for high-performance message log storage.
"""

import logging
from typing import Optional

from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.agent_chat_message import AgentMessage

logger = logging.getLogger(__name__)


class AgentChatHistoryListener:
    """
    Listens to AgentChatSignals and automatically saves messages to history.

    Connects to the agent_message_send signal and persists messages
    to the history storage system using FastMessageHistoryService.
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
            # Check if message should be filtered (e.g., certain system messages)
            from agent.chat.agent_chat_types import ContentType
            primary_type = message.get_primary_content_type()
            if primary_type == ContentType.METADATA:
                # Optional: Filter out certain metadata messages
                event_type = message.metadata.get("event_type", "")
                if event_type in ("producer_start", "crew_member_start", "responding_agent_start"):
                    # Skip these system event messages
                    return

            # Save message to history using FastMessageHistoryService
            success = FastMessageHistoryService.add_message(
                self.workspace_path,
                self.project_name,
                message
            )

            if success:
                logger.debug(f"Saved message {message.message_id} to message.log")
            else:
                logger.warning(f"Failed to save message {message.message_id}")

        except Exception as e:
            logger.error(f"Failed to save message to history: {e}", exc_info=True)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
