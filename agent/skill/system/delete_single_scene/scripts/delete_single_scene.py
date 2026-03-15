#!/usr/bin/env python3
"""
Single Scene Deletion Skill Script

This script deletes individual scenes from the project's screenplay manager.
Supports both CLI execution and in-context execution via the SkillExecutor.

Supports scene identification by:
- Explicit scene_id (e.g., "scene_001")
- Position descriptions (e.g., "last", "first", "next")
- Scene numbers (e.g., "scene 3", "第 3 个场景")
"""
import json
import sys
import logging
import re
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

if False:  # TYPE_CHECKING
    from agent.tool.tool_context import ToolContext


def resolve_scene_id_from_description(
    screenplay_manager: Any,
    scene_description: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve a scene description to a scene_id.

    Args:
        screenplay_manager: ScreenPlayManager instance
        scene_description: Description like "scene_001", "last scene", "第一幕", etc.

    Returns:
        Tuple of (scene_id, error_message)
        - If successful: (scene_id, None)
        - If failed: (None, error_message)
    """
    try:
        # Get all scenes
        scenes = screenplay_manager.list_scenes()

        if not scenes:
            return None, "No scenes exist in the screenplay. Nothing to delete."

        # Normalize the description
        desc = scene_description.lower().strip()

        # Handle "last scene", "final scene", "最后一幕", "最后一场戏"
        if any(keyword in desc for keyword in ['last', 'final', 'ending', '最后', '末尾']):
            # Get the last scene
            last_scene = scenes[-1]
            return last_scene.scene_id, None

        # Handle "first scene", "第一幕", "第一个场景"
        if any(keyword in desc for keyword in ['first', '第一', '开头', '开始']):
            first_scene = scenes[0]
            return first_scene.scene_id, None

        # Handle "next scene", "下一幕"
        if any(keyword in desc for keyword in ['next', '下一', '随后']):
            # For now, treat "next" as the first scene (could be enhanced with context)
            if len(scenes) > 1:
                next_scene = scenes[1]
            else:
                next_scene = scenes[0]
            return next_scene.scene_id, None

        # Handle "previous scene", "上一幕"
        if any(keyword in desc for keyword in ['previous', '上一', '前一个']):
            # For now, treat "previous" as the second-to-last scene
            if len(scenes) > 1:
                prev_scene = scenes[-2]
            else:
                prev_scene = scenes[0]
            return prev_scene.scene_id, None

        # Handle explicit scene_id format (scene_001, scene_002, etc.)
        match = re.match(r'scene[_\s]?(\d+)', desc)
        if match:
            scene_num = int(match.group(1))
            scene_id = f"scene_{scene_num:03d}"
            # Verify scene exists
            scene = screenplay_manager.get_scene(scene_id)
            if scene:
                return scene_id, None
            else:
                return None, f"Scene '{scene_id}' does not exist."

        # Handle Chinese ordinal format (第 X 个场景)
        chinese_match = re.search(r'第 ([零一二三四五六七八九十百千\d]+) [个场]', desc)
        if chinese_match:
            num_str = chinese_match.group(1)
            # Convert Chinese numerals to Arabic
            chinese_numerals = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
                               '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
            if num_str.isdigit():
                scene_num = int(num_str)
            elif num_str in chinese_numerals:
                scene_num = chinese_numerals[num_str]
            else:
                # Handle complex Chinese numerals (十一，十二，etc.)
                if len(num_str) == 2 and num_str[0] == '十':
                    scene_num = 10 + chinese_numerals.get(num_str[1], 0)
                elif len(num_str) == 2 and num_str[1] == '十':
                    scene_num = chinese_numerals.get(num_str[0], 1) * 10
                else:
                    scene_num = 1  # Default fallback

            if 1 <= scene_num <= len(scenes):
                target_scene = scenes[scene_num - 1]
                return target_scene.scene_id, None
            else:
                return None, f"Scene number {scene_num} is out of range (1-{len(scenes)})."

        # Handle simple number format (scene 3, 场景 3)
        number_match = re.search(r'(\d+)', desc)
        if number_match:
            scene_num = int(number_match.group(1))
            if 1 <= scene_num <= len(scenes):
                target_scene = scenes[scene_num - 1]
                return target_scene.scene_id, None
            else:
                return None, f"Scene number {scene_num} is out of range (1-{len(scenes)})."

        # If we can't resolve, return error
        return None, f"Could not resolve scene description: '{scene_description}'. Please provide a valid scene_id or position (e.g., 'last scene', 'scene_001', '第一幕')."

    except Exception as e:
        logger.error(f"Error resolving scene description: {e}", exc_info=True)
        return None, f"Error resolving scene description: {str(e)}"


def delete_scene_from_manager(
    screenplay_manager: Any,
    scene_id: str
) -> Dict[str, Any]:
    """
    Delete a single scene using a ScreenPlayManager instance.

    Args:
        screenplay_manager: ScreenPlayManager instance
        scene_id: Unique identifier for the scene

    Returns:
        Result dictionary with success status and deletion info
    """
    try:
        # Check if scene exists first
        scene = screenplay_manager.get_scene(scene_id)
        exists = scene is not None

        # Attempt deletion
        deleted = screenplay_manager.delete_scene(scene_id)

        if exists and deleted:
            return {
                "success": True,
                "scene_id": scene_id,
                "deleted": True,
                "message": f"Scene '{scene_id}' deleted successfully."
            }
        elif not exists:
            return {
                "success": True,
                "scene_id": scene_id,
                "deleted": False,
                "message": f"Scene '{scene_id}' does not exist. Nothing to delete."
            }
        else:
            return {
                "success": False,
                "scene_id": scene_id,
                "deleted": False,
                "message": f"Failed to delete scene '{scene_id}'."
            }

    except Exception as e:
        logger.error(f"Error deleting scene '{scene_id}': {e}", exc_info=True)
        return {
            "success": False,
            "scene_id": scene_id,
            "error": str(e),
            "message": f"Error deleting scene: {str(e)}"
        }


def execute(context: 'ToolContext', args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the single scene deletion skill in context.

    This is the main entry point for in-context execution via SkillExecutor.

    Args:
        context: ToolContext containing workspace and project
        args: Dictionary of arguments for the skill. Supports:
            - scene_id: Explicit scene identifier (e.g., "scene_001")
            - scene_description: Natural language description (e.g., "last scene", "第一幕")

    Returns:
        Result dictionary with success status and deletion info
    """
    try:
        # Extract arguments
        scene_id = args.get('scene_id')
        scene_description = args.get('scene_description')

        # Get screenplay_manager from context
        screenplay_manager = context.get_screenplay_manager()

        if screenplay_manager is None:
            return {
                "success": False,
                "error": "no_screenplay_manager",
                "message": "No screenplay manager available in context. Cannot delete scene."
            }

        # If scene_id is not provided, try to resolve from description
        if not scene_id:
            if not scene_description:
                return {
                    "success": False,
                    "error": "missing_scene_identifier",
                    "message": "Either scene_id or scene_description is required"
                }

            # Resolve scene_id from description
            resolved_scene_id, error = resolve_scene_id_from_description(
                screenplay_manager,
                scene_description
            )

            if error:
                return {
                    "success": False,
                    "error": "scene_resolution_failed",
                    "message": error
                }

            scene_id = resolved_scene_id

        return delete_scene_from_manager(
            screenplay_manager=screenplay_manager,
            scene_id=scene_id
        )

    except Exception as e:
        logger.error(f"Error in single scene deletion: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error in single scene deletion: {str(e)}"
        }


# Alias for SkillExecutor compatibility
execute_in_context = execute


def main():
    """CLI entry point for standalone execution."""
    args = sys.argv[1:]

    scene_id = None

    # Process arguments
    i = 0
    while i < len(args):
        if args[i] == '--scene-id' and i + 1 < len(args):
            scene_id = args[i + 1]
            i += 2
        else:
            # Handle positional argument for scene_id
            if scene_id is None and not args[i].startswith('--'):
                scene_id = args[i]
            i += 1

    # Validate required arguments
    if not scene_id:
        error_result = {
            "success": False,
            "error": "missing_scene_id",
            "message": "scene_id is required. Please provide --scene-id or as first positional argument."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    # Try to get screenplay_manager from context
    script_context = globals().get('context')
    screenplay_manager = None

    if script_context:
        if hasattr(script_context, 'get_screenplay_manager'):
            screenplay_manager = script_context.get_screenplay_manager()

    if not screenplay_manager:
        error_result = {
            "success": False,
            "error": "no_context",
            "message": "This script requires a context with screenplay manager. Please run via the skill system."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    # Build args dict and call execute
    args_dict = {
        'scene_id': scene_id
    }

    result = execute(script_context, args_dict)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
