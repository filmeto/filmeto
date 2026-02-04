#!/usr/bin/env python3
"""
Single Scene Reading Skill Script

This script reads and retrieves individual scenes from the project's screenplay manager.
Supports both CLI execution and in-context execution via the SkillExecutor.
"""
import json
import sys
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

if False:  # TYPE_CHECKING
    from agent.tool.tool_context import ToolContext


def read_scene_from_manager(
    screenplay_manager: Any,
    scene_id: str,
    include_content: bool = True,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Read a single scene using a ScreenPlayManager instance.

    Args:
        screenplay_manager: ScreenPlayManager instance
        scene_id: Unique identifier for the scene
        include_content: Whether to include scene content in response
        include_metadata: Whether to include scene metadata in response

    Returns:
        Result dictionary with success status and scene info
    """
    try:
        # Try to get the scene
        scene = screenplay_manager.get_scene(scene_id)

        if not scene:
            return {
                "success": False,
                "scene_id": scene_id,
                "message": f"Scene '{scene_id}' not found in the screenplay."
            }

        # Build response
        result = {
            "success": True,
            "scene_id": scene_id,
            "title": scene.title,
            "message": f"Scene '{scene_id}' retrieved successfully."
        }

        if include_content:
            result["content"] = scene.content

        if include_metadata:
            result["metadata"] = {
                "scene_number": scene.scene_number,
                "location": scene.location,
                "time_of_day": scene.time_of_day,
                "genre": scene.genre,
                "logline": scene.logline,
                "characters": scene.characters,
                "story_beat": scene.story_beat,
                "page_count": scene.page_count,
                "duration_minutes": scene.duration_minutes,
                "tags": scene.tags,
                "status": scene.status,
                "revision_number": scene.revision_number,
                "created_at": scene.created_at,
                "updated_at": scene.updated_at
            }

        return result

    except Exception as e:
        logger.error(f"Error reading scene '{scene_id}': {e}", exc_info=True)
        return {
            "success": False,
            "scene_id": scene_id,
            "error": str(e),
            "message": f"Error reading scene: {str(e)}"
        }


def execute(context: 'ToolContext', args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the single scene reading skill in context.

    This is the main entry point for in-context execution via SkillExecutor.

    Args:
        context: ToolContext containing workspace and project
        args: Dictionary of arguments for the skill

    Returns:
        Result dictionary with success status and scene info
    """
    try:
        # Extract arguments
        scene_id = args.get('scene_id')
        include_content = args.get('include_content', True)
        include_metadata = args.get('include_metadata', True)

        if not scene_id:
            return {
                "success": False,
                "error": "missing_scene_id",
                "message": "scene_id is required"
            }

        # Get screenplay_manager from context
        screenplay_manager = context.get_screenplay_manager()

        if screenplay_manager is None:
            return {
                "success": False,
                "error": "no_screenplay_manager",
                "message": "No screenplay manager available in context. Cannot read scene."
            }

        return read_scene_from_manager(
            screenplay_manager=screenplay_manager,
            scene_id=scene_id,
            include_content=include_content,
            include_metadata=include_metadata
        )

    except Exception as e:
        logger.error(f"Error in single scene reading: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error in single scene reading: {str(e)}"
        }


# Alias for SkillExecutor compatibility
execute_in_context = execute


def main():
    """CLI entry point for standalone execution."""
    args = sys.argv[1:]

    scene_id = None
    include_content = True
    include_metadata = True

    # Process arguments
    i = 0
    while i < len(args):
        if args[i] == '--scene-id' and i + 1 < len(args):
            scene_id = args[i + 1]
            i += 2
        elif args[i] == '--include-content' and i + 1 < len(args):
            include_content = args[i + 1].lower() in ('true', '1', 'yes')
            i += 2
        elif args[i] == '--include-metadata' and i + 1 < len(args):
            include_metadata = args[i + 1].lower() in ('true', '1', 'yes')
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
        'scene_id': scene_id,
        'include_content': include_content,
        'include_metadata': include_metadata
    }

    result = execute(script_context, args_dict)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
