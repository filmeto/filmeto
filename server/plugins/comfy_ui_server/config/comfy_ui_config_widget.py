"""
ComfyUI Server Configuration Widget

Custom configuration UI for ComfyUI server with workflow management.
Designed to be embedded in the server_list dialog's ServerConfigView.
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame,
    QScrollArea, QFormLayout, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QFileDialog, QTabWidget, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

logger = logging.getLogger(__name__)

# Import ToolType from server API
try:
    from server.api.types import ToolType
except ImportError:
    # Fallback enum if import fails
    from enum import Enum
    class ToolType(str, Enum):
        TEXT2IMAGE = "text2image"
        IMAGE2IMAGE = "image2image"
        IMAGE2VIDEO = "image2video"
        TEXT2VIDEO = "text2video"
        SPEAK2VIDEO = "speak2video"
        TEXT2SPEAK = "text2speak"
        TEXT2MUSIC = "text2music"


class ComfyUIConfigWidget(QWidget):
    """Custom configuration widget for ComfyUI server"""
    
    # Signal emitted when configuration changes
    config_changed = Signal()
    
    def __init__(self, workspace_path: str, server_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.server_config = server_config or {}
        self.server_name = server_config.get('name', '') if server_config else ''
        
        # Built-in workflows directory (read-only templates)
        # Located in plugin directory: server/plugins/comfy_ui_server/workflows
        self.builtin_workflows_dir = Path(__file__).parent.parent / "workflows"
        
        # Workspace workflows directory (user-editable)
        # Located in workspace: workspace_path/servers/{server_name}/workflows
        if self.workspace_path and self.server_name:
            self.workspace_workflows_dir = self.workspace_path / "servers" / self.server_name / "workflows"
            self.workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.workspace_workflows_dir = None
        
        # Use workspace workflows dir as primary workflows dir for saving
        self.workflows_dir = self.workspace_workflows_dir if self.workspace_workflows_dir else self.builtin_workflows_dir
        
        # ToolType to workflow name mapping
        self.tooltype_workflow_map = {
            ToolType.TEXT2IMAGE: "text2image",
            ToolType.IMAGE2IMAGE: "image2image",
            ToolType.IMAGE2VIDEO: "image2video",
            ToolType.TEXT2VIDEO: "text2video",
            ToolType.SPEAK2VIDEO: "speak2video",
            ToolType.TEXT2SPEAK: "text2speak",
            ToolType.TEXT2MUSIC: "text2music",
        }
        
        self.field_widgets: Dict[str, QWidget] = {}
        self.workflows = []
        
        self._init_ui()
        self._load_config()
        self._initialize_default_workflows()
        self._load_workflows()
    
    def _init_ui(self):
        """Initialize the UI with tab layout"""
        # Main layout - vertical to accommodate tabs at top
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #1e1e1e;
                border-top: none; /* Remove top border to connect with tabs */
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 8px 16px;
                border: 1px solid #3a3a3a;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                min-width: 100px; /* Minimum width for better appearance */
                text-align: left;  /* Left align text */
            }
            QTabBar::tab:selected {
                background-color: #3a3a3a;
                color: #ffffff;
                border-bottom: 2px solid #1e1e1e; /* Connect with content area */
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
            }
        """)
        # Set tab position to ensure left alignment
        self.tab_widget.tabBar().setExpanding(False)  # Prevent tabs from expanding to fill width

        # Create pages
        self.service_page = self._create_service_page()
        self.workflow_page = self._create_workflow_page()

        # Add tabs
        self.tab_widget.addTab(self.service_page, "⚙ Service")
        self.tab_widget.addTab(self.workflow_page, "⚡ Workflows")

        main_layout.addWidget(self.tab_widget)
    
    
    def _create_service_page(self) -> QWidget:
        """Create service configuration page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 5, 10, 5)  # Reduced margins from 20,10,20,10 to 10,5,10,5
        layout.setSpacing(8)

        # Scroll area for form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")

        # Form container
        form_container = QWidget()
        form_container.setStyleSheet("background-color: #1e1e1e;")
        container_layout = QVBoxLayout(form_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # Connection settings group
        conn_group = self._create_form_group("Connection Settings", [
            ("server_url", "Server URL", "text", "http://192.168.1.100", True, "ComfyUI server address"),
            ("port", "Port", "number", 3000, True, "ComfyUI server port"),
            ("timeout", "Timeout (seconds)", "number", 120, False, "Request timeout in seconds"),
            ("enable_ssl", "Enable SSL", "boolean", False, False, "Use HTTPS connection")
        ])
        container_layout.addWidget(conn_group)
        
        # Authentication group
        auth_group = self._create_form_group("Authentication", [
            ("api_key", "API Key", "password", "", False, "Optional API key for authentication")
        ])
        container_layout.addWidget(auth_group)
        
        # Performance group
        perf_group = self._create_form_group("Performance", [
            ("max_concurrent_jobs", "Max Concurrent Jobs", "number", 1, False, "Maximum number of concurrent jobs"),
            ("queue_timeout", "Queue Timeout (seconds)", "number", 3200, False, "Maximum time to wait in queue")
        ])
        container_layout.addWidget(perf_group)
        
        container_layout.addStretch()
        
        scroll_area.setWidget(form_container)
        layout.addWidget(scroll_area, 1)
        
        return page
    
    def _create_workflow_page(self) -> QWidget:
        """Create workflow management page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        add_btn = QPushButton("+ Add Workflow")
        add_btn.setFixedHeight(28)
        add_btn.clicked.connect(self._on_add_workflow)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                background-color: #3498db;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
        """)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Workflow list with custom items
        self.workflow_list = QListWidget()
        self.workflow_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 0px;
                margin: 4px 0;
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
                border: none;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.workflow_list, 1)

        return page
    
    def _create_form_group(self, title: str, fields: list) -> QWidget:
        """Create a form group widget"""
        group_frame = QFrame()
        group_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """)

        group_layout = QVBoxLayout(group_frame)
        group_layout.setContentsMargins(10, 8, 10, 8)  # Reduced margins from 15,12,15,12 to 10,8,10,8
        group_layout.setSpacing(6)

        # Group label
        group_label = QLabel(title)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        group_label.setFont(font)
        group_label.setStyleSheet("color: #ffffff; border: none;")
        group_layout.addWidget(group_label)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setSpacing(5)
        form_layout.setHorizontalSpacing(8)

        # Add fields
        for field_name, label, field_type, default, required, description in fields:
            self._add_field_to_form(form_layout, field_name, label, field_type, default, required, description)

        group_layout.addLayout(form_layout)

        return group_frame
    
    def _add_field_to_form(self, form_layout: QFormLayout, field_name: str, label: str, 
                           field_type: str, default: Any, required: bool, description: str):
        """Add a field to the form"""
        # Create label
        label_text = label + (" *" if required else "")
        label_widget = QLabel(label_text)
        label_widget.setStyleSheet("color: #cccccc; font-size: 11px;")
        label_widget.setToolTip(description)
        
        # Create widget based on type
        if field_type == "text":
            widget = QLineEdit()
            widget.setText(str(default))
            widget.setStyleSheet(self._get_input_style())
        elif field_type == "password":
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.Password)
            widget.setText(str(default))
            widget.setStyleSheet(self._get_input_style())
        elif field_type == "number":
            widget = QSpinBox()
            widget.setRange(0, 99999)
            widget.setValue(int(default))
            widget.setStyleSheet(self._get_input_style())
        elif field_type == "boolean":
            widget = QCheckBox()
            widget.setChecked(bool(default))
            widget.setStyleSheet("color: #ffffff;")
        else:
            widget = QLineEdit()
            widget.setText(str(default))
            widget.setStyleSheet(self._get_input_style())
        
        widget.setFixedWidth(240)

        # Store widget reference
        self.field_widgets[field_name] = widget

        # Create container
        widget_container = QWidget()
        widget_layout = QVBoxLayout(widget_container)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.setSpacing(2)

        widget_layout.addWidget(widget)

        # Add description
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #FFFFFF; font-size: 8px;")  # Reduced font size from 9px to 8px
            desc_label.setWordWrap(True)
            desc_label.setMaximumWidth(240)
            widget_layout.addWidget(desc_label)
        
        # Add to form
        form_layout.addRow(label_widget, widget_container)
        
        # Connect change signal
        if hasattr(widget, 'textChanged'):
            widget.textChanged.connect(lambda: self.config_changed.emit())
        elif hasattr(widget, 'valueChanged'):
            widget.valueChanged.connect(lambda: self.config_changed.emit())
        elif hasattr(widget, 'stateChanged'):
            widget.stateChanged.connect(lambda: self.config_changed.emit())
    
    def _get_input_style(self) -> str:
        """Get input field stylesheet"""
        return """
            QLineEdit, QSpinBox {
                padding: 4px 8px;
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #ffffff;
                font-size: 10px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #3498db;
            }
        """
    
    def _get_action_button_style(self, bg_color: str = "#555555", hover_color: str = "#666666") -> str:
        """Get action button stylesheet"""
        return f"""
            QPushButton {{
                padding: 4px 10px;
                background-color: {bg_color};
                border: none;
                border-radius: 3px;
                color: #ffffff;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """
    
    def _load_config(self):
        """Load current configuration"""
        if not self.server_config:
            return
        
        config = self.server_config.get('config', {})
        
        for field_name, widget in self.field_widgets.items():
            value = config.get(field_name)
            if value is not None:
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
    
    def _initialize_default_workflows(self):
        """Initialize default workflow files for each ToolType in workspace directory"""
        # Only initialize in workspace directory, not in builtin directory
        if not self.workspace_workflows_dir:
            return
        
        self.workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
        
        for tool_type, workflow_name in self.tooltype_workflow_map.items():
            workflow_file = self.workspace_workflows_dir / f"{workflow_name}.json"
            
            # Only create if it doesn't exist (don't overwrite existing)
            if not workflow_file.exists():
                # Try to copy from builtin templates first
                builtin_file = self.builtin_workflows_dir / f"{workflow_name}.json"
                if builtin_file.exists():
                    try:
                        import shutil
                        shutil.copy2(builtin_file, workflow_file)
                        continue
                    except Exception as e:
                        logger.error(f"Failed to copy builtin workflow {builtin_file}: {e}")
                
                # Create empty workflow if builtin doesn't exist
                empty_workflow = {
                    "prompt": {},
                    "extra": {},
                    "filmeto": {
                        "name": workflow_name.replace('_', ' ').title(),
                        "type": workflow_name,
                        "description": f"Workflow for {workflow_name}",
                        "node_mapping": {}
                    }
                }
                try:
                    with open(workflow_file, 'w', encoding='utf-8') as f:
                        json.dump(empty_workflow, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"Failed to create default workflow {workflow_file}: {e}")
    
    def _load_workflows(self):
        """Load workflows from both workspace and builtin directories, merge and deduplicate"""
        self.workflows = []
        self.workflow_list.clear()
        
        # Track loaded workflows by name to avoid duplicates
        loaded_workflows = {}  # workflow_name -> workflow_entry
        
        # First, load from workspace directory (user-editable, takes priority)
        if self.workspace_workflows_dir and self.workspace_workflows_dir.exists():
            self._load_workflows_from_dir(self.workspace_workflows_dir, loaded_workflows, is_builtin=False)
        
        # Then, load from builtin directory (templates, only if not already loaded)
        if self.builtin_workflows_dir and self.builtin_workflows_dir.exists():
            self._load_workflows_from_dir(self.builtin_workflows_dir, loaded_workflows, is_builtin=True)
        
        # Convert dict to list
        self.workflows = list(loaded_workflows.values())
        
        # Update UI
        self._refresh_workflow_list()
    
    def _load_workflows_from_dir(self, workflows_dir: Path, loaded_workflows: Dict, is_builtin: bool):
        """Load workflows from a specific directory"""
        # Load workflows for each ToolType
        for tool_type, workflow_name in self.tooltype_workflow_map.items():
            workflow_file = workflows_dir / f"{workflow_name}.json"
            
            if not workflow_file.exists():
                continue
            
            # Skip if already loaded from workspace (workspace takes priority)
            if workflow_name in loaded_workflows and not is_builtin:
                continue
            
            try:
                # Load workflow file
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                
                # Extract filmeto configuration from filmeto key
                filmeto_config = workflow_data.get('filmeto', {})
                
                if filmeto_config:
                    # Has filmeto config - use it
                    workflow_entry = {
                        'name': filmeto_config.get('name', workflow_name.replace('_', ' ').title()),
                        'type': filmeto_config.get('type', workflow_name),
                        'description': filmeto_config.get('description', f"Workflow for {workflow_name}"),
                        'file_path': workflow_file,
                        'node_mapping': filmeto_config.get('node_mapping', {}),
                        'is_builtin': is_builtin
                    }
                else:
                    # No filmeto config - check if it's old format metadata file
                    if isinstance(workflow_data, dict) and "name" in workflow_data and "type" in workflow_data:
                        # Old format metadata file
                        workflow_entry = dict(workflow_data)
                        workflow_entry['file_path'] = workflow_file
                        workflow_entry['is_builtin'] = is_builtin
                    else:
                        # Raw workflow JSON without filmeto config - create default entry
                        workflow_entry = {
                            'name': workflow_name.replace('_', ' ').title(),
                            'type': workflow_name,
                            'file_path': workflow_file,
                            'description': f"Workflow for {workflow_name} (needs configuration)",
                            'is_builtin': is_builtin
                        }
                
                # Store by workflow_name (type) for deduplication
                loaded_workflows[workflow_name] = workflow_entry
                
            except Exception as e:
                logger.error(f"Failed to load workflow {workflow_file}: {e}")
                # Create default entry on error
                if workflow_name not in loaded_workflows:
                    workflow_entry = {
                        'name': workflow_name.replace('_', ' ').title(),
                        'type': workflow_name,
                        'file_path': workflow_file,
                        'description': f"Workflow for {workflow_name}",
                        'is_builtin': is_builtin
                    }
                    loaded_workflows[workflow_name] = workflow_entry
        
        # Load any additional workflow files that don't match ToolType patterns
        for workflow_file in workflows_dir.glob("*.json"):
            workflow_name = workflow_file.stem
            
            # Skip if already loaded
            if workflow_name in loaded_workflows:
                continue
            
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                
                if isinstance(workflow_data, dict):
                    # Check for filmeto key first
                    filmeto_config = workflow_data.get('filmeto', {})
                    if filmeto_config:
                        workflow_entry = {
                            'name': filmeto_config.get('name', workflow_name.replace('_', ' ').title()),
                            'type': filmeto_config.get('type', 'custom'),
                            'description': filmeto_config.get('description', f"Custom workflow"),
                            'file_path': workflow_file,
                            'node_mapping': filmeto_config.get('node_mapping', {}),
                            'is_builtin': is_builtin
                        }
                    elif "name" in workflow_data and "type" in workflow_data:
                        # Old format metadata file
                        workflow_entry = dict(workflow_data)
                        workflow_entry['file_path'] = workflow_file
                        workflow_entry['is_builtin'] = is_builtin
                    else:
                        # Try to determine type from filename
                        tool_type = self._guess_tool_type_from_filename(workflow_name)
                        workflow_entry = {
                            'name': workflow_name.replace('_', ' ').title(),
                            'type': tool_type or 'custom',
                            'file_path': workflow_file,
                            'description': f"Workflow for {tool_type or 'custom'} (needs configuration)",
                            'is_builtin': is_builtin
                        }
                    
                    loaded_workflows[workflow_name] = workflow_entry
            except Exception as e:
                logger.error(f"Failed to load workflow {workflow_file}: {e}")
    
    def _guess_tool_type_from_filename(self, filename: str) -> Optional[str]:
        """Guess tool type from filename"""
        filename_lower = filename.lower()
        for tool_type, workflow_name in self.tooltype_workflow_map.items():
            if workflow_name in filename_lower:
                return workflow_name
        return None
    
    def _refresh_workflow_list(self):
        """Refresh the workflow list UI"""
        self.workflow_list.clear()
        
        # Group workflows by type
        workflows_by_type = {}
        for workflow in self.workflows:
            tool_type = workflow.get('type', 'unknown')
            if tool_type not in workflows_by_type:
                workflows_by_type[tool_type] = []
            workflows_by_type[tool_type].append(workflow)
        
        # Add workflows sorted by ToolType order
        for tool_type in self.tooltype_workflow_map.values():
            if tool_type in workflows_by_type:
                for workflow in workflows_by_type[tool_type]:
                    self._add_workflow_item(workflow)
        
        # Add any remaining workflows
        for tool_type, workflows in workflows_by_type.items():
            if tool_type not in self.tooltype_workflow_map.values():
                for workflow in workflows:
                    self._add_workflow_item(workflow)
    
    def _add_workflow_item(self, workflow: Dict[str, Any]):
        """Add a workflow item to the list with edit and configure buttons"""
        # Create item widget
        item_widget = QWidget()
        item_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(14, 12, 14, 12)
        item_layout.setSpacing(14)
        
        # Workflow info
        info_widget = QWidget()
        info_widget.setStyleSheet("background-color: transparent;")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(5)
        
        # Name
        name_label = QLabel(workflow.get('name', 'Unnamed Workflow'))
        name_font = QFont()
        name_font.setPointSize(12)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #ffffff; border: none;")
        info_layout.addWidget(name_label)
        
        # Type and description
        type_text = f"Type: {workflow.get('type', 'Unknown')}"
        if workflow.get('description'):
            type_text += f" • {workflow['description']}"
        type_label = QLabel(type_text)
        type_label.setStyleSheet("color: #888888; font-size: 10px; border: none;")
        type_label.setWordWrap(True)
        info_layout.addWidget(type_label)
        
        item_layout.addWidget(info_widget, 1)
        
        # Action buttons container
        buttons_widget = QWidget()
        buttons_widget.setStyleSheet("background-color: transparent;")
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)
        
        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(65, 30)
        edit_btn.clicked.connect(lambda checked=False, w=workflow: self._on_edit_workflow(w))
        edit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        edit_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 14px;
                background-color: #555555;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        buttons_layout.addWidget(edit_btn)
        
        # Config button
        config_btn = QPushButton("Config")
        config_btn.setFixedSize(65, 30)
        config_btn.clicked.connect(lambda checked=False, w=workflow: self._on_configure_workflow(w))
        config_btn.setCursor(QCursor(Qt.PointingHandCursor))
        config_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 14px;
                background-color: #3498db;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
        """)
        buttons_layout.addWidget(config_btn)
        
        item_layout.addWidget(buttons_widget)
        
        # Create list item
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        item.setData(Qt.UserRole, workflow)
        self.workflow_list.addItem(item)
        self.workflow_list.setItemWidget(item, item_widget)
    
    def _on_add_workflow(self):
        """Handle add workflow button click"""
        if not self.workflows_dir:
            QMessageBox.warning(self, "No Server", "Please save the server configuration first.")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Workflow File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Import workflow configuration dialog
        try:
            from server.plugins.comfy_ui_server.config.workflow_config_dialog import WorkflowConfigDialog
            
            dialog = WorkflowConfigDialog(file_path, self.workflows_dir, self)
            if dialog.exec() == QDialog.Accepted:
                self._load_workflows()
                self.config_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open workflow configuration: {e}")
    
    def _on_edit_workflow(self, workflow: Dict[str, Any]):
        """Handle edit workflow button click - opens JSON editor"""
        workflow_type = workflow.get('type', 'workflow')
        is_builtin = workflow.get('is_builtin', False)
        
        # Determine target file path (always save to workspace, not builtin)
        if not self.workspace_workflows_dir:
            QMessageBox.warning(self, "Error", "Workspace workflows directory not available.")
            return
        
        target_workflow_file = self.workspace_workflows_dir / f"{workflow_type}.json"
        
        # Source file for loading (prefer workspace, fallback to builtin)
        source_workflow_file = None
        if target_workflow_file.exists():
            source_workflow_file = target_workflow_file
        elif is_builtin:
            builtin_file = workflow.get('file_path')
            if builtin_file and Path(builtin_file).exists():
                # Copy from builtin to workspace
                try:
                    import shutil
                    self.workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(builtin_file, target_workflow_file)
                    source_workflow_file = target_workflow_file
                except Exception as e:
                    logger.error(f"Failed to copy builtin workflow: {e}")
        
        # If still no source file, create empty one
        if not source_workflow_file or not Path(source_workflow_file).exists():
            empty_workflow = {
                "prompt": {},
                "extra": {},
                "filmeto": {
                    "name": workflow.get('name', workflow_type.replace('_', ' ').title()),
                    "type": workflow_type,
                    "description": workflow.get('description', ''),
                    "node_mapping": workflow.get('node_mapping', {})
                }
            }
            try:
                self.workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
                with open(target_workflow_file, 'w', encoding='utf-8') as f:
                    json.dump(empty_workflow, f, indent=2, ensure_ascii=False)
                source_workflow_file = target_workflow_file
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create workflow file:\n{str(e)}"
                )
                return
        
        # Open JSON editor dialog
        try:
            from server.plugins.comfy_ui_server.config.workflow_json_editor_dialog import WorkflowJsonEditorDialog
            
            dialog = WorkflowJsonEditorDialog(source_workflow_file, self)
            if dialog.exec() == QDialog.Accepted:
                # Reload workflows
                self._load_workflows()
                self.config_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open workflow editor: {e}")
    
    def _on_configure_workflow(self, workflow: Optional[Dict[str, Any]] = None):
        """Handle configure workflow button click - opens config dialog"""
        if workflow is None:
            # Try to get from selected item
            current_item = self.workflow_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "No Selection", "Please select a workflow to configure.")
                return
            workflow = current_item.data(Qt.UserRole)
        
        workflow_type = workflow.get('type', 'workflow')
        is_builtin = workflow.get('is_builtin', False)
        
        # Determine target file path (always save to workspace, not builtin)
        if not self.workspace_workflows_dir:
            QMessageBox.warning(self, "Error", "Workspace workflows directory not available.")
            return
        
        target_workflow_file = self.workspace_workflows_dir / f"{workflow_type}.json"
        
        # Source file for loading (prefer workspace, fallback to builtin)
        source_workflow_file = None
        if target_workflow_file.exists():
            source_workflow_file = target_workflow_file
        elif is_builtin:
            source_workflow_file = workflow.get('file_path')
        
        # If source file doesn't exist, try to copy from builtin
        if not source_workflow_file or not Path(source_workflow_file).exists():
            if is_builtin:
                builtin_file = workflow.get('file_path')
                if builtin_file and Path(builtin_file).exists():
                    try:
                        import shutil
                        self.workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(builtin_file, target_workflow_file)
                        source_workflow_file = target_workflow_file
                    except Exception as e:
                        logger.error(f"Failed to copy builtin workflow: {e}")
        
        # If still no source file, create empty one
        if not source_workflow_file or not Path(source_workflow_file).exists():
            empty_workflow = {
                "prompt": {},
                "extra": {},
                "filmeto": {
                    "name": workflow.get('name', workflow_type.replace('_', ' ').title()),
                    "type": workflow_type,
                    "description": workflow.get('description', ''),
                    "node_mapping": workflow.get('node_mapping', {})
                }
            }
            try:
                self.workspace_workflows_dir.mkdir(parents=True, exist_ok=True)
                with open(target_workflow_file, 'w', encoding='utf-8') as f:
                    json.dump(empty_workflow, f, indent=2, ensure_ascii=False)
                source_workflow_file = target_workflow_file
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create workflow file:\n{str(e)}"
                )
                return
        
        # Load workflow data to pass to dialog
        try:
            with open(source_workflow_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # Extract filmeto config for existing_config parameter
            existing_config = workflow_data.get('filmeto', workflow)
        except Exception as e:
            existing_config = workflow
        
        # Open workflow configuration dialog (save to workspace directory)
        try:
            from server.plugins.comfy_ui_server.config.workflow_config_dialog import WorkflowConfigDialog
            
            dialog = WorkflowConfigDialog(str(source_workflow_file), self.workspace_workflows_dir, self, existing_config)
            if dialog.exec() == QDialog.Accepted:
                # Reload workflows
                self._load_workflows()
                self.config_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open workflow configuration: {e}")
            logger.error(f"Failed to open workflow configuration: {e}", exc_info=True)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration from widgets"""
        config = {}
        
        for field_name, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                config[field_name] = widget.text()
            elif isinstance(widget, QSpinBox):
                config[field_name] = widget.value()
            elif isinstance(widget, QCheckBox):
                config[field_name] = widget.isChecked()
        
        return config
    
    def validate_config(self) -> bool:
        """Validate current configuration"""
        config = self.get_config()
        
        # Check required fields
        if not config.get('server_url'):
            QMessageBox.warning(self, "Validation Error", "Server URL is required.")
            return False
        
        if not config.get('port'):
            QMessageBox.warning(self, "Validation Error", "Port is required.")
            return False
        
        return True

