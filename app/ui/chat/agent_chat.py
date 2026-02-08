"""Agent Chat Component combining prompt input and chat history.

This component combines the agent prompt widget and chat history widget
into a single reusable component that can be used in both the agent panel
and the startup window.
"""

from typing import Optional, Any
import asyncio
import logging
from PySide6.QtWidgets import QVBoxLayout, QWidget, QSplitter
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import Signal, Slot
from qasync import asyncSlot

from app.ui.base_widget import BaseWidget
from app.data.workspace import Workspace
from app.ui.chat.list import AgentChatListWidget
from app.ui.chat.plan import AgentChatPlanWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class AgentChatWidget(BaseWidget):
    """Agent chat component combining prompt input and chat history."""

    # Signal for error reporting
    error_occurred = Signal(str)

    def __init__(self, workspace: Workspace, parent=None):
        """Initialize the agent chat component."""
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        # Agent management - simplified state
        self.agent = None
        self._agent_ready = False
        self._agent_lock = asyncio.Lock()

        # Connect internal signal
        self.error_occurred.connect(self._on_error)

        self._setup_ui()

        # Auto-initialize agent when workspace has a project
        QTimer.singleShot(100, self._auto_initialize_agent)

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create a vertical splitter for the three components
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("agent_chat_splitter")
        self.splitter.setHandleWidth(0)

        # Chat history component (top, takes most space)
        self.chat_history_widget = AgentChatListWidget(self.workspace, self)
        self.chat_history_widget.setObjectName("agent_chat_history_widget")
        self.splitter.addWidget(self.chat_history_widget)

        # Plan component (middle, collapsible)
        self.plan_widget = AgentChatPlanWidget(self.workspace, self)
        self.plan_widget.setObjectName("agent_chat_plan_widget")
        self.splitter.addWidget(self.plan_widget)
        self.splitter.setCollapsible(1, False)

        # Prompt input component (bottom, auto-expands)
        self.prompt_input_widget = AgentPromptWidget(self.workspace, self)
        self.prompt_input_widget.setObjectName("agent_chat_prompt_widget")
        self.splitter.addWidget(self.prompt_input_widget)

        # Set initial sizes
        QTimer.singleShot(0, lambda: self.splitter.setSizes([600, self.plan_widget._collapsed_height, 200]))
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)

        layout.addWidget(self.splitter)

        # Connect signals
        self.prompt_input_widget.message_submitted.connect(self._on_message_submitted)
        self.chat_history_widget.reference_clicked.connect(self._on_reference_clicked)

    def _auto_initialize_agent(self):
        """Auto-initialize agent when workspace has a project."""
        if self.workspace and self.workspace.get_project():
            asyncio.ensure_future(self._initialize_agent())

    async def _initialize_agent(self) -> bool:
        """
        Initialize agent asynchronously with current workspace project.

        Returns:
            True if initialization succeeded, False otherwise
        """
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

                logger.info(f"✅ Agent initialized for project '{project_name}'")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to initialize agent: {e}", exc_info=True)
                self.agent = None
                self._agent_ready = False
                return False

    def _on_message_submitted(self, message: str):
        """Handle message submission from prompt input widget."""
        if not message:
            return

        # User message will be added through history listener and loaded by polling
        # No need to manually add it here to avoid duplication
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._process_message_async(message))
        except RuntimeError:
            # No event loop running, schedule via QTimer
            QTimer.singleShot(0, lambda: asyncio.ensure_future(self._process_message_async(message)))

    def _on_reference_clicked(self, ref_type: str, ref_id: str):
        """Handle reference click in chat history."""
        logger.info(f"Reference clicked: {ref_type} / {ref_id}")

    async def _process_message_async(self, message: str):
        """Process message asynchronously, initializing agent if needed."""
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
        """Handle error during agent processing."""
        if self.chat_history_widget:
            self.chat_history_widget.append_message(tr("System"), error_message)

    def _extract_project_name(self, project: Any) -> str:
        """Extract project name from a project object."""
        if project:
            if hasattr(project, 'project_name'):
                return project.project_name
            elif hasattr(project, 'name'):
                return project.name
            elif isinstance(project, str):
                return project
        return "default"

    def _get_model_config(self) -> tuple:
        """Get model configuration from workspace settings."""
        settings = self.workspace.get_settings()
        model = settings.get('ai_services.default_model', 'gpt-4o-mini') if settings else 'gpt-4o-mini'
        temperature = 0.7
        return model, temperature

    def on_project_switch(self, project: Any) -> None:
        """Handle project switching by reinitializing the agent."""
        if not project:
            return

        # Reset agent state
        self._agent_ready = False
        self.agent = None

        # Initialize with new project
        asyncio.ensure_future(self._initialize_agent())

        # Update UI
        if self.plan_widget:
            self.plan_widget.refresh_plan()
        if self.chat_history_widget:
            self.chat_history_widget.on_project_switched(self._extract_project_name(project))

    def get_current_project_name(self) -> Optional[str]:
        """Get the current agent's project name."""
        return self._extract_project_name(self.workspace.get_project()) if self.agent else None

    def set_enabled(self, enabled: bool):
        """Enable or disable the entire component."""
        if self.prompt_input_widget:
            self.prompt_input_widget.set_enabled(enabled)
