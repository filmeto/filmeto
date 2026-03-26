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