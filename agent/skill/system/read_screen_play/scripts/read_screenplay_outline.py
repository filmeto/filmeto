#!/usr/bin/env python3
"""
Screenplay Outline Reading Skill Script

This script reads and retrieves the complete screenplay outline from the project's
screenplay manager. Supports both CLI execution and in-context execution via the SkillExecutor.
"""
import json
import sys
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

if False:  # TYPE_CHECKING
    from agent.tool.tool_context import ToolContext


def read_outline_from_manager(
    screenplay_manager: Any,
    include_content: bool = False,
    sort_by: str = "scene_number",
    filter_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read the screenplay outline using a ScreenPlayManager instance.

    Args:
        screenplay_manager: ScreenPlayManager instance
        include_content: Whether to include full scene content in response
        sort_by: How to sort scenes (scene_number, created_at, updated_at, title)
        filter_status: Optional status filter (draft, revised, final, approved)

    Returns:
        Result dictionary with success status and outline info
    """
    try:
        # Get all scenes
        scenes = screenplay_manager.list_scenes()

        if not scenes:
            return {
                "success": True,
                "total_scenes": 0,
                "outline": [],
                "message": "No scenes found in the screenplay. The outline is empty."
            }

        # Apply status filter if specified
        if filter_status:
            scenes = [s for s in scenes if s.status == filter_status]

        # Sort scenes
        if sort_by == "scene_number":
            # Try to sort by scene number as integer for proper ordering
            def get_sort_key(scene):
                try:
                    # Extract numeric part for sorting (e.g., "1A" -> 1, "2" -> 2)
                    import re
                    match = re.search(r'\d+', scene.scene_number)
                    return int(match.group()) if match else 0
                except (ValueError, AttributeError):
                    return 0
            scenes.sort(key=get_sort_key)
        elif sort_by == "created_at":
            scenes.sort(key=lambda s: s.created_at or "")
        elif sort_by == "updated_at":
            scenes.sort(key=lambda s: s.updated_at or "")
        elif sort_by == "title":
            scenes.sort(key=lambda s: s.title or "")

        # Build outline
        outline = []
        for scene in scenes:
            scene_data = {
                "scene_id": scene.scene_id,
                "title": scene.title,
                "scene_number": scene.scene_number,
                "logline": scene.logline,
                "location": scene.location,
                "time_of_day": scene.time_of_day,
                "characters": scene.characters,
                "story_beat": scene.story_beat,
                "duration_minutes": scene.duration_minutes,
                "status": scene.status,
                "created_at": scene.created_at,
                "updated_at": scene.updated_at
            }

            if include_content:
                scene_data["content"] = scene.content

            outline.append(scene_data)

        return {
            "success": True,
            "total_scenes": len(outline),
            "outline": outline,
            "filtered_by": filter_status,
            "sorted_by": sort_by,
            "message": f"Screenplay outline retrieved successfully with {len(outline)} scene(s)."
        }

    except Exception as e:
        logger.error(f"Error reading screenplay outline: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error reading screenplay outline: {str(e)}"
        }


def execute(context: 'ToolContext', args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the screenplay outline reading skill in context.

    This is the main entry point for in-context execution via SkillExecutor.

    Args:
        context: ToolContext containing workspace and project
        args: Dictionary of arguments for the skill

    Returns:
        Result dictionary with success status and outline info
    """
    try:
        # Extract arguments
        include_content = args.get('include_content', False)
        sort_by = args.get('sort_by', 'scene_number')
        filter_status = args.get('filter_status', None)

        # Get screenplay_manager from context
        screenplay_manager = context.get_screenplay_manager()

        if screenplay_manager is None:
            return {
                "success": False,
                "error": "no_screenplay_manager",
                "message": "No screenplay manager available in context. Cannot read outline."
            }

        return read_outline_from_manager(
            screenplay_manager=screenplay_manager,
            include_content=include_content,
            sort_by=sort_by,
            filter_status=filter_status
        )

    except Exception as e:
        logger.error(f"Error in screenplay outline reading: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error in screenplay outline reading: {str(e)}"
        }


# Alias for SkillExecutor compatibility
execute_in_context = execute


def main():
    """CLI entry point for standalone execution."""
    args = sys.argv[1:]

    include_content = False
    sort_by = "scene_number"
    filter_status = None

    # Process arguments
    i = 0
    while i < len(args):
        if args[i] == '--include-content' and i + 1 < len(args):
            include_content = args[i + 1].lower() in ('true', '1', 'yes')
            i += 2
        elif args[i] == '--sort-by' and i + 1 < len(args):
            sort_by = args[i + 1]
            i += 2
        elif args[i] == '--filter-status' and i + 1 < len(args):
            filter_status = args[i + 1]
            i += 2
        else:
            i += 1

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
        'include_content': include_content,
        'sort_by': sort_by
    }

    if filter_status:
        args_dict['filter_status'] = filter_status

    result = execute(script_context, args_dict)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
