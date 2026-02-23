"""
Bailian Server Configuration Widget

Custom configuration UI for Alibaba Cloud Bailian server.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QFormLayout, QLineEdit, 
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class BailianConfigWidget(QWidget):
    """Custom configuration widget for Bailian server"""
    
    config_changed = Signal()
    
    def __init__(self, workspace_path: str, server_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        
        self.workspace_path = workspace_path
        self.server_config = server_config or {}
        self.field_widgets: Dict[str, QWidget] = {}
        
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e1e;")
        container_layout = QVBoxLayout(container)
        
        # Bailian Settings
        bailian_group = self._create_form_group("Bailian Settings", [
            ("agent_key", "Agent Key / App ID", "text", "", True, "Bailian Agent Key or App ID"),
            ("endpoint", "API Endpoint", "text", "https://bailian.aliyuncs.com", False, "Bailian API endpoint URL"),
        ])
        container_layout.addWidget(bailian_group)
        
        container_layout.addStretch()
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
    
    def _create_form_group(self, title: str, fields: list) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                margin-bottom: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setFont(QFont("Arial", 11, QFont.Bold))
        label.setStyleSheet("color: #ffffff; border: none; margin-bottom: 5px;")
        layout.addWidget(label)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        for field_name, label_text, field_type, default, required, desc in fields:
            label_widget = QLabel(label_text + (" *" if required else ""))
            label_widget.setStyleSheet("color: #cccccc; border: none;")
            
            if field_type == "password":
                widget = QLineEdit()
                widget.setEchoMode(QLineEdit.Password)
            else:
                widget = QLineEdit()
            
            widget.setText(str(default))
            widget.setToolTip(desc)
            widget.setStyleSheet("""
                QLineEdit {
                    padding: 6px;
                    background-color: #1e1e1e;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    color: #ffffff;
                }
                QLineEdit:focus { border-color: #3498db; }
            """)
            
            self.field_widgets[field_name] = widget
            form.addRow(label_widget, widget)
            widget.textChanged.connect(lambda: self.config_changed.emit())
            
        layout.addLayout(form)
        return frame

    def _load_config(self):
        config = self.server_config.get('config', {})
        for name, widget in self.field_widgets.items():
            if name in config:
                widget.setText(str(config[name]))

    def get_config(self) -> Dict[str, Any]:
        return {name: widget.text() for name, widget in self.field_widgets.items()}

    def validate_config(self) -> bool:
        config = self.get_config()
        if not config.get('agent_key'):
            QMessageBox.warning(self, "Validation Error", "Agent Key / App ID is required.")
            return False
        return True
