"""Widget for displaying table content in chat messages."""

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt

from agent.chat.content import TableContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class TableWidget(BaseStructuredContentWidget):
    """Widget for displaying table content."""

    def __init__(self, content: TableContent, parent=None):
        """Initialize table widget."""
        super().__init__(structure_content=content, parent=parent)
        self.table_widget = None

    def _setup_ui(self):
        """Set up UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Table title if available
        if self.structure_content.table_title:
            title_label = QLabel(self.structure_content.table_title, self)
            title_label.setStyleSheet("""
                QLabel {
                    color: #7c4dff;
                    font-weight: bold;
                    font-size: 12px;
                    padding-bottom: 4px;
                }
            """)
            title_label.setAlignment(Qt.AlignLeft)
            layout.addWidget(title_label)

        # Create table widget
        self.table_widget = QTableWidget(self)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252526;
                color: #d4d4d4;
                gridline-color: #3c3c3c;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 6px 4px;
            }
            QTableWidget::item:selected {
                background-color: #4a90d9;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #333337;
                color: #cccccc;
                padding: 6px 4px;
                border: none;
                border-right: 1px solid #444;
                border-bottom: 1px solid #444;
                font-weight: bold;
                font-size: 11px;
            }
            QHeaderView::section:first {
                border-top-left-radius: 3px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 3px;
                border-right: none;
            }
        """)

        # Populate table from TableContent attributes (headers, rows)
        headers = self.structure_content.headers or []
        rows = self.structure_content.rows or []

        if headers:
            self.table_widget.setColumnCount(len(headers))
            self.table_widget.setHorizontalHeaderLabels(headers)

        if rows:
            self.table_widget.setRowCount(len(rows))
            for row_idx, row_data in enumerate(rows):
                for col_idx, cell_data in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_data))
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.table_widget.setItem(row_idx, col_idx, item)

        # Resize columns to content
        self.table_widget.resizeColumnsToContents()
        self.table_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.table_widget)

        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

    def update_content(self, structure_content: TableContent):
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
            "headers": self.structure_content.headers,
            "rows": self.structure_content.rows,
            "table_title": self.structure_content.table_title,
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "headers" in state and hasattr(self.structure_content, 'headers'):
            self.structure_content.headers = state["headers"]
        if "rows" in state and hasattr(self.structure_content, 'rows'):
            self.structure_content.rows = state["rows"]
        if "table_title" in state and hasattr(self.structure_content, 'table_title'):
            self.structure_content.table_title = state["table_title"]

        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child is not None:
                child.setParent(None)
        self._setup_ui()
