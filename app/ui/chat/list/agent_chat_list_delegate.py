"""Delegate for agent chat list rendering.

This module provides the delegate that handles size hints and painting
for items in the agent chat list.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtGui import QPainter
from PySide6.QtCore import QStyleOptionViewItem, QModelIndex, QSize

if TYPE_CHECKING:
    from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget


class AgentChatListDelegate(QStyledItemDelegate):
    """Delegate for rendering chat list items.

    This delegate delegates the size calculation to the widget's
    get_item_size_hint method, allowing the widget to control
    the sizing logic while the delegate handles the Qt integration.

    The actual rendering is done through setIndexWidget in the
    widget, so the paint method does nothing.
    """

    def __init__(self, owner: "AgentChatListWidget", parent=None):
        """Initialize the delegate.

        Args:
            owner: The AgentChatListWidget that owns this delegate
            parent: Parent QObject for memory management
        """
        super().__init__(parent)
        self._owner = owner

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> "QSize":
        """Calculate the size hint for the given index.

        Delegates to the owner widget's get_item_size_hint method.

        Args:
            option: Style options for the item
            index: Model index of the item

        Returns:
            Size hint for the item
        """
        return self._owner.get_item_size_hint(option, index)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint the item (does nothing as rendering is done via setIndexWidget).

        Args:
            painter: Painter to use (not used)
            option: Style options (not used)
            index: Model index (not used)
        """
        # Actual rendering is done via setIndexWidget in the widget
        return
