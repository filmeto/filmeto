"""
Settings Management Module

Provides global configuration management with YAML-based storage.
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from utils.yaml_utils import load_yaml, save_yaml

logger = logging.getLogger(__name__)


@dataclass
class SettingField:
    """Represents a single setting field definition"""
    name: str
    label: str
    type: str
    default: Any
    description: str = ""
    validation: Optional[Dict[str, Any]] = None
    options: Optional[List[Dict[str, str]]] = None


@dataclass
class SettingGroup:
    """Represents a group of related settings"""
    name: str
    label: str
    icon: str = ""
    fields: List[SettingField] = None
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []


class Settings:
    """
    Global settings management class.

    Loads and manages configuration from settings.yml file in workspace directory.
    Supports grouped settings with validation and type-safe access.
    """
    
    def __init__(self, workspace_path: str, defer_load: bool = False):
        """
        Initialize Settings instance.
        
        Args:
            workspace_path: Path to the workspace directory
            defer_load: If True, defer loading settings until first access
        """
        self.workspace_path = workspace_path
        self.settings_file = os.path.join(workspace_path, "settings.yml")
        self.template_file = os.path.join(
            os.path.dirname(__file__),
            "settings_template.yml"
        )
        
        # Internal data structures
        self.schema: Dict[str, Dict[str, SettingField]] = {}
        self.values: Dict[str, Dict[str, Any]] = {}
        self._groups: List[SettingGroup] = []
        self._dirty = False
        self._loaded = False
        self._defer_load = defer_load
        
        # Load settings unless deferred
        if not defer_load:
            self.load()
    
    def _ensure_loaded(self):
        """Ensure settings are loaded (for deferred loading)"""
        if not self._loaded:
            import time
            import logging
            logger = logging.getLogger(__name__)
            load_start = time.time()
            logger.info(f"⏱️  [Settings] Starting deferred settings loading...")
            self.load()
            self._loaded = True
            load_time = (time.time() - load_start) * 1000
            logger.info(f"⏱️  [Settings] Deferred settings loading completed in {load_time:.2f}ms")
    
    def load(self):
        """Load settings from YML file or create from template if not exists"""
        # Ensure workspace directory exists
        os.makedirs(self.workspace_path, exist_ok=True)
        
        # Create settings file from template if it doesn't exist
        if not os.path.exists(self.settings_file):
            self._create_from_template()
        
        # Load settings YAML
        try:
            data = load_yaml(self.settings_file)
            if not data or 'groups' not in data:
                logger.warning(f"⚠️ Invalid settings file, creating from template")
                self._create_from_template()
                data = load_yaml(self.settings_file)
            
            self._parse_settings(data)
            logger.info(f"✅ Settings loaded from {self.settings_file}")
            
        except Exception as e:
            logger.error(f"❌ Error loading settings: {e}")
            # Backup corrupted file and create from template
            if os.path.exists(self.settings_file):
                backup_file = f"{self.settings_file}.backup"
                shutil.copy(self.settings_file, backup_file)
                logger.warning(f"⚠️ Backed up corrupted settings to {backup_file}")
            
            self._create_from_template()
            data = load_yaml(self.settings_file)
            self._parse_settings(data)
    
    def _create_from_template(self):
        """Create settings file from template"""
        if os.path.exists(self.template_file):
            shutil.copy(self.template_file, self.settings_file)
            logger.info(f"✅ Created settings from template: {self.settings_file}")
        else:
            logger.error(f"❌ Template file not found: {self.template_file}")
            raise FileNotFoundError(f"Settings template not found: {self.template_file}")
    
    def _parse_settings(self, data: Dict):
        """Parse settings YML data into internal structures"""
        self.schema.clear()
        self.values.clear()
        self._groups.clear()
        
        groups_data = data.get('groups', [])
        
        for group_data in groups_data:
            group_name = group_data.get('name')
            if not group_name:
                continue
            
            # Create group
            group = SettingGroup(
                name=group_name,
                label=group_data.get('label', group_name),
                icon=group_data.get('icon', '')
            )
            
            # Initialize schema and values for this group
            self.schema[group_name] = {}
            self.values[group_name] = {}
            
            # Parse fields
            fields_data = group_data.get('fields', [])
            for field_data in fields_data:
                field_name = field_data.get('name')
                if not field_name:
                    continue
                
                # Create field definition
                field = SettingField(
                    name=field_name,
                    label=field_data.get('label', field_name),
                    type=field_data.get('type', 'text'),
                    default=field_data.get('default'),
                    description=field_data.get('description', ''),
                    validation=field_data.get('validation'),
                    options=field_data.get('options')
                )
                
                # Store in schema
                self.schema[group_name][field_name] = field

                # Initialize value - use 'value' field if present and not None, otherwise use default
                # Note: dict.get(key, default) only returns default when key doesn't exist,
                # not when key exists but value is None. We need to handle both cases.
                saved_value = field_data.get('value')
                if saved_value is None:
                    saved_value = field.default
                self.values[group_name][field_name] = saved_value
                
                # Add to group
                group.fields.append(field)
            
            self._groups.append(group)
        
        self._dirty = False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by key path.

        Args:
            key: Dot-notation key path (e.g., "general.language")
            default: Default value to return if key not found

        Returns:
            Setting value or default if not found
        """
        if self._defer_load:
            self._ensure_loaded()
        try:
            parts = key.split('.')
            if len(parts) != 2:
                logger.warning(f"⚠️ Invalid key format: {key} (expected 'group.field')")
                return default

            group_name, field_name = parts

            if group_name not in self.values:
                logger.warning(f"⚠️ Group not found: {group_name}")
                return default

            if field_name not in self.values[group_name]:
                logger.warning(f"⚠️ Field not found: {field_name} in group {group_name}")
                return default

            return self.values[group_name][field_name]

        except Exception as e:
            logger.error(f"❌ Error getting setting {key}: {e}")
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set setting value by key path.
        
        Args:
            key: Dot-notation key path (e.g., "general.language")
            value: New value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            parts = key.split('.')
            if len(parts) != 2:
                logger.warning(f"⚠️ Invalid key format: {key} (expected 'group.field')")
                return False

            group_name, field_name = parts

            if group_name not in self.schema:
                logger.warning(f"⚠️ Group not found: {group_name}")
                return False

            if field_name not in self.schema[group_name]:
                logger.warning(f"⚠️ Field not found: {field_name} in group {group_name}")
                return False

            # Validate value
            if not self.validate(key, value):
                logger.warning(f"⚠️ Validation failed for {key} = {value}")
                return False

            # Update value
            self.values[group_name][field_name] = value
            self._dirty = True

            return True

        except Exception as e:
            logger.error(f"❌ Error setting {key} = {value}: {e}")
            return False
    
    def validate(self, key: str, value: Any) -> bool:
        """
        Validate a value against field schema.
        
        Args:
            key: Dot-notation key path
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parts = key.split('.')
            if len(parts) != 2:
                return False
            
            group_name, field_name = parts
            
            if group_name not in self.schema:
                return False
            
            if field_name not in self.schema[group_name]:
                return False
            
            field = self.schema[group_name][field_name]
            
            # Type-specific validation
            if field.type == 'text':
                return self._validate_text(value, field.validation or {})
            elif field.type == 'number':
                return self._validate_number(value, field.validation or {})
            elif field.type == 'boolean':
                return isinstance(value, bool)
            elif field.type == 'select':
                return self._validate_select(value, field.options or [])
            elif field.type == 'combo':
                # Combo field validation is similar to text but may also validate against options
                return self._validate_text(value, field.validation or {})
            elif field.type == 'color':
                return self._validate_color(value, field.validation or {})
            elif field.type == 'slider':
                return self._validate_slider(value, field.validation or {})
            else:
                logger.warning(f"⚠️ Unknown field type: {field.type}")
                return True  # Allow unknown types for extensibility

        except Exception as e:
            logger.error(f"❌ Validation error for {key}: {e}")
            return False
    
    def _validate_text(self, value: Any, validation: Dict) -> bool:
        """Validate text field"""
        if not isinstance(value, str):
            return False
        
        min_length = validation.get('min_length', 0)
        max_length = validation.get('max_length', float('inf'))
        pattern = validation.get('pattern')
        
        if len(value) < min_length or len(value) > max_length:
            return False
        
        if pattern and not re.match(pattern, value):
            return False
        
        return True
    
    def _validate_number(self, value: Any, validation: Dict) -> bool:
        """Validate number field"""
        if not isinstance(value, (int, float)):
            return False
        
        min_val = validation.get('min', float('-inf'))
        max_val = validation.get('max', float('inf'))
        
        return min_val <= value <= max_val
    
    def _validate_select(self, value: Any, options: List[Dict]) -> bool:
        """Validate select field"""
        valid_values = [opt.get('value') for opt in options]
        return value in valid_values
    
    def _validate_color(self, value: Any, validation: Dict) -> bool:
        """Validate color field"""
        if not isinstance(value, str):
            return False
        
        # Check hex format
        if validation.get('format') == 'hex':
            return bool(re.match(r'^#[0-9A-Fa-f]{6}$', value))
        
        # Default: accept any string
        return True
    
    def _validate_slider(self, value: Any, validation: Dict) -> bool:
        """Validate slider field"""
        if not isinstance(value, (int, float)):
            return False
        
        min_val = validation.get('min', 0)
        max_val = validation.get('max', 100)
        
        return min_val <= value <= max_val
    
    def save(self) -> bool:
        """
        Save current settings to YML file.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build YAML structure
            groups_data = []
            
            for group in self._groups:
                group_data = {
                    'name': group.name,
                    'label': group.label,
                    'icon': group.icon,
                    'fields': []
                }
                
                for field in group.fields:
                    field_data = {
                        'name': field.name,
                        'label': field.label,
                        'type': field.type,
                        'default': field.default,  # Preserve original default value
                        'value': self.values[group.name][field.name],  # Save current user value
                        'description': field.description
                    }
                    
                    if field.validation:
                        field_data['validation'] = field.validation
                    
                    if field.options:
                        field_data['options'] = field.options
                    
                    group_data['fields'].append(field_data)
                
                groups_data.append(group_data)
            
            data = {'groups': groups_data}
            
            # Save to file
            save_yaml(self.settings_file, data)
            self._dirty = False

            logger.info(f"✅ Settings saved to {self.settings_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving settings: {e}")
            return False
    
    def reload(self):
        """Reload settings from file, discarding unsaved changes"""
        self.load()
        logger.info("✅ Settings reloaded from file")

    def reset_to_defaults(self):
        """Reset all settings to their default values"""
        for group_name, fields in self.schema.items():
            for field_name, field in fields.items():
                self.values[group_name][field_name] = field.default

        self._dirty = True
        logger.info("✅ Settings reset to defaults")
    
    def get_groups(self) -> List[SettingGroup]:
        """
        Get all setting groups.
        
        Returns:
            List of SettingGroup objects
        """
        return self._groups
    
    def is_dirty(self) -> bool:
        """Check if settings have unsaved changes"""
        return self._dirty
    
    def get_group(self, group_name: str) -> Optional[SettingGroup]:
        """
        Get a specific setting group by name.
        
        Args:
            group_name: Name of the group
            
        Returns:
            SettingGroup object or None if not found
        """
        for group in self._groups:
            if group.name == group_name:
                return group
        return None
