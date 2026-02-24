"""Manager classes for chat list functionality.

This package contains components that manage:
- History loading and caching
- Skill lifecycle and merging
- Crew member metadata
- Scroll position
"""

from app.ui.chat.list.managers.history_manager import HistoryManager
from app.ui.chat.list.managers.skill_manager import SkillManager
from app.ui.chat.list.managers.metadata_resolver import MetadataResolver
from app.ui.chat.list.managers.scroll_manager import ScrollManager

__all__ = [
    "HistoryManager",
    "SkillManager",
    "MetadataResolver",
    "ScrollManager",
]
