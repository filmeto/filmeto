"""
Screenplay manager module for Filmeto.

Scenes live under project/screen_plays/<scene_id>/scene.md with a sibling shots/
directory for storyboard material (see app.data.story_board).
Legacy single-file screen_plays/<scene_id>.md is migrated on read.
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from utils.yaml_utils import to_thread
from utils.md_with_meta_utils import (
    read_md_with_meta,
    write_md_with_meta,
    update_md_with_meta,
    get_metadata,
    get_content,
)
from .screen_play_scene import ScreenPlayScene
from .scene_paths import SCENE_MD_NAME, SHOTS_DIR_NAME


class ScreenPlayManager:
    """Manages screenplays for a project."""

    def __init__(self, project_path: Union[str, Path]):
        self.project_path = Path(project_path)
        self.screen_plays_dir = self.project_path / "screen_plays"
        self.screen_plays_dir.mkdir(parents=True, exist_ok=True)

    def scene_root_path(self, scene_id: str) -> Path:
        return self.screen_plays_dir / scene_id

    def scene_md_path(self, scene_id: str) -> Path:
        return self.scene_root_path(scene_id) / SCENE_MD_NAME

    def shots_dir_path(self, scene_id: str) -> Path:
        return self.scene_root_path(scene_id) / SHOTS_DIR_NAME

    def legacy_scene_file_path(self, scene_id: str) -> Path:
        return self.screen_plays_dir / f"{scene_id}.md"

    def _migrate_legacy_if_needed(self, scene_id: str) -> None:
        legacy = self.legacy_scene_file_path(scene_id)
        if not legacy.is_file():
            return
        target_md = self.scene_md_path(scene_id)
        if target_md.exists():
            return
        root = self.scene_root_path(scene_id)
        root.mkdir(parents=True, exist_ok=True)
        legacy.rename(target_md)
        self.shots_dir_path(scene_id).mkdir(exist_ok=True)

    def _resolve_scene_md(self, scene_id: str) -> Optional[Path]:
        self._migrate_legacy_if_needed(scene_id)
        p = self.scene_md_path(scene_id)
        return p if p.is_file() else None

    def _iter_scene_ids(self) -> List[str]:
        ids: List[str] = []
        if not self.screen_plays_dir.exists():
            return ids
        for md in sorted(self.screen_plays_dir.glob(f"*/{SCENE_MD_NAME}")):
            ids.append(md.parent.name)
        for legacy in sorted(self.screen_plays_dir.glob("*.md")):
            sid = legacy.stem
            self._migrate_legacy_if_needed(sid)
            if sid not in ids:
                ids.append(sid)
        ids.sort()
        return ids

    def create_scene(
        self,
        scene_id: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if metadata is None:
            metadata = {}

        scene = ScreenPlayScene(
            scene_id=scene_id,
            title=title,
            content=content,
            scene_number=metadata.get("scene_number", ""),
            location=metadata.get("location", ""),
            time_of_day=metadata.get("time_of_day", ""),
            genre=metadata.get("genre", ""),
            logline=metadata.get("logline", ""),
            characters=metadata.get("characters", []),
            story_beat=metadata.get("story_beat", ""),
            page_count=metadata.get("page_count", 0),
            duration_minutes=metadata.get("duration_minutes", 0),
            tags=metadata.get("tags", []),
            status=metadata.get("status", "draft"),
            revision_number=metadata.get("revision_number", 1),
            created_at=metadata.get("created_at", self._get_timestamp()),
            updated_at=metadata.get("updated_at", self._get_timestamp()),
        )

        scene_data = scene.to_dict()
        metadata_for_storage = {
            k: v for k, v in scene_data.items() if k not in ["scene_id", "title", "content"]
        }
        standard_fields = {
            "scene_number",
            "location",
            "time_of_day",
            "genre",
            "logline",
            "characters",
            "story_beat",
            "page_count",
            "duration_minutes",
            "tags",
            "status",
            "revision_number",
            "created_at",
            "updated_at",
        }
        for key, value in metadata.items():
            if key not in standard_fields and key not in metadata_for_storage:
                metadata_for_storage[key] = value

        metadata_for_storage["scene_id"] = scene_id
        metadata_for_storage["title"] = title

        root = self.scene_root_path(scene_id)
        root.mkdir(parents=True, exist_ok=True)
        self.shots_dir_path(scene_id).mkdir(exist_ok=True)
        legacy = self.legacy_scene_file_path(scene_id)
        if legacy.exists():
            try:
                legacy.unlink()
            except OSError:
                pass

        scene_file_path = self.scene_md_path(scene_id)
        try:
            write_md_with_meta(scene_file_path, metadata_for_storage, content)
            return True
        except Exception:
            return False

    def get_scene(self, scene_id: str) -> Optional[ScreenPlayScene]:
        scene_file_path = self._resolve_scene_md(scene_id)
        if scene_file_path is None:
            return None

        try:
            metadata, content = read_md_with_meta(scene_file_path)
            title = metadata.get("title", scene_id)

            return ScreenPlayScene(
                scene_id=scene_id,
                title=title,
                content=content,
                scene_number=metadata.get("scene_number", ""),
                location=metadata.get("location", ""),
                time_of_day=metadata.get("time_of_day", ""),
                genre=metadata.get("genre", ""),
                logline=metadata.get("logline", ""),
                characters=metadata.get("characters", []),
                story_beat=metadata.get("story_beat", ""),
                page_count=metadata.get("page_count", 0),
                duration_minutes=metadata.get("duration_minutes", 0),
                tags=metadata.get("tags", []),
                status=metadata.get("status", "draft"),
                revision_number=metadata.get("revision_number", 1),
                created_at=metadata.get("created_at", ""),
                updated_at=metadata.get("updated_at", ""),
            )
        except Exception:
            return None

    def update_scene(
        self,
        scene_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
    ) -> bool:
        scene_file_path = self._resolve_scene_md(scene_id)
        if scene_file_path is None:
            return False

        try:
            current_metadata, current_content = read_md_with_meta(scene_file_path)

            updates: Dict[str, Any] = {}
            if title is not None:
                updates["title"] = title
                current_metadata["title"] = title
            if metadata_updates:
                updates.update(metadata_updates)
                current_metadata.update(metadata_updates)

            updates["updated_at"] = self._get_timestamp()
            current_metadata["updated_at"] = self._get_timestamp()

            final_content = content if content is not None else current_content

            return update_md_with_meta(scene_file_path, updates, final_content)
        except Exception:
            return False

    def delete_scene(self, scene_id: str) -> bool:
        root = self.scene_root_path(scene_id)
        legacy = self.legacy_scene_file_path(scene_id)
        try:
            if root.is_dir() and self.scene_md_path(scene_id).exists():
                shutil.rmtree(root)
                if legacy.exists():
                    legacy.unlink()
                return True
            if legacy.exists():
                os.remove(legacy)
                return True
            return False
        except Exception:
            return False

    def list_scenes(self) -> List[ScreenPlayScene]:
        scenes: List[ScreenPlayScene] = []
        for scene_id in self._iter_scene_ids():
            scene = self.get_scene(scene_id)
            if scene:
                scenes.append(scene)
        return scenes

    async def list_scenes_async(self) -> List[ScreenPlayScene]:
        scene_ids = await to_thread(self._iter_scene_ids)

        async def _one(sid: str) -> Optional[ScreenPlayScene]:
            return await to_thread(self.get_scene, sid)

        loaded = await asyncio.gather(*(_one(sid) for sid in scene_ids))
        return [s for s in loaded if s is not None]

    def get_scene_by_title(self, title: str) -> Optional[ScreenPlayScene]:
        for scene in self.list_scenes():
            if scene.title.lower() == title.lower():
                return scene
        return None

    def _get_timestamp(self) -> str:
        from datetime import datetime

        return datetime.now().isoformat()

    def get_scene_metadata(self, scene_id: str) -> Optional[Dict[str, Any]]:
        scene_file_path = self._resolve_scene_md(scene_id)
        if scene_file_path is None:
            return None

        try:
            return get_metadata(scene_file_path)
        except Exception:
            return None

    def get_scene_content(self, scene_id: str) -> Optional[str]:
        scene_file_path = self._resolve_scene_md(scene_id)
        if scene_file_path is None:
            return None

        try:
            return get_content(scene_file_path)
        except Exception:
            return None

    def update_scene_metadata(self, scene_id: str, metadata_updates: Dict[str, Any]) -> bool:
        scene_file_path = self._resolve_scene_md(scene_id)
        if scene_file_path is None:
            return False

        try:
            current_content = self.get_scene_content(scene_id)
            if current_content is None:
                return False

            metadata_updates["updated_at"] = self._get_timestamp()
            return update_md_with_meta(scene_file_path, metadata_updates, current_content)
        except Exception:
            return False

    def bulk_create_scenes(self, scenes_data: List[Dict[str, Any]]) -> Dict[str, bool]:
        results = {}
        for scene_data in scenes_data:
            scene_id = scene_data.get("scene_id")
            title = scene_data.get("title", "")
            content = scene_data.get("content", "")
            metadata = scene_data.get("metadata", {})

            success = self.create_scene(scene_id, title, content, metadata)
            results[scene_id] = success

        return results

    def get_scenes_by_character(self, character_name: str) -> List[ScreenPlayScene]:
        matching_scenes = []
        all_scenes = self.list_scenes()

        for scene in all_scenes:
            characters = scene.characters if hasattr(scene, "characters") else []
            if character_name in characters:
                matching_scenes.append(scene)

        return matching_scenes

    def get_scenes_by_location(self, location: str) -> List[ScreenPlayScene]:
        matching_scenes = []
        all_scenes = self.list_scenes()

        for scene in all_scenes:
            scene_location = scene.location if hasattr(scene, "location") else ""
            if location.lower() in scene_location.lower():
                matching_scenes.append(scene)

        return matching_scenes

    def delete_all_scenes(self) -> Dict[str, Any]:
        scenes = self.list_scenes()
        deleted_scene_ids = []
        failed_scene_ids = []

        for scene in scenes:
            scene_id = scene.scene_id
            if self.delete_scene(scene_id):
                deleted_scene_ids.append(scene_id)
            else:
                failed_scene_ids.append(scene_id)

        return {
            "deleted_count": len(deleted_scene_ids),
            "deleted_scene_ids": deleted_scene_ids,
            "failed_scene_ids": failed_scene_ids,
            "total_count": len(scenes),
        }

    def delete_scenes(self, scene_ids: List[str]) -> Dict[str, Any]:
        deleted_scene_ids = []
        not_found_ids = []
        failed_scene_ids = []

        for scene_id in scene_ids:
            scene = self.get_scene(scene_id)
            if scene is None:
                not_found_ids.append(scene_id)
                continue

            if self.delete_scene(scene_id):
                deleted_scene_ids.append(scene_id)
            else:
                failed_scene_ids.append(scene_id)

        return {
            "deleted_count": len(deleted_scene_ids),
            "deleted_scene_ids": deleted_scene_ids,
            "not_found_ids": not_found_ids,
            "failed_scene_ids": failed_scene_ids,
            "requested_count": len(scene_ids),
        }
