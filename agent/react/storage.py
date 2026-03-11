import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ReactStorage:
    """
    Handles file-based storage for ReAct history and config.

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
        self.history_file = self.storage_path / "history.jsonl"
        self.config_file = self.storage_path / "config.json"

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
