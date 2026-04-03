"""Abstract service coordination layer.

A Service sits between the UI and the Worker pool.  It is responsible for:

* Parameter validation and input sanitization.
* Creating the appropriate BaseWorker subclass.
* Submitting workers to the TaskManager.
* Aggregating / transforming results before forwarding to the UI.
* Retry logic and error recovery.

Services never touch widgets or QML objects.  The UI interacts with a Service
by calling its methods and subscribing to its signals (or the EventBus).

Usage::

    class ResourceService(BaseAppService):

        resources_loaded = Signal(list)

        def load_resources(self, project_path: str) -> str:
            worker = FunctionWorker(
                self._do_load, project_path,
                task_type="resource_load",
            )
            return self.submit_task(
                worker,
                on_finished=lambda tid, res: self.resources_loaded.emit(res),
            )

        def _do_load(self, project_path: str):
            ...  # heavy IO
"""

import logging
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt

from app.ui.core.base_worker import BaseWorker
from app.ui.core.event_bus import EventBus
from app.ui.core.task_manager import TaskManager

logger = logging.getLogger(__name__)


class BaseAppService(QObject):
    """Base class for application service layers.

    Subclass this to implement feature-specific coordination logic.
    """

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        task_manager: Optional[TaskManager] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._bus = bus or EventBus.instance()
        self._task_manager = task_manager or TaskManager.instance()

    # ── Convenience accessors ────────────────────────────────────

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

    # ── Task helpers ─────────────────────────────────────────────

    def submit_task(
        self,
        worker: BaseWorker,
        on_finished: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_progress: Optional[Callable] = None,
        on_cancelled: Optional[Callable] = None,
    ) -> str:
        """Submit a worker and optionally wire one-shot callbacks.

        Callbacks receive the same arguments as the corresponding
        ``WorkerSignals`` signal:

        * ``on_finished(task_id, result)``
        * ``on_error(task_id, error_msg, exception)``
        * ``on_progress(task_id, percent, message)``
        * ``on_cancelled(task_id)``

        Returns the ``task_id``.
        """
        if on_finished:
            worker.signals.finished.connect(on_finished, Qt.ConnectionType.SingleShotConnection)
        if on_error:
            worker.signals.error.connect(on_error, Qt.ConnectionType.SingleShotConnection)
        if on_progress:
            worker.signals.progress.connect(on_progress)
        if on_cancelled:
            worker.signals.cancelled.connect(on_cancelled, Qt.ConnectionType.SingleShotConnection)

        return self._task_manager.submit(worker)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a previously submitted task."""
        return self._task_manager.cancel(task_id)

    def cancel_all(self) -> None:
        """Cancel all active tasks submitted through this service.

        Note: this cancels *all* tasks in the shared TaskManager.
        For per-service isolation, track task_ids and cancel individually.
        """
        self._task_manager.cancel_all()
