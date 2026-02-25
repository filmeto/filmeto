"""
Settings Widget

Provides a UI for managing application settings with tabs, dynamic fields, and actions.
"""

from typing import Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QScrollArea, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.data.settings import SettingGroup, SettingField
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.settings.field_widget_factory import FieldWidgetFactory
from app.ui.settings.plugin_grid_widget import PluginGridWidget
from app.ui.settings.plugin_detail_dialog import PluginDetailDialog


class SettingsWidget(BaseWidget):
    """
    Settings management widget with dynamic field generation.
    
    Features:
    - Tab-based group organization
    - Dynamic field widgets based on field type
    - Save, revert, and reset to default actions
    - Dirty state tracking
    - Search functionality
    """
    
    settings_changed = Signal()
    
    def __init__(self, workspace: Workspace):
        super().__init__(workspace)

        self.settings = workspace.get_settings()
        self.field_widgets: Dict[str, QWidget] = {}  # key -> widget mapping
        self.original_values: Dict[str, Any] = {}  # Track original values for dirty state
        self._is_dirty = False

        # Get service registry from workspace's plugins
        self.service_registry = None
        if hasattr(workspace, 'bot') and hasattr(workspace.bot, 'plugins'):
            self.service_registry = workspace.bot.plugins.get_service_registry()

        # Set window properties
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 600)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create UI sections
        self._create_header(main_layout)
        self._create_tabs(main_layout)
        self._create_footer(main_layout)

        # Load current values
        self._load_values()

        # Connect the API host change to update model options
        self._connect_api_host_change_handler()

        # Apply styling
        self._apply_style()
    
    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header with title and search"""
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #252525; border-bottom: 1px solid #333333;")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Settings")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #ffffff; border: none;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Search box (placeholder for future implementation)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search settings...")
        self.search_box.setFixedWidth(250)
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        layout.addWidget(self.search_box)
        
        parent_layout.addWidget(header)
    
    def _create_tabs(self, parent_layout: QVBoxLayout):
        """Create tab widget for setting groups"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px 20px;
                border: none;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
            }
        """)
        
        # Create tab for each group
        groups = self.settings.get_groups()
        for group in groups:
            tab_widget = self._create_group_tab(group)
            self.tab_widget.addTab(tab_widget, group.label)
        
        # Add Services tab if service registry is available
        if self.service_registry:
            services_tab = self._create_services_tab()
            self.tab_widget.addTab(services_tab, "Services")
        
        parent_layout.addWidget(self.tab_widget, 1)
    
    def _create_group_tab(self, group: SettingGroup) -> QWidget:
        """Create a tab widget for a setting group"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        
        # Scroll area for fields
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """)
        
        # Container for fields
        fields_container = QWidget()
        fields_container.setStyleSheet("background-color: #1e1e1e;")
        form_layout = QFormLayout(fields_container)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Create field widgets
        for field in group.fields:
            self._add_field_to_form(form_layout, group, field)
        
        scroll_area.setWidget(fields_container)
        tab_layout.addWidget(scroll_area)
        
        return tab
    
    def _add_field_to_form(self, form_layout: QFormLayout, group: SettingGroup, field: SettingField):
        """Add a field widget to the form layout"""
        # Create label
        label = QLabel(f"{field.label}:")
        label.setStyleSheet("color: #ffffff; font-size: 12px;")
        label.setToolTip(field.description)

        # Get current value
        key = f"{group.name}.{field.name}"
        current_value = self.settings.get(key, field.default)

        # Create widget using factory
        widget = FieldWidgetFactory.create_widget(field, current_value)
        widget.setFixedWidth(300)

        # Store widget reference
        self.field_widgets[key] = widget
        self.original_values[key] = current_value

        # Connect change handler for all fields
        FieldWidgetFactory.connect_change_handler(
            widget,
            field.type,
            lambda: self._on_field_changed()
        )

        # Create container for widget and description
        widget_container = QWidget()
        widget_layout = QVBoxLayout(widget_container)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.setSpacing(4)

        widget_layout.addWidget(widget)

        # Add description label
        if field.description:
            desc_label = QLabel(field.description)
            desc_label.setStyleSheet("color: #888888; font-size: 10px;")
            desc_label.setWordWrap(True)
            desc_label.setMaximumWidth(300)
            widget_layout.addWidget(desc_label)

        widget_layout.addStretch()

        # Add to form
        form_layout.addRow(label, widget_container)
    
    def _create_footer(self, parent_layout: QVBoxLayout):
        """Create footer with action buttons"""
        footer = QWidget()
        footer.setFixedHeight(50)
        footer.setStyleSheet("background-color: #252525; border-top: 1px solid #333333;")
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(12)
        
        layout.addStretch()
        
        # Reset to Default button
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setFixedHeight(32)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        layout.addWidget(self.reset_btn)
        
        # Revert button
        self.revert_btn = QPushButton("Revert")
        self.revert_btn.setFixedHeight(32)
        self.revert_btn.clicked.connect(self._on_revert_clicked)
        self.revert_btn.setEnabled(False)
        self.revert_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
        """)
        layout.addWidget(self.revert_btn)
        
        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedHeight(32)
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 20px;
                background-color: #3498db;
                border: 1px solid #2980b9;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                border: 1px solid #555555;
                color: #666666;
            }
        """)
        layout.addWidget(self.save_btn)
        
        parent_layout.addWidget(footer)
    
    def _get_model_options_by_service(self, api_host: str) -> list:
        """Get model options based on the API host"""
        if 'dashscope.aliyuncs.com' in api_host:
            # DashScope models
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
            # Azure OpenAI models
            return [
                {"value": "gpt-4", "label": "GPT-4"},
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "gpt-4o-mini", "label": "GPT-4o Mini"},
                {"value": "gpt-35-turbo", "label": "GPT-3.5 Turbo"},
                {"value": "text-embedding-ada-002", "label": "Text Embedding Ada 002"}
            ]
        elif 'openai.com' in api_host:
            # Standard OpenAI models
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
            # Anthropic models
            return [
                {"value": "claude-3-opus", "label": "Claude 3 Opus"},
                {"value": "claude-3-sonnet", "label": "Claude 3 Sonnet"},
                {"value": "claude-3-haiku", "label": "Claude 3 Haiku"},
                {"value": "claude-2.1", "label": "Claude 2.1"}
            ]
        elif 'googleapis.com' in api_host:
            # Google models
            return [
                {"value": "gemini-pro", "label": "Gemini Pro"},
                {"value": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
                {"value": "gemini-1.5-flash", "label": "Gemini 1.5 Flash"},
                {"value": "text-embedding-005", "label": "Text Embedding 005"}
            ]
        else:
            # Default models (OpenAI-compatible)
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

    def _update_model_options(self):
        """Update the model options based on the selected API host"""
        # Get the current API host
        api_host_widget = self.field_widgets.get('ai_services.openai_host')
        if not api_host_widget:
            return

        api_host = api_host_widget.text()

        # Get the model widget
        model_widget = self.field_widgets.get('ai_services.default_model')
        if not model_widget:
            return

        # Get the current value before clearing
        current_value = model_widget.currentText()

        # Clear existing items
        model_widget.clear()

        # Get new options based on the API host
        model_options = self._get_model_options_by_service(api_host)

        # Add new options
        for option in model_options:
            model_widget.addItem(option.get('label', ''), option.get('value'))

        # Try to restore the current value if it exists in the new options
        index = model_widget.findData(current_value)
        if index >= 0:
            model_widget.setCurrentIndex(index)
        else:
            # If the current value is not in the new options, set it as text
            model_widget.setEditText(current_value)

    def _connect_api_host_change_handler(self):
        """Connect the API host change event to update model options"""
        api_host_widget = self.field_widgets.get('ai_services.openai_host')
        if api_host_widget:
            api_host_widget.textChanged.connect(self._update_model_options)

    def _apply_style(self):
        """Apply overall widget style"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
    
    def _load_values(self):
        """Load current values from settings into widgets"""
        for key, widget in self.field_widgets.items():
            parts = key.split('.')
            if len(parts) != 2:
                continue

            group_name, field_name = parts
            group = self.settings.get_group(group_name)
            if not group:
                continue

            field = next((f for f in group.fields if f.name == field_name), None)
            if not field:
                continue

            current_value = self.settings.get(key, field.default)
            self._set_widget_value(widget, field.type, current_value)
            self.original_values[key] = current_value

        # Update model options based on the loaded API host
        self._update_model_options()
    
    def _set_widget_value(self, widget: QWidget, field_type: str, value: Any):
        """Set widget value based on field type"""
        if field_type == 'text':
            widget.setText(str(value))
        elif field_type == 'number':
            widget.setValue(int(value) if value is not None else 0)
        elif field_type == 'boolean':
            widget.setChecked(bool(value))
        elif field_type == 'select':
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)
        elif field_type == 'color':
            widget.set_color(str(value))
        elif field_type == 'slider':
            widget.set_value(int(value) if value is not None else 0)
    
    def _on_field_changed(self):
        """Handle field value change"""
        # Check if any values have changed
        has_changes = False
        
        for key, widget in self.field_widgets.items():
            parts = key.split('.')
            if len(parts) != 2:
                continue
            
            group_name, field_name = parts
            group = self.settings.get_group(group_name)
            if not group:
                continue
            
            field = next((f for f in group.fields if f.name == field_name), None)
            if not field:
                continue
            
            current_value = FieldWidgetFactory.get_widget_value(widget, field.type)
            original_value = self.original_values.get(key)
            
            if current_value != original_value:
                has_changes = True
                break
        
        self._is_dirty = has_changes
        self.save_btn.setEnabled(has_changes)
        self.revert_btn.setEnabled(has_changes)
        
        # Update window title to show dirty state
        title = "Settings"
        if self._is_dirty:
            title += " *"
        self.setWindowTitle(title)
    
    def _on_save_clicked(self):
        """Handle save button click"""
        # Collect all values from widgets
        validation_errors = []
        
        for key, widget in self.field_widgets.items():
            parts = key.split('.')
            if len(parts) != 2:
                continue
            
            group_name, field_name = parts
            group = self.settings.get_group(group_name)
            if not group:
                continue
            
            field = next((f for f in group.fields if f.name == field_name), None)
            if not field:
                continue
            
            # Get widget value
            value = FieldWidgetFactory.get_widget_value(widget, field.type)
            
            # Validate
            if not self.settings.validate(key, value):
                validation_errors.append(f"{field.label}: Invalid value")
                continue
            
            # Update settings
            self.settings.set(key, value)
        
        # Show validation errors if any
        if validation_errors:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Some settings have invalid values:\n\n" + "\n".join(validation_errors)
            )
            return
        
        # Save to file
        if self.settings.save():
            # Update original values
            for key, widget in self.field_widgets.items():
                parts = key.split('.')
                if len(parts) != 2:
                    continue
                
                group_name, field_name = parts
                group = self.settings.get_group(group_name)
                if not group:
                    continue
                
                field = next((f for f in group.fields if f.name == field_name), None)
                if not field:
                    continue
                
                value = FieldWidgetFactory.get_widget_value(widget, field.type)
                self.original_values[key] = value
            
            self._is_dirty = False
            self.save_btn.setEnabled(False)
            self.revert_btn.setEnabled(False)
            self.setWindowTitle("Settings")
            
            # Show success message
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
            # Emit signal
            self.settings_changed.emit()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings. Please try again.")
    
    def _on_revert_clicked(self):
        """Handle revert button click"""
        reply = QMessageBox.question(
            self,
            "Revert Changes",
            "Are you sure you want to discard all changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reload settings from file
            self.settings.reload()
            
            # Update widgets with original values
            self._load_values()
            
            self._is_dirty = False
            self.save_btn.setEnabled(False)
            self.revert_btn.setEnabled(False)
            self.setWindowTitle("Settings")
    
    def _on_reset_clicked(self):
        """Handle reset to default button click"""
        reply = QMessageBox.question(
            self,
            "Reset to Default",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to defaults in settings object
            self.settings.reset_to_defaults()
            
            # Update widgets with default values
            for key, widget in self.field_widgets.items():
                parts = key.split('.')
                if len(parts) != 2:
                    continue
                
                group_name, field_name = parts
                group = self.settings.get_group(group_name)
                if not group:
                    continue
                
                field = next((f for f in group.fields if f.name == field_name), None)
                if not field:
                    continue
                
                self._set_widget_value(widget, field.type, field.default)
            
            # Mark as dirty since defaults may differ from saved values
            self._on_field_changed()

    def _create_services_tab(self) -> QWidget:
        """Create the services plugin tab"""
        # Create plugin grid widget
        self.plugin_grid = PluginGridWidget()
        
        # Connect signals
        self.plugin_grid.plugin_selected.connect(self._on_plugin_selected)
        
        # Load services
        services = self.service_registry.get_all_services()
        self.plugin_grid.set_services(services)
        
        return self.plugin_grid
    
    def _on_plugin_selected(self, service_id: str):
        """Handle plugin selection to open detail dialog"""
        if not self.service_registry:
            return
        
        try:
            # Use specialized ComfyUI dialog for comfyui service
            if service_id == "comfyui":
                pass
            else:
                # Open standard plugin detail dialog
                dialog = PluginDetailDialog(service_id, self.service_registry, self)
            
            dialog.config_saved.connect(self._on_plugin_config_saved)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open plugin configuration: {e}"
            )
    
    def _on_plugin_config_saved(self, service_id: str):
        """Handle plugin configuration save"""
        # Reload the service
        if self.service_registry:
            self.service_registry.reload_service(service_id)
            
            # Refresh plugin grid
            services = self.service_registry.get_all_services()
            self.plugin_grid.refresh(services)
