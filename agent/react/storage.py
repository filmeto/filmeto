import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
from .types import CheckpointData

logger = logging.getLogger(__name__)


class ReactStorage:
    """
    Handles file-based storage for ReAct checkpoints and related data.

    Uses atomic file operations for data safety.
    """

    def __init__(self, project_name: str, react_type: str, workspace_root: str = "workspace"):
        self.project_name = project_name
        self.react_type = react_type
        self.workspace_root = Path(workspace_root)

        # Define the storage path
        self.storage_path = (
            self.workspace_root / "projects" / project_name / "agent" / "react" / react_type
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Define file paths
        self.checkpoint_file = self.storage_path / "checkpoint.json"
        self.history_file = self.storage_path / "history.jsonl"
        self.config_file = self.storage_path / "config.json"

    def save_checkpoint(self, checkpoint_data: CheckpointData) -> None:
        """
        Save checkpoint data to file atomically.
        """
        checkpoint_data.updated_at = time.time()
        temp_file = self.checkpoint_file.with_suffix('.tmp')

        try:
            # Write to temporary file first
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data.__dict__, f, indent=2, ensure_ascii=False)

            # Atomic replace (POSIX systems)
            temp_file.replace(self.checkpoint_file)
        except (IOError, OSError) as e:
            logger.error(f"Failed to save checkpoint to {self.checkpoint_file}: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise

    def load_checkpoint(self) -> Optional[CheckpointData]:
        """
        Load checkpoint data from file.
        """
        if not self.checkpoint_file.exists():
            return None

        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ['run_id', 'step_id', 'status', 'messages', 'pending_user_messages']
            for field in required_fields:
                if field not in data:
                    logger.error(f"Checkpoint missing required field: {field}")
                    return None

            # Create CheckpointData instance from loaded data
            return CheckpointData(
                run_id=data['run_id'],
                step_id=data['step_id'],
                status=data['status'],
                messages=data['messages'],
                pending_user_messages=data['pending_user_messages'],
                last_tool_calls=data.get('last_tool_calls'),
                last_tool_results=data.get('last_tool_results'),
                todo_state=data.get('todo_state'),
                todo_patches=data.get('todo_patches'),
                created_at=data.get('created_at', time.time()),
                updated_at=data.get('updated_at', time.time())
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to load checkpoint from {self.checkpoint_file}: {e}")
            return None

    def append_to_history(self, event: dict) -> None:
        """
        Append an event to the history file.
        """
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
        except (IOError, OSError) as e:
            logger.error(f"Failed to append to history: {e}")

    def clear_history(self) -> None:
        """
        Clear the history file.
        """
        if self.history_file.exists():
            try:
                self.history_file.unlink()
            except (IOError, OSError) as e:
                logger.error(f"Failed to clear history: {e}")

    def save_config(self, config: dict) -> None:
        """
        Save configuration to file atomically.
        """
        temp_file = self.config_file.with_suffix('.tmp')

        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.config_file)
        except (IOError, OSError) as e:
            logger.error(f"Failed to save config: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise

    def load_config(self) -> Optional[dict]:
        """
        Load configuration from file.
        """
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load config: {e}")
            return None

    def delete_checkpoint(self) -> bool:
        """
        Delete the checkpoint file.
        """
        if self.checkpoint_file.exists():
            try:
                self.checkpoint_file.unlink()
                return True
            except (IOError, OSError) as e:
                logger.error(f"Failed to delete checkpoint: {e}")
                return False
        return False
