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


def utc_timestamp_milliseconds(timestamp: datetime) -> int:
    return int(normalize_timestamp(timestamp).timestamp() * 1000)


def date_str_from_timestamp(timestamp: datetime) -> str:
    return normalize_timestamp(timestamp).strftime("%Y%m%d")


def sanitize_sender(sender: str) -> str:
    if not sender:
        return "unknown"
    return sender.replace(" ", "_").replace("/", "_").replace("\\", "_")


def build_message_filename(timestamp: datetime, message_id: str, sender: str) -> str:
    timestamp_ms = utc_timestamp_milliseconds(timestamp)
    safe_sender = sanitize_sender(sender)
    return f"{timestamp_ms}_{safe_sender}_{message_id}.md"


def parse_message_filename(path: Path) -> Optional[ParsedMessageFilename]:
    """
    Parse a message filename in the format: {millisecond_timestamp}_{sender}_{message_id}.md

    Args:
        path: Path to the message file

    Returns:
        ParsedMessageFilename with timestamp in milliseconds, or None if parsing fails
    """
    name = path.stem
    # Find first underscore (end of timestamp) and last underscore (start of message_id)
    first_underscore = name.find("_")
    last_underscore = name.rfind("_")

    if first_underscore == -1 or last_underscore == -1 or first_underscore >= last_underscore:
        return None

    try:
        # Parse timestamp (milliseconds)
        timestamp = int(name[:first_underscore])
    except ValueError:
        return None

    # Extract sender (between first and last underscore) and message_id (after last underscore)
    sender = name[first_underscore + 1:last_underscore]
    message_id = name[last_underscore + 1:]

    if not message_id:
        return None

    return ParsedMessageFilename(timestamp=timestamp, message_id=message_id, sender=sender)
