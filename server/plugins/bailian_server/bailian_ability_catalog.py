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

    return rows
