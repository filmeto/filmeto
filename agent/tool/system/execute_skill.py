from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
from ..base_tool import BaseTool, ToolMetadata, ToolParameter

if TYPE_CHECKING:
    from ...tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class ExecuteSkillTool(BaseTool):
    """
    Tool to execute a skill through SkillService's chat_stream method.
    This is a bridge tool that allows React to execute skills using ReAct.
    """

    def __init__(self):
        super().__init__(
            name="execute_skill",
            description="Execute a skill through ReAct-based chat stream"
        )

    def metadata(self, lang: str = "en_US") -> ToolMetadata:
        """Get metadata for the execute_skill tool."""
        if lang == "zh_CN":
            return ToolMetadata(
                name=self.name,
                description="通过 ReAct 执行一个 skill",
                parameters=[
                    ToolParameter(
                        name="skill_name",
                        description="skill 名称",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="message",
                        description="用户消息/问题",
                        param_type="string",
                        required=False
                    ),
                    ToolParameter(
                        name="max_steps",
                        description="最大执行步数",
                        param_type="integer",
                        required=False,
                        default=10
                    ),
                ],
                return_description="返回 skill 的执行结果（流式输出）"
            )
        else:
            return ToolMetadata(
                name=self.name,
                description="Execute a skill through ReAct-based chat stream",
                parameters=[
                    ToolParameter(
                        name="skill_name",
                        description="Name of the skill to execute",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="message",
                        description="User message/question for the skill",
                        param_type="string",
                        required=False
                    ),
                    ToolParameter(
                        name="max_steps",
                        description="Maximum number of execution steps",
                        param_type="integer",
                        required=False,
                        default=10
                    ),
                ],
                return_description="Returns the execution result from the skill (streamed)"
            )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional["ToolContext"] = None,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Execute a skill using SkillService.chat_stream().

        This method uses SkillService's ReAct-based chat stream to execute skills,
        which allows the skill to use tools and have multi-step reasoning.

        Args:
            parameters: Parameters including skill_name, message, and max_steps
            context: ToolContext containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender

        Yields:
            ReactEvent objects with progress updates and results
        """
        workspace = context.workspace if context else None

        if not workspace:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error="Workspace not available in context"
            )
            return

        from agent.skill.skill_service import SkillService
        from agent.event.agent_event import AgentEventType

        skill_service = SkillService(workspace)

        skill_name = parameters.get("skill_name")
        message = parameters.get("message")
        max_steps = parameters.get("max_steps", 10)

        if not skill_name:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error="skill_name is required"
            )
            return

        skill = skill_service.get_skill(skill_name)
        if not skill:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error=f"Skill '{skill_name}' not found"
            )
            return

        try:
            # Use SkillService.chat_stream to execute the skill
            # Forward events from skill_chat directly, preserving event types
            final_response = None
            async for event in skill_service.chat_stream(
                skill=skill,
                user_message=message,
                workspace=workspace,
                project=context.project_name if context else None,
                llm_service=None,  # Will use default LLM service
                max_steps=max_steps,
            ):
                # Forward the event directly, preserving original event type and content
                # The sender_id/sender_name will be added by CrewMember upstream
                if event.event_type == AgentEventType.FINAL:
                    # Extract final_response from content or payload (backward compat)
                    if event.content and hasattr(event.content, 'text'):
                        final_response = event.content.text
                    elif event.payload:
                        final_response = event.payload.get("final_response")
                    # Convert FINAL to tool_end for tool completion
                    yield self._create_event(
                        "tool_end",
                        project_name,
                        react_type,
                        run_id,
                        step_id,
                        sender_id,
                        sender_name,
                        ok=True,
                        result=final_response
                    )
                    return
                elif event.event_type == AgentEventType.ERROR:
                    # Extract error from content or payload (backward compat)
                    if event.content and hasattr(event.content, 'error_message'):
                        error = event.content.error_message
                    elif event.payload:
                        error = event.payload.get("error", "Unknown error")
                    else:
                        error = "Unknown error"
                    # Convert ERROR to tool error event
                    yield self._create_event(
                        "error",
                        project_name,
                        react_type,
                        run_id,
                        step_id,
                        sender_id,
                        sender_name,
                        error=error
                    )
                    return
                else:
                    # Forward all other events directly (LLM_THINKING, TOOL_START, TOOL_PROGRESS, TOOL_END, etc.)
                    # Create new event with updated sender info, preserving content
                    yield AgentEvent.create(
                        event_type=event.event_type,
                        project_name=event.project_name or project_name,
                        react_type=event.react_type or react_type,
                        run_id=event.run_id or run_id,
                        step_id=event.step_id or step_id,
                        sender_id=sender_id,
                        sender_name=sender_name,
                        content=event.content
                    )

            # If we get here without a FINAL event, return whatever we collected
            if final_response:
                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    sender_id,
                    sender_name,
                    ok=True,
                    result=final_response
                )
            else:
                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    sender_id,
                    sender_name,
                    ok=True,
                    result="Skill execution completed"
                )

        except Exception as e:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error=f"Error executing skill: {str(e)}"
            )
