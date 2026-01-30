"""Widget for displaying form content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QLineEdit, QTextEdit, QSpinBox, QComboBox
from PySide6.QtCore import Qt

from agent.chat.structure_content import FormContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class FormContentWidget(BaseStructuredContentWidget):
    """Widget for displaying form content."""

    def __init__(self, content: FormContent, parent=None):
        """Initialize form widget."""
        super().__init__(structure_content=content, parent=parent)
        self.input_widgets = {}  # Store field widgets for value retrieval

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(103, 58, 183, 0.1);
                border: 1px solid rgba(103, 58, 183, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(6)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_label = QLabel("📝", container)
        icon_label.setStyleSheet("font-size: 18px;")
        header_row.addWidget(icon_label)

        # Form title
        form_title = self.structure_content.form_title or "Form"
        title_label = QLabel(form_title, container)
        title_label.setStyleSheet("""
            QLabel {
                color: #673ab7;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_row.addWidget(title_label)
        header_row.addStretch()

        container_layout.addLayout(header_row)

        # Form fields
        fields = self.structure_content.fields or []
        for field in fields:
            field_name = field.get("name", "")
            field_label = field.get("label", field_name)
            field_type = field.get("type", "text")
            field_options = field.get("options", [])
            field_default = field.get("default", "")
            field_required = field.get("required", False)

            # Field label
            label_text = f"{field_label}"
            if field_required:
                label_text += " *"
            field_label_widget = QLabel(label_text, container)
            field_label_widget.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            container_layout.addWidget(field_label_widget)

            # Field input based on type
            if field_type == "text":
                input_widget = QLineEdit(container)
                input_widget.setText(field_default)
                input_widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #1e1e1e;
                        color: #e1e1e1;
                        border: 1px solid #3c3c3c;
                        border-radius: 4px;
                        padding: 6px;
                    }
                """)
                container_layout.addWidget(input_widget)
                self.input_widgets[field_name] = input_widget

            elif field_type == "textarea":
                input_widget = QTextEdit(container)
                input_widget.setPlainText(field_default)
                input_widget.setMaximumHeight(80)
                input_widget.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e1e1e;
                        color: #e1e1e1;
                        border: 1px solid #3c3c3c;
                        border-radius: 4px;
                        padding: 6px;
                    }
                """)
                container_layout.addWidget(input_widget)
                self.input_widgets[field_name] = input_widget

            elif field_type == "number":
                input_widget = QSpinBox(container)
                input_widget.setStyleSheet("""
                    QSpinBox {
                        background-color: #1e1e1e;
                        color: #e1e1e1;
                        border: 1px solid #3c3c3c;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)
                container_layout.addWidget(input_widget)
                self.input_widgets[field_name] = input_widget

            elif field_type == "select":
                input_widget = QComboBox(container)
                input_widget.addItems(field_options)
                if field_default in field_options:
                    input_widget.setCurrentText(field_default)
                input_widget.setStyleSheet("""
                    QComboBox {
                        background-color: #1e1e1e;
                        color: #e1e1e1;
                        border: 1px solid #3c3c3c;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        width: 12px;
                        height: 12px;
                    }
                """)
                container_layout.addWidget(input_widget)
                self.input_widgets[field_name] = input_widget

            elif field_type == "checkbox":
                # For checkboxes, we need a different layout
                checkbox_row = QHBoxLayout()
                checkbox_row.setSpacing(8)
                # Placeholder for checkbox implementation
                placeholder = QLabel("Checkbox (not implemented)", container)
                placeholder.setStyleSheet("""
                    QLabel {
                        color: #a0a0a0;
                        font-size: 10px;
                        font-style: italic;
                    }
                """)
                checkbox_row.addWidget(placeholder)
                checkbox_row.addStretch()
                container_layout.addLayout(checkbox_row)

        # Submit button
        submit_label = self.structure_content.submit_label or "Submit"
        submit_button = QPushButton(submit_label, container)
        submit_button.setStyleSheet("""
            QPushButton {
                background-color: #673ab7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
        """)
        submit_button.clicked.connect(self._on_submit)
        container_layout.addWidget(submit_button)

        layout.addWidget(container)

    def _on_submit(self):
        """Handle form submission."""
        # Collect form data
        form_data = {}
        for field_name, widget in self.input_widgets.items():
            if isinstance(widget, QLineEdit):
                form_data[field_name] = widget.text()
            elif isinstance(widget, QTextEdit):
                form_data[field_name] = widget.toPlainText()
            elif isinstance(widget, QSpinBox):
                form_data[field_name] = widget.value()
            elif isinstance(widget, QComboBox):
                form_data[field_name] = widget.currentText()

        print(f"Form submitted: {self.structure_content.submit_action}, data: {form_data}")

        # Find parent and emit signal
        parent = self.parent()
        while parent:
            if hasattr(parent, 'reference_clicked'):
                parent.reference_clicked.emit('form_submit', self.structure_content.submit_action)
                break
            parent = parent.parent()

    def update_content(self, structure_content: FormContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content
        self.input_widgets.clear()
        # Clear and re-layout the widget
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "fields": self.structure_content.fields,
            "submit_action": self.structure_content.submit_action,
            "submit_label": self.structure_content.submit_label,
            "form_title": self.structure_content.form_title,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        for key in ["fields", "submit_action", "submit_label", "form_title"]:
            if key in state and hasattr(self.structure_content, key):
                setattr(self.structure_content, key, state[key])

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
