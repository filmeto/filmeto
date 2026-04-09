"""TimelineItem tool for creating/editing timeline items and submitting generation tasks."""
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator, Tuple
import logging

from ...base_tool import BaseTool

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from app.data.timeline import Timeline
    from app.data.workspace import Workspace
    from server.api.types import Ability as AbilityEnum

logger = logging.getLogger(__name__)
_tool_dir = Path(__file__).parent


class TimelineItemTool(BaseTool):
    """Create/edit timeline items and submit image/video/audio generation tasks."""

    _ABILITY_ALIASES = {
        "image": "text2image",
        "video": "text2video",
        "audio": "text2music",
        "speech": "text2speak",
        "music": "text2music",
        "text2image": "text2image",
        "image2image": "image2image",
        "imageedit": "imageedit",
        "image2video": "image2video",
        "text2video": "text2video",
        "text2speak": "text2speak",
        "text2music": "text2music",
        "speak2video": "speak2video",
    }

    def __init__(self):
        super().__init__(
            name="timeline_item",
            description="Create or edit timeline item, select it, and optionally submit generation tasks",
        )
        self._tool_dir = _tool_dir

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional["ToolContext"] = None,
        project_name: str = "",
        react_type: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        message_id: str = "",
    ) -> AsyncGenerator["AgentEvent", None]:
        try:
            operation = str(parameters.get("operation", "upsert")).strip().lower()
            if operation not in ("upsert", "create", "edit"):
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    step_id,
                    error=f"Unknown operation: {operation}. Valid operations: upsert, create, edit",
                )
                return

            workspace = self._get_workspace(context)
            timeline = self._get_timeline(context)
            if workspace is None or timeline is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    step_id,
                    error="Could not access workspace/timeline from context.",
                )
                return

            index = self._resolve_target_index(timeline, operation, parameters)
            if index is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    step_id,
                    error="index is required for edit, and must be a valid positive integer.",
                )
                return

            if index < 1:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    step_id,
                    error="index must be >= 1",
                )
                return

            created = False
            item_count = timeline.get_item_count()
            if index > item_count:
                if operation == "edit":
                    yield self._create_event(
                        "error",
                        project_name,
                        react_type,
                        step_id,
                        error=f"Cannot edit index {index}. Valid range is 1-{item_count}.",
                    )
                    return
                # upsert/create: append until target index exists
                while timeline.get_item_count() < index:
                    timeline.add_item()
                    created = True
            elif operation == "create":
                # create always makes a new one; ignore provided index when exists
                index = timeline.add_item()
                created = True

            timeline.set_item_index(index)
            item = timeline.get_item(index)

            ability_raw = parameters.get("ability")
            ability_tool = self._normalize_ability(ability_raw)
            prompt = parameters.get("prompt")
            if prompt is not None:
                item.set_prompt(str(prompt), ability_tool)

            if ability_tool:
                item.set_config_value("current_tool", ability_tool)

            # Trigger thumbnail refresh path used by timeline cards.
            timeline.timeline_changed.send(timeline, item)

            yield self._create_event(
                "tool_progress",
                project_name,
                react_type,
                step_id,
                progress=f"Selected timeline item #{index} and synchronized editor state",
            )

            submit_task = bool(parameters.get("submit_task", False))
            task_params: Optional[Dict[str, Any]] = None
            if submit_task:
                if not ability_tool:
                    yield self._create_event(
                        "error",
                        project_name,
                        react_type,
                        step_id,
                        error="ability is required when submit_task=true",
                    )
                    return

                task_params = self._build_task_params(item, ability_tool, prompt)
                if not task_params:
                    yield self._create_event(
                        "error",
                        project_name,
                        react_type,
                        step_id,
                        error=f"Unsupported ability for task submission: {ability_tool}",
                    )
                    return

                self._apply_selection_overrides(task_params, parameters)

                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    step_id,
                    progress=f"Submitting {ability_tool} task for timeline item #{index}",
                )
                workspace.submit_task(task_params, timeline_item_id=index)

            result = {
                "operation": operation,
                "success": True,
                "created": created,
                "index": index,
                "total_items": timeline.get_item_count(),
                "selected": timeline.project.get_timeline_index() == index,
                "ability": ability_tool,
                "prompt_set": prompt is not None,
                "task_submitted": submit_task,
                "task_params": task_params if submit_task else None,
            }
            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                step_id,
                ok=True,
                result=result,
            )
        except Exception as e:
            logger.error("Error in timeline_item tool: %s", e, exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                step_id,
                error=str(e),
            )

    def _get_workspace(self, context: Optional["ToolContext"]) -> Optional["Workspace"]:
        if context is None:
            return None
        return getattr(context, "workspace", None)

    def _get_timeline(self, context: Optional["ToolContext"]) -> Optional["Timeline"]:
        if context is None or context.project is None:
            return None
        return context.project.get_timeline()

    def _resolve_target_index(
        self, timeline: "Timeline", operation: str, parameters: Dict[str, Any]
    ) -> Optional[int]:
        idx = parameters.get("index")
        if idx is None:
            if operation in ("upsert", "create"):
                return timeline.get_item_count() + 1
            return None
        return int(idx)

    def _normalize_ability(self, ability_raw: Any) -> Optional[str]:
        if ability_raw is None:
            return None
        val = str(ability_raw).strip().lower()
        return self._ABILITY_ALIASES.get(val, val or None)

    def _build_task_params(
        self, item: Any, ability_tool: str, prompt: Optional[Any]
    ) -> Optional[Dict[str, Any]]:
        text_prompt = str(prompt or "")
        layer_manager = item.get_layer_manager()
        width, height = layer_manager.get_valid_dimensions()

        if ability_tool in ("text2image", "image2image", "imageedit"):
            return {
                "tool": ability_tool,
                "prompt": text_prompt,
                "width": width,
                "height": height,
            }
        if ability_tool in ("text2video", "image2video", "speak2video"):
            return {
                "tool": ability_tool,
                "prompt": text_prompt,
                "width": width,
                "height": height,
                "duration": 5,
            }
        if ability_tool == "text2music":
            return {
                "tool": ability_tool,
                "prompt": text_prompt,
            }
        if ability_tool == "text2speak":
            return {
                "tool": ability_tool,
                "text": text_prompt,
            }
        return None

    def _apply_selection_overrides(self, task_params: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        mode = parameters.get("selection_mode")
        server = parameters.get("server_name")
        model = parameters.get("model_name")
        tags = parameters.get("selection_tags")
        min_priority = parameters.get("min_priority")

        if mode:
            task_params["selection_mode"] = str(mode)
        if server:
            task_params["server_name"] = str(server)
        if model:
            task_params["model"] = str(model)
        if isinstance(tags, list):
            task_params["selection_tags"] = tags
        if min_priority is not None:
            task_params["min_priority"] = min_priority
