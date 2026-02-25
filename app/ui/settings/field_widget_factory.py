"""
Field Widget Factory

Creates appropriate Qt widgets based on field type specifications.
"""

from typing import Any, Dict, Callable
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QSpinBox, QCheckBox, QComboBox, 
    QPushButton, QSlider, QLabel, QHBoxLayout, QColorDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.data.settings import SettingField


class ColorPickerButton(QPushButton):
    """Custom color picker button widget"""
    
    color_changed = Signal(str)
    
    def __init__(self, initial_color: str = "#ffffff"):
        super().__init__()
        self.current_color = initial_color
        self.setFixedSize(100, 30)
        self.clicked.connect(self._show_color_dialog)
        self._update_style()
    
    def _update_style(self):
        """Update button style to show current color"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color};
                border: 1px solid #555555;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 1px solid #888888;
            }}
        """)
    
    def _show_color_dialog(self):
        """Show color picker dialog"""
        color = QColorDialog.getColor(
            QColor(self.current_color),
            self,
            "Choose Color"
        )
        
        if color.isValid():
            self.current_color = color.name()
            self._update_style()
            self.color_changed.emit(self.current_color)
    
    def get_color(self) -> str:
        """Get current color as hex string"""
        return self.current_color
    
    def set_color(self, color: str):
        """Set current color"""
        self.current_color = color
        self._update_style()


class SliderWidget(QWidget):
    """Custom slider widget with value label"""
    
    value_changed = Signal(int)
    
    def __init__(self, min_val: int = 0, max_val: int = 100, step: int = 1):
        super().__init__()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setSingleStep(step)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 6px;
                background: #2d2d2d;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #5dade2;
            }
        """)
        
        self.value_label = QLabel(str(min_val))
        self.value_label.setFixedWidth(40)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setStyleSheet("color: #ffffff;")
        
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)
        
        self.slider.valueChanged.connect(self._on_value_changed)
    
    def _on_value_changed(self, value: int):
        """Handle slider value change"""
        self.value_label.setText(str(value))
        self.value_changed.emit(value)
    
    def get_value(self) -> int:
        """Get current slider value"""
        return self.slider.value()
    
    def set_value(self, value: int):
        """Set slider value"""
        self.slider.setValue(value)


class FieldWidgetFactory:
    """
    Factory for creating field widgets based on field type.
    """
    
    @staticmethod
    def create_widget(field: SettingField, current_value: Any) -> QWidget:
        """
        Create appropriate widget for the given field.
        
        Args:
            field: Field specification
            current_value: Current value of the field
            
        Returns:
            QWidget configured for the field type
        """
        field_type = field.type
        
        if field_type == 'text':
            return FieldWidgetFactory._create_text_widget(field, current_value)
        elif field_type == 'number':
            return FieldWidgetFactory._create_number_widget(field, current_value)
        elif field_type == 'boolean':
            return FieldWidgetFactory._create_boolean_widget(field, current_value)
        elif field_type == 'select':
            return FieldWidgetFactory._create_select_widget(field, current_value)
        elif field_type == 'combo':
            return FieldWidgetFactory._create_combo_widget(field, current_value)
        elif field_type == 'color':
            return FieldWidgetFactory._create_color_widget(field, current_value)
        elif field_type == 'slider':
            return FieldWidgetFactory._create_slider_widget(field, current_value)
        else:
            # Unknown type: create read-only text field
            widget = QLineEdit(str(current_value))
            widget.setReadOnly(True)
            widget.setPlaceholderText(f"Unknown field type: {field_type}")
            return widget
    
    @staticmethod
    def _create_text_widget(field: SettingField, current_value: Any) -> QLineEdit:
        """Create text input widget"""
        widget = QLineEdit(str(current_value))
        widget.setPlaceholderText(field.description or field.label)
        
        # Apply validation
        if field.validation:
            max_length = field.validation.get('max_length')
            if max_length:
                widget.setMaxLength(max_length)
        
        widget.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        
        return widget
    
    @staticmethod
    def _create_number_widget(field: SettingField, current_value: Any) -> QSpinBox:
        """Create number input widget"""
        widget = QSpinBox()
        
        # Apply validation
        if field.validation:
            min_val = field.validation.get('min', 0)
            max_val = field.validation.get('max', 99999)
            widget.setMinimum(min_val)
            widget.setMaximum(max_val)
        
        widget.setValue(int(current_value) if current_value is not None else 0)
        
        widget.setStyleSheet("""
            QSpinBox {
                padding: 6px;
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QSpinBox:focus {
                border: 1px solid #3498db;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3a3a3a;
                border: 1px solid #555555;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4a4a4a;
            }
        """)
        
        return widget
    
    @staticmethod
    def _create_boolean_widget(field: SettingField, current_value: Any) -> QCheckBox:
        """Create checkbox widget"""
        widget = QCheckBox(field.description or "")
        widget.setChecked(bool(current_value))
        
        widget.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border: 1px solid #2980b9;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #888888;
            }
        """)
        
        return widget
    
    @staticmethod
    def _create_combo_widget(field: SettingField, current_value: Any) -> QComboBox:
        """Create editable combobox widget"""
        widget = QComboBox()
        widget.setEditable(True)  # Make the combo box editable

        # Populate options
        if field.options:
            for option in field.options:
                widget.addItem(option.get('label', ''), option.get('value'))

            # Set current value - if it matches an option, select it; otherwise, set as text
            index = widget.findData(current_value)
            if index >= 0:
                widget.setCurrentIndex(index)
            else:
                # If the current value is not in the predefined options, set it as the text
                widget.setEditText(str(current_value))

        widget.setStyleSheet("""
            QComboBox {
                padding: 6px;
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QComboBox:focus {
                border: 1px solid #3498db;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #3a3a3a;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
                selection-background-color: #3498db;
            }
            QComboBox QAbstractItemView:item {
                padding: 4px;
            }
        """)

        return widget

    @staticmethod
    def _create_select_widget(field: SettingField, current_value: Any) -> QComboBox:
        """Create dropdown/select widget"""
        widget = QComboBox()

        # Populate options
        if field.options:
            for option in field.options:
                widget.addItem(option.get('label', ''), option.get('value'))

            # Set current value
            index = widget.findData(current_value)
            if index >= 0:
                widget.setCurrentIndex(index)

        widget.setStyleSheet("""
            QComboBox {
                padding: 6px;
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QComboBox:focus {
                border: 1px solid #3498db;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #3a3a3a;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
                selection-background-color: #3498db;
            }
        """)

        return widget
    
    @staticmethod
    def _create_color_widget(field: SettingField, current_value: Any) -> ColorPickerButton:
        """Create color picker widget"""
        widget = ColorPickerButton(str(current_value) if current_value else "#ffffff")
        return widget
    
    @staticmethod
    def _create_slider_widget(field: SettingField, current_value: Any) -> SliderWidget:
        """Create slider widget"""
        min_val = 0
        max_val = 100
        step = 1
        
        if field.validation:
            min_val = field.validation.get('min', 0)
            max_val = field.validation.get('max', 100)
            step = field.validation.get('step', 1)
        
        widget = SliderWidget(min_val, max_val, step)
        widget.set_value(int(current_value) if current_value is not None else min_val)
        
        return widget
    
    @staticmethod
    def get_widget_value(widget: QWidget, field_type: str) -> Any:
        """
        Extract value from widget based on field type.
        
        Args:
            widget: The widget to extract value from
            field_type: Type of the field
            
        Returns:
            Current value of the widget
        """
        if field_type == 'text':
            return widget.text()
        elif field_type == 'number':
            return widget.value()
        elif field_type == 'boolean':
            return widget.isChecked()
        elif field_type == 'select':
            return widget.currentData()
        elif field_type == 'combo':
            # For editable combo box, prefer currentData (value) over currentText (label)
            # If user selected from dropdown, use the value; if typed custom text, use that
            data = widget.currentData()
            if data is not None:
                return data
            return widget.currentText()
        elif field_type == 'color':
            return widget.get_color()
        elif field_type == 'slider':
            return widget.get_value()
        else:
            return None
    
    @staticmethod
    def connect_change_handler(widget: QWidget, field_type: str, handler: Callable):
        """
        Connect widget's value change signal to handler.
        
        Args:
            widget: The widget to connect
            field_type: Type of the field
            handler: Callback function for value changes
        """
        if field_type == 'text':
            widget.textChanged.connect(handler)
        elif field_type == 'number':
            widget.valueChanged.connect(handler)
        elif field_type == 'boolean':
            widget.stateChanged.connect(handler)
        elif field_type == 'select':
            widget.currentIndexChanged.connect(handler)
        elif field_type == 'combo':
            # For editable combo box, connect both text change and index change
            widget.currentTextChanged.connect(handler)
            widget.currentIndexChanged.connect(handler)
        elif field_type == 'color':
            widget.color_changed.connect(handler)
        elif field_type == 'slider':
            widget.value_changed.connect(handler)
