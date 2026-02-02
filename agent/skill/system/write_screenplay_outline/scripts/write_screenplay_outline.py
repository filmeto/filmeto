#!/usr/bin/env python3
"""
Screenplay Outline Writing Skill Script

This script generates screenplay outlines and creates scenes in the project's screenplay manager.
Supports both CLI execution and in-context execution via the SkillExecutor.
"""
import json
import sys
import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import os
from datetime import datetime

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent.tool.tool_context import ToolContext


def generate_screenplay_outline(
    concept: str,
    genre: str = "General",
    num_scenes: int = 10
) -> List[Dict[str, Any]]:
    """
    Generate a screenplay outline based on the provided concept.

    Args:
        concept: The basic concept or idea for the screenplay
        genre: The genre of the screenplay
        num_scenes: Number of scenes to generate in the outline

    Returns:
        A list of scene dictionaries with structure information
    """
    outline = []

    # Define scene types for story structure
    scene_types = [
        "establishing shot", "character introduction", "conflict setup",
        "rising action", "subplot development", "character development",
        "plot twist", "climax setup", "climactic scene", "resolution"
    ]

    # Genre-appropriate locations
    genre_locations = {
        "film noir": [
            "INT. JAZZ CLUB - NIGHT", "EXT. RAIN-SOAKED ALLEY - NIGHT",
            "INT. DETECTIVE'S OFFICE - DAY", "EXT. DOCKS - NIGHT",
            "INT. SPEAKEASY - NIGHT", "EXT. CITY STREET - NIGHT",
            "INT. POLICE STATION - DAY", "INT. MANSION - EVENING"
        ],
        "drama": [
            "INT. LIVING ROOM - DAY", "EXT. HOSPITAL - DAY",
            "INT. OFFICE - DAY", "EXT. PARK - DAY",
            "INT. RESTAURANT - NIGHT", "EXT. SUBURBAN HOME - DAY",
            "INT. COURTROOM - DAY", "EXT. CEMETERY - DAY"
        ],
        "action": [
            "EXT. ROOFTOP - NIGHT", "INT. WAREHOUSE - DAY",
            "EXT. HIGHWAY - DAY", "INT. UNDERGROUND BUNKER - NIGHT",
            "EXT. DOCK YARD - NIGHT", "INT. PENTHOUSE - NIGHT",
            "EXT. CONSTRUCTION SITE - DAY", "INT. CONTROL ROOM - DAY"
        ],
        "default": [
            "INT. MAIN CHARACTER'S APARTMENT - DAY", "EXT. CITY STREET - DAY",
            "INT. OFFICE BUILDING - DAY", "EXT. PARK - DAY",
            "INT. RESTAURANT - NIGHT", "EXT. SUBURBAN HOME - DAY",
            "INT. POLICE STATION - DAY", "EXT. INDUSTRIAL AREA - NIGHT"
        ]
    }

    locations = genre_locations.get(genre.lower(), genre_locations["default"])

    # Extract character hints from concept
    characters = _extract_characters_from_concept(concept)

    # Generate scenes based on the concept
    for i in range(min(num_scenes, len(scene_types))):
        scene_type = scene_types[i % len(scene_types)]
        location = locations[i % len(locations)]
        character_set = [characters[j % len(characters)] for j in range((i % 3) + 1)]

        # Parse location parts
        loc_parts = location.split(" - ")
        loc_name = loc_parts[0][5:] if len(loc_parts[0]) > 5 else loc_parts[0]  # Remove INT./EXT.
        time_of_day = loc_parts[1] if len(loc_parts) > 1 else "DAY"

        scene = {
            "scene_number": f"{i+1:02d}",
            "location": loc_name,
            "time_of_day": time_of_day,
            "setup": f"{scene_type.replace('_', ' ').title()} scene",
            "characters": character_set,
            "logline": f"Scene {i+1}: {scene_type.replace('_', ' ').title()} - {loc_name}",
            "story_beat": scene_type,
            "content": _generate_scene_content(location, scene_type, character_set, concept),
            "duration_minutes": 2 + (i % 3),
            "tags": [genre.lower(), scene_type.replace(" ", "_")],
            "genre": genre
        }

        outline.append(scene)

    return outline


def _extract_characters_from_concept(concept: str) -> List[str]:
    """Extract potential character names or generate defaults based on concept."""
    # Default character names if none can be extracted
    default_characters = [
        "ALEX", "JORDAN", "MAYA", "RILEY", "QUINN",
        "CAMERON", "PARKER", "DREW", "CASEY", "FINLEY"
    ]
    
    # In a full implementation, this would use NLP to extract character names
    # For now, return defaults
    return default_characters


def _generate_scene_content(
    location: str,
    scene_type: str,
    characters: List[str],
    concept: str
) -> str:
    """Generate screenplay-formatted content for a scene."""
    content_lines = [
        f"# {location}",
        "",
        f"% {scene_type.replace('_', ' ').title()} scene based on: {concept[:100]}...",
        "",
    ]
    
    if characters:
        content_lines.extend([
            f"**{characters[0]}**",
            f"This is where the {scene_type.replace('_', ' ')} unfolds.",
            ""
        ])
    
    content_lines.append("% Scene content to be developed...")
    
    return "\n".join(content_lines)


def write_scenes_to_manager(
    outline: List[Dict[str, Any]],
    screenplay_manager: Any
) -> Dict[str, Any]:
    """
    Write screenplay scenes to a ScreenPlayManager instance.

    Args:
        outline: The screenplay outline to convert to scenes
        screenplay_manager: ScreenPlayManager instance

    Returns:
        Result dictionary with success status and created scene IDs
    """
    created_scenes = []
    failed_scenes = []

    for scene_data in outline:
        scene_id = f"scene_{scene_data['scene_number'].zfill(3)}"

        try:
            # Prepare metadata
            metadata = {
                "scene_number": scene_data['scene_number'],
                "location": scene_data['location'],
                "time_of_day": scene_data['time_of_day'],
                "genre": scene_data.get('genre', 'General'),
                "logline": scene_data['logline'],
                "characters": scene_data['characters'],
                "story_beat": scene_data['story_beat'],
                "page_count": len(scene_data['content'].split('\n')) // 10,
                "duration_minutes": scene_data['duration_minutes'],
                "tags": scene_data['tags'],
                "status": "draft",
                "revision_number": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Create the scene
            success = screenplay_manager.create_scene(
                scene_id=scene_id,
                title=scene_data['logline'],
                content=scene_data['content'],
                metadata=metadata
            )

            if success:
                created_scenes.append(scene_id)
            else:
                failed_scenes.append(scene_id)

        except Exception as e:
            logger.error(f"Error creating scene {scene_id}: {e}", exc_info=True)
            failed_scenes.append(scene_id)

    result = {
        "success": len(failed_scenes) == 0,
        "total_scenes": len(outline),
        "created_scenes": created_scenes,
        "failed_scenes": failed_scenes,
        "message": f"Successfully created {len(created_scenes)} out of {len(outline)} scenes."
    }

    if failed_scenes:
        result["message"] += f" Failed to create {len(failed_scenes)} scenes: {failed_scenes}."

    return result


def execute(context: 'ToolContext', args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the screenplay outline skill in context.

    This is the main entry point for in-context execution via SkillExecutor.

    Args:
        context: ToolContext containing workspace and project
        args: Dictionary of arguments for the skill (concept, genre, num_scenes)

    Returns:
        Result dictionary with success status and created scene IDs
    """
    try:
        # Extract arguments
        concept = args.get('concept')
        genre = args.get('genre', 'General')
        num_scenes = args.get('num_scenes', 10)

        if not concept:
            return {
                "success": False,
                "error": "missing_concept",
                "message": "concept is required"
            }

        # Get screenplay_manager from context using the convenience method
        screenplay_manager = context.get_screenplay_manager()

        if screenplay_manager is None:
            return {
                "success": False,
                "error": "no_screenplay_manager",
                "message": "No screenplay manager available in context. Cannot create scenes."
            }

        # Generate the outline
        outline = generate_screenplay_outline(concept, genre, num_scenes)

        # Write scenes to the manager
        result = write_scenes_to_manager(outline, screenplay_manager)

        # Add the outline to the result for reference
        result["outline_summary"] = [
            {"scene_id": f"scene_{s['scene_number'].zfill(3)}", "logline": s['logline']}
            for s in outline
        ]

        print(json.dumps(result, indent=2))
        return result

    except Exception as e:
        logger.error(f"Error in screenplay outline generation: {e}", exc_info=True)
        result = {
            "success": False,
            "error": str(e),
            "message": f"Error in screenplay outline generation: {str(e)}"
        }
        print(json.dumps(result, indent=2))
        return result


# Alias for SkillExecutor compatibility
execute_in_context = execute


def main():
    """CLI entry point for standalone execution.

    This function is designed to be flexible and work both as a standalone script
    and when called via execute_skill_script tool. It manually parses arguments
    rather than using argparse to avoid errors when optional parameters are missing.
    """
    # Handle both traditional positional args and new approach with named args
    args = sys.argv[1:]  # Skip script name

    concept = None
    genre = "General"
    num_scenes = 10

    # Process arguments by looking for known flags first
    i = 0
    while i < len(args):
        if args[i] == '--concept' and i + 1 < len(args):
            concept = args[i + 1]
            i += 2
        elif args[i] == '--genre' and i + 1 < len(args):
            genre = args[i + 1]
            i += 2
        elif args[i] == '--num-scenes' and i + 1 < len(args):
            try:
                num_scenes = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            # For backward compatibility, handle positional arguments
            # First non-flag argument is concept
            if concept is None and not args[i].startswith('--'):
                concept = args[i]
                i += 1
            else:
                # Skip unknown arguments (including --project-path)
                i += 1

    # Validate required arguments
    if not concept:
        error_result = {
            "success": False,
            "error": "missing_concept",
            "message": "concept is required. Please provide --concept or as first positional argument."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    # Try to get context from injected globals
    # This is injected by tool_service when executing skill scripts
    script_context = globals().get('context')

    if not script_context:
        error_result = {
            "success": False,
            "error": "no_context",
            "message": "This script requires a context with screenplay manager. Please run via the skill system."
        }
        print(json.dumps(error_result, indent=2))
        return error_result

    # Build args dict and call execute
    args_dict = {
        'concept': concept,
        'genre': genre,
        'num_scenes': num_scenes
    }

    result = execute(script_context, args_dict)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()