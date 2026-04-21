"""
Unit tests for utils/download_utils.py

Tests download worker functionality including:
- DownloadWorkerSignals signal definitions
- DownloadWorker initialization and lifecycle
- get_download_worker global instance management
- shutdown_download_worker cleanup
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtCore import QObject, Signal
from utils.download_utils import (
    DownloadWorkerSignals,
    DownloadWorker,
    get_download_worker,
    shutdown_download_worker,
    FileEventHandler,
)


class TestDownloadWorkerSignals:
    """Tests for DownloadWorkerSignals class."""

    def test_signals_has_started_signal(self):
        """DownloadWorkerSignals has started signal."""
        signals = DownloadWorkerSignals()
        assert hasattr(signals, 'started')

    def test_signals_has_progress_signal(self):
        """DownloadWorkerSignals has progress signal."""
        signals = DownloadWorkerSignals()
        assert hasattr(signals, 'progress')

    def test_signals_has_finished_signal(self):
        """DownloadWorkerSignals has finished signal."""
        signals = DownloadWorkerSignals()
        assert hasattr(signals, 'finished')

    def test_signals_has_error_signal(self):
        """DownloadWorkerSignals has error signal."""
        signals = DownloadWorkerSignals()
        assert hasattr(signals, 'error')

    def test_signals_has_cancelled_signal(self):
        """DownloadWorkerSignals has cancelled signal."""
        signals = DownloadWorkerSignals()
        assert hasattr(signals, 'cancelled')

    def test_signals_is_qobject(self):
        """DownloadWorkerSignals is a QObject."""
        signals = DownloadWorkerSignals()
        assert isinstance(signals, QObject)


class TestDownloadWorkerInit:
    """Tests for DownloadWorker initialization."""

    def test_init_creates_signals(self):
        """DownloadWorker creates DownloadWorkerSignals on init."""
        worker = DownloadWorker()
        assert worker.signals is not None
        assert isinstance(worker.signals, DownloadWorkerSignals)

    def test_init_creates_empty_running_tasks(self):
        """DownloadWorker has empty running tasks dict."""
        worker = DownloadWorker()
        assert worker._running_tasks == {}

    def test_init_loop_is_none(self):
        """DownloadWorker loop is None before run."""
        worker = DownloadWorker()
        assert worker.loop is None


class TestDownloadWorkerStartDownload:
    """Tests for DownloadWorker.start_download method."""

    def test_start_download_adds_to_running_tasks(self):
        """start_download adds URL to running tasks."""
        worker = DownloadWorker()
        url = "http://example.com/file.txt"
        worker.start_download(url)
        assert url in worker._running_tasks

    def test_start_download_generates_save_path_if_none(self):
        """start_download generates save path when not provided."""
        worker = DownloadWorker()
        url = "http://example.com/file.txt"
        worker.start_download(url)
        save_path = worker._running_tasks[url]
        assert "file.txt" in save_path or "download_" in save_path

    def test_start_download_uses_provided_save_path(self):
        """start_download uses provided save path."""
        worker = DownloadWorker()
        url = "http://example.com/file.txt"
        save_path = "/tmp/test_file.txt"
        worker.start_download(url, save_path)
        assert worker._running_tasks[url] == save_path


class TestDownloadWorkerCancelDownload:
    """Tests for DownloadWorker.cancel_download method."""

    def test_cancel_download_removes_from_running_tasks(self):
        """cancel_download removes URL from running tasks."""
        worker = DownloadWorker()
        url = "http://example.com/file.txt"
        worker.start_download(url)
        worker.cancel_download(url)
        assert url not in worker._running_tasks


class TestGetDownloadWorker:
    """Tests for get_download_worker function."""

    def test_get_download_worker_creates_instance(self):
        """get_download_worker creates global worker on first call."""
        shutdown_download_worker()  # Reset first
        import utils.download_utils as du
        du._global_download_worker = None

        worker = get_download_worker()
        assert worker is not None
        assert isinstance(worker, DownloadWorker)

    def test_get_download_worker_returns_same_instance(self):
        """get_download_worker returns same instance on subsequent calls."""
        shutdown_download_worker()
        import utils.download_utils as du
        du._global_download_worker = None

        worker1 = get_download_worker()
        worker2 = get_download_worker()
        assert worker1 is worker2


class TestShutdownDownloadWorker:
    """Tests for shutdown_download_worker function."""

    def test_shutdown_sets_global_to_none(self):
        """shutdown_download_worker sets global instance to None."""
        get_download_worker()  # Ensure instance exists
        shutdown_download_worker()
        import utils.download_utils as du
        assert du._global_download_worker is None

    def test_shutdown_is_safe_when_none(self):
        """shutdown_download_worker is safe when worker is None."""
        shutdown_download_worker()  # Already None or running
        shutdown_download_worker()  # Call again - should not raise


class TestFileEventHandler:
    """Tests for FileEventHandler class."""

    @pytest.mark.asyncio
    async def test_on_file_downloaded_default_handler(self):
        """FileEventHandler.on_file_downloaded prints filepath."""
        handler = FileEventHandler()
        # Default handler just prints and sleeps
        await handler.on_file_downloaded("/tmp/test.txt")
        # Should complete without error

    @pytest.mark.asyncio
    async def test_custom_handler_can_be_overridden(self):
        """Custom FileEventHandler can override on_file_downloaded."""

        class CustomHandler(FileEventHandler):
            async def on_file_downloaded(self, filepath: str):
                return filepath

        handler = CustomHandler()
        result = await handler.on_file_downloaded("/tmp/custom.txt")
        assert result == "/tmp/custom.txt"