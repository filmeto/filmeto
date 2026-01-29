"""Agent Chat Component combining prompt input and chat history.

This component combines the agent prompt widget and chat history widget
into a single reusable component that can be used in both the agent panel
and the startup window.
"""

from typing import Optional
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
from app.ui.chat.agent_chat_plan import AgentChatPlanWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr
from utils.signal_utils import AsyncSignal

logger = logging.getLogger(__name__)


class AgentChatWidget(BaseWidget):
    """Agent chat component combining prompt input and chat history."""

    # Signals for async operations
    response_token_received = Signal(str)
    response_complete = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, workspace: Workspace, parent=None):
        """Initialize the agent chat component."""
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        # Initialize agent (will be set when project is available)
        # Using forward reference to avoid import at class definition time
        self.agent = None
        self._current_response = ""
        self._current_message_id = None
        self._is_processing = False
        self._initialization_in_progress = False

        # Connect to AgentChatSignals for message handling
        self._signals = AgentChatSignals()
        self._signals.connect(self._on_agent_message_sent)
        
        # Queue and task for processing messages sequentially
        self._message_queue = asyncio.Queue()
        self._message_processing_task = None
        
        # Defer starting the message processor until after the event loop is running
        # We'll start it when the first message arrives
        self._message_processor_started = False

        # Connect internal signals
        self.response_token_received.connect(self._on_token_received)
        self.response_complete.connect(self._on_response_complete)
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
        """Process message asynchronously, initializing agent if needed."""
        # Check if agent is initialized, if not, initialize it first
        if not self.agent:
            if not self._initialization_in_progress:
                # Show message that agent is initializing
                init_message_id = self.chat_history_widget.start_streaming_message(tr("System"))
                self.chat_history_widget.update_streaming_message(
                    init_message_id,
                    tr("Agent is initializing, please wait...")
                )

                # Initialize agent asynchronously
                await self._initialize_agent_async()

                # Update initialization message
                if self.agent:
                    self.chat_history_widget.update_streaming_message(
                        init_message_id,
                        tr("Agent initialization complete")
                    )
                else:
                    self.chat_history_widget.update_streaming_message(
                        init_message_id,
                        tr("Error: Agent initialization failed. Please ensure project is loaded.")
                    )
                    return
            else:
                # Wait for ongoing initialization to complete
                while self._initialization_in_progress:
                    await asyncio.sleep(0.1)

                if not self.agent:
                    self.chat_history_widget.append_message(
                        tr("System"),
                        tr("Error: Agent initialization failed. Please ensure project is loaded.")
                    )
                    return

        # In group chat mode, don't disable input to allow continuous messaging
        self._is_processing = True

        # Reset current response - don't create a message card yet
        # The streaming events will create cards as agents start responding
        self._current_response = ""
        self._current_message_id = None

        # Start streaming response
        try:
            await self._stream_response(message)
        except Exception as e:
            # If streaming fails, show error
            error_msg = f"{tr('Error')}: {str(e)}"
            self.error_occurred.emit(error_msg)

    async def _stream_response(self, message: str):
        """Send message to agent, responses are delivered via AgentChatSignals."""
        try:
            # Simply call chat() - results will be delivered via signals
            await self.agent.chat(message)
        except Exception as e:
            # Ensure error is displayed
            error_msg = f"{tr('Error')}: {str(e)}"
            self.error_occurred.emit(error_msg)
        finally:
            # Reset processing state
            self._is_processing = False
            # Note: In group chat mode, we don't re-enable the input widget
            # since it was never disabled

    @Slot(str)
    def _on_token_received(self, token: str):
        """Handle received token from agent (legacy API)."""
        self._current_response += token

        # If we have a current message ID (legacy mode), update it
        if self._current_message_id and self.chat_history_widget:
            self.chat_history_widget.update_streaming_message(
                self._current_message_id,
                self._current_response
            )

    @Slot(str)
    def _on_response_complete(self, response: str):
        """Handle complete response from agent."""
        # Update the final message if in legacy mode
        if self._current_message_id and self.chat_history_widget:
            self.chat_history_widget.update_streaming_message(
                self._current_message_id,
                response
            )

        # Clear message ID
        self._current_message_id = None

        # Reset processing state
        self._is_processing = False
        # Note: In group chat mode, we don't re-enable the input widget
        # since it was never disabled

    @Slot(str)
    def _on_error(self, error_message: str):
        """Handle error during agent processing."""
        if not self.chat_history_widget:
            logger.error(f"❌ Error but chat history widget not initialized: {error_message}")
            return

        # If there's a streaming message in progress, update it with error
        if self._current_message_id:
            self.chat_history_widget.update_streaming_message(
                self._current_message_id,
                error_message
            )
            self._current_message_id = None
        else:
            # Add error message as new system message
            self.chat_history_widget.append_message(tr("System"), error_message)

        # Clear current response
        self._current_response = ""

        # Reset processing state
        self._is_processing = False
        # Note: In group chat mode, we don't re-enable the input widget
        # since it was never disabled

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
                        # Get session from agent
                        session = self.agent.get_current_session() if self.agent else None

                        # Forward the AgentMessage directly to downstream components
                        await self.chat_history_widget.handle_agent_message(message, session)
                        if self.plan_widget:
                            await self.plan_widget.handle_agent_message(message, session)
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
            logger.error(f"❌ Error initializing agent: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._initialization_in_progress = False

    def _initialize_agent_sync(self):
        """Synchronously initialize the agent with current workspace and project."""
        import time
        init_start = time.time()
        logger.info("⏱️  [AgentChatComponent] Starting lazy agent initialization...")
        try:
            # Lazy import heavy agent module only when needed
            from agent.filmeto_agent import FilmetoAgent

            # Get current project from workspace
            project = self.workspace.get_project()

            # Get settings (model from settings, let FilmetoAgent read api_key internally)
            settings = self.workspace.get_settings()
            model = settings.get('ai_services.default_model', 'gpt-4o-mini') if settings else 'gpt-4o-mini'
            temperature = 0.7  # Could also make this configurable

            # Create agent instance (it will handle project loading internally)
            self.agent = FilmetoAgent(
                workspace=self.workspace,
                project=project,
                model=model,
                temperature=temperature,
                streaming=True
            )

            init_time = (time.time() - init_start) * 1000
            # Check if agent has a valid LLM initialized
            if not self.agent.llm_service.validate_config():
                logger.warning(f"⚠️ Agent initialized in {init_time:.2f}ms but LLM is not configured (missing API key or base URL)")
            else:
                logger.info(f"✅ Agent initialized successfully in {init_time:.2f}ms")
        except Exception as e:
            logger.error(f"❌ Error initializing agent: {e}")
            import traceback
            traceback.print_exc()

    def update_project(self, project):
        """Update agent with new project context."""
        if self.agent:
            self.agent.update_context(project=project)
        if self.plan_widget:
            self.plan_widget.refresh_plan()
        if self.chat_history_widget:
            # Reload the conversation history for the new project
            self.chat_history_widget._load_recent_conversation()

    def set_enabled(self, enabled: bool):
        """Enable or disable the entire component."""
        if self.prompt_input_widget:
            self.prompt_input_widget.set_enabled(enabled)
        self._is_processing = not enabled