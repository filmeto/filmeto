"""
Agent Chat Signals Module

This module provides a singleton class AgentChatSignals that manages
blinker signals for agent chat functionality.
"""

import blinker

from .agent_chat_message import AgentMessage


class AgentChatSignals:
    """
    Provides blinker signals for agent chat functionality.

    Note: Previously this was a singleton, but now instances should be
    created by FilmetoAgent and passed to other components.
    """

    def __init__(self):
        self.__agent_message_send = blinker.Signal()

    def connect(self, receiver, weak: bool = True):
        """
        Connect a receiver function to the agent_message_send signal.

        Args:
            receiver: A function that receives the signal
            weak: Whether to use a weak reference (default True)
        """
        self.__agent_message_send.connect(receiver, weak=weak)

    def disconnect(self, receiver):
        """
        Disconnect a receiver function from the agent_message_send signal.

        Args:
            receiver: The function to disconnect
        """
        self.__agent_message_send.disconnect(receiver)

    async def send_agent_message(self, message: AgentMessage) -> AgentMessage:
        """
        Send an AgentMessage via the blinker signal.

        Args:
            message: The AgentMessage to send.

        Returns:
            The same AgentMessage that was sent.
        """
        self.__agent_message_send.send(self, message=message)
        return message
