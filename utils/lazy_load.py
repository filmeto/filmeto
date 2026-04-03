"""Shared lazy-load helpers for sync + asyncio paths."""

from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod


class AsyncLazyLoadMixin(ABC):
    """Thread-safe lazy load; subclasses must set ``_loaded`` and ``_load_lock`` in ``__init__``."""

    _loaded: bool
    _load_lock: threading.Lock

    @abstractmethod
    def _do_load(self) -> None:
        """Populate in-memory state from disk (no ``_loaded`` flag management)."""

    def _lazy_load_require_attrs(self) -> None:
        if not hasattr(self, "_load_lock") or not hasattr(self, "_loaded"):
            raise TypeError(
                f"{type(self).__name__} must assign _load_lock and _loaded in __init__ "
                "before using AsyncLazyLoadMixin"
            )

    def _clear_internal_state(self) -> None:
        """Clear in-memory caches; called with ``_load_lock`` held."""
        return

    def _get_async_load_lock(self) -> asyncio.Lock:
        if getattr(self, "_async_load_lock", None) is None:
            self._async_load_lock = asyncio.Lock()
        return self._async_load_lock

    async def _do_load_async(self) -> None:
        """Disk I/O entry point for async callers; override for true async loads."""
        await asyncio.to_thread(self._do_load)

    def _ensure_loaded(self) -> None:
        self._lazy_load_require_attrs()
        if not self._loaded:
            with self._load_lock:
                if not self._loaded:
                    self._do_load()
                    self._loaded = True

    async def ensure_loaded_async(self) -> None:
        self._lazy_load_require_attrs()
        if self._loaded:
            return
        lock = self._get_async_load_lock()
        async with lock:
            if not self._loaded:
                await self._do_load_async()
                self._loaded = True

    def invalidate_cache(self) -> None:
        self._lazy_load_require_attrs()
        with self._load_lock:
            self._clear_internal_state()
            self._loaded = False
