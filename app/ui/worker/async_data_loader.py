"""
Generic async data loader with debouncing, optional caching, and race protection.

Loads run via ``run_in_background`` after a per-key debounce delay. A monotonic
token per key is incremented when a load actually starts (after debounce), so
late completions from superseded runs are ignored.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Generic, Hashable, Optional, Set, TypeVar, cast

from PySide6.QtCore import QObject, QTimer, Signal

from app.ui.worker.worker import run_in_background

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)


class AsyncDataLoader(QObject, Generic[T, K]):
    """Debounced background loads with token-based stale result suppression."""

    data_loaded = Signal(object, object)  # key, data
    load_error = Signal(object, str)  # key, error_msg
    load_started = Signal(object)  # key
    load_finished = Signal(object)  # key (after success or error)

    DEFAULT_DEBOUNCE_MS = 300

    def __init__(
        self,
        loader_func: Callable[[K], T],
        parent: Optional[QObject] = None,
        debounce_ms: Optional[int] = None,
        cache_enabled: bool = True,
    ):
        super().__init__(parent)
        self._loader_func = loader_func
        self._debounce_ms = int(debounce_ms or self.DEFAULT_DEBOUNCE_MS)
        self._cache_enabled = cache_enabled

        self._load_token: Dict[Any, int] = {}
        self._cache: Dict[Any, T] = {}
        self._loading: Dict[Any, bool] = {}
        self._debounce_timers: Dict[Any, QTimer] = {}
        self._pending_keys: Set[Any] = set()

    def schedule_load(self, key: K, force: bool = False) -> None:
        if (
            self._cache_enabled
            and not force
            and key in self._cache
        ):
            self.data_loaded.emit(key, self._cache[key])
            self.load_finished.emit(key)
            return

        if key not in self._debounce_timers:
            timer = QTimer(self)
            timer.setSingleShot(True)

            def on_timeout(k: Any = key) -> None:
                self._execute_load(cast(K, k))

            timer.timeout.connect(on_timeout)
            self._debounce_timers[key] = timer

        self._debounce_timers[key].start(self._debounce_ms)
        self._pending_keys.add(key)

    def _execute_load(self, key: K) -> None:
        self._pending_keys.discard(key)
        self._load_token[key] = self._load_token.get(key, 0) + 1
        token = self._load_token[key]
        self._loading[key] = True

        self.load_started.emit(key)

        def load_task() -> T:
            return self._loader_func(key)

        def on_finished(result: T) -> None:
            if self._load_token.get(key, 0) != token:
                return
            if self._cache_enabled:
                self._cache[key] = result
            self._loading[key] = False
            self.data_loaded.emit(key, result)
            self.load_finished.emit(key)

        def on_error(msg: str, _exc: Exception) -> None:
            if self._load_token.get(key, 0) != token:
                return
            logger.debug("AsyncDataLoader load failed for %r: %s", key, msg)
            self._loading[key] = False
            self.load_error.emit(key, msg)
            self.load_finished.emit(key)

        run_in_background(load_task, on_finished=on_finished, on_error=on_error)

    def invalidate(self, key: K) -> None:
        self._load_token[key] = self._load_token.get(key, 0) + 1
        self._cache.pop(key, None)
        self._loading[key] = False
        timer = self._debounce_timers.get(key)
        if timer is not None:
            timer.stop()
        self._pending_keys.discard(key)

    def invalidate_all(self) -> None:
        keys: Set[Any] = set(self._cache.keys()) | set(self._debounce_timers.keys()) | set(self._pending_keys)
        for k in list(keys):
            self.invalidate(cast(K, k))

    def is_loading(self, key: K) -> bool:
        return bool(self._loading.get(key, False))

    def is_pending(self, key: K) -> bool:
        return key in self._pending_keys

    def get_cached(self, key: K) -> Optional[T]:
        return self._cache.get(key)

    def cancel_pending(self, key: Optional[K] = None) -> None:
        if key is not None:
            timer = self._debounce_timers.get(key)
            if timer is not None:
                timer.stop()
            self._pending_keys.discard(key)
            self._load_token[key] = self._load_token.get(key, 0) + 1
            return
        keys = set(self._debounce_timers.keys()) | set(self._pending_keys)
        for k in list(keys):
            self.cancel_pending(cast(K, k))


class AsyncDataLoaderMixin:
    """Attach an :class:`AsyncDataLoader` as a child of ``self`` (expect ``QObject``)."""

    _async_loader: AsyncDataLoader

    def setup_async_loader(
        self,
        loader_func: Callable[[Any], Any],
        on_loaded: Optional[Callable[[Any, Any], None]] = None,
        on_error: Optional[Callable[[Any, str], None]] = None,
        on_started: Optional[Callable[[Any], None]] = None,
        debounce_ms: int = AsyncDataLoader.DEFAULT_DEBOUNCE_MS,
        cache_enabled: bool = True,
    ) -> None:
        self._async_loader = AsyncDataLoader(
            loader_func,
            parent=self,
            debounce_ms=debounce_ms,
            cache_enabled=cache_enabled,
        )
        if on_loaded is not None:
            self._async_loader.data_loaded.connect(on_loaded)
        if on_error is not None:
            self._async_loader.load_error.connect(on_error)
        if on_started is not None:
            self._async_loader.load_started.connect(on_started)

    def schedule_async_load(self, key: Hashable, force: bool = False) -> None:
        self._async_loader.schedule_load(key, force=force)

    def invalidate_async_cache(self, key: Optional[Hashable] = None) -> None:
        if key is None:
            self._async_loader.invalidate_all()
        else:
            self._async_loader.invalidate(key)

    def cancel_async_pending(self, key: Optional[Hashable] = None) -> None:
        self._async_loader.cancel_pending(key)

    def is_async_loading(self, key: Hashable) -> bool:
        return self._async_loader.is_loading(key) or self._async_loader.is_pending(key)

    def get_async_cached(self, key: Hashable) -> Any:
        return self._async_loader.get_cached(key)
