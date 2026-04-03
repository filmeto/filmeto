"""
Generic async data loader with debouncing, optional caching, and race protection.

Loads run via ``run_in_background`` after a per-key debounce delay. A monotonic
token per key is incremented when a load actually starts (after debounce), so
late completions from superseded runs are ignored.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Generic, Hashable, Iterable, Optional, Set, TypeVar, cast

from PySide6.QtCore import QObject, QTimer, Signal

from app.ui.worker.worker import BackgroundWorker, run_in_background

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
        self._active_workers: Dict[Any, BackgroundWorker] = {}

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

    def schedule_load_batch(self, keys: Iterable[K], force: bool = False) -> None:
        """Queue debounced loads for multiple keys (same rules as :meth:`schedule_load`)."""
        for key in keys:
            self.schedule_load(key, force=force)

    def _execute_load(self, key: K) -> None:
        self._pending_keys.discard(key)
        prev = self._active_workers.pop(key, None)
        if prev is not None:
            prev.stop()

        self._load_token[key] = self._load_token.get(key, 0) + 1
        token = self._load_token[key]
        self._loading[key] = True

        self.load_started.emit(key)

        def load_task() -> T:
            return self._loader_func(key)

        worker: Optional[BackgroundWorker] = None

        def on_finished(result: T) -> None:
            nonlocal worker
            if self._active_workers.get(key) is worker:
                self._active_workers.pop(key, None)
            if self._load_token.get(key, 0) != token:
                return
            if self._cache_enabled:
                self._cache[key] = result
            self._loading[key] = False
            self.data_loaded.emit(key, result)
            self.load_finished.emit(key)

        def on_error(msg: str, _exc: Exception) -> None:
            nonlocal worker
            if self._active_workers.get(key) is worker:
                self._active_workers.pop(key, None)
            if self._load_token.get(key, 0) != token:
                return
            logger.debug("AsyncDataLoader load failed for %r: %s", key, msg)
            self._loading[key] = False
            self.load_error.emit(key, msg)
            self.load_finished.emit(key)

        worker = run_in_background(load_task, on_finished=on_finished, on_error=on_error)
        self._active_workers[key] = worker

    def invalidate(self, key: K) -> None:
        w = self._active_workers.pop(key, None)
        if w is not None:
            w.stop()
        self._load_token[key] = self._load_token.get(key, 0) + 1
        self._cache.pop(key, None)
        self._loading[key] = False
        timer = self._debounce_timers.get(key)
        if timer is not None:
            timer.stop()
        self._pending_keys.discard(key)

    def invalidate_all(self) -> None:
        keys: Set[Any] = (
            set(self._cache.keys())
            | set(self._debounce_timers.keys())
            | set(self._pending_keys)
            | set(self._active_workers.keys())
            | {k for k, active in self._loading.items() if active}
        )
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
            self._loading[key] = False
            return
        keys: Set[Any] = (
            set(self._debounce_timers.keys())
            | set(self._pending_keys)
            | set(self._cache.keys())
            | {k for k, active in self._loading.items() if active}
        )
        for k in list(keys):
            self.cancel_pending(cast(K, k))

    def cancel_load(self, key: Optional[K] = None) -> None:
        """Cancel debounced (not yet started) and in-flight loads for ``key`` (or all keys if None)."""

        def _cancel_one(k: Any) -> None:
            timer = self._debounce_timers.get(k)
            if timer is not None:
                timer.stop()
            self._pending_keys.discard(k)
            w = self._active_workers.pop(k, None)
            if w is not None:
                w.stop()
            self._load_token[k] = self._load_token.get(k, 0) + 1
            self._loading[k] = False

        if key is not None:
            _cancel_one(key)
            return
        keys: Set[Any] = (
            set(self._debounce_timers.keys())
            | set(self._pending_keys)
            | set(self._active_workers.keys())
            | set(self._cache.keys())
            | {k for k, active in self._loading.items() if active}
        )
        for k in list(keys):
            _cancel_one(k)


class AsyncDataLoaderMixin(QObject):
    """Adds a child :class:`AsyncDataLoader`; the concrete widget must also inherit ``QObject`` (e.g. ``QWidget``)."""

    _async_loader: AsyncDataLoader[Any, Any]

    def setup_async_loader(
        self,
        loader_func: Callable[[K], T],
        on_loaded: Optional[Callable[[K, T], None]] = None,
        on_error: Optional[Callable[[K, str], None]] = None,
        on_started: Optional[Callable[[K], None]] = None,
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

    def schedule_async_load_batch(self, keys: Iterable[Hashable], force: bool = False) -> None:
        self._async_loader.schedule_load_batch(keys, force=force)

    def invalidate_async_cache(self, key: Optional[Hashable] = None) -> None:
        if key is None:
            self._async_loader.invalidate_all()
        else:
            self._async_loader.invalidate(key)

    def cancel_async_pending(self, key: Optional[Hashable] = None) -> None:
        self._async_loader.cancel_pending(key)

    def cancel_async_load(self, key: Optional[Hashable] = None) -> None:
        self._async_loader.cancel_load(key)

    def is_async_loading(self, key: Hashable) -> bool:
        return self._async_loader.is_loading(key) or self._async_loader.is_pending(key)

    def get_async_cached(self, key: Hashable) -> Any:
        return self._async_loader.get_cached(key)
