"""Background worker module for non-blocking UI operations.

This module provides utilities for running tasks in background threads
without blocking the main UI thread.

Classes:
    BackgroundWorker: Single task worker with signals
    TaskExecutor: Low-level task executor (moved to QThread)
    WorkerPool: Pool for running multiple concurrent tasks

Functions:
    run_in_background: Convenience function for quick background tasks
    get_worker_pool: Get global worker pool singleton
"""

from .async_data_loader import AsyncDataLoader, AsyncDataLoaderMixin
from .worker import (
    TaskExecutor,
    BackgroundWorker,
    WorkerPool,
    run_in_background,
    get_worker_pool,
)

__all__ = [
    "AsyncDataLoader",
    "AsyncDataLoaderMixin",
    "TaskExecutor",
    "BackgroundWorker",
    "WorkerPool",
    "run_in_background",
    "get_worker_pool",
]
