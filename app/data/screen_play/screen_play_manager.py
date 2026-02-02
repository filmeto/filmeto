"""
Screenplay manager module for Filmeto.

This module manages screenplays for a project, handling creation, retrieval,
updating, and deletion of screenplay scenes.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from utils.md_with_meta_utils import (
    read_md_with_meta,
    write_md_with_meta,
    update_md_with_meta,
    get_metadata,
    get_content
)
from .screen_play_scene import ScreenPlayScene


class ScreenPlayManager:
    """Manages screenplays for a project."""

    def __init__(self, project_path: Union[str, Path]):
        """
        Initialize the ScreenPlayManager for a specific project.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path)
        self.screen_plays_dir = self.project_path / "screen_plays"
        self.screen_plays_dir.mkdir(parents=True, exist_ok=True)

    def create_scene(
        self,
        scene_id: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new screenplay scene.

        Args:
            scene_id: Unique identifier for the scene
            title: Title of the scene
            content: Content of the scene in markdown format
            metadata: Additional metadata for the scene

        Returns:
            True if creation was successful, False otherwise
        """
        if metadata is None:
            metadata = {}

        # Create a ScreenPlayScene instance with the provided data
        scene = ScreenPlayScene(
            scene_id=scene_id,
            title=title,
            content=content,
            # Override defaults with provided metadata
            scene_number=metadata.get("scene_number", ""),
            location=metadata.get("location", ""),
            time_of_day=metadata.get("time_of_day", ""),
            genre=metadata.get("genre", ""),
            logline=metadata.get("logline", ""),
            characters=metadata.get("characters", []),
            story_beat=metadata.get("story_beat", ""),
            page_count=metadata.get("page_count", 0),
            duration_minutes=metadata.get("duration_minutes", 0),
            tags=metadata.get("tags", []),
            status=metadata.get("status", "draft"),
            revision_number=metadata.get("revision_number", 1),
            created_at=metadata.get("created_at", self._get_timestamp()),
            updated_at=metadata.get("updated_at", self._get_timestamp())
        )

        # Get the metadata from the scene instance using to_dict
        scene_data = scene.to_dict()

        # Extract only the metadata fields (excluding scene_id, title, content)
        metadata_for_storage = {
            k: v for k, v in scene_data.items()
            if k not in ["scene_id", "title", "content"]
        }

        # Include any additional custom fields from metadata that aren't in the standard schema
        standard_fields = {
            "scene_number", "location", "time_of_day", "genre", "logline",
            "characters", "story_beat", "page_count", "duration_minutes",
            "tags", "status", "revision_number", "created_at", "updated_at"
        }
        for key, value in metadata.items():
            if key not in standard_fields and key not in metadata_for_storage:
                metadata_for_storage[key] = value

        # Ensure scene_id, title, and content are properly set
        metadata_for_storage["scene_id"] = scene_id
        metadata_for_storage["title"] = title

        scene_file_path = self.screen_plays_dir / f"{scene_id}.md"

        try:
            write_md_with_meta(scene_file_path, metadata_for_storage, content)
            return True
        except Exception:
            return False

    def get_scene(self, scene_id: str) -> Optional[ScreenPlayScene]:
        """
        Retrieve a screenplay scene by ID.

        Args:
            scene_id: Unique identifier for the scene

        Returns:
            ScreenPlayScene object if found, None otherwise
        """
        scene_file_path = self.screen_plays_dir / f"{scene_id}.md"

        if not scene_file_path.exists():
            return None

        try:
            metadata, content = read_md_with_meta(scene_file_path)
            title = metadata.get("title", scene_id)

            # Extract individual meta attributes from the metadata dictionary
            return ScreenPlayScene(
                scene_id=scene_id,
                title=title,
                content=content,
                scene_number=metadata.get("scene_number", ""),
                location=metadata.get("location", ""),
                time_of_day=metadata.get("time_of_day", ""),
                genre=metadata.get("genre", ""),
                logline=metadata.get("logline", ""),
                characters=metadata.get("characters", []),
                story_beat=metadata.get("story_beat", ""),
                page_count=metadata.get("page_count", 0),
                duration_minutes=metadata.get("duration_minutes", 0),
                tags=metadata.get("tags", []),
                status=metadata.get("status", "draft"),
                revision_number=metadata.get("revision_number", 1),
                created_at=metadata.get("created_at", ""),
                updated_at=metadata.get("updated_at", "")
            )
        except Exception:
            return None

    def update_scene(
        self,
        scene_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing screenplay scene.

        Args:
            scene_id: Unique identifier for the scene
            title: New title for the scene (optional)
            content: New content for the scene (optional)
            metadata_updates: Additional metadata updates (optional)

        Returns:
            True if update was successful, False otherwise
        """
        scene_file_path = self.screen_plays_dir / f"{scene_id}.md"

        if not scene_file_path.exists():
            return False

        try:
            # Get current metadata and content
            current_metadata, current_content = read_md_with_meta(scene_file_path)

            # Prepare updates
            updates = {}
            if title is not None:
                updates["title"] = title
                current_metadata["title"] = title
            if metadata_updates:
                updates.update(metadata_updates)
                current_metadata.update(metadata_updates)

            # Update timestamp
            updates["updated_at"] = self._get_timestamp()
            current_metadata["updated_at"] = self._get_timestamp()

            # Determine content to use
            final_content = content if content is not None else current_content

            # Update the file
            return update_md_with_meta(scene_file_path, updates, final_content)
        except Exception:
            return False

    def delete_scene(self, scene_id: str) -> bool:
        """
        Delete a screenplay scene.

        Args:
            scene_id: Unique identifier for the scene

        Returns:
            True if deletion was successful, False otherwise
        """
        scene_file_path = self.screen_plays_dir / f"{scene_id}.md"

        try:
            if scene_file_path.exists():
                os.remove(scene_file_path)
                return True
            return False
        except Exception:
            return False

    def list_scenes(self) -> List[ScreenPlayScene]:
        """
        List all screenplay scenes in the project.

        Returns:
            List of ScreenPlayScene objects
        """
        scenes = []

        for file_path in self.screen_plays_dir.glob("*.md"):
            scene_id = file_path.stem
            scene = self.get_scene(scene_id)
            if scene:
                scenes.append(scene)

        return scenes

    def get_scene_by_title(self, title: str) -> Optional[ScreenPlayScene]:
        """
        Find a scene by its title.

        Args:
            title: Title of the scene to find

        Returns:
            ScreenPlayScene object if found, None otherwise
        """
        for scene in self.list_scenes():
            if scene.title.lower() == title.lower():
                return scene
        return None

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_scene_metadata(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """
        Get only the metadata for a specific scene.

        Args:
            scene_id: Unique identifier for the scene

        Returns:
            Metadata dictionary if found, None otherwise
        """
        scene_file_path = self.screen_plays_dir / f"{scene_id}.md"
        if not scene_file_path.exists():
            return None

        try:
            return get_metadata(scene_file_path)
        except Exception:
            return None

    def get_scene_content(self, scene_id: str) -> Optional[str]:
        """
        Get only the content for a specific scene.

        Args:
            scene_id: Unique identifier for the scene

        Returns:
            Content string if found, None otherwise
        """
        scene_file_path = self.screen_plays_dir / f"{scene_id}.md"
        if not scene_file_path.exists():
            return None

        try:
            return get_content(scene_file_path)
        except Exception:
            return None

    def update_scene_metadata(self, scene_id: str, metadata_updates: Dict[str, Any]) -> bool:
        """
        Update only the metadata for a specific scene.

        Args:
            scene_id: Unique identifier for the scene
            metadata_updates: Dictionary containing metadata fields to update

        Returns:
            True if update was successful, False otherwise
        """
        scene_file_path = self.screen_plays_dir / f"{scene_id}.md"
        if not scene_file_path.exists():
            return False

        try:
            # Get current content
            current_content = self.get_scene_content(scene_id)
            if current_content is None:
                return False

            # Update metadata
            metadata_updates["updated_at"] = self._get_timestamp()
            return update_md_with_meta(scene_file_path, metadata_updates, current_content)
        except Exception:
            return False

    def bulk_create_scenes(self, scenes_data: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Create multiple scenes in bulk.

        Args:
            scenes_data: List of dictionaries containing scene data
                         Each dict should have: scene_id, title, content, and optional metadata

        Returns:
            Dictionary mapping scene_id to success status
        """
        results = {}
        for scene_data in scenes_data:
            scene_id = scene_data.get("scene_id")
            title = scene_data.get("title", "")
            content = scene_data.get("content", "")
            metadata = scene_data.get("metadata", {})

            success = self.create_scene(scene_id, title, content, metadata)
            results[scene_id] = success

        return results

    def get_scenes_by_character(self, character_name: str) -> List[ScreenPlayScene]:
        """
        Find all scenes that include a specific character.

        Args:
            character_name: Name of the character to search for

        Returns:
            List of ScreenPlayScene objects that include the character
        """
        matching_scenes = []
        all_scenes = self.list_scenes()

        for scene in all_scenes:
            # Use the characters attribute directly
            characters = scene.characters if hasattr(scene, 'characters') else []
            if character_name in characters:
                matching_scenes.append(scene)

        return matching_scenes

    def get_scenes_by_location(self, location: str) -> List[ScreenPlayScene]:
        """
        Find all scenes that take place at a specific location.

        Args:
            location: Location to search for

        Returns:
            List of ScreenPlayScene objects that take place at the location
        """
        matching_scenes = []
        all_scenes = self.list_scenes()

        for scene in all_scenes:
            # Use the location attribute directly
            scene_location = scene.location if hasattr(scene, 'location') else ""
            if location.lower() in scene_location.lower():
                matching_scenes.append(scene)

        return matching_scenes