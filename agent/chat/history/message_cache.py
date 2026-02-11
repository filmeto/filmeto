"""Message memory cache for reducing disk access.

This module provides an in-memory LRU cache for message history,
reducing repeated file reads for frequently accessed messages.

Thread Safety:
    This class uses threading.Lock for thread-safe operations.
"""

import logging
import threading
from collections import OrderedDict
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class MessageCache:
    """Thread-safe in-memory LRU cache for message data.

    Reduces repeated file reads by caching recently accessed messages.
    Messages are evicted in LRU order when the cache reaches max_size.

    Thread Safety:
        All public methods are protected by a lock for safe concurrent access.
    """

    def __init__(self, max_size: int = 1000):
        """Initialize the message cache.

        Args:
            max_size: Maximum number of messages to cache
        """
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def get(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a cached message by ID (thread-safe).

        Args:
            message_id: The message ID to look up

        Returns:
            Cached message data, or None if not found
        """
        with self._lock:
            if message_id in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(message_id)
                self._hits += 1
                return self._cache[message_id]
            self._misses += 1
            return None

    def put(self, message_id: str, message_data: Dict[str, Any]) -> None:
        """Put a message into the cache (thread-safe).

        Args:
            message_id: The message ID
            message_data: The message data to cache
        """
        with self._lock:
            if message_id in self._cache:
                # Update existing entry and move to end
                self._cache.move_to_end(message_id)
            else:
                # Add new entry, evict oldest if at capacity
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)

            self._cache[message_id] = message_data

    def put_batch(self, messages: List[Dict[str, Any]]) -> None:
        """Put multiple messages into the cache (thread-safe).

        Args:
            messages: List of message dictionaries to cache
        """
        with self._lock:
            for msg_data in messages:
                message_id = (
                    msg_data.get("message_id") or
                    msg_data.get("metadata", {}).get("message_id", "")
                )
                if message_id:
                    if message_id in self._cache:
                        self._cache.move_to_end(message_id)
                    else:
                        if len(self._cache) >= self._max_size:
                            self._cache.popitem(last=False)
                    self._cache[message_id] = msg_data

    def get_messages_after_gsn(
        self,
        last_seen_gsn: int,
        count: int,
        fetch_func: Callable[[int, int], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Get messages after a GSN, using cache first (thread-safe).

        Checks cache first for messages with GSN > last_seen_gsn.
        If cache doesn't have enough messages, calls fetch_func to get more.

        Note: fetch_func is called OUTSIDE the lock to avoid deadlock.

        Args:
            last_seen_gsn: The last GSN the caller has seen
            count: Maximum number of messages to return
            fetch_func: Function to call when cache miss occurs (last_seen_gsn, count) -> messages

        Returns:
            List of message dictionaries sorted by GSN (ascending)
        """
        # First, collect from cache (with lock)
        with self._lock:
            cached = [
                msg.copy() for msg in self._cache.values()
                if msg.get('metadata', {}).get('gsn', 0) > last_seen_gsn
            ]
            current_hit_count = self._hits
            current_miss_count = self._misses

        # Sort outside the lock
        if cached:
            cached.sort(key=lambda m: m['metadata']['gsn'])

        if len(cached) >= count:
            # Cache has all we need
            return cached[:count]

        # Cache miss or insufficient data - fetch from storage (outside lock)
        try:
            fetched = fetch_func(last_seen_gsn, count)

            # Update cache with fetched messages
            if fetched:
                self.put_batch(fetched)

            return fetched
        except Exception as e:
            logger.error(f"Error in fetch_func: {e}", exc_info=True)
            return cached[:count] if cached else []

    def invalidate(self, message_id: str) -> None:
        """Remove a specific message from cache (thread-safe).

        Args:
            message_id: The message ID to invalidate
        """
        with self._lock:
            if message_id in self._cache:
                del self._cache[message_id]

    def clear(self) -> None:
        """Clear all cached messages (thread-safe)."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def size(self) -> int:
        """Return current cache size (thread-safe)."""
        with self._lock:
            return len(self._cache)

    def hit_rate(self) -> float:
        """Return cache hit rate (0.0 to 1.0) (thread-safe)."""
        with self._lock:
            total = self._hits + self._misses
            if total == 0:
                return 0.0
            return self._hits / total

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics (thread-safe)."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0.0
            }

    def __contains__(self, message_id: str) -> bool:
        """Check if a message ID is in the cache (thread-safe)."""
        with self._lock:
            return message_id in self._cache

    def __len__(self) -> int:
        """Return current cache size (thread-safe)."""
        with self._lock:
            return len(self._cache)


# Global cache instances keyed by workspace||project
_global_caches: Dict[str, MessageCache] = {}
_global_cache_lock = threading.Lock()


def get_cache(workspace_path: str, project_name: str, max_size: int = 1000) -> MessageCache:
    """Get or create a cache instance for a workspace/project (thread-safe).

    Args:
        workspace_path: Path to workspace
        project_name: Name of project
        max_size: Maximum cache size (only used on first call)

    Returns:
        MessageCache instance
    """
    key = f"{workspace_path}||{project_name}"
    with _global_cache_lock:
        if key not in _global_caches:
            _global_caches[key] = MessageCache(max_size=max_size)
        return _global_caches[key]


def clear_cache(workspace_path: str, project_name: str) -> None:
    """Clear the cache for a specific workspace/project (thread-safe).

    Args:
        workspace_path: Path to workspace
        project_name: Name of project
    """
    key = f"{workspace_path}||{project_name}"
    with _global_cache_lock:
        if key in _global_caches:
            _global_caches[key].clear()


def clear_all_caches() -> None:
    """Clear all global caches (thread-safe)."""
    with _global_cache_lock:
        for cache in _global_caches.values():
            cache.clear()
        _global_caches.clear()
