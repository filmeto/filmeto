"""Cancellable QRunnable worker with QObject signal bridge.

Workers are lightweight tasks submitted to a QThreadPool.  Each worker carries
a unique ``task_id`` and emits lifecycle signals through a ``WorkerSignals``
QObject bridge (QRunnable itself cannot emit signals).

Two flavours are provided:

* **BaseWorker** – subclass and override ``execute()``.
* **FunctionWorker** – wraps a plain callable for one-off tasks.

Cancellation contract: long-running ``execute()`` implementations must
periodically call ``self.check_cancelled()`` which raises ``CancelledError``
when cancellation has been requested.  The ``run()`` wrapper catches this and
emits ``signals.cancelled`` instead of ``signals.error``.

Usage::

    class ImageLoader(BaseWorker):
        def execute(self):
            for i, path in enumerate(self.paths):
                self.check_cancelled()
                img = load(path)
                self.report_progress(i * 100 // len(self.paths))
            return images

    worker = ImageLoader(task_id="img-load-1")
    worker.paths = [...]
    task_manager.submit(worker)
"""

import enum
import logging
import uuid
from abc import abstractmethod
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Signal

logger = logging.getLogger(__name__)


class TaskStatus(enum.Enum):
    """Lifecycle states of a submitted worker."""
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"


class CancelledError(Exception):
    """Raised inside ``execute()`` when the worker has been cancelled."""


class WorkerSignals(QObject):
    """Signal bridge for BaseWorker (QRunnable cannot inherit QObject).

    All signals carry ``task_id`` as first argument so that listeners can
    demultiplex by task without extra closures.
    """

    started = Signal(str)               # task_id
    progress = Signal(str, int, str)    # task_id, percent, message
    finished = Signal(str, object)      # task_id, result
    error = Signal(str, str, object)    # task_id, error_msg, exception
    cancelled = Signal(str)             # task_id


class BaseWorker(QRunnable):
    """Abstract cancellable worker executed on a QThreadPool thread.

    Subclasses must implement ``execute() -> Any``.
    """

    def __init__(self, task_id: Optional[str] = None, task_type: str = ""):
        super().__init__()
        self.setAutoDelete(True)

        self.task_id: str = task_id or uuid.uuid4().hex[:12]
        self.task_type: str = task_type
        self.signals = WorkerSignals()

        self._cancelled = False
        self._status = TaskStatus.PENDING

    # ── Public API ───────────────────────────────────────────────

    @property
    def status(self) -> TaskStatus:
        return self._status

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Request cancellation.  The worker must cooperate by calling
        ``check_cancelled()`` in its ``execute()`` loop."""
        self._cancelled = True

    def check_cancelled(self) -> None:
        """Raise ``CancelledError`` if cancellation was requested.
        Call this periodically in long-running ``execute()`` implementations."""
        if self._cancelled:
            raise CancelledError(f"Worker {self.task_id} cancelled")

    def report_progress(self, percent: int, message: str = "") -> None:
        """Emit a progress update (safe to call from worker thread)."""
        self.signals.progress.emit(self.task_id, percent, message)

    # ── QRunnable entry point ────────────────────────────────────

    def run(self) -> None:
        """QRunnable entry point. Do **not** override; implement ``execute()``."""
        self._status = TaskStatus.RUNNING
        self.signals.started.emit(self.task_id)
        try:
            result = self.execute()
            if self._cancelled:
                self._status = TaskStatus.CANCELLED
                self.signals.cancelled.emit(self.task_id)
            else:
                self._status = TaskStatus.FINISHED
                self.signals.finished.emit(self.task_id, result)
        except CancelledError:
            self._status = TaskStatus.CANCELLED
            self.signals.cancelled.emit(self.task_id)
        except Exception as exc:
            self._status = TaskStatus.ERROR
            error_msg = str(exc)
            logger.error("Worker %s failed: %s", self.task_id, error_msg, exc_info=True)
            self.signals.error.emit(self.task_id, error_msg, exc)

    # ── Abstract ─────────────────────────────────────────────────

    @abstractmethod
    def execute(self) -> Any:
        """Implement the actual work here.  Return value is forwarded via
        ``signals.finished``."""


class FunctionWorker(BaseWorker):
    """Wraps a plain callable into a BaseWorker for quick submission.

    Usage::

        worker = FunctionWorker(load_image, "path/to/img.png",
                                task_id="load-1", task_type="image_load")
        task_manager.submit(worker)
    """

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        task_id: Optional[str] = None,
        task_type: str = "",
        **kwargs: Any,
    ):
        super().__init__(task_id=task_id, task_type=task_type)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def execute(self) -> Any:
        return self._fn(*self._args, **self._kwargs)
