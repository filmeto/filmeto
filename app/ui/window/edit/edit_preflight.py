# -*- coding: utf-8 -*-
"""
Background preflight for edit shell staged load.

Qt widgets must be created on the GUI thread; these callables only perform
cheap import / warm-cache work on a TaskManager worker thread so the main
thread spends less time inside each attach_* step.
"""
import logging

logger = logging.getLogger(__name__)


def preflight_edit_top_bar() -> None:
    try:
        import app.ui.window.edit.top_side_bar  # noqa: F401
        import app.ui.drawing_tools  # noqa: F401
        import app.ui.dialog.mac_button  # noqa: F401
        import app.ui.project_menu.project_menu  # noqa: F401
        import app.ui.server_status  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_top_bar: %s", e)


def preflight_bottom_bar_shell() -> None:
    """Bottom bar chrome only (no PlayControlWidget yet)."""
    try:
        import app.ui.window.edit.bottom_side_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_bottom_bar_shell: %s", e)


def preflight_edit_h_layout_shell() -> None:
    try:
        import app.ui.window.edit.h_layout  # noqa: F401
        import app.ui.window.edit.workspace  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_h_layout_shell: %s", e)


def preflight_workspace_top() -> None:
    try:
        import app.ui.window.edit.workspace_top  # noqa: F401
        import app.ui.editor  # noqa: F401
        import app.ui.panels  # noqa: F401
    except Exception as e:
        logger.debug("preflight_workspace_top: %s", e)


def preflight_workspace_bottom() -> None:
    try:
        import app.ui.window.edit.workspace_bottom  # noqa: F401
        import app.ui.timeline.timeline_container  # noqa: F401
    except Exception as e:
        logger.debug("preflight_workspace_bottom: %s", e)


def preflight_left_tool_strip_shell() -> None:
    try:
        import app.ui.window.edit.left_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_left_tool_strip_shell: %s", e)


def preflight_right_tool_strip_shell() -> None:
    try:
        import app.ui.window.edit.right_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_right_tool_strip_shell: %s", e)


def preflight_left_side_bar_content() -> None:
    try:
        import app.ui.window.edit.left_side_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_left_side_bar_content: %s", e)


def preflight_right_side_bar_content() -> None:
    try:
        import app.ui.window.edit.right_side_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_right_side_bar_content: %s", e)


def preflight_play_control() -> None:
    try:
        import app.ui.play_control  # noqa: F401
    except Exception as e:
        logger.debug("preflight_play_control: %s", e)


PREFLIGHT_BY_STAGE = (
    preflight_edit_top_bar,
    preflight_bottom_bar_shell,
    preflight_edit_h_layout_shell,
    preflight_workspace_top,
    preflight_workspace_bottom,
    preflight_left_tool_strip_shell,
    preflight_right_tool_strip_shell,
    preflight_left_side_bar_content,
    preflight_right_side_bar_content,
    preflight_play_control,
)
