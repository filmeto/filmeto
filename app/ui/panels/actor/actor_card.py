"""Legacy actor card compatibility stub.

Actor cards are now rendered by QML delegate `app/ui/qml/panels/ActorCard.qml`.
This class is kept only to avoid import breaks in older code paths.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame

from app.data.character import Character


class ActorCard(QFrame):
    edit_requested = Signal(str)
    clicked = Signal(str)
    selection_changed = Signal(str, bool)

    def __init__(self, character: Character, parent=None):
        super().__init__(parent)
        self.character = character
        self._is_selected = False

    def set_selected(self, selected: bool):
        self._is_selected = selected
