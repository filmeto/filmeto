"""Storyboard shot model with simplified metadata schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class StoryBoardShot:
    """A single storyboard shot under screen_plays/<scene_id>/shots/<shot_id>/."""

    scene_id: str
    shot_id: str
    shot_no: str = ""
    description: str = ""
    key_moment_relpath: str = ""
    keyframe_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_metadata(self) -> Dict[str, Any]:
        """Serialize simplified shot metadata."""
        return {
            "scene_id": self.scene_id,
            "shot_id": self.shot_id,
            "shot_no": self.shot_no,
            "key_moment_relpath": self.key_moment_relpath,
            "keyframe_context": dict(self.keyframe_context),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_metadata(
        cls,
        scene_id: str,
        shot_id: str,
        metadata: Dict[str, Any],
        content: str,
        key_moment_relpath: str = "",
    ) -> StoryBoardShot:
        keyframe_context = metadata.get("keyframe_context") or {}
        if not isinstance(keyframe_context, dict):
            keyframe_context = {}
        # Body is the canonical storyboard description; metadata fallback is for legacy data.
        legacy_desc = str(content or metadata.get("description", "") or metadata.get("content", "") or "")
        return cls(
            scene_id=metadata.get("scene_id", scene_id) or scene_id,
            shot_id=metadata.get("shot_id", shot_id) or shot_id,
            shot_no=str(metadata.get("shot_no", "") or ""),
            description=legacy_desc,
            key_moment_relpath=str(
                metadata.get("key_moment_relpath", "") or key_moment_relpath
            ),
            keyframe_context=keyframe_context,
            created_at=str(metadata.get("created_at", "") or ""),
            updated_at=str(metadata.get("updated_at", "") or ""),
        )
