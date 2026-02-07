"""Custom QListView for agent chat list with smooth scrolling.

This module provides a custom QListView that supports pixel-perfect
scrolling for variable-height items by using cached row positions.
"""

from typing import Dict, Tuple

from PySide6.QtCore import Signal, Qt, QModelIndex, QRect
from PySide6.QtWidgets import QListView
from PySide6.QtGui import QResizeEvent


class AgentChatListView(QListView):
    """Custom QListView for smooth scrolling with variable-height items.

    This view uses cached row positions to provide pixel-perfect scrolling
    even when items have different heights. It overrides visualRect to use
    the cached positions and provides signals for viewport events.

    Signals:
        viewport_scrolled: Emitted when the viewport is scrolled
        viewport_resized: Emitted when the viewport is resized
    """

    viewport_scrolled = Signal()
    viewport_resized = Signal()

    def __init__(self, parent=None):
        """Initialize the view.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._total_content_height = 0
        self._row_positions: Dict[int, Tuple[int, int]] = {}  # {row: (y_position, height)}

    def set_row_positions(self, positions: Dict[int, Tuple[int, int]], total_height: int) -> None:
        """Set cached row positions for smooth scrolling.

        Args:
            positions: Dictionary mapping row to (y_position, height)
            total_height: Total height of all content
        """
        self._row_positions = dict(positions)
        self._total_content_height = total_height
        # Update scrollbar range immediately for smooth scrolling
        viewport_height = self.viewport().height()
        if viewport_height > 0:
            scroll_maximum = max(0, total_height - viewport_height)
            scrollbar = self.verticalScrollBar()
            current_value = scrollbar.value()
            scrollbar.setRange(0, scroll_maximum)
            scrollbar.setPageStep(viewport_height)
            # Restore scroll position if needed
            if current_value <= scroll_maximum:
                scrollbar.setValue(current_value)
        # Trigger geometry update
        self.updateGeometry()
        # Schedule viewport update
        self.viewport().update()

    def visualRect(self, index: QModelIndex) -> QRect:
        """Override to use precise cached positions for smooth scrolling.

        Args:
            index: Model index of the item

        Returns:
            QRect with the visual position of the item
        """
        if not index.isValid():
            return QRect()

        row = index.row()
        model = self.model()
        if model is None or row < 0 or row >= model.rowCount():
            return QRect()

        # Use cached position if available
        if row in self._row_positions:
            y, height = self._row_positions[row]
            viewport_width = self.viewport().width()
            return QRect(0, y, viewport_width, height)

        # Fall back to default implementation
        return super().visualRect(index)

    def verticalScrollbarAction(self, action: int) -> None:
        """Handle scrollbar actions smoothly.

        Args:
            action: Scrollbar action
        """
        super().verticalScrollbarAction(action)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Handle content scrolling and emit signal.

        Args:
            dx: Horizontal scroll delta
            dy: Vertical scroll delta
        """
        super().scrollContentsBy(dx, dy)
        self.viewport_scrolled.emit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize and emit signal.

        Args:
            event: Resize event
        """
        super().resizeEvent(event)
        self.viewport_resized.emit()

    def calculateViewportSize(self):
        """Calculate total viewport size based on cached positions."""
        # Update scrollbar range based on total content height
        if hasattr(self, '_total_content_height'):
            viewport_height = self.viewport().height()
            scroll_maximum = max(0, self._total_content_height - viewport_height)
            self.verticalScrollBar().setRange(0, scroll_maximum)
            self.verticalScrollBar().setPageStep(viewport_height)
        return super().calculateViewportSize()

    def doItemsLayout(self) -> None:
        """Override to ensure scrollbar range is updated after layout."""
        super().doItemsLayout()
        # Update scrollbar range based on cached content height
        if hasattr(self, '_total_content_height') and self._total_content_height > 0:
            viewport_height = self.viewport().height()
            scroll_maximum = max(0, self._total_content_height - viewport_height)
            self.verticalScrollBar().setRange(0, scroll_maximum)
            self.verticalScrollBar().setPageStep(viewport_height)
