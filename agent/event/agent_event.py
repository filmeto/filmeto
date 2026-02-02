"""Event types for ReAct pattern."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Set, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agent.chat.content import StructureContent


class AgentEventType(str, Enum):
    """Constants for ReAct event types.

    Events represent different stages in the agent group chat process,
    including LLM thinking, crew member tasks, skill execution, and tool calls.
    """
    # === LLM相关 ===
    LLM_THINKING = "llm_thinking"       # LLM思考过程
    LLM_OUTPUT = "llm_output"           # LLM原始输出

    # === Crew成员相关 ===
    CREW_MEMBER_START = "crew_member_start"       # Crew成员开始处理任务
    CREW_MEMBER_THINKING = "crew_member_thinking" # Crew成员思考过程
    CREW_MEMBER_END = "crew_member_end"           # Crew成员完成处理

    # === Skill相关 ===
    SKILL_START = "skill_start"         # Skill开始执行
    SKILL_PROGRESS = "skill_progress"   # Skill执行进度
    SKILL_END = "skill_end"             # Skill执行完成
    SKILL_ERROR = "skill_error"         # Skill执行错误

    # === 工具相关 ===
    TOOL_START = "tool_start"           # 工具开始执行
    TOOL_PROGRESS = "tool_progress"     # 工具执行进度
    TOOL_END = "tool_end"               # 工具执行完成

    # === 计划相关 ===
    PLAN_CREATED = "plan_created"       # 计划创建完成
    PLAN_UPDATED = "plan_updated"       # 计划更新
    PLAN_STEP_START = "plan_step_start" # 计划步骤开始
    PLAN_STEP_END = "plan_step_end"     # 计划步骤完成
    PLAN_STEP_FAILED = "plan_step_failed" # 计划步骤失败

    # === 状态相关 ===
    STEP_START = "step_start"           # 当前步骤开始
    STEP_END = "step_end"               # 当前步骤结束
    STATUS_CHANGE = "status_change"     # 状态变更
    TODO_UPDATE = "todo_update"         # TODO更新

    # === 终止相关 ===
    FINAL = "final"                     # 最终响应
    ERROR = "error"                     # 错误
    INTERRUPTED = "interrupted"         # 用户中断
    TIMEOUT = "timeout"                 # 超时

    # === 控制相关 ===
    USER_MESSAGE = "user_message"       # 用户消息
    PAUSE = "pause"                     # 暂停
    RESUME = "resume"                   # 恢复

    @classmethod
    def is_tool_event(cls, event_type: str) -> bool:
        """Check if event type is tool-related."""
        return event_type in {
            cls.TOOL_START.value,
            cls.TOOL_PROGRESS.value,
            cls.TOOL_END.value
        }

    @classmethod
    def is_skill_event(cls, event_type: str) -> bool:
        """Check if event type is skill-related."""
        return event_type in {
            cls.SKILL_START.value,
            cls.SKILL_PROGRESS.value,
            cls.SKILL_END.value,
            cls.SKILL_ERROR.value
        }

    @classmethod
    def is_crew_member_event(cls, event_type: str) -> bool:
        """Check if event type is crew member-related."""
        return event_type in {
            cls.CREW_MEMBER_START.value,
            cls.CREW_MEMBER_THINKING.value,
            cls.CREW_MEMBER_END.value
        }

    @classmethod
    def is_plan_event(cls, event_type: str) -> bool:
        """Check if event type is plan-related."""
        return event_type in {
            cls.PLAN_CREATED.value,
            cls.PLAN_UPDATED.value,
            cls.PLAN_STEP_START.value,
            cls.PLAN_STEP_END.value,
            cls.PLAN_STEP_FAILED.value
        }

    @classmethod
    def is_terminal_event(cls, event_type: str) -> bool:
        """Check if event type indicates termination."""
        return event_type in {
            cls.FINAL.value,
            cls.ERROR.value,
            cls.INTERRUPTED.value,
            cls.TIMEOUT.value
        }

    @classmethod
    def get_valid_types(cls) -> Set[str]:
        """Get all valid event type values."""
        return {e.value for e in cls}


@dataclass
class AgentEvent:
    """
    Represents an event in the ReAct process.

    Attributes:
        event_type: Type of event (llm_thinking, tool_start, tool_progress, tool_end, llm_output, final, error)
        project_name: Name of the project
        react_type: Type of ReAct process
        run_id: Unique identifier for the current run
        step_id: Step number in the current run
        sender_id: ID of the event sender (e.g., crew member name, agent name)
        sender_name: Display name of the event sender
        content: Structured content for the event (StructureContent subclass) - REQUIRED
        payload: DEPRECATED - Use event.content instead. Will be removed in future version.

    Note:
        The `payload` field is deprecated and will be removed in a future version.
        Always use `content` with appropriate StructureContent subclass instead.
    """
    event_type: str
    project_name: str
    react_type: str
    run_id: str
    step_id: int
    sender_id: str = ""
    sender_name: str = ""
    content: Optional['StructureContent'] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate event fields and deprecate payload."""
        # Validate event_type
        valid_types = AgentEventType.get_valid_types()
        if self.event_type not in valid_types:
            raise ValueError(
                f"Invalid event_type: '{self.event_type}'. "
                f"Must be one of: {sorted(valid_types)}"
            )

        # Validate step_id
        if self.step_id < 0:
            raise ValueError(f"step_id must be >= 0, got {self.step_id}")

        # Deprecation warning for payload
        if self.payload:
            import warnings
            warnings.warn(
                "AgentEvent.payload is deprecated and will be removed in a future version. "
                "Use event.content with StructureContent subclass instead.",
                DeprecationWarning,
                stacklevel=2
            )

        # Validate content is provided for new code
        if not self.content and not self.payload:
            raise ValueError(
                f"Event {self.event_type} must have either content or payload. "
                f"content (StructureContent) is required."
            )

    @staticmethod
    def create(
        event_type: str,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int,
        sender_id: str = "",
        sender_name: str = "",
        content: Optional['StructureContent'] = None
    ) -> "AgentEvent":
        """
        Create an AgentEvent with the given parameters.

        Args:
            event_type: Type of event (from AgentEventType)
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender (e.g., crew member name, agent name)
            sender_name: Display name of the event sender
            content: Structured content for the event (StructureContent subclass)

        Returns:
            AgentEvent object

        Example:
            from agent.chat.content import ToolCallContent

            event = AgentEvent.create(
                AgentEventType.TOOL_START.value,
                project_name="my_project",
                react_type="crew",
                run_id="run_123",
                step_id=1,
                sender_id="script_writer",
                sender_name="Script Writer",
                content=ToolCallContent(
                    tool_name="my_tool",
                    tool_input={"arg": "value"}
                )
            )
        """
        return AgentEvent(
            event_type=event_type,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content
        )

    @staticmethod
    def error(
        error_message: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        content: Optional['StructureContent'] = None
    ) -> "AgentEvent":
        """
        Create an error event.

        Args:
            error_message: The error message
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            content: Structured content for the event (optional, will be created if not provided)

        Returns:
            AgentEvent with type ERROR
        """
        # Create ErrorContent if not provided
        if content is None:
            from agent.chat.content import ErrorContent
            content = ErrorContent(
                error_message=error_message,
                title="Error",
                description="An error occurred"
            )

        return AgentEvent.create(
            AgentEventType.ERROR.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content
        )

    @staticmethod
    def final(
        final_response: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        content: Optional['StructureContent'] = None
    ) -> "AgentEvent":
        """
        Create a final response event.

        Args:
            final_response: The final response content
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            content: Structured content for the event (optional, will be created if not provided)

        Returns:
            AgentEvent with type FINAL
        """
        # Create TextContent if not provided
        if content is None:
            from agent.chat.content import TextContent
            content = TextContent(
                text=final_response,
                title="Response",
                description="Final response from agent"
            )

        return AgentEvent.create(
            AgentEventType.FINAL.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content
        )

    @staticmethod
    def tool_start(
        tool_name: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        content: Optional['StructureContent'] = None
    ) -> "AgentEvent":
        """
        Create a tool start event.

        Args:
            tool_name: Name of the tool being started
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            content: Structured content for the event (optional, will be created if not provided)

        Returns:
            AgentEvent with type TOOL_START
        """
        # Create ToolCallContent if not provided
        if content is None:
            from agent.chat.content import ToolCallContent
            content = ToolCallContent(
                tool_name=tool_name,
                tool_input={},
                title=f"Tool: {tool_name}",
                description="Tool execution started"
            )

        return AgentEvent.create(
            AgentEventType.TOOL_START.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content
        )

    @staticmethod
    def tool_progress(
        tool_name: str,
        progress: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        content: Optional['StructureContent'] = None
    ) -> "AgentEvent":
        """
        Create a tool progress event.

        Args:
            tool_name: Name of the tool
            progress: Progress message
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            content: Structured content for the event (optional, will be created if not provided)

        Returns:
            AgentEvent with type TOOL_PROGRESS
        """
        # Create ProgressContent if not provided
        if content is None:
            from agent.chat.content import ProgressContent
            content = ProgressContent(
                progress=progress,
                tool_name=tool_name,
                title="Tool Execution",
                description="Tool execution in progress"
            )

        return AgentEvent.create(
            AgentEventType.TOOL_PROGRESS.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content
        )

    @staticmethod
    def tool_end(
        tool_name: str,
        result: Any = None,
        ok: bool = True,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        content: Optional['StructureContent'] = None
    ) -> "AgentEvent":
        """
        Create a tool end event.

        Args:
            tool_name: Name of the tool
            result: Tool execution result
            ok: Whether execution succeeded
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            content: Structured content for the event (optional, will be created if not provided)

        Returns:
            AgentEvent with type TOOL_END
        """
        # Create ToolResponseContent if not provided
        if content is None:
            from agent.chat.content import ToolResponseContent
            content = ToolResponseContent(
                tool_name=tool_name,
                result=result,
                error=None if ok else "Execution failed",
                tool_status="completed" if ok else "failed",
                title=f"Tool Result: {tool_name}",
                description=f"Tool execution {'completed' if ok else 'failed'}"
            )
            if ok:
                content.complete()
            else:
                content.fail()

        return AgentEvent.create(
            AgentEventType.TOOL_END.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content
        )
