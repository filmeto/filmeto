#!/usr/bin/env python3
"""
Screenplay Deletion Skill Script

This script deletes screenplay scenes from the project.
Supports both full deletion (all scenes) and partial deletion (specific scenes).
Supports both CLI execution and in-context execution via the SkillExecutor.
"""
import json
import sys
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

if False:  # TYPE_CHECKING
    from agent.tool.tool_context import ToolContext


def delete_all_scenes_from_manager(
    screenplay_manager: Any
) -> Dict[str, Any]:
    """
    Delete all scenes using a ScreenPlayManager instance.

    Args:
        screenplay_manager: ScreenPlayManager instance

    Returns:
        Result dictionary with success status and deletion info
    """
    try:
        # Get all scenes first
        scenes = screenplay_manager.list_scenes()
        deleted_scene_ids = []
        failed_scene_ids = []

        for scene in scenes:
            scene_id = scene.scene_id if hasattr(scene, 'scene_id') else str(scene)
            if screenplay_manager.delete_scene(scene_id):
                deleted_scene_ids.append(scene_id)
            else:
                failed_scene_ids.append(scene_id)

        total_count = len(scenes)
        deleted_count = len(deleted_scene_ids)

        if failed_scene_ids:
            return {
                "success": True,
                "delete_mode": "all",
                "deleted_count": deleted_count,
                "deleted_scene_ids": deleted_scene_ids,
                "failed_scene_ids": failed_scene_ids,
                "message": f"Deleted {deleted_count} of {total_count} scenes. Failed to delete: {', '.join(failed_scene_ids)}"
            }

        if total_count == 0:
            return {
                "success": True,
                "delete_mode": "all",
                "deleted_count": 0,
                "deleted_scene_ids": [],
                "message": "No screenplay scenes found. Nothing to delete."
            }

        return {
            "success": True,
            "delete_mode": "all",
            "deleted_count": deleted_count,
            "deleted_scene_ids": deleted_scene_ids,
            "message": f"Successfully deleted all {deleted_count} screenplay scenes."
        }

    except Exception as e:
        logger.error(f"Error deleting all scenes: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error deleting scenes: {str(e)}"
        }


def delete_partial_scenes_from_manager(
    screenplay_manager: Any,
    scene_ids: List[str]
) -> Dict[str, Any]:
    """
    Delete specific scenes using a ScreenPlayManager instance.

    Args:
        screenplay_manager: ScreenPlayManager instance
        scene_ids: List of scene identifiers to delete

    Returns:
        Result dictionary with success status and deletion info
    """
    try:
        deleted_scene_ids = []
        failed_scene_ids = []

        for scene_id in scene_ids:
            # Check if scene exists first
            scene = screenplay_manager.get_scene(scene_id)
            if scene is None:
                # Scene doesn't exist, skip it
                continue

            if screenplay_manager.delete_scene(scene_id):
                deleted_scene_ids.append(scene_id)
            else:
                failed_scene_ids.append(scene_id)

        deleted_count = len(deleted_scene_ids)

        if failed_scene_ids:
            return {
                "success": True,
                "delete_mode": "partial",
                "deleted_count": deleted_count,
                "deleted_scene_ids": deleted_scene_ids,
                "failed_scene_ids": failed_scene_ids,
                "message": f"Deleted {deleted_count} scenes. Failed to delete: {', '.join(failed_scene_ids)}"
            }

        if deleted_count == 0:
            return {
                "success": True,
                "delete_mode": "partial",
                "deleted_count": 0,
                "deleted_scene_ids": [],
                "message": "None of the specified scenes were found. Nothing to delete."
            }

        return {
            "success": True,
            "delete_mode": "partial",
            "deleted_count": deleted_count,
            "deleted_scene_ids": deleted_scene_ids,
            "message": f"Successfully deleted {deleted_count} screenplay scenes."
        }

    except Exception as e:
        logger.error(f"Error deleting partial scenes: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error deleting scenes: {str(e)}"
        }


def execute(context: 'ToolContext', args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the screenplay deletion skill in context.

    This is the main entry point for in-context execution via SkillExecutor.

    Args:
        context: ToolContext containing workspace and project
        args: Dictionary of arguments for the skill

    Returns:
        Result dictionary with success status and deletion info
    """
    try:
        # Extract arguments
        delete_mode = args.get('delete_mode', 'all')

        # Validate delete_mode
        if delete_mode not in ['all', 'partial']:
            return {
                "success": False,
                "error": "invalid_delete_mode",
                "message": "delete_mode must be 'all' or 'partial'"
            }

        # Get screenplay_manager from context
        screenplay_manager = context.get_screenplay_manager()

        if screenplay_manager is None:
            return {
                "success": False,
                "error": "no_screenplay_manager",
                "message": "No screenplay manager available in context. Cannot delete scenes."
            }

        if delete_mode == 'all':
            return delete_all_scenes_from_manager(
                screenplay_manager=screenplay_manager
            )
        else:  # partial
            scene_ids = args.get('scene_ids')

            if not scene_ids:
                return {
                    "success": False,
                    "error": "missing_scene_ids",
                    "message": "scene_ids is required for partial deletion mode"
                }

            if not isinstance(scene_ids, list):
                return {
                    "success": False,
                    "error": "invalid_scene_ids",
                    "message": "scene_ids must be a list of scene identifiers"
                }

            return delete_partial_scenes_from_manager(
                screenplay_manager=screenplay_manager,
                scene_ids=scene_ids
            )

    except Exception as e:
        logger.error(f"Error in screenplay deletion: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error in screenplay deletion: {str(e)}"
        }


# Alias for SkillExecutor compatibility
execute_in_context = execute


def main():
    """CLI entry point for standalone execution."""
    args = sys.argv[1:]

    delete_mode = 'all'
    scene_ids = []

    # Process arguments
    i = 0
    while i < len(args):
        if args[i] == '--mode' and i + 1 < len(args):
            delete_mode = args[i + 1]
            i += 2
        elif args[i] == '--scene-ids' and i + 1 < len(args):
            # Parse comma-separated scene IDs
            scene_ids = [s.strip() for s in args[i + 1].split(',')]
            i += 2
        elif args[i] == '--all':
            delete_mode = 'all'
            i += 1
        elif args[i] == '--partial':
            delete_mode = 'partial'
            i += 1
        else:
            i += 1

    # Validate arguments
    if delete_mode not in ['all', 'partial']:
        error_result = {
            "success": False,
            "error": "invalid_delete_mode",
            "message": "delete_mode must be 'all' or 'partial'. Use --all or --partial flag."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    if delete_mode == 'partial' and not scene_ids:
        error_result = {
            "success": False,
            "error": "missing_scene_ids",
            "message": "scene_ids is required for partial deletion. Use --scene-ids with comma-separated IDs."
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
        'delete_mode': delete_mode
    }
    if scene_ids:
        args_dict['scene_ids'] = scene_ids

    result = execute(script_context, args_dict)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
