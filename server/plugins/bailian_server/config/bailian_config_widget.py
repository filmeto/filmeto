"""
Bailian Server Configuration Widget

Custom configuration UI for Alibaba Cloud Bailian server.
Supports both Bailian App and DashScope LLM chat configuration.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QFormLayout, QLineEdit,
    QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


_LINE_EDIT_STYLE = """
    QLineEdit {
        padding: 6px;
        background-color: #1e1e1e;
        border: 1px solid #3a3a3a;
        border-radius: 3px;
        color: #ffffff;
    }
    QLineEdit:focus { border-color: #3498db; }
"""

_CHECKBOX_STYLE = """
    QCheckBox {
        color: #cccccc;
        border: none;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 16px; height: 16px;
        border: 1px solid #3a3a3a;
        border-radius: 3px;
        background-color: #1e1e1e;
    }
    QCheckBox::indicator:checked {
        background-color: #3498db;
        border-color: #3498db;
    }
"""


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

        # DashScope LLM Settings
        llm_group = self._create_form_group("DashScope LLM Settings", [
            ("chat_enabled", "Enable LLM Chat", "checkbox", True, False,
             "Enable OpenAI-compatible chat completion via DashScope"),
            ("dashscope_api_key", "DashScope API Key", "password", "", False,
             "DashScope API key for LLM and image generation"),
            ("dashscope_endpoint", "Chat Endpoint", "text",
             "https://dashscope.aliyuncs.com/compatible-mode/v1", False,
             "DashScope OpenAI-compatible endpoint"),
            ("default_model", "Default Chat Model", "text", "qwen-max", False,
             "Default model for chat completions (e.g. qwen-max, qwen-plus, qwen-turbo)"),
        ])
        container_layout.addWidget(llm_group)

        # Bailian App Settings
        bailian_group = self._create_form_group("Bailian App Settings", [
            ("agent_key", "Agent Key / App ID", "text", "", False,
             "Bailian Agent Key or App ID (required only for Bailian App tool)"),
            ("endpoint", "Bailian API Endpoint", "text",
             "https://bailian.aliyuncs.com", False,
             "Bailian API endpoint (for Bailian App tool)"),
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

            if field_type == "checkbox":
                widget = QCheckBox()
                widget.setChecked(bool(default))
                widget.setToolTip(desc)
                widget.setStyleSheet(_CHECKBOX_STYLE)
                widget.stateChanged.connect(lambda _: self.config_changed.emit())
            elif field_type == "password":
                widget = QLineEdit()
                widget.setEchoMode(QLineEdit.Password)
                widget.setText(str(default) if default else "")
                widget.setToolTip(desc)
                widget.setStyleSheet(_LINE_EDIT_STYLE)
                widget.textChanged.connect(lambda: self.config_changed.emit())
            else:
                widget = QLineEdit()
                widget.setText(str(default) if default else "")
                widget.setToolTip(desc)
                widget.setStyleSheet(_LINE_EDIT_STYLE)
                widget.textChanged.connect(lambda: self.config_changed.emit())

            self.field_widgets[field_name] = widget
            form.addRow(label_widget, widget)

        layout.addLayout(form)
        return frame

    def _load_config(self):
        config = self.server_config.get('config', {})
        params = self.server_config.get('parameters', {})
        merged = {**params, **config}

        for name, widget in self.field_widgets.items():
            if name in merged:
                val = merged[name]
                if isinstance(widget, QCheckBox):
                    widget.setChecked(bool(val))
                else:
                    widget.setText(str(val))

    # Default DashScope models advertised when chat is enabled
    _DASHSCOPE_MODELS = [
        "qwen-max", "qwen-plus", "qwen-turbo", "qwen-long",
        "qwen-vl-max", "qwen-vl-plus",
    ]

    def get_config(self) -> Dict[str, Any]:
        result = {}
        for name, widget in self.field_widgets.items():
            if isinstance(widget, QCheckBox):
                result[name] = widget.isChecked()
            else:
                result[name] = widget.text()

        if result.get("chat_enabled"):
            result.setdefault("provider", "dashscope")
            default_model = result.get("default_model", "qwen-max")
            models = list(self._DASHSCOPE_MODELS)
            if default_model and default_model not in models:
                models.insert(0, default_model)
            result["models"] = models

        return result

    def validate_config(self) -> bool:
        config = self.get_config()
        if config.get("chat_enabled"):
            if not config.get("dashscope_api_key"):
                QMessageBox.warning(
                    self, "Validation Error",
                    "DashScope API Key is required when LLM Chat is enabled."
                )
                return False
        return True
