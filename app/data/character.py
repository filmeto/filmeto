"""
Character Management System

Manages actor data for projects with support for:
- Character metadata (name, story, relationships, etc.)
- Character resource files (images: main view, front, back, left, right, poses, costumes, etc.)
- Project-scoped actor organization
"""

import os
import uuid
import shutil
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
from pathlib import Path
from blinker import signal

from utils.lazy_load import AsyncLazyLoadMixin
from utils.async_file_io import path_exists, run_coroutine_blocking, to_thread
from utils.yaml_utils import AsyncFileIoError, load_yaml, load_yaml_async, save_yaml


class Character:
    """Represents a single actor in the project"""
    
    # Resource file types
    RESOURCE_TYPES = {
        'main_view': '主视图',
        'front_view': '前视图',
        'back_view': '后视图',
        'left_view': '左视图',
        'right_view': '右视图',
        'pose': '姿势图',
        'costume': '服装图',
        'other': '其他'
    }
    
    def __init__(self, data: Dict[str, Any], project_path: str):
        """Initialize actor from metadata dictionary
        
        Args:
            data: Character metadata dictionary
            project_path: Absolute path to the project directory
        """
        self.project_path = project_path
        self.character_id = data.get('character_id', str(uuid.uuid4()))
        self.name = data.get('name', '')
        self.description = data.get('description', '')
        self.story = data.get('story', '')
        self.relationships = data.get('relationships', {})  # Dict of character_name -> relationship_description
        self.resources = data.get('resources', {})  # Dict of resource_type -> resource_path (relative to project root)
        self.metadata = data.get('metadata', {})  # Additional metadata
        self.created_at = data.get('created_at', datetime.now().isoformat())
        self.updated_at = data.get('updated_at', datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert actor to dictionary for serialization"""
        return {
            'character_id': self.character_id,
            'name': self.name,
            'description': self.description,
            'story': self.story,
            'relationships': self.relationships,
            'resources': self.resources,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def get_resource_path(self, resource_type: str) -> Optional[str]:
        """Get resource file path (relative to project root)
        
        Args:
            resource_type: Type of resource (main_view, front_view, etc.)
            
        Returns:
            Relative file path or None if not set
        """
        return self.resources.get(resource_type)
    
    def get_absolute_resource_path(self, resource_type: str) -> Optional[str]:
        """Get absolute resource file path
        
        Args:
            resource_type: Type of resource
            
        Returns:
            Absolute file path or None if not set
        """
        rel_path = self.get_resource_path(resource_type)
        if rel_path:
            return os.path.join(self.project_path, rel_path)
        return None
    
    def resource_exists(self, resource_type: str) -> bool:
        """Check if resource file exists
        
        Args:
            resource_type: Type of resource
            
        Returns:
            True if resource exists, False otherwise
        """
        # Fast check: just verify resource path is set, don't check file system
        # File existence check should be done lazily when actually loading the image
        return resource_type in self.resources and self.resources[resource_type] is not None
    
    def set_resource(self, resource_type: str, resource_path: str):
        """Set resource file path
        
        Args:
            resource_type: Type of resource
            resource_path: Relative file path from project root
        """
        self.resources[resource_type] = resource_path
        self.updated_at = datetime.now().isoformat()
    
    def remove_resource(self, resource_type: str):
        """Remove resource file reference
        
        Args:
            resource_type: Type of resource
        """
        if resource_type in self.resources:
            del self.resources[resource_type]
            self.updated_at = datetime.now().isoformat()


class CharacterManager(AsyncLazyLoadMixin):
    """Manages project characters with centralized YAML storage"""
    
    # Signals for actor events
    character_added = signal('character_added')
    character_updated = signal('character_updated')
    character_deleted = signal('character_deleted')
    
    def __init__(self, project_path: str, resource_manager=None):
        """Initialize actor manager for a project
        
        Args:
            project_path: Absolute path to the project directory
            resource_manager: ResourceManager instance for handling actor resources
        """
        self.project_path = project_path
        self.resource_manager = resource_manager
        self.characters_dir = os.path.join(project_path, 'characters')
        self.config_path = os.path.join(self.characters_dir, 'config.yml')
        
        # In-memory index: character_name -> Character
        self._characters: Dict[str, Character] = {}
        self._loaded = False
        self._load_lock = threading.Lock()
        
        # Initialize directory structure
        self._ensure_directories()

    def _do_load(self) -> None:
        run_coroutine_blocking(self._do_load_async())

    async def _do_load_async(self) -> None:
        if await path_exists(self.config_path):
            try:
                data = await load_yaml_async(self.config_path)
                if data and "characters" in data:
                    for char_data in data["characters"]:
                        character = Character(char_data, self.project_path)
                        self._characters[character.name] = character
                    logger.info(
                        "✅ Loaded %s characters from central config", len(self._characters)
                    )
                    return
            except AsyncFileIoError as e:
                logger.error("❌ Error loading central actor config: %s", e)
            except Exception as e:
                logger.error("❌ Error loading central actor config: %s", e)

        await to_thread(self._load_characters_migration_sync)

    def _clear_internal_state(self) -> None:
        self._characters.clear()

    def _ensure_directories(self):
        """Create characters directory if it doesn't exist"""
        os.makedirs(self.characters_dir, exist_ok=True)
    
    def _load_characters_migration_sync(self) -> None:
        """Directory-based migration (blocking); run via ``to_thread`` from async load."""
        if not os.path.exists(self.characters_dir):
            return
        migrated_count = 0
        for item in os.listdir(self.characters_dir):
            if item == "config.yml":
                continue
            character_dir = os.path.join(self.characters_dir, item)
            if os.path.isdir(character_dir):
                config_path = os.path.join(character_dir, "config.yml")
                if os.path.exists(config_path):
                    try:
                        data = load_yaml(config_path)
                        if data:
                            character = Character(data, self.project_path)

                            if self.resource_manager:
                                updated_resources = {}
                                for res_type, rel_path in character.resources.items():
                                    abs_src = os.path.join(self.project_path, rel_path)
                                    if os.path.exists(abs_src):
                                        resource = self.resource_manager.add_resource(
                                            source_file_path=abs_src,
                                            source_type="character_resource",
                                            source_id=character.character_id,
                                            original_name=os.path.basename(rel_path),
                                        )
                                        if resource:
                                            updated_resources[res_type] = resource.file_path
                                    else:
                                        updated_resources[res_type] = rel_path
                                character.resources = updated_resources

                            self._characters[character.name] = character
                            migrated_count += 1
                            logger.info("📦 Migrated actor: %s", character.name)
                    except Exception as e:
                        logger.error("❌ Error loading actor %s for migration: %s", item, e)

        if migrated_count > 0:
            logger.info("✅ Migrated %s characters to new structure", migrated_count)
            self._save_all_characters()

    def _save_all_characters(self) -> bool:
        """Save all characters to the central config.yml

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'characters': [char.to_dict() for char in self._characters.values()]
            }
            save_yaml(self.config_path, data)
            return True
        except Exception as e:
            logger.error(f"❌ Error saving characters config: {e}")
            return False

    def _save_character(self, character: Character) -> bool:
        """Save all characters to disk (since they are now in a single file)
        
        Args:
            character: Character instance (unused, kept for API compatibility)
            
        Returns:
            True if successful, False otherwise
        """
        return self._save_all_characters()
    
    def create_character(self, name: str, description: str = '', story: str = '') -> Optional[Character]:
        """Create a new actor
        
        Args:
            name: Character name (must be unique)
            description: Character description
            story: Character story/background
            
        Returns:
            Character instance if successful, None if name already exists
        """
        self._ensure_loaded()
        # Validate name
        if not name or not name.strip():
            logger.error("❌ Character name cannot be empty")
            return None
        
        name = name.strip()
        
        # Check if actor already exists
        if name in self._characters:
            logger.error(f"❌ Character '{name}' already exists")
            return None
        
        # Create actor instance
        character_data = {
            'character_id': str(uuid.uuid4()),
            'name': name,
            'description': description,
            'story': story,
            'relationships': {},
            'resources': {},
            'metadata': {},
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        character = Character(character_data, self.project_path)
        
        # Add to index
        self._characters[name] = character
        
        # Save to disk
        if not self._save_all_characters():
            del self._characters[name]
            return None
        
        # Send signal
        self.character_added.send(character)
        
        logger.info(f"✅ Created actor: {name}")
        return character
    
    def get_character(self, name: str) -> Optional[Character]:
        """Get actor by name
        
        Args:
            name: Character name
            
        Returns:
            Character instance or None if not found
        """
        self._ensure_loaded()
        return self._characters.get(name)
    
    def list_characters(self) -> List[Character]:
        """List all characters
        
        Returns:
            List of Character instances
        """
        self._ensure_loaded()
        return list(self._characters.values())
    
    def update_character(self, name: str, **kwargs) -> bool:
        """Update actor properties
        
        Args:
            name: Character name
            **kwargs: Properties to update (description, story, relationships, name, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_loaded()
        character = self.get_character(name)
        if not character:
            logger.error(f"❌ Character '{name}' not found")
            return False

        # Update allowed fields
        allowed_fields = ['name', 'description', 'story', 'relationships', 'metadata']
        updated = False
        old_name = character.name

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(character, field):
                if field == 'name':
                    new_name = value.strip()
                    if not new_name: continue
                    if new_name != old_name:
                        if new_name in self._characters:
                            logger.error(f"❌ Cannot rename to '{new_name}': already exists")
                            continue
                        # Handle name change in index
                        del self._characters[old_name]
                        character.name = new_name
                        self._characters[new_name] = character
                        updated = True
                else:
                    setattr(character, field, value)
                    updated = True

        if updated:
            character.updated_at = datetime.now().isoformat()

            # Save to disk
            if not self._save_all_characters():
                return False

            # Send signal
            self.character_updated.send(character)

            logger.info(f"✅ Updated actor: {character.name}")
            return True

        return False
    
    def delete_character(self, name: str, remove_files: bool = True) -> bool:
        """Delete a actor
        
        Args:
            name: Character name
            remove_files: Unused, kept for API compatibility
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_loaded()
        character = self.get_character(name)
        if not character:
            logger.error(f"❌ Character '{name}' not found")
            return False

        try:
            # Remove from index
            del self._characters[name]

            # Save to disk
            if not self._save_all_characters():
                self._characters[name] = character
                return False

            # Send signal
            self.character_deleted.send(name)

            logger.info(f"✅ Deleted actor: {name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error deleting actor {name}: {e}")
            return False
    
    def add_resource(self, character_name: str, resource_type: str, source_file_path: str) -> Optional[str]:
        """Add a resource file to a actor via ResourceManager
        
        Args:
            character_name: Character name
            resource_type: Type of resource (main_view, front_view, etc.)
            source_file_path: Path to source file (absolute or relative)
            
        Returns:
            Relative path to the resource file if successful, None otherwise
        """
        self._ensure_loaded()
        if not self.resource_manager:
            logger.error("❌ ResourceManager not available in CharacterManager")
            return None

        character = self.get_character(character_name)
        if not character:
            logger.error(f"❌ Character '{character_name}' not found")
            return None

        # Resolve source file path
        if not os.path.isabs(source_file_path):
            abs_source = os.path.join(self.project_path, source_file_path)
        else:
            abs_source = source_file_path

        if not os.path.exists(abs_source):
            logger.error(f"❌ Source file does not exist: {abs_source}")
            return None

        # Check if this resource is already managed by ResourceManager and belongs to this actor
        current_rel_path = character.get_resource_path(resource_type)
        if current_rel_path:
            abs_current = os.path.join(self.project_path, current_rel_path)
            if os.path.normpath(abs_current) == os.path.normpath(abs_source):
                # Path hasn't changed, no need to re-add
                return current_rel_path

        try:
            # Add to ResourceManager
            resource = self.resource_manager.add_resource(
                source_file_path=abs_source,
                source_type='character_resource',
                source_id=character.character_id,
                original_name=f"{character_name}_{resource_type}{os.path.splitext(abs_source)[1]}"
            )

            if not resource:
                return None

            # Set resource path in actor (relative path from project root)
            character.set_resource(resource_type, resource.file_path)

            # Save actor config
            if not self._save_all_characters():
                return None

            # Send signal
            self.character_updated.send(character)

            logger.info(f"✅ Added resource '{resource_type}' to actor '{character_name}' via ResourceManager")
            return resource.file_path

        except Exception as e:
            logger.error(f"❌ Error adding resource to actor {character_name}: {e}")
            return None
    
    def remove_resource(self, character_name: str, resource_type: str, remove_file: bool = False) -> bool:
        """Remove a resource from a actor
        
        Args:
            character_name: Character name
            resource_type: Type of resource
            remove_file: Whether to delete the physical file from ResourceManager (default: False)
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_loaded()
        character = self.get_character(character_name)
        if not character:
            logger.error(f"❌ Character '{character_name}' not found")
            return False

        # Optional: remove from ResourceManager if requested
        if remove_file and self.resource_manager:
            rel_path = character.get_resource_path(resource_type)
            if rel_path:
                resource_name = os.path.basename(rel_path)
                self.resource_manager.delete_resource(resource_name)

        # Remove resource reference
        character.remove_resource(resource_type)

        # Save actor config
        if not self._save_all_characters():
            return False

        # Send signal
        self.character_updated.send(character)

        logger.info(f"✅ Removed resource '{resource_type}' from actor '{character_name}'")
        return True
    
    def rename_character(self, old_name: str, new_name: str) -> bool:
        """Rename a actor
        
        Args:
            old_name: Current actor name
            new_name: New actor name
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_character(old_name, name=new_name)
    
    def search_characters(self, query: str) -> List[Character]:
        """Search characters by name or description
        
        Args:
            query: Search query string
            
        Returns:
            List of matching Character instances
        """
        self._ensure_loaded()
        query_lower = query.lower()
        results = []
        
        for character in self._characters.values():
            if (query_lower in character.name.lower() or 
                query_lower in character.description.lower() or
                query_lower in character.story.lower()):
                results.append(character)
        
        return results

