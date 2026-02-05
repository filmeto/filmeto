"""
Storage module for agent chat history.

Handles file-based storage of AgentMessage objects with daily directory organization.
"""

import os
import yaml
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

from agent.chat.agent_chat_message import AgentMessage

logger = logging.getLogger(__name__)


class MessageStorage:
    """
    Handles storage and retrieval of AgentMessage objects to/from markdown files.

    File naming convention: {utc_timestamp}_{message_id}_{sender}.md
    File structure:
        ---
        metadata: {...}
        ---
        content:
          - {...}
          - {...}
    """

    def __init__(self, history_root_path: str):
        """
        Initialize message storage.

        Args:
            history_root_path: Root path for history storage (e.g., workspace/projects/xxx/agent/history)
        """
        self.history_root_path = Path(history_root_path)
        self.history_root_path.mkdir(parents=True, exist_ok=True)

    def _get_date_dir_path(self, date: datetime) -> Path:
        """
        Get the directory path for a specific date (yyyyMMdd format).

        Args:
            date: The date to get the directory for

        Returns:
            Path to the date-specific directory
        """
        date_str = date.strftime("%Y%m%d")
        dir_path = self.history_root_path / date_str
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def _get_file_path(self, message: AgentMessage) -> Path:
        """
        Generate the file path for a message.

        File naming: {utc_timestamp}_{message_id}_{sender}.md

        Args:
            message: The AgentMessage to generate path for

        Returns:
            Path to the message file
        """
        date_dir = self._get_date_dir_path(message.timestamp)

        # Get UTC timestamp in seconds
        utc_timestamp = int(message.timestamp.timestamp())

        # Sanitize sender name for filename
        sender = message.sender_name or message.sender_id
        safe_sender = sender.replace(" ", "_").replace("/", "_").replace("\\", "_")

        filename = f"{utc_timestamp}_{message.message_id}_{safe_sender}.md"
        return date_dir / filename

    def _message_to_dict(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Convert AgentMessage to dictionary for YAML serialization.

        Args:
            message: The AgentMessage to convert

        Returns:
            Dictionary representation of the message
        """
        return {
            "message_id": message.message_id,
            "message_type": message.message_type.value if hasattr(message.message_type, 'value') else str(message.message_type),
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "timestamp": message.timestamp.isoformat(),
            "metadata": message.metadata or {}
        }

    def _structured_content_to_dict(self, content) -> Dict[str, Any]:
        """
        Convert StructureContent to dictionary for YAML serialization.

        Args:
            content: The StructureContent to convert

        Returns:
            Dictionary representation of the content
        """
        # Try to use to_dict method if available
        if hasattr(content, 'to_dict'):
            return content.to_dict()

        # Fallback to basic serialization
        result = {
            "content_type": str(content.content_type)
        }
        if hasattr(content, 'text'):
            result['text'] = content.text
        if hasattr(content, 'data'):
            result['data'] = content.data
        if hasattr(content, 'metadata'):
            result['metadata'] = content.metadata

        return result

    def save_message(self, message: AgentMessage, append_content: bool = True) -> Path:
        """
        Save an AgentMessage to a file.

        If append_content is True and the file exists, only append new content entries.
        Otherwise, overwrite the entire file.

        Args:
            message: The AgentMessage to save
            append_content: Whether to append content to existing file

        Returns:
            Path to the saved file
        """
        file_path = self._get_file_path(message)

        # Convert message metadata to dict
        message_dict = self._message_to_dict(message)

        # Convert structured content to list of dicts
        content_list = []
        for content in message.structured_content:
            try:
                content_list.append(self._structured_content_to_dict(content))
            except Exception as e:
                logger.warning(f"Failed to convert content to dict: {e}")
                content_list.append({
                    "content_type": str(content.content_type),
                    "error": str(e)
                })

        if append_content and file_path.exists():
            # Read existing content and append
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse existing YAML content list
                if '\n---\ncontent:\n' in content:
                    parts = content.split('\n---\ncontent:\n')
                    if len(parts) == 2:
                        existing_yaml = parts[1]
                        try:
                            existing_content = yaml.safe_load(existing_yaml) or []
                            if isinstance(existing_content, list):
                                content_list = existing_content + content_list
                        except yaml.YAMLError as e:
                            logger.warning(f"Failed to parse existing content YAML: {e}")
            except Exception as e:
                logger.warning(f"Failed to read existing file for appending: {e}")

        # Build YAML content
        yaml_content = {
            "metadata": message_dict,
            "content": content_list
        }

        # Write to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("---\n")
                f.write(f"metadata:\n")
                yaml.dump(message_dict, f, default_flow_style=False, allow_unicode=True)
                f.write("\n---\n")
                f.write("content:\n")
                yaml.dump(content_list, f, default_flow_style=False, allow_unicode=True)

            logger.debug(f"Saved message to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save message to {file_path}: {e}")
            raise

        return file_path

    def load_message(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load a message from a file.

        Args:
            file_path: Path to the message file

        Returns:
            Dictionary containing metadata and content, or None if loading fails
        """
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the YAML content
            parts = content.split('\n---\n')

            result = {}

            # Parse metadata section
            for part in parts:
                if part.strip().startswith('metadata:'):
                    try:
                        result['metadata'] = yaml.safe_load(part)
                    except yaml.YAMLError as e:
                        logger.warning(f"Failed to parse metadata YAML: {e}")
                        result['metadata'] = {}
                elif part.strip().startswith('content:'):
                    try:
                        result['content'] = yaml.safe_load(part)
                    except yaml.YAMLError as e:
                        logger.warning(f"Failed to parse content YAML: {e}")
                        result['content'] = []

            # Add file metadata
            result['_file_path'] = str(file_path)
            result['_file_mtime'] = os.path.getmtime(file_path)

            return result

        except Exception as e:
            logger.error(f"Failed to load message from {file_path}: {e}")
            return None

    def list_message_files(self, date: datetime) -> List[Path]:
        """
        List all message files for a specific date.

        Args:
            date: The date to list messages for

        Returns:
            List of file paths, sorted by timestamp (from filename)
        """
        date_dir = self._get_date_dir_path(date)

        if not date_dir.exists():
            return []

        files = list(date_dir.glob("*.md"))

        # Sort by timestamp in filename (first part before first underscore)
        def get_timestamp(file_path: Path) -> int:
            try:
                name = file_path.stem
                timestamp_str = name.split('_')[0]
                return int(timestamp_str)
            except (ValueError, IndexError):
                return 0

        files.sort(key=get_timestamp)

        return files

    def delete_message(self, file_path: Path) -> bool:
        """
        Delete a message file.

        Args:
            file_path: Path to the message file

        Returns:
            True if deleted, False otherwise
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted message file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete message file {file_path}: {e}")
            return False

    def get_latest_message_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the most recent message.

        Returns:
            Dictionary with message_id, timestamp, and file_path, or None if no messages exist
        """
        # Scan all date directories
        date_dirs = sorted([d for d in self.history_root_path.iterdir() if d.is_dir()], reverse=True)

        for date_dir in date_dirs:
            files = list(date_dir.glob("*.md"))
            if not files:
                continue

            # Sort by timestamp in filename
            def get_timestamp(file_path: Path) -> int:
                try:
                    name = file_path.stem
                    timestamp_str = name.split('_')[0]
                    return int(timestamp_str)
                except (ValueError, IndexError):
                    return 0

            files.sort(key=get_timestamp, reverse=True)

            if files:
                latest_file = files[0]
                try:
                    name = latest_file.stem
                    parts = name.split('_')
                    if len(parts) >= 2:
                        timestamp = int(parts[0])
                        message_id = parts[1]

                        return {
                            "message_id": message_id,
                            "timestamp": timestamp,
                            "file_path": str(latest_file)
                        }
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse filename {latest_file.name}: {e}")
                    continue

        return None
