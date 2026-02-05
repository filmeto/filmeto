#!/usr/bin/env python3
"""
Single Scene Deletion Skill Script

This script deletes individual scenes from the project's screenplay manager.
Supports both CLI execution and in-context execution via the SkillExecutor.
"""
import json
import sys
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

if False:  # TYPE_CHECKING
    from agent.tool.tool_context import ToolContext


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
        args: Dictionary of arguments for the skill

    Returns:
        Result dictionary with success status and deletion info
    """
    try:
        # Extract arguments
        scene_id = args.get('scene_id')

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
                "message": "No screenplay manager available in context. Cannot delete scene."
            }

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
