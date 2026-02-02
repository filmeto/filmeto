"""Widget for displaying metadata content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt

from agent.chat.content import MetadataContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class MetadataContentWidget(BaseStructuredContentWidget):
    """Widget for displaying metadata content."""

    def __init__(self, content: MetadataContent, parent=None):
        """Initialize metadata widget."""
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
                background-color: rgba(156, 39, 176, 0.1);
                border: 1px solid rgba(156, 39, 176, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(6)

        # Header with metadata type
        metadata_type = self.structure_content.metadata_type or "Metadata"
        header_label = QLabel(f"📋 {metadata_type.replace('_', ' ').title()}", container)
        header_label.setStyleSheet("""
            QLabel {
                color: #9c27b0;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        header_label.setAlignment(Qt.AlignLeft)
        container_layout.addWidget(header_label)

        # Display metadata as key-value table
        metadata_data = self.structure_content.metadata_data or {}
        if metadata_data:
            table = QTableWidget(container)
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Key", "Value"])
            table.setRowCount(len(metadata_data))

            table.setStyleSheet("""
                QTableWidget {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    gridline-color: #3c3c3c;
                    border: 1px solid #3c3c3c;
                    border-radius: 4px;
                }
                QTableWidget::item {
                    padding: 4px;
                }
                QHeaderView::section {
                    background-color: #333337;
                    color: #cccccc;
                    padding: 4px;
                    border: none;
                    border-right: 1px solid #444;
                    border-bottom: 1px solid #444;
                    font-weight: bold;
                    font-size: 10px;
                }
            """)

            for row_idx, (key, value) in enumerate(metadata_data.items()):
                # Key column
                key_item = QTableWidgetItem(str(key))
                key_item.setBackground(Qt.transparent)
                table.setItem(row_idx, 0, key_item)

                # Value column
                value_str = str(value) if value is not None else ""
                value_item = QTableWidgetItem(value_str)
                value_item.setBackground(Qt.transparent)
                table.setItem(row_idx, 1, value_item)

            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)
            container_layout.addWidget(table)
        else:
            # No data message
            no_data_label = QLabel("No metadata available", container)
            no_data_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 11px;
                    font-style: italic;
                }
            """)
            container_layout.addWidget(no_data_label)

        layout.addWidget(container)

    def update_content(self, structure_content: MetadataContent):
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
            "metadata_type": self.structure_content.metadata_type,
            "metadata_data": self.structure_content.metadata_data,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "metadata_type" in state and hasattr(self.structure_content, 'metadata_type'):
            self.structure_content.metadata_type = state["metadata_type"]
        if "metadata_data" in state and hasattr(self.structure_content, 'metadata_data'):
            self.structure_content.metadata_data = state["metadata_data"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
