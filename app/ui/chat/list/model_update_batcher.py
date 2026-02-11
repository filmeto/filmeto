"""Model update batcher for reducing QML rendering frequency.

This module provides batching of model updates to reduce the frequency
of QML re-rendering during rapid message updates (e.g., streaming responses).
"""

import logging
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, QTimer

from app.ui.chat.list.qml_agent_chat_list_model import QmlAgentChatListModel

logger = logging.getLogger(__name__)


class ModelUpdateBatcher(QObject):
    """Batches model updates to reduce QML rendering frequency.

    Instead of triggering a dataChanged signal for every single update,
    this batcher collects updates over a short time window and emits
    a single combined signal.

    Usage:
        batcher = ModelUpdateBatcher(model, batch_interval_ms=100)

        # Schedule updates - they won't trigger immediate render
        batcher.schedule_update(message_id, {"content": "new text"})

        # After batch_interval_ms, all pending updates are applied at once
    """

    def __init__(
        self,
        model: QmlAgentChatListModel,
        batch_interval_ms: int = 100,
        parent: Optional[QObject] = None
    ):
        """Initialize the update batcher.

        Args:
            model: The QmlAgentChatListModel to batch updates for
            batch_interval_ms: Milliseconds to wait before flushing updates
            parent: Parent QObject
        """
        super().__init__(parent)

        self._model = model
        self._batch_interval_ms = batch_interval_ms
        self._pending_updates: Dict[str, Dict[str, Any]] = {}
        self._pending_adds: list = []

        # Timer for flushing updates
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush_updates)

    def schedule_update(self, message_id: str, updates: Dict[str, Any]) -> None:
        """Schedule a model update for batching.

        Args:
            message_id: ID of the message to update
            updates: Dictionary of fields to update
        """
        # Merge with existing pending updates for this message
        if message_id in self._pending_updates:
            self._pending_updates[message_id].update(updates)
        else:
            self._pending_updates[message_id] = dict(updates)

        # Reset/start the timer
        self._timer.start(self._batch_interval_ms)

    def schedule_add(self, item: Dict[str, Any]) -> None:
        """Schedule a model add for batching.

        Args:
            item: The item to add to the model
        """
        self._pending_adds.append(item)
        self._timer.start(self._batch_interval_ms)

    def _flush_updates(self) -> None:
        """Flush all pending updates to the model.

        This is called automatically by the timer. It processes all
        pending updates and emits a single dataChanged signal.
        """
        if not self._pending_updates and not self._pending_adds:
            return

        try:
            # First, handle any pending adds
            while self._pending_adds:
                item = self._pending_adds.pop(0)
                self._model.add_item(item)

            # Then, handle updates
            if not self._pending_updates:
                return

            # Collect all row indices that need updating
            rows_to_update = []
            for message_id in self._pending_updates:
                row = self._model.get_row_by_message_id(message_id)
                if row is not None:
                    rows_to_update.append(row)

            if not rows_to_update:
                self._pending_updates.clear()
                return

            # Apply all updates
            for message_id, updates in self._pending_updates.items():
                row = self._model.get_row_by_message_id(message_id)
                if row is not None:
                    item = self._model.get_item(row)
                    if item:
                        item.update(updates)

            # Emit single dataChanged for all affected rows
            min_row = min(rows_to_update)
            max_row = max(rows_to_update)

            from PySide6.QtCore import QModelIndex
            start_index = self._model.index(min_row, 0)
            end_index = self._model.index(max_row, 0)
            self._model.dataChanged.emit(start_index, end_index)

            logger.debug(f"Flushed {len(self._pending_updates)} batched updates")

        except Exception as e:
            logger.error(f"Error flushing batched updates: {e}", exc_info=True)
        finally:
            self._pending_updates.clear()
            self._pending_adds.clear()

    def flush_now(self) -> None:
        """Immediately flush pending updates without waiting for timer.

        Call this when you need updates to be applied immediately,
        such as when the user is about to interact with the UI.
        """
        if self._timer.isActive():
            self._timer.stop()
        self._flush_updates()

    def has_pending(self) -> bool:
        """Check if there are pending updates.

        Returns:
            True if there are pending updates or adds
        """
        return bool(self._pending_updates or self._pending_adds)

    def clear_pending(self) -> None:
        """Clear all pending updates without applying them."""
        self._pending_updates.clear()
        self._pending_adds.clear()
        if self._timer.isActive():
            self._timer.stop()

    def set_batch_interval(self, interval_ms: int) -> None:
        """Change the batch interval.

        Args:
            interval_ms: New batch interval in milliseconds
        """
        self._batch_interval_ms = interval_ms
        self._timer.setInterval(interval_ms)
