"""
Server Management Views

Provides modular views for server list and server configuration that can be
switched within a single dialog (Mac-style preferences).
"""

import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit, QCheckBox,
    QSpinBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.base_widget import BaseWidget

from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class ServerItemWidget(QWidget):
    """
    Custom widget for displaying server information in list.
    """
    
    # Signals
    enable_clicked = Signal(str, bool)  # server_name, new_enabled_state
    edit_clicked = Signal(str)  # server_name
    delete_clicked = Signal(str)  # server_name
    
    def __init__(self, server, parent=None):
        super().__init__(parent)
        self.server = server
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Status indicator (colored circle)
        self.status_indicator = QLabel("●", self)
        self.status_indicator.setFixedSize(16, 16)
        status_font = QFont("Arial", 14, QFont.Bold)
        self.status_indicator.setFont(status_font)
        
        if server.is_enabled:
            self.status_indicator.setStyleSheet("color: #4CAF50;")  # Green
        else:
            self.status_indicator.setStyleSheet("color: #F44336;")  # Red
        
        layout.addWidget(self.status_indicator)
        
        # Server info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Name and type
        name_label = QLabel(f"{server.name} ({server.server_type})", self)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #E1E1E1;")
        info_layout.addWidget(name_label)
        
        # Description
        desc_label = QLabel(server.config.description or tr("无描述"), self)
        desc_label.setStyleSheet("color: #999999; font-size: 10px;")
        info_layout.addWidget(desc_label)

        # Plugin name
        plugin_label = QLabel(f"{tr('插件')}: {server.config.plugin_name}", self)
        plugin_label.setStyleSheet("color: #888888; font-size: 9px;")
        info_layout.addWidget(plugin_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        
        # Enable/Disable toggle button
        self.toggle_button = QPushButton(tr("禁用") if server.is_enabled else tr("启用"), self)
        self.toggle_button.setFixedSize(60, 28)
        self.toggle_button.clicked.connect(self._on_toggle_clicked)
        self._style_button(self.toggle_button, "#FF9800" if server.is_enabled else "#4CAF50")
        button_layout.addWidget(self.toggle_button)

        # Edit button
        self.edit_button = QPushButton(tr("编辑"), self)
        self.edit_button.setFixedSize(50, 28)
        self.edit_button.clicked.connect(lambda: self.edit_clicked.emit(server.name))
        self._style_button(self.edit_button, "#2196F3")
        button_layout.addWidget(self.edit_button)

        # Delete button (disabled for default servers)
        self.delete_button = QPushButton(tr("删除"), self)
        self.delete_button.setFixedSize(50, 28)
        self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(server.name))
        
        if server.name in ["local", "filmeto"]:
            self.delete_button.setEnabled(False)
            self._style_button(self.delete_button, "#555555")
        else:
            self._style_button(self.delete_button, "#F44336")
        
        button_layout.addWidget(self.delete_button)
        
        layout.addLayout(button_layout)
    
    def _style_button(self, button: QPushButton, color: str):
        """Apply consistent button styling"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #888888;
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
    
    def _on_toggle_clicked(self):
        """Handle toggle button click"""
        new_state = not self.server.is_enabled
        self.enable_clicked.emit(self.server.name, new_state)


class ServerListView(QWidget):
    """
    View for displaying list of servers.
    """
    
    # Signals
    server_selected_for_edit = Signal(str)  # server_name
    server_toggled = Signal(str, bool)  # server_name, enabled
    server_deleted = Signal(str)  # server_name
    add_server_clicked = Signal()
    refresh_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_manager = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Server list
        self.server_list = QListWidget(self)
        self.server_list.setSelectionMode(QListWidget.NoSelection)
        self.server_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                color: #E1E1E1;
            }
            QListWidget::item {
                border-bottom: 1px solid #3c3c3c;
                padding: 4px;
            }
            QListWidget::item:hover {
                background-color: #323232;
            }
            QListWidget::item:selected {
                background-color: #404040;
            }
        """)
        layout.addWidget(self.server_list)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel(self)
        self.status_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; }")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
    
    def set_server_manager(self, server_manager):
        """Set the server manager and load servers"""
        self.server_manager = server_manager
        self.load_servers()
    
    def load_servers(self):
        """Load servers from server manager"""
        if not self.server_manager:
            return
        
        # Clear existing items
        self.server_list.clear()
        
        # Get servers
        servers = self.server_manager.list_servers()
        
        if not servers:
            # Show empty state
            item = QListWidgetItem(self.server_list)
            empty_widget = QLabel(tr("暂无服务器配置"), self)
            empty_widget.setAlignment(Qt.AlignCenter)
            empty_widget.setStyleSheet("QLabel { color: #666666; padding: 40px; }")
            item.setSizeHint(empty_widget.sizeHint())
            self.server_list.addItem(item)
            self.server_list.setItemWidget(item, empty_widget)
        else:
            # Add server items
            for server in servers:
                item = QListWidgetItem(self.server_list)
                server_widget = ServerItemWidget(server, self)
                
                # Connect signals
                server_widget.enable_clicked.connect(self.server_toggled.emit)
                server_widget.edit_clicked.connect(self.server_selected_for_edit.emit)
                server_widget.delete_clicked.connect(self.server_deleted.emit)
                
                item.setSizeHint(server_widget.sizeHint())
                self.server_list.addItem(item)
                self.server_list.setItemWidget(item, server_widget)
        
        # Update status
        active_count = sum(1 for s in servers if s.is_enabled)
        inactive_count = sum(1 for s in servers if not s.is_enabled)
        self.status_label.setText(
            f"{tr('总计')}: {len(servers)} | "
            f"{tr('活跃')}: {active_count} | "
            f"{tr('禁用')}: {inactive_count}"
        )


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
        
        # Clear existing layout
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        
        # Build UI
        self._build_config_ui()
    
    def _clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _build_config_ui(self):
        """Build the configuration UI based on plugin info (should now be handled by plugin's init_ui)"""
        # Check if plugin has custom UI
        custom_widget = self._try_get_custom_ui()
        if custom_widget:
            # Use custom UI from plugin
            self.custom_config_widget = custom_widget
            self.main_layout.addWidget(custom_widget)

            # Connect config changed signal if available
            if hasattr(custom_widget, 'config_changed'):
                custom_widget.config_changed.connect(self._on_custom_config_changed)

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
                    'config': self.server_config.parameters
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
    
    def _on_save_clicked(self):
        """Handle save button click"""
        # Check if using custom UI
        if self.custom_config_widget:
            return self._on_save_clicked_custom()
        
        # Default form-based save
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
        # Validate custom widget config
        if hasattr(self.custom_config_widget, 'validate_config'):
            if not self.custom_config_widget.validate_config():
                return
        
        # Get config from custom widget
        if not hasattr(self.custom_config_widget, 'get_config'):
            QMessageBox.warning(self, tr("错误"), "Custom widget does not implement get_config()")
            return
        
        config_data = self.custom_config_widget.get_config()
        
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

