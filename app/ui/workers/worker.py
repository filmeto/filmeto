"""Background execution via app.ui.core TaskManager + FunctionWorker.

Legacy API preserved for callers:

* :class:`BackgroundWorker` — QObject facade; signals ``finished(result)``,
  ``error(str, Exception|None)``, ``progress(int, str)``, ``started()``.
* :func:`run_in_background` — one-shot helper.
* :class:`WorkerPool` — bounded concurrent submits with ``all_finished``.

All work runs on the shared :class:`app.ui.core.task_manager.TaskManager` thread pool
and emits task lifecycle events on :class:`app.ui.core.event_bus.EventBus`.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QEventLoop, QObject, QTimer, Signal

from app.ui.core.base_worker import FunctionWorker
from app.ui.core.task_manager import TaskManager

logger = logging.getLogger(__name__)


class BackgroundWorker(QObject):
    """Runs a callable on the shared TaskManager pool (replaces QThread pattern)."""

    finished = Signal(object)
    error = Signal(str, object)
    progress = Signal(int, str)
    started = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._task: Optional[Callable[..., Any]] = None
        self._args: Tuple[Any, ...] = ()
        self._kwargs: Dict[str, Any] = {}
        self._task_id: Optional[str] = None
        self._task_type: str = "legacy_background_worker"
        self._auto_cleanup = True
        self._started = False
        self._tm = TaskManager.instance()

    @property
    def task_id(self) -> Optional[str]:
        """TaskManager id while the runnable is queued or running (``None`` after completion)."""
        return self._task_id

    def set_task_type(self, task_type: str) -> None:
        """Correlates this worker with :class:`~app.ui.core.event_bus.EventBus` ``task_*`` signals."""
        if not self._started:
            self._task_type = task_type or self._task_type

    def set_auto_cleanup(self, enabled: bool) -> None:
        """If True (default), call ``deleteLater()`` on this object after the task ends."""
        self._auto_cleanup = enabled

    def set_task(self, task: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Configure the callable to run. Call before ``start()``."""
        if self._started:
            logger.warning("set_task called after start(); ignored")
            return
        self._task = task
        self._args = args
        self._kwargs = kwargs

    def start(self) -> None:
        """Submit the configured task to the pool."""
        if self._task is None:
            logger.error("BackgroundWorker.start: no task configured")
            return
        if self._started:
            logger.warning("BackgroundWorker is already running")
            return
        self._started = True

        fw = FunctionWorker(
            self._task,
            *self._args,
            **self._kwargs,
            task_id=f"bg-{uuid.uuid4().hex[:10]}",
            task_type=self._task_type,
        )
        fw.signals.started.connect(lambda _tid: self.started.emit())
        fw.signals.progress.connect(lambda _tid, pct, msg: self.progress.emit(pct, msg))
        fw.signals.finished.connect(self._on_fw_finished)
        fw.signals.error.connect(self._on_fw_error)
        fw.signals.cancelled.connect(self._on_fw_cancelled)

        self._task_id = self._tm.submit(fw)

    def _on_fw_finished(self, _tid: str, result: object) -> None:
        self.finished.emit(result)
        self._complete()

    def _on_fw_error(self, _tid: str, msg: str, exc: object) -> None:
        self.error.emit(msg, exc)
        self._complete()

    def _on_fw_cancelled(self, _tid: str) -> None:
        self.error.emit("Cancelled", None)
        self._complete()

    def _complete(self) -> None:
        self._task_id = None
        if self._auto_cleanup:
            self.deleteLater()

    def stop(self) -> None:
        """Request cooperative cancellation."""
        if self._task_id:
            self._tm.cancel(self._task_id)
        self._task_id = None

    def is_running(self) -> bool:
        if not self._task_id:
            return False
        return self._tm.is_running(self._task_id)

    def get_executor(self) -> None:
        """Deprecated. Progress from inside tasks: use :class:`FunctionWorker` / :class:`BaseWorker` instead."""
        return None


class WorkerPool(QObject):
    """Submits tasks through TaskManager; tracks batch completion via ``all_finished``."""

    all_finished = Signal()

    def __init__(self, max_workers: int = 4, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tm = TaskManager.instance()
        pool = self._tm.pool
        if pool.maxThreadCount() < max_workers:
            pool.setMaxThreadCount(max_workers)
        self._outstanding = 0
        self._pending_tasks: List[
            Tuple[Callable, Tuple, Dict, Optional[Callable], Optional[Callable]]
        ] = []
        self._max_workers = max_workers

    def submit(
        self,
        task: Callable[..., Any],
        on_finished: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str, Exception], None]] = None,
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        kwargs = kwargs or {}
        if self._outstanding >= self._max_workers:
            self._pending_tasks.append((task, args, kwargs, on_finished, on_error))
            return
        self._start_task(task, args, kwargs, on_finished, on_error)

    def _start_task(
        self,
        task: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        on_finished: Optional[Callable[[Any], None]],
        on_error: Optional[Callable[[str, Exception], None]],
    ) -> None:
        self._outstanding += 1
        fw = FunctionWorker(
            task,
            *args,
            **kwargs,
            task_id=f"pool-{uuid.uuid4().hex[:10]}",
            task_type="legacy_worker_pool",
        )

        def _wrap_done(_tid: str, result: object) -> None:
            if on_finished:
                on_finished(result)
            self._on_task_done()

        def _wrap_err(_tid: str, msg: str, exc: object) -> None:
            if on_error:
                ex: Exception = exc if isinstance(exc, Exception) else Exception(msg)
                on_error(msg, ex)
            self._on_task_done()

        def _wrap_canc(_tid: str) -> None:
            if on_error:
                on_error("Cancelled", Exception("Cancelled"))
            self._on_task_done()

        fw.signals.finished.connect(_wrap_done)
        fw.signals.error.connect(_wrap_err)
        fw.signals.cancelled.connect(_wrap_canc)
        self._tm.submit(fw)

    def _on_task_done(self) -> None:
        self._outstanding -= 1
        if self._pending_tasks and self._outstanding < self._max_workers:
            t, a, k, of, oe = self._pending_tasks.pop(0)
            self._start_task(t, a, k, of, oe)
        elif self._outstanding <= 0:
            self._outstanding = 0
            if not self._pending_tasks:
                self.all_finished.emit()

    def active_count(self) -> int:
        return self._outstanding

    def pending_count(self) -> int:
        return len(self._pending_tasks)

    def wait_all(self) -> None:
        """Block until outstanding work (including pending queue) completes."""
        if self._outstanding == 0 and not self._pending_tasks:
            return
        loop = QEventLoop()

        def _quit() -> None:
            if self._outstanding == 0 and not self._pending_tasks:
                loop.quit()

        self.all_finished.connect(_quit)
        QTimer.singleShot(120_000, loop.quit)
        loop.exec()
        try:
            self.all_finished.disconnect(_quit)
        except (RuntimeError, TypeError):
            pass

    def cancel_pending(self) -> None:
        self._pending_tasks.clear()


_global_pool: Optional[WorkerPool] = None


def get_worker_pool(max_workers: int = 4) -> WorkerPool:
    global _global_pool
    if _global_pool is None:
        _global_pool = WorkerPool(max_workers)
    return _global_pool


def run_in_background(
    task: Callable[..., Any],
    on_finished: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[str, Exception], None]] = None,
    on_progress: Optional[Callable[[int, str], None]] = None,
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    auto_cleanup: bool = True,
    parent: Optional[QObject] = None,
    task_type: str = "legacy_background_worker",
) -> BackgroundWorker:
    """Run ``task`` on the shared TaskManager pool."""
    kwargs = kwargs or {}
    worker = BackgroundWorker(parent)
    worker.set_task_type(task_type)
    worker.set_auto_cleanup(auto_cleanup)
    worker.set_task(task, *args, **kwargs)
    if on_finished:
        worker.finished.connect(on_finished)
    if on_error:
        worker.error.connect(on_error)
    if on_progress:
        worker.progress.connect(on_progress)
    worker.start()
    return worker
