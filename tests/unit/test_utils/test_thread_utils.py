"""
Unit tests for utils/thread_utils.py

Tests thread safety utilities including:
- ThreadSafetyMixin: Mixin for Qt object thread safety
- safe_callback_wrapper: Wrapper for safe callback execution
- run_safe_background_task: Safe background task runner
- SafeWorkerManager: Manager for multiple background workers
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from utils.thread_utils import (
    ThreadSafetyMixin,
    safe_callback_wrapper,
    run_safe_background_task,
    SafeWorkerManager,
)


class TestThreadSafetyMixinInit:
    """Tests for ThreadSafetyMixin initialization."""

    def test_init_creates_active_workers_list(self):
        """ThreadSafetyMixin.__init__ creates empty active workers list."""
        mixin = ThreadSafetyMixin()
        mixin.__init__()
        assert mixin._active_workers == []

    def test_init_creates_worker_callbacks_dict(self):
        """ThreadSafetyMixin.__init__ creates empty worker callbacks dict."""
        mixin = ThreadSafetyMixin()
        mixin.__init__()
        assert mixin._worker_callbacks == {}


class TestThreadSafetyMixinIsValidQtObject:
    """Tests for ThreadSafetyMixin.is_valid_qt_object method."""

    def test_is_valid_returns_true_when_shiboken_available(self):
        """is_valid_qt_object returns True when shiboken6 isValid passes."""
        mixin = ThreadSafetyMixin()

        with patch("utils.thread_utils.isValid", return_value=True):
            result = mixin.is_valid_qt_object()
            assert result is True

    def test_is_valid_returns_false_when_shiboken_invalid(self):
        """is_valid_qt_object returns False when shiboken6 isValid fails."""
        mixin = ThreadSafetyMixin()

        with patch("utils.thread_utils.isValid", return_value=False):
            result = mixin.is_valid_qt_object()
            assert result is False

    def test_is_valid_returns_true_on_import_error(self):
        """is_valid_qt_object returns True when shiboken6 not available."""
        mixin = ThreadSafetyMixin()

        with patch("utils.thread_utils.isValid", side_effect=ImportError):
            result = mixin.is_valid_qt_object()
            assert result is True


class TestThreadSafetyMixinStopAllWorkers:
    """Tests for ThreadSafetyMixin.stop_all_workers method."""

    def test_stop_all_workers_stops_running_workers(self):
        """stop_all_workers stops all workers that are running."""
        mixin = ThreadSafetyMixin()
        mixin.__init__()

        mock_worker1 = Mock()
        mock_worker1.is_running.return_value = True
        mock_worker1.stop = Mock()

        mock_worker2 = Mock()
        mock_worker2.is_running.return_value = False
        mock_worker2.stop = Mock()

        mixin._active_workers = [mock_worker1, mock_worker2]
        mixin.stop_all_workers()

        mock_worker1.stop.assert_called_once()
        mock_worker2.stop.assert_not_called()

    def test_stop_all_workers_clears_worker_lists(self):
        """stop_all_workers clears active_workers and worker_callbacks."""
        mixin = ThreadSafetyMixin()
        mixin.__init__()
        mixin._active_workers = [Mock()]
        mixin._worker_callbacks = {"key": "value"}

        mixin.stop_all_workers()

        assert mixin._active_workers == []
        assert mixin._worker_callbacks == {}


class TestSafeCallbackWrapper:
    """Tests for safe_callback_wrapper function."""

    def test_wrapper_calls_callback_when_object_valid(self):
        """safe_callback_wrapper calls callback when object is valid."""
        obj = Mock()
        callback = Mock(return_value="result")

        with patch("utils.thread_utils.isValid", return_value=True):
            wrapped = safe_callback_wrapper(obj, callback)
            result = wrapped("arg1", "arg2")

            callback.assert_called_once_with("arg1", "arg2")
            assert result == "result"

    def test_wrapper_skips_callback_when_object_invalid(self):
        """safe_callback_wrapper skips callback when object invalid."""
        obj = Mock()
        callback = Mock()

        with patch("utils.thread_utils.isValid", return_value=False):
            wrapped = safe_callback_wrapper(obj, callback)
            wrapped("arg1")

            callback.assert_not_called()

    def test_wrapper_handles_import_error(self):
        """safe_callback_wrapper handles ImportError gracefully."""
        obj = Mock()
        callback = Mock(return_value="result")

        with patch("utils.thread_utils.isValid", side_effect=ImportError):
            wrapped = safe_callback_wrapper(obj, callback)
            result = wrapped("arg")

            callback.assert_called_once_with("arg")
            assert result == "result"


class TestRunSafeBackgroundTask:
    """Tests for run_safe_background_task function."""

    @patch("utils.thread_utils.run_in_background")
    def test_runs_task_with_wrapped_callbacks(self, mock_run):
        """run_safe_background_task wraps callbacks before passing."""
        obj = Mock()
        task = Mock()
        on_finished = Mock()
        on_error = Mock()

        result = run_safe_background_task(obj, task, on_finished, on_error)

        mock_run.assert_called_once()
        # Check that callbacks were passed
        call_args = mock_run.call_args
        assert call_args[1]["on_finished"] is not None
        assert call_args[1]["on_error"] is not None


class TestSafeWorkerManagerInit:
    """Tests for SafeWorkerManager initialization."""

    def test_init_creates_empty_workers_list(self):
        """SafeWorkerManager.__init__ creates empty workers list."""
        manager = SafeWorkerManager()
        assert manager._workers == []

    def test_init_creates_empty_callbacks_dict(self):
        """SafeWorkerManager.__init__ creates empty callbacks dict."""
        manager = SafeWorkerManager()
        assert manager._callbacks == {}


class TestSafeWorkerManagerAddWorker:
    """Tests for SafeWorkerManager.add_worker method."""

    def test_add_worker_appends_to_workers_list(self):
        """add_worker adds worker to workers list."""
        manager = SafeWorkerManager()
        mock_worker = Mock()
        mock_worker.finished = Mock()
        mock_worker.error = Mock()

        manager.add_worker(mock_worker)

        assert mock_worker in manager._workers

    def test_add_worker_stores_callbacks(self):
        """add_worker stores callbacks in callbacks dict."""
        manager = SafeWorkerManager()
        mock_worker = Mock()
        mock_worker.finished = Mock()
        mock_worker.error = Mock()
        finished_cb = Mock()
        error_cb = Mock()

        manager.add_worker(mock_worker, finished_cb, error_cb)

        assert id(mock_worker) in manager._callbacks


class TestSafeWorkerManagerStopAllWorkers:
    """Tests for SafeWorkerManager.stop_all_workers method."""

    def test_stop_all_workers_stops_running_workers(self):
        """stop_all_workers stops all workers that are running."""
        manager = SafeWorkerManager()

        mock_worker1 = Mock()
        mock_worker1.is_running.return_value = True
        mock_worker1.stop = Mock()

        mock_worker2 = Mock()
        mock_worker2.is_running.return_value = False
        mock_worker2.stop = Mock()

        manager._workers = [mock_worker1, mock_worker2]
        manager.stop_all_workers()

        mock_worker1.stop.assert_called_once()
        mock_worker2.stop.assert_not_called()

    def test_stop_all_workers_clears_lists(self):
        """stop_all_workers clears workers and callbacks."""
        manager = SafeWorkerManager()
        manager._workers = [Mock()]
        manager._callbacks = {"key": "value"}

        manager.stop_all_workers()

        assert manager._workers == []
        assert manager._callbacks == {}


class TestSafeWorkerManagerGetActiveCount:
    """Tests for SafeWorkerManager.get_active_count method."""

    def test_get_active_count_returns_running_count(self):
        """get_active_count returns count of running workers."""
        manager = SafeWorkerManager()

        mock_worker1 = Mock()
        mock_worker1.is_running.return_value = True

        mock_worker2 = Mock()
        mock_worker2.is_running.return_value = False

        mock_worker3 = Mock()
        mock_worker3.is_running.return_value = True

        manager._workers = [mock_worker1, mock_worker2, mock_worker3]

        count = manager.get_active_count()
        assert count == 2

    def test_get_active_count_returns_zero_empty(self):
        """get_active_count returns 0 when no workers."""
        manager = SafeWorkerManager()
        count = manager.get_active_count()
        assert count == 0