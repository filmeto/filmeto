import os
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
from ..base_tool import BaseTool, ToolMetadata, ToolParameter

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ...tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class ExecuteSkillScriptTool(BaseTool):
    """
    Tool to execute a pre-defined script from a skill.
    """

    def __init__(self):
        super().__init__(
            name="execute_skill_script",
            description="Execute a pre-defined script from a skill"
        )

    def metadata(self, lang: str = "en_US") -> ToolMetadata:
        """Get metadata for the execute_skill_script tool."""
        if lang == "zh_CN":
            return ToolMetadata(
                name=self.name,
                description="执行 skill 中预定义的脚本",
                parameters=[
                    ToolParameter(
                        name="skill_path",
                        description="skill 目录路径",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="script_name",
                        description="要执行的脚本名称",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="args",
                        description="传递给脚本的参数",
                        param_type="object",
                        required=False,
                        default={}
                    ),
                ],
                return_description="返回脚本的执行结果（流式输出）"
            )
        else:
            return ToolMetadata(
                name=self.name,
                description="Execute a pre-defined script from a skill",
                parameters=[
                    ToolParameter(
                        name="skill_path",
                        description="Path to the skill directory",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="script_name",
                        description="Name of the script to execute",
                        param_type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="args",
                        description="Arguments to pass to the script",
                        param_type="object",
                        required=False,
                        default={}
                    ),
                ],
                return_description="Returns the execution result from the script (streamed)"
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
        Execute a skill script using ToolService.execute_script.

        Args:
            parameters: Parameters including skill_path, script_name, and args
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

        skill_path = parameters.get("skill_path")
        script_name = parameters.get("script_name")
        args = parameters.get("args", {})

        if not skill_path or not script_name:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error="skill_path and script_name are required"
            )
            return

        tool_service = ToolService()

        # Find the script path
        full_script_path = os.path.join(skill_path, script_name)
        if not os.path.exists(full_script_path):
            # Try to find in scripts directory
            scripts_dir = os.path.join(skill_path, "scripts")
            full_script_path = os.path.join(scripts_dir, script_name)

        if not os.path.exists(full_script_path):
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=f"Script not found at {full_script_path}"
            )
            return

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
                progress=f"Executing script: {script_name}"
            )

            # execute_script now returns the result directly
            result = await tool_service.execute_script(
                full_script_path,
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
            logger.error(f"Error executing skill script '{parameters.get('script_path', 'unknown')}': {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
