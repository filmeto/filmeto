"""Agent panel for AI Agent interactions using AgentChatWidget for consistent experience."""

import logging
from typing import Optional
from PySide6.QtWidgets import QApplication

from app.ui.panels.base_panel import BasePanel
from app.data.workspace import Workspace
from utils.i18n_utils import tr


logger = logging.getLogger(__name__)


class AgentPanel(BasePanel):
    """Panel for AI Agent interactions using AgentChatWidget.

    Features:
    - Consistent experience with startup window
    - Multi-agent streaming display
    - Group-chat style agent collaboration visualization
    - Concurrent agent execution support
    - Structured content display (plans, tasks, media, references)
    """

    def __init__(self, workspace: Workspace, parent=None):
        """Initialize the agent panel."""
        import time
        init_start = time.time()
        super().__init__(workspace, parent)

        # Initialize agent chat component (will be set when panel is activated)
        self.agent_chat_component = None
        self._widgets_initialized = False

        init_time = (time.time() - init_start) * 1000
        logger.debug(f"⏱️  [AgentPanel] __init__ completed in {init_time:.2f}ms")

    def setup_ui(self):
        """Set up the UI components with vertical layout."""
        import time
        setup_start = time.time()
        self.set_panel_title(tr("Agent"))

        # Defer widget creation to avoid blocking UI initialization
        # Widgets will be created on first activation
        self.agent_chat_component = None
        self._widgets_initialized = False

        setup_time = (time.time() - setup_start) * 1000
        logger.debug(f"⏱️  [AgentPanel] setup_ui completed in {setup_time:.2f}ms")

    def _initialize_widgets(self):
        """Initialize heavy UI widgets (deferred until first activation)."""
        import time
        init_start = time.time()

        # Import widgets locally to defer expensive imports
        import_start = time.time()
        from app.ui.chat.agent_chat import AgentChatWidget
        import_time = (time.time() - import_start) * 1000
        logger.info(f"⏱️  Import AgentChatWidget: {import_time:.2f}ms")

        # Agent chat component (contains both chat history and prompt input)
        chat_start = time.time()
        self.agent_chat_component = AgentChatWidget(self.workspace, self)
        chat_time = (time.time() - chat_start) * 1000
        logger.info(f"⏱️  AgentChatWidget created: {chat_time:.2f}ms")

        self.content_layout.addWidget(self.agent_chat_component, 1)  # Stretch factor 1

        self._widgets_initialized = True

        init_time = (time.time() - init_start) * 1000
        logger.info(f"✅ Agent panel widgets initialized in {init_time:.2f}ms")

    def update_project(self, project):
        """Update agent with new project context."""
        if self.agent_chat_component:
            self.agent_chat_component.on_project_switch(project)

    def load_data(self):
        """Load agent data when panel is first activated."""
        super().load_data()
        # Agent will be initialized lazily on first message submission

    def on_activated(self):
        """Called when panel becomes visible."""
        super().on_activated()

        # Initialize widgets on first activation
        if not self._widgets_initialized:
            self._initialize_widgets()

        logger.info("✅ Agent panel activated")

    def on_deactivated(self):
        """Called when panel is hidden."""
        super().on_deactivated()
        logger.info("⏸️ Agent panel deactivated")
