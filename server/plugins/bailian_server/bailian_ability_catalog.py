"""Build ability_models_catalog rows for Bailian from models.yml."""

from __future__ import annotations

from typing import Any, Dict, List

from server.plugins.bailian_server.models_config import models_config


def build_bailian_ability_catalog() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for name in models_config.get_dashscope_models():
        rows.append(
            {
                "ability": "chat_completion",
                "model_id": name,
                "label": name,
                "default_enabled": True,
            }
        )

    for name in models_config.get_coding_plan_models(with_prefix=True):
        rows.append(
            {
                "ability": "chat_completion",
                "model_id": name,
                "label": f"{name} (Coding Plan)",
                "default_enabled": True,
            }
        )

    for name in models_config.get_text_to_image_models():
        rows.append(
            {
                "ability": "text2image",
                "model_id": name,
                "label": name,
                "default_enabled": True,
            }
        )

    for name in models_config.get_image_to_image_models():
        rows.append(
            {
                "ability": "image2image",
                "model_id": name,
                "label": name,
                "default_enabled": True,
            }
        )

    for name in models_config.get_image_editing_models():
        rows.append(
            {
                "ability": "imageedit",
                "model_id": name,
                "label": name,
                "default_enabled": True,
            }
        )

    for name in models_config.get_image_to_video_models():
        rows.append(
            {
                "ability": "image2video",
                "model_id": name,
                "label": name,
                "default_enabled": True,
            }
        )

    for name in models_config.get_text_to_video_models():
        rows.append(
            {
                "ability": "text2video",
                "model_id": name,
                "label": name,
                "default_enabled": True,
            }
        )

    return rows


def build_default_bailian_ability_models() -> List[Dict[str, Any]]:
    """
    Initial ``parameters.ability_models`` payload for Bailian: every catalog
    ( DashScope chat, coding-plan chat, T2I, I2I ) model entry with enabled=True.
    Used when no ``ability_models`` key exists yet (e.g. new server / legacy yml).
    """
    return [
        {"ability": r["ability"], "model_id": r["model_id"], "enabled": True}
        for r in build_bailian_ability_catalog()
    ]
