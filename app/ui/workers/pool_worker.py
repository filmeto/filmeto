"""Bounded concurrent submits on the shared TaskManager (legacy batch helper).

For single callables prefer :mod:`app.ui.workers.background_worker` or submit
:class:`app.ui.core.base_worker.FunctionWorker` via :class:`app.ui.core.task_manager.TaskManager`.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QEventLoop, QObject, QTimer, Signal

from app.ui.core.base_worker import FunctionWorker
from app.ui.core.task_manager import TaskManager


class PoolWorker(QObject):
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


_global_pool: Optional[PoolWorker] = None


def get_worker_pool(max_workers: int = 4) -> PoolWorker:
    global _global_pool
    if _global_pool is None:
        _global_pool = PoolWorker(max_workers)
    return _global_pool
