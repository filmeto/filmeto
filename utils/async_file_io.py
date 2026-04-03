"""
Async file I/O helpers for YAML/JSON and small directory scans.

File reads use aiofiles; parsing/dumping runs in a worker thread so the event
loop stays responsive for large documents when used with qasync/Qt.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Awaitable, Callable, Coroutine, List, Optional, TypeVar

import aiofiles
import yaml

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class AsyncFileIoError(Exception):
    """Base exception for async file helpers."""


class AsyncFileNotFoundError(AsyncFileIoError):
    """Readable path was missing."""


class AsyncFileParseError(AsyncFileIoError):
    """Content could not be parsed (YAML/JSON)."""


class AsyncFileWriteError(AsyncFileIoError):
    """Write failed (I/O or serialization)."""


async def to_thread(fn: Callable[..., T], *args, **kwargs) -> T:
    """Run a blocking callable on the default asyncio thread pool (not Qt)."""
    return await asyncio.to_thread(fn, *args, **kwargs)


async def load_files_parallel(
    files: Sequence[Path],
    load_one: Callable[[Path], Awaitable[Optional[R]]],
) -> List[R]:
    """Load each path with ``load_one`` concurrently; drop ``None`` results."""
    if not files:
        return []
    results = await asyncio.gather(*(load_one(p) for p in files))
    return [r for r in results if r is not None]


def run_coroutine_blocking(coro: Coroutine[Any, Any, T]) -> T:
    """Run ``coro`` from sync code: ``asyncio.run`` if no loop on this thread, else a worker thread.

    Uses a one-off ``ThreadPoolExecutor``, not :class:`app.ui.core.task_manager.TaskManager`.
    Prefer ``TaskManager`` + :class:`app.ui.core.base_worker.FunctionWorker` for Qt UI–driven work.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    def _runner() -> T:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_runner).result()


run_async_safely = run_coroutine_blocking


def _yaml_dumps(data: Any) -> str:
    import io

    buf = io.StringIO()
    yaml.safe_dump(data, buf, allow_unicode=True)
    return buf.getvalue()


async def load_yaml_async(path: str | Path) -> Any:
    path = Path(path)
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
        return await to_thread(yaml.safe_load, content)
    except FileNotFoundError:
        logger.error("file not exists: %s", path)
        raise AsyncFileNotFoundError(path) from None
    except yaml.YAMLError as e:
        logger.error("YAML error: %s", e)
        raise AsyncFileParseError(f"{path}: {e}") from e


async def save_yaml_async(path: str | Path, data: Any) -> None:
    path = Path(path)
    try:
        text = await to_thread(_yaml_dumps, data)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(text)
    except FileNotFoundError:
        logger.error("file not exists: %s", path)
        raise AsyncFileNotFoundError(path) from None
    except yaml.YAMLError as e:
        logger.error("YAML error: %s", e)
        raise AsyncFileWriteError(str(e)) from e
    except OSError as e:
        logger.error("YAML save error: %s", e)
        raise AsyncFileWriteError(str(e)) from e


async def load_json_async(path: str | Path) -> Any:
    path = Path(path)
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
        return await to_thread(json.loads, content)
    except FileNotFoundError:
        logger.error("file not exists: %s", path)
        raise AsyncFileNotFoundError(path) from None
    except json.JSONDecodeError as e:
        logger.error("JSON error: %s", e)
        raise AsyncFileParseError(f"{path}: {e}") from e


async def save_json_async(
    path: str | Path, data: Any, *, indent: int = 2, ensure_ascii: bool = False
) -> None:
    path = Path(path)

    def _dumps(text: Any) -> str:
        return json.dumps(text, indent=indent, ensure_ascii=ensure_ascii)

    try:
        text = await to_thread(_dumps, data)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(text)
    except OSError as e:
        logger.error("JSON save error: %s", e)
        raise AsyncFileWriteError(str(e)) from e


async def glob_paths(directory: str | Path, pattern: str) -> List[Path]:
    """Non-blocking glob; directory scan runs in a worker thread."""
    directory = Path(directory)

    def _glob() -> List[Path]:
        if not directory.exists():
            return []
        return sorted(directory.glob(pattern))

    return await to_thread(_glob)


async def list_dir_names(path: str | Path) -> List[str]:
    """Non-blocking os.listdir."""

    def _list(p: str) -> List[str]:
        return sorted(os.listdir(p))

    return await to_thread(_list, str(path))


async def path_exists(path: str | Path) -> bool:
    return await to_thread(os.path.exists, str(path))


async def shutil_copy2_async(src: str | Path, dst: str | Path) -> None:
    await to_thread(shutil.copy2, str(src), str(dst))


def shutil_copy2(src: str | Path, dst: str | Path) -> None:
    """Copy a file without blocking the caller's event loop (uses thread pool + asyncio)."""
    run_coroutine_blocking(shutil_copy2_async(src, dst))
