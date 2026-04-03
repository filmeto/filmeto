from typing import Any

import logging

from utils.async_file_io import (
    AsyncFileIoError,
    AsyncFileNotFoundError,
    AsyncFileParseError,
    AsyncFileWriteError,
    glob_paths,
    list_dir_names,
    load_files_parallel,
    load_json_async,
    load_yaml_async,
    path_exists,
    run_coroutine_blocking,
    save_json_async,
    save_yaml_async,
    shutil_copy2,
    to_thread,
)

logger = logging.getLogger(__name__)

__all__ = (
    "load_yaml",
    "save_yaml",
    "load_yaml_async",
    "save_yaml_async",
    "load_json_async",
    "save_json_async",
    "AsyncFileIoError",
    "AsyncFileNotFoundError",
    "AsyncFileParseError",
    "AsyncFileWriteError",
    "glob_paths",
    "list_dir_names",
    "load_files_parallel",
    "path_exists",
    "run_coroutine_blocking",
    "to_thread",
    "shutil_copy2",
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
