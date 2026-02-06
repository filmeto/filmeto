"""Agent chat list component using QListView for virtualized rendering."""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING

from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QListView, QStyledItemDelegate, QAbstractItemView,
    QStyleOptionViewItem, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, Slot, QTimer, QAbstractListModel, QModelIndex, QSize, QPoint
)

from agent import AgentMessage
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr
from agent.chat.history.agent_chat_history_service import AgentChatHistoryService

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.workspace import Workspace


@dataclass
class ChatListItem:
    message_id: str
    sender_id: str
    sender_name: str
    is_user: bool
    user_content: str = ""
    agent_message: Optional[AgentMessage] = None
    agent_color: str = "#4a90e2"
    agent_icon: str = "🤖"
    crew_member_metadata: Dict[str, Any] = field(default_factory=dict)


class AgentChatListModel(QAbstractListModel):
    ITEM_ROLE = Qt.UserRole + 1
    MESSAGE_ID_ROLE = Qt.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[ChatListItem] = []
        self._message_id_to_row: Dict[str, int] = {}

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == self.ITEM_ROLE:
            return item
        if role == self.MESSAGE_ID_ROLE:
            return item.message_id
        if role == Qt.DisplayRole:
            if item.is_user:
                return item.user_content
            if item.agent_message:
                return item.agent_message.get_text_content()
        return None

    def add_item(self, item: ChatListItem) -> int:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        if item.message_id:
            self._message_id_to_row[item.message_id] = row
        self.endInsertRows()
        return row

    def get_item(self, row: int) -> Optional[ChatListItem]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_row_by_message_id(self, message_id: str) -> Optional[int]:
        return self._message_id_to_row.get(message_id)

    def get_item_by_message_id(self, message_id: str) -> Optional[ChatListItem]:
        row = self.get_row_by_message_id(message_id)
        if row is None:
            return None
        return self._items[row]

    def notify_row_changed(self, row: int):
        if row < 0 or row >= len(self._items):
            return
        index = self.index(row, 0)
        self.dataChanged.emit(index, index)

    def clear(self):
        self.beginResetModel()
        self._items = []
        self._message_id_to_row = {}
        self.endResetModel()


class AgentChatListDelegate(QStyledItemDelegate):
    def __init__(self, owner: "AgentChatListWidget", parent=None):
        super().__init__(parent)
        self._owner = owner

    def sizeHint(self, option, index):
        return self._owner.get_item_size_hint(option, index)

    def paint(self, painter, option, index):
        return


class AgentChatListView(QListView):
    viewport_scrolled = Signal()
    viewport_resized = Signal()

    def scrollContentsBy(self, dx: int, dy: int):
        super().scrollContentsBy(dx, dy)
        self.viewport_scrolled.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewport_resized.emit()


class AgentChatListWidget(BaseWidget):
    """Virtualized chat list widget for agent conversations."""

    reference_clicked = Signal(str, str)  # ref_type, ref_id
    message_complete = Signal(str, str)  # message_id, agent_name
    load_more_requested = Signal()

    def __init__(self, workspace: "Workspace", parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self._model = AgentChatListModel(self)
        self._delegate = AgentChatListDelegate(self, self)
        self._visible_widgets: Dict[int, QWidget] = {}
        self._size_hint_cache: Dict[str, Dict[int, QSize]] = {}

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._scroll_to_bottom)

        self._visible_refresh_timer = QTimer(self)
        self._visible_refresh_timer.setSingleShot(True)
        self._visible_refresh_timer.timeout.connect(self._refresh_visible_widgets)

        # New data check timer - polls for new messages when at bottom
        self._new_data_check_timer = QTimer(self)
        self._new_data_check_timer.timeout.connect(self._check_for_new_data)

        self._user_at_bottom = True
        self._bottom_reached = False

        self._crew_member_metadata: Dict[str, Dict[str, Any]] = {}
        self._agent_current_cards: Dict[str, str] = {}

        # Track the latest message_id to detect new messages
        self._latest_message_id: Optional[str] = None

        self._setup_ui()
        self._load_crew_member_metadata()
        self._load_recent_conversation()
        self._start_new_data_check_timer()

    def on_project_switched(self, project_name: str):
        self.refresh_crew_member_metadata()
        # Reset latest message_id tracking
        self._latest_message_id = None
        self._load_recent_conversation()

    def refresh_crew_member_metadata(self):
        self._load_crew_member_metadata()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        self.list_view = AgentChatListView(self)
        self.list_view.setModel(self._model)
        self.list_view.setItemDelegate(self._delegate)
        self.list_view.setUniformItemSizes(False)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_view.setFocusPolicy(Qt.NoFocus)
        self.list_view.setSpacing(8)
        self.list_view.setViewportMargins(5, 10, 5, 10)
        self.list_view.setStyleSheet("""
            QListView {
                background-color: #252525;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2b2d30;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #505254;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #606264;
            }
        """)

        self.list_view.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)
        self.list_view.viewport_scrolled.connect(self._schedule_visible_refresh)
        self.list_view.viewport_resized.connect(self._on_viewport_resized)

        self._model.rowsInserted.connect(self._on_rows_inserted)
        self._model.dataChanged.connect(self._on_model_data_changed)
        self._model.modelReset.connect(self._clear_visible_widgets)

        layout.addWidget(self.list_view)

    def _load_recent_conversation(self):
        """Load recent conversation from AgentChatHistoryService."""
        try:
            project = self.workspace.get_project()
            if not project:
                return

            workspace_path = self.workspace.workspace_path
            project_name = self.workspace.project_name

            # Get the latest 50 messages from history
            messages = AgentChatHistoryService.get_latest_messages(
                workspace_path, project_name, count=50
            )

            if messages:
                # Update the latest message_id tracker
                last_msg_info = AgentChatHistoryService.get_latest_message_info(
                    workspace_path, project_name
                )
                if last_msg_info:
                    self._latest_message_id = last_msg_info.get("message_id")

                # Clear and reload the model
                self._model.clear()
                self._size_hint_cache.clear()
                self._clear_visible_widgets()

                # Load messages in order (oldest first)
                for msg_data in reversed(messages):
                    self._load_message_from_history(msg_data)

                # Scroll to bottom after loading
                self._schedule_scroll()

                logger.info(f"Loaded {len(messages)} messages from history")
            else:
                logger.info("No messages found in history")

        except Exception as e:
            logger.error(f"Error loading recent conversation: {e}")

    def _load_crew_member_metadata(self):
        try:
            from agent.crew.crew_service import CrewService

            project = self.workspace.get_project()
            if project:
                crew_member_service = CrewService()
                crew_members = crew_member_service.get_project_crew_members(project)
                self._crew_member_metadata = {}
                for name, crew_member in crew_members.items():
                    self._crew_member_metadata[crew_member.config.name.lower()] = crew_member
            else:
                self._crew_member_metadata = {}
        except Exception as e:
            print(f"Error loading crew members: {e}")
            self._crew_member_metadata = {}

    def _load_message_from_history(self, msg_data: Dict[str, Any]):
        """Load a single message from history data into the model."""
        try:
            from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
            from agent.chat.agent_chat_types import MessageType
            from agent.chat.content import StructureContent

            metadata = msg_data.get("metadata", {})
            content_list = msg_data.get("content", [])

            # Extract basic info
            message_id = metadata.get("message_id", "")
            sender_id = metadata.get("sender_id", "unknown")
            sender_name = metadata.get("sender_name", sender_id)
            message_type_str = metadata.get("message_type", "text")

            if not message_id:
                return

            # Parse message_type
            try:
                message_type = MessageType(message_type_str)
            except ValueError:
                message_type = MessageType.TEXT

            # Check if this is a user message
            is_user = sender_id.lower() == "user"

            if is_user:
                # For user messages, extract text from content
                text_content = ""
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        if content_item.get("content_type") == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                            break

                item = ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=True,
                    user_content=text_content,
                )
            else:
                # Reconstruct structured content from content list
                structured_content = []
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        try:
                            sc = StructureContent.from_dict(content_item)
                            structured_content.append(sc)
                        except Exception as e:
                            logger.warning(f"Failed to load structured content: {e}")

                # Create AgentMessage
                agent_message = ChatAgentMessage(
                    message_type=message_type,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    message_id=message_id,
                    metadata=metadata,
                    structured_content=structured_content,
                )

                # Get agent metadata
                agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(
                    sender_name, metadata
                )

                item = ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=False,
                    agent_message=agent_message,
                    agent_color=agent_color,
                    agent_icon=agent_icon,
                    crew_member_metadata=crew_member_data,
                )

            self._model.add_item(item)

        except Exception as e:
            logger.error(f"Error loading message from history: {e}")

    def _start_new_data_check_timer(self):
        """Start the timer to check for new data."""
        # Check every 1 second
        self._new_data_check_timer.start(1000)

    def _stop_new_data_check_timer(self):
        """Stop the new data check timer."""
        self._new_data_check_timer.stop()

    def _check_for_new_data(self):
        """Check for new data and refresh if at bottom."""
        # Only check if user is at the bottom
        if not self._user_at_bottom:
            return

        try:
            workspace_path = self.workspace.workspace_path
            project_name = self.workspace.project_name

            # Get the latest message_id from history
            latest_message_id = AgentChatHistoryService.get_latest_message_id(
                workspace_path, project_name
            )

            # Check if there's a new message
            if latest_message_id and latest_message_id != self._latest_message_id:
                # Load new messages
                self._load_new_messages(latest_message_id)

        except Exception as e:
            logger.error(f"Error checking for new data: {e}")

    def _load_new_messages(self, new_latest_message_id: str):
        """Load new messages since the last known message."""
        try:
            workspace_path = self.workspace.workspace_path
            project_name = self.workspace.project_name

            # Get messages after the last known message_id
            if self._latest_message_id:
                new_messages = AgentChatHistoryService.get_messages_after(
                    workspace_path, project_name, self._latest_message_id, count=100
                )
            else:
                # If no previous message, get latest messages
                new_messages = AgentChatHistoryService.get_latest_messages(
                    workspace_path, project_name, count=50
                )
                new_messages = list(reversed(new_messages))

            if new_messages:
                # Load new messages
                for msg_data in new_messages:
                    # Skip if already in model
                    message_id = msg_data.get("metadata", {}).get("message_id")
                    if message_id and not self._model.get_row_by_message_id(message_id):
                        self._load_message_from_history(msg_data)

                # Update the latest message_id tracker
                self._latest_message_id = new_latest_message_id

                # Scroll to bottom to show new messages
                self._schedule_scroll()

                logger.info(f"Loaded {len(new_messages)} new messages")

        except Exception as e:
            logger.error(f"Error loading new messages: {e}")

    def _get_sender_info(self, sender: str):
        normalized_sender = sender.lower()
        is_user = normalized_sender in [tr("用户").lower(), "用户", "user", tr("user").lower()]
        is_system = normalized_sender in [tr("系统").lower(), "系统", "system", tr("system").lower()]
        is_tool = normalized_sender in [tr("工具").lower(), "工具", "tool", tr("tool").lower()]
        is_assistant = normalized_sender in [tr("助手").lower(), "助手", "assistant", tr("assistant").lower()]

        if is_user:
            icon_char = "\ue6b3"
            alignment = Qt.AlignRight
        elif is_system or is_tool:
            icon_char = "⚙️"
            alignment = Qt.AlignLeft
        elif is_assistant:
            icon_char = "A"
            alignment = Qt.AlignLeft
        else:
            icon_char = "A"
            alignment = Qt.AlignLeft

        return is_user, icon_char, alignment

    def _resolve_agent_metadata(self, sender: str, message_metadata: Optional[Dict[str, Any]] = None):
        if not self._crew_member_metadata:
            self._load_crew_member_metadata()

        agent_color = "#4a90e2"
        agent_icon = "🤖"
        crew_member_data: Dict[str, Any] = {}

        normalized_sender = sender.lower()
        sender_crew_member = self._crew_member_metadata.get(normalized_sender)
        if sender_crew_member:
            agent_color = sender_crew_member.config.color
            agent_icon = sender_crew_member.config.icon
            crew_member_data = {
                "name": sender_crew_member.config.name,
                "description": sender_crew_member.config.description,
                "color": sender_crew_member.config.color,
                "icon": sender_crew_member.config.icon,
                "soul": sender_crew_member.config.soul,
                "skills": sender_crew_member.config.skills,
                "model": sender_crew_member.config.model,
                "temperature": sender_crew_member.config.temperature,
                "max_steps": sender_crew_member.config.max_steps,
                "config_path": sender_crew_member.config.config_path,
                "crew_title": sender_crew_member.config.metadata.get("crew_title", normalized_sender),
            }
        else:
            if message_metadata:
                agent_color = message_metadata.get("color", agent_color)
                agent_icon = message_metadata.get("icon", agent_icon)
                crew_member_data = dict(message_metadata)
        return agent_color, agent_icon, crew_member_data

    def _create_message_widget(self, item: ChatListItem, parent=None) -> QWidget:
        from app.ui.chat.card import AgentMessageCard, UserMessageCard

        if item.is_user:
            widget = UserMessageCard(item.user_content, parent)
        else:
            widget = AgentMessageCard(
                agent_message=item.agent_message,
                agent_color=item.agent_color,
                agent_icon=item.agent_icon,
                crew_member_metadata=item.crew_member_metadata,
                parent=parent,
            )
            widget.reference_clicked.connect(self.reference_clicked.emit)
        return widget

    def _build_sizing_widget(self, item: ChatListItem, width: int) -> QWidget:
        widget = self._create_message_widget(item, None)
        widget.setAttribute(Qt.WA_DontShowOnScreen, True)
        widget.setFixedWidth(max(1, width))
        if widget.layout():
            widget.layout().activate()
        widget.adjustSize()
        return widget

    def get_item_size_hint(self, option, index) -> QSize:
        item = index.data(self._model.ITEM_ROLE)
        if not item:
            return QSize(0, 0)

        width = option.rect.width()
        if width <= 0:
            width = self.list_view.viewport().width()
        width = max(1, width)

        cached = self._size_hint_cache.get(item.message_id, {}).get(width)
        if cached:
            return cached

        widget = self._build_sizing_widget(item, width)
        size = widget.sizeHint()
        widget.deleteLater()

        if size.width() <= 0:
            size.setWidth(width)
        else:
            size.setWidth(width)
        if size.height() < 1:
            size.setHeight(1)

        self._size_hint_cache.setdefault(item.message_id, {})[width] = size
        return size

    def _invalidate_size_hint(self, message_id: str):
        if message_id in self._size_hint_cache:
            self._size_hint_cache.pop(message_id, None)

    def _on_viewport_resized(self):
        self._size_hint_cache.clear()
        # Clear existing widgets so they will be recreated with updated width
        self._clear_visible_widgets()
        self.list_view.doItemsLayout()
        self._schedule_visible_refresh()

    def _schedule_visible_refresh(self):
        if not self._visible_refresh_timer.isActive():
            self._visible_refresh_timer.start(0)

    def _clear_visible_widgets(self):
        for row, widget in list(self._visible_widgets.items()):
            index = self._model.index(row, 0)
            self.list_view.setIndexWidget(index, None)
            widget.setParent(None)
            widget.deleteLater()
        self._visible_widgets = {}

    def _refresh_visible_widgets(self):
        row_count = self._model.rowCount()
        if row_count <= 0:
            self._clear_visible_widgets()
            return

        first_row, last_row = self._get_visible_row_range()
        if first_row is None or last_row is None:
            return

        buffer_size = 2
        start_row = max(0, first_row - buffer_size)
        end_row = min(row_count - 1, last_row + buffer_size)
        desired_rows = set(range(start_row, end_row + 1))

        for row in list(self._visible_widgets.keys()):
            if row not in desired_rows:
                index = self._model.index(row, 0)
                widget = self._visible_widgets.pop(row)
                self.list_view.setIndexWidget(index, None)
                widget.setParent(None)
                widget.deleteLater()

        for row in desired_rows:
            if row in self._visible_widgets:
                continue
            item = self._model.get_item(row)
            if not item:
                continue
            index = self._model.index(row, 0)
            widget = self._create_message_widget(item, self.list_view.viewport())
            # Set fixed width to match viewport width, ensuring each row has independent sizing
            widget_width = self.list_view.viewport().width()
            widget.setFixedWidth(max(1, widget_width))
            # Get cached size or build sizing widget to determine height
            cached_size = self._size_hint_cache.get(item.message_id, {}).get(widget_width)
            if cached_size:
                item_height = cached_size.height()
            else:
                # Build a temporary widget to calculate height
                option = QStyleOptionViewItem()
                option.rect = self.list_view.viewport().rect()
                item_height = self.get_item_size_hint(option, index).height()
            widget.setFixedHeight(max(1, item_height))
            # Set size policy to fixed to prevent automatic resizing
            widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            if widget.layout():
                widget.layout().activate()
            self.list_view.setIndexWidget(index, widget)
            self._visible_widgets[row] = widget

    def _get_visible_row_range(self) -> Tuple[Optional[int], Optional[int]]:
        viewport = self.list_view.viewport()
        if viewport is None:
            return None, None

        top_index = self.list_view.indexAt(QPoint(0, 0))
        if top_index.isValid():
            first_row = top_index.row()
        else:
            first_row = 0

        bottom_pos = max(0, viewport.height() - 1)
        bottom_index = self.list_view.indexAt(QPoint(0, bottom_pos))
        if not bottom_index.isValid():
            y = bottom_pos
            step = max(1, viewport.height() // 10)
            while y >= 0 and not bottom_index.isValid():
                bottom_index = self.list_view.indexAt(QPoint(0, y))
                y -= step

        if bottom_index.isValid():
            last_row = bottom_index.row()
        else:
            last_row = first_row

        return first_row, last_row

    def _on_model_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex, roles=None):
        for row in range(top_left.row(), bottom_right.row() + 1):
            self._update_widget_for_row(row)
        self._schedule_visible_refresh()

    def _update_widget_for_row(self, row: int):
        widget = self._visible_widgets.get(row)
        if not widget:
            return
        item = self._model.get_item(row)
        if not item:
            return
        if item.is_user:
            if hasattr(widget, "set_content"):
                widget.set_content(item.user_content)
        else:
            if hasattr(widget, "update_from_agent_message") and item.agent_message:
                widget.update_from_agent_message(item.agent_message)

        # Update widget height after content change
        widget_width = widget.width()
        # Invalidate size hint cache to force recalculation
        self._invalidate_size_hint(item.message_id)
        # Recalculate height
        option = QStyleOptionViewItem()
        option.rect = self.list_view.viewport().rect()
        index = self._model.index(row, 0)
        new_size = self.get_item_size_hint(option, index)
        # Update widget height
        widget.setFixedHeight(max(1, new_size.height()))

    def _on_rows_inserted(self, parent: QModelIndex, start: int, end: int):
        self._schedule_visible_refresh()
        self._schedule_scroll()

    def _on_scroll_value_changed(self, value: int):
        scrollbar = self.list_view.verticalScrollBar()
        scroll_diff = scrollbar.maximum() - value
        was_at_bottom = self._user_at_bottom
        self._user_at_bottom = scroll_diff < 50

        if self._user_at_bottom and not was_at_bottom:
            if not self._bottom_reached:
                self._bottom_reached = True
                self.load_more_requested.emit()
        elif not self._user_at_bottom:
            self._bottom_reached = False

    def _scroll_to_bottom(self):
        if self._user_at_bottom:
            self.list_view.scrollToBottom()

    def _schedule_scroll(self):
        self._scroll_timer.start(50)

    def _add_historical_message(self, sender: str, message):
        if not message.content:
            return None

        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType
        from agent.chat.content import TextContent

        is_user = message.role == "user"
        is_user_normalized = sender.lower() in [tr("用户").lower(), "用户", "user", tr("user").lower()]

        if is_user or is_user_normalized:
            return self.add_user_message(message.content)

        message_id = (
            message.metadata.get("message_id", f"hist_{message.timestamp}")
            if message.metadata else f"hist_{message.timestamp}"
        )

        agent_message = ChatAgentMessage(
            message_type=MessageType.TEXT,
            sender_id=sender,
            sender_name=sender,
            message_id=message_id,
            structured_content=[TextContent(text=message.content)] if message.content else [],
        )

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(sender, message.metadata)

        item = ChatListItem(
            message_id=message_id,
            sender_id=sender,
            sender_name=sender,
            is_user=False,
            agent_message=agent_message,
            agent_color=agent_color,
            agent_icon=agent_icon,
            crew_member_metadata=crew_member_data,
        )
        self._model.add_item(item)
        self._schedule_scroll()
        return item

    def append_message(self, sender: str, message: str, message_id: str = None):
        if not message:
            return None

        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType
        from agent.chat.content import TextContent

        is_user, _icon_char, _alignment = self._get_sender_info(sender)
        if is_user:
            return self.add_user_message(message)

        if not message_id:
            message_id = str(uuid.uuid4())

        agent_message = ChatAgentMessage(
            message_type=MessageType.TEXT,
            sender_id=sender,
            sender_name=sender,
            message_id=message_id,
            structured_content=[TextContent(text=message)] if message else [],
        )

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(sender)

        item = ChatListItem(
            message_id=message_id,
            sender_id=sender,
            sender_name=sender,
            is_user=False,
            agent_message=agent_message,
            agent_color=agent_color,
            agent_icon=agent_icon,
            crew_member_metadata=crew_member_data,
        )

        row = self._model.add_item(item)
        self._schedule_scroll()
        return self._visible_widgets.get(row)

    def update_last_message(self, message: str):
        row_count = self._model.rowCount()
        if row_count <= 0:
            return

        last_row = row_count - 1
        item = self._model.get_item(last_row)
        if not item:
            return

        if item.is_user:
            item.user_content = message
            self._invalidate_size_hint(item.message_id)
            self._model.notify_row_changed(last_row)
        else:
            self.update_agent_card(item.message_id, content=message, append=False)

        self._schedule_scroll()

    def start_streaming_message(self, sender: str) -> str:
        message_id = str(uuid.uuid4())
        self.append_message(sender, "...", message_id)
        return message_id

    def update_streaming_message(self, message_id: str, content: str):
        item = self._model.get_item_by_message_id(message_id)
        if not item:
            return
        if item.is_user:
            item.user_content = content
            self._invalidate_size_hint(item.message_id)
            row = self._model.get_row_by_message_id(message_id)
            if row is not None:
                self._model.notify_row_changed(row)
        else:
            self.update_agent_card(message_id, content=content, append=False)
        self._schedule_scroll()

    def add_user_message(self, content: str):
        message_id = str(uuid.uuid4())
        item = ChatListItem(
            message_id=message_id,
            sender_id="user",
            sender_name=tr("User"),
            is_user=True,
            user_content=content,
        )
        row = self._model.add_item(item)
        self._schedule_scroll()
        return self._visible_widgets.get(row)

    def get_or_create_agent_card(self, message_id: str, agent_name: str, title=None):
        existing_row = self._model.get_row_by_message_id(message_id)
        if existing_row is not None:
            return self._visible_widgets.get(existing_row)

        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType

        agent_message = ChatAgentMessage(
            message_type=MessageType.TEXT,
            sender_id=agent_name,
            sender_name=agent_name,
            message_id=message_id,
            structured_content=[],
        )

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(agent_name)

        item = ChatListItem(
            message_id=message_id,
            sender_id=agent_name,
            sender_name=agent_name,
            is_user=False,
            agent_message=agent_message,
            agent_color=agent_color,
            agent_icon=agent_icon,
            crew_member_metadata=crew_member_data,
        )

        row = self._model.add_item(item)
        self._agent_current_cards[agent_name] = message_id
        self._schedule_scroll()
        return self._visible_widgets.get(row)

    def get_agent_current_card(self, agent_name: str):
        message_id = self._agent_current_cards.get(agent_name)
        if message_id:
            row = self._model.get_row_by_message_id(message_id)
            if row is not None:
                return self._visible_widgets.get(row)
        return None

    def update_agent_card(
        self,
        message_id: str,
        content: str = None,
        append: bool = True,
        is_thinking: bool = False,
        thinking_text: str = "",
        is_complete: bool = False,
        structured_content=None,
        error: str = None,
    ):
        item = self._model.get_item_by_message_id(message_id)
        if not item or not item.agent_message:
            return

        card = None
        row = self._model.get_row_by_message_id(message_id)
        if row is not None:
            card = self._visible_widgets.get(row)

        from agent.chat.content import TextContent, TypingContent, TypingState
        from agent.chat.agent_chat_types import ContentType
        from agent.chat.content import StructureContent

        agent_message = item.agent_message

        if content is not None:
            text_content = None
            for sc in agent_message.structured_content:
                if sc.content_type == ContentType.TEXT:
                    text_content = sc
                    break
            if text_content:
                text_content.text = (text_content.text or "") + content if append else content
            else:
                agent_message.structured_content.append(TextContent(text=content))

            if card:
                final_content = text_content.text if text_content else content
                card.set_content(final_content)
                if card.has_typing_indicator():
                    card.remove_typing_indicator()

        if structured_content is not None:
            items = (
                [structured_content]
                if isinstance(structured_content, StructureContent)
                else list(structured_content)
            )
            for sc in items:
                is_typing_content = isinstance(sc, TypingContent) or sc.content_type == ContentType.TYPING
                is_typing_end = (
                    is_typing_content
                    and isinstance(sc, TypingContent)
                    and sc.state == TypingState.END
                )

                if is_typing_end:
                    agent_message.structured_content = [
                        existing for existing in agent_message.structured_content
                        if existing.content_type != ContentType.TYPING
                    ]
                    if card and card.has_typing_indicator():
                        card.remove_typing_indicator()
                    continue

                agent_message.structured_content.append(sc)
                if card:
                    card.add_structure_content_widget(sc)
                    if not is_typing_content and is_complete:
                        if card.has_typing_indicator():
                            card.remove_typing_indicator()

        if error:
            error_text = f"❌ Error: {error}"
            agent_message.structured_content = [
                sc for sc in agent_message.structured_content
                if sc.content_type != ContentType.TEXT
                and sc.content_type != ContentType.TYPING
            ]
            agent_message.structured_content.append(TextContent(text=error_text))
            if card:
                card.set_content(error_text)
                if card.has_typing_indicator():
                    card.remove_typing_indicator()

        if is_complete:
            agent_message.structured_content = [
                sc for sc in agent_message.structured_content
                if sc.content_type != ContentType.TYPING
            ]

        self._invalidate_size_hint(message_id)
        if row is not None:
            self._model.notify_row_changed(row)
        self._schedule_scroll()

    async def handle_agent_message(self, message: AgentMessage):
        if message.sender_id == "user":
            return

        if getattr(message, "message_type", None):
            from agent.chat.agent_chat_types import MessageType
            if message.message_type == MessageType.SYSTEM and message.metadata.get("event_type") in (
                "crew_member_start", "producer_start", "mentioned_agent_start",
                "responding_agent_start", "plan_update", "plan_created",
            ):
                return

        message_id = (
            getattr(message, "message_id", None)
            or (message.metadata.get("message_id") if message.metadata else None)
        )
        if not message_id:
            message_id = str(uuid.uuid4())

        self.get_or_create_agent_card(
            message_id,
            message.sender_name,
            message.sender_name,
        )

        has_structure = bool(message.structured_content)
        if has_structure:
            for sc in message.structured_content:
                self.update_agent_card(message_id, structured_content=sc)

    @Slot(object, object)
    def handle_stream_event(self, event, session):
        if event.event_type == "error":
            error_content = event.data.get("content", "Unknown error occurred")
            message_id = str(uuid.uuid4())
            self.get_or_create_agent_card(message_id, "System", "System")
            from agent.chat.content import ErrorContent
            error_structure = ErrorContent(error_message=error_content)
            self.update_agent_card(
                message_id,
                structured_content=error_structure,
                error=error_content,
            )
        elif event.event_type == "agent_response":
            content = event.data.get("content", "")
            sender_name = event.data.get("sender_name", "Unknown")
            sender_id = event.data.get("sender_id", sender_name.lower())
            session_id = event.data.get("session_id", "unknown")

            if sender_id == "user":
                return

            message_id = event.data.get("message_id")
            if not message_id:
                message_id = f"response_{session_id}_{uuid.uuid4()}"

            self.get_or_create_agent_card(message_id, sender_name, sender_name)
            from agent.chat.content import TextContent
            text_structure = TextContent(text=content)
            self.update_agent_card(message_id, structured_content=text_structure)
        elif event.event_type in ["skill_start", "skill_progress", "skill_end"]:
            skill_name = event.data.get("skill_name", "Unknown")
            sender_name = event.data.get("sender_name", "Unknown")
            sender_id = event.data.get("sender_id", sender_name.lower())
            message_id = event.data.get("message_id", str(uuid.uuid4()))

            if sender_id == "user":
                return

            if event.event_type == "skill_start":
                content = f"[Skill: {skill_name}] Starting execution..."
            elif event.event_type == "skill_progress":
                message = event.data.get("progress_text", "Processing...")
                content = f"[Skill: {skill_name}] {message}"
            elif event.event_type == "skill_end":
                result = event.data.get("result", "No result returned")
                content = f"[Skill: {skill_name}] Completed. Result: {result}"
            else:
                content = f"[Skill: {skill_name}] Unknown skill status"

            self.get_or_create_agent_card(message_id, sender_name, sender_name)
            from agent.chat.content import ProgressContent
            skill_content = ProgressContent(
                progress=content,
                percentage=None,
                tool_name=skill_name,
            )
            self.update_agent_card(
                message_id,
                content=content,
                append=False,
                structured_content=skill_content,
            )
        elif hasattr(event, "content") and event.content:
            sender_id = getattr(event, "sender_id", "")
            if hasattr(event, "agent_name"):
                sender_id = getattr(event, "agent_name", "").lower()

            if sender_id == "user":
                return

            message_type = getattr(event, "message_type", None)
            from agent.chat.agent_chat_types import MessageType
            card = self._model.get_item_by_message_id(event.message_id)
            if not card:
                agent_name = getattr(event, "agent_name", "Unknown")
                self.get_or_create_agent_card(
                    event.message_id,
                    agent_name,
                    getattr(event, "title", None),
                )

            if message_type == MessageType.THINKING:
                from agent.chat.content import ThinkingContent
                if isinstance(event.content, ThinkingContent):
                    thinking_structure = event.content
                else:
                    thinking_content = event.content
                    if thinking_content.startswith("🤔 Thinking: "):
                        thinking_content = thinking_content[len("🤔 Thinking: "):]
                    thinking_structure = ThinkingContent(
                        thought=thinking_content,
                        title="Thinking Process",
                        description="Agent's thought process",
                    )
                self.update_agent_card(event.message_id, structured_content=thinking_structure)
            else:
                from agent.chat.content import TextContent
                text_structure = TextContent(text=event.content)
                self.update_agent_card(event.message_id, structured_content=text_structure)

    def sync_from_session(self, session):
        pass

    def clear(self):
        self._stop_new_data_check_timer()
        self._clear_visible_widgets()
        self._size_hint_cache.clear()
        self._agent_current_cards.clear()
        self._model.clear()
        self._latest_message_id = None
