#!/usr/bin/env python3
"""
Single Scene Writing Skill Script

This script writes and updates individual scenes in the project's screenplay manager.
Supports both CLI execution and in-context execution via the SkillExecutor.
"""
import json
import sys
import argparse
import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import os
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
        context: SkillContext containing workspace, project, screenplay_manager
        scene_id: Unique identifier for the scene
        title: Title of the scene
        content: Content of the scene in screenplay format
        ... (other scene parameters)

    Returns:
        Result dictionary with success status and scene info
    """
    try:
        # Validate context
        screenplay_manager = context.screenplay_manager
        if screenplay_manager is None:
            if context.project is not None and hasattr(context.project, 'screenplay_manager'):
                screenplay_manager = context.project.screenplay_manager

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
    """CLI entry point for standalone execution."""
    parser = argparse.ArgumentParser(
        description="Write or update a single scene in the screenplay"
    )
    parser.add_argument(
        "--scene-id", type=str, required=True,
        help="Unique identifier for the scene"
    )
    parser.add_argument(
        "--title", type=str, required=True,
        help="Title of the scene"
    )
    parser.add_argument(
        "--content", type=str, required=True,
        help="Content of the scene in screenplay format"
    )
    parser.add_argument(
        "--project-path", type=str, required=True,
        help="Path to the project directory"
    )
    parser.add_argument("--scene-number", type=str, help="Scene number in the screenplay")
    parser.add_argument("--location", type=str, help="Location of the scene")
    parser.add_argument("--time-of-day", type=str, help="Time of day for the scene")
    parser.add_argument("--genre", type=str, help="Genre of the screenplay")
    parser.add_argument("--logline", type=str, help="Logline for the scene")
    parser.add_argument("--characters", type=str, nargs='+', help="Characters in the scene")
    parser.add_argument("--story-beat", type=str, help="Story beat for the scene")
    parser.add_argument("--page-count", type=int, help="Estimated page count")
    parser.add_argument("--duration-minutes", type=int, help="Estimated duration in minutes")
    parser.add_argument("--tags", type=str, nargs='+', help="Tags for the scene")
    parser.add_argument("--status", type=str, help="Status (draft, revised, final)")

    args = parser.parse_args()

    try:
        # For CLI execution, create the screenplay manager directly
        from app.data.screen_play import ScreenPlayManager

        screenplay_manager = ScreenPlayManager(args.project_path)

        result = write_scene_to_manager(
            screenplay_manager=screenplay_manager,
            scene_id=args.scene_id,
            title=args.title,
            content=args.content,
            scene_number=args.scene_number,
            location=args.location,
            time_of_day=args.time_of_day,
            genre=args.genre,
            logline=args.logline,
            characters=args.characters,
            story_beat=args.story_beat,
            page_count=args.page_count,
            duration_minutes=args.duration_minutes,
            tags=args.tags,
            status=args.status
        )

        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Error in single scene writing: {str(e)}"
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()