#!/usr/bin/env python3
"""
Rewrite Screenplay Skill Script

Rewrites screenplay scenes according to user instructions. Uses context's
screenplay manager and LLM service to read, rewrite with instruction compliance,
and write back scene content.
"""
import json
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent.tool.tool_context import ToolContext

REWRITE_SYSTEM = """You are a professional screenwriter. Your task is to rewrite screenplay content according to the user's instruction.

Rules:
- Output ONLY the rewritten screenplay content. No explanations, no meta-commentary, no "Here is the rewritten scene".
- Preserve Hollywood screenplay format: scene headings (e.g. INT. LOCATION - TIME), action lines, character names in caps for dialogue, parentheticals where needed.
- Strictly follow the user's instruction: every requested change must appear in the output.
- Keep the same language as the original unless the instruction asks to change it.
- Do not add scenes or remove scenes; only rewrite the given content.
- If the instruction is ambiguous, apply the most natural interpretation that fits the existing story."""


def _rewrite_content_with_llm(
    llm_service: Any,
    instruction: str,
    scene_id: str,
    current_content: str,
    current_title: str,
) -> Optional[str]:
    """Call LLM to rewrite scene content per instruction. Returns new content or None on failure."""
    user_content = (
        f"Rewrite the following screenplay scene according to this instruction.\n\n"
        f"**Instruction:** {instruction}\n\n"
        f"**Scene id:** {scene_id}\n"
        f"**Scene title:** {current_title}\n\n"
        f"**Current content:**\n{current_content}\n\n"
        f"Output only the rewritten screenplay content, nothing else."
    )
    messages = [
        {"role": "system", "content": REWRITE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    try:
        response = llm_service.completion(messages=messages, temperature=0.3)
        from agent.llm.llm_service import LlmService
        text = LlmService.extract_content(response)
        if not text or not text.strip():
            return None
        return text.strip()
    except Exception as e:
        logger.error(f"LLM rewrite failed for {scene_id}: {e}", exc_info=True)
        return None


def rewrite_screenplay_in_context(
    screenplay_manager: Any,
    llm_service: Any,
    instruction: str,
    scene_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Rewrite one or more scenes according to instruction using the given manager and LLM.

    Args:
        screenplay_manager: ScreenPlayManager instance
        llm_service: LLM service for completion
        instruction: User's rewrite directive
        scene_ids: List of scene_id to rewrite; if None, rewrite all scenes

    Returns:
        Result dict with success, updated_scenes, message, and optional error.
    """
    if not instruction or not instruction.strip():
        return {
            "success": False,
            "error": "missing_instruction",
            "message": "instruction is required for rewrite_screenplay.",
        }
    if not screenplay_manager:
        return {
            "success": False,
            "error": "no_screenplay_manager",
            "message": "No screenplay manager available. Cannot rewrite.",
        }
    if not llm_service:
        return {
            "success": False,
            "error": "no_llm_service",
            "message": "No LLM service available. Cannot rewrite.",
        }

    if scene_ids is None:
        scenes = screenplay_manager.list_scenes()
        scene_ids = [s.scene_id for s in scenes]
    if not scene_ids:
        return {
            "success": True,
            "updated_scenes": [],
            "message": "No scenes to rewrite.",
        }

    updated: List[str] = []
    for scene_id in scene_ids:
        scene = screenplay_manager.get_scene(scene_id)
        if not scene:
            logger.warning(f"Scene {scene_id} not found, skipping.")
            continue
        new_content = _rewrite_content_with_llm(
            llm_service,
            instruction,
            scene_id,
            scene.content,
            scene.title,
        )
        if not new_content:
            continue
        success = screenplay_manager.update_scene(
            scene_id=scene_id,
            content=new_content,
        )
        if success:
            updated.append(scene_id)
            logger.debug(f"Rewrote scene {scene_id}.")

    return {
        "success": True,
        "updated_scenes": updated,
        "message": f"Rewrote {len(updated)} scene(s) according to instruction: {', '.join(updated) or 'none'}.",
    }


def execute(context: "ToolContext", args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the rewrite screenplay skill in context.

    Args:
        context: ToolContext with get_screenplay_manager() and llm_service
        args: Must contain "instruction". Optional: "scene_id" (single) or "scope" ("all")

    Returns:
        Result dict with success, updated_scenes, message.
    """
    try:
        instruction = args.get("instruction") or (args.get("instruction_text") or "").strip()
        scene_id = args.get("scene_id")
        scope = args.get("scope", "all")

        if not instruction:
            return {
                "success": False,
                "error": "missing_instruction",
                "message": "instruction is required. Describe how the screenplay should be rewritten.",
            }

        screenplay_manager = context.get_screenplay_manager()
        if screenplay_manager is None:
            return {
                "success": False,
                "error": "no_screenplay_manager",
                "message": "No screenplay manager available in context. Cannot rewrite.",
            }

        llm_service = getattr(context, "llm_service", None)
        if llm_service is None:
            return {
                "success": False,
                "error": "no_llm_service",
                "message": "No LLM service available in context. Cannot rewrite.",
            }

        scene_ids: Optional[List[str]] = None
        if scene_id and str(scene_id).strip():
            scene_ids = [str(scene_id).strip()]
        elif scope and str(scope).strip().lower() != "all":
            scene_ids = [str(scope).strip()]

        return rewrite_screenplay_in_context(
            screenplay_manager=screenplay_manager,
            llm_service=llm_service,
            instruction=instruction,
            scene_ids=scene_ids,
        )
    except Exception as e:
        logger.error(f"Error in rewrite_screenplay: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error during rewrite: {str(e)}",
        }


execute_in_context = execute
