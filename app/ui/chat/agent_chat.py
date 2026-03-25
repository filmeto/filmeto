"""Agent Chat Component combining prompt input and chat history.

This component combines the agent prompt widget and chat history widget
into a single reusable component that can be used in both the agent panel
and the startup window. Supports tabbed chat with group chat and private
1-on-1 crew member conversations.
"""

from typing import Optional, Any, Dict
import asyncio
import logging
from pathlib import Path
import uuid

from PySide6.QtWidgets import QVBoxLayout, QWidget, QTabWidget, QTabBar
from PySide6.QtCore import Qt, QTimer, QObject, Slot, QUrl
from PySide6.QtCore import Signal
from PySide6.QtQuickWidgets import QQuickWidget

from app.ui.base_widget import BaseWidget
from app.data.workspace import Workspace
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.builders.message_builder import MessageBuilder
from app.ui.chat.list.handlers.qml_handler import QmlHandler
from app.ui.chat.list.handlers.stream_event_handler import StreamEventHandler
from app.ui.chat.list.managers.history_manager import HistoryManager
from app.ui.chat.list.managers.metadata_resolver import MetadataResolver
from app.ui.chat.list.managers.scroll_manager import ScrollManager
from app.ui.chat.list.managers.skill_manager import SkillManager
from app.ui.chat.plan.plan_view_model import PlanViewModel
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)

GROUP_CHAT_TAB_INDEX = 0
GROUP_VIEW_QML_PATH = Path(__file__).parent.parent / "qml" / "chat" / "widgets" / "AgentChatGroupView.qml"


class AgentChatWidget(BaseWidget):
    """Agent chat component combining prompt input and chat history."""

    error_occurred = Signal(str)
    crew_member_activity = Signal(str, bool)  # member_name, is_active

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.agent = None
        self._agent_ready = False
        self._agent_lock = asyncio.Lock()
        self._private_tabs: Dict[str, int] = {}  # crew_member_name -> tab_index
        self._prompt_widget: Optional[AgentPromptWidget] = None
        # Cached reference for blinker connect/disconnect (same object required)
        self._crew_activity_handler = self._on_crew_member_activity_from_agent
        self._pending_crew_activity: list = []  # [(member_name, active), ...] replayed after init

        # Group chat QML/controller state (kept explicit and testable)
        self._group_model: Optional[QmlAgentChatListModel] = None
        self._group_qml_root = None
        self._group_chat_list_qml = None
        self._metadata_resolver: Optional[MetadataResolver] = None
        self._message_builder: Optional[MessageBuilder] = None
        self._scroll_manager: Optional[ScrollManager] = None
        self._skill_manager: Optional[SkillManager] = None
        self._history_manager: Optional[HistoryManager] = None
        self._qml_handler: Optional[QmlHandler] = None
        self._stream_event_handler: Optional[StreamEventHandler] = None
        self._plan_bridge: Optional[PlanViewModel] = None

        self.error_occurred.connect(self._on_error)

        self._setup_ui()

        # Connect tab change to manage active state of private chat widgets
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        QTimer.singleShot(100, self._auto_initialize_agent)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("agent_chat_tabs")
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(False)
        self.tab_widget.setDocumentMode(False)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)

        # 设置标签宽度根据内容自适应
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setExpanding(False)
        tab_bar.setElideMode(Qt.ElideNone)

        self._setup_group_chat_tab()

        self.tab_widget.tabBar().setTabButton(GROUP_CHAT_TAB_INDEX, QTabBar.RightSide, None)
        self.tab_widget.tabBar().setTabButton(GROUP_CHAT_TAB_INDEX, QTabBar.LeftSide, None)

        layout.addWidget(self.tab_widget)

    def _setup_group_chat_tab(self):
        """Create the fixed group chat tab (always at index 0)."""
        group_chat_container = QWidget()
        group_layout = QVBoxLayout(group_chat_container)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)

        self._init_group_chat_controller()

        self._group_quick = QQuickWidget(self)
        self._group_quick.setObjectName("agent_chat_group_qml")
        self._group_quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._group_quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._group_quick.setClearColor(Qt.transparent)

        qml_root_dir = Path(__file__).resolve().parent.parent / "qml"
        self._group_quick.engine().addImportPath(str(qml_root_dir))

        # Expose legacy names for existing QML components.
        self._group_quick.rootContext().setContextProperty("_chatModel", self._group_model)
        self._group_quick.rootContext().setContextProperty("_planViewModel", self._plan_bridge)

        self._group_quick.statusChanged.connect(self._on_prompt_qml_status_changed)
        self._group_quick.setSource(QUrl.fromLocalFile(str(GROUP_VIEW_QML_PATH)))
        self._check_prompt_qml_loaded()

        self._group_qml_root = self._group_quick.rootObject()
        if self._group_qml_root is not None:
            self._group_qml_root.setProperty("chatModel", self._group_model)
            self._group_qml_root.setProperty("planViewModel", self._plan_bridge)

        self._wire_group_qml()
        group_layout.addWidget(self._group_quick)
        self._prompt_widget = AgentPromptWidget(self.workspace, group_chat_container)
        self._prompt_widget.setObjectName("agent_chat_prompt_widget")
        self._prompt_widget.set_placeholder(tr("Type your message..."))
        self._prompt_widget.prompt_submitted.connect(self._on_message_submitted)
        group_layout.addWidget(self._prompt_widget)


        self.tab_widget.addTab(group_chat_container, "\ue89e")
        self.tab_widget.setTabToolTip(GROUP_CHAT_TAB_INDEX, tr("Group Chat"))

    def _init_group_chat_controller(self) -> None:
        self._group_model = QmlAgentChatListModel(self)
        self._metadata_resolver = MetadataResolver(self.workspace)
        self._message_builder = MessageBuilder(self._metadata_resolver, self._group_model)
        self._scroll_manager = ScrollManager(self._group_model, 300)
        self._skill_manager = SkillManager(self._group_model, self._metadata_resolver, self._scroll_manager)
        self._history_manager = HistoryManager(self.workspace, self._group_model, self._message_builder)
        self._qml_handler = QmlHandler(self._group_model, 300)
        self._stream_event_handler = StreamEventHandler(self._group_model, self._skill_manager, self._metadata_resolver)
        self._plan_bridge = PlanViewModel(self.workspace, self)

        # Set up callbacks between components (mirrors QmlAgentChatListWidget).
        load_more_timer = QTimer(self)
        load_more_timer.setSingleShot(True)
        load_more_timer.timeout.connect(self._history_manager.load_older_messages)
        self._qml_handler.set_debounce_timer(load_more_timer)

        self._qml_handler.set_callbacks(
            on_reference_clicked=lambda ref_type, ref_id: self._on_reference_clicked(ref_type, ref_id),
            on_message_completed=lambda msg_id, agent_name: None,
            on_load_more=lambda: None,
        )
        self._stream_event_handler.set_callbacks(
            update_agent_card=lambda *args, **kwargs: None,
            scroll_to_bottom=lambda force=False: self._scroll_manager.scroll_to_bottom(force=force),
            crew_member_activity=lambda name, active: self.crew_member_activity.emit(name, active),
        )

        self._history_manager.connect_to_storage_signals()

    def _wire_group_qml(self) -> None:
        if not self._group_qml_root:
            return

        try:
            self._group_chat_list_qml = self._group_qml_root.findChild(QObject, "agentChatList")
        except Exception:
            self._group_chat_list_qml = None

        if not self._group_chat_list_qml:
            logger.error("AgentChatGroupView missing agentChatList object")
            return

        self._qml_handler.set_qml_root(self._group_chat_list_qml)
        self._scroll_manager.set_qml_root(self._group_chat_list_qml)
        self._scroll_manager.set_qml_handler(self._qml_handler)

        self._history_manager.set_qml_root(self._group_chat_list_qml)
        self._history_manager.set_callbacks(
            on_load_more=lambda: None,
            refresh_qml=lambda: self._qml_handler.refresh_model_binding(self._group_quick),
            scroll_to_bottom=lambda: self._scroll_manager.scroll_to_bottom(force=True),
            get_first_visible_message_id=self._qml_handler.get_first_visible_message_id,
            restore_scroll_position=self._qml_handler.restore_scroll_position,
        )

        self._metadata_resolver.load_crew_member_metadata()
        self._history_manager.load_recent_conversation()

    def open_private_chat(self, crew_member) -> None:
        """Open a private chat tab for a crew member, or switch to it if already open."""
        from app.ui.chat.private_chat_widget import PrivateChatWidget

        member_name = crew_member.config.name

        if member_name in self._private_tabs:
            tab_index = self._private_tabs[member_name]
            if tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(tab_index)
                return
            else:
                del self._private_tabs[member_name]

        private_widget = PrivateChatWidget(self.workspace, crew_member, self)
        # New private chat tab starts as inactive (will be activated by _on_tab_changed)
        private_widget.set_active(False)

        icon_text = crew_member.config.icon or crew_member.config.name[0].upper()
        tab_title = crew_member.config.name.title()

        tab_index = self.tab_widget.addTab(private_widget, f"{icon_text} {tab_title}")
        self._private_tabs[member_name] = tab_index

        self.tab_widget.setCurrentIndex(tab_index)

    def _on_tab_close_requested(self, index: int):
        """Handle tab close - only allow closing private chat tabs."""
        if index == GROUP_CHAT_TAB_INDEX:
            return

        widget = self.tab_widget.widget(index)
        member_name = None
        for name, idx in self._private_tabs.items():
            if idx == index:
                member_name = name
                break

        self.tab_widget.removeTab(index)

        if member_name:
            del self._private_tabs[member_name]

        self._rebuild_tab_index_map()

        if widget:
            widget.deleteLater()

    def _on_tab_changed(self, index: int):
        """Handle tab change - update active state of private chat widgets."""
        from app.ui.chat.private_chat_widget import PrivateChatWidget

        # Deactivate all private chat tabs
        for i in range(1, self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, PrivateChatWidget):
                widget.set_active(i == index)

        # The newly active tab (if it's a private chat) will load incremental messages
        # via its set_active(True) call

    def _rebuild_tab_index_map(self):
        """Rebuild the name->index mapping after tab removal."""
        from app.ui.chat.private_chat_widget import PrivateChatWidget
        new_map = {}
        for i in range(1, self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, PrivateChatWidget):
                new_map[widget.get_crew_member().config.name] = i
        self._private_tabs = new_map

    def _auto_initialize_agent(self):
        if self.workspace and self.workspace.get_project():
            asyncio.ensure_future(self._initialize_agent())

    async def _initialize_agent(self) -> bool:
        async with self._agent_lock:
            if self._agent_ready and self.agent:
                return True

            try:
                project = self.workspace.get_project()
                if not project:
                    return False

                project_name = self._extract_project_name(project) or "default"
                model, temperature = self._get_model_config()

                from agent.filmeto_agent import FilmetoAgent
                self.agent = FilmetoAgent.get_instance(
                    workspace=self.workspace,
                    project_name=project_name,
                    model=model,
                    temperature=temperature,
                    streaming=True
                )

                self._agent_ready = True
                self.agent.signals.connect_crew_member_activity(
                    self._crew_activity_handler, weak=False
                )
                for member_name, active in self._pending_crew_activity:
                    self.crew_member_activity.emit(member_name, active)
                self._pending_crew_activity.clear()
                logger.info(f"Agent initialized for project '{project_name}'")
                return True

            except Exception as e:
                logger.error(f"Failed to initialize agent: {e}", exc_info=True)
                self.agent = None
                self._agent_ready = False
                self._pending_crew_activity.clear()
                return False

    def _on_message_submitted(self, message: str):
        if not message:
            return

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._process_message_async(message))
        except RuntimeError:
            QTimer.singleShot(0, lambda: asyncio.ensure_future(self._process_message_async(message)))

    @Slot()
    def _check_prompt_qml_loaded(self):
        if not hasattr(self, "_group_quick") or self._group_quick.status() != QQuickWidget.Error:
            return
        errors = [err.toString() for err in self._group_quick.errors()]
        logger.error("Failed to load agent chat QML group view: %s", "; ".join(errors))
        self.error_occurred.emit(tr("Failed to load chat input UI."))

    @Slot(int)
    def _on_prompt_qml_status_changed(self, _status):
        self._check_prompt_qml_loaded()

    def _on_reference_clicked(self, ref_type: str, ref_id: str):
        logger.info(f"Reference clicked: {ref_type} / {ref_id}")

    async def _process_message_async(self, message: str):
        try:
            if not self._agent_ready:
                await self._initialize_agent()

            if not self._agent_ready or not self.agent:
                self.error_occurred.emit(tr("Agent not available. Please ensure a project is loaded."))
                return

            await self.agent.chat(message)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            self.error_occurred.emit(f"{tr('Error')}: {str(e)}")

    @Slot(str)
    def _on_error(self, error_message: str):
        if not self._group_model:
            return
        item = {
            self._group_model.MESSAGE_ID: str(uuid.uuid4()),
            self._group_model.SENDER_ID: "system",
            self._group_model.SENDER_NAME: tr("System"),
            self._group_model.IS_USER: False,
            self._group_model.CONTENT: error_message,
            self._group_model.AGENT_COLOR: "#9a9a9a",
            self._group_model.AGENT_ICON: "\ue6b3",
            self._group_model.CREW_METADATA: {},
            self._group_model.STRUCTURED_CONTENT: [],
            self._group_model.CONTENT_TYPE: "error",
            self._group_model.IS_READ: True,
            self._group_model.CREW_READ_BY: [],
            self._group_model.TIMESTAMP: None,
            self._group_model.START_TIME: "",
            self._group_model.DATE_GROUP: "",
        }
        self._group_model.add_item(item)

    def _extract_project_name(self, project: Any) -> str:
        if project:
            if hasattr(project, 'project_name'):
                return project.project_name
            elif hasattr(project, 'name'):
                return project.name
            elif isinstance(project, str):
                return project
        return "default"

    def _get_model_config(self) -> tuple:
        settings = self.workspace.get_settings()
        model = settings.get('ai_services.default_model', 'gpt-4o-mini') if settings else 'gpt-4o-mini'
        temperature = 0.7
        return model, temperature

    def _on_crew_member_activity_from_agent(self, sender, member_name=None, active=None):
        """Forward agent signals crew_member_activity to Qt signal (group chat path)."""
        if member_name is None or active is None:
            return
        if self._agent_ready:
            self.crew_member_activity.emit(member_name, active)
        else:
            self._pending_crew_activity.append((member_name, active))

    def on_project_switch(self, project: Any) -> None:
        if not project:
            return

        self._agent_ready = False
        self._pending_crew_activity.clear()
        if self.agent and hasattr(self.agent, "signals"):
            try:
                self.agent.signals.disconnect_crew_member_activity(self._crew_activity_handler)
            except Exception as e:
                logger.debug("Could not disconnect crew_member_activity signal: %s", e)
        self.agent = None

        asyncio.ensure_future(self._initialize_agent())

        if self._plan_bridge:
            self._plan_bridge.on_project_switched()
            self._plan_bridge.checkInterruptedPlans()
            self._plan_bridge.refresh_plan()
        if self._history_manager:
            self._metadata_resolver.load_crew_member_metadata()
            self._history_manager.on_project_switched()

        self._close_all_private_tabs()

    def _close_all_private_tabs(self):
        """Close all private chat tabs (e.g. on project switch)."""
        for i in range(self.tab_widget.count() - 1, 0, -1):
            widget = self.tab_widget.widget(i)
            self.tab_widget.removeTab(i)
            if widget:
                widget.deleteLater()
        self._private_tabs.clear()

    def get_current_project_name(self) -> Optional[str]:
        return self._extract_project_name(self.workspace.get_project()) if self.agent else None

    def set_enabled(self, enabled: bool):
        if self._prompt_widget:
            self._prompt_widget.set_enabled(enabled)
