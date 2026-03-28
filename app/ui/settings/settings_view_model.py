"""
Settings View Model

Provides a ViewModel for application settings.
Exposes settings groups, fields, and operations to QML.
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtWidgets import QMessageBox

from app.ui.settings.plugin_detail_dialog import PluginDetailDialog

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
    services_changed = Signal()

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
        self._services_revision = 0

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

    @Property(int, notify=services_changed)
    def servicesRevision(self) -> int:
        """Incrementing value used by QML to refresh services list bindings."""
        return self._services_revision

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

    @Slot(str, result="QVariant")
    def get_model_options(self, key: str) -> List[Dict[str, str]]:
        """
        Get model options for a select/combo field.
        """
        return []

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
                "id": service.service_id,
                "name": service.name,
                "description": service.description,
                "enabled": service.enabled,
                "icon": service.icon
            })
        return result

    @Slot(str, result=bool)
    def open_service_config(self, service_id: str) -> bool:
        """Open service configuration dialog and refresh service list on save."""
        if not self._service_registry:
            self.error_occurred.emit("Service registry is not available")
            return False

        if not service_id:
            self.error_occurred.emit("Invalid service id")
            return False

        try:
            dialog = PluginDetailDialog(service_id, self._service_registry)
            if dialog.exec():
                self._service_registry.reload_service(service_id)
                self._services_revision += 1
                self.services_changed.emit()
            return True
        except Exception as e:
            logger.error(f"Failed to open service configuration: {e}")
            self.error_occurred.emit(str(e))
            QMessageBox.critical(
                None,
                "Error",
                f"Failed to open plugin configuration: {e}"
            )
            return False

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