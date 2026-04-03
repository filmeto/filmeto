from typing import Any

import logging

from utils.async_file_io import (
    AsyncFileIoError,
    AsyncFileNotFoundError,
    AsyncFileParseError,
    AsyncFileWriteError,
    load_yaml_async,
    save_yaml_async,
    run_coroutine_blocking,
)

logger = logging.getLogger(__name__)

__all__ = (
    "load_yaml",
    "save_yaml",
    "load_yaml_async",
    "save_yaml_async",
    "AsyncFileIoError",
    "AsyncFileNotFoundError",
    "AsyncFileParseError",
    "AsyncFileWriteError",
)


def load_yaml(path):
    """Load YAML via async I/O (thread offload when a loop is already running)."""
    try:
        return run_coroutine_blocking(load_yaml_async(path))
    except AsyncFileNotFoundError:
        logger.error("file not exists")
        return None
    except AsyncFileParseError as e:
        logger.error("YAML error: %s", e)
        return None


def save_yaml(path, data: Any) -> None:
    """Persist YAML via async I/O (thread offload when a loop is already running)."""
    try:
        run_coroutine_blocking(save_yaml_async(path, data))
    except (AsyncFileNotFoundError, AsyncFileParseError, AsyncFileWriteError) as e:
        logger.error("YAML save error: %s", e)