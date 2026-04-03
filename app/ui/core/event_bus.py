"""Unified signal bus for cross-module communication.

The EventBus is a global singleton QObject that centralizes all cross-module
signals. Components subscribe to bus signals instead of connecting directly
to each other, eliminating mesh dependencies.

Thread safety: All signals use Qt.QueuedConnection by default when crossing
thread boundaries, ensuring slot execution on the receiver's thread.

Usage::

    bus = EventBus.instance()

    # Subscribe in UI
    bus.task_progress.connect(self._on_progress)

    # Emit from Service / Worker
    bus.task_progress.emit(task_id, 50, "Processing...")
"""

import logging
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class EventBus(QObject):
    """Global singleton signal bus.

    All cross-module communication flows through this object.
    Signals are grouped by domain for clarity.
    """

    # ── Task lifecycle ───────────────────────────────────────────
    task_started = Signal(str, str)           # task_id, task_type
    task_progress = Signal(str, int, str)     # task_id, percent, message
    task_finished = Signal(str, object)       # task_id, result
    task_error = Signal(str, str, object)     # task_id, error_msg, exception
    task_cancelled = Signal(str)              # task_id

    # ── Application-level notifications ──────────────────────────
    status_message = Signal(str, str)         # category, message
    notification = Signal(str, str, str)      # level(info/warn/error), title, body

    # ── Project / workspace events ───────────────────────────────
    project_switched = Signal(str)            # project_name
    project_data_changed = Signal(str, str)   # project_name, change_type

    # ── Resource events ──────────────────────────────────────────
    resource_added = Signal(str, object)      # resource_type, resource_data
    resource_updated = Signal(str, object)    # resource_type, resource_data
    resource_deleted = Signal(str, str)       # resource_type, resource_id

    # ── Server / service events ──────────────────────────────────
    server_status_changed = Signal(str, str)  # server_id, status
    service_state_changed = Signal(str, str)  # service_id, state

    # ── Singleton machinery ──────────────────────────────────────
    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()

    def __init__(self, parent: Optional[QObject] = None):
        if EventBus._instance is not None:
            raise RuntimeError(
                "EventBus is a singleton. Use EventBus.instance() instead of direct construction."
            )
        super().__init__(parent)
        self.setObjectName("EventBus")

    @classmethod
    def instance(cls) -> "EventBus":
        """Return the global EventBus singleton (thread-safe lazy init)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls.__new__(cls)
                    QObject.__init__(cls._instance)
                    cls._instance.setObjectName("EventBus")
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton (for testing only)."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance.deleteLater()
                except RuntimeError:
                    pass
                cls._instance = None

    # ── Convenience helpers ──────────────────────────────────────

    def emit_task_started(self, task_id: str, task_type: str = "") -> None:
        self.task_started.emit(task_id, task_type)

    def emit_task_progress(self, task_id: str, percent: int, message: str = "") -> None:
        self.task_progress.emit(task_id, percent, message)

    def emit_task_finished(self, task_id: str, result: object = None) -> None:
        self.task_finished.emit(task_id, result)

    def emit_task_error(self, task_id: str, error_msg: str, exception: object = None) -> None:
        self.task_error.emit(task_id, error_msg, exception)

    def emit_task_cancelled(self, task_id: str) -> None:
        self.task_cancelled.emit(task_id)

    def emit_notification(self, level: str, title: str, body: str = "") -> None:
        self.notification.emit(level, title, body)

    def emit_status(self, category: str, message: str) -> None:
        self.status_message.emit(category, message)
