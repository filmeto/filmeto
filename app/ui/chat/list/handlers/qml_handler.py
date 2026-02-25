"""QML signal handler for chat list widget.

This module handles QML signal connections and interactions between
Python and QML layers.
"""

import logging
from typing import Optional, TYPE_CHECKING, Callable

from PySide6.QtCore import QTimer

if TYPE_CHECKING:
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

logger = logging.getLogger(__name__)


class QmlHandler:
    """Handles QML signal connections and interactions.

    This class manages:
    - QML signal connections and disconnections
    - QML signal handling (referenceClicked, messageCompleted, loadMoreRequested, scrollPositionChanged)
    - QML method invocation (scrollToBottom, positionViewAtIndex)
    - Load-more debouncing

    Attributes:
        _model: QML model instance
        _qml_root: Reference to QML root object
        _user_at_bottom: Whether user is currently at bottom of list
        _load_more_debounce_ms: Debounce delay for load more requests
        _is_scrolling: Whether scroll animation is currently in progress
    """

    # Default debounce delay for load more requests (ms)
    DEFAULT_LOAD_MORE_DEBOUNCE_MS = 300

    def __init__(
        self,
        model: "QmlAgentChatListModel",
        load_more_debounce_ms: int = DEFAULT_LOAD_MORE_DEBOUNCE_MS
    ):
        """Initialize the QML handler.

        Args:
            model: QML model instance
            load_more_debounce_ms: Debounce delay for load more requests
        """
        self._model = model
        self._qml_root: Optional = None
        self._user_at_bottom = True
        self._is_scrolling = False  # Track if scroll animation is in progress
        self._load_more_debounce_ms = load_more_debounce_ms

        # Callbacks (to be set by widget)
        self._on_reference_clicked_callback: Optional[Callable] = None
        self._on_message_completed_callback: Optional[Callable] = None
        self._on_load_more_callback: Optional[Callable] = None

        # Debounce timer
        self._debounce_timer = None

    def set_qml_root(self, qml_root) -> None:
        """Set the QML root object and connect signals.

        Args:
            qml_root: QML root object from QQuickWidget
        """
        self._qml_root = qml_root

        # Connect QML signals to Python
        if self._qml_root:
            self._qml_root.referenceClicked.connect(self._on_qml_reference_clicked)
            self._qml_root.messageCompleted.connect(self._on_qml_message_completed)
            self._qml_root.loadMoreRequested.connect(self._on_qml_load_more)
            self._qml_root.scrollPositionChanged.connect(self._on_qml_scroll_position_changed)

            logger.info("QML signals connected")

    def set_callbacks(
        self,
        on_reference_clicked: Optional[Callable] = None,
        on_message_completed: Optional[Callable] = None,
        on_load_more: Optional[Callable] = None,
    ) -> None:
        """Set callbacks for QML events.

        Args:
            on_reference_clicked: Called when user clicks a reference (ref_type, ref_id)
            on_message_completed: Called when message finishes streaming (message_id, agent_name)
            on_load_more: Called when user scrolls to top and more messages should load
        """
        self._on_reference_clicked_callback = on_reference_clicked
        self._on_message_completed_callback = on_message_completed
        self._on_load_more_callback = on_load_more

    def set_debounce_timer(self, timer) -> None:
        """Set the debounce timer for load more requests.

        Args:
            timer: QTimer instance for debouncing
        """
        self._debounce_timer = timer

    def _on_qml_reference_clicked(self, ref_type: str, ref_id: str) -> None:
        """Handle reference click from QML.

        Args:
            ref_type: Type of reference (e.g., 'file', 'url')
            ref_id: ID of the referenced item
        """
        if self._on_reference_clicked_callback:
            self._on_reference_clicked_callback(ref_type, ref_id)

    def _on_qml_message_completed(self, message_id: str, agent_name: str) -> None:
        """Handle message completion from QML.

        Args:
            message_id: ID of the completed message
            agent_name: Name of the agent that sent the message
        """
        if self._on_message_completed_callback:
            self._on_message_completed_callback(message_id, agent_name)

    def _on_qml_load_more(self) -> None:
        """Handle load more request from QML (scroll to top) with debounce."""
        if self._debounce_timer:
            self._debounce_timer.start(self._load_more_debounce_ms)

    # Maximum duration for _is_scrolling state to prevent permanent lockup
    SCROLL_STATE_RESET_MS = 300

    def _on_qml_scroll_position_changed(self, at_bottom: bool) -> None:
        """Handle scroll position change from QML.

        Args:
            at_bottom: Whether user is at bottom of list
        """
        # Detect if scrolling is in progress by checking if at_bottom state changed
        was_at_bottom = self._user_at_bottom
        self._user_at_bottom = at_bottom

        # Mark scrolling as in progress if at_bottom state changed
        # This prevents excessive scroll-to-bottom calls during user scrolling
        if was_at_bottom != at_bottom:
            self._is_scrolling = True
            # Use static QTimer.singleShot to avoid conflict with load-more debounce timer
            QTimer.singleShot(self.SCROLL_STATE_RESET_MS, self._reset_scrolling_flag)
    
    def _reset_scrolling_flag(self) -> None:
        """Reset the scrolling flag after scroll animation completes."""
        self._is_scrolling = False

    def scroll_to_bottom(self, force: bool = False) -> None:
        """Scroll the chat list to bottom.

        Args:
            force: If True, scroll regardless of user position.
                   If False, only scroll if user is already at bottom.
        """
        # Skip if already scrolling to avoid interrupting scroll animation
        # This prevents the "jumping" effect during user scrolling
        if self._is_scrolling and not force:
            return
        
        if self._qml_root and (force or self._user_at_bottom):
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
            if item_count_before_load > 0:
                # Position to where the original first message is now (shifted by new items)
                new_items_count = self._model.rowCount() - item_count_before_load
                target_row = min(new_items_count, self._model.rowCount() - 1)
                self._qml_root.positionViewAtIndex(target_row, 1)  # 1 = Beginning
            else:
                # Fallback: scroll near the top but not at the very edge
                target_row = min(5, self._model.rowCount() - 1)
                self._qml_root.positionViewAtIndex(target_row, 1)  # 1 = Beginning

    def get_user_at_bottom(self) -> bool:
        """Check if user is currently at bottom of list.

        Returns:
            True if user is at bottom, False otherwise
        """
        return self._user_at_bottom

    def set_loading_older(self, loading: bool) -> None:
        """Set the loading older state on QML.

        Args:
            loading: Whether currently loading older messages
        """
        if self._qml_root:
            self._qml_root.setProperty("isLoadingOlder", loading)

    def refresh_model_binding(self, quick_widget) -> None:
        """Force QML to refresh the model binding.

        Args:
            quick_widget: The QQuickWidget instance
        """
        if self._qml_root:
            # Re-set the context property to trigger QML update
            quick_widget.rootContext().setContextProperty("_chatModel", None)
            quick_widget.rootContext().setContextProperty("_chatModel", self._model)
