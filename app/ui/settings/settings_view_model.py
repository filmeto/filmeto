"""
Settings View Model

Provides a ViewModel for application settings.
Exposes settings groups, fields, and operations to QML.
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot, Property

logger = logging.getLogger(__name__)


class SettingsViewModel(QObject):
    """
    ViewModel for application settings.

    Provides settings data binding between Python and QML.
    This model exposes:
    - Settings groups (tabs)
    - Settings fields with values
    - Save, revert, reset operations
    - Dirty state tracking
    - API host to model options linkage
    """

    # Signals
    settings_changed = Signal()
    values_changed = Signal()
    dirty_changed = Signal()
    error_occurred = Signal(str)
    success_message = Signal(str)
    model_options_changed = Signal(str)  # field_key

    def __init__(
        self,
        settings,
        service_registry=None,
        parent=None
    ):
        """
        Initialize the Settings QML model.

        Args:
            settings: Settings instance from app.data.settings
            service_registry: Optional service registry for Services tab
            parent: Parent QObject
        """
        super().__init__(parent)

        self._settings = settings
        self._service_registry = service_registry
        self._is_dirty = False
        self._current_values: Dict[str, Any] = {}  # key -> current value
        self._original_values: Dict[str, Any] = {}  # key -> original value
        self._search_text = ""
        self._field_options: Dict[str, List[Dict]] = {}  # key -> options list

        self._init_values()

    def _init_values(self):
        """Initialize values from settings."""
        self._current_values.clear()
        self._original_values.clear()

        groups = self._settings.get_groups()
        for group in groups:
            for field in group.fields:
                key = f"{group.name}.{field.name}"
                value = self._settings.get(key, field.default)
                self._current_values[key] = value
                self._original_values[key] = value

    # ─────────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────────

    @Property("QVariant", constant=True)
    def groups(self) -> List[Dict[str, Any]]:
        """Get list of setting groups for QML."""
        result = []
        groups = self._settings.get_groups()
        for group in groups:
            group_data = {
                "name": group.name,
                "label": group.label,
                "icon": group.icon,
                "fields": []
            }

            for field in group.fields:
                key = f"{group.name}.{field.name}"
                field_data = {
                    "name": field.name,
                    "key": key,
                    "label": field.label,
                    "type": field.type,
                    "default": field.default,
                    "description": field.description,
                    "value": self._current_values.get(key, field.default),
                    "options": field.options or []
                }

                # Add validation info
                if field.validation:
                    field_data["validation"] = field.validation

                group_data["fields"].append(field_data)

            result.append(group_data)

        return result

    @Property(bool, notify=dirty_changed)
    def isDirty(self) -> bool:
        """Check if there are unsaved changes."""
        return self._is_dirty

    @Property(str, notify=values_changed)
    def searchText(self) -> str:
        """Get search text."""
        return self._search_text

    @searchText.setter
    def searchText(self, text: str):
        if self._search_text != text:
            self._search_text = text
            self.values_changed.emit()

    @Property(bool, constant=True)
    def hasServicesTab(self) -> bool:
        """Check if Services tab should be shown."""
        return self._service_registry is not None

    # ─────────────────────────────────────────────────────────────
    # Slots (callable from QML)
    # ─────────────────────────────────────────────────────────────

    @Slot(str, result="QVariant")
    def get_value(self, key: str) -> Any:
        """Get a setting value by key."""
        return self._current_values.get(key)

    @Slot(str, "QVariant")
    def set_value(self, key: str, value: Any):
        """Set a setting value."""
        if self._current_values.get(key) != value:
            self._current_values[key] = value
            self._check_dirty()
            self.values_changed.emit()

            # Special handling for API host to update model options
            if key == "ai_services.openai_host":
                self._update_model_options(value)

    @Slot(str, result="QVariant")
    def get_model_options(self, key: str) -> List[Dict[str, str]]:
        """
        Get model options for a select/combo field.
        Returns dynamic options based on API host for default_model field.
        """
        if key == "ai_services.default_model":
            api_host = self._current_values.get("ai_services.openai_host", "")
            return self._get_model_options_by_service(api_host)
        return []

    def _get_model_options_by_service(self, api_host: str) -> List[Dict[str, str]]:
        """Get model options based on the API host."""
        if 'dashscope.aliyuncs.com' in api_host:
            return [
                {"value": "qwen3.5-flash", "label": "Qwen3.5 Flash"},
                {"value": "qwen3.5-plus", "label": "Qwen3.5 Plus"},
                {"value": "kimi-k2.5", "label": "Kimi K2.5"},
                {"value": "kimi-k2-thinking", "label": "Kimi K2 Thinking"},
                {"value": "glm-5", "label": "GLM-5"},
                {"value": "glm-4.7", "label": "GLM-4.7"},
                {"value": "qwen-turbo", "label": "Qwen Turbo"},
                {"value": "qwen-plus", "label": "Qwen Plus"},
                {"value": "qwen-max", "label": "Qwen Max"},
                {"value": "qwen-max-longcontext", "label": "Qwen Max (Long Context)"},
                {"value": "qwen-vl-plus", "label": "Qwen VL Plus (Vision)"},
                {"value": "qwen-vl-max", "label": "Qwen VL Max (Vision)"},
                {"value": "text-embedding-v1", "label": "Text Embedding (v1)"}
            ]
        elif 'openai.azure.com' in api_host or 'openai.azure' in api_host:
            return [
                {"value": "gpt-4", "label": "GPT-4"},
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "gpt-4o-mini", "label": "GPT-4o Mini"},
                {"value": "gpt-35-turbo", "label": "GPT-3.5 Turbo"},
                {"value": "text-embedding-ada-002", "label": "Text Embedding Ada 002"}
            ]
        elif 'openai.com' in api_host:
            return [
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "gpt-4o-mini", "label": "GPT-4o Mini"},
                {"value": "gpt-4-turbo", "label": "GPT-4 Turbo"},
                {"value": "gpt-4", "label": "GPT-4"},
                {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"},
                {"value": "text-embedding-3-small", "label": "Text Embedding 3 Small"},
                {"value": "text-embedding-3-large", "label": "Text Embedding 3 Large"}
            ]
        elif 'anthropic' in api_host:
            return [
                {"value": "claude-3-opus", "label": "Claude 3 Opus"},
                {"value": "claude-3-sonnet", "label": "Claude 3 Sonnet"},
                {"value": "claude-3-haiku", "label": "Claude 3 Haiku"},
                {"value": "claude-2.1", "label": "Claude 2.1"}
            ]
        elif 'googleapis.com' in api_host:
            return [
                {"value": "gemini-pro", "label": "Gemini Pro"},
                {"value": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
                {"value": "gemini-1.5-flash", "label": "Gemini 1.5 Flash"},
                {"value": "text-embedding-005", "label": "Text Embedding 005"}
            ]
        else:
            return [
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "gpt-4o-mini", "label": "GPT-4o Mini"},
                {"value": "gpt-4-turbo", "label": "GPT-4 Turbo"},
                {"value": "gpt-4", "label": "GPT-4"},
                {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"},
                {"value": "claude-3-haiku", "label": "Claude 3 Haiku"},
                {"value": "claude-3-sonnet", "label": "Claude 3 Sonnet"},
                {"value": "gemini-pro", "label": "Gemini Pro"},
                {"value": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"}
            ]

    def _update_model_options(self, api_host: str):
        """Update model options based on API host change."""
        options = self._get_model_options_by_service(api_host)
        self._field_options["ai_services.default_model"] = options
        self.model_options_changed.emit("ai_services.default_model")

    @Slot(str, result="QVariant")
    def get_field_info(self, key: str) -> Dict[str, Any]:
        """Get field information for a setting key."""
        parts = key.split('.')
        if len(parts) != 2:
            return {}

        group_name, field_name = parts
        group = self._settings.get_group(group_name)
        if not group:
            return {}

        for field in group.fields:
            if field.name == field_name:
                return {
                    "name": field.name,
                    "label": field.label,
                    "type": field.type,
                    "default": field.default,
                    "description": field.description,
                    "options": field.options or []
                }

        return {}

    @Slot(result=bool)
    def save(self) -> bool:
        """
        Save all settings.

        Returns:
            True if saved successfully
        """
        try:
            # Validate all values
            for key, value in self._current_values.items():
                if not self._settings.validate(key, value):
                    self.error_occurred.emit(f"Invalid value for {key}")
                    return False

            # Set all values in settings
            for key, value in self._current_values.items():
                self._settings.set(key, value)

            # Save to file
            if self._settings.save():
                # Update original values
                self._original_values = dict(self._current_values)
                self._is_dirty = False
                self.dirty_changed.emit()
                self.settings_changed.emit()
                self.success_message.emit("Settings saved successfully!")
                return True
            else:
                self.error_occurred.emit("Failed to save settings file")
                return False

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            self.error_occurred.emit(str(e))
            return False

    @Slot()
    def revert(self):
        """Revert all changes to last saved state."""
        self._current_values = dict(self._original_values)
        self._is_dirty = False
        self.dirty_changed.emit()
        self.values_changed.emit()

    @Slot()
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        groups = self._settings.get_groups()
        for group in groups:
            for field in group.fields:
                key = f"{group.name}.{field.name}"
                self._current_values[key] = field.default

        self._check_dirty()
        self.values_changed.emit()

    @Slot(result="QVariant")
    def get_services(self) -> List[Dict[str, Any]]:
        """Get list of available services for Services tab."""
        if not self._service_registry:
            return []

        services = self._service_registry.get_all_services()
        result = []
        for service in services:
            result.append({
                "id": service.get("id", ""),
                "name": service.get("name", ""),
                "description": service.get("description", ""),
                "enabled": service.get("enabled", True),
                "icon": service.get("icon", "")
            })
        return result

    @Slot(str, result="QVariant")
    def get_filtered_fields(self, group_name: str) -> List[Dict[str, Any]]:
        """Get filtered fields for a group based on search text."""
        group = self._settings.get_group(group_name)
        if not group:
            return []

        result = []
        search_lower = self._search_text.lower()

        for field in group.fields:
            # Check if field matches search
            if search_lower:
                label_match = search_lower in field.label.lower()
                desc_match = search_lower in (field.description or "").lower()
                name_match = search_lower in field.name.lower()

                if not (label_match or desc_match or name_match):
                    continue

            key = f"{group.name}.{field.name}"
            field_data = {
                "name": field.name,
                "key": key,
                "label": field.label,
                "type": field.type,
                "default": field.default,
                "description": field.description,
                "value": self._current_values.get(key, field.default),
                "options": field.options or []
            }

            if field.validation:
                field_data["validation"] = field.validation

            result.append(field_data)

        return result

    # ─────────────────────────────────────────────────────────────
    # Internal Methods
    # ─────────────────────────────────────────────────────────────

    def _check_dirty(self):
        """Check if current values differ from original."""
        has_changes = False

        for key, value in self._current_values.items():
            original = self._original_values.get(key)
            if value != original:
                has_changes = True
                break

        if has_changes != self._is_dirty:
            self._is_dirty = has_changes
            self.dirty_changed.emit()

    def reload(self):
        """Reload settings from file."""
        self._settings.reload()
        self._init_values()
        self._is_dirty = False
        self.dirty_changed.emit()
        self.values_changed.emit()