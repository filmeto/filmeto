"""
Plugin Config QML Model

Provides a QML data model for plugin configuration.
This model exposes configuration data and schema to QML for data binding.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot

from server.plugins.ability_model_config import (
    ABILITY_MODELS_KEY,
    normalize_ability_models_raw,
    normalize_catalog_item,
)
from server.plugins.ability_models_qml_model import AbilityModelsConfigModel

logger = logging.getLogger(__name__)


class PluginConfigQMLModel(QObject):
    """
    QML data model for plugin configuration.

    Provides configuration data binding between Python and QML.
    This model exposes:
    - Plugin metadata (name, description)
    - Configuration schema (field definitions)
    - Configuration values (get/set methods)

    Usage in QML:
        TextField {
            text: _pluginConfigModel.get_config_value("api_key")
            onTextChanged: _pluginConfigModel.set_config_value("api_key", text)
        }
    """

    # Signals
    config_changed = Signal()
    values_changed = Signal()
    validation_error = Signal(str)

    def __init__(
        self,
        plugin_info: Dict[str, Any],
        config_schema: Optional[Dict[str, Any]] = None,
        server_config: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        """
        Initialize the QML config model.

        Args:
            plugin_info: Plugin metadata dictionary
            config_schema: Configuration schema with field definitions
            server_config: Existing server configuration (for editing)
            parent: Parent QObject
        """
        super().__init__(parent)

        self._plugin_info = plugin_info or {}
        self._config_schema = config_schema or {"fields": []}
        self._server_config = server_config or {}
        self._config_values: Dict[str, Any] = {}
        self._ability_models_model: Optional[AbilityModelsConfigModel] = None

        self._init_values()
        self._init_ability_models_from_plugin()

    def _init_values(self):
        """Initialize config values from schema defaults and existing config."""
        # Get fields from schema
        fields = self._config_schema.get("fields", [])

        # Set default values from schema
        for field in fields:
            name = field.get("name")
            if name:
                default = field.get("default")
                self._config_values[name] = default

        # Override with existing server config
        config = self._server_config.get("config", {})
        params = self._server_config.get("parameters", {})
        merged = {**params, **config}

        for key, value in merged.items():
            if value is not None:
                self._config_values[key] = value

        # Legacy YAML may store api_key only on ServerConfig (top-level), not inside parameters.
        legacy_api_key = self._server_config.get("api_key")
        if legacy_api_key and not self._config_values.get("api_key"):
            self._config_values["api_key"] = legacy_api_key

    def _persist_ability_models(self):
        if not self._ability_models_model:
            return
        self._config_values[ABILITY_MODELS_KEY] = self._ability_models_model.serialize()
        self.config_changed.emit()

    def _build_ability_models_catalog(self) -> List[Dict[str, Any]]:
        raw = self._plugin_info.get("ability_models_catalog") or []
        out: List[Dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            c = normalize_catalog_item(item)
            if c:
                out.append(c)
        return out

    def _init_ability_models_from_plugin(self):
        catalog = self._build_ability_models_catalog()
        if not catalog:
            return
        saved = normalize_ability_models_raw(self._config_values.get(ABILITY_MODELS_KEY))
        self._ability_models_model = AbilityModelsConfigModel(
            parent=self, on_persist=self._persist_ability_models
        )
        self._ability_models_model.load(catalog, saved)
        self.ability_models_model_changed.emit()

    # ─────────────────────────────────────────────────────────────
    # Properties (exposed to QML)
    # ─────────────────────────────────────────────────────────────

    ability_models_model_changed = Signal()

    def _get_ability_models_model(self):
        return self._ability_models_model

    abilityModelsModel = Property(
        QObject,
        _get_ability_models_model,
        notify=ability_models_model_changed,
    )

    @Property(str, constant=True)
    def plugin_name(self) -> str:
        """Get plugin name."""
        return self._plugin_info.get("name", "Unknown Plugin")

    @Property(str, constant=True)
    def plugin_version(self) -> str:
        """Get plugin version."""
        return self._plugin_info.get("version", "")

    @Property(str, constant=True)
    def plugin_description(self) -> str:
        """Get plugin description."""
        return self._plugin_info.get("description", "")

    @Property("QVariant", constant=True)
    def config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return self._config_schema

    @Property("QVariant", constant=True)
    def fields(self) -> List[Dict[str, Any]]:
        """Get list of configuration fields from schema."""
        return self._config_schema.get("fields", [])

    # ─────────────────────────────────────────────────────────────
    # Slots (callable from QML)
    # ─────────────────────────────────────────────────────────────

    @Slot(str, result="QVariant")
    def get_config_value(self, key: str) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key name

        Returns:
            Configuration value or None if not found
        """
        return self._config_values.get(key)

    @Slot(str, "QVariant")
    def set_config_value(self, key: str, value: Any):
        """
        Set a configuration value.

        Args:
            key: Configuration key name
            value: New value
        """
        if self._config_values.get(key) != value:
            self._config_values[key] = value
            self.config_changed.emit()
            self.values_changed.emit()

    @Slot(result="QVariant")
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Get all configuration values as a dictionary.

        Returns:
            Dictionary of all configuration values
        """
        result = dict(self._config_values)
        if self._ability_models_model:
            result[ABILITY_MODELS_KEY] = self._ability_models_model.serialize()
        return result

    @Slot(result=bool)
    def validate(self) -> bool:
        """
        Validate the current configuration.

        Returns:
            True if valid, False otherwise
        """
        fields = self._config_schema.get("fields", [])

        for field in fields:
            name = field.get("name")
            required = field.get("required", False)

            if required:
                value = self._config_values.get(name)
                if value is None or value == "":
                    error_msg = f"{field.get('label', name)} is required"
                    self.validation_error.emit(error_msg)
                    return False

        return True

    @Slot(result=str)
    def get_validation_errors(self) -> str:
        """
        Get validation error messages.

        Returns:
            Combined error messages or empty string if valid
        """
        errors = []
        fields = self._config_schema.get("fields", [])

        for field in fields:
            name = field.get("name")
            required = field.get("required", False)
            label = field.get("label", name)

            if required:
                value = self._config_values.get(name)
                if value is None or value == "":
                    errors.append(f"{label} is required")

        return "\n".join(errors)

    @Slot(str, result="QVariant")
    def get_field_schema(self, field_name: str) -> Dict[str, Any]:
        """
        Get schema for a specific field.

        Args:
            field_name: Field name

        Returns:
            Field schema dictionary or empty dict if not found
        """
        fields = self._config_schema.get("fields", [])
        for field in fields:
            if field.get("name") == field_name:
                return field
        return {}

    @Slot(str, result=bool)
    def is_field_visible(self, field_name: str) -> bool:
        """
        Check if a field should be visible.
        This can be overridden in subclasses for conditional visibility.

        Args:
            field_name: Field name

        Returns:
            True if field should be visible
        """
        # Default implementation - all fields visible
        return True

    @Slot(str, result=bool)
    def is_field_enabled(self, field_name: str) -> bool:
        """
        Check if a field should be enabled.
        This can be overridden in subclasses for conditional enabling.

        Args:
            field_name: Field name

        Returns:
            True if field should be enabled
        """
        # Default implementation - all fields enabled
        return True

    # ─────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────

    def set_values(self, values: Dict[str, Any]):
        """
        Set multiple configuration values at once.

        Args:
            values: Dictionary of values to set
        """
        changed = False
        for key, value in values.items():
            if self._config_values.get(key) != value:
                self._config_values[key] = value
                changed = True

        if changed:
            self.config_changed.emit()
            self.values_changed.emit()

    def get_values(self) -> Dict[str, Any]:
        """
        Get a copy of all configuration values.

        Returns:
            Dictionary of all configuration values
        """
        return dict(self._config_values)

    def reset_to_defaults(self):
        """Reset all configuration values to their defaults."""
        fields = self._config_schema.get("fields", [])
        for field in fields:
            name = field.get("name")
            if name:
                default = field.get("default")
                self._config_values[name] = default

        self.config_changed.emit()
        self.values_changed.emit()


class BailianConfigQMLModel(PluginConfigQMLModel):
    """
    Specialized QML model for Bailian Server configuration.

    Adds support for:
    - Coding Plan conditional visibility
    - Model selection helpers
    """

    def __init__(
        self,
        plugin_info: Dict[str, Any],
        config_schema: Optional[Dict[str, Any]] = None,
        server_config: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(plugin_info, config_schema, server_config, parent)
        if (
            ABILITY_MODELS_KEY not in self._config_values
            or self._config_values.get(ABILITY_MODELS_KEY) is None
        ):
            from server.plugins.bailian_server.bailian_ability_catalog import (
                build_default_bailian_ability_models,
            )

            defaults = build_default_bailian_ability_models()
            self._config_values[ABILITY_MODELS_KEY] = defaults
            if self._ability_models_model:
                self._ability_models_model.load(
                    self._build_ability_models_catalog(), defaults
                )

    def _build_ability_models_catalog(self) -> List[Dict[str, Any]]:
        try:
            from server.plugins.bailian_server.bailian_ability_catalog import (
                build_bailian_ability_catalog,
            )

            return build_bailian_ability_catalog()
        except Exception as e:
            logger.warning("Bailian ability catalog unavailable: %s", e)
            return super()._build_ability_models_catalog()

    @Slot(result=bool)
    def is_coding_plan_enabled(self) -> bool:
        """Check if Coding Plan is enabled."""
        return bool(self._config_values.get("coding_plan_enabled", False))

    @Slot(result="QVariant")
    def get_available_models(self) -> List[str]:
        """Get list of available chat models."""
        # Try to get from models config
        try:
            from server.plugins.bailian_server.models_config import models_config
            return models_config.get_dashscope_models()
        except ImportError:
            # Fallback list
            return [
                "qwen-max",
                "qwen-plus",
                "qwen-turbo",
                "qwen-flash",
            ]

    @Slot(result="QVariant")
    def get_available_image_models(self) -> List[str]:
        """Get list of available image models."""
        return [
            "wanx2.1-t2i-turbo",
            "wanx2.1-t2i-plus",
            "wanx2.6-t2i-turbo",
            "wanx2.6-t2i-plus",
        ]

    @Slot(str, result=bool)
    def is_field_visible(self, field_name: str) -> bool:
        """
        Override visibility for Coding Plan API Key field.
        Only visible when Coding Plan is enabled.
        """
        if field_name == "coding_plan_api_key":
            return bool(self._config_values.get("coding_plan_enabled", False))
        return True

    @Slot(result="QVariant")
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Override to add computed values like models list.
        """
        result = super().get_config_dict()

        # Add provider
        result["provider"] = "dashscope"

        from server.plugins.ability_model_config import is_model_enabled_for_ability

        # Add available models
        default_model = result.get("default_model", "qwen-max")
        try:
            from server.plugins.bailian_server.models_config import models_config

            models = [
                m
                for m in models_config.get_dashscope_models()
                if is_model_enabled_for_ability(result, "chat_completion", m)
            ]
            if default_model and default_model not in models:
                models.insert(0, default_model)
            result["models"] = models
        except ImportError:
            result["models"] = [default_model] if default_model else []

        # Add Coding Plan config if enabled
        if result.get("coding_plan_enabled") and result.get("coding_plan_api_key"):
            try:
                from server.plugins.bailian_server.models_config import models_config

                result["coding_plan_endpoint"] = models_config.get_coding_plan_endpoint()
                all_cp = models_config.get_coding_plan_models(with_prefix=True)
                result["coding_plan_models"] = [
                    m
                    for m in all_cp
                    if is_model_enabled_for_ability(result, "chat_completion", m)
                ]
            except ImportError:
                pass

        return result


class ComfyUIConfigQMLModel(PluginConfigQMLModel):
    """
    Specialized QML model for ComfyUI Server configuration.

    Adds support for:
    - Workflow management (list, add, edit, configure)
    - ToolType to workflow mapping
    - Workflow JSON data handling
    """

    # Signals
    workflows_changed = Signal()
    workflow_saved = Signal(str)  # workflow_type
    workflow_error = Signal(str)  # error_message

    def __init__(
        self,
        plugin_info: Dict[str, Any],
        config_schema: Optional[Dict[str, Any]] = None,
        server_config: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(plugin_info, config_schema, server_config, parent)
        self._workflows: List[Dict[str, Any]] = []
        self._workspace_path: Optional[Path] = None
        self._server_name: str = server_config.get("name", "") if server_config else ""
        self._init_workspace_path()
        self._init_workflows()

    def _init_workspace_path(self):
        """Initialize workspace path from server config."""
        config = self._server_config.get("config", {}) if self._server_config else {}
        workspace = config.get("workspace_path")
        if workspace:
            self._workspace_path = Path(workspace)
        else:
            # Fallback to default workspace
            self._workspace_path = Path.home() / ".filmeto" / "workspace"

    def _init_workflows(self):
        """Initialize workflows from ability_models_catalog."""
        catalog = self._build_ability_models_catalog()
        self._workflows = []
        for item in catalog:
            ability = item.get("ability", "")
            model_id = item.get("model_id", "")
            label = item.get("label", "")
            self._workflows.append({
                "name": label or model_id.replace("_", " ").title(),
                "type": model_id,
                "ability": ability,
                "description": f"Workflow for {ability}",
                "enabled": True,
                "node_mapping": {},
            })
        self.workflows_changed.emit()

    def _get_workflow_file_path(self, workflow_type: str) -> Optional[Path]:
        """Get the file path for a workflow."""
        if not self._workspace_path or not self._server_name:
            return None
        workflows_dir = self._workspace_path / "servers" / self._server_name / "workflows"
        return workflows_dir / f"{workflow_type}.json"

    @Property("QVariant", notify=workflows_changed)
    def workflows(self) -> List[Dict[str, Any]]:
        """Get list of workflows."""
        return self._workflows

    @Slot(result="QVariant")
    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get list of workflows (callable from QML)."""
        return self._workflows

    @Slot(str, result="QVariant")
    def get_workflow_by_type(self, workflow_type: str) -> Optional[Dict[str, Any]]:
        """Get workflow by type."""
        for workflow in self._workflows:
            if workflow.get("type") == workflow_type:
                return workflow
        return None

    @Slot(int, result="QVariant")
    def get_workflow_at(self, index: int) -> Optional[Dict[str, Any]]:
        """Get workflow at index."""
        if 0 <= index < len(self._workflows):
            return self._workflows[index]
        return None

    @Slot(str, bool)
    def set_workflow_enabled(self, workflow_type: str, enabled: bool):
        """Enable/disable a workflow."""
        for workflow in self._workflows:
            if workflow.get("type") == workflow_type:
                workflow["enabled"] = enabled
                self.workflows_changed.emit()
                self.config_changed.emit()
                break

    @Slot(str, str, str)
    def update_workflow(self, workflow_type: str, name: str, description: str):
        """Update workflow metadata."""
        for workflow in self._workflows:
            if workflow.get("type") == workflow_type:
                workflow["name"] = name
                workflow["description"] = description
                self.workflows_changed.emit()
                self.config_changed.emit()
                break

    @Slot(str, result="QVariant")
    def get_workflow_json(self, workflow_type: str) -> Dict[str, Any]:
        """
        Get workflow JSON content.
        Returns dict with 'content' (str) and 'exists' (bool).
        """
        workflow_file = self._get_workflow_file_path(workflow_type)
        result = {"content": "", "exists": False}

        if workflow_file and workflow_file.exists():
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                result["content"] = content
                result["exists"] = True
            except Exception as e:
                logger.error(f"Failed to read workflow {workflow_type}: {e}")
                result["content"] = f"{{\"error\": \"{str(e)}\"}}"
        else:
            # Return empty workflow template
            workflow = self.get_workflow_by_type(workflow_type)
            name = workflow.get("name", workflow_type.replace("_", " ").title()) if workflow else workflow_type
            template = {
                "prompt": {},
                "extra": {},
                "filmeto": {
                    "name": name,
                    "type": workflow_type,
                    "description": f"Workflow for {workflow_type}",
                    "node_mapping": {}
                }
            }
            result["content"] = json.dumps(template, indent=2, ensure_ascii=False)

        return result

    @Slot(str, str, result=bool)
    def save_workflow_json(self, workflow_type: str, json_content: str) -> bool:
        """Save workflow JSON content."""
        workflow_file = self._get_workflow_file_path(workflow_type)
        if not workflow_file:
            self.workflow_error.emit("Workspace path not configured")
            return False

        try:
            workflow_file.parent.mkdir(parents=True, exist_ok=True)
            with open(workflow_file, 'w', encoding='utf-8') as f:
                f.write(json_content)
            self.workflow_saved.emit(workflow_type)
            self.config_changed.emit()
            return True
        except Exception as e:
            logger.error(f"Failed to save workflow {workflow_type}: {e}")
            self.workflow_error.emit(str(e))
            return False

    @Slot(str, result="QVariant")
    def get_workflow_nodes(self, workflow_type: str) -> List[Dict[str, Any]]:
        """
        Get list of nodes from a workflow for configuration.
        Returns list of node info dicts with id, type, and title.
        """
        result = self.get_workflow_json(workflow_type)
        content = result.get("content", "")
        nodes = []

        if not content:
            return nodes

        try:
            workflow_data = json.loads(content)
            prompt = workflow_data.get("prompt", {})

            for node_id, node_data in prompt.items():
                if isinstance(node_data, dict):
                    node_type = node_data.get("class_type", "")
                    node_inputs = node_data.get("inputs", {})
                    # Only include nodes with configurable inputs
                    if node_type and node_type not in ["Reroute", "Note"]:
                        nodes.append({
                            "id": str(node_id),
                            "type": node_type,
                            "title": node_inputs.get("title", node_type) if isinstance(node_inputs, dict) else node_type,
                        })
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse workflow JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting workflow nodes: {e}")

        return nodes

    @Slot(str, str, str, result=bool)
    def save_workflow_config(self, workflow_type: str, name: str, mapping_json: str) -> bool:
        """
        Save workflow configuration (node mapping).
        mapping_json is a JSON string with node mappings.
        """
        result = self.get_workflow_json(workflow_type)
        content = result.get("content", "")

        try:
            if content:
                workflow_data = json.loads(content)
            else:
                workflow_data = {
                    "prompt": {},
                    "extra": {},
                    "filmeto": {}
                }

            # Parse the mapping
            node_mapping = json.loads(mapping_json)

            # Update filmeto section
            if "filmeto" not in workflow_data:
                workflow_data["filmeto"] = {}
            workflow_data["filmeto"]["name"] = name
            workflow_data["filmeto"]["type"] = workflow_type
            workflow_data["filmeto"]["node_mapping"] = node_mapping

            # Update the workflow data
            new_content = json.dumps(workflow_data, indent=2, ensure_ascii=False)
            return self.save_workflow_json(workflow_type, new_content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse node mapping JSON: {e}")
            self.workflow_error.emit(f"Invalid node mapping: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to save workflow config: {e}")
            self.workflow_error.emit(str(e))
            return False

    @Slot(result="QVariant")
    def get_tooltype_workflow_map(self) -> Dict[str, str]:
        """Get mapping of ToolType to workflow names."""
        return {
            "text2image": "text2image",
            "image2image": "image2image",
            "image2video": "image2video",
            "text2video": "text2video",
            "speak2video": "speak2video",
            "text2speak": "text2speak",
            "text2music": "text2music",
            "inpainting": "inpainting",
        }

    @Slot(str, result=str)
    def get_workflow_display_name(self, workflow_type: str) -> str:
        """Get display name for a workflow type."""
        workflow = self.get_workflow_by_type(workflow_type)
        if workflow:
            return workflow.get("name", workflow_type)
        return workflow_type.replace("_", " ").title()

    @Slot(result="QVariant")
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Override to add workflow configuration.
        """
        result = super().get_config_dict()

        # Add workflow enabled states
        result["workflows"] = {
            workflow["type"]: workflow.get("enabled", True)
            for workflow in self._workflows
        }

        return result