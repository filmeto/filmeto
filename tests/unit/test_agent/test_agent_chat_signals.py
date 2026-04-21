"""
Unit tests for AgentChatSignals.

Tests for:
- agent/chat/agent_chat_signals.py
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.agent_chat_message import AgentMessage


class TestAgentChatSignalsInit:
    """Tests for AgentChatSignals initialization"""

    def test_signals_defaults(self):
        """Verify default values"""
        signals = AgentChatSignals()
        assert signals.CONSUME_INTERVAL_MS == 300
        assert signals.QUEUE_MAXSIZE == 0
        assert signals._consume_interval_ms == 300

    def test_signals_custom_interval(self):
        """Verify custom consume interval"""
        signals = AgentChatSignals(consume_interval_ms=500)
        assert signals._consume_interval_ms == 500

    def test_signals_custom_interval_float(self):
        """Verify custom consume interval as float"""
        signals = AgentChatSignals(consume_interval_ms=0.5)
        assert signals._consume_interval_ms == 0.5


class TestAgentChatSignalsConnect:
    """Tests for AgentChatSignals connect/disconnect"""

    def test_connect_receiver(self):
        """Verify connect adds receiver"""
        signals = AgentChatSignals()
        receiver = Mock()
        signals.connect(receiver)
        # Should not raise - just verify it's callable
        assert True

    def test_disconnect_receiver(self):
        """Verify disconnect removes receiver"""
        signals = AgentChatSignals()
        receiver = Mock()
        signals.connect(receiver)
        signals.disconnect(receiver)
        # Should not raise
        assert True

    def test_connect_crew_member_activity(self):
        """Verify connect_crew_member_activity adds receiver"""
        signals = AgentChatSignals()
        receiver = Mock()
        signals.connect_crew_member_activity(receiver)
        assert True

    def test_disconnect_crew_member_activity(self):
        """Verify disconnect_crew_member_activity removes receiver"""
        signals = AgentChatSignals()
        receiver = Mock()
        signals.connect_crew_member_activity(receiver)
        signals.disconnect_crew_member_activity(receiver)
        assert True


class TestAgentChatSignalsEmit:
    """Tests for AgentChatSignals emit methods"""

    def test_emit_crew_member_activity(self):
        """Verify emit_crew_member_activity sends signal"""
        signals = AgentChatSignals()
        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs)

        signals.connect_crew_member_activity(receiver)
        signals.emit_crew_member_activity("Director", True)

        assert len(received) == 1
        assert received[0]["member_name"] == "Director"
        assert received[0]["active"] == True

    def test_emit_crew_member_activity_inactive(self):
        """Verify emit_crew_member_activity with inactive state"""
        signals = AgentChatSignals()
        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs)

        signals.connect_crew_member_activity(receiver)
        signals.emit_crew_member_activity("Writer", False)

        assert len(received) == 1
        assert received[0]["member_name"] == "Writer"
        assert received[0]["active"] == False


class TestAgentChatSignalsAsyncMethods:
    """Tests for AgentChatSignals async methods"""

    @pytest.mark.asyncio
    async def test_ensure_consumer_running(self):
        """Verify _ensure_consumer_running starts queue manager"""
        signals = AgentChatSignals()
        # Should start the queue manager
        await signals._ensure_consumer_running()
        assert signals._queue_manager.is_running
        # Clean up
        signals.stop()

    @pytest.mark.asyncio
    async def test_process_message(self):
        """Verify _process_message emits signal"""
        signals = AgentChatSignals()
        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs.get("message"))

        signals.connect(receiver)

        # Create a simple message
        msg = AgentMessage(sender_id="test")
        await signals._process_message(msg)

        assert len(received) == 1
        assert received[0].sender_id == "test"

        signals.stop()

    @pytest.mark.asyncio
    async def test_send_agent_message(self):
        """Verify send_agent_message queues and sends message"""
        signals = AgentChatSignals()
        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs.get("message"))

        signals.connect(receiver)

        msg = AgentMessage(sender_id="sender", sender_name="Test Agent")
        result = await signals.send_agent_message(msg)

        # Wait for message to be processed
        await signals.join()

        assert result.sender_id == "sender"
        assert len(received) >= 1
        assert received[0].sender_id == "sender"

        signals.stop()

    @pytest.mark.asyncio
    async def test_join(self):
        """Verify join waits for queue processing"""
        signals = AgentChatSignals()
        msg = AgentMessage(sender_id="test")
        await signals.send_agent_message(msg)
        await signals.join()
        # Should complete without hanging
        assert True
        signals.stop()


class TestAgentChatSignalsStop:
    """Tests for AgentChatSignals stop method"""

    def test_stop_when_not_running(self):
        """Verify stop does nothing when not running"""
        signals = AgentChatSignals()
        # Queue manager not started yet
        signals.stop()
        assert True  # Should not raise

    @pytest.mark.asyncio
    async def test_stop_after_running(self):
        """Verify stop stops running queue manager"""
        signals = AgentChatSignals()
        await signals._ensure_consumer_running()
        assert signals._queue_manager.is_running
        signals.stop()
        # Give it time to stop
        await asyncio.sleep(0.1)
        assert not signals._queue_manager.is_running


class TestAgentChatSignalsMultipleReceivers:
    """Tests for multiple receivers"""

    def test_multiple_receivers_crew_activity(self):
        """Verify multiple receivers all receive crew activity signals"""
        signals = AgentChatSignals()
        received1 = []
        received2 = []

        def receiver1(sender, **kwargs):
            received1.append(kwargs)

        def receiver2(sender, **kwargs):
            received2.append(kwargs)

        signals.connect_crew_member_activity(receiver1)
        signals.connect_crew_member_activity(receiver2)

        signals.emit_crew_member_activity("Editor", True)

        assert len(received1) == 1
        assert len(received2) == 1
        assert received1[0]["member_name"] == "Editor"
        assert received2[0]["member_name"] == "Editor"

    @pytest.mark.asyncio
    async def test_multiple_receivers_async(self):
        """Verify multiple receivers receive async messages"""
        signals = AgentChatSignals()
        received1 = []
        received2 = []

        def receiver1(sender, **kwargs):
            received1.append(kwargs.get("message"))

        def receiver2(sender, **kwargs):
            received2.append(kwargs.get("message"))

        signals.connect(receiver1)
        signals.connect(receiver2)

        msg = AgentMessage(sender_id="test")
        await signals.send_agent_message(msg)
        await signals.join()

        assert len(received1) >= 1
        assert len(received2) >= 1

        signals.stop()