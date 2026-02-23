import asyncio
import inspect
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from agent.llm.llm_service import LlmService
from agent.tool.tool_service import ToolService
from agent.tool.tool_context import ToolContext
from agent.chat.content import (
    StructureContent,
    TextContent,
    ThinkingContent,
    LlmOutputContent,
    ToolCallContent,
    ToolResponseContent,
    ProgressContent,
    MetadataContent,
    ErrorContent,
    TodoWriteContent,
)


logger = logging.getLogger(__name__)

from .types import (
    AgentEvent,
    AgentEventType,
    ReactStatus,
    CheckpointData,
    ReactAction,
    ToolAction,
    FinalAction,
    ErrorAction,
    ReactActionParser,
    ActionType,
    TodoState,
)
from .storage import ReactStorage


class React:
    """
    A generic ReAct processor that handles the ReAct (Reasoning and Acting) loop.
    """

    def __init__(
        self,
        *,
        workspace,
        project_name: str,
        react_type: str,
        build_prompt_function: Callable[[str], str],
        available_tool_names: Optional[List[str]] = None,
        llm_service: Optional[LlmService] = None,
        max_steps: int = 20,
        checkpoint_interval: int = 1,
    ):
        self.workspace = workspace
        self.project_name = project_name
        self.react_type = react_type
        self.build_prompt_function = build_prompt_function
        self.available_tool_names = available_tool_names or []
        self.llm_service = llm_service or LlmService(workspace)
        self.max_steps = max_steps
        self.checkpoint_interval = checkpoint_interval
        self.tool_service = ToolService()

        if workspace and hasattr(workspace, "get_path"):
            self.workspace_root = workspace.get_path()
        else:
            self.workspace_root = "workspace"

        self.storage = ReactStorage(
            project_name=project_name,
            react_type=react_type,
            workspace_root=self.workspace_root,
        )

        self.run_id: str = ""
        self.step_id: int = 0
        self.status: str = ReactStatus.IDLE
        self.messages: List[Dict[str, str]] = []
        self.pending_user_messages: List[str] = []
        self._in_react_loop: bool = False
        self._loop_lock = asyncio.Lock()
        self._steps_since_checkpoint: int = 0

        # Metrics
        self._total_llm_calls: int = 0
        self._total_tool_calls: int = 0
        self._llm_duration_ms: float = 0.0
        self._tool_duration_ms: float = 0.0

        # TODO state
        self.todo_state = TodoState()
        self._pending_todo_update = None

        checkpoint = self.storage.load_checkpoint()
        if checkpoint and checkpoint.status == ReactStatus.RUNNING:
            self.run_id = checkpoint.run_id
            self.step_id = checkpoint.step_id
            self.status = checkpoint.status
            self.messages = checkpoint.messages
            self.pending_user_messages = list(checkpoint.pending_user_messages)
            # Restore TODO state from checkpoint
            if checkpoint.todo_state:
                self.todo_state = TodoState.from_dict(checkpoint.todo_state)

    def _create_event(self, event_type: str, content=None) -> AgentEvent:
        """
        Create an AgentEvent with instance context.

        Args:
            event_type: Type of event
            content: Optional StructureContent object for the event

        Returns:
            AgentEvent object
        """
        return AgentEvent.create(
            event_type=event_type,
            project_name=self.project_name,
            react_type=self.react_type,
            run_id=self.run_id,
            step_id=self.step_id,
            content=content
        )

    def _update_checkpoint(self) -> None:
        """Save checkpoint state to storage."""
        checkpoint_data = CheckpointData(
            run_id=self.run_id,
            step_id=self.step_id,
            status=self.status,
            messages=self.messages,
            pending_user_messages=self.pending_user_messages,
            last_tool_calls=[],
            last_tool_results=[],
            todo_state=self.todo_state.to_dict(),
        )
        try:
            self.storage.save_checkpoint(checkpoint_data)
        except (IOError, OSError) as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _maybe_update_checkpoint(self) -> None:
        """Update checkpoint only if enough steps have passed."""
        self._steps_since_checkpoint += 1
        if self._steps_since_checkpoint >= self.checkpoint_interval:
            self._update_checkpoint()
            self._steps_since_checkpoint = 0

    def _drain_pending_messages(self) -> List[str]:
        messages = self.pending_user_messages[:]
        self.pending_user_messages.clear()
        return messages

    def _start_new_run(self, user_questions: List[str]) -> None:
        """Start a new run with user questions.

        Args:
            user_questions: List of user questions to build the prompt.
        """
        self.run_id = f"run_{uuid.uuid4().hex[:16]}_{self.project_name}_{self.react_type}"
        self.step_id = 0
        self.status = ReactStatus.RUNNING
        self._steps_since_checkpoint = 0

        # Reset metrics for new run
        self._total_llm_calls = 0
        self._total_tool_calls = 0
        self._llm_duration_ms = 0.0
        self._tool_duration_ms = 0.0

        # Concatenate multiple user questions if present
        combined_question = "\n".join(user_questions) if user_questions else ""

        # Build the task context using the build_prompt_function
        task_context = self.build_prompt_function(combined_question)

        # Format tools from ToolService for the prompt
        import json
        tools_formatted = ""
        for tool_name in self.available_tool_names:
            metadata = self.tool_service.get_tool_metadata(tool_name)
            tools_formatted += f"### {metadata.name}\n"
            tools_formatted += f"**Description**: {metadata.description}\n\n"

            if metadata.parameters:
                tools_formatted += "**Arguments**:\n"
                tools_formatted += "```json\n"
                args_schema = {
                    "type": "object",
                    "properties": {
                        p.name: {
                            "type": p.param_type,
                            "description": p.description
                        } for p in metadata.parameters
                    },
                    "required": [p.name for p in metadata.parameters if p.required]
                }
                tools_formatted += json.dumps(args_schema, indent=2)
                tools_formatted += "\n```\n\n"

        # Use the prompt service to render the template
        from agent.prompt.prompt_service import prompt_service
        user_prompt = prompt_service.render_prompt(
            name="react_global_template",
            tools_formatted=tools_formatted,
            task_context=task_context
        )

        if user_prompt is None:
            raise RuntimeError("Global ReAct prompt template 'react_global_template' not found. Please ensure the template exists in the prompt system.")

        self.messages = [{"role": "user", "content": user_prompt}]

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call LLM service with timing and metrics tracking.

        Returns:
            The content of the LLM response message.
        """
        if not self.llm_service.validate_config():
            logger.warning("LLM service is not configured")
            return '{"type": "final", "final": "LLM service is not configured."}'

        loop = asyncio.get_event_loop()
        model_to_use = self.llm_service.default_model or "qwen-plus"
        temperature_to_use = getattr(self.llm_service, "temperature", 0.7)

        start_time = time.time()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.llm_service.completion(
                    model=model_to_use,
                    messages=messages,
                    temperature=temperature_to_use,
                    stream=False,
                ),
            )
            duration_ms = (time.time() - start_time) * 1000
            self._total_llm_calls += 1
            self._llm_duration_ms += duration_ms
            logger.debug(f"LLM call completed in {duration_ms:.2f}ms")

            # Extract content using LlmService's extract_content method
            return self.llm_service.extract_content(response)
        except Exception as exc:
            logger.error(f"LLM call failed: {exc}", exc_info=True)
            return f'{{"type": "final", "final": "LLM call failed: {str(exc)}"}}'

    def _parse_action(self, response_text: str) -> ReactAction:
        """
        Parse LLM response into a ReactAction.

        Uses ReactActionParser for robust parsing with multiple fallback strategies.
        """
        return ReactActionParser.parse(response_text)

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute tool with timing and metrics tracking.

        Tool completion is determined by the completion of this method call,
        not by receiving a tool_end event in the stream. This ensures that
        nested tool calls (e.g., tools called within a skill) don't cause
        premature termination of the parent tool execution.

        All events are still yielded for real-time display.
        """
        start_time = time.time()
        tool_context = ToolContext(
            workspace=self.workspace,
            project_name=self.project_name,
            _react_instance=self,  # Pass reference to React instance for TodoWriteTool
        )

        try:
            # Track the final result from this specific tool execution
            # (not from nested tools within the tool)
            final_result = None
            has_error = False

            # The async for loop completes when tool.execute() completes
            # This is the definitive signal that the tool is done
            async for event in self.tool_service.execute_tool(
                tool_name,
                tool_args,
                tool_context,
                project_name=self.project_name,
                react_type=self.react_type,
                run_id=self.run_id,
                step_id=self.step_id,
            ):
                # Process different event types from ToolService
                if event.event_type == "tool_start":
                    # Only emit progress for the top-level tool being executed
                    # (identified by matching tool_name)
                    if (event.content and hasattr(event.content, 'tool_name') and
                            event.content.tool_name == tool_name):
                        yield {"progress": f"Starting tool: {tool_name}"}

                elif event.event_type == "tool_progress":
                    progress = event.payload.get("progress")
                    if progress:
                        yield {"progress": progress}

                elif event.event_type == "tool_end":
                    # Check if this is the top-level tool_end or a nested one
                    # by comparing the tool_name in the event
                    is_top_level_end = (
                        event.content and
                        hasattr(event.content, 'tool_name') and
                        event.content.tool_name == tool_name
                    )

                    if is_top_level_end:
                        # This is the actual end of the tool we're executing
                        # Extract result from content or payload (backward compat)
                        if event.content and hasattr(event.content, 'result'):
                            final_result = event.content.result
                        elif event.payload:
                            final_result = event.payload.get("result")
                        else:
                            final_result = None

                        duration_ms = (time.time() - start_time) * 1000
                        self._total_tool_calls += 1
                        self._tool_duration_ms += duration_ms
                        logger.debug(f"Tool '{tool_name}' completed in {duration_ms:.2f}ms")

                        # Forward the tool_end event and return - this is safe now
                        # because we've verified it's the top-level tool_end
                        yield event
                        return
                    else:
                        # This is a nested tool_end (e.g., from a tool called within a skill)
                        # Forward it for display but don't return
                        yield event

                elif event.event_type == "error":
                    # Check if this error is for the top-level tool
                    is_top_level_error = (
                        event.content and
                        hasattr(event.content, 'tool_name') and
                        event.content.tool_name == tool_name
                    )

                    if is_top_level_error:
                        # Extract error from content or payload (backward compat)
                        if event.content and hasattr(event.content, 'error_message'):
                            error_msg = event.content.error_message
                        elif event.payload:
                            error_msg = event.payload.get("error", "Unknown error")
                        else:
                            error_msg = "Unknown error"

                        duration_ms = (time.time() - start_time) * 1000
                        logger.error(f"Tool '{tool_name}' failed after {duration_ms:.2f}ms: {error_msg}")

                        yield event
                        has_error = True
                        return
                    else:
                        # Nested error - forward for display but don't return
                        yield event

                else:
                    # Forward all other events directly (e.g., LLM_THINKING, nested TOOL_START/PROGRESS/END from skill_chat)
                    yield event

            # If we get here without a tool_end event, something went wrong
            if not has_error:
                duration_ms = (time.time() - start_time) * 1000
                self._total_tool_calls += 1
                self._tool_duration_ms += duration_ms
                logger.debug(f"Tool '{tool_name}' completed in {duration_ms:.2f}ms (no final event)")
                yield {"result": final_result}

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Tool '{tool_name}' failed after {duration_ms:.2f}ms: {exc}", exc_info=True)
            yield {"error": str(exc)}

    async def chat_stream(self, user_message: Optional[str]) -> AsyncGenerator[AgentEvent, None]:
        """Main ReAct loop with thread safety and iterative pending message processing."""
        async with self._loop_lock:
            if self._in_react_loop:
                # If loop is already running, queue the message and return
                if user_message:
                    self.pending_user_messages.append(user_message)
                    self._maybe_update_checkpoint()
                return

            # Add initial user message
            if user_message:
                self.pending_user_messages.append(user_message)

            # Gather all pending messages for starting new run
            pending_messages = self._drain_pending_messages()

            # Start new run if needed (with user questions)
            if not self.run_id or self.status in {ReactStatus.IDLE, ReactStatus.FINAL, ReactStatus.FAILED}:
                self._start_new_run(pending_messages)

            self._in_react_loop = True
            self._maybe_update_checkpoint()

        try:
            # Main ReAct loop - iteratively process all messages
            while True:
                # Process messages until we reach a terminal state
                for step in range(self.step_id, self.max_steps):
                    self.step_id = step
                    self._maybe_update_checkpoint()

                    # Check for new pending messages (added while we're processing)
                    new_pending = self._drain_pending_messages()
                    for msg in new_pending:
                        self.messages.append({"role": "user", "content": msg})

                    response_text = await self._call_llm(self.messages)
                    action = self._parse_action(response_text)
                    thinking = ReactActionParser.get_thinking_message(action, step + 1, self.max_steps)
                    yield self._create_event(
                        AgentEventType.LLM_THINKING,
                        content=ThinkingContent(
                            thought=thinking,
                            step=step + 1,
                            total_steps=self.max_steps,
                            title="Thinking",
                            description=f"Step {step + 1}/{self.max_steps}"
                        )
                    )

                    yield self._create_event(
                        AgentEventType.LLM_OUTPUT,
                        content=LlmOutputContent(
                            output=response_text,
                            title="LLM Output",
                            description="Raw LLM response"
                        )
                    )

                    if action.is_tool():
                        assert isinstance(action, ToolAction), f"Expected ToolAction, got {type(action)}"
                        # Validate tool_name before execution
                        if not action.tool_name:
                            error_msg = "Tool name is empty - LLM returned a tool action without specifying which tool to use"
                            logger.warning(error_msg)
                            yield self._create_event(
                                AgentEventType.ERROR,
                                content=ErrorContent(
                                    error_message=error_msg,
                                    error_type="ValidationError",
                                    details=f"Response: {response_text[:200]}",
                                    title="Tool Name Error",
                                    description="LLM did not specify which tool to use"
                                )
                            )
                            self.messages.append({"role": "assistant", "content": response_text})
                            self.messages.append({"role": "user", "content": f"Error: {error_msg}. Please specify a valid tool name."})
                            continue
                        yield self._create_event(
                            AgentEventType.TOOL_START,
                            content=ToolCallContent(
                                tool_name=action.tool_name,
                                tool_input=action.tool_args,
                                title=f"Tool: {action.tool_name}",
                                description="Starting tool execution"
                            )
                        )
                        try:
                            tool_result = None
                            tool_end_received = False  # Track if we received a tool_end event
                            async for item in self._execute_tool(action.tool_name, action.tool_args):
                                # Handle both dict items and AgentEvent objects
                                if isinstance(item, dict):
                                    # Legacy dict format
                                    if "progress" in item:
                                        yield self._create_event(
                                            AgentEventType.TOOL_PROGRESS,
                                            content=ProgressContent(
                                                progress=item["progress"],
                                                tool_name=action.tool_name,
                                                title="Tool Progress",
                                                description=f"Tool {action.tool_name} in progress"
                                            )
                                        )
                                    if "result" in item:
                                        tool_result = item["result"]
                                    if "error" in item:
                                        tool_result = item["error"]
                                        break
                                elif hasattr(item, 'event_type'):
                                    # AgentEvent object - forward directly
                                    yield item
                                    # Extract result from tool_end event for final observation
                                    if item.event_type == AgentEventType.TOOL_END:
                                        # Mark that we received a tool_end event
                                        tool_end_received = True
                                        # Extract from content or payload (backward compat)
                                        if item.content and hasattr(item.content, 'result'):
                                            tool_result = item.content.result
                                        elif item.payload:
                                            tool_result = item.payload.get("result")
                                    elif item.event_type == AgentEventType.ERROR:
                                        # Mark that we received an error event
                                        tool_end_received = True
                                        # Extract from content or payload (backward compat)
                                        if item.content and hasattr(item.content, 'error_message'):
                                            tool_result = item.content.error_message
                                        elif item.payload:
                                            tool_result = item.payload.get("error", "Unknown error")
                                        break

                            # Only create a new ToolCallContent if we didn't receive a tool_end event
                            # (for backward compatibility with tools that don't emit proper events)
                            if not tool_end_received:
                                if tool_result is None:
                                    tool_result = "Tool execution completed"
                                # Create ToolCallContent with result
                                tool_response = ToolCallContent(
                                    tool_name=action.tool_name,
                                    tool_input=action.tool_args,
                                    tool_status="completed",
                                    result=tool_result,
                                    title=f"Tool Result: {action.tool_name}",
                                    description="Tool execution completed successfully"
                                )
                                tool_response.complete()
                                yield self._create_event(AgentEventType.TOOL_END, content=tool_response)

                            # Check for pending TODO update and emit event
                            if self._pending_todo_update:
                                from agent.react.todo import TodoState
                                todo_state = TodoState.from_dict(self._pending_todo_update)
                                yield self._create_event(
                                    AgentEventType.TODO_WRITE,
                                    content=TodoWriteContent.from_todo_state(
                                        todo_state,
                                        title="Task Progress",
                                        description="Current task status"
                                    )
                                )
                                self._pending_todo_update = None

                            self.messages.append({"role": "assistant", "content": response_text})
                            self.messages.append({"role": "user", "content": f"Observation: {tool_result}"})
                        except Exception as exc:
                            logger.error(f"Tool execution error: {exc}", exc_info=True)
                            tool_error_response = ToolCallContent(
                                tool_name=action.tool_name,
                                tool_input=action.tool_args,
                                tool_status="failed",
                                error=str(exc),
                                title=f"Tool Error: {action.tool_name}",
                                description="Tool execution failed"
                            )
                            tool_error_response.fail()
                            yield self._create_event(AgentEventType.TOOL_END, content=tool_error_response)
                            self.messages.append({"role": "assistant", "content": response_text})
                            self.messages.append({"role": "user", "content": f"Error: {str(exc)}"})
                        continue

                    if action.is_final():
                        assert isinstance(action, FinalAction), f"Expected FinalAction, got {type(action)}"
                        self.status = ReactStatus.FINAL
                        self._update_checkpoint()
                        final_payload = action.to_final_payload()
                        yield self._create_event(
                            AgentEventType.FINAL,
                            content=TextContent(
                                text=final_payload.get("final_response", ""),
                                title="Final Response",
                                description=final_payload.get("summary", "ReAct process completed")
                            )
                        )
                        break

                # Check if we've reached max steps
                if self.status != ReactStatus.FINAL:
                    max_steps_action = ReactActionParser.create_final_action(
                        final="Reached maximum steps without completion",
                        stop_reason=ReactActionParser.get_max_steps_stop_reason()
                    )
                    self.status = ReactStatus.FINAL
                    self._update_checkpoint()
                    max_steps_payload = max_steps_action.to_final_payload()
                    yield self._create_event(
                        AgentEventType.FINAL,
                        content=TextContent(
                            text=max_steps_payload.get("final_response", ""),
                            title="Final Response",
                            description=max_steps_payload.get("summary", "ReAct process stopped")
                        )
                    )

                # Check if there are more messages to process (iterative, not recursive!)
                async with self._loop_lock:
                    if not self.pending_user_messages:
                        break
                    # Prepare for next iteration with new pending messages
                    pending_messages = self._drain_pending_messages()
                    self._start_new_run(pending_messages)
                    self._in_react_loop = True
                    self._maybe_update_checkpoint()

        except Exception as exc:
            logger.error(f"React loop error: {exc}", exc_info=True)
            self.status = ReactStatus.FAILED
            self._update_checkpoint()
            yield self._create_event(
                AgentEventType.ERROR,
                content=ErrorContent(
                    error_message=ReactActionParser.get_error_summary(exc),
                    error_type=type(exc).__name__,
                    details=repr(exc),
                    title="React Error",
                    description="ReAct loop encountered an error"
                )
            )
        finally:
            async with self._loop_lock:
                self._in_react_loop = False
                self._update_checkpoint()

    async def resume(self) -> AsyncGenerator[AgentEvent, None]:
        checkpoint = self.storage.load_checkpoint()
        if not checkpoint:
            yield self._create_event(
                AgentEventType.ERROR,
                content=ErrorContent(
                    error_message="No checkpoint found to resume from",
                    error_type="CheckpointError",
                    details="Cannot resume ReAct process without a saved checkpoint",
                    title="Resume Error",
                    description="No checkpoint available"
                )
            )
            return

        self.run_id = checkpoint.run_id
        self.step_id = checkpoint.step_id
        self.status = checkpoint.status
        self.messages = checkpoint.messages
        self.pending_user_messages = list(checkpoint.pending_user_messages)

        async for event in self.chat_stream(None):
            yield event

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        async with self._loop_lock:
            self._in_react_loop = False
        # Reset status to idle for clean state
        if self.status in {ReactStatus.RUNNING, ReactStatus.WAITING}:
            self.status = ReactStatus.IDLE
        return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics for this React instance."""
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "status": self.status,
            "total_llm_calls": self._total_llm_calls,
            "total_tool_calls": self._total_tool_calls,
            "llm_duration_ms": round(self._llm_duration_ms, 2),
            "tool_duration_ms": round(self._tool_duration_ms, 2),
            "pending_messages": len(self.pending_user_messages),
            "message_count": len(self.messages),
        }
