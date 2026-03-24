"""ViewModel + model for QML screenplay panel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Qt, Signal, Slot, QObject


@dataclass
class _SceneRow:
    scene_id: str
    title: str
    overview: str
    scene_number: str


class ScreenPlayListModel(QAbstractListModel):
    """Model exposed to QML for screenplay scene list."""

    SceneIdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    OverviewRole = Qt.UserRole + 3
    SceneNumberRole = Qt.UserRole + 4

    countChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._rows: List[_SceneRow] = []

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    def roleNames(self):
        return {
            self.SceneIdRole: b"sceneId",
            self.TitleRole: b"title",
            self.OverviewRole: b"overview",
            self.SceneNumberRole: b"sceneNumber",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == self.SceneIdRole:
            return row.scene_id
        if role == self.TitleRole:
            return row.title
        if role == self.OverviewRole:
            return row.overview
        if role == self.SceneNumberRole:
            return row.scene_number
        return None

    def set_rows(self, rows: List[_SceneRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.countChanged.emit()


class ScreenPlayViewModel(QObject):
    """ViewModel with UI-facing state and actions for screenplay panel."""

    modeChanged = Signal()
    editingSceneIdChanged = Signal()
    editorTextChanged = Signal()
    editorTextUpdated = Signal(str)
    emptyMessageChanged = Signal()

    addSceneRequested = Signal()
    refreshRequested = Signal()
    openSceneRequested = Signal(str)
    returnRequested = Signal()
    saveRequested = Signal(str, str)
    insertActionRequested = Signal()
    insertCharacterRequested = Signal()
    insertDialogueRequested = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._mode = "list"
        self._editing_scene_id = ""
        self._editor_text = ""
        self._empty_message = ""

    @Property(str, notify=modeChanged)
    def mode(self) -> str:
        return self._mode

    @Property(str, notify=editingSceneIdChanged)
    def editingSceneId(self) -> str:
        return self._editing_scene_id

    @Property(str, notify=editorTextChanged)
    def editorText(self) -> str:
        return self._editor_text

    @Property(str, notify=emptyMessageChanged)
    def emptyMessage(self) -> str:
        return self._empty_message

    def set_mode(self, mode: str) -> None:
        if self._mode != mode:
            self._mode = mode
            self.modeChanged.emit()

    def set_editing_scene_id(self, scene_id: str) -> None:
        if self._editing_scene_id != scene_id:
            self._editing_scene_id = scene_id
            self.editingSceneIdChanged.emit()

    def set_editor_text(self, text: str) -> None:
        if self._editor_text != text:
            self._editor_text = text
            self.editorTextChanged.emit()
            self.editorTextUpdated.emit(text)

    def set_empty_message(self, text: str) -> None:
        if self._empty_message != text:
            self._empty_message = text
            self.emptyMessageChanged.emit()

    @Slot()
    def on_add_scene_clicked(self) -> None:
        self.addSceneRequested.emit()

    @Slot()
    def on_refresh_clicked(self) -> None:
        self.refreshRequested.emit()

    @Slot(str)
    def on_scene_clicked(self, scene_id: str) -> None:
        self.openSceneRequested.emit(scene_id)

    @Slot()
    def on_return_clicked(self) -> None:
        self.returnRequested.emit()

    @Slot(str)
    def on_editor_text_changed(self, text: str) -> None:
        if self._editor_text != text:
            self._editor_text = text
            self.editorTextChanged.emit()

    @Slot()
    def on_save_clicked(self) -> None:
        self.saveRequested.emit(self._editing_scene_id, self._editor_text)

    @Slot()
    def on_insert_action_clicked(self) -> None:
        self.insertActionRequested.emit()

    @Slot()
    def on_insert_character_clicked(self) -> None:
        self.insertCharacterRequested.emit()

    @Slot()
    def on_insert_dialogue_clicked(self) -> None:
        self.insertDialogueRequested.emit()
