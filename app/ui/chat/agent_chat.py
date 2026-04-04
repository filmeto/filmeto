"""Agent Chat Component combining prompt input and chat history.

This component combines the agent prompt widget and chat history widget
into a single reusable component that can be used in both the agent panel
and the startup window. Supports tabbed chat with group chat and private
1-on-1 crew member conversations.
"""

from typing import Optional, Any, Dict
import asyncio
import logging
import uuid
from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QSplitter,
    QTabWidget,
    QTabBar,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QObject, Property, Slot, QUrl, QEvent
from PySide6.QtCore import Signal
from PySide6.QtQuickWidgets import QQuickWidget
from qasync import asyncSlot

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.core.base_worker import FunctionWorker
from app.ui.core.task_manager import TaskManager
from app.ui.chat.list import AgentChatListWidget
from app.ui.chat.plan import AgentChatPlanWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)

GROUP_CHAT_TAB_INDEX = 0


def _filmeto_agent_build_on_pool(
    workspace: Workspace,
    project_name: str,
    model: str,
    temperature: float,
):
    """Construct FilmetoAgent on TaskManager pool thread (heavy path off UI thread)."""
    from agent.filmeto_agent import FilmetoAgent

    return FilmetoAgent.get_instance(
        workspace=workspace,
        project_name=project_name,
        model=model,
        temperature=temperature,
        streaming=True,
    )


class AgentChatWidget(BaseWidget):
    """Agent chat component combining prompt input and chat history."""

    error_occurred = Signal(str)
    crew_member_activity = Signal(str, bool)  # member_name, is_active

    def __init__(self, workspace: Workspace, parent=None, defer_chat_list: bool = False):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self._defer_chat_list = defer_chat_list
        self._chat_list_placeholder: Optional[QWidget] = None

        self.agent = None
        self._agent_ready = False
        self._agent_lock = asyncio.Lock()
        self._agent_init_future: Optional[asyncio.Future] = None
        self._agent_init_worker_queued = False
        self._agent_init_generation = 0
        self._private_tabs: Dict[str, int] = {}  # member_id -> tab_index
        # Cached reference for blinker connect/disconnect (same object required)
        self._crew_activity_handler = self._on_crew_member_activity_from_agent
        self._pending_crew_activity: list = []  # [(member_name, active), ...] replayed after init

        self.error_occurred.connect(self._on_error)

        self._setup_ui()

        # Connect tab change to manage active state of private chat widgets
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        if self._defer_chat_list:
            QTimer.singleShot(0, self._ensure_chat_list_widget)
            self.prompt_input_widget.installEventFilter(self)
            _pq = getattr(self.prompt_input_widget, "_quick", None)
            if _pq is not None:
                _pq.installEventFilter(self)

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
        group_layout.setContentsMargins(2, 2, 2, 2)
        group_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("agent_chat_splitter")
        self.splitter.setHandleWidth(0)

        if self._defer_chat_list:
            self._chat_list_placeholder = QWidget()
            self._chat_list_placeholder.setObjectName("agent_chat_history_placeholder")
            self._chat_list_placeholder.setMinimumHeight(120)
            self._chat_list_placeholder.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            self._chat_list_placeholder.setStyleSheet("background-color: #2b2b2b;")
            self.splitter.addWidget(self._chat_list_placeholder)
            self.chat_history_widget = None
        else:
            self.chat_history_widget = AgentChatListWidget(self.workspace, self)
            self.chat_history_widget.setObjectName("agent_chat_history_widget")
            self.splitter.addWidget(self.chat_history_widget)

        self.plan_widget = AgentChatPlanWidget(self.workspace, self)
        self.plan_widget.setObjectName("agent_chat_plan_widget")
        self.splitter.addWidget(self.plan_widget)
        self.splitter.setCollapsible(1, False)

        self.prompt_input_widget = AgentPromptWidget(self.workspace, self)
        self.prompt_input_widget.setObjectName("agent_chat_prompt_widget")
        self.prompt_input_widget.prompt_submitted.connect(self._on_message_submitted)
        self.splitter.addWidget(self.prompt_input_widget)

        QTimer.singleShot(0, lambda: self.splitter.setSizes([600, self.plan_widget._collapsed_height, 200]))
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)

        group_layout.addWidget(self.splitter)

        if not self._defer_chat_list:
            self.chat_history_widget.reference_clicked.connect(self._on_reference_clicked)
            self.chat_history_widget.crew_member_activity.connect(self.crew_member_activity.emit)
        self.plan_widget.expandedChanged.connect(self._on_plan_expanded_changed)

        self.tab_widget.addTab(group_chat_container, "\ue89e")
        self.tab_widget.setTabToolTip(GROUP_CHAT_TAB_INDEX, tr("Group Chat"))

    def eventFilter(self, obj, event):
        if (
            self._defer_chat_list
            and self.chat_history_widget is None
            and event.type() == QEvent.Type.FocusIn
        ):
            targets = [self.prompt_input_widget]
            _pq = getattr(self.prompt_input_widget, "_quick", None)
            if _pq is not None:
                targets.append(_pq)
            if obj in targets:
                self._ensure_chat_list_widget()
        return super().eventFilter(obj, event)

    def _ensure_chat_list_widget(self) -> None:
        """Create AgentChatListWidget (QML) after first frame or prompt focus."""
        if self.chat_history_widget is not None:
            return
        ph = self._chat_list_placeholder
        if ph is None or self.splitter.indexOf(ph) < 0:
            return

        self.chat_history_widget = AgentChatListWidget(self.workspace, self)
        self.chat_history_widget.setObjectName("agent_chat_history_widget")
        self.splitter.replaceWidget(self.splitter.indexOf(ph), self.chat_history_widget)
        ph.deleteLater()
        self._chat_list_placeholder = None
        self._defer_chat_list = False
        self.prompt_input_widget.removeEventFilter(self)
        _pq = getattr(self.prompt_input_widget, "_quick", None)
        if _pq is not None:
            _pq.removeEventFilter(self)

        self.chat_history_widget.reference_clicked.connect(self._on_reference_clicked)
        self.chat_history_widget.crew_member_activity.connect(self.crew_member_activity.emit)

        QTimer.singleShot(
            0,
            lambda: self.splitter.setSizes(
                [
                    600,
                    self.plan_widget._collapsed_height,
                    200,
                ]
            ),
        )

    def open_private_chat(self, crew_member) -> None:
        """Open a private chat tab for a crew member, or switch to it if already open."""
        from app.ui.chat.private_chat_widget import PrivateChatWidget

        member_id = crew_member.member_id

        if member_id in self._private_tabs:
            tab_index = self._private_tabs[member_id]
            if tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(tab_index)
                return
            else:
                del self._private_tabs[member_id]

        private_widget = PrivateChatWidget(self.workspace, crew_member, self)
        # New private chat tab starts as inactive (will be activated by _on_tab_changed)
        private_widget.set_active(False)

        icon_text = crew_member.config.icon or crew_member.config.name[0].upper()
        tab_title = crew_member.config.name.title()

        tab_index = self.tab_widget.addTab(private_widget, f"{icon_text} {tab_title}")
        self._private_tabs[member_id] = tab_index

        self.tab_widget.setCurrentIndex(tab_index)

    def _on_tab_close_requested(self, index: int):
        """Handle tab close - only allow closing private chat tabs."""
        if index == GROUP_CHAT_TAB_INDEX:
            return

        widget = self.tab_widget.widget(index)
        member_id = None
        for mid, idx in self._private_tabs.items():
            if idx == index:
                member_id = mid
                break

        self.tab_widget.removeTab(index)

        if member_id:
            del self._private_tabs[member_id]

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
        """Rebuild the member_id->index mapping after tab removal."""
        from app.ui.chat.private_chat_widget import PrivateChatWidget
        new_map = {}
        for i in range(1, self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, PrivateChatWidget):
                new_map[widget.get_crew_member().member_id] = i
        self._private_tabs = new_map

    def _auto_initialize_agent(self):
        if not self.workspace or not self.workspace.get_project():
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            QTimer.singleShot(0, self._auto_initialize_agent)
            return
        asyncio.ensure_future(self._initialize_agent())

    async def _initialize_agent(self) -> bool:
        async with self._agent_lock:
            if self._agent_ready and self.agent:
                return True
            try:
                project = self.workspace.get_project()
                if not project:
                    return False
            except Exception as e:
                logger.error("Failed to get project for agent init: %s", e, exc_info=True)
                return False

        await self._await_agent_via_task_manager()

        async with self._agent_lock:
            return bool(self._agent_ready and self.agent)

    async def _await_agent_via_task_manager(self) -> None:
        if self._agent_ready and self.agent:
            return
        loop = asyncio.get_running_loop()
        if self._agent_init_future is None or self._agent_init_future.done():
            self._agent_init_future = loop.create_future()
            self._submit_filmeto_agent_worker()
        if self._agent_init_future is not None:
            await self._agent_init_future

    def _submit_filmeto_agent_worker(self) -> None:
        if self._agent_init_worker_queued:
            return
        project = self.workspace.get_project()
        if not project:
            if self._agent_init_future and not self._agent_init_future.done():
                self._agent_init_future.set_result(False)
            return
        project_name = self._extract_project_name(project) or "default"
        model, temperature = self._get_model_config()
        gen = self._agent_init_generation
        self._agent_init_worker_queued = True
        worker = FunctionWorker(
            _filmeto_agent_build_on_pool,
            self.workspace,
            project_name,
            model,
            temperature,
            task_id=f"filmeto-agent-{id(self)}-{gen}-{uuid.uuid4().hex[:8]}",
            task_type="filmeto_agent_init",
        )
        worker.signals.finished.connect(
            lambda tid, res, g=gen, pn=project_name: self._on_agent_pool_finished(tid, res, g, pn)
        )
        worker.signals.error.connect(
            lambda tid, msg, exc, g=gen, pn=project_name: self._on_agent_pool_error(
                tid, msg, exc, g, pn
            )
        )
        TaskManager.instance().submit(worker)

    def _on_agent_pool_finished(self, task_id: str, agent: Any, gen: int, project_name: str) -> None:
        self._agent_init_worker_queued = False
        if gen != self._agent_init_generation:
            from agent.filmeto_agent import FilmetoAgent

            try:
                FilmetoAgent.remove_instance(self.workspace, project_name)
            except Exception as e:
                logger.debug("Stale agent init discard: %s", e)
            return
        try:
            self.agent = agent
            self._agent_ready = True
            self.agent.signals.connect_crew_member_activity(
                self._crew_activity_handler, weak=False
            )
            for member_name, active in self._pending_crew_activity:
                self.crew_member_activity.emit(member_name, active)
            self._pending_crew_activity.clear()
            logger.info("Agent initialized for project '%s'", project_name)
            if self._agent_init_future and not self._agent_init_future.done():
                self._agent_init_future.set_result(True)
        except Exception as e:
            logger.error("Failed to finalize agent on main thread: %s", e, exc_info=True)
            self.agent = None
            self._agent_ready = False
            self._pending_crew_activity.clear()
            if self._agent_init_future and not self._agent_init_future.done():
                self._agent_init_future.set_result(False)

    def _on_agent_pool_error(
        self, task_id: str, msg: str, exc: object, gen: int, _project_name: str
    ) -> None:
        self._agent_init_worker_queued = False
        if gen != self._agent_init_generation:
            return
        logger.error("Failed to initialize agent in worker: %s", msg, exc_info=exc)
        self.agent = None
        self._agent_ready = False
        self._pending_crew_activity.clear()
        if self._agent_init_future and not self._agent_init_future.done():
            self._agent_init_future.set_result(False)

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
            if self.chat_history_widget is None:
                self._ensure_chat_list_widget()
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
        if self.chat_history_widget is None:
            self._ensure_chat_list_widget()
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
        # Use default model configuration without relying on settings
        model = 'qwen3.5-flash'
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

        if self.chat_history_widget is None:
            self._ensure_chat_list_widget()

        self._agent_init_generation += 1
        if self._agent_init_future and not self._agent_init_future.done():
            self._agent_init_future.set_result(False)
        self._agent_init_future = None
        self._agent_init_worker_queued = False

        self._agent_ready = False
        self._pending_crew_activity.clear()
        if self.agent and hasattr(self.agent, "signals"):
            try:
                self.agent.signals.disconnect_crew_member_activity(self._crew_activity_handler)
            except Exception as e:
                logger.debug("Could not disconnect crew_member_activity signal: %s", e)
        self.agent = None

        # 快速同步清理标签页
        self._close_all_private_tabs()

        # 异步初始化 Agent（使用 QTimer 延迟确保事件循环就绪）
        QTimer.singleShot(0, self._start_initialize_agent)

        # 异步刷新 plan_widget（避免阻塞主线程）
        if self.plan_widget:
            QTimer.singleShot(0, self.plan_widget.refresh_plan)

        # 异步刷新 chat_history_widget（避免阻塞主线程）
        if self.chat_history_widget:
            project_name = self._extract_project_name(project)
            QTimer.singleShot(0, lambda pn=project_name: self.chat_history_widget.on_project_switched(pn))

    def _start_initialize_agent(self):
        """Wrapper to start async initialization safely."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._initialize_agent())
            else:
                # If no loop is running, create a new task directly
                asyncio.create_task(self._initialize_agent())
        except RuntimeError:
            # Fallback: try to get the running loop
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, schedule for later
                QTimer.singleShot(10, self._start_initialize_agent)

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
        self.prompt_input_widget.set_enabled(enabled)
