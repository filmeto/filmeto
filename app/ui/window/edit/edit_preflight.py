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
    """Warm imports for MainWindowTopSideBar and its typical dependencies."""
    try:
        import app.ui.window.edit.top_side_bar  # noqa: F401
        import app.ui.drawing_tools  # noqa: F401
        import app.ui.dialog.mac_button  # noqa: F401
        import app.ui.project_menu.project_menu  # noqa: F401
        import app.ui.server_status  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_top_bar: %s", e)


def preflight_edit_bottom_bar() -> None:
    """Warm imports for MainWindowBottomSideBar / PlayControlWidget."""
    try:
        import app.ui.play_control  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_bottom_bar: %s", e)


def preflight_edit_h_layout_shell() -> None:
    """Warm imports for deferred H layout shell (workspace container + side skeletons)."""
    try:
        import app.ui.window.edit.h_layout  # noqa: F401
        import app.ui.window.edit.workspace  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_h_layout_shell: %s", e)


def preflight_workspace_top() -> None:
    """Warm imports for editor / canvas (MainWindowWorkspaceTop)."""
    try:
        import app.ui.window.edit.workspace_top  # noqa: F401
        import app.ui.editor  # noqa: F401
        import app.ui.panels  # noqa: F401
    except Exception as e:
        logger.debug("preflight_workspace_top: %s", e)


def preflight_workspace_bottom() -> None:
    """Warm imports for timeline (MainWindowWorkspaceBottom)."""
    try:
        import app.ui.window.edit.workspace_bottom  # noqa: F401
        import app.ui.timeline.timeline_container  # noqa: F401
    except Exception as e:
        logger.debug("preflight_workspace_bottom: %s", e)


def preflight_left_tool_strip() -> None:
    """Warm imports for left tool strip."""
    try:
        import app.ui.window.edit.left_side_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_left_tool_strip: %s", e)


def preflight_right_tool_strip() -> None:
    """Warm imports for right tool strip."""
    try:
        import app.ui.window.edit.right_side_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_right_tool_strip: %s", e)


PREFLIGHT_BY_STAGE = (
    preflight_edit_top_bar,
    preflight_edit_bottom_bar,
    preflight_edit_h_layout_shell,
    preflight_workspace_top,
    preflight_workspace_bottom,
    preflight_left_tool_strip,
    preflight_right_tool_strip,
)
