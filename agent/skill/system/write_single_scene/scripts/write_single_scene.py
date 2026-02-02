#!/usr/bin/env python3
"""
Single Scene Writing Skill Script

This script writes and updates individual scenes in the project's screenplay manager.
Supports both CLI execution and in-context execution via the SkillExecutor.
"""
import json
import sys
import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import os
import ast
from datetime import datetime

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent.skill.skill_service import SkillContext


def write_scene_to_manager(
    screenplay_manager: Any,
    scene_id: str,
    title: str,
    content: str,
    scene_number: Optional[str] = None,
    location: Optional[str] = None,
    time_of_day: Optional[str] = None,
    genre: Optional[str] = None,
    logline: Optional[str] = None,
    characters: Optional[List[str]] = None,
    story_beat: Optional[str] = None,
    page_count: Optional[int] = None,
    duration_minutes: Optional[int] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Write or update a single scene using a ScreenPlayManager instance.

    Args:
        screenplay_manager: ScreenPlayManager instance
        scene_id: Unique identifier for the scene
        title: Title of the scene
        content: Content of the scene in screenplay format
        scene_number: Scene number in the screenplay
        location: Location of the scene
        time_of_day: Time of day for the scene
        genre: Genre of the screenplay
        logline: Logline for the scene
        characters: List of characters appearing in the scene
        story_beat: Story beat or plot point for the scene
        page_count: Estimated page count for the scene
        duration_minutes: Estimated duration in minutes
        tags: Tags for categorizing the scene
        status: Status of the scene (draft, revised, final)

    Returns:
        Result dictionary with success status and scene info
    """
    try:
        # Try to get the existing scene to preserve unchanged metadata
        existing_scene = screenplay_manager.get_scene(scene_id)

        # Prepare metadata for the scene
        if existing_scene:
            # Update existing scene - use current values as defaults
            metadata = {
                "scene_number": scene_number if scene_number is not None else existing_scene.scene_number,
                "location": location if location is not None else existing_scene.location,
                "time_of_day": time_of_day if time_of_day is not None else existing_scene.time_of_day,
                "genre": genre if genre is not None else existing_scene.genre,
                "logline": logline if logline is not None else existing_scene.logline,
                "characters": characters if characters is not None else existing_scene.characters,
                "story_beat": story_beat if story_beat is not None else existing_scene.story_beat,
                "page_count": page_count if page_count is not None else existing_scene.page_count,
                "duration_minutes": duration_minutes if duration_minutes is not None else existing_scene.duration_minutes,
                "tags": tags if tags is not None else existing_scene.tags,
                "status": status if status is not None else existing_scene.status,
                "revision_number": existing_scene.revision_number + 1,
                "created_at": existing_scene.created_at,
                "updated_at": datetime.now().isoformat()
            }
            action = "updated"
        else:
            # Creating new scene - use provided values or defaults
            metadata = {
                "scene_number": scene_number or "",
                "location": location or "",
                "time_of_day": time_of_day or "",
                "genre": genre or "General",
                "logline": logline or title,
                "characters": characters or [],
                "story_beat": story_beat or "",
                "page_count": page_count or 0,
                "duration_minutes": duration_minutes or 0,
                "tags": tags or [],
                "status": status or "draft",
                "revision_number": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            action = "created"

        # Create or update the scene
        if existing_scene:
            success = screenplay_manager.update_scene(
                scene_id=scene_id,
                title=title,
                content=content,
                metadata_updates=metadata
            )
        else:
            success = screenplay_manager.create_scene(
                scene_id=scene_id,
                title=title,
                content=content,
                metadata=metadata
            )

        if success:
            return {
                "success": True,
                "action": action,
                "scene_id": scene_id,
                "title": title,
                "message": f"Scene '{scene_id}' successfully {action}."
            }
        else:
            return {
                "success": False,
                "scene_id": scene_id,
                "message": f"Failed to {action} scene '{scene_id}'."
            }

    except Exception as e:
        logger.error(f"Error writing scene '{args.get('scene_id', 'unknown')}': {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error writing scene: {str(e)}"
        }


def execute_in_context(
    context: 'SkillContext',
    scene_id: str,
    title: str,
    content: str,
    scene_number: Optional[str] = None,
    location: Optional[str] = None,
    time_of_day: Optional[str] = None,
    genre: Optional[str] = None,
    logline: Optional[str] = None,
    characters: Optional[List[str]] = None,
    story_beat: Optional[str] = None,
    page_count: Optional[int] = None,
    duration_minutes: Optional[int] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute the single scene writing skill in-context with a SkillContext.

    This is the main entry point for in-context execution via SkillExecutor.

    Args:
        context: SkillContext containing workspace, project, and basic services
        scene_id: Unique identifier for the scene
        title: Title of the scene
        content: Content of the scene in screenplay format
        ... (other scene parameters)

    Returns:
        Result dictionary with success status and scene info
    """
    try:
        # Get screenplay_manager from context using the convenience method
        # This keeps business-specific logic out of the basic context
        screenplay_manager = context.get_screenplay_manager()

        if screenplay_manager is None:
            return {
                "success": False,
                "error": "no_screenplay_manager",
                "message": "No screenplay manager available in context. Cannot write scene."
            }

        return write_scene_to_manager(
            screenplay_manager=screenplay_manager,
            scene_id=scene_id,
            title=title,
            content=content,
            scene_number=scene_number,
            location=location,
            time_of_day=time_of_day,
            genre=genre,
            logline=logline,
            characters=characters,
            story_beat=story_beat,
            page_count=page_count,
            duration_minutes=duration_minutes,
            tags=tags,
            status=status
        )

    except Exception as e:
        logger.error(f"Error in single scene writing: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error in single scene writing: {str(e)}"
        }


# Alias for SkillExecutor compatibility
execute = execute_in_context


def main():
    """CLI entry point for standalone execution.

    This function is designed to be flexible and work both as a standalone script
    and when called via execute_skill_script tool. It manually parses arguments
    rather than using argparse to avoid errors when optional parameters are missing.
    """
    # Handle both traditional positional args and new approach with named args
    args = sys.argv[1:]  # Skip script name

    scene_id = None
    title = None
    content = None
    project_path = None
    scene_number = None
    location = None
    time_of_day = None
    genre = None
    logline = None
    characters_str = None
    story_beat = None
    page_count = None
    duration_minutes = None
    tags_str = None
    status = None

    # Process arguments by looking for known flags first
    i = 0
    while i < len(args):
        if args[i] == '--scene-id' and i + 1 < len(args):
            scene_id = args[i + 1]
            i += 2
        elif args[i] == '--title' and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i] == '--content' and i + 1 < len(args):
            content = args[i + 1]
            i += 2
        elif args[i] == '--project-path' and i + 1 < len(args):
            project_path = args[i + 1]
            i += 2
        elif args[i] == '--scene-number' and i + 1 < len(args):
            scene_number = args[i + 1]
            i += 2
        elif args[i] == '--location' and i + 1 < len(args):
            location = args[i + 1]
            i += 2
        elif args[i] == '--time-of-day' and i + 1 < len(args):
            time_of_day = args[i + 1]
            i += 2
        elif args[i] == '--genre' and i + 1 < len(args):
            genre = args[i + 1]
            i += 2
        elif args[i] == '--logline' and i + 1 < len(args):
            logline = args[i + 1]
            i += 2
        elif args[i] == '--characters' and i + 1 < len(args):
            characters_str = args[i + 1]
            i += 2
        elif args[i] == '--story-beat' and i + 1 < len(args):
            story_beat = args[i + 1]
            i += 2
        elif args[i] == '--page-count' and i + 1 < len(args):
            try:
                page_count = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == '--duration-minutes' and i + 1 < len(args):
            try:
                duration_minutes = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == '--tags' and i + 1 < len(args):
            tags_str = args[i + 1]
            i += 2
        elif args[i] == '--status' and i + 1 < len(args):
            status = args[i + 1]
            i += 2
        else:
            # For backward compatibility, handle positional arguments
            # Order: scene_id, title, content, project_path
            if scene_id is None and not args[i].startswith('--'):
                scene_id = args[i]
                i += 1
            elif title is None and not args[i].startswith('--'):
                title = args[i]
                i += 1
            elif content is None and not args[i].startswith('--'):
                content = args[i]
                i += 1
            elif project_path is None and not args[i].startswith('--'):
                project_path = args[i]
                i += 1
            else:
                # Skip unknown arguments
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

    if not title:
        error_result = {
            "success": False,
            "error": "missing_title",
            "message": "title is required. Please provide --title or as second positional argument."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    if not content:
        error_result = {
            "success": False,
            "error": "missing_content",
            "message": "content is required. Please provide --content or as third positional argument."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    # project_path is optional when called via execute_skill_script (it's in context)
    # but required for standalone CLI execution
    if not project_path:
        error_result = {
            "success": False,
            "error": "missing_project_path",
            "message": "project_path is required. Please provide --project-path or as fourth positional argument."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    # Parse list arguments (characters, tags)
    characters = None
    if characters_str:
        try:
            # Try JSON first
            characters = json.loads(characters_str)
        except json.JSONDecodeError:
            # Try Python literal
            try:
                characters = ast.literal_eval(characters_str)
                if not isinstance(characters, list):
                    characters = [characters]
            except (ValueError, SyntaxError):
                # Split by comma as last resort
                characters = characters_str.split(',')

    tags = None
    if tags_str:
        try:
            # Try JSON first
            tags = json.loads(tags_str)
        except json.JSONDecodeError:
            # Try Python literal
            try:
                tags = ast.literal_eval(tags_str)
                if not isinstance(tags, list):
                    tags = [tags]
            except (ValueError, SyntaxError):
                # Split by comma as last resort
                tags = tags_str.split(',')

    try:
        # For CLI execution, create the screenplay manager directly
        from app.data.screen_play import ScreenPlayManager

        screenplay_manager = ScreenPlayManager(project_path)

        result = write_scene_to_manager(
            screenplay_manager=screenplay_manager,
            scene_id=scene_id,
            title=title,
            content=content,
            scene_number=scene_number,
            location=location,
            time_of_day=time_of_day,
            genre=genre,
            logline=logline,
            characters=characters,
            story_beat=story_beat,
            page_count=page_count,
            duration_minutes=duration_minutes,
            tags=tags,
            status=status
        )

        print(json.dumps(result, indent=2))
        return result

    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Error in single scene writing: {str(e)}"
        }
        print(json.dumps(error_result, indent=2))
        return error_result


if __name__ == "__main__":
    main()