"""
Storyboard shot model: one shot belongs to a screenplay scene directory.

Metadata is stored as YAML frontmatter in shot.md, grouped by production layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VisualLayerMeta:
    picture_content: str = ""
    composition: str = ""
    color_tendency: str = ""
    key_motion: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> VisualLayerMeta:
        if not data:
            return cls()
        return cls(
            picture_content=str(data.get("picture_content", "") or ""),
            composition=str(data.get("composition", "") or ""),
            color_tendency=str(data.get("color_tendency", "") or ""),
            key_motion=str(data.get("key_motion", "") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "picture_content": self.picture_content,
            "composition": self.composition,
            "color_tendency": self.color_tendency,
            "key_motion": self.key_motion,
        }


@dataclass
class AudioLayerMeta:
    dialogue: str = ""
    ambient: str = ""
    sfx: str = ""
    music_mood_or_rhythm: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> AudioLayerMeta:
        if not data:
            return cls()
        return cls(
            dialogue=str(data.get("dialogue", "") or ""),
            ambient=str(data.get("ambient", "") or ""),
            sfx=str(data.get("sfx", "") or ""),
            music_mood_or_rhythm=str(data.get("music_mood_or_rhythm", "") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dialogue": self.dialogue,
            "ambient": self.ambient,
            "sfx": self.sfx,
            "music_mood_or_rhythm": self.music_mood_or_rhythm,
        }


@dataclass
class TechDirectorLayerMeta:
    camera_move: str = ""
    axis: str = ""
    vfx_tags: List[str] = field(default_factory=list)
    edit_markers: str = ""
    render_notes: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> TechDirectorLayerMeta:
        if not data:
            return cls()
        raw_tags = data.get("vfx_tags") or []
        if isinstance(raw_tags, str):
            vfx_tags = [raw_tags] if raw_tags else []
        else:
            vfx_tags = [str(x) for x in raw_tags]
        return cls(
            camera_move=str(data.get("camera_move", "") or ""),
            axis=str(data.get("axis", "") or ""),
            vfx_tags=vfx_tags,
            edit_markers=str(data.get("edit_markers", "") or ""),
            render_notes=str(data.get("render_notes", "") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_move": self.camera_move,
            "axis": self.axis,
            "vfx_tags": list(self.vfx_tags),
            "edit_markers": self.edit_markers,
            "render_notes": self.render_notes,
        }


@dataclass
class UxLogicLayerMeta:
    user_flow: str = ""
    ui_state_transitions: str = ""
    loading_error_empty: str = ""
    navigation: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> UxLogicLayerMeta:
        if not data:
            return cls()
        return cls(
            user_flow=str(data.get("user_flow", "") or ""),
            ui_state_transitions=str(data.get("ui_state_transitions", "") or ""),
            loading_error_empty=str(data.get("loading_error_empty", "") or ""),
            navigation=str(data.get("navigation", "") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_flow": self.user_flow,
            "ui_state_transitions": self.ui_state_transitions,
            "loading_error_empty": self.loading_error_empty,
            "navigation": self.navigation,
        }


@dataclass
class StoryBoardShot:
    """A single storyboard shot under screen_plays/<scene_id>/shots/<shot_id>/."""

    scene_id: str
    shot_id: str
    title: str = ""
    content: str = ""
    visual: VisualLayerMeta = field(default_factory=VisualLayerMeta)
    audio: AudioLayerMeta = field(default_factory=AudioLayerMeta)
    tech_director: TechDirectorLayerMeta = field(default_factory=TechDirectorLayerMeta)
    ux_logic: UxLogicLayerMeta = field(default_factory=UxLogicLayerMeta)
    key_moment_relpath: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_metadata(self) -> Dict[str, Any]:
        """Flatten for YAML frontmatter (nested groups preserved)."""
        return {
            "scene_id": self.scene_id,
            "shot_id": self.shot_id,
            "title": self.title,
            "visual": self.visual.to_dict(),
            "audio": self.audio.to_dict(),
            "tech_director": self.tech_director.to_dict(),
            "ux_logic": self.ux_logic.to_dict(),
            "key_moment_relpath": self.key_moment_relpath,
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
        return cls(
            scene_id=metadata.get("scene_id", scene_id) or scene_id,
            shot_id=metadata.get("shot_id", shot_id) or shot_id,
            title=str(metadata.get("title", "") or ""),
            content=content,
            visual=VisualLayerMeta.from_dict(metadata.get("visual")),
            audio=AudioLayerMeta.from_dict(metadata.get("audio")),
            tech_director=TechDirectorLayerMeta.from_dict(metadata.get("tech_director")),
            ux_logic=UxLogicLayerMeta.from_dict(metadata.get("ux_logic")),
            key_moment_relpath=str(
                metadata.get("key_moment_relpath", "") or key_moment_relpath
            ),
            created_at=str(metadata.get("created_at", "") or ""),
            updated_at=str(metadata.get("updated_at", "") or ""),
        )
