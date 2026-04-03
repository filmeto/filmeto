"""QThreadPool-based worker lifecycle manager.

TaskManager owns a QThreadPool and provides:

* ``submit(worker)`` – enqueue a BaseWorker, wire its signals to the EventBus,
  and track its lifecycle.
* ``cancel(task_id)`` / ``cancel_all()`` – cooperative cancellation.
* ``get_status(task_id)`` – query current task state.
* ``clear()`` – purge finished/error/cancelled records.
* ``shutdown()`` – cancel pending work and wait for the pool to drain.

TaskManager itself is a QObject so it can live on the main thread and receive
queued signal deliveries from worker threads.

Usage::

    tm = TaskManager.instance()
    worker = FunctionWorker(heavy_io, path, task_type="file_load")
    worker.signals.finished.connect(lambda tid, res: update_ui(res))
    tm.submit(worker)
"""

import logging
import threading
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal

from app.core.base_worker import BaseWorker, TaskStatus
from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class _TaskRecord:
    """Internal bookkeeping for a submitted worker."""

    __slots__ = ("worker", "signals", "task_id", "task_type", "status")

    def __init__(self, worker: BaseWorker):
        self.worker = worker
        self.signals = worker.signals
        self.task_id = worker.task_id
        self.task_type = worker.task_type
        self.status = TaskStatus.PENDING


class TaskManager(QObject):
    """Manages worker submission, tracking, cancellation and cleanup.

    One global instance is recommended; use ``TaskManager.instance()``.
    """

    # Forwarded aggregate signals (UI can listen on TaskManager directly)
    task_submitted = Signal(str, str)     # task_id, task_type
    all_tasks_finished = Signal()

    _instance: Optional["TaskManager"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        max_workers: int = 4,
        bus: Optional[EventBus] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.setObjectName("TaskManager")

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max_workers)

        self._bus = bus or EventBus.instance()
        self._records: Dict[str, _TaskRecord] = {}
        self._active_ids: Set[str] = set()

    # ── Singleton ────────────────────────────────────────────────

    @classmethod
    def instance(cls, max_workers: int = 4) -> "TaskManager":
        """Return the global TaskManager singleton (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls.__new__(cls)
                    QObject.__init__(inst)
                    inst.setObjectName("TaskManager")
                    inst._pool = QThreadPool(inst)
                    inst._pool.setMaxThreadCount(max_workers)
                    inst._bus = EventBus.instance()
                    inst._records = {}
                    inst._active_ids = set()
                    cls._instance = inst
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton (for testing only)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
                try:
                    cls._instance.deleteLater()
                except RuntimeError:
                    pass
                cls._instance = None

    # ── Public API ───────────────────────────────────────────────

    def submit(self, worker: BaseWorker) -> str:
        """Submit a worker for execution on the thread pool.

        The worker's signals are connected to the EventBus before enqueueing.
        Returns the ``task_id``.
        """
        task_id = worker.task_id
        if task_id in self._records:
            logger.warning(
                "submit(): duplicate task_id %s (overwrites tracking record)",
                task_id,
            )
        record = _TaskRecord(worker)
        self._records[task_id] = record
        self._active_ids.add(task_id)

        worker.signals.setParent(self)

        self._connect_worker_signals(worker)

        self._pool.start(worker)
        self.task_submitted.emit(task_id, worker.task_type)
        logger.debug("Submitted worker %s (type=%s)", task_id, worker.task_type)
        return task_id

    def cancel(self, task_id: str) -> bool:
        """Request cancellation of a running or pending task.

        Returns True if the task was found and cancel() was called.
        """
        record = self._records.get(task_id)
        if record is None:
            logger.warning("cancel(): unknown task_id %s", task_id)
            return False
        record.worker.cancel()
        return True

    def cancel_all(self) -> None:
        """Cancel every active task."""
        for task_id in list(self._active_ids):
            self.cancel(task_id)

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Return the current status of a task, or None if unknown."""
        record = self._records.get(task_id)
        return record.status if record else None

    def is_running(self, task_id: str) -> bool:
        return task_id in self._active_ids

    def active_count(self) -> int:
        return len(self._active_ids)

    def active_task_ids(self) -> List[str]:
        return list(self._active_ids)

    def clear(self) -> None:
        """Remove records for tasks that are no longer active."""
        finished = [
            tid for tid, rec in self._records.items()
            if rec.status in (TaskStatus.FINISHED, TaskStatus.ERROR, TaskStatus.CANCELLED)
        ]
        for tid in finished:
            del self._records[tid]

    def shutdown(self) -> None:
        """Cancel all tasks and wait for the pool to drain."""
        self.cancel_all()
        self._pool.clear()
        self._pool.waitForDone(5000)
        self._active_ids.clear()
        logger.info("TaskManager shut down")

    @property
    def pool(self) -> QThreadPool:
        """Expose the underlying pool for advanced use (e.g. priority tuning)."""
        return self._pool

    # ── Internal signal wiring ───────────────────────────────────

    def _connect_worker_signals(self, worker: BaseWorker) -> None:
        """Wire worker signals to internal handlers and the EventBus."""
        bus = self._bus

        worker.signals.started.connect(self._on_worker_started)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.cancelled.connect(self._on_worker_cancelled)

        worker.signals.started.connect(
            lambda tid: bus.emit_task_started(tid, worker.task_type)
        )
        worker.signals.progress.connect(bus.emit_task_progress)
        worker.signals.finished.connect(bus.emit_task_finished)
        worker.signals.error.connect(bus.emit_task_error)
        worker.signals.cancelled.connect(bus.emit_task_cancelled)

    def _on_worker_started(self, task_id: str) -> None:
        record = self._records.get(task_id)
        if record:
            record.status = TaskStatus.RUNNING

    def _on_worker_finished(self, task_id: str, _result: object) -> None:
        self._mark_done(task_id, TaskStatus.FINISHED)

    def _on_worker_error(self, task_id: str, _msg: str, _exc: object) -> None:
        self._mark_done(task_id, TaskStatus.ERROR)

    def _on_worker_cancelled(self, task_id: str) -> None:
        self._mark_done(task_id, TaskStatus.CANCELLED)

    def _mark_done(self, task_id: str, status: TaskStatus) -> None:
        record = self._records.get(task_id)
        if record:
            record.status = status
            sig = record.signals

            def cleanup() -> None:
                try:
                    sig.disconnect()
                except (RuntimeError, TypeError):
                    pass
                sig.setParent(None)
                sig.deleteLater()

            QTimer.singleShot(0, cleanup)
        self._active_ids.discard(task_id)
        if not self._active_ids:
            QTimer.singleShot(0, self.all_tasks_finished.emit)
