"""
ComfyUI Config QML Model

Provides a QML data model for ComfyUI plugin configuration.
Extends PluginConfigQMLModel with workflow management capabilities.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from PySide6.QtCore import Slot, Signal, Property

from server.plugins.plugin_config_qml_model import PluginConfigQMLModel

logger = logging.getLogger(__name__)


class ComfyUIConfigQMLModel(PluginConfigQMLModel):
    """
    QML data model for ComfyUI plugin configuration.

    Extends PluginConfigQMLModel with:
    - Workflow management (load, save, list)
    - Server connection settings
    - Performance settings
    """

    # Signals for workflow operations
    workflows_changed = Signal()
    workflow_saved = Signal(str)  # workflow_name
    workflow_error = Signal(str)  # error_message

    # ToolType to workflow name mapping
    TOOLTYPE_WORKFLOW_MAP = {
        "text2image": "text2image",
        "image2image": "image2image",
        "image2video": "image2video",
        "text2video": "text2video",
        "speak2video": "speak2video",
        "text2speak": "text2speak",
        "text2music": "text2music",
    }

    def __init__(
        self,
        plugin_info: Dict[str, Any],
        config_schema: Optional[Dict[str, Any]] = None,
        server_config: Optional[Dict[str, Any]] = None,
        workspace_path: Optional[str] = None,
        server_name: Optional[str] = None,
        parent=None
    ):
        """
        Initialize the ComfyUI QML config model.

        Args:
            plugin_info: Plugin metadata dictionary
            config_schema: Configuration schema with field definitions
            server_config: Existing server configuration (for editing)
            workspace_path: Path to workspace directory
            server_name: Name of the server instance
            parent: Parent QObject
        """
        super().__init__(plugin_info, config_schema, server_config, parent)

        self._workspace_path = Path(workspace_path) if workspace_path else None
        self._server_name = server_name or (server_config.get('name', '') if server_config else '')

        # Workflow directories
        self._builtin_workflows_dir = Path(__file__).parent.parent / "workflows"
        if self._workspace_path and self._server_name:
            self._workspace_workflows_dir = self._workspace_path / "servers" / self._server_name / "workflows"
            self._workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._workspace_workflows_dir = None

        self._workflows: List[Dict[str, Any]] = []
        self._load_workflows()

    # ─────────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────────

    @Property("QVariant", notify=workflows_changed)
    def workflows(self) -> List[Dict[str, Any]]:
        """Get list of workflows."""
        return self._workflows

    @Property(int, notify=workflows_changed)
    def workflowCount(self) -> int:
        """Get number of workflows."""
        return len(self._workflows)

    # ─────────────────────────────────────────────────────────────
    # Workflow Management Slots
    # ─────────────────────────────────────────────────────────────

    @Slot(result="QVariant")
    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get list of all workflows."""
        return self._workflows

    @Slot(int, result="QVariant")
    def get_workflow_at(self, index: int) -> Dict[str, Any]:
        """Get workflow at specified index."""
        if 0 <= index < len(self._workflows):
            return self._workflows[index]
        return {}

    @Slot(str, result="QVariant")
    def get_workflow_by_type(self, workflow_type: str) -> Dict[str, Any]:
        """Get workflow by type."""
        for workflow in self._workflows:
            if workflow.get('type') == workflow_type:
                return workflow
        return {}

    @Slot(result="QVariant")
    def get_workflow_types(self) -> List[str]:
        """Get list of workflow types in order."""
        return list(self.TOOLTYPE_WORKFLOW_MAP.values())

    @Slot()
    def reload_workflows(self):
        """Reload workflows from disk."""
        self._load_workflows()
        self.workflows_changed.emit()

    @Slot(str, str, str, result=bool)
    def save_workflow_config(
        self,
        workflow_type: str,
        name: str,
        node_mapping_json: str
    ) -> bool:
        """
        Save workflow configuration.

        Args:
            workflow_type: Workflow type (e.g., "text2image")
            name: Workflow display name
            node_mapping_json: JSON string of node mappings

        Returns:
            True if saved successfully
        """
        if not self._workspace_workflows_dir:
            self.workflow_error.emit("No workspace directory available")
            return False

        try:
            node_mapping = json.loads(node_mapping_json) if node_mapping_json else {}
        except json.JSONDecodeError as e:
            self.workflow_error.emit(f"Invalid node mapping JSON: {e}")
            return False

        target_file = self._workspace_workflows_dir / f"{workflow_type}.json"

        # Load existing workflow data or create new
        workflow_data = {}
        if target_file.exists():
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing workflow: {e}")

        # Ensure basic structure
        if 'prompt' not in workflow_data:
            workflow_data['prompt'] = {}
        if 'extra' not in workflow_data:
            workflow_data['extra'] = {}

        # Update filmeto config
        workflow_data['filmeto'] = {
            'name': name,
            'type': workflow_type,
            'description': f"Workflow for {workflow_type}",
            'node_mapping': node_mapping
        }

        try:
            self._workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)

            self._load_workflows()
            self.workflows_changed.emit()
            self.workflow_saved.emit(workflow_type)
            return True

        except Exception as e:
            error_msg = f"Failed to save workflow: {e}"
            logger.error(error_msg)
            self.workflow_error.emit(error_msg)
            return False

    @Slot(str, str, result=bool)
    def save_workflow_json(self, workflow_type: str, json_content: str) -> bool:
        """
        Save workflow JSON content directly.

        Args:
            workflow_type: Workflow type
            json_content: Full JSON content of the workflow

        Returns:
            True if saved successfully
        """
        if not self._workspace_workflows_dir:
            self.workflow_error.emit("No workspace directory available")
            return False

        # Validate JSON
        try:
            json.loads(json_content)
        except json.JSONDecodeError as e:
            self.workflow_error.emit(f"Invalid JSON: {e}")
            return False

        target_file = self._workspace_workflows_dir / f"{workflow_type}.json"

        try:
            self._workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(json_content)

            self._load_workflows()
            self.workflows_changed.emit()
            self.workflow_saved.emit(workflow_type)
            return True

        except Exception as e:
            error_msg = f"Failed to save workflow JSON: {e}"
            logger.error(error_msg)
            self.workflow_error.emit(error_msg)
            return False

    @Slot(str, result="QVariant")
    def get_workflow_json(self, workflow_type: str) -> Dict[str, Any]:
        """
        Get workflow JSON content for editing.

        Args:
            workflow_type: Workflow type

        Returns:
            Dict with 'content', 'path', and 'exists' keys
        """
        result = {'content': '', 'path': '', 'exists': False}

        # Find workflow file
        workflow_file = None

        # Try workspace first
        if self._workspace_workflows_dir:
            ws_file = self._workspace_workflows_dir / f"{workflow_type}.json"
            if ws_file.exists():
                workflow_file = ws_file

        # Fallback to builtin
        if not workflow_file:
            builtin_file = self._builtin_workflows_dir / f"{workflow_type}.json"
            if builtin_file.exists():
                workflow_file = builtin_file

        if not workflow_file or not workflow_file.exists():
            return result

        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Format JSON
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)

            result['content'] = formatted
            result['path'] = str(workflow_file)
            result['exists'] = True
            return result

        except Exception as e:
            logger.error(f"Failed to load workflow JSON: {e}")
            return result

    @Slot(str, result="QVariant")
    def get_workflow_nodes(self, workflow_type: str) -> List[Dict[str, Any]]:
        """
        Get list of nodes from a workflow for configuration.

        Args:
            workflow_type: Workflow type

        Returns:
            List of node info dicts with 'id' and 'class_type'
        """
        workflow_data = self._load_workflow_data(workflow_type)
        if not workflow_data:
            return []

        nodes = []

        # Extract prompt graph
        prompt_data = None
        if isinstance(workflow_data, dict):
            if 'prompt' in workflow_data:
                prompt_data = workflow_data['prompt']
            else:
                prompt_data = workflow_data

        # Extract nodes
        if isinstance(prompt_data, dict):
            for node_id, node_data in prompt_data.items():
                if isinstance(node_data, dict) and 'class_type' in node_data:
                    nodes.append({
                        'id': node_id,
                        'class_type': node_data.get('class_type', 'Unknown')
                    })

        return nodes

    @Slot(str, result=str)
    def get_workflow_file_path(self, workflow_type: str) -> str:
        """Get the file path for a workflow type."""
        if self._workspace_workflows_dir:
            return str(self._workspace_workflows_dir / f"{workflow_type}.json")
        return ""

    # ─────────────────────────────────────────────────────────────
    # Internal Methods
    # ─────────────────────────────────────────────────────────────

    def _load_workflows(self):
        """Load workflows from workspace and builtin directories."""
        self._workflows = []
        loaded_workflows = {}  # workflow_name -> workflow_entry

        # Load from workspace directory first (takes priority)
        if self._workspace_workflows_dir and self._workspace_workflows_dir.exists():
            self._load_workflows_from_dir(self._workspace_workflows_dir, loaded_workflows, is_builtin=False)

        # Load from builtin directory (templates, only if not already loaded)
        if self._builtin_workflows_dir and self._builtin_workflows_dir.exists():
            self._load_workflows_from_dir(self._builtin_workflows_dir, loaded_workflows, is_builtin=True)

        # Convert dict to list, sorted by ToolType order
        for workflow_type in self.TOOLTYPE_WORKFLOW_MAP.values():
            if workflow_type in loaded_workflows:
                self._workflows.append(loaded_workflows[workflow_type])

        # Add any remaining workflows not in standard order
        for workflow_name, workflow_entry in loaded_workflows.items():
            if workflow_name not in self.TOOLTYPE_WORKFLOW_MAP.values():
                self._workflows.append(workflow_entry)

    def _load_workflows_from_dir(
        self,
        workflows_dir: Path,
        loaded_workflows: Dict[str, Dict],
        is_builtin: bool
    ):
        """Load workflows from a specific directory."""
        # Load workflows for each ToolType
        for workflow_type in self.TOOLTYPE_WORKFLOW_MAP.values():
            workflow_file = workflows_dir / f"{workflow_type}.json"

            if not workflow_file.exists():
                continue

            # Skip if already loaded from workspace
            if workflow_type in loaded_workflows and not is_builtin:
                continue

            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)

                filmeto_config = workflow_data.get('filmeto', {})

                if filmeto_config:
                    workflow_entry = {
                        'name': filmeto_config.get('name', workflow_type.replace('_', ' ').title()),
                        'type': filmeto_config.get('type', workflow_type),
                        'description': filmeto_config.get('description', f"Workflow for {workflow_type}"),
                        'file_path': str(workflow_file),
                        'node_mapping': filmeto_config.get('node_mapping', {}),
                        'is_builtin': is_builtin
                    }
                else:
                    workflow_entry = {
                        'name': workflow_type.replace('_', ' ').title(),
                        'type': workflow_type,
                        'file_path': str(workflow_file),
                        'description': f"Workflow for {workflow_type} (needs configuration)",
                        'is_builtin': is_builtin
                    }

                loaded_workflows[workflow_type] = workflow_entry

            except Exception as e:
                logger.error(f"Failed to load workflow {workflow_file}: {e}")

        # Load any additional workflow files
        for workflow_file in workflows_dir.glob("*.json"):
            workflow_name = workflow_file.stem

            if workflow_name in loaded_workflows:
                continue

            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)

                filmeto_config = workflow_data.get('filmeto', {})

                if filmeto_config:
                    workflow_entry = {
                        'name': filmeto_config.get('name', workflow_name.replace('_', ' ').title()),
                        'type': filmeto_config.get('type', 'custom'),
                        'description': filmeto_config.get('description', "Custom workflow"),
                        'file_path': str(workflow_file),
                        'node_mapping': filmeto_config.get('node_mapping', {}),
                        'is_builtin': is_builtin
                    }
                else:
                    workflow_entry = {
                        'name': workflow_name.replace('_', ' ').title(),
                        'type': 'custom',
                        'file_path': str(workflow_file),
                        'description': "Custom workflow (needs configuration)",
                        'is_builtin': is_builtin
                    }

                loaded_workflows[workflow_name] = workflow_entry

            except Exception as e:
                logger.error(f"Failed to load workflow {workflow_file}: {e}")

    def _load_workflow_data(self, workflow_type: str) -> Optional[Dict]:
        """Load workflow data from file."""
        # Try workspace first
        if self._workspace_workflows_dir:
            ws_file = self._workspace_workflows_dir / f"{workflow_type}.json"
            if ws_file.exists():
                try:
                    with open(ws_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load workflow: {e}")

        # Try builtin
        builtin_file = self._builtin_workflows_dir / f"{workflow_type}.json"
        if builtin_file.exists():
            try:
                with open(builtin_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load builtin workflow: {e}")

        return None

    def _initialize_default_workflows(self):
        """Initialize default workflow files in workspace directory."""
        if not self._workspace_workflows_dir:
            return

        self._workspace_workflows_dir.mkdir(parents=True, exist_ok=True)

        for workflow_type in self.TOOLTYPE_WORKFLOW_MAP.values():
            workflow_file = self._workspace_workflows_dir / f"{workflow_type}.json"

            if not workflow_file.exists():
                # Try to copy from builtin templates
                builtin_file = self._builtin_workflows_dir / f"{workflow_type}.json"
                if builtin_file.exists():
                    try:
                        import shutil
                        shutil.copy2(builtin_file, workflow_file)
                        continue
                    except Exception as e:
                        logger.error(f"Failed to copy builtin workflow: {e}")

                # Create empty workflow
                empty_workflow = {
                    "prompt": {},
                    "extra": {},
                    "filmeto": {
                        "name": workflow_type.replace('_', ' ').title(),
                        "type": workflow_type,
                        "description": f"Workflow for {workflow_type}",
                        "node_mapping": {}
                    }
                }
                try:
                    with open(workflow_file, 'w', encoding='utf-8') as f:
                        json.dump(empty_workflow, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"Failed to create default workflow: {e}")