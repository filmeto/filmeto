"""Feature workers and UI-thread helpers submitted via :class:`app.core.task_manager.TaskManager`.

Organization
============

- **Framework** (pool, bus, abstract worker): :mod:`app.core` — ``BaseWorker``,
  ``FunctionWorker``, ``TaskManager``, ``EventBus``, ``BaseAppService``.
- **This package** — concrete ``BaseWorker`` subclasses, legacy QObject helpers
  (:class:`BackgroundWorker`, :class:`AsyncDataLoader`), one domain module per
  feature where applicable:

  - ``worker`` — pool-backed :class:`BackgroundWorker`, :func:`run_in_background`.
  - ``async_data_loader`` — debounced loads for UI lists/previews.
  - ``timeline_export`` — FFmpeg timeline export.

Adding a worker
================

1. Subclass :class:`app.core.base_worker.BaseWorker` (or use ``FunctionWorker`` for one-shot callables).
2. Place the class in a new module under ``app/workers/`` (e.g. ``app/workers/my_feature.py``).
3. Export it from this ``__init__.py`` if it is part of the public surface.
4. Submit via ``TaskManager.instance().submit(worker)`` or a :class:`app.core.base_service.BaseAppService` subclass — not ``QThreadPool.globalInstance()`` for domain work.
"""

from app.workers.async_data_loader import AsyncDataLoader, AsyncDataLoaderMixin
from app.workers.timeline_export import TimelineExportWorker
from app.workers.worker import (
    BackgroundWorker,
    WorkerPool,
    get_worker_pool,
    run_in_background,
)

__all__ = [
    "AsyncDataLoader",
    "AsyncDataLoaderMixin",
    "BackgroundWorker",
    "TimelineExportWorker",
    "WorkerPool",
    "get_worker_pool",
    "run_in_background",
]
