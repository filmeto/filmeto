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

        # Safely parse priority (default to 0 on any error)
        try:
            priority_val = item.get("priority", 0)
            priority = int(priority_val) if priority_val is not None else 0
        except (ValueError, TypeError):
            priority = 0

        # Safely parse tags (ensure it's a list of strings)
        tags_val = item.get("tags", [])
        if isinstance(tags_val, list):
            tags = [str(t) for t in tags_val if t is not None]
        else:
            tags = []

        row: Dict[str, Any] = {
            "ability": str(ability),
            "model_id": str(mid),
            "enabled": bool(item.get("enabled", True)),
            "priority": priority,
            "tags": tags,
        }
        for k, v in item.items():
            if k in ("ability", "capability", "model_id", "model", "name", "enabled", "priority", "tags"):
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
                "priority": s.get("priority", 0),
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
                "priority": s.get("priority", 0),
                "custom": True,
            }
        )
        seen.add(key)

    # Sort by priority descending (higher priority = first)
    entries.sort(key=lambda e: -e.get("priority", 0))

    return entries


def serialize_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Save order based on list position: first item = highest priority
    # Priority decreases from (len-1) to 0 as we go down the list
    result = []
    for i, e in enumerate(entries):
        result.append(
            {
                "ability": e["ability"],
                "model_id": e["model_id"],
                "enabled": bool(e.get("enabled", True)),
                "priority": len(entries) - 1 - i,
            }
        )
    return result


def is_model_enabled_for_ability(
    parameters: Dict[str, Any],
    ability: str,
    model_id: str,
    *,
    default: bool = False,
) -> bool:
    """
    Runtime helper: if ``ability_models`` is missing or empty, all models stay disabled
    (``default``). A non-empty list controls only listed (ability, model_id) pairs;
    ids not present in the list are disabled.
    """
    raw = parameters.get(ABILITY_MODELS_KEY)
    if not raw:
        return default
    for item in normalize_ability_models_raw(raw):
        if item["ability"] == ability and item["model_id"] == model_id:
            return bool(item.get("enabled", True))
    return default


def get_model_priority(
    parameters: Dict[str, Any],
    ability: str,
    model_id: str,
    *,
    default: int = 0,
) -> int:
    """
    Get priority for a specific (ability, model_id) pair.

    Priority determines selection order when multiple models are available.
    Higher priority values are preferred.

    Args:
        parameters: ServerConfig.parameters dict
        ability: Ability/capability name (e.g., "text2image")
        model_id: Model identifier
        default: Default priority if not configured (default: 0)

    Returns:
        Priority value (higher = more preferred)
    """
    raw = parameters.get(ABILITY_MODELS_KEY)
    if not raw:
        return default
    for item in normalize_ability_models_raw(raw):
        if item["ability"] == ability and item["model_id"] == model_id:
            return int(item.get("priority", default))
    return default


def get_model_tags(
    parameters: Dict[str, Any],
    ability: str,
    model_id: str,
) -> List[str]:
    """
    Get tags for a specific (ability, model_id) pair.

    Tags can be used for filtering models during selection.

    Args:
        parameters: ServerConfig.parameters dict
        ability: Ability/capability name (e.g., "text2image")
        model_id: Model identifier

    Returns:
        List of tags (empty list if not configured)
    """
    raw = parameters.get(ABILITY_MODELS_KEY)
    if not raw:
        return []
    for item in normalize_ability_models_raw(raw):
        if item["ability"] == ability and item["model_id"] == model_id:
            tags = item.get("tags", [])
            return list(tags) if isinstance(tags, list) else []
    return []


def set_model_config(
    parameters: Dict[str, Any],
    ability: str,
    model_id: str,
    *,
    enabled: Optional[bool] = None,
    priority: Optional[int] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Set configuration for a specific (ability, model_id) pair.

    Creates or updates the ability_models configuration in parameters.
    Returns updated parameters dict (does not mutate original).

    Args:
        parameters: Original parameters dict
        ability: Ability/capability name
        model_id: Model identifier
        enabled: Whether the model is enabled (None = don't change)
        priority: Priority value (None = don't change)
        tags: Tags list (None = don't change)

    Returns:
        Updated parameters dict
    """
    # Deep copy to avoid mutation
    result = {k: v for k, v in parameters.items() if k != ABILITY_MODELS_KEY}

    # Get existing entries
    raw = parameters.get(ABILITY_MODELS_KEY, [])
    entries = normalize_ability_models_raw(raw)

    # Find and update existing entry, or create new one
    found = False
    new_entries = []
    for entry in entries:
        if entry["ability"] == ability and entry["model_id"] == model_id:
            found = True
            updated = dict(entry)
            if enabled is not None:
                updated["enabled"] = enabled
            if priority is not None:
                updated["priority"] = priority
            if tags is not None:
                updated["tags"] = tags
            new_entries.append(updated)
        else:
            new_entries.append(entry)

    if not found:
        new_entry = {
            "ability": ability,
            "model_id": model_id,
            "enabled": enabled if enabled is not None else True,
            "priority": priority if priority is not None else 0,
            "tags": tags if tags is not None else [],
        }
        new_entries.append(new_entry)

    result[ABILITY_MODELS_KEY] = new_entries
    return result
