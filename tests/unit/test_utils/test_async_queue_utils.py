"""
Unit tests for utils/async_queue_utils.py

Tests AsyncQueue functionality including:
- Adding tasks to queue
- Connecting handlers to task types
- Sequential processing
- Stop and join operations
- Async context manager
"""

import pytest
import asyncio
from utils.async_queue_utils import AsyncQueue


class TestAsyncQueueInit:
    """Tests for AsyncQueue initialization."""

    def test_init_creates_empty_queue(self):
        """AsyncQueue should initialize with empty queue and no handlers."""
        queue = AsyncQueue()
        assert queue._queue.empty()
        assert queue._handlers == {}
        assert queue._running is True
        assert queue._task is None


class TestAsyncQueueAdd:
    """Tests for AsyncQueue.add method."""

    def test_add_puts_task_in_queue(self):
        """Adding a task should put it in the internal queue."""
        queue = AsyncQueue()
        queue.add("test_type", {"data": "value"})
        assert not queue._queue.empty()
        item = queue._queue.get_nowait()
        assert item["type"] == "test_type"
        assert item["data"] == {"data": "value"}

    def test_add_multiple_tasks(self):
        """Multiple tasks can be added to queue."""
        queue = AsyncQueue()
        queue.add("type1", "data1")
        queue.add("type2", "data2")
        queue.add("type3", "data3")
        assert queue._queue.qsize() == 3


class TestAsyncQueueConnect:
    """Tests for AsyncQueue.connect method."""

    @pytest.mark.asyncio
    async def test_connect_registers_handler(self):
        """Connecting a handler registers it for task type."""

        async def dummy_handler(data):
            pass

        queue = AsyncQueue()
        queue.connect("test_type", dummy_handler)
        assert "test_type" in queue._handlers
        assert dummy_handler in queue._handlers["test_type"]

    @pytest.mark.asyncio
    async def test_connect_multiple_handlers_same_type(self):
        """Multiple handlers can be connected to same task type."""

        async def handler1(data):
            pass

        async def handler2(data):
            pass

        queue = AsyncQueue()
        queue.connect("test_type", handler1)
        queue.connect("test_type", handler2)
        assert len(queue._handlers["test_type"]) == 2


class TestAsyncQueueProcessTask:
    """Tests for AsyncQueue._process_task method."""

    @pytest.mark.asyncio
    async def test_process_task_calls_handlers(self):
        """Processing a task calls all connected handlers."""
        results = []

        async def handler1(data):
            results.append(("handler1", data))

        async def handler2(data):
            results.append(("handler2", data))

        queue = AsyncQueue()
        queue.connect("test_type", handler1)
        queue.connect("test_type", handler2)

        task = {"type": "test_type", "data": "test_data"}
        await queue._process_task(task)

        assert ("handler1", "test_data") in results
        assert ("handler2", "test_data") in results

    @pytest.mark.asyncio
    async def test_process_task_no_handlers(self):
        """Processing task with no handlers completes without error."""
        queue = AsyncQueue()
        task = {"type": "unknown_type", "data": "data"}
        await queue._process_task(task)  # Should not raise


class TestAsyncQueueStop:
    """Tests for AsyncQueue.stop method."""

    def test_stop_sets_running_false(self):
        """Stop sets _running to False."""
        queue = AsyncQueue()
        assert queue._running is True
        queue.stop()
        assert queue._running is False

    def test_stop_cancels_task(self):
        """Stop cancels the running task if exists."""
        queue = AsyncQueue()
        # Create a mock task
        async def mock_coro():
            await asyncio.sleep(10)

        queue._task = asyncio.create_task(mock_coro())
        queue.stop()
        assert queue._task.cancelled() or queue._task.done()


class TestAsyncQueueJoin:
    """Tests for AsyncQueue.join method."""

    @pytest.mark.asyncio
    async def test_join_waits_for_empty_queue(self):
        """Join waits until queue is empty."""
        queue = AsyncQueue()
        queue.add("type1", "data1")

        # Add a handler that processes immediately
        async def quick_handler(data):
            pass

        queue.connect("type1", quick_handler)

        # Process the queue manually then join
        if queue._task is None or queue._task.done():
            try:
                loop = asyncio.get_running_loop()
                queue._task = loop.create_task(queue._run())
            except RuntimeError:
                pass

        queue.stop()
        await queue.join()  # Should complete


class TestAsyncQueueContextManager:
    """Tests for AsyncQueue async context manager."""

    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        """__aenter__ returns the queue itself."""
        queue = AsyncQueue()
        result = await queue.__aenter__()
        assert result is queue

    @pytest.mark.asyncio
    async def test_aexit_stops_queue(self):
        """__aexit__ stops the queue."""
        queue = AsyncQueue()
        await queue.__aenter__()
        assert queue._running is True
        await queue.__aexit__(None, None, None)
        assert queue._running is False


class TestAsyncQueueRun:
    """Tests for AsyncQueue._run method."""

    @pytest.mark.asyncio
    async def test_run_processes_tasks_sequentially(self):
        """_run processes tasks in queue sequentially."""
        processed = []

        async def handler(data):
            processed.append(data)
            await asyncio.sleep(0.01)  # Simulate work

        queue = AsyncQueue()
        queue.connect("test_type", handler)

        # Add tasks
        queue.add("test_type", "task1")
        queue.add("test_type", "task2")

        # Run for a short time
        async def run_briefly():
            task = asyncio.create_task(queue._run())
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        await run_briefly()

        # Both tasks should be processed
        assert "task1" in processed
        assert "task2" in processed