import os
import uuid
import shutil
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from blinker import signal

from utils.lazy_load import AsyncLazyLoadMixin
from utils.async_file_io import (
    load_yaml_async,
    path_exists,
    run_coroutine_blocking,
    save_yaml_async,
    shutil_copy2,
    to_thread,
)
from utils.yaml_utils import AsyncFileIoError, save_yaml

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import cv2
except ImportError:
    cv2 = None


class Resource:
    """Represents a single resource in the project"""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize resource from metadata dictionary"""
        self.resource_id = data.get('resource_id', str(uuid.uuid4()))
        self.name = data['name']
        self.original_name = data.get('original_name', self.name)
        self.media_type = data['media_type']
        self.file_path = data['file_path']  # Relative path from project root
        self.source_type = data.get('source_type', 'imported')
        self.source_id = data.get('source_id', '')
        self.file_size = data.get('file_size', 0)
        self.created_at = data.get('created_at', datetime.now().isoformat())
        self.updated_at = data.get('updated_at', datetime.now().isoformat())
        self.metadata = data.get('metadata', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to dictionary for serialization"""
        return {
            'resource_id': self.resource_id,
            'name': self.name,
            'original_name': self.original_name,
            'media_type': self.media_type,
            'file_path': self.file_path,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'file_size': self.file_size,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata
        }
    
    def get_absolute_path(self, project_path: str) -> str:
        """Get absolute file path"""
        return os.path.join(project_path, self.file_path)
    
    def exists(self, project_path: str) -> bool:
        """Check if resource file exists on disk"""
        return os.path.exists(self.get_absolute_path(project_path))


class ResourceManager(AsyncLazyLoadMixin):
    """Manages project resources with centralized storage and metadata indexing"""
    
    # Signals for resource events
    resource_added = signal('resource_added')
    resource_updated = signal('resource_updated')
    resource_deleted = signal('resource_deleted')
    index_loaded = signal('index_loaded')
    
    # Media type mappings
    MEDIA_TYPE_EXTENSIONS = {
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
        'video': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
        'audio': ['.mp3', '.wav', '.aac', '.flac'],
    }
    
    def __init__(self, project_path: str):
        """Initialize resource manager for a project
        
        Args:
            project_path: Absolute path to the project directory
        """
        self.project_path = project_path
        self.resources_dir = os.path.join(project_path, 'resources')
        self.index_file = os.path.join(self.resources_dir, 'resource_index.yml')
        
        # In-memory indexes
        self._resources_by_name: Dict[str, Resource] = {}
        self._resources_by_id: Dict[str, Resource] = {}
        self._loaded = False
        self._load_lock = threading.Lock()
        
        # Initialize directories and migrate old index file if needed
        self._ensure_directories()

    def _do_load(self) -> None:
        run_coroutine_blocking(self._do_load_async())

    async def _do_load_async(self) -> None:
        await to_thread(self._migrate_index_if_needed)
        if await path_exists(self.index_file):
            try:
                data = await load_yaml_async(self.index_file)
                if data and "resources" in data:
                    for resource_data in data["resources"]:
                        resource = Resource(resource_data)
                        self._resources_by_name[resource.name] = resource
                        self._resources_by_id[resource.resource_id] = resource
                    logger.info("✅ Loaded %s resources from index", len(self._resources_by_name))
                    self.index_loaded.send(len(self._resources_by_name))
                else:
                    logger.warning("⚠️ Empty or invalid index file, starting fresh")
            except AsyncFileIoError as e:
                logger.error("❌ Error loading resource index: %s", e)
                logger.warning("⚠️ Starting with empty index")
            except Exception as e:
                logger.error("❌ Error loading resource index: %s", e)
                logger.warning("⚠️ Starting with empty index")
        else:
            logger.info("📝 No existing index found, creating new one")
            await save_yaml_async(self.index_file, {"resources": []})

    def _clear_internal_state(self) -> None:
        self._resources_by_name.clear()
        self._resources_by_id.clear()

    def _ensure_directories(self):
        """Create resources directory structure if it doesn't exist"""
        os.makedirs(self.resources_dir, exist_ok=True)
        os.makedirs(os.path.join(self.resources_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(self.resources_dir, 'videos'), exist_ok=True)
        os.makedirs(os.path.join(self.resources_dir, 'audio'), exist_ok=True)
        os.makedirs(os.path.join(self.resources_dir, 'others'), exist_ok=True)
    
    def _migrate_index_if_needed(self):
        """Migrate resource_index.yml from project root to resources directory if it exists in old location"""
        old_index_file = os.path.join(self.project_path, 'resource_index.yml')

        # Check if old index file exists and new one doesn't
        if os.path.exists(old_index_file) and not os.path.exists(self.index_file):
            try:
                # Move the file to new location
                shutil.move(old_index_file, self.index_file)
                logger.info(f"✅ Migrated resource_index.yml from project root to resources directory")
            except Exception as e:
                logger.warning(f"⚠️ Warning: Could not migrate resource_index.yml: {e}")
                # If move fails, try copying instead
                try:
                    shutil.copy2(old_index_file, self.index_file)
                    logger.info(f"✅ Copied resource_index.yml to resources directory")
                except Exception as e2:
                    logger.error(f"❌ Error copying resource_index.yml: {e2}")
        elif os.path.exists(old_index_file) and os.path.exists(self.index_file):
            # Both exist - keep the new one, remove the old one
            try:
                os.remove(old_index_file)
                logger.info(f"✅ Removed old resource_index.yml from project root (new one already exists)")
            except Exception as e:
                logger.warning(f"⚠️ Warning: Could not remove old resource_index.yml: {e}")
    
    def _save_index(self):
        """Persist resource index to YAML file"""
        try:
            data = {
                'resources': [resource.to_dict() for resource in self._resources_by_name.values()]
            }
            save_yaml(self.index_file, data)
        except Exception as e:
            logger.error(f"❌ Error saving resource index: {e}")
            raise
    
    def _get_media_type(self, filename: str) -> str:
        """Determine media type from file extension"""
        ext = os.path.splitext(filename)[1].lower()
        for media_type, extensions in self.MEDIA_TYPE_EXTENSIONS.items():
            if ext in extensions:
                return media_type
        return 'other'
    
    def _get_media_subdirectory(self, media_type: str) -> str:
        """Get subdirectory name for media type"""
        if media_type in ['image', 'video', 'audio']:
            return f"{media_type}s"
        return 'others'
    
    def _generate_unique_name(self, desired_name: str) -> str:
        """Generate unique resource name by appending counter if needed
        
        Args:
            desired_name: The desired filename (with extension)
            
        Returns:
            Unique filename that doesn't conflict with existing resources
        """
        if desired_name not in self._resources_by_name:
            return desired_name
        
        # Extract base name and extension
        base, ext = os.path.splitext(desired_name)
        counter = 1
        
        while True:
            new_name = f"{base}_{counter}{ext}"
            if new_name not in self._resources_by_name:
                return new_name
            counter += 1
    
    def _extract_file_metadata(self, file_path: str, media_type: str) -> Dict[str, Any]:
        """Extract metadata from media file
        
        Args:
            file_path: Absolute path to the file
            media_type: Type of media (image, video, etc.)
            
        Returns:
            Dictionary of metadata attributes
        """
        metadata = {}
        
        try:
            if media_type == 'image' and Image is not None:
                # Extract image metadata using PIL
                with Image.open(file_path) as img:
                    metadata['width'] = img.width
                    metadata['height'] = img.height
                    metadata['format'] = img.format
            
            elif media_type == 'video' and cv2 is not None:
                # Extract video metadata using OpenCV
                cap = cv2.VideoCapture(file_path)
                if cap.isOpened():
                    metadata['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    metadata['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    metadata['fps'] = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    if metadata['fps'] > 0:
                        metadata['duration'] = frame_count / metadata['fps']
                    cap.release()
        
        except Exception as e:
            logger.warning(f"⚠️ Warning: Could not extract metadata from {file_path}: {e}")
        
        return metadata
    
    def add_resource(self, 
                    source_file_path: str,
                    source_type: str = 'imported',
                    source_id: str = '',
                    original_name: Optional[str] = None,
                    additional_metadata: Optional[Dict[str, Any]] = None) -> Optional[Resource]:
        """Add a new resource to the project
        
        Args:
            source_file_path: Path to the source file
            source_type: Origin type (uploaded, drawing, ai_generated, imported)
            source_id: Optional reference to source entity (task_id, layer_id, etc.)
            original_name: Optional override for original filename
            additional_metadata: Optional type-specific metadata (prompt, model, etc.)
            
        Returns:
            Resource object if successful, None if failed
        """
        self._ensure_loaded()
        # Validate source file exists
        if not os.path.exists(source_file_path):
            logger.error(f"❌ Source file does not exist: {source_file_path}")
            return None
        
        try:
            # Determine filename and media type
            filename = original_name or os.path.basename(source_file_path)
            media_type = self._get_media_type(filename)
            
            # Generate unique resource name
            unique_name = self._generate_unique_name(filename)
            
            # Determine destination path
            subdirectory = self._get_media_subdirectory(media_type)
            relative_path = os.path.join('resources', subdirectory, unique_name)
            destination_path = os.path.join(self.project_path, relative_path)
            
            # Copy file to resources directory (async-backed I/O)
            shutil_copy2(source_file_path, destination_path)

            # Get file size
            file_size = os.path.getsize(destination_path)

            # Extract metadata off the event-loop thread when invoked from Qt async loop
            extracted_metadata = run_coroutine_blocking(
                to_thread(self._extract_file_metadata, destination_path, media_type)
            )
            
            # Merge with additional metadata
            if additional_metadata:
                extracted_metadata.update(additional_metadata)
            
            # Create resource record
            resource_data = {
                'resource_id': str(uuid.uuid4()),
                'name': unique_name,
                'original_name': filename,
                'media_type': media_type,
                'file_path': relative_path,
                'source_type': source_type,
                'source_id': source_id,
                'file_size': file_size,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'metadata': extracted_metadata
            }
            
            resource = Resource(resource_data)
            
            # Update indexes
            self._resources_by_name[resource.name] = resource
            self._resources_by_id[resource.resource_id] = resource
            
            # Persist index
            self._save_index()
            
            # Send signal
            self.resource_added.send(resource)
            
            logger.info(f"✅ Added resource: {unique_name} (type: {media_type})")
            return resource
        
        except Exception as e:
            logger.error(f"❌ Error adding resource: {e}")
            # Cleanup if file was copied but registration failed
            if 'destination_path' in locals() and os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                except:
                    pass
            return None
    
    def get_by_name(self, name: str) -> Optional[Resource]:
        """Retrieve resource by filename"""
        self._ensure_loaded()
        return self._resources_by_name.get(name)
    
    def get_by_id(self, resource_id: str) -> Optional[Resource]:
        """Retrieve resource by UUID"""
        self._ensure_loaded()
        return self._resources_by_id.get(resource_id)
    
    def get_by_source(self, source_type: str, source_id: str) -> List[Resource]:
        """Get all resources from a specific source"""
        self._ensure_loaded()
        return [
            resource for resource in self._resources_by_name.values()
            if resource.source_type == source_type and resource.source_id == source_id
        ]
    
    def list_by_type(self, media_type: str) -> List[Resource]:
        """List all resources of a media type"""
        self._ensure_loaded()
        return [
            resource for resource in self._resources_by_name.values()
            if resource.media_type == media_type
        ]
    
    def get_all(self) -> List[Resource]:
        """Retrieve all project resources"""
        self._ensure_loaded()
        return list(self._resources_by_name.values())

    def list_resources(self, resource_type: Optional[str] = None) -> List[Resource]:
        """List all resources, optionally filtered by resource type

        Args:
            resource_type: Optional filter for resource type ('image', 'video', 'audio', etc.)

        Returns:
            List of Resource objects
        """
        self._ensure_loaded()
        if resource_type:
            return self.list_by_type(resource_type)
        return self.get_all()
    
    def search(self, 
              media_type: Optional[str] = None,
              source_type: Optional[str] = None,
              name_contains: Optional[str] = None) -> List[Resource]:
        """Search resources by criteria
        
        Args:
            media_type: Filter by media type
            source_type: Filter by source type
            name_contains: Filter by name substring
            
        Returns:
            List of matching resources
        """
        self._ensure_loaded()
        results = self.get_all()
        
        if media_type:
            results = [r for r in results if r.media_type == media_type]
        
        if source_type:
            results = [r for r in results if r.source_type == source_type]
        
        if name_contains:
            results = [r for r in results if name_contains.lower() in r.name.lower()]
        
        return results
    
    def update_metadata(self, resource_name: str, metadata: Dict[str, Any]) -> bool:
        """Update resource metadata

        Args:
            resource_name: Name of the resource
            metadata: New metadata to merge with existing

        Returns:
            True if successful, False otherwise
        """
        self._ensure_loaded()
        resource = self.get_by_name(resource_name)
        if not resource:
            logger.error(f"❌ Resource not found: {resource_name}")
            return False

        try:
            # Update metadata
            resource.metadata.update(metadata)
            resource.updated_at = datetime.now().isoformat()

            # Persist changes
            self._save_index()

            # Send signal
            self.resource_updated.send(resource)

            logger.info(f"✅ Updated metadata for resource: {resource_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Error updating resource metadata: {e}")
            return False
    
    def delete_resource(self, resource_name: str, remove_file: bool = True) -> bool:
        """Delete a resource

        Args:
            resource_name: Name of the resource to delete
            remove_file: Whether to delete the physical file (default: True)

        Returns:
            True if successful, False otherwise
        """
        self._ensure_loaded()
        resource = self.get_by_name(resource_name)
        if not resource:
            logger.error(f"❌ Resource not found: {resource_name}")
            return False

        try:
            # Remove physical file if requested
            if remove_file:
                file_path = resource.get_absolute_path(self.project_path)
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Remove from indexes
            del self._resources_by_name[resource.name]
            del self._resources_by_id[resource.resource_id]

            # Persist changes
            self._save_index()

            # Send signal
            self.resource_deleted.send(resource_name)

            logger.info(f"✅ Deleted resource: {resource_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Error deleting resource: {e}")
            return False
    
    def get_resource_path(self, resource_name: str) -> Optional[str]:
        """Get absolute file path for a resource
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            Absolute file path or None if resource not found
        """
        self._ensure_loaded()
        resource = self.get_by_name(resource_name)
        if resource:
            return resource.get_absolute_path(self.project_path)
        return None
    
    def validate_index(self) -> Dict[str, Any]:
        """Validate index consistency and return report
        
        Returns:
            Dictionary with validation results
        """
        self._ensure_loaded()
        report = {
            'total_resources': len(self._resources_by_name),
            'missing_files': [],
            'orphaned_files': [],
            'valid_resources': 0
        }
        
        # Check for missing files
        for resource in self._resources_by_name.values():
            if not resource.exists(self.project_path):
                report['missing_files'].append(resource.name)
            else:
                report['valid_resources'] += 1
        
        # Check for orphaned files in resources directory
        indexed_files = {resource.file_path for resource in self._resources_by_name.values()}
        
        for media_type_dir in ['images', 'videos', 'audio', 'others']:
            dir_path = os.path.join(self.resources_dir, media_type_dir)
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    file_path = os.path.join('resources', media_type_dir, filename)
                    if file_path not in indexed_files:
                        report['orphaned_files'].append(file_path)
        
        return report
