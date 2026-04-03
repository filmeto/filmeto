"""History manager for chat list message loading and caching.

This module handles loading messages from history storage, including
pagination, GSN-based fetching, and cache management.

Architecture:
- Storage layer: returns raw messages as stored (no merging)
- MessageBuilder: handles ALL grouping and merging logic
- HistoryManager: coordinates loading and delegates to MessageBuilder
"""

import copy
import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING, Callable

from PySide6.QtCore import QTimer

from app.ui.chat.list.agent_chat_list_items import LoadState
from app.ui.workers.background_worker import BackgroundWorker, run_in_background

if TYPE_CHECKING:
    from app.data.workspace import Workspace
    from app.ui.chat.list.builders.message_builder import MessageBuilder
    from app.ui.chat.list.agent_chat_list_model import AgentChatListModel

logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages history loading and caching for the chat list.

    This class handles:
    - History service management and caching
    - Loading recent conversation on startup
    - Loading older messages (pagination)
    - Loading new messages (via signal/timer)
    - GSN-based message fetching
    - Message pruning (top/bottom)
    - Storage signal handling

    Attributes:
        _workspace: Workspace instance
        _model: QML model instance
        _message_builder: Message builder instance
        _history: Cached MessageLogHistory instance
        _load_state: Current loading state
        _loading_older: Whether currently loading older messages
    """

    # Configuration constants
    PAGE_SIZE = 200
    MAX_MODEL_ITEMS = 300
    NEW_DATA_CHECK_INTERVAL_MS = 500

    def __init__(
        self,
        workspace: "Workspace",
        model: "AgentChatListModel",
        message_builder: "MessageBuilder",
    ):
        """Initialize the history manager.

        Args:
            workspace: Workspace instance
            model: QML model instance
            message_builder: Message builder instance
        """
        self._workspace = workspace
        self._model = model
        self._message_builder = message_builder

        # State
        self._history = None
        self._load_state = LoadState()
        self._loading_older = False

        # New data check timer
        self._new_data_check_timer = QTimer()
        self._new_data_check_timer.timeout.connect(self._check_for_new_data)

        # Guard flags for async loads
        self._loading_recent = False
        self._recent_worker: Optional[BackgroundWorker] = None
        self._older_worker: Optional[BackgroundWorker] = None

        # Callbacks (to be set by widget)
        self._on_load_more_callback: Optional[Callable] = None
        self._on_message_loaded_callback: Optional[Callable] = None
        self._refresh_qml_callback: Optional[Callable] = None
        self._scroll_to_bottom_callback: Optional[Callable] = None
        self._get_first_visible_message_id_callback: Optional[Callable] = None
        self._restore_scroll_position_callback: Optional[Callable] = None

        # QML root reference (set by widget)
        self._qml_root = None

    def _cancel_background_loads(self) -> None:
        for w in (self._recent_worker, self._older_worker):
            if w is not None:
                w.stop()
        self._recent_worker = None
        self._older_worker = None
        self._loading_recent = False
        self._loading_older = False

    def set_qml_root(self, qml_root) -> None:
        """Set the QML root object.

        Args:
            qml_root: QML root object from QQuickWidget
        """
        self._qml_root = qml_root

    def set_callbacks(
        self,
        on_load_more: Optional[Callable] = None,
        on_message_loaded: Optional[Callable] = None,
        refresh_qml: Optional[Callable] = None,
        scroll_to_bottom: Optional[Callable] = None,
        get_first_visible_message_id: Optional[Callable] = None,
        restore_scroll_position: Optional[Callable] = None,
    ) -> None:
        """Set callbacks for history events.

        Args:
            on_load_more: Called when more messages need to be loaded
            on_message_loaded: Called when a message is loaded
            refresh_qml: Called to refresh QML model binding
            scroll_to_bottom: Called to scroll to bottom
            get_first_visible_message_id: Called to get first visible message
            restore_scroll_position: Called to restore scroll position
        """
        self._on_load_more_callback = on_load_more
        self._on_message_loaded_callback = on_message_loaded
        self._refresh_qml_callback = refresh_qml
        self._scroll_to_bottom_callback = scroll_to_bottom
        self._get_first_visible_message_id_callback = get_first_visible_message_id
        self._restore_scroll_position_callback = restore_scroll_position

    def get_history(self):
        """Get or create cached history instance.

        Returns:
            MessageLogHistory instance or None
        """
        if self._history is None:
            workspace_path = self._workspace.workspace_path
            project_name = self._workspace.project_name
            if workspace_path and project_name:
                from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
                self._history = FastMessageHistoryService.get_history(
                    workspace_path, project_name
                )
        return self._history

    def load_recent_conversation(self) -> None:
        """Load recent conversation from history off the UI thread.

        The heavy work (disk IO + message building) runs in a BackgroundWorker.
        Only Qt-model mutations run on the main thread in the finished callback.
        """
        if self._loading_recent:
            return
        self._loading_recent = True

        workspace_path = self._workspace.workspace_path
        project_name = self._workspace.project_name
        page_size = self.PAGE_SIZE
        message_builder = self._message_builder

        def _fetch() -> Optional[Dict[str, Any]]:
            """Runs in background thread: IO + parsing, no Qt model access."""
            try:
                project = self._workspace.get_project()
                if not project:
                    return None

                history = self.get_history()
                if not history:
                    return None

                raw_messages = history.get_latest_messages(count=page_size)
                active_log_count = history.storage.get_message_count()
                total_count = history.get_total_count()

                current_gsn = 0
                try:
                    from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
                    current_gsn = FastMessageHistoryService.get_current_gsn(
                        workspace_path, project_name
                    )
                except Exception as e:
                    logger.debug(f"Could not initialize GSN tracking: {e}")

                max_gsn = 0
                min_gsn = float('inf')
                for msg_data in raw_messages:
                    msg_gsn = msg_data.get('metadata', {}).get('gsn', 0)
                    if msg_gsn > max_gsn:
                        max_gsn = msg_gsn
                    if msg_gsn > 0 and msg_gsn < min_gsn:
                        min_gsn = msg_gsn

                from app.ui.chat.list.builders.message_converter import MessageConverter
                items = message_builder.build_items_from_raw_messages(raw_messages)
                qml_items = [
                    MessageConverter.from_chat_list_item(item) for item in items
                ]

                return {
                    "qml_items": qml_items,
                    "raw_count": len(raw_messages),
                    "total_count": total_count,
                    "active_log_count": active_log_count,
                    "max_gsn": max_gsn,
                    "min_gsn": min_gsn if min_gsn != float('inf') else 0,
                    "current_gsn": current_gsn,
                    "message_ids": [item.message_id for item in items],
                }
            except Exception as e:
                logger.error(f"Background fetch error (recent): {e}", exc_info=True)
                return None

        def _on_finished(result: Optional[Dict[str, Any]]) -> None:
            """Runs on main thread: update Qt model and load state."""
            self._loading_recent = False
            self._recent_worker = None
            try:
                self._model.clear()
                self._load_state.known_message_ids.clear()
                self._load_state.unique_message_count = 0
                self._load_state.total_loaded_count = 0
                self._load_state.has_more_older = False

                if not result:
                    logger.info("No messages found in history")
                    return

                qml_items = result["qml_items"]
                # Filter duplicates then insert all at once (single rowsInserted signal)
                new_qml_items = []
                for qml_item, msg_id in zip(qml_items, result["message_ids"]):
                    if msg_id not in self._load_state.known_message_ids:
                        new_qml_items.append(qml_item)
                        self._load_state.known_message_ids.add(msg_id)
                self._model.add_items_batch(new_qml_items)

                self._load_state.active_log_count = result["active_log_count"]
                self._load_state.current_line_offset = result["active_log_count"]
                self._load_state.last_seen_gsn = result["max_gsn"]
                self._load_state.min_loaded_gsn = result["min_gsn"]
                self._load_state.unique_message_count = len(qml_items)
                self._load_state.total_loaded_count = result["raw_count"]
                self._load_state.has_more_older = result["raw_count"] < result["total_count"]
                if result["current_gsn"] > 0 and self._load_state.current_gsn == 0:
                    self._load_state.current_gsn = result["current_gsn"]

                logger.info(
                    f"Loaded {len(qml_items)} unique messages from {result['raw_count']} "
                    f"raw records (total in storage: {result['total_count']})"
                )

                if self._refresh_qml_callback:
                    self._refresh_qml_callback()
                if self._scroll_to_bottom_callback:
                    QTimer.singleShot(0, lambda: self._scroll_to_bottom_callback(force=True))

            except Exception as e:
                logger.error(f"Error applying recent conversation to model: {e}", exc_info=True)

        def _on_error(msg: str, exc) -> None:
            self._loading_recent = False
            self._recent_worker = None
            logger.error(f"Background load_recent_conversation error: {msg}")

        self._recent_worker = run_in_background(
            _fetch,
            on_finished=_on_finished,
            on_error=_on_error,
            task_type="chat_history_recent",
        )

    def load_older_messages(self) -> None:
        """Load older messages when user scrolls to top (background thread).

        The heavy work (disk IO + message building) runs in a BackgroundWorker.
        Only Qt-model mutations and load-state updates run on the main thread.
        """
        if self._loading_older or not self._load_state.has_more_older:
            return

        self._loading_older = True
        if self._qml_root:
            self._qml_root.setProperty("isLoadingOlder", True)

        min_loaded_gsn = self._load_state.min_loaded_gsn
        known_ids_snapshot = set(self._load_state.known_message_ids)
        page_size = self.PAGE_SIZE
        message_builder = self._message_builder
        workspace_path = self._workspace.workspace_path
        project_name = self._workspace.project_name

        def _fetch() -> Optional[Dict[str, Any]]:
            """Runs in background thread: IO + parsing."""
            try:
                from agent.chat.history.global_sequence_manager import get_enhanced_history

                enhanced_history = get_enhanced_history(workspace_path, project_name)
                older_messages = enhanced_history.get_messages_before_gsn(
                    min_loaded_gsn, count=page_size
                )
                total_count = enhanced_history.get_total_count()

                if not older_messages:
                    return {"empty": True, "total_count": total_count}

                batch_min_gsn = min_loaded_gsn
                for msg_data in older_messages:
                    msg_gsn = msg_data.get('metadata', {}).get('gsn', 0)
                    if msg_gsn > 0 and msg_gsn < batch_min_gsn:
                        batch_min_gsn = msg_gsn

                from app.ui.chat.list.builders.message_converter import MessageConverter
                all_items = message_builder.build_items_from_raw_messages(older_messages)
                new_items = [i for i in all_items if i.message_id not in known_ids_snapshot]
                qml_items = [
                    MessageConverter.from_chat_list_item(item) for item in new_items
                ]

                return {
                    "empty": False,
                    "qml_items": qml_items,
                    "message_ids": [i.message_id for i in new_items],
                    "raw_count": len(older_messages),
                    "batch_min_gsn": batch_min_gsn,
                    "total_count": total_count,
                }
            except Exception as e:
                logger.error(f"Background fetch error (older): {e}", exc_info=True)
                return None

        def _on_finished(result: Optional[Dict[str, Any]]) -> None:
            """Runs on main thread: update Qt model and load state."""
            try:
                if not result or result.get("empty"):
                    self._load_state.has_more_older = False
                    return

                qml_items = result["qml_items"]
                new_ids = result["message_ids"]

                if qml_items:
                    first_visible_id = None
                    item_count_before_load = self._model.rowCount()
                    if self._get_first_visible_message_id_callback:
                        first_visible_id = self._get_first_visible_message_id_callback()

                    self._model.prepend_items(qml_items)
                    for msg_id in new_ids:
                        self._load_state.known_message_ids.add(msg_id)

                    self._load_state.unique_message_count += len(qml_items)
                    self._load_state.total_loaded_count += result["raw_count"]

                    if result["batch_min_gsn"] < self._load_state.min_loaded_gsn:
                        self._load_state.min_loaded_gsn = result["batch_min_gsn"]

                    self._prune_model_bottom()

                    if first_visible_id and self._restore_scroll_position_callback:
                        saved_id = first_visible_id
                        QTimer.singleShot(
                            0,
                            lambda: self._restore_scroll_position_callback(
                                saved_id, item_count_before_load
                            ),
                        )

                    logger.debug(
                        f"Prepended {len(qml_items)} older messages from "
                        f"{result['raw_count']} raw records, "
                        f"new min_gsn={self._load_state.min_loaded_gsn}"
                    )

                self._load_state.has_more_older = (
                    self._load_state.total_loaded_count < result["total_count"]
                )

            except Exception as e:
                logger.error(f"Error applying older messages to model: {e}", exc_info=True)
            finally:
                self._loading_older = False
                self._older_worker = None
                if self._qml_root:
                    self._qml_root.setProperty("isLoadingOlder", False)

        def _on_error(msg: str, exc) -> None:
            self._loading_older = False
            self._older_worker = None
            if self._qml_root:
                self._qml_root.setProperty("isLoadingOlder", False)
            logger.error(f"Background load_older_messages error: {msg}")

        self._older_worker = run_in_background(
            _fetch,
            on_finished=_on_finished,
            on_error=_on_error,
            task_type="chat_history_older",
        )

    def _prune_model_bottom(self) -> None:
        """Remove excess items from bottom in one batch."""
        excess = self._model.rowCount() - self.MAX_MODEL_ITEMS
        if excess <= 0:
            return
        count = self._model.rowCount()
        for row in range(count - excess, count):
            item = self._model.get_item(row)
            if item:
                msg_id = item.get(self._model.MESSAGE_ID)
                if msg_id and msg_id in self._load_state.known_message_ids:
                    self._load_state.known_message_ids.discard(msg_id)
        self._model.remove_last_n(excess)

    def _prune_model_top(self) -> None:
        """Remove excess items from top in one batch."""
        excess = self._model.rowCount() - self.MAX_MODEL_ITEMS
        if excess <= 0:
            return
        for row in range(excess):
            item = self._model.get_item(row)
            if item:
                msg_id = item.get(self._model.MESSAGE_ID)
                if msg_id and msg_id in self._load_state.known_message_ids:
                    self._load_state.known_message_ids.discard(msg_id)
        self._model.remove_first_n(excess)
        self._load_state.has_more_older = True

    def clear_all_caches_and_model(self) -> None:
        """Clear all caches and the model."""
        self._cancel_background_loads()
        self._model.clear()
        self._load_state.known_message_ids.clear()
        self._load_state.unique_message_count = 0
        self._load_state.total_loaded_count = 0
        self._load_state.min_loaded_gsn = 0
        self._load_state.has_more_older = False
        # Note: GSN tracking is NOT reset here to maintain state across UI refreshes

    def on_project_switched(self) -> None:
        """Handle project switch."""
        self._cancel_background_loads()
        self._stop_new_data_check_timer()
        self._load_state = LoadState()
        self._loading_older = False
        self._history = None
        self._model.clear()
        self.load_recent_conversation()

    def connect_to_storage_signals(self) -> None:
        """Connect to storage signals for storage-driven refresh."""
        try:
            from agent.chat.history.agent_chat_history_service import message_saved
            message_saved.connect(self._on_message_saved, weak=False)
            logger.debug("Connected to message_saved signal")
        except Exception as e:
            logger.error(f"Error connecting to message_saved signal: {e}")

    def disconnect_from_storage_signals(self) -> None:
        """Disconnect from storage signals."""
        try:
            from agent.chat.history.agent_chat_history_service import message_saved
            message_saved.disconnect(self._on_message_saved)
            logger.debug("Disconnected from message_saved signal")
        except Exception:
            pass  # Signal might not be connected

    def _on_message_saved(
        self,
        sender,
        workspace_path: str,
        project_name: str,
        message_id: str,
        gsn: int = 0,
        current_gsn: int = 0
    ) -> None:
        """Handle message_saved signal from storage.

        Args:
            sender: Signal sender
            workspace_path: Path to workspace
            project_name: Name of project
            message_id: ID of the saved message
            gsn: Global sequence number of the saved message
            current_gsn: Current (latest) GSN in the system
        """
        # Only refresh if this message belongs to our current project
        if (workspace_path == self._workspace.workspace_path and
            project_name == self._workspace.project_name):
            # Update current GSN tracking
            if current_gsn > 0:
                self._load_state.current_gsn = current_gsn

            # Load new messages from storage using GSN-based fetching
            self._load_new_messages_from_history(gsn, current_gsn)

    def _start_new_data_check_timer(self) -> None:
        """Start the timer to check for new data."""
        self._new_data_check_timer.start(self.NEW_DATA_CHECK_INTERVAL_MS)

    def _stop_new_data_check_timer(self) -> None:
        """Stop the new data check timer."""
        self._new_data_check_timer.stop()

    def _check_for_new_data(self) -> None:
        """Check for new data by comparing active log count.

        This method is called both by the timer (backup) and by message_saved signal.

        Enhanced with GSN support for archive-aware checking.
        """
        try:
            # Try to use GSN-based checking first
            from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

            current_gsn = FastMessageHistoryService.get_current_gsn(
                self._workspace.workspace_path,
                self._workspace.project_name
            )

            # Check if we have new messages via GSN
            if current_gsn > self._load_state.current_gsn:
                self._load_state.current_gsn = current_gsn
                self._load_new_messages_from_history(current_gsn, current_gsn)
                return

            # Fallback to legacy line-based checking
            history = self.get_history()
            if not history:
                return

            # Use active log count for fast checking (O(1) cached value)
            current_count = history.storage.get_message_count()

            # Check if new messages were added to active log
            if current_count > self._load_state.active_log_count:
                self._load_state.active_log_count = current_count
                self._load_new_messages_from_history()

        except Exception as e:
            logger.error(f"Error checking for new data: {e}")

    def _load_new_messages_from_history(self, trigger_gsn: int = 0, current_gsn: int = 0) -> None:
        """Load new messages from history that aren't in the model yet.

        This method handles two scenarios:
        1. New messages (not in model) - creates new bubbles
        2. Existing messages (same message_id) - merges new content into existing bubbles

        For streaming responses that are saved in chunks with the same message_id,
        this method ensures all content chunks are properly merged into the existing
        message bubble instead of being ignored.

        Enhanced with GSN (Global Sequence Number) support for archive-aware
        message fetching. When GSN parameters are provided, uses GSN-based fetching
        which correctly handles archived messages.

        Args:
            trigger_gsn: The GSN that triggered this load (optional)
            current_gsn: The current (latest) GSN in the system (optional)
        """
        try:
            use_gsn_fetching = trigger_gsn > 0 or current_gsn > 0

            if use_gsn_fetching:
                # Use GSN-based fetching (archive-aware)
                new_messages = self._fetch_messages_by_gsn(trigger_gsn, current_gsn)
            else:
                # Legacy line-offset-based fetching
                history = self.get_history()
                if not history:
                    return

                # Get messages after current offset
                current_offset = self._load_state.current_line_offset
                new_messages = history.get_messages_after(current_offset, count=100)

            if not new_messages:
                return

            # Group messages by message_id with simple dict (no need for MessageGroup class)
            # For streaming flow, we need to group multiple chunks with same message_id
            message_groups: Dict[str, List[Dict[str, Any]]] = {}
            for msg_data in new_messages:
                message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                if not message_id:
                    continue

                if message_id not in message_groups:
                    message_groups[message_id] = []
                message_groups[message_id].append(msg_data)

            # Process messages - handle both new and existing message_ids
            for message_id, msg_list in message_groups.items():
                # For streaming, combine content from all chunks
                # Use MessageBuilder's build_items_from_raw_messages for consistency
                # But since we have pre-grouped messages, handle inline
                if len(msg_list) == 1:
                    combined_msg = msg_list[0]
                else:
                    # Simple merge: combine content from all messages
                    combined_msg = dict(msg_list[0])
                    all_content = []
                    for msg in msg_list:
                        all_content.extend(msg.get("content", []))
                    combined_msg["content"] = all_content

                # Check if this message already exists in the model
                existing_row = self._model.get_row_by_message_id(message_id)

                if existing_row is not None:
                    # Message bubble already exists - merge new content
                    self._message_builder.merge_content_into_existing_bubble(message_id, combined_msg)
                    logger.debug(f"Merged new content into existing bubble: {message_id[:8]}...")
                else:
                    # New message - create new bubble
                    # Use build_item_from_history for single combined message
                    item = self._message_builder.build_item_from_history(combined_msg)
                    if item:
                        qml_item = self._model.from_chat_list_item(item)
                        self._model.add_item(qml_item)
                        self._load_state.known_message_ids.add(message_id)

            # Update tracking
            if not use_gsn_fetching:
                # Legacy offset tracking
                if new_messages:
                    current_offset = self._load_state.current_line_offset
                    self._load_state.current_line_offset = current_offset + len(new_messages)
            else:
                # GSN tracking
                self._load_state.last_seen_gsn = current_gsn

            # Update unique message count
            if new_messages:
                # Only count unique new messages (not updates to existing ones)
                new_unique_count = sum(1 for msg_id in message_groups.keys()
                                      if msg_id not in self._load_state.known_message_ids)
                self._load_state.unique_message_count += new_unique_count
                # Add all processed message_ids to known set
                for msg_id in message_groups.keys():
                    self._load_state.known_message_ids.add(msg_id)

                # Scroll to bottom only if user is already there
                if self._scroll_to_bottom_callback:
                    self._scroll_to_bottom_callback(force=False)
                fetch_method = "GSN" if use_gsn_fetching else "line-offset"
                logger.debug(f"Processed {len(message_groups)} message groups from history using {fetch_method} fetching")

        except Exception as e:
            logger.error(f"Error loading new messages from history: {e}", exc_info=True)

    def _fetch_messages_by_gsn(self, trigger_gsn: int, current_gsn: int) -> List[Dict[str, Any]]:
        """Fetch messages using GSN-based (archive-aware) method.

        Args:
            trigger_gsn: The GSN that triggered this fetch
            current_gsn: The current (latest) GSN

        Returns:
            List of message dictionaries
        """
        try:
            from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

            # Get messages after the last seen GSN
            last_seen = self._load_state.last_seen_gsn
            new_messages = FastMessageHistoryService.get_messages_after_gsn(
                self._workspace.workspace_path,
                self._workspace.project_name,
                last_seen_gsn=last_seen,
                count=100
            )

            logger.debug(f"GSN fetch: last_seen={last_seen}, current={current_gsn}, found={len(new_messages)} messages")
            return new_messages

        except Exception as e:
            logger.error(f"Error in GSN-based fetching: {e}")
            return []

    def get_load_state(self) -> LoadState:
        """Get the current load state.

        Returns:
            Current LoadState instance
        """
        return self._load_state

    def has_more_older(self) -> bool:
        """Check if there are more older messages to load.

        Returns:
            True if more older messages are available
        """
        return self._load_state.has_more_older

    def is_loading_older(self) -> bool:
        """Check if currently loading older messages.

        Returns:
            True if currently loading older messages
        """
        return self._loading_older
