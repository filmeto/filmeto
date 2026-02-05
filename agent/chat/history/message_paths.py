from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ParsedMessageFilename:
    timestamp: int
    message_id: str
    sender: str


def normalize_timestamp(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def utc_timestamp_seconds(timestamp: datetime) -> int:
    return int(normalize_timestamp(timestamp).timestamp())


def date_str_from_timestamp(timestamp: datetime) -> str:
    return normalize_timestamp(timestamp).strftime("%Y%m%d")


def sanitize_sender(sender: str) -> str:
    if not sender:
        return "unknown"
    return sender.replace(" ", "_").replace("/", "_").replace("\\", "_")


def build_message_filename(timestamp: datetime, message_id: str, sender: str) -> str:
    timestamp_seconds = utc_timestamp_seconds(timestamp)
    safe_sender = sanitize_sender(sender)
    return f"{timestamp_seconds}_{message_id}_{safe_sender}.md"


def parse_message_filename(path: Path) -> Optional[ParsedMessageFilename]:
    name = path.stem
    parts = name.split("_", 2)
    if len(parts) < 2:
        return None
    try:
        timestamp = int(parts[0])
    except ValueError:
        return None
    message_id = parts[1]
    sender = parts[2] if len(parts) > 2 else ""
    return ParsedMessageFilename(timestamp=timestamp, message_id=message_id, sender=sender)
