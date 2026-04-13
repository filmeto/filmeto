"""ViewModel and shot list model for the storyboard editor (center column QML)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Qt, Signal, Slot, QObject, QUrl

from app.data.screen_play import ScreenPlayManager, ScreenPlayScene
from app.data.story_board import StoryBoardManager, StoryBoardShot


def _sort_shot_ids(ids: List[str]) -> List[str]:
    return sorted(ids, key=lambda s: (len(s), s.lower()))


def _shot_subline(shot: StoryBoardShot) -> str:
    parts: List[str] = []
    ctx = shot.keyframe_context or {}
    prompt = str(ctx.get("prompt", "") or "").strip()
    ability_model = str(ctx.get("ability_model", "") or ctx.get("model", "") or "").strip()
    refs = ctx.get("reference_images") or ctx.get("references") or []
    if prompt:
        parts.append(prompt[:100] + ("…" if len(prompt) > 100 else ""))
    if ability_model:
        parts.append(f"model: {ability_model}")
    if isinstance(refs, list) and refs:
        parts.append(f"refs: {len(refs)}")
    return " · ".join(parts) if parts else ""


def _image_url(path: Optional[Path]) -> str:
    if path is None or not path.is_file():
        return ""
    return QUrl.fromLocalFile(str(path.resolve())).toString()


class StoryBoardShotListModel(QAbstractListModel):
    """Shots for the current scene (comic grid)."""

    ShotIdRole = Qt.UserRole + 1
    SceneIdRole = Qt.UserRole + 2
    HeaderRole = Qt.UserRole + 3
    SublineRole = Qt.UserRole + 4
    ImageUrlRole = Qt.UserRole + 5
    BodyRole = Qt.UserRole + 6

    countChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._rows: List[StoryBoardShot] = []
        self._scene_id = ""
        self._image_urls: List[str] = []

    def roleNames(self):
        return {
            self.ShotIdRole: b"shotId",
            self.SceneIdRole: b"sceneId",
            self.HeaderRole: b"headerLine",
            self.SublineRole: b"subLine",
            self.ImageUrlRole: b"imageUrl",
            self.BodyRole: b"bodyText",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        shot = self._rows[index.row()]
        if role == self.ShotIdRole:
            return shot.shot_id
        if role == self.SceneIdRole:
            return shot.scene_id
        if role == self.HeaderRole:
            return f"Shot {shot.shot_no or shot.shot_id}"
        if role == self.SublineRole:
            return _shot_subline(shot)
        if role == self.ImageUrlRole:
            if 0 <= index.row() < len(self._image_urls):
                return self._image_urls[index.row()]
            return ""
        if role == self.BodyRole:
            return shot.description or ""
        return None

    def set_rows(self, scene_id: str, shots: List[StoryBoardShot], image_urls: List[str]) -> None:
        self.beginResetModel()
        self._scene_id = scene_id
        self._rows = shots
        self._image_urls = list(image_urls)
        self.endResetModel()
        self.countChanged.emit()


class StoryBoardEditorViewModel(QObject):
    sceneLabelsChanged = Signal()
    currentSceneIndexChanged = Signal()
    emptyMessageChanged = Signal()
    shotsReloaded = Signal()
    selectedShotIdChanged = Signal()

    refreshRequested = Signal()
    addShotRequested = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._scene_ids: List[str] = []
        self._scene_labels: List[str] = []
        self._current_index = 0
        self._empty_message = ""
        self._selected_shot_id = ""
        self.shot_model = StoryBoardShotListModel(self)

        self._screenplay: Optional[ScreenPlayManager] = None
        self._storyboard: Optional[StoryBoardManager] = None

    @Property("QStringList", notify=sceneLabelsChanged)
    def sceneLabels(self) -> List[str]:
        return list(self._scene_labels)

    @Property(int, notify=currentSceneIndexChanged)
    def currentSceneIndex(self) -> int:
        return self._current_index

    @Property(str, notify=emptyMessageChanged)
    def emptyMessage(self) -> str:
        return self._empty_message

    @Property(str, notify=selectedShotIdChanged)
    def selectedShotId(self) -> str:
        return self._selected_shot_id

    def _set_selected_shot(self, shot_id: str) -> None:
        shot_id = shot_id or ""
        if self._selected_shot_id != shot_id:
            self._selected_shot_id = shot_id
            self.selectedShotIdChanged.emit()

    def attach_managers(
        self,
        screenplay: Optional[ScreenPlayManager],
        storyboard: Optional[StoryBoardManager],
    ) -> None:
        self._screenplay = screenplay
        self._storyboard = storyboard

    def reload_scenes(self) -> None:
        self._scene_ids.clear()
        self._scene_labels.clear()
        if not self._screenplay:
            self._empty_message = "No active project."
            self.sceneLabelsChanged.emit()
            self.currentSceneIndexChanged.emit()
            self.shot_model.set_rows("", [], [])
            self._set_selected_shot("")
            self.emptyMessageChanged.emit()
            return

        scenes = list(self._screenplay.list_scenes())

        def sk(s: ScreenPlayScene):
            try:
                return (True, int(s.scene_number), str(s.scene_number))
            except (TypeError, ValueError):
                return (False, 0, str(s.scene_number or ""))

        scenes.sort(key=sk)
        for sc in scenes:
            self._scene_ids.append(sc.scene_id)
            num = (sc.scene_number or "").strip()
            head = (sc.title or "").strip()
            if num and head:
                lab = f"{num}. {head}"
            elif num:
                lab = num
            else:
                lab = head or sc.scene_id
            self._scene_labels.append(lab)

        if not self._scene_ids:
            self._empty_message = "No screenplay scenes. Add scenes in script mode or the screenplay panel."
        else:
            self._empty_message = ""

        if self._current_index >= len(self._scene_ids):
            self._current_index = max(0, len(self._scene_ids) - 1)

        self.sceneLabelsChanged.emit()
        self.currentSceneIndexChanged.emit()
        self.emptyMessageChanged.emit()
        self.reload_shots_for_current_scene()

    def reload_shots_for_current_scene(self, preserve_shot_id: Optional[str] = None) -> None:
        if not self._storyboard or not self._scene_ids:
            self.shot_model.set_rows("", [], [])
            self._set_selected_shot("")
            self.shotsReloaded.emit()
            return
        if self._current_index < 0 or self._current_index >= len(self._scene_ids):
            self.shot_model.set_rows("", [], [])
            self._set_selected_shot("")
            self.shotsReloaded.emit()
            return
        sid = self._scene_ids[self._current_index]
        ids = _sort_shot_ids(self._storyboard.list_shot_ids(sid))
        shots: List[StoryBoardShot] = []
        paths: List[str] = []
        for shot_id in ids:
            sh = self._storyboard.get_shot(sid, shot_id)
            if sh:
                shots.append(sh)
                km = self._storyboard.key_moment_path(sid, shot_id)
                paths.append(_image_url(km))
        self.shot_model.set_rows(sid, shots, paths)
        if preserve_shot_id and preserve_shot_id in ids:
            self._set_selected_shot(preserve_shot_id)
        else:
            self._validate_shot_selection(sid, ids)
        self.shotsReloaded.emit()

    def _validate_shot_selection(self, scene_id: str, shot_ids: List[str]) -> None:
        if not self._selected_shot_id:
            # 自动选择第一个 shot（如果有）
            if shot_ids:
                self._set_selected_shot(shot_ids[0])
            return
        if self._selected_shot_id not in shot_ids:
            # 选中 shot 不存在时，选择第一个可用的
            self._set_selected_shot(shot_ids[0] if shot_ids else "")

    @Slot(int)
    def set_current_scene_index(self, index: int) -> None:
        if index < 0 or index >= len(self._scene_ids):
            return
        if self._current_index != index:
            self._current_index = index
            self.currentSceneIndexChanged.emit()
            self._set_selected_shot("")
            self.reload_shots_for_current_scene()

    @Slot()
    def on_refresh_clicked(self) -> None:
        self.refreshRequested.emit()

    @Slot()
    def on_add_shot_clicked(self) -> None:
        self.addShotRequested.emit()

    @Slot(str, str)
    def save_shot_body(self, shot_id: str, body: str) -> None:
        if not self._storyboard or not self._scene_ids:
            return
        if self._current_index < 0 or self._current_index >= len(self._scene_ids):
            return
        scene_id = self._scene_ids[self._current_index]
        self._storyboard.update_shot(scene_id, shot_id, {"description": body}, content=body)
        self.reload_shots_for_current_scene(preserve_shot_id=shot_id)

    @Slot(str)
    def select_shot(self, shot_id: str) -> None:
        if not shot_id:
            return
        if self._selected_shot_id == shot_id:
            self._set_selected_shot("")
        else:
            self._set_selected_shot(shot_id)

    def set_shot_selected(self, shot_id: str) -> None:
        """Select a shot without toggling off (e.g. after adding a shot)."""
        self._set_selected_shot(shot_id or "")

    def get_selected_shot(self) -> Optional[StoryBoardShot]:
        if not self._storyboard or not self._selected_shot_id:
            return None
        sid = self.current_scene_id()
        if not sid:
            return None
        return self._storyboard.get_shot(sid, self._selected_shot_id)

    @Slot(str, str)
    def save_shot_title(self, shot_id: str, title: str) -> None:
        if not self._storyboard or not self._scene_ids:
            return
        scene_id = self._scene_ids[self._current_index]
        self._storyboard.update_shot(scene_id, shot_id, {"description": title})

    def current_scene_id(self) -> Optional[str]:
        if not self._scene_ids or self._current_index < 0:
            return None
        if self._current_index >= len(self._scene_ids):
            return None
        return self._scene_ids[self._current_index]

    def open_scene(self, scene_id: str, shot_id: Optional[str] = None) -> None:
        """Open a scene and optionally select a shot.

        Args:
            scene_id: Scene ID to open
            shot_id: Optional shot ID to select after opening scene
        """
        if not scene_id:
            return
        if scene_id not in self._scene_ids:
            self.reload_scenes()
        try:
            idx = self._scene_ids.index(scene_id)
        except ValueError:
            return
        if self._current_index != idx:
            self._current_index = idx
            self.currentSceneIndexChanged.emit()
            self._set_selected_shot("")
        self.reload_shots_for_current_scene(preserve_shot_id=shot_id)
