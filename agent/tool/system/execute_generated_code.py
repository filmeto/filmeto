from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging
from ..base_tool import BaseTool, ToolMetadata, ToolParameter

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ...tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class ExecuteGeneratedCodeTool(BaseTool):
    """
    Tool to execute dynamically generated Python code.
    """

    def __init__(self):
        super().__init__(
            name="execute_generated_code",
            description="Execute dynamically generated Python code"
        )

    def metadata(self, lang: str = "en_US") -> ToolMetadata:
        """Get metadata for the execute_generated_code tool."""
        if lang == "zh_CN":
            return ToolMetadata(
                name=self.name,
                description="执行动态生成的 Python 代码",
                parameters=[
                    ToolParameter(
                        name="code",
                        description="要执行的 Python 代码",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="args",
                        description="传递给代码的参数",
                        param_type="object",
                        required=False,
                        default={}
                    ),
                ],
                return_description="返回代码的执行结果（流式输出）"
            )
        else:
            return ToolMetadata(
                name=self.name,
                description="Execute dynamically generated Python code",
                parameters=[
                    ToolParameter(
                        name="code",
                        description="Python code to execute",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="args",
                        description="Arguments to pass to the code",
                        param_type="object",
                        required=False,
                        default={}
                    ),
                ],
                return_description="Returns the execution result from the generated code (streamed)"
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
        Execute dynamically generated Python code using ToolService.execute_script_content.

        Args:
            parameters: Parameters including code and args
            context: ToolContext containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            step_id: Step ID for event tracking

        Yields:
            ReactEvent objects with progress updates and results
        """
        from ..tool_service import ToolService

        code = parameters.get("code")
        args = parameters.get("args", {})

        if not code:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error="code is required"
            )
            return

        tool_service = ToolService()

        # Build argv from args
        argv = []
        for key, value in args.items():
            argv.extend([f"--{key}", str(value)])

        try:
            # Yield progress before execution
            yield self._create_event(
                "tool_progress",
                project_name,
                react_type,
                run_id,
                step_id,
                progress="Executing generated code..."
            )

            # execute_script_content now returns the result directly
            result = await tool_service.execute_script_content(
                code,
                argv,
                context,
                project_name=project_name,
                react_type=react_type,
                run_id=run_id,
                step_id=step_id,
            )

            # Yield the final result
            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result=result
            )

        except Exception as e:
            logger.error(f"Error executing generated code: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
