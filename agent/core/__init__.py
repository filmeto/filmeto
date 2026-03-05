"""
Filmeto Agent Core Module

Exports instance management, utilities, and constants for the FilmetoAgent system.
"""

# Instance management
from agent.core.filmeto_instance import FilmetoInstanceManager

# Utilities
from agent.core.filmeto_utils import (
    extract_text_content,
    truncate_text,
    get_workspace_path_safe,
    get_project_from_workspace,
    resolve_project_name,
)

# Constants
from agent.core.filmeto_constants import (
    PRODUCER_NAME,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_STREAMING,
)

__all__ = [
    # Instance management
    "FilmetoInstanceManager",
    # Utilities
    "extract_text_content",
    "truncate_text",
    "get_workspace_path_safe",
    "get_project_from_workspace",
    "resolve_project_name",
    # Constants
    "PRODUCER_NAME",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_STREAMING",
]