"""
Unit tests for signal utilities in utils/signal_utils.py
"""
import asyncio
import threading
import pytest
from unittest.mock import Mock
from utils.signal_utils import (
    BaseSignal,
    BlockingSignal,
    AsyncSignal,
    AsyncioSignal,
    create_blocking_signal,
    create_async_signal,
    create_asyncio_signal,
)


class TestBaseSignal:
    """Tests for BaseSignal common functionality"""

    def test_connect_adds_slot(self):
        sig = BaseSignal()
        slot = lambda x: x
        sig.connect(slot)
        assert slot in sig._slots

    def test_connect_does_not_duplicate(self):
        sig = BaseSignal()
        slot = lambda x: x
        sig.connect(slot)
        sig.connect(slot)
        assert len(sig._slots) == 1

    def test_disconnect_removes_slot(self):
        sig = BaseSignal()
        slot = lambda x: x
        sig.connect(slot)
        sig.disconnect(slot)
        assert slot not in sig._slots

    def test_disconnect_all_clears_slots(self):
        sig = BaseSignal()
        sig.connect(lambda x: x)
        sig.connect(lambda x: x + 1)
        sig.disconnect_all()
        assert len(sig._slots) == 0

    def test_slot_lock_thread_safety(self):
        """Verify that slot modifications are thread-safe"""
        sig = BaseSignal()
        errors = []

        def add_slots():
            for i in range(100):
                try:
                    sig.connect(lambda x: x + i)
                except Exception as e:
                    errors.append(e)

        def remove_slots():
            slots = list(sig._slots)
            for slot in slots[:50]:
                try:
                    sig.disconnect(slot)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=add_slots),
            threading.Thread(target=add_slots),
            threading.Thread(target=remove_slots),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestBlockingSignal:
    """Tests for BlockingSignal synchronous execution"""

    def test_emit_executes_all_slots_synchronously(self):
        results = []
        sig = BlockingSignal()

        def slot1(msg):
            results.append(("slot1", msg))

        def slot2(msg):
            results.append(("slot2", msg))

        sig.connect(slot1)
        sig.connect(slot2)
        sig.emit("test")

        assert results == [("slot1", "test"), ("slot2", "test")]

    def test_emit_with_kwargs(self):
        results = []
        sig = BlockingSignal()

        def slot(**kwargs):
            results.append(kwargs)

        sig.connect(slot)
        sig.emit(key="value", num=42)

        assert results == [{"key": "value", "num": 42}]

    def test_emit_copies_slots_before_execution(self):
        """Verify slots can be modified during emit without affecting current execution"""
        results = []
        sig = BlockingSignal()

        def slot1(msg):
            results.append("slot1")
            # Remove self during execution
            sig.disconnect(slot1)

        def slot2(msg):
            results.append("slot2")

        sig.connect(slot1)
        sig.connect(slot2)
        sig.emit("test")

        # Both slots should execute even though slot1 removed itself
        assert "slot1" in results
        assert "slot2" in results


class TestAsyncSignal:
    """Tests for AsyncSignal async execution"""

    @pytest.mark.asyncio
    async def test_emit_executes_async_slots(self):
        results = []
        sig = AsyncSignal()

        async def async_slot(msg):
            await asyncio.sleep(0.01)
            results.append(("async", msg))

        sig.connect(async_slot)
        await sig.emit("test")

        assert results == [("async", "test")]

    @pytest.mark.asyncio
    async def test_emit_executes_sync_slots_in_executor(self):
        results = []
        sig = AsyncSignal()

        def sync_slot(msg):
            results.append(("sync", msg))

        sig.connect(sync_slot)
        await sig.emit("test")

        assert results == [("sync", "test")]

    @pytest.mark.asyncio
    async def test_emit_executes_both_async_and_sync_slots(self):
        results = []
        sig = AsyncSignal()

        async def async_slot(msg):
            results.append("async")

        def sync_slot(msg):
            results.append("sync")

        sig.connect(async_slot)
        sig.connect(sync_slot)
        await sig.emit("test")

        assert "async" in results
        assert "sync" in results

    @pytest.mark.asyncio
    async def test_emit_returns_exceptions_with_return_exceptions_true(self):
        sig = AsyncSignal()

        async def failing_slot(msg):
            raise ValueError("test error")

        sig.connect(failing_slot)
        # Should not raise, exceptions are gathered
        await sig.emit("test")

    @pytest.mark.asyncio
    async def test_close_shuts_down_executor(self):
        sig = AsyncSignal()
        sig.close()
        # Executor should be shut down
        assert sig._executor._shutdown


class TestAsyncioSignal:
    """Tests for AsyncioSignal asyncio event loop integration"""

    @pytest.mark.asyncio
    async def test_emit_executes_async_slots(self):
        results = []
        sig = AsyncioSignal()

        async def async_slot(msg):
            results.append(("async", msg))

        sig.connect(async_slot)
        await sig.emit("test")

        assert results == [("async", "test")]

    @pytest.mark.asyncio
    async def test_emit_executes_sync_slots_as_tasks(self):
        results = []
        sig = AsyncioSignal()

        def sync_slot(msg):
            results.append(("sync", msg))

        sig.connect(sync_slot)
        await sig.emit("test")

        assert results == [("sync", "test")]

    @pytest.mark.asyncio
    async def test_emit_nowait_does_not_block(self):
        results = []
        sig = AsyncioSignal()

        async def slow_slot(msg):
            await asyncio.sleep(0.5)
            results.append(msg)

        sig.connect(slow_slot)
        sig.emit_nowait("test")

        # Should return immediately without waiting
        assert len(results) == 0

        # Wait for task to complete
        await sig.wait_all()
        assert results == ["test"]

    @pytest.mark.asyncio
    async def test_wait_all_waits_for_pending_tasks(self):
        results = []
        sig = AsyncioSignal()

        async def slot(msg):
            await asyncio.sleep(0.1)
            results.append(msg)

        sig.connect(slot)
        sig.emit_nowait("test")
        await sig.wait_all()

        assert results == ["test"]

    def test_close_iterates_and_calls_cancel(self):
        """Verify close() iterates through tasks and calls cancel"""
        sig = AsyncioSignal()

        # Create mock tasks
        mock_task1 = Mock()
        mock_task1.done.return_value = False

        mock_task2 = Mock()
        mock_task2.done.return_value = True  # Already done

        sig._tasks = {mock_task1, mock_task2}

        sig.close()

        # Cancel should be called on non-done tasks
        mock_task1.cancel.assert_called_once()
        # Cancel should not be called on done tasks
        mock_task2.cancel.assert_not_called()


class TestConvenienceFunctions:
    """Tests for convenience factory functions"""

    def test_create_blocking_signal(self):
        sig = create_blocking_signal()
        assert isinstance(sig, BlockingSignal)

    def test_create_async_signal(self):
        sig = create_async_signal()
        assert isinstance(sig, AsyncSignal)

    def test_create_asyncio_signal(self):
        sig = create_asyncio_signal()
        assert isinstance(sig, AsyncioSignal)