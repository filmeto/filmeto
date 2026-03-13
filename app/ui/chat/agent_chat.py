"""Agent Chat Component combining prompt input and chat history.

This component combines the agent prompt widget and chat history widget
into a single reusable component that can be used in both the agent panel
and the startup window. Supports tabbed chat with group chat and private
1-on-1 crew member conversations.
"""

from typing import Optional, Any, Dict
import asyncio
import logging
from PySide6.QtWidgets import QVBoxLayout, QWidget, QSplitter, QTabWidget, QTabBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import Signal, Slot

from app.ui.base_widget import BaseWidget
from app.data.workspace import Workspace
from app.ui.chat.list import QmlAgentChatListWidget
from app.ui.chat.plan import AgentChatPlanWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)

GROUP_CHAT_TAB_INDEX = 0


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
        # Cached reference for blinker connect/disconnect (same object required)
        self._crew_activity_handler = self._on_crew_member_activity_from_agent
        self._pending_crew_activity: list = []  # [(member_name, active), ...] replayed after init

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

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("agent_chat_splitter")
        self.splitter.setHandleWidth(0)

        self.chat_history_widget = QmlAgentChatListWidget(self.workspace, self)
        self.chat_history_widget.setObjectName("agent_chat_history_widget")
        self.splitter.addWidget(self.chat_history_widget)

        self.plan_widget = AgentChatPlanWidget(self.workspace, self)
        self.plan_widget.setObjectName("agent_chat_plan_widget")
        self.splitter.addWidget(self.plan_widget)
        self.splitter.setCollapsible(1, False)

        self.prompt_input_widget = AgentPromptWidget(self.workspace, self)
        self.prompt_input_widget.setObjectName("agent_chat_prompt_widget")
        self.splitter.addWidget(self.prompt_input_widget)

        QTimer.singleShot(0, lambda: self.splitter.setSizes([600, self.plan_widget._collapsed_height, 200]))
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)

        group_layout.addWidget(self.splitter)

        self.prompt_input_widget.message_submitted.connect(self._on_message_submitted)
        self.chat_history_widget.reference_clicked.connect(self._on_reference_clicked)
        self.plan_widget.expandedChanged.connect(self._on_plan_expanded_changed)
        self.chat_history_widget.crew_member_activity.connect(self.crew_member_activity.emit)

        self.tab_widget.addTab(group_chat_container, "\ue89e")
        self.tab_widget.setTabToolTip(GROUP_CHAT_TAB_INDEX, tr("Group Chat"))

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

    def _on_reference_clicked(self, ref_type: str, ref_id: str):
        logger.info(f"Reference clicked: {ref_type} / {ref_id}")

    @Slot(bool)
    def _on_plan_expanded_changed(self, is_expanded: bool):
        current_sizes = self.splitter.sizes()
        chat_height = current_sizes[0]
        prompt_height = current_sizes[2]

        plan_height = self.plan_widget._expanded_height if is_expanded else self.plan_widget._collapsed_height

        total_available = chat_height + current_sizes[1] + prompt_height
        new_chat_height = total_available - plan_height - prompt_height

        self.splitter.setSizes([max(100, new_chat_height), plan_height, prompt_height])

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
        if self.chat_history_widget:
            self.chat_history_widget.append_message(tr("System"), error_message)

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

        if self.plan_widget:
            self.plan_widget.refresh_plan()
        if self.chat_history_widget:
            self.chat_history_widget.on_project_switched(self._extract_project_name(project))

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
        if self.prompt_input_widget:
            self.prompt_input_widget.set_enabled(enabled)
