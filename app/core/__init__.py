"""Core architecture module: EventBus, Worker pool, Service layer.

Provides the foundational decoupling infrastructure for the application:

- **EventBus**: Centralized Qt signal bus for cross-module communication.
- **BaseWorker / FunctionWorker**: Cancellable QRunnable workers with signal bridge.
- **TaskManager**: QThreadPool-based worker lifecycle and tracking.
- **BaseAppService**: Abstract service coordination layer between UI and workers.

Dependency flow (unidirectional):
    UI -> Service -> TaskManager -> Worker (QThreadPool thread)
    Worker -> signals -> EventBus -> UI
"""

from app.core.event_bus import EventBus
from app.core.base_worker import BaseWorker, FunctionWorker, WorkerSignals, TaskStatus
from app.core.task_manager import TaskManager
from app.core.base_service import BaseAppService

__all__ = [
    "EventBus",
    "BaseWorker",
    "FunctionWorker",
    "WorkerSignals",
    "TaskStatus",
    "TaskManager",
    "BaseAppService",
]
