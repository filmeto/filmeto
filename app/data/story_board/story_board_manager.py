"""
Storyboard shot storage under each screenplay scene directory.

Layout: screen_plays/<scene_id>/shots/<shot_id>/shot.md (+ optional key_moment.* image)
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from blinker import signal

from utils.md_with_meta_utils import read_md_with_meta, write_md_with_meta, update_md_with_meta

from app.data.screen_play.scene_paths import SHOT_MD_NAME
from app.data.screen_play.screen_play_manager import ScreenPlayManager

from .story_board_shot import (
    AudioLayerMeta,
    StoryBoardShot,
    TechDirectorLayerMeta,
    UxLogicLayerMeta,
    VisualLayerMeta,
)

_KEY_MOMENT_PREFIX = "key_moment"
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _apply_shot_updates(base: StoryBoardShot, updates: Dict[str, Any]) -> None:
    if "title" in updates and updates["title"] is not None:
        base.title = str(updates["title"])
    if "content" in updates and updates["content"] is not None:
        base.content = str(updates["content"])
    if "visual" in updates and isinstance(updates["visual"], dict):
        base.visual = VisualLayerMeta.from_dict({**base.visual.to_dict(), **updates["visual"]})
    if "audio" in updates and isinstance(updates["audio"], dict):
        base.audio = AudioLayerMeta.from_dict({**base.audio.to_dict(), **updates["audio"]})
    if "tech_director" in updates and isinstance(updates["tech_director"], dict):
        base.tech_director = TechDirectorLayerMeta.from_dict(
            {**base.tech_director.to_dict(), **updates["tech_director"]}
        )
    if "ux_logic" in updates and isinstance(updates["ux_logic"], dict):
        base.ux_logic = UxLogicLayerMeta.from_dict({**base.ux_logic.to_dict(), **updates["ux_logic"]})
    if "key_moment_relpath" in updates and updates["key_moment_relpath"] is not None:
        base.key_moment_relpath = str(updates["key_moment_relpath"])


class StoryBoardManager:
    """
    CRUD for storyboard shots; paths align with ScreenPlayManager scene directories.
    """

    def __init__(self, project_path: Union[str, Path]):
        self._screenplay = ScreenPlayManager(project_path)
        self._shot_changed = signal("storyboard_shot_changed")

    def connect_shot_changed(self, func) -> None:
        """Connect a listener for storyboard shot create/update/delete events."""
        self._shot_changed.connect(func)

    def disconnect_shot_changed(self, func) -> None:
        """Disconnect a previously connected shot-changed listener."""
        self._shot_changed.disconnect(func)

    def _scene_exists(self, scene_id: str) -> bool:
        return self._screenplay.get_scene(scene_id) is not None

    def shots_root(self, scene_id: str) -> Path:
        return self._screenplay.shots_dir_path(scene_id)

    def shot_dir(self, scene_id: str, shot_id: str) -> Path:
        return self.shots_root(scene_id) / shot_id

    def shot_md_path(self, scene_id: str, shot_id: str) -> Path:
        return self.shot_dir(scene_id, shot_id) / SHOT_MD_NAME

    def _discover_key_moment(self, sdir: Path) -> tuple[Optional[Path], str]:
        if not sdir.is_dir():
            return None, ""
        for p in sorted(sdir.iterdir()):
            if not p.is_file():
                continue
            name = p.name.lower()
            if not name.startswith(_KEY_MOMENT_PREFIX):
                continue
            if p.suffix.lower() in _IMAGE_EXTS:
                return p, p.name
        return None, ""

    def key_moment_path(self, scene_id: str, shot_id: str) -> Optional[Path]:
        p, _ = self._discover_key_moment(self.shot_dir(scene_id, shot_id))
        return p

    def _clear_key_moment_files(self, sdir: Path) -> None:
        if not sdir.is_dir():
            return
        for p in sdir.iterdir():
            if p.is_file() and p.name.lower().startswith(_KEY_MOMENT_PREFIX):
                try:
                    p.unlink()
                except OSError:
                    pass

    def set_key_moment_image(
        self,
        scene_id: str,
        shot_id: str,
        image_path: Union[str, Path],
    ) -> bool:
        src = Path(image_path)
        if not src.is_file():
            return False
        if not self._scene_exists(scene_id):
            return False
        sdir = self.shot_dir(scene_id, shot_id)
        if not (sdir / SHOT_MD_NAME).is_file():
            return False
        ext = src.suffix.lower()
        if ext not in _IMAGE_EXTS:
            return False
        sdir.mkdir(parents=True, exist_ok=True)
        self._clear_key_moment_files(sdir)
        dst_name = f"{_KEY_MOMENT_PREFIX}{ext}"
        dst = sdir / dst_name
        try:
            shutil.copy2(src, dst)
        except OSError:
            return False
        rel = dst_name
        return self.update_shot(scene_id, shot_id, {"key_moment_relpath": rel})

    def clear_key_moment_image(self, scene_id: str, shot_id: str) -> bool:
        sdir = self.shot_dir(scene_id, shot_id)
        self._clear_key_moment_files(sdir)
        return self.update_shot(scene_id, shot_id, {"key_moment_relpath": ""})

    def get_shot(self, scene_id: str, shot_id: str) -> Optional[StoryBoardShot]:
        md = self.shot_md_path(scene_id, shot_id)
        if not md.is_file():
            return None
        try:
            meta, body = read_md_with_meta(md)
            km_path, km_name = self._discover_key_moment(self.shot_dir(scene_id, shot_id))
            rel = meta.get("key_moment_relpath") or (km_name if km_name else "")
            if km_path and not rel:
                rel = km_path.name
            return StoryBoardShot.from_metadata(scene_id, shot_id, meta, body, rel)
        except Exception:
            return None

    def list_shot_ids(self, scene_id: str) -> List[str]:
        root = self.shots_root(scene_id)
        if not root.is_dir():
            return []
        ids: List[str] = []
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / SHOT_MD_NAME).is_file():
                ids.append(d.name)
        return ids

    def list_shots(self, scene_id: str) -> List[StoryBoardShot]:
        out: List[StoryBoardShot] = []
        for sid in self.list_shot_ids(scene_id):
            shot = self.get_shot(scene_id, sid)
            if shot:
                out.append(shot)
        return out

    def create_shot(
        self,
        scene_id: str,
        shot_id: str,
        title: str = "",
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self._scene_exists(scene_id):
            return False
        sdir = self.shot_dir(scene_id, shot_id)
        if sdir.exists():
            return False
        self._screenplay.shots_dir_path(scene_id).mkdir(parents=True, exist_ok=True)
        sdir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat()
        shot = StoryBoardShot(
            scene_id=scene_id,
            shot_id=shot_id,
            title=title,
            content=content,
            created_at=ts,
            updated_at=ts,
        )
        if metadata:
            _apply_shot_updates(shot, metadata)
        try:
            write_md_with_meta(self.shot_md_path(scene_id, shot_id), shot.to_metadata(), content)
            self._shot_changed.send(
                self,
                params={"action": "created", "scene_id": scene_id, "shot_id": shot_id},
            )
            return True
        except Exception:
            try:
                shutil.rmtree(sdir)
            except OSError:
                pass
            return False

    def update_shot(
        self,
        scene_id: str,
        shot_id: str,
        updates: Dict[str, Any],
        content: Optional[str] = None,
    ) -> bool:
        md = self.shot_md_path(scene_id, shot_id)
        if not md.is_file():
            return False
        try:
            meta, cur_body = read_md_with_meta(md)
            base = StoryBoardShot.from_metadata(scene_id, shot_id, meta, cur_body)
            updates = dict(updates)
            updates["updated_at"] = datetime.now().isoformat()
            _apply_shot_updates(base, updates)
            final_body = content if content is not None else base.content
            ok = update_md_with_meta(md, base.to_metadata(), final_body)
            if ok:
                self._shot_changed.send(
                    self,
                    params={"action": "updated", "scene_id": scene_id, "shot_id": shot_id},
                )
            return ok
        except Exception:
            return False

    def delete_shot(self, scene_id: str, shot_id: str) -> bool:
        sdir = self.shot_dir(scene_id, shot_id)
        try:
            if sdir.is_dir():
                shutil.rmtree(sdir)
                self._shot_changed.send(
                    self,
                    params={"action": "deleted", "scene_id": scene_id, "shot_id": shot_id},
                )
                return True
            return False
        except Exception:
            return False
