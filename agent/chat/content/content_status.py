"""Content status enumeration for Filmeto agent system."""
from enum import Enum


class ContentStatus(str, Enum):
    """Status of content during its lifecycle."""
    CREATING = "creating"      # Content is being created
    UPDATING = "updating"      # Content is being updated
    COMPLETED = "completed"    # Content is completed
    FAILED = "failed"          # Content creation/update failed
