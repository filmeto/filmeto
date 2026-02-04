"""
Agent Chat Signals Module

This module provides a singleton class AgentChatSignals that manages
blinker signals for agent chat functionality.
"""

import asyncio
import blinker

from .agent_chat_message import AgentMessage


class AgentChatSignals:
    """
    Provides blinker signals for agent chat functionality.

    Note: Previously this was a singleton, but now instances should be
    created by FilmetoAgent and passed to other components.

    Messages are queued and consumed at a constant rate (100ms per message)
    to ensure stable UI rendering performance.
    """

    # Constant rate for message consumption (100ms per message)
    CONSUME_INTERVAL_MS = 300

    def __init__(self):
        self.__agent_message_send = blinker.Signal()
        self._message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._consumer_task: asyncio.Task | None = None
        self._running = False
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

    def _ensure_consumer_running(self) -> None:
        """
        Ensure the consumer task is running. Starts it if not already running.
        """
        if self._consumer_task is None or self._consumer_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._loop = loop
                if self._consumer_task is None or self._consumer_task.done():
                    self._running = True
                    self._consumer_task = loop.create_task(self._consume_messages())
            except RuntimeError:
                # No event loop running yet
                pass

    async def _consume_messages(self) -> None:
        """
        Consumer task that processes messages at a constant rate.

        Pulls one message every CONSUME_INTERVAL_MS and sends it via blinker signal.
        This ensures UI rendering performance is not affected by message bursts.
        """
        while self._running:
            try:
                # Wait for a message with timeout
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=0.1
                )

                # Send the message via blinker signal
                self.__agent_message_send.send(self, message=message)

                # Mark as done
                self._message_queue.task_done()

                # Wait for the constant interval before processing next message
                await asyncio.sleep(self.CONSUME_INTERVAL_MS / 1000.0)

            except asyncio.TimeoutError:
                # No message available, continue waiting
                continue
            except asyncio.CancelledError:
                # Handle cancellation gracefully
                break
            except Exception as e:
                # Log error but continue processing
                print(f"Error in message consumer: {e}")
                try:
                    self._message_queue.task_done()
                except ValueError:
                    pass

    async def send_agent_message(self, message: AgentMessage) -> AgentMessage:
        """
        Send an AgentMessage via the blinker signal.

        The message is placed in a queue and consumed at a constant rate
        (100ms per message) to ensure stable UI rendering performance.

        Args:
            message: The AgentMessage to send.

        Returns:
            The same AgentMessage that was sent.
        """
        # Ensure consumer is running
        self._ensure_consumer_running()

        # Put message in queue for consumption
        await self._message_queue.put(message)
        return message

    async def join(self) -> None:
        """
        Wait until all messages in the queue are processed.
        """
        await self._message_queue.join()

    def stop(self) -> None:
        """
        Stop the consumer task gracefully.
        """
        self._running = False
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
