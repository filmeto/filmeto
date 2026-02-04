"""Agent Chat Component combining prompt input and chat history.

This component combines the agent prompt widget and chat history widget
into a single reusable component that can be used in both the agent panel
and the startup window.
"""

from typing import Optional, Any
import asyncio
import logging
from PySide6.QtWidgets import QVBoxLayout, QWidget, QSplitter
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal, Slot
from qasync import asyncSlot

from agent import AgentMessage
from agent.chat.agent_chat_signals import AgentChatSignals
from app.ui.base_widget import BaseWidget
from app.data.workspace import Workspace
from app.ui.chat.agent_chat_history import AgentChatHistoryWidget
from app.ui.chat.plan import AgentChatPlanWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr
from utils.signal_utils import AsyncSignal

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

        # Track current project for agent instance management
        self._current_project_name = None
        self._current_project = None

        # Target project for delayed switching
        self._target_project_name = None
        self._agent_needs_sync = False

        # Initialize agent (will be set when project is available)
        self.agent = None
        self._is_processing = False
        self._initialization_in_progress = False

        # Note: We'll connect to signals after agent is initialized
        # The signals instance will be obtained from FilmetoAgent
        self._signals_connected = False

        # Queue and task for processing messages sequentially
        self._message_queue = asyncio.Queue()
        self._message_processing_task = None
        self._message_processor_started = False

        # Connect internal signal
        self.error_occurred.connect(self._on_error)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create a vertical splitter for the three components
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("agent_chat_splitter")
        # Set the splitter to be non-resizable by user
        self.splitter.setHandleWidth(0)

        # Chat history component (top, takes most space)
        self.chat_history_widget = AgentChatHistoryWidget(self.workspace, self)
        self.chat_history_widget.setObjectName("agent_chat_history_widget")
        self.splitter.addWidget(self.chat_history_widget)

        # Plan component (middle, collapsible)
        self.plan_widget = AgentChatPlanWidget(self.workspace, self)
        self.plan_widget.setObjectName("agent_chat_plan_widget")
        self.splitter.addWidget(self.plan_widget)
        # Set size policy to ensure proper sizing in splitter
        self.splitter.setCollapsible(1, False)  # Make sure plan widget is not collapsible by user

        # Prompt input component (bottom, auto-expands)
        self.prompt_input_widget = AgentPromptWidget(self.workspace, self)
        self.prompt_input_widget.setObjectName("agent_chat_prompt_widget")
        self.splitter.addWidget(self.prompt_input_widget)

        # Set initial sizes for the splitter with fixed heights
        # Chat history: takes remaining space (will expand to fill available space)
        # Plan widget: fixed collapsed height
        # Prompt input: fixed height for input area
        from PySide6.QtCore import QTimer
        def set_initial_splitter_sizes():
            self.splitter.setSizes([600, self.plan_widget._collapsed_height, 200])
            # Force the splitter to update its layout
            self.splitter.update()

        # Prevent widgets from being collapsible to maintain fixed layout
        self.splitter.setCollapsible(0, False)  # Chat history
        self.splitter.setCollapsible(1, False)  # Plan widget
        self.splitter.setCollapsible(2, False)  # Prompt input

        # Add the splitter to the main layout
        layout.addWidget(self.splitter)

        # Set initial sizes for the splitter with fixed heights
        # Do this after the splitter is added to the layout
        set_initial_splitter_sizes()

        # Connect signals
        self.prompt_input_widget.message_submitted.connect(self._on_message_submitted)
        self.chat_history_widget.reference_clicked.connect(self._on_reference_clicked)

    def _on_message_submitted(self, message: str):
        """Handle message submission from prompt input widget."""
        if not message:
            return

        # Add user message to chat history using new card-based display
        self.chat_history_widget.add_user_message(message)

        # Start async processing which will initialize agent if needed
        # Use the standard asyncio.create_task but wrapped in a way that's compatible with Qt
        # The agent system will handle sending the user message through AgentChatSignals
        asyncio.ensure_future(self._process_message_async(message))

    def _on_reference_clicked(self, ref_type: str, ref_id: str):
        """Handle reference click in chat history."""
        logger.info(f"Reference clicked: {ref_type} / {ref_id}")
        # TODO: Implement reference navigation (e.g., jump to timeline item, show task details)

    async def _process_message_async(self, message: str):
        """Process message asynchronously, initializing and syncing agent if needed."""
        try:
            # Sync agent to current workspace project (handles delayed switches)
            self.sync_agent_instance()

            # Ensure agent is initialized
            await self._ensure_agent_initialized()

            # Send message to agent
            await self._stream_response(message)
        except Exception as e:
            error_msg = f"{tr('Error')}: {str(e)}"
            self.error_occurred.emit(error_msg)
        finally:
            self._is_processing = False

    async def _ensure_agent_initialized(self) -> bool:
        """Ensure agent is initialized, showing status messages to user."""
        if self.agent:
            return True

        if self._initialization_in_progress:
            # Wait for ongoing initialization
            while self._initialization_in_progress:
                await asyncio.sleep(0.1)
            return self.agent is not None

        # Show initialization status
        init_message_id = self.chat_history_widget.start_streaming_message(tr("System"))
        self.chat_history_widget.update_streaming_message(
            init_message_id,
            tr("Agent is initializing, please wait...")
        )

        # Initialize agent
        await self._initialize_agent_async()

        # Update status
        if self.agent:
            self.chat_history_widget.update_streaming_message(
                init_message_id,
                tr("Agent initialization complete")
            )
            return True
        else:
            self.chat_history_widget.update_streaming_message(
                init_message_id,
                tr("Error: Agent initialization failed. Please ensure project is loaded.")
            )
            return False

    async def _stream_response(self, message: str):
        """Send message to agent, responses are delivered via AgentChatSignals."""
        # Simply call chat() - results will be delivered via signals
        await self.agent.chat(message)

    @Slot(str)
    def _on_error(self, error_message: str):
        """Handle error during agent processing."""
        if self.chat_history_widget:
            self.chat_history_widget.append_message(tr("System"), error_message)

    def _start_message_processor(self):
        """Start the message processing task if not already started."""
        if not self._message_processor_started:
            try:
                # Try to create the task, but if there's no running event loop, schedule it for later
                loop = asyncio.get_running_loop()
                if self._message_processing_task is None or self._message_processing_task.done():
                    self._message_processing_task = asyncio.create_task(self._process_messages())
                    self._message_processor_started = True
            except RuntimeError:
                # No running event loop yet, defer the task creation
                # We'll try again when the first message comes in
                pass
    
    async def _process_messages(self):
        """Process messages from the queue sequentially."""
        while True:
            try:
                # Get the next message from the queue
                message = await self._message_queue.get()
                
                if message is None:  # Sentinel value to stop the processor
                    break
                    
                if message:
                    try:
                        # Forward the AgentMessage directly to downstream components
                        await self.chat_history_widget.handle_agent_message(message)
                        if self.plan_widget:
                            await self.plan_widget.handle_agent_message(message)
                    except Exception as e:
                        logger.error(f"Error handling agent message: {e}", exc_info=True)
                    finally:
                        # Mark the task as done
                        self._message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message processor: {e}", exc_info=True)
    
    @asyncSlot()
    async def _on_agent_message_sent(self, sender, message:AgentMessage):
        """Handle agent message sent via AgentChatSignals by queuing it for processing."""
        # Put the message in the queue for sequential processing
        await self._message_queue.put(message)
        
        # Start the processor if needed (first message triggers the task creation)
        self._start_message_processor()

    def _extract_project_name(self, project: Any) -> str:
        """
        Extract project name from a project object.

        Args:
            project: Project object (can be object with project_name/name attribute, or string)

        Returns:
            Project name as string, or "default" if not found
        """
        if project:
            if hasattr(project, 'project_name'):
                return project.project_name
            elif hasattr(project, 'name'):
                return project.name
            elif isinstance(project, str):
                return project
        return "default"

    def _get_model_config(self) -> tuple:
        """
        Get model configuration from workspace settings.

        Returns:
            Tuple of (model_name, temperature)
        """
        settings = self.workspace.get_settings()
        model = settings.get('ai_services.default_model', 'gpt-4o-mini') if settings else 'gpt-4o-mini'
        temperature = 0.7
        return model, temperature

    def _ensure_agent_for_project(self, project_name: str, project_obj: Any = None) -> bool:
        """
        Ensure an agent instance exists for the specified project.

        This is the core method that creates or retrieves agent instances.
        It handles all the common logic for both initial creation and project switching.

        Args:
            project_name: Name of the project
            project_obj: Optional project object for reference

        Returns:
            True if agent was created/retrieved successfully, False otherwise
        """
        from agent.filmeto_agent import FilmetoAgent

        if not project_name:
            project_name = "default"
            logger.warning("⚠️ No project name provided, using 'default'")

        # Check if we already have the right instance
        if self._current_project_name == project_name and self.agent:
            logger.debug(f"Agent already exists for project '{project_name}'")
            return True

        logger.info(f"🔧 Ensuring agent instance for project '{project_name}'")

        # Get model configuration
        model, temperature = self._get_model_config()

        try:
            # Get or create agent instance
            self.agent = FilmetoAgent.get_instance(
                workspace=self.workspace,
                project_name=project_name,
                model=model,
                temperature=temperature,
                streaming=True
            )

            # Update current tracking
            self._current_project_name = project_name
            self._current_project = project_obj

            logger.info(f"✅ Agent ready for project '{project_name}'")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to get agent instance for project '{project_name}': {e}", exc_info=True)
            return False

    async def _initialize_agent_async(self):
        """Initialize the agent asynchronously with current workspace and project."""
        if self._initialization_in_progress or self.agent:
            return

        self._initialization_in_progress = True

        try:
            # Run initialization in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._initialize_agent_sync)
        except Exception as e:
            logger.error(f"❌ Error initializing agent: {e}", exc_info=True)
        finally:
            self._initialization_in_progress = False

    def _initialize_agent_sync(self):
        """Synchronously initialize the agent with current workspace and project."""
        import time
        init_start = time.time()
        logger.info("⏱️  [AgentChatComponent] Starting lazy agent initialization...")

        # Get current project from workspace
        project = self.workspace.get_project()
        project_name = self._extract_project_name(project)

        # Ensure agent instance exists
        success = self._ensure_agent_for_project(project_name, project)

        if success:
            # Connect to FilmetoAgent's message handler
            if not self._signals_connected and self.agent:
                self.agent.connect_message_handler(self._on_agent_message_sent)
                self._signals_connected = True
                logger.info("✅ Connected to FilmetoAgent's message handler")

            init_time = (time.time() - init_start) * 1000
            # Check if agent has a valid LLM initialized
            if not self.agent.llm_service.validate_config():
                logger.warning(f"⚠️ Agent initialized in {init_time:.2f}ms but LLM is not configured")
            else:
                logger.info(f"✅ Agent initialized successfully for project '{project_name}' in {init_time:.2f}ms")
        else:
            logger.error(f"❌ Agent initialization failed for project '{project_name}'")

    def on_project_switch(self, project: Any) -> None:
        """
        Handle project switching with delayed agent instance switching.

        The agent instance switches lazily when next accessed, ensuring we use
        the workspace's real current project rather than stale references.

        Args:
            project: The new project (object, name string, or None)
        """
        new_project_name = self._extract_project_name(project)

        if self._target_project_name == new_project_name:
            return

        logger.info(f"🔄 Project switch requested: '{self._current_project_name}' → '{new_project_name}' (delayed)")

        self._target_project_name = new_project_name
        self._agent_needs_sync = True

        # Update UI immediately
        if self.plan_widget:
            self.plan_widget.refresh_plan()
        if self.chat_history_widget:
            self.chat_history_widget._load_recent_conversation()

    def sync_agent_instance(self) -> None:
        """
        Synchronize the agent instance with the workspace's current project.

        This ensures the agent instance matches the workspace's real current project.
        Called automatically before using the agent.

        Key: we query workspace.get_project() to get the REAL current project.
        """
        # Early return if no sync needed and we have an agent
        if not self._agent_needs_sync and self.agent:
            return

        # Get the REAL current project from workspace
        current_workspace_project = self.workspace.get_project()
        real_project_name = self._extract_project_name(current_workspace_project)

        # Fall back to target if workspace has no project
        if not current_workspace_project:
            real_project_name = self._target_project_name or "default"

        # Ensure agent instance for the real current project
        if self._ensure_agent_for_project(real_project_name, current_workspace_project):
            self._agent_needs_sync = False

    def update_project(self, project):
        """
        Update agent with new project context (legacy method).

        This method is kept for backward compatibility. New code should use
        on_project_switch() which properly manages agent instances per project.

        Args:
            project: The new project object
        """
        # Delegate to on_project_switch
        self.on_project_switch(project)

    def get_current_project_name(self) -> Optional[str]:
        """
        Get the name of the current project (the agent instance's project).

        Note: This returns the project of the currently loaded agent instance,
        which may differ from the target project if a switch is pending.
        Use get_target_project_name() to get the pending target project.

        Returns:
            The current agent instance's project name, or None if not set
        """
        return self._current_project_name

    def get_target_project_name(self) -> Optional[str]:
        """
        Get the name of the target project (where we want to switch to).

        Returns:
            The target project name if a switch is pending, otherwise the current project name
        """
        if self._agent_needs_sync and self._target_project_name:
            return self._target_project_name
        return self._current_project_name

    def get_current_project(self) -> Optional[Any]:
        """
        Get the current project object (the agent instance's project).

        Note: This returns the project of the currently loaded agent instance,
        which may differ from the target project if a switch is pending.

        Returns:
            The current agent instance's project object, or None if not set
        """
        return self._current_project

    def get_agent_instance_key(self) -> Optional[str]:
        """
        Get the instance key for the current agent.

        Returns:
            The instance key in format "workspace_path:project_name", or None if no agent
        """
        if not self.agent or not self._current_project_name:
            return None
        from agent.filmeto_agent import FilmetoAgent
        workspace_path = FilmetoAgent._get_workspace_path(self.workspace)
        return f"{workspace_path}:{self._current_project_name}"

    def is_agent_sync_needed(self) -> bool:
        """
        Check if agent instance synchronization is needed.

        Returns:
            True if a project switch is pending and agent needs to be synced
        """
        return self._agent_needs_sync

    def get_workspace_current_project_name(self) -> Optional[str]:
        """
        Get the real current project name from the workspace.

        This method queries the workspace directly to get the actual current project,
        which is useful for debugging or verifying sync state.

        Returns:
            The workspace's current project name, or None if not available
        """
        project = self.workspace.get_project()
        return self._extract_project_name(project) if project else None

    def set_enabled(self, enabled: bool):
        """Enable or disable the entire component."""
        if self.prompt_input_widget:
            self.prompt_input_widget.set_enabled(enabled)
        self._is_processing = not enabled