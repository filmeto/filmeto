"""
Bailian Server Configuration Widget

Simplified configuration UI for Alibaba Cloud DashScope (Bailian) server.
Only requires a single API Key for authentication.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QFormLayout, QLineEdit,
    QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from server.plugins.bailian_server.models_config import models_config, CODING_PLAN_PREFIX


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
    """Simplified configuration widget for Bailian server - Only API Key needed."""

    config_changed = Signal()

    def __init__(self, workspace_path: str, server_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)

        self.workspace_path = workspace_path
        self.server_config = server_config or {}
        self.field_widgets: Dict[str, QWidget] = {}
        # Store label widgets for show/hide
        self.label_widgets: Dict[str, QLabel] = {}

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

        # Help text
        help_label = QLabel(
            "获取 API Key: 阿里云控制台 → DashScope → API-KEY管理\n"
            "文档: https://help.aliyun.com/zh/model-studio/developer-reference/api-key-management"
        )
        help_label.setStyleSheet("color: #888888; padding: 10px; background-color: #252525; border-radius: 4px;")
        help_label.setWordWrap(True)
        container_layout.addWidget(help_label)

        # API Key Settings group (includes Coding Plan)
        self.api_group = self._create_api_group()
        container_layout.addWidget(self.api_group)

        # Model Settings (Optional)
        model_group = self._create_form_group("Model Settings (Optional)", [
            ("default_model", "Default Chat Model", "text", "qwen-max", False,
             "Default model for chat (e.g., qwen-max, qwen-plus, qwen-turbo)"),
            ("default_image_model", "Default Image Model", "text", "wanx2.1-t2i-turbo", False,
             "Default model for text-to-image"),
        ])
        container_layout.addWidget(model_group)

        container_layout.addStretch()
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)

    def _create_api_group(self) -> QFrame:
        """Create API Key settings group with dynamic Coding Plan API key field."""
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
        label = QLabel("API Key Settings")
        label.setFont(QFont("Arial", 11, QFont.Bold))
        label.setStyleSheet("color: #ffffff; border: none; margin-bottom: 5px;")
        layout.addWidget(label)

        form = QFormLayout()
        form.setSpacing(10)

        # DashScope API Key
        api_key_label = QLabel("API Key *")
        api_key_label.setStyleSheet("color: #cccccc; border: none;")
        api_key_widget = QLineEdit()
        api_key_widget.setEchoMode(QLineEdit.Password)
        api_key_widget.setText("")
        api_key_widget.setToolTip("DashScope API Key (required)")
        api_key_widget.setStyleSheet(_LINE_EDIT_STYLE)
        api_key_widget.textChanged.connect(lambda: self.config_changed.emit())
        self.field_widgets["api_key"] = api_key_widget
        self.label_widgets["api_key"] = api_key_label
        form.addRow(api_key_label, api_key_widget)

        # Coding Plan enable checkbox
        coding_plan_enabled_label = QLabel("Enable Coding Plan")
        coding_plan_enabled_label.setStyleSheet("color: #cccccc; border: none;")
        coding_plan_enabled_widget = QCheckBox()
        coding_plan_enabled_widget.setChecked(False)
        coding_plan_enabled_widget.setToolTip(
            "Enable Coding Plan for AI coding assistant (requires separate subscription)"
        )
        coding_plan_enabled_widget.setStyleSheet(_CHECKBOX_STYLE)
        coding_plan_enabled_widget.stateChanged.connect(self._on_coding_plan_enabled_changed)
        self.field_widgets["coding_plan_enabled"] = coding_plan_enabled_widget
        self.label_widgets["coding_plan_enabled"] = coding_plan_enabled_label
        form.addRow(coding_plan_enabled_label, coding_plan_enabled_widget)

        # Coding Plan API Key (hidden by default)
        coding_plan_api_key_label = QLabel("Coding Plan API Key")
        coding_plan_api_key_label.setStyleSheet("color: #cccccc; border: none;")
        coding_plan_api_key_widget = QLineEdit()
        coding_plan_api_key_widget.setEchoMode(QLineEdit.Password)
        coding_plan_api_key_widget.setText("")
        coding_plan_api_key_widget.setToolTip("Coding Plan API Key (format: sk-sp-xxxxx)")
        coding_plan_api_key_widget.setStyleSheet(_LINE_EDIT_STYLE)
        coding_plan_api_key_widget.textChanged.connect(lambda: self.config_changed.emit())
        self.field_widgets["coding_plan_api_key"] = coding_plan_api_key_widget
        self.label_widgets["coding_plan_api_key"] = coding_plan_api_key_label
        form.addRow(coding_plan_api_key_label, coding_plan_api_key_widget)

        # Hide Coding Plan API Key by default
        coding_plan_api_key_label.setVisible(False)
        coding_plan_api_key_widget.setVisible(False)

        layout.addLayout(form)
        return frame

    def _on_coding_plan_enabled_changed(self, state):
        """Handle Coding Plan enabled checkbox state change."""
        enabled = state == Qt.Checked
        # Show/hide Coding Plan API Key field
        self.label_widgets["coding_plan_api_key"].setVisible(enabled)
        self.field_widgets["coding_plan_api_key"].setVisible(enabled)
        # Force layout update to adjust frame height
        self.api_group.adjustSize()
        self.config_changed.emit()

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
            self.label_widgets[field_name] = label_widget
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

        # Update Coding Plan API Key visibility based on loaded config
        coding_plan_enabled = self.field_widgets.get("coding_plan_enabled")
        if coding_plan_enabled:
            enabled = coding_plan_enabled.isChecked()
            self.label_widgets["coding_plan_api_key"].setVisible(enabled)
            self.field_widgets["coding_plan_api_key"].setVisible(enabled)
            # Adjust frame height if Coding Plan is enabled
            if enabled:
                self.api_group.adjustSize()

    def get_config(self) -> Dict[str, Any]:
        result = {}
        for name, widget in self.field_widgets.items():
            if isinstance(widget, QCheckBox):
                result[name] = widget.isChecked()
            else:
                result[name] = widget.text()

        # Always enable chat provider
        result["provider"] = "dashscope"
        default_model = result.get("default_model", "qwen-max")

        # Get DashScope models from config
        models = models_config.get_dashscope_models()
        if default_model and default_model not in models:
            models.insert(0, default_model)
        result["models"] = models

        # Add Coding Plan models if enabled (with prefix for UI)
        if result.get("coding_plan_enabled") and result.get("coding_plan_api_key"):
            result["coding_plan_endpoint"] = models_config.get_coding_plan_endpoint()
            # Models with prefix for UI display
            result["coding_plan_models"] = models_config.get_coding_plan_models(with_prefix=True)

        return result

    def validate_config(self) -> bool:
        config = self.get_config()
        if not config.get("api_key"):
            QMessageBox.warning(
                self, "Validation Error",
                "API Key is required.\n\n"
                "Get your API Key from:\n"
                "阿里云控制台 → DashScope → API-KEY管理"
            )
            return False
        return True
