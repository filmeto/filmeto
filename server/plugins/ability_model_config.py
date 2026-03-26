"""
Unified server configuration for per-ability model entries (enable/disable and extensions).

Stored under ServerConfig.parameters[\"ability_models\"] as a list of maps:

    [
        {"ability": "text2image", "model_id": "wanx2.1-t2i-turbo", "enabled": true},
        ...
    ]
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

ABILITY_MODELS_KEY = "ability_models"


def normalize_ability_models_raw(raw: Any) -> List[Dict[str, Any]]:
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        ability = item.get("ability") or item.get("capability")
        mid = item.get("model_id") or item.get("model") or item.get("name")
        if not ability or not mid:
            continue
        row: Dict[str, Any] = {
            "ability": str(ability),
            "model_id": str(mid),
            "enabled": bool(item.get("enabled", True)),
        }
        for k, v in item.items():
            if k in ("ability", "capability", "model_id", "model", "name", "enabled"):
                continue
            row[k] = v
        out.append(row)
    return out


def normalize_catalog_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    ability = item.get("ability") or item.get("capability")
    mid = item.get("model_id") or item.get("model")
    if not ability or not mid:
        return None
    return {
        "ability": str(ability),
        "model_id": str(mid),
        "label": str(item.get("label") or mid),
        "default_enabled": bool(item.get("default_enabled", True)),
    }


def merge_catalog_with_saved(
    catalog: List[Dict[str, Any]],
    saved: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    saved_norm = normalize_ability_models_raw(saved)
    saved_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for s in saved_norm:
        saved_map[(s["ability"], s["model_id"])] = s

    entries: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()

    for c in catalog:
        key = (c["ability"], c["model_id"])
        seen.add(key)
        s = saved_map.get(key, {})
        entries.append(
            {
                "ability": c["ability"],
                "model_id": c["model_id"],
                "label": c.get("label") or c["model_id"],
                "enabled": s.get("enabled", c.get("default_enabled", True)),
                "custom": False,
            }
        )

    for s in saved_norm:
        key = (s["ability"], s["model_id"])
        if key in seen:
            continue
        entries.append(
            {
                "ability": s["ability"],
                "model_id": s["model_id"],
                "label": str(s.get("label", s["model_id"])),
                "enabled": s.get("enabled", True),
                "custom": True,
            }
        )
        seen.add(key)

    return entries


def serialize_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {"ability": e["ability"], "model_id": e["model_id"], "enabled": bool(e.get("enabled", True))}
        for e in entries
    ]


def is_model_enabled_for_ability(
    parameters: Dict[str, Any],
    ability: str,
    model_id: str,
    *,
    default: bool = True,
) -> bool:
    """
    Runtime helper: if ``ability_models`` is missing or empty, all models stay enabled
    (``default``). A non-empty list controls only listed (ability, model_id) pairs;
    ids not present in the list still use ``default`` (not a strict whitelist).
    """
    raw = parameters.get(ABILITY_MODELS_KEY)
    if not raw:
        return default
    for item in normalize_ability_models_raw(raw):
        if item["ability"] == ability and item["model_id"] == model_id:
            return bool(item.get("enabled", True))
    return default
