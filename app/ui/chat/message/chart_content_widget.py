"""Widget for displaying chart content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt

from agent.chat.structure_content import ChartContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class ChartContentWidget(BaseStructuredContentWidget):
    """Widget for displaying chart content."""

    def __init__(self, content: ChartContent, parent=None):
        """Initialize chart widget."""
        super().__init__(structure_content=content, parent=parent)

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Create container frame
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 87, 34, 0.1);
                border: 1px solid rgba(255, 87, 34, 0.3);
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

        # Chart icon
        icon_label = QLabel("📊", container)
        icon_label.setStyleSheet("font-size: 18px;")
        header_row.addWidget(icon_label)

        # Chart type and title
        chart_type = self.structure_content.chart_type or "chart"
        chart_title = self.structure_content.chart_title or f"{chart_type.replace('_', ' ').title()} Chart"

        title_label = QLabel(chart_title, container)
        title_label.setStyleSheet("""
            QLabel {
                color: #ff5722;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_row.addWidget(title_label)
        header_row.addStretch()

        # Chart type badge
        type_label = QLabel(chart_type.upper(), container)
        type_label.setStyleSheet("""
            QLabel {
                color: #ff5722;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 6px;
                background-color: rgba(255, 87, 34, 0.2);
                border-radius: 3px;
            }
        """)
        header_row.addWidget(type_label)

        container_layout.addLayout(header_row)

        # Axis labels
        if self.structure_content.x_axis_label or self.structure_content.y_axis_label:
            axis_row = QHBoxLayout()
            axis_row.setSpacing(12)

            if self.structure_content.x_axis_label:
                x_label = QLabel(f"X: {self.structure_content.x_axis_label}", container)
                x_label.setStyleSheet("""
                    QLabel {
                        color: #a0a0a0;
                        font-size: 10px;
                    }
                """)
                axis_row.addWidget(x_label)

            if self.structure_content.y_axis_label:
                y_label = QLabel(f"Y: {self.structure_content.y_axis_label}", container)
                y_label.setStyleSheet("""
                    QLabel {
                        color: #a0a0a0;
                        font-size: 10px;
                    }
                """)
                axis_row.addWidget(y_label)

            axis_row.addStretch()
            container_layout.addLayout(axis_row)

        # Chart placeholder
        chart_placeholder = QLabel(container)
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_placeholder.setMinimumSize(250, 150)
        chart_placeholder.setStyleSheet("""
            QLabel {
                background-color: #252526;
                border: 2px dashed #3c3c3c;
                border-radius: 6px;
                color: #a0a0a0;
                font-size: 12px;
            }
        """)
        chart_placeholder.setText(f"📈 {chart_type.upper()} CHART\n(Visualization not available)")
        container_layout.addWidget(chart_placeholder)

        # Data info
        chart_data = self.structure_content.data or {}
        if chart_data:
            # Show data keys
            data_keys = list(chart_data.keys())
            if len(data_keys) > 5:
                data_info = f"Data keys: {', '.join(data_keys[:5])}..."
            else:
                data_info = f"Data keys: {', '.join(data_keys)}"

            data_label = QLabel(data_info, container)
            data_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-size: 10px;
                }
            """)
            data_label.setWordWrap(True)
            container_layout.addWidget(data_label)

        layout.addWidget(container)

    def update_content(self, structure_content: ChartContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content
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
            "chart_type": self.structure_content.chart_type,
            "data": self.structure_content.data,
            "chart_title": self.structure_content.chart_title,
            "x_axis_label": self.structure_content.x_axis_label,
            "y_axis_label": self.structure_content.y_axis_label,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        for key in ["chart_type", "data", "chart_title", "x_axis_label", "y_axis_label"]:
            if key in state and hasattr(self.structure_content, key):
                setattr(self.structure_content, key, state[key])

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
