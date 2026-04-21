"""
Unit tests for agent/core/filmeto_routing.py

Tests routing manager functionality including:
- MAX_ROUTING_DEPTH constant
- FilmetoRoutingManager: Message routing and crew member streaming
- Loop protection with depth and visited_senders
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from agent.core.filmeto_routing import (
    MAX_ROUTING_DEPTH,
    FilmetoRoutingManager,
)


class TestMaxRoutingDepth:
    """Tests for MAX_ROUTING_DEPTH constant."""

    def test_max_routing_depth_is_5(self):
        """MAX_ROUTING_DEPTH should be 5."""
        assert MAX_ROUTING_DEPTH == 5

    def test_max_routing_depth_is_integer(self):
        """MAX_ROUTING_DEPTH should be an integer."""
        assert isinstance(MAX_ROUTING_DEPTH, int)


class TestFilmetoRoutingManagerInit:
    """Tests for FilmetoRoutingManager initialization."""

    def test_init_sets_crew_manager(self):
        """FilmetoRoutingManager sets crew manager."""
        mock_crew_manager = Mock()
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )
        assert manager._crew_manager is mock_crew_manager

    def test_init_sets_message_router(self):
        """FilmetoRoutingManager sets message router."""
        mock_crew_manager = Mock()
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )
        assert manager._message_router is mock_router

    def test_init_sets_signals(self):
        """FilmetoRoutingManager sets signals."""
        mock_crew_manager = Mock()
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )
        assert manager._signals is mock_signals

    def test_init_sets_conversation_history(self):
        """FilmetoRoutingManager sets conversation history."""
        mock_crew_manager = Mock()
        mock_router = Mock()
        mock_signals = Mock()
        history = [{"id": "msg1"}]

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )
        assert manager._conversation_history is history

    def test_init_creates_empty_routing_state(self):
        """FilmetoRoutingManager creates empty routing state dict."""
        mock_crew_manager = Mock()
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )
        assert manager._routing_state == {}


class TestFilmetoRoutingManagerRouteMessageWithLLM:
    """Tests for FilmetoRoutingManager.route_message_with_llm method."""

    @pytest.mark.asyncio
    async def test_route_terminates_at_max_depth(self):
        """Routing terminates when depth reaches MAX_ROUTING_DEPTH."""
        mock_crew_manager = Mock()
        mock_crew_manager.crew_members = {}
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )

        # Should return without calling router when depth >= MAX_ROUTING_DEPTH
        await manager.route_message_with_llm(
            message="test",
            sender_id="sender1",
            sender_name="Sender",
            session_id="session1",
            _routing_depth=MAX_ROUTING_DEPTH,
        )

        # Router should not be called
        mock_router.route_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_terminates_on_cycle(self):
        """Routing terminates when sender already in visited_senders."""
        mock_crew_manager = Mock()
        mock_crew_manager.crew_members = {}
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )

        # Sender already in visited set - should terminate
        await manager.route_message_with_llm(
            message="test",
            sender_id="sender1",
            sender_name="Sender",
            session_id="session1",
            _visited_senders=frozenset(["sender1", "sender2"]),
        )

        mock_router.route_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_adds_sender_to_visited(self):
        """route_message_with_llm adds sender to visited_senders."""
        mock_crew_manager = Mock()
        mock_crew_manager.crew_members = {}
        mock_crew_manager.get_producer.return_value = None
        mock_router = Mock()
        mock_router.route_message = AsyncMock(return_value=Mock(routed_members=[], member_messages={}))
        mock_signals = Mock()
        mock_signals.send_agent_message = AsyncMock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )

        await manager.route_message_with_llm(
            message="test",
            sender_id="sender1",
            sender_name="Sender",
            session_id="session1",
            _visited_senders=frozenset(),
        )

        # Router should be called with updated visited_senders
        # The actual routing logic adds sender1 to visited
        mock_router.route_message.assert_called()


class TestFilmetoRoutingManagerCreateContentFromEvent:
    """Tests for FilmetoRoutingManager._create_content_from_event method."""

    def test_create_content_from_event_returns_none_for_unknown(self):
        """_create_content_from_event returns None for unknown event types."""
        mock_crew_manager = Mock()
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )

        from agent.react import AgentEventType
        event = Mock(
            event_type="unknown_type",
            payload={},
        )
        content_tracking = {}

        result = manager._create_content_from_event(event, content_tracking)
        assert result is None


class TestFilmetoRoutingManagerDispatchToMembers:
    """Tests for FilmetoRoutingManager._dispatch_to_members method."""

    @pytest.mark.asyncio
    async def test_dispatch_to_members_creates_tasks(self):
        """_dispatch_to_members creates async tasks for each member."""
        mock_crew_manager = Mock()
        mock_member = Mock()
        mock_member.config.name = "member1"
        mock_crew_manager.get_member.return_value = mock_member
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )

        # Mock stream_crew_member to be async generator
        async def mock_stream(*args, **kwargs):
            yield Mock()

        manager.stream_crew_member = mock_stream

        decision = Mock(
            routed_members=["member1"],
            member_messages={"member1": "hello"},
        )

        await manager._dispatch_to_members(decision, "test message", "session1")

        mock_crew_manager.get_member.assert_called_with("member1")


class TestFilmetoRoutingManagerEmitCrewMemberRead:
    """Tests for FilmetoRoutingManager._emit_crew_member_read method."""

    @pytest.mark.asyncio
    async def test_emit_crew_member_read_sends_message(self):
        """_emit_crew_member_read sends read content message."""
        mock_crew_manager = Mock()
        mock_member = Mock()
        mock_member.config.name = "member1"
        mock_member.config.icon = "icon"
        mock_member.config.color = "blue"
        mock_crew_manager.get_member.return_value = mock_member

        mock_router = Mock()
        mock_signals = Mock()
        mock_signals.send_agent_message = AsyncMock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )

        await manager._emit_crew_member_read(
            routed_members=["member1"],
            sender_id="sender1",
            sender_name="Sender",
            user_message_id="msg_id",
            session_id="session1",
        )

        mock_signals.send_agent_message.assert_called_once()


class TestFilmetoRoutingManagerHandleCrewMemberMessage:
    """Tests for FilmetoRoutingManager._handle_crew_member_message method."""

    @pytest.mark.asyncio
    async def test_handle_crew_member_message_empty_text_returns(self):
        """_handle_crew_member_message returns when message is empty."""
        mock_crew_manager = Mock()
        mock_router = Mock()
        mock_signals = Mock()
        history = []

        manager = FilmetoRoutingManager(
            mock_crew_manager, mock_router, mock_signals, history
        )

        content = Mock(metadata={"message": "", "mode": "public"})
        event = Mock(sender_id="sender1")

        await manager._handle_crew_member_message(event, content, "session1")

        # No routing should occur
        mock_router.route_message.assert_not_called()