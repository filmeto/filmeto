"""StoryBoard tool for storyboard shot CRUD and keyframe generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator, List
import logging
import re

from ...base_tool import BaseTool

_tool_dir = Path(__file__).parent
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent
    from app.data.story_board import StoryBoardManager
    from app.data.screen_play import ScreenPlayManager


class StoryBoardTool(BaseTool):
    """Manage storyboard shots and generate shot keyframes."""

    def __init__(self):
        super().__init__(
            name="story_board",
            description="Manage storyboard shots with CRUD plus text2image/image2image keyframe generation",
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
            operation = str(parameters.get("operation", "")).strip().lower()
            if not operation:
                yield self._create_event(
                    "error", project_name, react_type, step_id, error="operation parameter is required"
                )
                return

            managers = self._get_managers(context)
            if managers is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    step_id,
                    error="Could not access storyboard/screenplay manager from context.",
                )
                return
            sbm, spm = managers

            if operation == "create":
                async for e in self._handle_create(sbm, spm, parameters, project_name, react_type, step_id):
                    yield e
            elif operation == "get":
                async for e in self._handle_get(sbm, parameters, project_name, react_type, step_id):
                    yield e
            elif operation == "update":
                async for e in self._handle_update(sbm, parameters, project_name, react_type, step_id):
                    yield e
            elif operation == "delete":
                async for e in self._handle_delete(sbm, parameters, project_name, react_type, step_id):
                    yield e
            elif operation == "delete_batch":
                async for e in self._handle_delete_batch(sbm, parameters, project_name, react_type, step_id):
                    yield e
            elif operation == "delete_all":
                async for e in self._handle_delete_all(sbm, parameters, project_name, react_type, step_id):
                    yield e
            elif operation == "list":
                async for e in self._handle_list(sbm, parameters, project_name, react_type, step_id):
                    yield e
            elif operation in ("text2image", "image2image"):
                async for e in self._handle_generate(
                    sbm, parameters, operation, project_name, react_type, step_id
                ):
                    yield e
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    step_id,
                    error=(
                        f"Unknown operation: {operation}. Valid operations: "
                        "create, get, update, delete, delete_batch, delete_all, list, text2image, image2image"
                    ),
                )
        except Exception as e:
            logger.error("Error in story_board tool: %s", e, exc_info=True)
            yield self._create_event("error", project_name, react_type, step_id, error=str(e))

    def _get_managers(
        self, context: Optional["ToolContext"]
    ) -> Optional[tuple["StoryBoardManager", "ScreenPlayManager"]]:
        if context is None or context.project is None:
            return None
        project = context.project
        sbm = getattr(project, "story_board_manager", None)
        spm = getattr(project, "screenplay_manager", None)
        if sbm is None or spm is None:
            return None
        return sbm, spm

    def _build_scene_scoped_shot_id(self, scene_id: str, existing: List[str]) -> str:
        nums: List[int] = []
        for sid in existing:
            m = re.search(r"(\d+)$", sid or "")
            if m:
                nums.append(int(m.group(1)))
        next_no = (max(nums) + 1) if nums else 1
        return f"{scene_id}_shot_{next_no:03d}"

    async def _handle_create(
        self,
        manager: "StoryBoardManager",
        _spm: "ScreenPlayManager",
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        if not scene_id:
            yield self._create_event("error", project_name, react_type, step_id, error="scene_id is required")
            return
        shot_id = str(parameters.get("shot_id", "")).strip()
        if not shot_id:
            shot_id = self._build_scene_scoped_shot_id(scene_id, manager.list_shot_ids(scene_id))

        description = str(parameters.get("description", "")).strip()
        keyframe_context = parameters.get("keyframe_context", {}) or {}
        if not isinstance(keyframe_context, dict):
            yield self._create_event(
                "error", project_name, react_type, step_id, error="keyframe_context must be an object"
            )
            return
        metadata = {
            "description": description,
            "keyframe_context": keyframe_context,
        }
        ok = manager.create_shot(scene_id=scene_id, shot_id=shot_id, content=description, metadata=metadata)
        if not ok:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                step_id,
                error=f"Failed to create shot '{shot_id}' in scene '{scene_id}'",
            )
            return

        shot = manager.get_shot(scene_id, shot_id)
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={
                "operation": "create",
                "success": True,
                "scene_id": scene_id,
                "shot_id": shot_id,
                "shot_no": shot.shot_no if shot else "",
                "message": f"Created storyboard shot '{shot_id}' in scene '{scene_id}'",
            },
        )

    async def _handle_get(
        self,
        manager: "StoryBoardManager",
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        shot_id = str(parameters.get("shot_id", "")).strip()
        if not scene_id or not shot_id:
            yield self._create_event(
                "error", project_name, react_type, step_id, error="scene_id and shot_id are required"
            )
            return
        shot = manager.get_shot(scene_id, shot_id)
        if not shot:
            yield self._create_event(
                "error", project_name, react_type, step_id, error=f"Shot '{scene_id}/{shot_id}' not found"
            )
            return
        km = manager.key_moment_path(scene_id, shot_id)
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={
                "operation": "get",
                "success": True,
                "shot": {
                    "scene_id": shot.scene_id,
                    "shot_id": shot.shot_id,
                    "shot_no": shot.shot_no,
                    "description": shot.description,
                    "keyframe_path": str(km) if km else "",
                    "keyframe_context": shot.keyframe_context,
                },
            },
        )

    async def _handle_update(
        self,
        manager: "StoryBoardManager",
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        shot_id = str(parameters.get("shot_id", "")).strip()
        if not scene_id or not shot_id:
            yield self._create_event(
                "error", project_name, react_type, step_id, error="scene_id and shot_id are required"
            )
            return

        updates: Dict[str, Any] = {}
        if "description" in parameters:
            updates["description"] = str(parameters.get("description", "") or "")
        if "keyframe_context" in parameters:
            ctx = parameters.get("keyframe_context")
            if ctx is not None and not isinstance(ctx, dict):
                yield self._create_event(
                    "error", project_name, react_type, step_id, error="keyframe_context must be an object"
                )
                return
            updates["keyframe_context"] = ctx or {}
        if "key_moment_relpath" in parameters:
            updates["key_moment_relpath"] = str(parameters.get("key_moment_relpath", "") or "")

        if not updates:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                step_id,
                error="At least one updatable field is required: description, keyframe_context, key_moment_relpath",
            )
            return

        ok = manager.update_shot(scene_id, shot_id, updates, content=updates.get("description"))
        if not ok:
            yield self._create_event(
                "error", project_name, react_type, step_id, error=f"Failed to update shot '{scene_id}/{shot_id}'"
            )
            return
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={
                "operation": "update",
                "success": True,
                "scene_id": scene_id,
                "shot_id": shot_id,
                "updated_fields": list(updates.keys()),
            },
        )

    async def _handle_delete(
        self,
        manager: "StoryBoardManager",
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        shot_id = str(parameters.get("shot_id", "")).strip()
        if not scene_id or not shot_id:
            yield self._create_event(
                "error", project_name, react_type, step_id, error="scene_id and shot_id are required"
            )
            return
        ok = manager.delete_shot(scene_id, shot_id)
        if not ok:
            yield self._create_event(
                "error", project_name, react_type, step_id, error=f"Failed to delete shot '{scene_id}/{shot_id}'"
            )
            return
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={"operation": "delete", "success": True, "scene_id": scene_id, "shot_id": shot_id},
        )

    async def _handle_delete_batch(
        self,
        manager: "StoryBoardManager",
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        shot_ids = parameters.get("shot_ids") or []
        if not scene_id or not isinstance(shot_ids, list) or not shot_ids:
            yield self._create_event(
                "error", project_name, react_type, step_id, error="scene_id and non-empty shot_ids are required"
            )
            return
        deleted: List[str] = []
        failed: List[str] = []
        for sid in shot_ids:
            sid_text = str(sid).strip()
            if sid_text and manager.delete_shot(scene_id, sid_text):
                deleted.append(sid_text)
            else:
                failed.append(sid_text)
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={
                "operation": "delete_batch",
                "success": True,
                "scene_id": scene_id,
                "deleted_shot_ids": deleted,
                "failed_shot_ids": failed,
            },
        )

    async def _handle_delete_all(
        self,
        manager: "StoryBoardManager",
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        if not scene_id:
            yield self._create_event("error", project_name, react_type, step_id, error="scene_id is required")
            return
        shot_ids = list(manager.list_shot_ids(scene_id))
        deleted = 0
        for sid in shot_ids:
            if manager.delete_shot(scene_id, sid):
                deleted += 1
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={
                "operation": "delete_all",
                "success": True,
                "scene_id": scene_id,
                "deleted_count": deleted,
            },
        )

    async def _handle_list(
        self,
        manager: "StoryBoardManager",
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        if not scene_id:
            yield self._create_event("error", project_name, react_type, step_id, error="scene_id is required")
            return
        shots = manager.list_shots(scene_id)
        out = []
        for sh in shots:
            km = manager.key_moment_path(scene_id, sh.shot_id)
            out.append(
                {
                    "scene_id": sh.scene_id,
                    "shot_id": sh.shot_id,
                    "shot_no": sh.shot_no,
                    "description": sh.description,
                    "keyframe_path": str(km) if km else "",
                    "keyframe_context": sh.keyframe_context,
                }
            )
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={
                "operation": "list",
                "success": True,
                "scene_id": scene_id,
                "total_shots": len(out),
                "shots": out,
            },
        )

    async def _handle_generate(
        self,
        manager: "StoryBoardManager",
        parameters: Dict[str, Any],
        operation: str,
        project_name: str,
        react_type: str,
        step_id: int,
    ) -> AsyncGenerator["AgentEvent", None]:
        scene_id = str(parameters.get("scene_id", "")).strip()
        shot_id = str(parameters.get("shot_id", "")).strip()
        prompt = str(parameters.get("prompt", "")).strip()
        if not scene_id or not shot_id or not prompt:
            yield self._create_event(
                "error", project_name, react_type, step_id, error="scene_id, shot_id, and prompt are required"
            )
            return
        shot = manager.get_shot(scene_id, shot_id)
        if not shot:
            yield self._create_event(
                "error", project_name, react_type, step_id, error=f"Shot '{scene_id}/{shot_id}' not found"
            )
            return

        from server.api import FilmetoApi, FilmetoTask, Ability, ResourceInput, ResourceType
        from server.api.types import SelectionConfig

        width = int(parameters.get("width", 1024) or 1024)
        height = int(parameters.get("height", 1024) or 1024)
        model = str(parameters.get("model", "") or "").strip()
        server = str(parameters.get("server_name", "") or "").strip()
        refs = parameters.get("reference_images") or []
        if not isinstance(refs, list):
            refs = []

        if server and model:
            selection = SelectionConfig.exact(server=server, model=model)
        elif server:
            selection = SelectionConfig.server_only(server=server, model=model or None)
        else:
            selection = SelectionConfig.auto()

        resources = []
        if operation == "image2image":
            input_image_path = str(parameters.get("input_image_path", "") or "").strip()
            if not input_image_path:
                existing = manager.key_moment_path(scene_id, shot_id)
                if existing is not None:
                    input_image_path = str(existing)
            if not input_image_path:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    step_id,
                    error="image2image requires input_image_path (or existing keyframe for this shot)",
                )
                return
            resources.append(
                ResourceInput(type=ResourceType.LOCAL_PATH, data=input_image_path, mime_type="image/png")
            )
            parameters_payload = {
                "prompt": prompt,
                "input_image_path": input_image_path,
                "width": width,
                "height": height,
                "n": 1,
            }
            ability = Ability.IMAGE2IMAGE
        else:
            for ref in refs:
                ref_text = str(ref or "").strip()
                if ref_text:
                    resources.append(
                        ResourceInput(type=ResourceType.LOCAL_PATH, data=ref_text, mime_type="image/png")
                    )
            parameters_payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "n": 1,
            }
            ability = Ability.TEXT2IMAGE

        shot_dir = manager.shot_dir(scene_id, shot_id)
        shot_dir.mkdir(parents=True, exist_ok=True)
        parameters_payload["save_dir"] = str(shot_dir)

        yield self._create_event(
            "tool_progress",
            project_name,
            react_type,
            step_id,
            progress=f"Generating keyframe with {operation} for {scene_id}/{shot_id}",
        )

        api = FilmetoApi()
        filmeto_task = FilmetoTask(ability=ability, selection=selection, parameters=parameters_payload, resources=resources)
        final_result = None
        async for update in api.execute_task_stream(filmeto_task):
            final_result = update

        image_path = final_result.get_image_path() if final_result else None
        if not image_path:
            yield self._create_event(
                "error", project_name, react_type, step_id, error=f"{operation} finished without image output"
            )
            return

        saved = manager.set_key_moment_image(scene_id=scene_id, shot_id=shot_id, image_path=image_path)
        if not saved:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                step_id,
                error=f"Generated image but failed to save keyframe for shot '{scene_id}/{shot_id}'",
            )
            return

        context_patch = {
            "prompt": prompt,
            "ability_model": model,
            "model": model,
            "reference_images": refs,
            "tool": operation,
        }
        manager.update_shot(scene_id, shot_id, {"keyframe_context": context_patch})

        yield self._create_event(
            "tool_end",
            project_name,
            react_type,
            step_id,
            ok=True,
            result={
                "operation": operation,
                "success": True,
                "scene_id": scene_id,
                "shot_id": shot_id,
                "image_path": str(manager.key_moment_path(scene_id, shot_id) or ""),
            },
        )
