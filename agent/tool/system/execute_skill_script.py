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
                description="执行 skill 中预定义的脚本。可以直接指定完整脚本路径，或使用 skill_path + script_name 的组合。",
                parameters=[
                    ToolParameter(
                        name="script_path",
                        description="脚本的完整路径（优先使用此参数）",
                        param_type="string",
                        required=False
                    ),
                    ToolParameter(
                        name="skill_path",
                        description="skill 目录路径（当 script_path 未提供时使用）",
                        param_type="string",
                        required=False
                    ),
                    ToolParameter(
                        name="script_name",
                        description="要执行的脚本名称（当 script_path 未提供时使用）",
                        param_type="string",
                        required=False
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
                description="Execute a pre-defined script from a skill. Can specify full script path directly, or use skill_path + script_name combination.",
                parameters=[
                    ToolParameter(
                        name="script_path",
                        description="Full path to the script (takes priority over skill_path + script_name)",
                        param_type="string",
                        required=False
                    ),
                    ToolParameter(
                        name="skill_path",
                        description="Path to the skill directory (used when script_path is not provided)",
                        param_type="string",
                        required=False
                    ),
                    ToolParameter(
                        name="script_name",
                        description="Name of the script to execute (used when script_path is not provided)",
                        param_type="string",
                        required=False
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

        script_path = parameters.get("script_path")
        skill_path = parameters.get("skill_path")
        script_name = parameters.get("script_name")
        args = parameters.get("args", {})

        tool_service = ToolService()

        # Determine the full script path
        # Priority 1: Use script_path directly if provided
        if script_path:
            full_script_path = script_path
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
        # Priority 2: Use skill_path + script_name combination
        elif skill_path and script_name:
            # Try direct join first
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
        else:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error="Either script_path, or both skill_path and script_name must be provided"
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
