"""
Unit tests for app/ui/core/event_bus.py

Tests EventBus singleton functionality including:
- Singleton pattern implementation
- Signal emission methods
- Reset functionality
"""

import pytest
from unittest.mock import Mock
from PySide6.QtCore import QObject
from app.ui.core.event_bus import EventBus


class TestEventBusSingleton:
    """Tests for EventBus singleton pattern."""

    def test_instance_returns_same_object(self):
        """instance() returns the same EventBus object each time."""
        EventBus.reset()
        bus1 = EventBus.instance()
        bus2 = EventBus.instance()
        assert bus1 is bus2

    def test_instance_creates_singleton(self):
        """instance() creates singleton on first call."""
        EventBus.reset()
        bus = EventBus.instance()
        assert bus is not None
        assert isinstance(bus, QObject)

    def test_direct_construction_raises_error(self):
        """Direct construction raises RuntimeError."""
        EventBus.reset()
        EventBus.instance()  # Create singleton first
        with pytest.raises(RuntimeError):
            EventBus()  # Should raise

    def test_instance_thread_safety(self):
        """Singleton creation is thread-safe."""
        import threading

        EventBus.reset()
        buses = []

        def get_bus():
            buses.append(EventBus.instance())

        threads = [threading.Thread(target=get_bus) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance
        assert all(b is buses[0] for b in buses)


class TestEventBusReset:
    """Tests for EventBus.reset method."""

    def test_reset_clears_instance(self):
        """reset() clears the singleton instance."""
        bus1 = EventBus.instance()
        EventBus.reset()
        bus2 = EventBus.instance()
        assert bus1 is not bus2

    def test_reset_allows_new_instance(self):
        """After reset, new instance can be created."""
        EventBus.reset()
        bus = EventBus.instance()
        assert bus is not None


class TestEventBusSignals:
    """Tests for EventBus signal definitions."""

    def test_task_started_signal_exists(self):
        """EventBus has task_started signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'task_started')

    def test_task_progress_signal_exists(self):
        """EventBus has task_progress signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'task_progress')

    def test_task_finished_signal_exists(self):
        """EventBus has task_finished signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'task_finished')

    def test_task_error_signal_exists(self):
        """EventBus has task_error signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'task_error')

    def test_task_cancelled_signal_exists(self):
        """EventBus has task_cancelled signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'task_cancelled')

    def test_status_message_signal_exists(self):
        """EventBus has status_message signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'status_message')

    def test_notification_signal_exists(self):
        """EventBus has notification signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'notification')

    def test_project_switched_signal_exists(self):
        """EventBus has project_switched signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'project_switched')

    def test_server_status_changed_signal_exists(self):
        """EventBus has server_status_changed signal."""
        bus = EventBus.instance()
        assert hasattr(bus, 'server_status_changed')


class TestEventBusEmitMethods:
    """Tests for EventBus emit helper methods."""

    def test_emit_task_started_calls_emit(self):
        """emit_task_started emits signal correctly."""
        bus = EventBus.instance()
        mock_slot = Mock()
        bus.task_started.connect(mock_slot)
        bus.emit_task_started("task_123", "download")
        mock_slot.assert_called_once_with("task_123", "download")

    def test_emit_task_progress_calls_emit(self):
        """emit_task_progress emits signal correctly."""
        bus = EventBus.instance()
        mock_slot = Mock()
        bus.task_progress.connect(mock_slot)
        bus.emit_task_progress("task_123", 50, "Processing...")
        mock_slot.assert_called_once_with("task_123", 50, "Processing...")

    def test_emit_task_finished_calls_emit(self):
        """emit_task_finished emits signal correctly."""
        bus = EventBus.instance()
        mock_slot = Mock()
        bus.task_finished.connect(mock_slot)
        result = {"status": "success"}
        bus.emit_task_finished("task_123", result)
        mock_slot.assert_called_once_with("task_123", result)

    def test_emit_task_error_calls_emit(self):
        """emit_task_error emits signal correctly."""
        bus = EventBus.instance()
        mock_slot = Mock()
        bus.task_error.connect(mock_slot)
        bus.emit_task_error("task_123", "Error occurred", None)
        mock_slot.assert_called_once_with("task_123", "Error occurred", None)

    def test_emit_task_cancelled_calls_emit(self):
        """emit_task_cancelled emits signal correctly."""
        bus = EventBus.instance()
        mock_slot = Mock()
        bus.task_cancelled.connect(mock_slot)
        bus.emit_task_cancelled("task_123")
        mock_slot.assert_called_once_with("task_123")

    def test_emit_notification_calls_emit(self):
        """emit_notification emits signal correctly."""
        bus = EventBus.instance()
        mock_slot = Mock()
        bus.notification.connect(mock_slot)
        bus.emit_notification("info", "Title", "Body text")
        mock_slot.assert_called_once_with("info", "Title", "Body text")

    def test_emit_status_calls_emit(self):
        """emit_status emits signal correctly."""
        bus = EventBus.instance()
        mock_slot = Mock()
        bus.status_message.connect(mock_slot)
        bus.emit_status("category", "status message")
        mock_slot.assert_called_once_with("category", "status message")


class TestEventBusObjectName:
    """Tests for EventBus object name."""

    def test_object_name_is_event_bus(self):
        """EventBus has objectName 'EventBus'."""
        bus = EventBus.instance()
        assert bus.objectName() == "EventBus"