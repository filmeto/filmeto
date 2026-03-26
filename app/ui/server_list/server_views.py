"""
Server Management Views

Provides modular views for server list and server configuration that can be
switched within a single dialog (Mac-style preferences).
"""

import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QCheckBox,
    QSpinBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.base_widget import BaseWidget
from app.ui.server_list.qml_server_list_view import ServerListView

from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class ServerConfigView(BaseWidget):
    """
    View for configuring a server.
    Supports both creating new servers and editing existing ones.
    """

    # Signals
    save_clicked = Signal(str, object)  # server_name, config
    cancel_clicked = Signal()

    def __init__(self, workspace, parent=None):
        super().__init__(workspace)
        self.plugin_info = None
        self.server_config = None
        self.field_widgets = {}
        self._is_edit_mode = False
        self.custom_config_widget = None
        self._init_ui()

    @property
    def is_edit_mode(self):
        """Return whether the view is in edit mode"""
        return self._is_edit_mode
    
    def _init_ui(self):
        """Initialize UI components"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(16)
        
        # Content will be populated when configure() is called
    
    def configure(self, plugin_info, server_config=None):
        """
        Configure the view for a specific plugin/server.

        Args:
            plugin_info: PluginInfo object
            server_config: Optional ServerConfig for editing existing server
        """
        self.plugin_info = plugin_info
        self.server_config = server_config
        self._is_edit_mode = server_config is not None
        self.field_widgets = {}
        logger.info(
            "ServerConfigView configure plugin=%s edit_mode=%s",
            getattr(plugin_info, "name", "unknown"),
            self._is_edit_mode,
        )

        # Clean up existing custom widget first (before clearing layout)
        self._cleanup_custom_widget()

        # Clear existing layout
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                # Check for cleanup method (for QML widgets)
                if hasattr(widget, 'cleanup'):
                    try:
                        widget.cleanup()
                    except Exception as e:
                        logger.debug(f"Error cleaning up widget: {e}")
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        # Build UI
        self._build_config_ui()

    def _cleanup_custom_widget(self):
        """Clean up the custom config widget properly"""
        if self.custom_config_widget:
            # CRITICAL: Set focus to the config view itself BEFORE cleaning up.
            # QQuickWidget has its own focus management and when destroyed,
            # can leave focus as None instead of returning to parent.
            self.setFocus()
            self.activateWindow()

            # Clear focus from the custom widget
            self.custom_config_widget.clearFocus()

            # Release mouse grab BEFORE any other cleanup operations
            # This must be done while widget is still valid
            try:
                self.custom_config_widget.releaseMouse()
            except Exception as e:
                logger.debug(f"Error releasing mouse: {e}")

            # Disconnect config_changed signal if connected
            if hasattr(self.custom_config_widget, 'config_changed'):
                try:
                    self.custom_config_widget.config_changed.disconnect(self._on_custom_config_changed)
                except Exception as e:
                    logger.debug(f"Error disconnecting config_changed signal: {e}")

            # Call cleanup if available
            if hasattr(self.custom_config_widget, 'cleanup'):
                try:
                    self.custom_config_widget.cleanup()
                except Exception as e:
                    logger.debug(f"Error cleaning up custom config widget: {e}")

            # Hide the widget first
            self.custom_config_widget.hide()

            # Remove from layout
            self.main_layout.removeWidget(self.custom_config_widget)

            # Delete the widget
            self.custom_config_widget.deleteLater()

            # Clear reference
            self.custom_config_widget = None
    
    def _clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                # Clean up QML widgets properly
                if hasattr(widget, 'cleanup'):
                    try:
                        widget.cleanup()
                    except Exception as e:
                        logger.debug(f"Error cleaning up widget: {e}")
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _build_config_ui(self):
        """Build the configuration UI based on plugin info (should now be handled by plugin's init_ui)"""
        # Check if plugin has custom UI
        custom_widget = self._try_get_custom_ui()
        if custom_widget:
            # Use custom UI from plugin
            self.custom_config_widget = custom_widget
            logger.info(
                "ServerConfigView custom widget type=%s objectName=%s",
                type(custom_widget).__name__,
                custom_widget.objectName(),
            )

            # Set size policy to expand
            from PySide6.QtWidgets import QSizePolicy
            custom_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Set minimum size to ensure visibility
            custom_widget.setMinimumSize(400, 300)

            self.main_layout.addWidget(custom_widget)

            # Connect config changed signal if available
            if hasattr(custom_widget, 'config_changed'):
                try:
                    custom_widget.config_changed.connect(self._on_custom_config_changed)
                except Exception as e:
                    logger.debug(f"Could not connect config_changed signal: {e}")

            # Connect validation error signal if available
            if hasattr(custom_widget, '_config_model'):
                try:
                    config_model = custom_widget._config_model
                    if hasattr(config_model, 'validation_error'):
                        config_model.validation_error.connect(self._on_validation_error)
                except Exception as e:
                    logger.debug(f"Could not connect validation_error signal: {e}")

            return

        # This fallback should not be needed anymore as all plugins should implement init_ui
        # but we keep it for backwards compatibility and safety
        logger.warning("Falling back to default UI, plugin should implement init_ui")

        # Default form-based UI - this is the migrated logic that should now be in plugins
        # Header
        header_label = QLabel(f"{tr('配置')} {self.plugin_info.name} {tr('服务器')}", self)
        header_font = QFont()
        header_font.setPointSize(13)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setStyleSheet("QLabel { color: #E1E1E1; }")
        self.main_layout.addWidget(header_label)

        # Description
        desc_label = QLabel(self.plugin_info.description, self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { color: #999999; font-size: 11px; }")
        self.main_layout.addWidget(desc_label)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Server name field
        self.name_field = QLineEdit(self)
        self.name_field.setPlaceholderText(tr("输入唯一的服务器名称"))
        self._style_line_edit(self.name_field)
        name_label = QLabel(tr("服务器名称") + " *", self)
        name_label.setStyleSheet("QLabel { color: #E1E1E1; }")
        form_layout.addRow(name_label, self.name_field)

        # Pre-fill name if editing
        if self.is_edit_mode:
            self.name_field.setText(self.server_config.name)
            self.name_field.setEnabled(False)

        # Description field
        self.description_field = QLineEdit(self)
        self.description_field.setPlaceholderText(tr("输入服务器描述（可选）"))
        self._style_line_edit(self.description_field)
        desc_label = QLabel(tr("描述"), self)
        desc_label.setStyleSheet("QLabel { color: #E1E1E1; }")
        form_layout.addRow(desc_label, self.description_field)

        # Pre-fill description if editing
        if self.is_edit_mode:
            self.description_field.setText(self.server_config.description or "")

        # Get config schema from plugin
        config_schema = self._get_plugin_config_schema()

        # Create fields based on schema
        for field_config in config_schema.get("fields", []):
            field_name = field_config["name"]
            field_label = field_config.get("label", field_name)
            field_type = field_config.get("type", "string")
            required = field_config.get("required", False)
            default = field_config.get("default", "")
            placeholder = field_config.get("placeholder", "")
            description = field_config.get("description", "")

            # Create widget
            widget = self._create_field_widget(field_type, default, placeholder)
            self.field_widgets[field_name] = {
                "widget": widget,
                "type": field_type,
                "required": required
            }

            # Pre-fill if editing
            if self.is_edit_mode:
                self._prefill_field(field_name, widget, field_type)

            # Create label
            label_text = field_label
            if required:
                label_text += " *"
            label = QLabel(label_text, self)
            label.setStyleSheet("QLabel { color: #E1E1E1; }")
            if description:
                label.setToolTip(description)

            form_layout.addRow(label, widget)

        self.main_layout.addLayout(form_layout)

        # Enabled checkbox
        self.enabled_checkbox = QCheckBox(tr("启用此服务器"), self)
        self.enabled_checkbox.setChecked(True if not self.is_edit_mode else self.server_config.enabled)
        self.enabled_checkbox.setStyleSheet("""
            QCheckBox {
                color: #E1E1E1;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.main_layout.addWidget(self.enabled_checkbox)

        self.main_layout.addStretch()
    
    def _prefill_field(self, field_name: str, widget: QWidget, field_type: str):
        """Pre-fill field with existing server config value"""
        if not self.server_config:
            return
        
        value = self.server_config.parameters.get(field_name)
        
        # Handle special fields
        if field_name == "endpoint" and self.server_config.endpoint:
            value = self.server_config.endpoint
        elif field_name == "api_key" and self.server_config.api_key:
            value = self.server_config.api_key
        
        if value is not None:
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))
    
    def _get_plugin_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema from plugin"""
        if hasattr(self.plugin_info, 'config') and 'config_schema' in self.plugin_info.config:
            return self.plugin_info.config['config_schema']
        
        # Default schema
        return {
            "fields": [
                {
                    "name": "endpoint",
                    "label": tr("端点URL"),
                    "type": "url",
                    "required": False,
                    "default": "",
                    "description": tr("服务端点URL（如适用）"),
                    "placeholder": "http://localhost:8188"
                },
                {
                    "name": "api_key",
                    "label": tr("API密钥"),
                    "type": "password",
                    "required": False,
                    "default": "",
                    "description": tr("用于身份验证的API密钥（如需要）"),
                    "placeholder": tr("输入API密钥")
                }
            ]
        }
    
    def _create_field_widget(self, field_type: str, default: Any, placeholder: str) -> QWidget:
        """Create appropriate widget based on field type"""
        if field_type == "boolean":
            widget = QCheckBox(self)
            widget.setChecked(bool(default))
            widget.setStyleSheet("""
                QCheckBox {
                    color: #E1E1E1;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
            """)
            return widget
        
        elif field_type == "integer":
            widget = QSpinBox(self)
            widget.setMinimum(-999999)
            widget.setMaximum(999999)
            widget.setValue(int(default) if default else 0)
            widget.setStyleSheet("""
                QSpinBox {
                    background-color: #2b2b2b;
                    color: #E1E1E1;
                    border: 1px solid #3c3c3c;
                    border-radius: 4px;
                    padding: 6px;
                }
                QSpinBox:focus {
                    border: 1px solid #4CAF50;
                }
            """)
            return widget
        
        else:  # string, password, url
            widget = QLineEdit(self)
            if field_type == "password":
                widget.setEchoMode(QLineEdit.Password)
            if default:
                widget.setText(str(default))
            if placeholder:
                widget.setPlaceholderText(placeholder)
            self._style_line_edit(widget)
            return widget
    
    def _style_line_edit(self, widget: QLineEdit):
        """Apply consistent styling to line edit widgets"""
        widget.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #E1E1E1;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
    
    def _style_button(self, button: QPushButton, color: str):
        """Apply consistent button styling"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color)};
            }}
        """)
    
    def _lighten_color(self, color: str) -> str:
        """Lighten a hex color"""
        color = color.lstrip('#')
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r = min(255, r + 20)
        g = min(255, g + 20)
        b = min(255, b + 20)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _darken_color(self, color: str) -> str:
        """Darken a hex color"""
        color = color.lstrip('#')
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r = max(0, r - 20)
        g = max(0, g - 20)
        b = max(0, b - 20)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _try_get_custom_ui(self):
        """Try to get custom UI widget from plugin"""
        try:
            # Get workspace path from self (now that we inherit from BaseWidget)
            workspace_path = self.workspace.workspace_path

            if not workspace_path:
                return None

            # Use ServerManager to get custom UI widget
            from server.server import ServerManager
            server_manager = ServerManager(workspace_path)

            # Prepare server config dict for custom UI
            server_config_dict = None
            if self.server_config:
                server_config_dict = {
                    'name': self.server_config.name,
                    'description': self.server_config.description,
                    'enabled': self.server_config.enabled,
                    'config': self.server_config.parameters,
                    'api_key': self.server_config.api_key,
                }

            # Call the ServerManager method to get the custom widget
            custom_widget = server_manager.get_plugin_ui_widget(
                self.plugin_info.name,
                server_config_dict
            )

            return custom_widget

        except Exception as e:
            logger.error(f"Failed to get custom UI from plugin: {e}", exc_info=True)
            return None

    def _on_custom_config_changed(self):
        """Handle configuration change from custom widget"""
        # This can be used to enable/disable save button or show unsaved changes
        pass

    def _on_validation_error(self, error_msg: str):
        """Handle validation error from custom widget"""
        logger.warning(f"Validation error: {error_msg}")
        QMessageBox.warning(self, tr("验证错误"), error_msg)
    
    def _on_save_clicked(self):
        """Handle save button click"""
        logger.info(f"_on_save_clicked called, custom_config_widget={self.custom_config_widget}")
        # Check if using custom UI
        if self.custom_config_widget:
            logger.info("Using custom UI save path")
            return self._on_save_clicked_custom()

        # Default form-based save
        logger.info("Using default form-based save path")
        # Validate required fields
        server_name = self.name_field.text().strip()
        if not server_name:
            QMessageBox.warning(self, tr("验证错误"), tr("请输入服务器名称"))
            return
        
        # Validate other required fields
        for field_name, field_info in self.field_widgets.items():
            widget = field_info["widget"]
            required = field_info["required"]
            
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if required and not value:
                    QMessageBox.warning(
                        self,
                        tr("验证错误"),
                        f"{tr('字段')} '{field_name}' {tr('是必填的')}"
                    )
                    return
        
        # Build configuration
        from server.server import ServerConfig
        from datetime import datetime
        
        # Collect parameters
        parameters = {}
        for field_name, field_info in self.field_widgets.items():
            widget = field_info["widget"]
            
            if isinstance(widget, QCheckBox):
                parameters[field_name] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                parameters[field_name] = widget.value()
            elif isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if value:
                    parameters[field_name] = value
        
        # Create or update config
        if self.is_edit_mode:
            # Update existing config
            config = self.server_config
            config.description = self.description_field.text().strip()
            config.enabled = self.enabled_checkbox.isChecked()
            config.endpoint = parameters.get("endpoint")
            config.api_key = parameters.get("api_key")
            config.parameters = parameters
            config.updated_at = datetime.now()
        else:
            # Create new config
            config = ServerConfig(
                name=server_name,
                server_type=self.plugin_info.engine or "custom",
                plugin_name=self.plugin_info.name,
                description=self.description_field.text().strip(),
                enabled=self.enabled_checkbox.isChecked(),
                endpoint=parameters.get("endpoint"),
                api_key=parameters.get("api_key"),
                parameters=parameters,
                metadata={
                    "plugin_version": self.plugin_info.version,
                    "created_via": "ui"
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        # Emit signal
        self.save_clicked.emit(server_name, config)
    
    def _on_save_clicked_custom(self):
        """Handle save button click for custom UI"""
        logger.info("_on_save_clicked_custom called")

        # Check if model exists and get validation errors before validating
        if hasattr(self.custom_config_widget, '_config_model'):
            config_model = self.custom_config_widget._config_model
            if hasattr(config_model, 'get_validation_errors'):
                errors = config_model.get_validation_errors()
                if errors:
                    logger.warning(f"Validation errors: {errors}")
                    QMessageBox.warning(self, tr("验证错误"), errors)
                    return

        # Validate custom widget config
        if hasattr(self.custom_config_widget, 'validate_config'):
            logger.info("Validating custom widget config")
            if not self.custom_config_widget.validate_config():
                logger.warning("Custom widget validation failed")
                # Validation error should have been emitted and shown by _on_validation_error
                return

        # Get config from custom widget
        if not hasattr(self.custom_config_widget, 'get_config'):
            logger.error("Custom widget does not implement get_config()")
            QMessageBox.warning(self, tr("错误"), "Custom widget does not implement get_config()")
            return

        try:
            config_data = self.custom_config_widget.get_config()
            logger.info(f"Got config from custom widget: {config_data}")
        except Exception as e:
            logger.error(f"Error getting config from custom widget: {e}", exc_info=True)
            QMessageBox.warning(self, tr("错误"), f"{tr('获取配置失败')}: {str(e)}")
            return
        
        # Build configuration
        from server.server import ServerConfig
        from datetime import datetime
        
        # Get server name from custom widget or use existing
        server_name = self.server_config.name if self.is_edit_mode else config_data.get('name', self.plugin_info.name)
        
        # Create or update config
        if self.is_edit_mode:
            # Update existing config
            config = self.server_config
            config.description = config_data.get('description', config.description)
            config.enabled = config_data.get('enabled', config.enabled)
            config.endpoint = config_data.get('server_url', config.endpoint)
            if 'api_key' in config_data:
                config.api_key = config_data.get('api_key')
            config.parameters = config_data
            config.updated_at = datetime.now()
        else:
            # Create new config
            config = ServerConfig(
                name=server_name,
                server_type=self.plugin_info.engine or "custom",
                plugin_name=self.plugin_info.name,
                description=config_data.get('description', ''),
                enabled=config_data.get('enabled', True),
                endpoint=config_data.get('server_url'),
                api_key=config_data.get('api_key'),
                parameters=config_data,
                metadata={
                    "plugin_version": self.plugin_info.version,
                    "created_via": "custom_ui"
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        # Emit signal
        self.save_clicked.emit(server_name, config)

