"""Single-key load executed on the shared TaskManager (used by :class:`AsyncDataLoader`)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.ui.core.base_worker import BaseWorker


class AsyncDataLoadWorker(BaseWorker):
    """Runs ``loader_func(key)`` once on a pool thread."""

    def __init__(
        self,
        loader_func: Callable[[Any], Any],
        key: Any,
        *,
        task_id: Optional[str] = None,
        task_type: str = "async_data_loader",
    ):
        super().__init__(task_id=task_id, task_type=task_type)
        self._loader_func = loader_func
        self._key = key

    def execute(self) -> Any:
        return self._loader_func(self._key)
