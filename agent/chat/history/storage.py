"""
Storage module for agent chat history.

Handles file-based storage of AgentMessage objects with daily directory organization.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.history.message_paths import (
    build_message_filename,
    date_str_from_timestamp,
    parse_message_filename,
)

logger = logging.getLogger(__name__)


class MessageStorage:
    """
    Handles storage and retrieval of AgentMessage objects to/from markdown files.

    File naming convention: {utc_timestamp}_{message_id}_{sender}.md
    File structure (YAML):
        metadata:
          ...
        content:
          - ...
    """

    def __init__(self, history_root_path: str):
        """
        Initialize message storage.

        Args:
            history_root_path: Root path for history storage (e.g., workspace/projects/xxx/agent/history)
        """
        self.history_root_path = Path(history_root_path)
        self.history_root_path.mkdir(parents=True, exist_ok=True)

    def _get_date_dir_path(self, date: datetime, create: bool = True) -> Path:
        """
        Get the directory path for a specific date (yyyyMMdd format).

        Args:
            date: The date to get the directory for
            create: Whether to create the directory if missing

        Returns:
            Path to the date-specific directory
        """
        date_str = date_str_from_timestamp(date)
        dir_path = self.history_root_path / date_str
        if create:
            dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def _list_date_dirs(self, reverse: bool = False) -> List[Path]:
        if not self.history_root_path.exists():
            return []
        date_dirs = [d for d in self.history_root_path.iterdir() if d.is_dir()]
        date_dirs.sort(key=lambda d: d.name, reverse=reverse)
        return date_dirs

    def _get_file_timestamp(self, file_path: Path) -> int:
        parsed = parse_message_filename(file_path)
        return parsed.timestamp if parsed else 0

    def _get_file_path(self, message: AgentMessage) -> Path:
        """
        Generate the file path for a message.

        File naming: {utc_timestamp}_{message_id}_{sender}.md

        Args:
            message: The AgentMessage to generate path for

        Returns:
            Path to the message file
        """
        date_dir = self._get_date_dir_path(message.timestamp, create=True)
        sender = message.sender_name or message.sender_id or "unknown"
        filename = build_message_filename(message.timestamp, message.message_id, sender)
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
            "message_type": message.message_type.value if hasattr(message.message_type, "value") else str(message.message_type),
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "timestamp": message.timestamp.isoformat(),
            "metadata": message.metadata or {},
        }

    def _structured_content_to_dict(self, content) -> Dict[str, Any]:
        """
        Convert StructureContent to dictionary for YAML serialization.

        Args:
            content: The StructureContent to convert

        Returns:
            Dictionary representation of the content
        """
        if hasattr(content, "to_dict"):
            return content.to_dict()

        result = {"content_type": str(content.content_type)}
        if hasattr(content, "text"):
            result["text"] = content.text
        if hasattr(content, "data"):
            result["data"] = content.data
        if hasattr(content, "metadata"):
            result["metadata"] = content.metadata
        return result

    def _normalize_loaded_payload(self, documents: List[Any]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        content_list: List[Any] = []

        if not documents:
            return {"metadata": metadata, "content": content_list}

        if len(documents) == 1:
            doc = documents[0]
            if isinstance(doc, dict):
                metadata = doc.get("metadata") or {}
                content_list = doc.get("content") or []
                if not metadata and any(
                    key in doc for key in ("message_id", "sender_id", "timestamp", "message_type")
                ):
                    metadata = {k: v for k, v in doc.items() if k != "content"}
            elif isinstance(doc, list):
                content_list = doc
        else:
            first = documents[0]
            second = documents[1]
            if isinstance(first, dict):
                metadata = first.get("metadata")
                if metadata is None:
                    metadata = {k: v for k, v in first.items() if k != "metadata"}
            if isinstance(second, dict) and "content" in second:
                content_list = second.get("content") or []
            elif isinstance(second, list):
                content_list = second

        if not isinstance(metadata, dict):
            metadata = {}
        if not isinstance(content_list, list):
            content_list = []

        return {"metadata": metadata, "content": content_list}

    def _load_payload(self, file_path: Path) -> Optional[Dict[str, Any]]:
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read message file {file_path}: {e}")
            return None

        try:
            documents = list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML in {file_path}: {e}")
            return {"metadata": {}, "content": []}

        return self._normalize_loaded_payload(documents)

    def _coerce_content_list(self, content: Any) -> List[Any]:
        if isinstance(content, list):
            return content
        return []

    def _write_payload(self, file_path: Path, metadata: Dict[str, Any], content_list: List[Any]) -> None:
        payload = {
            "metadata": metadata,
            "content": content_list,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def _find_message_file_in_dir(self, date_dir: Path, message_id: str) -> Optional[Path]:
        if not date_dir.exists():
            return None
        matches = list(date_dir.glob(f"*_{message_id}_*.md"))
        if not matches:
            return None
        matches.sort(key=self._get_file_timestamp)
        return matches[-1]

    def find_message_file(self, message_id: str, date: Optional[datetime] = None) -> Optional[Path]:
        if date is not None:
            date_dir = self._get_date_dir_path(date, create=False)
            found = self._find_message_file_in_dir(date_dir, message_id)
            if found:
                return found

        for date_dir in self._list_date_dirs(reverse=True):
            found = self._find_message_file_in_dir(date_dir, message_id)
            if found:
                return found
        return None

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
        existing_path = self.find_message_file(message.message_id, message.timestamp)
        file_path = existing_path or self._get_file_path(message)

        message_dict = self._message_to_dict(message)

        content_list: List[Dict[str, Any]] = []
        for content in message.structured_content or []:
            try:
                content_list.append(self._structured_content_to_dict(content))
            except Exception as e:
                logger.warning(f"Failed to convert content to dict: {e}")
                content_list.append({
                    "content_type": str(content.content_type),
                    "error": str(e),
                })

        existing_payload = self._load_payload(file_path) if file_path.exists() else None
        existing_metadata = None
        existing_content = []
        if existing_payload:
            existing_metadata = existing_payload.get("metadata")
            existing_content = self._coerce_content_list(existing_payload.get("content"))

        if append_content and existing_content:
            content_list = existing_content + content_list

        metadata = dict(message_dict)
        if append_content and isinstance(existing_metadata, dict) and existing_metadata:
            metadata.update(existing_metadata)

        if metadata.get("message_id") is None:
            metadata["message_id"] = message.message_id

        try:
            self._write_payload(file_path, metadata, content_list)
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
        payload = self._load_payload(file_path)
        if payload is None:
            return None
        payload["_file_path"] = str(file_path)
        payload["_file_mtime"] = os.path.getmtime(file_path)
        return payload

    def list_message_files(self, date: datetime) -> List[Path]:
        """
        List all message files for a specific date.

        Args:
            date: The date to list messages for

        Returns:
            List of file paths, sorted by timestamp (from filename)
        """
        date_dir = self._get_date_dir_path(date, create=False)
        if not date_dir.exists():
            return []

        files = list(date_dir.glob("*.md"))
        files.sort(key=self._get_file_timestamp)
        return files

    def list_all_message_files(self) -> List[Path]:
        files: List[Path] = []
        for date_dir in self._list_date_dirs():
            files.extend(date_dir.glob("*.md"))
        files.sort(key=self._get_file_timestamp)
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
        for date_dir in self._list_date_dirs(reverse=True):
            files = list(date_dir.glob("*.md"))
            if not files:
                continue

            files.sort(key=self._get_file_timestamp, reverse=True)
            for file_path in files:
                parsed = parse_message_filename(file_path)
                if parsed:
                    return {
                        "message_id": parsed.message_id,
                        "timestamp": parsed.timestamp,
                        "file_path": str(file_path),
                    }

        return None
