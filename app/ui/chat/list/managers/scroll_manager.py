"""Scroll position manager for chat list.

This module handles scroll position tracking and restoration
for the chat list widget.
"""

import logging
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QTimer

if TYPE_CHECKING:
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

logger = logging.getLogger(__name__)


class ScrollManager:
    """Manages scroll position for the chat list.

    This class handles:
    - Scrolling to bottom (with optional force)
    - Saving and restoring scroll position during loads
    - Load-more debouncing

    Note: Scroll position state (_user_at_bottom) is managed by QmlHandler
    which receives the scrollPositionChanged signal from QML.

    Attributes:
        _qml_root: Reference to QML root object
        _model: QML model instance
        _qml_handler: Reference to QmlHandler for state access
        _load_more_debounce_ms: Debounce delay for load more requests
    """

    # Default debounce delay for load more requests (ms)
    DEFAULT_LOAD_MORE_DEBOUNCE_MS = 300

    def __init__(self, model: "QmlAgentChatListModel", load_more_debounce_ms: int = DEFAULT_LOAD_MORE_DEBOUNCE_MS):
        """Initialize the scroll manager.

        Args:
            model: QML model instance
            load_more_debounce_ms: Debounce delay for load more requests
        """
        self._model = model
        self._qml_root = None
        self._qml_handler = None  # Will be set by widget for state access

        # Load more debounce timer - prevents excessive load requests during scroll
        self._load_more_timer = QTimer()
        self._load_more_timer.setSingleShot(True)

        self._load_more_debounce_ms = load_more_debounce_ms

    def set_qml_root(self, qml_root):
        """Set the QML root object for scroll operations.

        Args:
            qml_root: QML root object from QQuickWidget
        """
        self._qml_root = qml_root

    def set_qml_handler(self, qml_handler) -> None:
        """Set the QML handler for state access.

        Args:
            qml_handler: QmlHandler instance that manages scroll state
        """
        self._qml_handler = qml_handler

    def connect_load_more_callback(self, callback):
        """Connect the load more callback to the debounce timer.

        Args:
            callback: Function to call when debounce timer expires
        """
        self._load_more_timer.timeout.connect(callback)

    def scroll_to_bottom(self, force: bool = False) -> None:
        """Scroll the chat list to bottom.

        Args:
            force: If True, scroll regardless of user position.
                   If False, only scroll if user is already at bottom.
        """
        # Get current scroll state from QmlHandler (the source of truth)
        user_at_bottom = False
        is_scrolling = False
        if self._qml_handler:
            user_at_bottom = self._qml_handler.get_user_at_bottom()
            # Check if scrolling is in progress to avoid interrupting user
            is_scrolling = getattr(self._qml_handler, '_is_scrolling', False)

        # Skip if already scrolling to avoid interrupting scroll animation
        # This prevents the "jumping" effect during user scrolling
        if is_scrolling and not force:
            return

        if self._qml_root and (force or user_at_bottom):
            # Only flush updates if we're actually going to scroll
            # This avoids interrupting the batch update mechanism during normal scrolling
            if force:
                self._model.flush_updates()
            self._qml_root.scrollToBottom()

    def get_first_visible_message_id(self) -> Optional[str]:
        """Get the first visible message ID (approximated as first item in model).

        Returns:
            First visible message ID or None if model is empty
        """
        if self._model.rowCount() > 0:
            item = self._model.get_item(0)
            if item:
                return item.get(self._model.MESSAGE_ID)
        return None

    def save_scroll_position(self) -> Optional[str]:
        """Save the current scroll position.

        Returns:
            The message ID that was visible at the top, or None
        """
        return self.get_first_visible_message_id()

    def restore_scroll_position(self, saved_message_id: Optional[str], item_count_before_load: int = 0) -> None:
        """Restore scroll position to the previously visible message.

        Args:
            saved_message_id: The message ID that was visible before load
            item_count_before_load: The number of items before the load (for fallback)
        """
        if not saved_message_id:
            return

        if not self._qml_root:
            return

        # Find the new index of the message that was at the top
        row = self._model.get_row_by_message_id(saved_message_id)

        if row is not None and row >= 0:
            # Position the view so this message is near the top
            self._qml_root.positionViewAtIndex(row, 1)  # 1 = Beginning
        else:
            # Message not found (might have been pruned), scroll to a reasonable position
            # Use the saved message count from before the load to approximate position
            if item_count_before_load > 0:
                # Position to where the original first message is now (shifted by new items)
                new_items_count = self._model.rowCount() - item_count_before_load
                target_row = min(new_items_count, self._model.rowCount() - 1)
                self._qml_root.positionViewAtIndex(target_row, 1)  # 1 = Beginning
            else:
                # Fallback: scroll near the top but not at the very edge
                target_row = min(5, self._model.rowCount() - 1)
                self._qml_root.positionViewAtIndex(target_row, 1)  # 1 = Beginning

    def start_load_more_debounce(self) -> None:
        """Start the debounce timer for load more request."""
        self._load_more_timer.start(self._load_more_debounce_ms)
