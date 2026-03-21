"""
Resource Processor

Handles processing of different resource input types:
- Local file paths
- Remote URLs (download)
- Base64 encoded data (decode)
"""

import os
import base64
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional
import aiohttp
import asyncio

from server.api.types import ResourceInput, ResourceType, ResourceProcessingError

logger = logging.getLogger(__name__)

DEFAULT_MAX_FILE_SIZES: Dict[str, int] = {
    'image': 50 * 1024 * 1024,   # 50MB
    'video': 500 * 1024 * 1024,  # 500MB
    'audio': 100 * 1024 * 1024,  # 100MB
}

DEFAULT_MIME_MAP: Dict[str, str] = {
    # Images
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/webp': '.webp',
    'image/gif': '.gif',
    'image/bmp': '.bmp',
    # Videos
    'video/mp4': '.mp4',
    'video/quicktime': '.mov',
    'video/x-msvideo': '.avi',
    'video/x-matroska': '.mkv',
    'video/webm': '.webm',
    # Audio
    'audio/mpeg': '.mp3',
    'audio/wav': '.wav',
    'audio/ogg': '.ogg',
    'audio/mp4': '.m4a',
    'audio/x-m4a': '.m4a',
}


class ResourceProcessor:
    """
    Processor for handling different types of resource inputs.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, config: Optional[Dict] = None):
        """
        Initialize resource processor.
        
        Args:
            cache_dir: Directory for caching downloaded/decoded resources
            config: Optional configuration dict. Supported keys:
                - max_file_sizes: dict mapping media category ('image', 'video', 'audio')
                  to max bytes
                - mime_type_map: dict mapping MIME type strings to file extensions
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "filmeto_cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        config = config or {}
        self.max_file_sizes: Dict[str, int] = {
            **DEFAULT_MAX_FILE_SIZES,
            **config.get('max_file_sizes', {}),
        }
        self.mime_type_map: Dict[str, str] = {
            **DEFAULT_MIME_MAP,
            **config.get('mime_type_map', {}),
        }
    
    async def process_resource(self, resource: ResourceInput) -> str:
        """
        Process resource and return local file path.
        
        Args:
            resource: Resource input to process
            
        Returns:
            Local file path to the processed resource
            
        Raises:
            ResourceProcessingError: If processing fails
        """
        if resource.type == ResourceType.LOCAL_PATH:
            return await self._process_local_path(resource)
        elif resource.type == ResourceType.REMOTE_URL:
            return await self._process_remote_url(resource)
        elif resource.type == ResourceType.BASE64:
            return await self._process_base64(resource)
        else:
            raise ResourceProcessingError(
                f"Unsupported resource type: {resource.type}",
                {"type": resource.type}
            )
    
    async def _process_local_path(self, resource: ResourceInput) -> str:
        """
        Process local file path.
        
        Validates that the file exists and is accessible.
        """
        file_path = resource.data
        
        # Security: Ensure path doesn't escape allowed directories
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            raise ResourceProcessingError(
                f"File not found: {file_path}",
                {"path": file_path}
            )
        
        if not os.path.isfile(abs_path):
            raise ResourceProcessingError(
                f"Path is not a file: {file_path}",
                {"path": file_path}
            )
        
        # Validate file size
        file_size = os.path.getsize(abs_path)
        self._validate_file_size(file_size, resource.mime_type)
        
        return abs_path
    
    async def _process_remote_url(self, resource: ResourceInput) -> str:
        """
        Download file from remote URL.
        
        Caches downloaded files to avoid re-downloading.
        """
        url = resource.data
        
        # Create cache key from URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Get file extension from mime type
        ext = self._get_extension_from_mime(resource.mime_type)
        cache_file = self.cache_dir / f"{url_hash}{ext}"
        
        # Return cached file if exists
        if cache_file.exists():
            logger.debug(f"Using cached file for URL: {url}")
            return str(cache_file)
        
        # Download file
        logger.info(f"Downloading from URL: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status != 200:
                        raise ResourceProcessingError(
                            f"Failed to download file: HTTP {response.status}",
                            {"url": url, "status": response.status}
                        )
                    
                    # Check content length
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        self._validate_file_size(int(content_length), resource.mime_type)
                    
                    # Download to cache file
                    total_size = 0
                    with open(cache_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            total_size += len(chunk)
                            
                            # Check size during download
                            self._validate_file_size(total_size, resource.mime_type)
            
            logger.info(f"Downloaded {total_size} bytes to {cache_file}")
            return str(cache_file)
            
        except asyncio.TimeoutError:
            raise ResourceProcessingError(
                f"Download timeout for URL: {url}",
                {"url": url}
            )
        except aiohttp.ClientError as e:
            raise ResourceProcessingError(
                f"Network error downloading file: {str(e)}",
                {"url": url, "error": str(e)}
            )
        except Exception as e:
            # Clean up partial download
            if cache_file.exists():
                cache_file.unlink()
            raise ResourceProcessingError(
                f"Failed to download file: {str(e)}",
                {"url": url, "error": str(e)}
            )
    
    async def _process_base64(self, resource: ResourceInput) -> str:
        """
        Decode base64 data and save to file.
        """
        base64_data = resource.data
        
        # Remove data URL prefix if present (e.g., "data:image/png;base64,")
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
        
        # Decode base64
        try:
            decoded_data = base64.b64decode(base64_data)
        except Exception as e:
            raise ResourceProcessingError(
                f"Failed to decode base64 data: {str(e)}",
                {"error": str(e)}
            )
        
        # Validate size
        self._validate_file_size(len(decoded_data), resource.mime_type)
        
        # Create cache file
        data_hash = hashlib.md5(decoded_data).hexdigest()
        ext = self._get_extension_from_mime(resource.mime_type)
        cache_file = self.cache_dir / f"{data_hash}{ext}"
        
        # Return cached file if exists
        if cache_file.exists():
            logger.debug("Using cached base64 data")
            return str(cache_file)
        
        # Save to file
        try:
            with open(cache_file, 'wb') as f:
                f.write(decoded_data)
            
            logger.info(f"Decoded {len(decoded_data)} bytes to {cache_file}")
            return str(cache_file)
            
        except Exception as e:
            raise ResourceProcessingError(
                f"Failed to save decoded data: {str(e)}",
                {"error": str(e)}
            )
    
    def _validate_file_size(self, size: int, mime_type: str):
        """
        Validate file size based on mime type.
        
        Raises:
            ResourceProcessingError: If file size exceeds limits
        """
        category = mime_type.split('/')[0] if '/' in mime_type else None
        max_size = self.max_file_sizes.get(category) if category else None
        
        if max_size and size > max_size:
            raise ResourceProcessingError(
                f"File size {size} bytes exceeds maximum {max_size} bytes for {mime_type}",
                {"size": size, "max_size": max_size, "mime_type": mime_type}
            )
    
    def _get_extension_from_mime(self, mime_type: str) -> str:
        """
        Get file extension from MIME type.
        """
        return self.mime_type_map.get(mime_type.lower(), '')
    
    def cleanup_cache(self, max_age_hours: int = 24):
        """
        Clean up old cached files.
        
        Args:
            max_age_hours: Maximum age of cached files in hours
        """
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        deleted_count = 0
        for cache_file in self.cache_dir.iterdir():
            if cache_file.is_file():
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        cache_file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete cache file {cache_file}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} cached files")
    
    def get_cache_size(self) -> int:
        """
        Get total size of cached files in bytes.
        """
        total_size = 0
        for cache_file in self.cache_dir.iterdir():
            if cache_file.is_file():
                total_size += cache_file.stat().st_size
        return total_size
