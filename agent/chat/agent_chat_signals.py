"""
Agent Chat Signals Module

This module provides a singleton class AgentChatSignals that manages
blinker signals for agent chat functionality.
"""

import asyncio
import logging
import blinker

from .agent_chat_message import AgentMessage
from utils.queue_utils import AsyncQueueManager

logger = logging.getLogger(__name__)


class AgentChatSignals:
    """
    Provides blinker signals for agent chat functionality.

    Note: Previously this was a singleton, but now instances should be
    created by FilmetoAgent and passed to other components.

    Messages are queued and consumed at a constant rate
    to ensure stable UI rendering performance.
    """

    # Constant rate for message consumption (ms per message)
    CONSUME_INTERVAL_MS = 300
    QUEUE_MAXSIZE = 0

    def __init__(self, consume_interval_ms: int | float | None = None):
        self.__agent_message_send = blinker.Signal()
        self._consume_interval_ms = (
            self.CONSUME_INTERVAL_MS if consume_interval_ms is None else consume_interval_ms
        )
        self._queue_manager = AsyncQueueManager(
            processor=self._process_message,
            maxsize=self.QUEUE_MAXSIZE,
            max_concurrent=1,
            name="AgentChatSignals",
            consume_interval_ms=self._consume_interval_ms,
        )
        self._loop: asyncio.AbstractEventLoop | None = None

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

    async def _ensure_consumer_running(self) -> None:
        """
        Ensure the consumer is running. Starts it if not already running.
        """
        if not self._queue_manager.is_running:
            self._loop = asyncio.get_running_loop()
            await self._queue_manager.start()
        elif self._loop is None:
            self._loop = asyncio.get_running_loop()

    async def _process_message(self, message: AgentMessage) -> None:
        """
        Process a single message and emit it via blinker signal.
        """
        self.__agent_message_send.send(self, message=message)

    async def send_agent_message(self, message: AgentMessage) -> AgentMessage:
        """
        Send an AgentMessage via the blinker signal.

        The message is placed in a queue and consumed at a constant rate
        to ensure stable UI rendering performance.

        Args:
            message: The AgentMessage to send.

        Returns:
            The same AgentMessage that was sent.
        """
        # Ensure consumer is running
        await self._ensure_consumer_running()

        # Put message in queue for consumption
        await self._queue_manager.put_async(message)
        return message

    async def join(self) -> None:
        """
        Wait until all messages in the queue are processed.
        """
        await self._queue_manager.join()

    def stop(self) -> None:
        """
        Stop the consumer task gracefully.
        """
        if not self._queue_manager.is_running:
            return
        if self._loop and self._loop.is_running():
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            if running_loop is self._loop:
                self._loop.create_task(self._queue_manager.stop())
            else:
                asyncio.run_coroutine_threadsafe(self._queue_manager.stop(), self._loop)
